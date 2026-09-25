"""
Thin helper for /fetch and /fetchbacklog: download an issue's attachments to a
local cache folder so they can be registered as clickable links, instead of
inlining the download loop as a fresh script in every skill invocation.

No new JIRA client code needed — reuses the same authenticated `jira`
instance jira_client.py already exports, via Attachment.get().
"""
import os

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attachment_cache")


def cache_attachments(issue):
    """
    Download every attachment on `issue` to attachment_cache/<KEY>/<filename>,
    skipping any file already cached locally from a previous run.

    Returns a list of {"filename": ..., "path": <absolute path>} dicts, in
    the same order as issue.fields.attachment. Empty list if there are none.
    """
    attachments = getattr(issue.fields, "attachment", None)
    if not attachments:
        return []

    issue_dir = os.path.join(CACHE_DIR, issue.key)
    os.makedirs(issue_dir, exist_ok=True)

    cached = []
    for att in attachments:
        path = os.path.join(issue_dir, att.filename)
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(att.get())
        cached.append({"filename": att.filename, "path": os.path.abspath(path)})
    return cached
