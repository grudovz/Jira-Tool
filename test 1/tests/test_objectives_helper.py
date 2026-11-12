import html
import json
import re
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from objectives_helper import (
    business_value, close, create, demo_line, demo_team_item, fix_version, last_iteration, objective_fields,
    pi_iterations, planned_values, text_problems,
)


@pytest.fixture(autouse=True)
def macro_server(monkeypatch):
    monkeypatch.setenv("CONFLUENCE_JIRA_SERVER", "Test JIRA")
    monkeypatch.setenv("CONFLUENCE_JIRA_SERVER_ID", "server-id-1")


def test_fix_version():
    assert fix_version("27.1") == "LPDA - PI#27.1"


def test_pi_iterations_keeps_only_numbered_sprints_of_that_pi():
    sprints = [
        {"id": 3, "name": "26.4-2", "endDate": "2026-11-06T11:25:00.000Z"},
        {"id": 1, "name": "26.4-1", "endDate": "2026-10-23T09:00:00.000Z"},
        {"id": 5, "name": "26.4-IP", "endDate": "2026-12-18T11:25:00.000Z"},
        {"id": 7, "name": "26.3-1TRS", "endDate": "2026-07-17T09:00:00.000Z"},
        {"id": 8, "name": "26.40-1"},
        {"id": 9, "name": "Low prio"},
    ]
    assert pi_iterations(sprints, "26.4") == [
        {"iteration": 1, "sprint_id": 1, "sprint": "26.4-1", "end": "2026-10-23"},
        {"iteration": 2, "sprint_id": 3, "sprint": "26.4-2", "end": "2026-11-06"},
    ]


def test_pi_iterations_without_end_date():
    assert pi_iterations([{"id": 1, "name": "27.1-1"}], "27.1")[0]["end"] is None


def test_last_iteration_ignores_empty_sprints():
    assert last_iteration({1: 3, 2: 0, 3: 1, 4: 0}) == 3


def test_last_iteration_with_no_stories():
    assert last_iteration({1: 0, 2: 0}) is None


def test_planned_values_count_down_from_ten():
    assert planned_values(3) == [10, 9, 8]


def test_planned_values_rejects_more_than_ten_epics():
    with pytest.raises(ValueError):
        planned_values(11)


def test_text_problems_accepts_house_style():
    summary = "[PRD] Migrate to NLT Hotel Only"
    description = ("We will fully support the use of NLT to fetch Hotel Only offer data, enabling the move "
                   "away from our current CWS integration, by the end of iteration 2 [PRD]")
    assert text_problems(summary, description, 2) == []


def test_text_problems_allows_a_scope_note_after_the_deadline():
    description = ("We will integrate Trip Guarantee into ALP IL, by the end of iteration 4 [PRD]. "
                   "The docket option will be delivered separately.")
    assert text_problems("[PRD] Integrate Trip Guarantee", description, 4) == []


@pytest.mark.parametrize("summary, description, expected", [
    ("Migrate to NLT", "We will migrate, by the end of iteration 2 [PRD]", "summary must start"),
    ("[PRD] Migrate", "Migrate it, by the end of iteration 2 [PRD]", "must start with 'We will '"),
    ("[PRD] Migrate", "We will migrate, by the end of iteration 3 [PRD]", "iteration 2 [PRD]"),
    ("[UAT] Migrate", "We will migrate, by the end of iteration 2 [PRD]", "iteration 2 [UAT]"),
])
def test_text_problems_flags_style_breaks(summary, description, expected):
    problems = text_problems(summary, description, 2)
    assert len(problems) == 1 and expected in problems[0]


def test_objective_fields():
    objective = {"epic": "LPDA-1", "summary": "[PRD] X", "description": "We will X, by the end of iteration 4 [PRD]",
                 "iteration": 4, "target_end": "2026-12-04", "planned_bv": 7}
    fields = objective_fields(objective, "26.4", "jdoe")
    assert fields["issuetype"] == {"name": "PI Objective"}
    assert fields["reporter"] == fields["assignee"] == {"name": "jdoe"}
    assert fields["components"] == [{"name": "TRS"}]
    assert fields["labels"] == ["Iteration4"]
    assert fields["fixVersions"] == [{"name": "LPDA - PI#26.4"}]
    assert fields["customfield_16200"] == 7
    assert fields["customfield_12808"] == "2026-12-04"
    assert fields["customfield_17500"] == {"value": "Committed"}


def _plan_file(tmp_path, *objectives):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"pi": "27.1", "objectives": list(objectives)}), encoding="utf-8")
    return str(path)


GOOD = {"epic": "LPDA-1", "summary": "[PRD] Do X", "description": "We will do X, by the end of iteration 2 [PRD]",
        "iteration": 2, "target_end": "2027-01-15", "planned_bv": 10}


def test_create_makes_the_objective_and_links_the_epic(tmp_path):
    with patch("jira_client.jira") as jira:
        jira.search_issues.return_value = []
        jira.myself.return_value = {"name": "jdoe"}
        jira.create_issue.return_value.key = "LPDA-900"
        results = create(_plan_file(tmp_path, GOOD))
    assert results[0]["status"] == "created" and results[0]["key"] == "LPDA-900"
    assert jira.create_issue.call_args.kwargs["fields"]["reporter"] == {"name": "jdoe"}
    assert jira.create_issue.call_args.kwargs["fields"]["fixVersions"] == [{"name": "LPDA - PI#27.1"}]
    jira.create_issue_link.assert_called_once_with("Relates", "LPDA-900", "LPDA-1")


