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


def get_issue(issue_key: str):
    """Fetch a single issue by key, e.g. 'PROJ-123'."""
    return jira.issue(issue_key)


def search_issues(jql: str, max_results: int = 50):
    """Run a JQL query and return matching issues.
    Example JQL: 'project = MYPROJ AND status = "In Progress" AND assignee = currentUser()'
    """
    return jira.search_issues(jql, maxResults=max_results)


def update_issue(issue_key: str, **fields):
    """Update fields on an issue.
    Example: update_issue('PROJ-123', summary='New title', description='New description')
    """
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
    attachments: "list | None" = None,
):
    """Create a new issue in the default project.
    issue_type: 'Story', 'Bug', 'Task', 'Sub-task', etc.
    Pass epic_link=None or component=None to omit those fields.
    attachments: optional list of attachments added after creation. Each item is either:
      - a file path string, e.g. 'C:/tmp/screenshot.png'
      - a dict with keys 'file' (bytes/BytesIO) and 'filename' (str),
        e.g. {"file": image_bytes, "filename": "screenshot.png"}
    """
    fields = {
        "project": project,
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
    }
    if epic_link:
        fields["customfield_10006"] = epic_link
    if component:
        fields["components"] = [{"name": component}]
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
