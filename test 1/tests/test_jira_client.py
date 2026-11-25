from unittest.mock import patch

from jira_client import issue_url


def test_issue_url_appends_browse_to_the_jira_url_as_is():
    with patch("jira_client.JIRA_URL", "https://jira.example.com/agile"):
        assert issue_url("TRSC-1") == "https://jira.example.com/agile/browse/TRSC-1"
