"""Creates labels, milestones and issues from github_plan.json using the GitHub CLI.

Usage (inside the repo, after `gh repo create ... --source=. --push`):
    python scripts/bootstrap_github.py            # create everything
    python scripts/bootstrap_github.py --dry-run  # just print what would happen

Safe to re-run: existing milestones and issues (matched by title) are skipped.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

PLAN = Path(__file__).with_name("github_plan.json")


def gh(*args: str, dry: bool = False) -> str:
    if dry:
        print("  [dry-run] gh", " ".join(args))
        return ""
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run

    if not dry and shutil.which("gh") is None:
        sys.exit("GitHub CLI (gh) not found. Install it from https://cli.github.com, "
                 "then run `gh auth login`.")

    plan = json.loads(PLAN.read_text(encoding="utf-8"))

    print("Labels")
    for label in plan["labels"]:
        gh("label", "create", label["name"], "--color", label["color"],
           "--description", label["description"], "--force", dry=dry)
        print(f"  ✓ {label['name']}")

    print("Milestones")
    existing_ms = set()
    if not dry:
        out = gh("api", "repos/{owner}/{repo}/milestones?state=all&per_page=100")
        existing_ms = {m["title"] for m in json.loads(out)}
    for ms in plan["milestones"]:
        if ms["title"] in existing_ms:
            print(f"  = {ms['title']} (exists)")
            continue
        gh("api", "repos/{owner}/{repo}/milestones", "-f", f"title={ms['title']}",
           "-f", f"description={ms['description']}", dry=dry)
        print(f"  ✓ {ms['title']}")

    print("Issues")
    existing_issues = set()
    if not dry:
        out = gh("issue", "list", "--state", "all", "--limit", "500", "--json", "title")
        existing_issues = {i["title"] for i in json.loads(out)}
    for issue in plan["issues"]:
        if issue["title"] in existing_issues:
            print(f"  = {issue['title']} (exists)")
            continue
        cmd = ["issue", "create", "--title", issue["title"], "--body", issue["body"],
               "--milestone", issue["milestone"]]
        for label in issue["labels"]:
            cmd += ["--label", label]
        gh(*cmd, dry=dry)
        print(f"  ✓ {issue['title']}")

    print("Done.")


if __name__ == "__main__":
    main()
