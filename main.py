import pyautogui
import keyboard
import time
from jira_client import get_issue, update_issue, create_issue, JIRA_URL

# --- Macros go here ---


def update_description_interactive():
    issue_key = input("Issue key (e.g. PROJ-123): ").strip()

    issue = get_issue(issue_key)
    print(f"\nSummary: {issue.fields.summary}")
    print(f"\nCurrent description:\n{issue.fields.description}\n")

    print("Enter new description (press Enter twice when done):")
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    new_description = "\n".join(lines).strip()

    confirm = input(f"\nUpdate description on {issue_key}? (y/n): ").strip().lower()
    if confirm == "y":
        update_issue(issue_key, description=new_description)
    else:
        print("Cancelled.")


if __name__ == "__main__":
    issue = create_issue("Test story - created via API")
    print(f"Success! View it at: {JIRA_URL}/browse/{issue.key}")