def test_create_skips_an_epic_that_already_has_a_trs_objective(tmp_path):
    with patch("jira_client.jira") as jira:
        jira.search_issues.return_value = [type("Issue", (), {"key": "LPDA-800"})()]
        results = create(_plan_file(tmp_path, GOOD))
    assert results == [{"epic": "LPDA-1", "status": "skipped", "existing": ["LPDA-800"]}]
    assert "component = TRS" in jira.search_issues.call_args.args[0]
    jira.create_issue.assert_not_called()


def test_create_refuses_text_that_breaks_house_style(tmp_path):
    bad = dict(GOOD, description="We will do X, by the end of iteration 3 [PRD]")
    with patch("jira_client.jira") as jira:
        results = create(_plan_file(tmp_path, bad))
    assert results[0]["status"] == "invalid"
    jira.create_issue.assert_not_called()


def test_create_carries_on_after_a_failure(tmp_path):
    second = dict(GOOD, epic="LPDA-2")
    with patch("jira_client.jira") as jira:
        jira.search_issues.return_value = []
        jira.create_issue.side_effect = [Exception("400 Bad Request"), type("Issue", (), {"key": "LPDA-901"})()]
        results = create(_plan_file(tmp_path, GOOD, second))
    assert [r["status"] for r in results] == ["failed", "created"]


@pytest.mark.parametrize("value, expected", [(9.0, "9"), (9, "9"), (7.5, "7.5"), (None, "")])
def test_business_value(value, expected):
    assert business_value(value) == expected


def test_demo_line_matches_the_page_format():
    line = demo_line("LPDA-3307", 9.0)
    assert line.startswith("<li><p><span data-type=\"inline-extension\" data-extension-key=\"jira\"")
    assert line.endswith("</span> (PBV: 9, ABV: )</p></li>")
    parameters = json.loads(html.unescape(re.search(r'data-parameters="([^"]*)"', line).group(1)))
    assert parameters["macroParams"]["key"] == {"value": "LPDA-3307"}
    assert parameters["macroParams"]["server"] == {"value": "Test JIRA"}
    assert parameters["macroParams"]["serverId"] == {"value": "server-id-1"}
    assert "macroId" not in parameters["macroMetadata"]


def test_demo_line_with_actual_value():
    assert demo_line("LPDA-3307", 9.0, 7).endswith("(PBV: 9, ABV: 7)</p></li>")


def test_demo_team_item_wraps_lines_under_trs():
    assert demo_team_item(["<li>a</li>", "<li>b</li>"]) == "<li><p>TRS</p><ul><li>a</li><li>b</li></ul></li>"


def _close_file(tmp_path, *entries):
    path = tmp_path / "close.json"
    path.write_text(json.dumps({"objectives": list(entries)}), encoding="utf-8")
    return str(path)


def _objective(status, planned_bv=9.0):
    return SimpleNamespace(fields=SimpleNamespace(status=SimpleNamespace(name=status), customfield_16200=planned_bv))


def test_close_sets_actual_value_then_transitions(tmp_path):
    issue = _objective("Reviewing")
    issue.update = lambda fields: calls.append(("update", fields))
    calls = []
    with patch("jira_client.jira") as jira, patch("jira_client.transition_issue") as transition:
        jira.issue.return_value = issue
        transition.side_effect = lambda key, name: calls.append(("transition", key, name))
        results = close(_close_file(tmp_path, {"key": "LPDA-3307", "status": "Partially Done", "actual_bv": 6}))
    assert calls == [("update", {"customfield_16302": 6}), ("transition", "LPDA-3307", "Partially Done")]
    assert results[0]["status"] == "closed"
    assert results[0]["line_html"].endswith("(PBV: 9, ABV: 6)</p></li>")


def test_close_skips_objectives_not_in_reviewing(tmp_path):
    with patch("jira_client.jira") as jira, patch("jira_client.transition_issue") as transition:
        jira.issue.return_value = _objective("Implementing")
        results = close(_close_file(tmp_path, {"key": "LPDA-3307", "status": "Done", "actual_bv": 9}))
    assert results == [{"key": "LPDA-3307", "status": "skipped", "current_status": "Implementing"}]
    transition.assert_not_called()


def test_close_refuses_other_statuses(tmp_path):
    with patch("jira_client.jira") as jira:
        results = close(_close_file(tmp_path, {"key": "LPDA-3307", "status": "Abandoned", "actual_bv": 0}))
    assert results[0]["status"] == "invalid"
    jira.issue.assert_not_called()


def test_demo_line_needs_the_macro_server_in_env(monkeypatch):
    monkeypatch.delenv("CONFLUENCE_JIRA_SERVER_ID")
    with pytest.raises(ValueError, match="CONFLUENCE_JIRA_SERVER_ID"):
        demo_line("LPDA-3307", 9.0)
