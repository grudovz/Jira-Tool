"""
Plans and creates the team's SAFe PI Objectives in LPDA for the /createobjectives skill,
and lists/closes them around each system demo for the /systemdemo skill.

One objective per team epic, following the conventions of the PI 26.4 objectives
(e.g. LPDA-3307, LPDA-3313): issue type "PI Objective", component TRS, reporter and
assignee = the JIRA account of the token in .env, fixVersion "LPDA - PI#<pi>", label "Iteration<N>", Planned Business
Value, Target end = end date of that iteration's sprint, Committed = "Committed", and
one "relates to" link to the epic.

The iteration is the PI sprint holding the epic's last planned story. PI sprints are
the TravelScript board sprints named "<pi>-<N>" (e.g. "26.4-3"); the IP sprint
("<pi>-IP") is not an iteration.

Around a system demo, TRS objectives in status Reviewing are listed on the PI's
"System Demos" Confluence page, one Jira Legacy macro line each, "(PBV: n, ABV: )".
After the demo each one moves to Done or Partially Done with its Actual Business Value.

Usage:
    python objectives_helper.py plan --pi 27.1 LPDA-1 LPDA-2 ...   (read-only, prints JSON)
    python objectives_helper.py create <plan.json>                  (writes to JIRA)
    python objectives_helper.py reviewing --pi 26.4                 (read-only, prints JSON)
    python objectives_helper.py close <close.json>                  (writes to JIRA)
"""
import argparse
import html
import json
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv()

OBJECTIVE_PROJECT = "LPDA"
OBJECTIVE_TYPE = "PI Objective"
OBJECTIVE_COMPONENT = "TRS"
PLANNED_BV_FIELD = "customfield_16200"
ACTUAL_BV_FIELD = "customfield_16302"
TARGET_END_FIELD = "customfield_12808"
COMMITTED_FIELD = "customfield_17500"
TOP_PLANNED_BV = 10  # highest-priority epic; each next one gets 1 less
ENV_TAGS = ("DEV", "UAT", "PRD")
CLOSING_STATUSES = ("Done", "Partially Done")  # the only transitions /systemdemo makes, from Reviewing

# Jira Legacy macro settings, copied from the TRS lines already on the System Demos pages.
# The JIRA server's name and id as Confluence knows it live in .env (internal identifiers).
JIRA_MACRO_SERVER_ENV = "CONFLUENCE_JIRA_SERVER"
JIRA_MACRO_SERVER_ID_ENV = "CONFLUENCE_JIRA_SERVER_ID"
JIRA_MACRO_COLUMNS = "key,summary,type,created,updated,due,assignee,reporter,priority,status,resolution"
JIRA_MACRO_COLUMN_IDS = "issuekey,summary,issuetype,created,updated,duedate,assignee,reporter,priority,status,resolution"


def fix_version(pi: str) -> str:
    return f"LPDA - PI#{pi}"


def pi_iterations(sprints: list, pi: str) -> list:
    """Picks the PI's iteration sprints out of raw board sprints, sorted by iteration.
    Each sprint is a dict with at least 'id', 'name' and (optionally) 'endDate'."""
    pattern = re.compile(rf"^{re.escape(pi)}-(\d+)$")
    iterations = []
    for sprint in sprints:
        match = pattern.match(sprint["name"].strip())
        if match:
            iterations.append({
                "iteration": int(match.group(1)),
                "sprint_id": sprint["id"],
                "sprint": sprint["name"],
                "end": (sprint.get("endDate") or "")[:10] or None,
            })
    return sorted(iterations, key=lambda i: i["iteration"])


def last_iteration(story_counts: dict):
    """Highest iteration number with at least one story, or None."""
    planned = [iteration for iteration, count in story_counts.items() if count]
    return max(planned) if planned else None


def planned_values(epic_count: int) -> list:
    """Planned Business Value by priority: 10 for the first epic, then 1 less each."""
    if epic_count > TOP_PLANNED_BV:
        raise ValueError(f"{epic_count} epics but only {TOP_PLANNED_BV} distinct values; ask the user")
    return [TOP_PLANNED_BV - i for i in range(epic_count)]


def text_problems(summary: str, description: str, iteration: int) -> list:
    """Checks an objective's text against the house style; returns readable problems."""
    problems = []
    match = re.match(r"^\[(\w+)\] \S", summary or "")
    env = match.group(1) if match else None
    if env not in ENV_TAGS:
        problems.append(f"summary must start with one of {', '.join(f'[{t}]' for t in ENV_TAGS)}")
    if not (description or "").startswith("We will "):
        problems.append("description must start with 'We will '")
    deadline = f"by the end of iteration {iteration} [{env}]"
    if env in ENV_TAGS and deadline not in (description or ""):
        problems.append(f"description must say '{deadline}'")
    return problems


