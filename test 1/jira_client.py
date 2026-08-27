import os
from typing import Optional
from dotenv import load_dotenv
from jira import JIRA

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


def get_jira_client() -> JIRA:
    """Return an authenticated JIRA client using a Personal Access Token (Bearer auth)."""
    if not JIRA_URL:
        raise ValueError("JIRA_URL is not set in .env")
    if not JIRA_API_TOKEN:
        raise ValueError("JIRA_API_TOKEN is not set in .env")
    return JIRA(
        server=JIRA_URL,
        token_auth=JIRA_API_TOKEN,
        get_server_info=False,
        max_retries=1,
    )


# --- Reusable client instance ---
jira = get_jira_client()

# --- Defaults for new issues ---
DEFAULT_PROJECT = "TRSC"
DEFAULT_EPIC_LINK = "LPDA-3064"
DEFAULT_COMPONENT = "Service center"
STORY_POINTS_FIELD = "customfield_10002"  # "Estimate" in the JIRA UI
DEFAULT_BOARD_ID = 19034  # "TravelScript - Sprint" board, used to resolve sprint names


def get_issue(issue_key: str):
    """Fetch a single issue by key, e.g. 'PROJ-123'."""
    return jira.issue(issue_key)


def search_issues(jql: str, max_results: int = 50):
    """Run a JQL query and return matching issues.
    Example JQL: 'project = MYPROJ AND status = "In Progress" AND assignee = currentUser()'
    """
    return jira.search_issues(jql, maxResults=max_results)


def update_issue(issue_key: str, story_points: "int | float | None" = None, **fields):
    """Update fields on an issue.
    Example: update_issue('PROJ-123', summary='New title', description='New description')
    story_points sets the "Estimate" field shown in the JIRA UI.
    """
    if story_points is not None:
        fields[STORY_POINTS_FIELD] = story_points
    issue = jira.issue(issue_key)
    issue.update(**fields)
    print(f"Updated {issue_key}")


def transition_issue(issue_key: str, transition_name: str):
    """Move an issue to a new status by transition name, e.g. 'In Progress', 'Done'."""
    issue = jira.issue(issue_key)
    transitions = jira.transitions(issue)
    match = next((t for t in transitions if t["name"].lower() == transition_name.lower()), None)
    if not match:
        available = [t["name"] for t in transitions]
        raise ValueError(f"Transition '{transition_name}' not found. Available: {available}")
    jira.transition_issue(issue, match["id"])
    print(f"Transitioned {issue_key} to '{transition_name}'")


def add_comment(issue_key: str, comment: str):
    """Add a comment to an issue."""
    jira.add_comment(issue_key, comment)
    print(f"Comment added to {issue_key}")


def assign_issue(issue_key: str, username: str):
    """Assign an issue to a user by their username/accountId."""
    jira.assign_issue(issue_key, username)
    print(f"Assigned {issue_key} to {username}")


def delete_issue(issue_key: str):
    """Permanently delete an issue. This cannot be undone."""
    issue = jira.issue(issue_key)
    issue.delete()
    print(f"Deleted {issue_key}")


def set_sprint(issue_keys: "str | list[str]", sprint_name: str, board_id: int = DEFAULT_BOARD_ID):
    """Move one or more issues into a sprint, by sprint name (e.g. '26.4').
    Looks up the sprint's id on board_id (defaults to DEFAULT_BOARD_ID) since
    JIRA's API takes a sprint id rather than a name.
    """
    if isinstance(issue_keys, str):
        issue_keys = [issue_keys]
    # Only future/active sprints are considered: sprints() defaults to the oldest
    # 50 sprints on the board, which would miss a currently-relevant sprint like "26.4"
    # buried behind years of closed sprints.
    sprints = jira.sprints(board_id, state="future,active")
    match = next((s for s in sprints if s.name == sprint_name), None)
    if not match:
        raise ValueError(f"Sprint '{sprint_name}' not found on board {board_id}. Available: {[s.name for s in sprints]}")
    jira.add_issues_to_sprint(match.id, issue_keys)
    print(f"Moved {', '.join(issue_keys)} to sprint '{sprint_name}'")


