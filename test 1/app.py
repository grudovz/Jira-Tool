"""
Streamlit UI for the JIRA Story Tool.
All JIRA API calls go via jira_client.
This file contains no business logic.
"""
import streamlit as st
from story_parser import parse_issue
from jira_client import create_issue, update_issue

st.set_page_config(page_title="JIRA Story Tool", layout="wide")
st.title("JIRA Story Tool")

# --- Session state ---
if "parsed" not in st.session_state:
    st.session_state.parsed = {}
if "last_created" not in st.session_state:
    st.session_state.last_created = None

# --- Layout ---
left, right = st.columns([1, 1])

with left:
    st.subheader("Paste Story Text")
    raw_text = st.text_area(
        label="raw_text",
        height=300,
        placeholder="Paste story text here — title, description, acceptance criteria...",
        label_visibility="collapsed",
    )
    if st.button("Parse"):
        if raw_text.strip():
            st.session_state.parsed = parse_issue(raw_text)
        else:
            st.warning("Paste some text first.")

with right:
    st.subheader("Story Fields")
    p = st.session_state.parsed

    title = st.text_input("Title *", value=p.get("title") or "")
    description = st.text_area("Description", value=p.get("description") or "", height=120)

    col_sp, col_comp = st.columns([1, 2])
    with col_sp:
        story_points = st.number_input(
            "Story Points", min_value=0, max_value=100,
            value=int(p.get("story_points") or 0), step=1,
        )
    with col_comp:
        component = st.text_input(
            "Component",
            value=", ".join(p.get("components") or []),
        )

    st.divider()

    # --- Actions ---
    col_create, col_update = st.columns(2)

    with col_create:
        if st.button("Create"):
            if not title.strip():
                st.error("Title is required.")
            else:
                try:
                    issue = create_issue(
                        summary=title,
                        description=description,
                    )
                    st.session_state.last_created = issue.key
                    st.success(f"Created {issue.key}")
                except Exception as e:
                    st.error(str(e))

    with col_update:
        issue_key = st.text_input("Issue key", placeholder="PROJ-123")
        if st.button("Update"):
            if not issue_key.strip():
                st.error("Enter an issue key.")
            elif not title.strip():
                st.error("Title is required.")
            else:
                try:
                    update_issue(issue_key.strip(), summary=title, description=description)
                    st.success(f"Updated {issue_key}")
                except Exception as e:
                    st.error(str(e))
