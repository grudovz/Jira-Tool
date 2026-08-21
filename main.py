from jira_client import get_issue, update_issue, create_issue, attach_file, JIRA_URL

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
    # --- Test 1: create a new issue ---
   #  issue = create_issue("Test story - created via API")
   #  print(f"Success! View it at: {JIRA_URL}/browse/{issue.key}")

    # --- Test 2: attach a file by path ---
    # Replace with any real file on your machine before running.
    attach_file("TRSC-2898", r"C:\Users\zgrudov\Downloads\Designer.jpg")

    # --- Test 3: attach raw bytes (simulates a clipboard paste) ---
    # In the future Streamlit UI, st.camera_input / st.file_uploader will supply
    # a BytesIO object that can be passed directly here.
    #
    # import io
    # with open(r"C:\Users\zgrudov\Pictures\screenshot.png", "rb") as f:
    #     image_bytes = io.BytesIO(f.read())
    # attach_file(issue.key, image_bytes, filename="pasted_screenshot.png")