def objective_fields(objective: dict, pi: str, owner: str) -> dict:
    """JIRA create fields for one approved plan entry."""
    return {
        "project": OBJECTIVE_PROJECT,
        "issuetype": {"name": OBJECTIVE_TYPE},
        "summary": objective["summary"],
        "description": objective["description"],
        "components": [{"name": OBJECTIVE_COMPONENT}],
        "reporter": {"name": owner},
        "assignee": {"name": owner},
        "labels": [f"Iteration{objective['iteration']}"],
        "fixVersions": [{"name": fix_version(pi)}],
        PLANNED_BV_FIELD: objective["planned_bv"],
        TARGET_END_FIELD: objective["target_end"],
        COMMITTED_FIELD: {"value": "Committed"},
    }


def business_value(value) -> str:
    """9.0 -> "9", 7.5 -> "7.5", None -> "" (an ABV not given yet)."""
    if value is None:
        return ""
    return str(int(value)) if float(value).is_integer() else str(value)


def _setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is not set in .env")
    return value


def demo_line(key: str, planned_bv, actual_bv=None) -> str:
    """One objective's list item on the System Demos page: Jira Legacy macro + "(PBV: n, ABV: m)"."""
    parameters = {
        "macroParams": {
            "server": {"value": _setting(JIRA_MACRO_SERVER_ENV)},
            "columns": {"value": JIRA_MACRO_COLUMNS},
            "columnIds": {"value": JIRA_MACRO_COLUMN_IDS},
            "serverId": {"value": _setting(JIRA_MACRO_SERVER_ID_ENV)},
            "key": {"value": key},
        },
        "macroMetadata": {"schemaVersion": {"value": "1"}, "title": "Jira Legacy"},
    }
    macro = ('<span data-type="inline-extension" data-extension-key="jira" '
             'data-extension-type="com.atlassian.confluence.macro.core" '
             f'data-parameters="{html.escape(json.dumps(parameters))}"></span>')
    return (f"<li><p>{macro} (PBV: {business_value(planned_bv)}, "
            f"ABV: {business_value(actual_bv)})</p></li>")


def demo_team_item(lines: list) -> str:
    """The TRS team item holding the objective lines, for a demo section without one yet."""
    return f"<li><p>{OBJECTIVE_COMPONENT}</p><ul>{''.join(lines)}</ul></li>"


def _existing_objectives(jira, epic_key: str, pi: str) -> list:
    # Other teams link their own objectives to the same epics, so only TRS ones count
    jql = (f'project = {OBJECTIVE_PROJECT} AND issuetype = "{OBJECTIVE_TYPE}" '
           f'AND component = {OBJECTIVE_COMPONENT} AND fixVersion = "{fix_version(pi)}" '
           f'AND issue in linkedIssues({epic_key})')
    return [i.key for i in jira.search_issues(jql, maxResults=10)]


def plan(pi: str, epic_keys: list) -> dict:
    from jira_client import DEFAULT_BOARD_ID, jira

    sprints = [s.raw for s in jira.sprints(DEFAULT_BOARD_ID, maxResults=False)]
    iterations = pi_iterations(sprints, pi)
    ip_sprint = next((s for s in sprints if s["name"].strip() == f"{pi}-IP"), None)
    values = planned_values(len(epic_keys))
    end_by_iteration = {i["iteration"]: i["end"] for i in iterations}

    epics = []
    for epic_key, planned_bv in zip(epic_keys, values):
        epic = jira.issue(epic_key)
        counts = {i["iteration"]: jira.search_issues(
            f'"Epic Link" = {epic_key} AND sprint = {i["sprint_id"]}', maxResults=0).total
            for i in iterations}
        in_ip = ip_sprint and jira.search_issues(
            f'"Epic Link" = {epic_key} AND sprint = {ip_sprint["id"]}', maxResults=0).total
        iteration = last_iteration(counts)
        epics.append({
            "epic": epic_key,
            "epic_type": epic.fields.issuetype.name,
            "epic_status": epic.fields.status.name,
            "epic_summary": epic.fields.summary,
            "epic_description": epic.fields.description,
            "planned_bv": planned_bv,
            "stories_per_iteration": {f"Iteration{n}": c for n, c in counts.items() if c},
            "stories_in_ip_sprint": in_ip or 0,
            "iteration": iteration,
            "target_end": end_by_iteration.get(iteration),
            "existing_objectives": _existing_objectives(jira, epic_key, pi),
        })

    return {
        "pi": pi,
        "fix_version": fix_version(pi),
        "fix_version_exists": fix_version(pi) in [v.name for v in jira.project_versions(OBJECTIVE_PROJECT)],
        "iterations": iterations,
        "epics": epics,
    }


