"""Fetch the exact public issue sources used by the locked corpus for human review."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

ISSUE_NUMBERS = (87, 90, 93, 102, 112, 199, 209, 212, 213, 223, 224, 231, 233, 234, 238)
API_ROOT = "https://api.github.com/repos/EvoAgentX/EvoAgentX/issues"


def fetch_issue(number: int) -> dict[str, object]:
    request = Request(f"{API_ROOT}/{number}", headers={"Accept": "application/vnd.github+json"})
    with urlopen(request, timeout=30) as response:  # nosec B310: fixed GitHub HTTPS endpoint
        issue = json.load(response)
    if issue.get("state") != "closed" or issue.get("pull_request"):
        raise ValueError(f"issue {number} is not a closed non-PR issue")
    if issue.get("html_url") != f"https://github.com/EvoAgentX/EvoAgentX/issues/{number}":
        raise ValueError(f"issue {number} has an unexpected URL")
    return {
        "number": issue["number"],
        "title": issue["title"],
        "url": issue["html_url"],
        "state": issue["state"],
        "closed_at": issue["closed_at"],
        "body": issue["body"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = {
        "repository": "EvoAgentX/EvoAgentX",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "issues": [fetch_issue(number) for number in ISSUE_NUMBERS],
    }
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    args.output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