def move_to_bottom_of_backlog(issue_keys: "str | list[str]", project: str = DEFAULT_PROJECT):
    """Move one or more issues to the backlog (out of any sprint) and rank them
    last, after whatever issue currently sits at the bottom of the backlog.
    Order among issue_keys is preserved (the last key ends up at the very bottom).
    """
    if isinstance(issue_keys, str):
        issue_keys = [issue_keys]
    jira.move_to_backlog(issue_keys)
    jql = f"project = {project} AND sprint is EMPTY AND statusCategory != Done ORDER BY Rank ASC"
    backlog = [i.key for i in search_issues(jql, max_results=2000) if i.key not in issue_keys]
    if not backlog:
        raise ValueError(f"No other backlog issues found in project '{project}' to rank against")
    prev_issue = backlog[-1]
    for key in issue_keys:
        jira.rank(key, prev_issue=prev_issue)
        prev_issue = key
    print(f"Moved {', '.join(issue_keys)} to the bottom of the backlog")


def get_my_open_issues(project: Optional[str] = None):
    """Return all open issues assigned to the current user, optionally filtered by project."""
    jql = "assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC"
    if project:
        jql = f"project = {project} AND {jql}"
    return search_issues(jql)


def attach_file(issue_key: str, attachment, filename: "str | None" = None):
    """Attach a file to an existing issue.

    attachment can be:
      - A file path string, e.g. attach_file('PROJ-123', 'C:/tmp/screenshot.png')
      - A bytes or BytesIO object (e.g. from a clipboard paste), e.g.
        attach_file('PROJ-123', image_bytes, filename='screenshot.png')

    filename is required when attachment is bytes/BytesIO; ignored for file paths.
    """
    import io
    if isinstance(attachment, (bytes, bytearray)):
        attachment = io.BytesIO(attachment)
    if isinstance(attachment, io.IOBase):
        if not filename:
            raise ValueError("filename is required when attaching bytes or a file-like object")
        jira.add_attachment(issue=issue_key, attachment=attachment, filename=filename)
    else:
        # File path string — let the library derive the filename
        jira.add_attachment(issue=issue_key, attachment=str(attachment))
    print(f"Attachment added to {issue_key}")


def create_issue(
    summary: str,
    description: str = "",
    issue_type: str = "Story",
    project: str = DEFAULT_PROJECT,
    epic_link: str = DEFAULT_EPIC_LINK,
    component: str = DEFAULT_COMPONENT,
    story_points: "int | float | None" = None,
    attachments: "list | None" = None,
):
    """Create a new issue in the default project.
    issue_type: 'Story', 'Bug', 'Task', 'Sub-task', etc. Matched case-insensitively
    against the project's actual issue types (JIRA requires the exact casing).
    Pass epic_link=None or component=None to omit those fields.
    story_points sets the "Estimate" field shown in the JIRA UI.
    attachments: optional list of attachments added after creation. Each item is either:
      - a file path string, e.g. 'C:/tmp/screenshot.png'
      - a dict with keys 'file' (bytes/BytesIO) and 'filename' (str),
        e.g. {"file": image_bytes, "filename": "screenshot.png"}
    """
    available_types = jira.project(project).issueTypes
    matched_type = next((t.name for t in available_types if t.name.lower() == issue_type.lower()), None)
    if not matched_type:
        available = [t.name for t in available_types]
        raise ValueError(f"Issue type '{issue_type}' not found in project '{project}'. Available: {available}")

    fields = {
        "project": project,
        "summary": summary,
        "description": description,
        "issuetype": {"name": matched_type},
    }
    if epic_link:
        fields["customfield_10006"] = epic_link
    if component:
        fields["components"] = [{"name": component}]
    if story_points is not None:
        fields[STORY_POINTS_FIELD] = story_points
    new_issue = jira.create_issue(fields=fields)
    print(f"Created {new_issue.key}: {summary}")
    if attachments:
        for item in attachments:
            if isinstance(item, dict):
                attach_file(new_issue.key, item["file"], filename=item["filename"])
            else:
                attach_file(new_issue.key, item)
    return new_issue


if __name__ == "__main__":
    try:
        myself = jira.myself()
        print(f"Connected as: {myself['displayName']} ({myself['emailAddress']})")
    except Exception as e:
        print(f"Connection failed: {e}")
        print(
            "Ensure you are on the Amadeus VPN and that JIRA_URL in .env "
            "matches the exact URL shown in your browser (including any sub-path)."
        )