def create(plan_path: str) -> list:
    """Creates every objective in an approved plan file; skips epics that already have one
    for this PI. Returns one result dict per entry."""
    from jira_client import issue_url, jira

    with open(plan_path, "r", encoding="utf-8") as f:
        approved = json.load(f)
    pi = approved["pi"]
    owner = jira.myself()["name"]  # reporter and assignee: the account of the token in .env

    results = []
    for objective in approved["objectives"]:
        epic_key = objective["epic"]
        try:
            problems = text_problems(objective["summary"], objective["description"], objective["iteration"])
            if problems:
                results.append({"epic": epic_key, "status": "invalid", "problems": problems})
                continue
            existing = _existing_objectives(jira, epic_key, pi)
            if existing:
                results.append({"epic": epic_key, "status": "skipped", "existing": existing})
                continue
            issue = jira.create_issue(fields=objective_fields(objective, pi, owner))
            jira.create_issue_link("Relates", issue.key, epic_key)
            results.append({"epic": epic_key, "status": "created", "key": issue.key,
                            "url": issue_url(issue.key)})
        except Exception as e:
            results.append({"epic": epic_key, "status": "failed", "error": str(e)})
    return results


def reviewing(pi: str) -> dict:
    """TRS objectives of the PI in status Reviewing, with their System Demos page markup."""
    from jira_client import issue_url, search_issues

    jql = (f'project = {OBJECTIVE_PROJECT} AND issuetype = "{OBJECTIVE_TYPE}" '
           f'AND component = {OBJECTIVE_COMPONENT} AND fixVersion = "{fix_version(pi)}" '
           f'AND status = Reviewing ORDER BY key')
    objectives = []
    for issue in search_issues(jql, max_results=50):
        planned_bv = getattr(issue.fields, PLANNED_BV_FIELD)
        objectives.append({
            "key": issue.key,
            "url": issue_url(issue.key),
            "summary": issue.fields.summary,
            "labels": issue.fields.labels,
            "planned_bv": planned_bv,
            "actual_bv": getattr(issue.fields, ACTUAL_BV_FIELD),
            "line_html": demo_line(issue.key, planned_bv),
        })
    return {
        "pi": pi,
        "objectives": objectives,
        "team_item_html": demo_team_item([o["line_html"] for o in objectives]) if objectives else None,
    }


def close(close_path: str) -> list:
    """Sets Actual Business Value and moves each listed objective from Reviewing to Done or
    Partially Done. Returns one result per entry, with its updated System Demos page line."""
    from jira_client import jira, transition_issue

    with open(close_path, "r", encoding="utf-8") as f:
        entries = json.load(f)["objectives"]

    results = []
    for entry in entries:
        key, status, actual_bv = entry["key"], entry["status"], entry["actual_bv"]
        try:
            if status not in CLOSING_STATUSES:
                results.append({"key": key, "status": "invalid",
                                "problems": [f"status must be one of {', '.join(CLOSING_STATUSES)}"]})
                continue
            issue = jira.issue(key)
            if issue.fields.status.name != "Reviewing":
                results.append({"key": key, "status": "skipped", "current_status": issue.fields.status.name})
                continue
            issue.update(fields={ACTUAL_BV_FIELD: actual_bv})
            transition_issue(key, status)
            planned_bv = getattr(issue.fields, PLANNED_BV_FIELD)
            results.append({"key": key, "status": "closed", "new_status": status,
                            "planned_bv": planned_bv, "actual_bv": actual_bv,
                            "line_html": demo_line(key, planned_bv, actual_bv)})
        except Exception as e:
            results.append({"key": key, "status": "failed", "error": str(e)})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    plan_cmd = commands.add_parser("plan")
    plan_cmd.add_argument("--pi", required=True, help="e.g. 27.1")
    plan_cmd.add_argument("epics", nargs="+", help="epic keys in priority order")
    create_cmd = commands.add_parser("create")
    create_cmd.add_argument("plan_file")
    reviewing_cmd = commands.add_parser("reviewing")
    reviewing_cmd.add_argument("--pi", required=True, help="e.g. 26.4")
    close_cmd = commands.add_parser("close")
    close_cmd.add_argument("close_file")
    args = parser.parse_args()

    if args.command == "plan":
        output = plan(args.pi, [k.upper() for k in args.epics])
    elif args.command == "create":
        output = create(args.plan_file)
    elif args.command == "reviewing":
        output = reviewing(args.pi)
    else:
        output = close(args.close_file)
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    print()
