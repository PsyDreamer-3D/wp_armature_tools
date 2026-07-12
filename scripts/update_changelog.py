#!/usr/bin/env python3
"""Date/rename the Unreleased section of CHANGELOG.md at release time, or
extract a dated section's body for use as release notes.

Usage:
    python3 scripts/update_changelog.py release <version> [--date YYYY-MM-DD]
    python3 scripts/update_changelog.py extract <version>

<version> is a bare semantic-version string, e.g. "1.2.3" (a leading "v" is
accepted and stripped automatically).

release
-------
Renames the "## [Unreleased]" heading to "## [<version>] — <date>" (date
defaults to today) and inserts a fresh, empty "## [Unreleased]" above it, so
the next round of development has somewhere to log entries. Refuses to run
if the Unreleased section has no content (nothing to release) or if a
section for <version> already exists (duplicate release).

extract
-------
Prints the body of an existing "## [<version>]" section to stdout, e.g. for
use as a GitHub Release body:

    python3 scripts/update_changelog.py extract 1.2.3 > release-notes.md
"""

import argparse
import datetime
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG_PATH = os.path.join(REPO_ROOT, "CHANGELOG.md")

UNRELEASED_RE = re.compile(
    r'^## \[Unreleased\][^\n]*\n(.*?)(?=^## \[|\Z)',
    re.MULTILINE | re.DOTALL,
)


def section_re(version: str) -> re.Pattern:
    return re.compile(
        rf'^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)',
        re.MULTILINE | re.DOTALL,
    )


def read_changelog() -> str:
    if not os.path.isfile(CHANGELOG_PATH):
        raise SystemExit(f"Error: {CHANGELOG_PATH} not found.")
    with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
        return f.read()


def write_changelog(content: str) -> None:
    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def has_content(body: str) -> bool:
    return any(line.strip() for line in body.splitlines())


def cmd_release(version: str, date: str) -> None:
    content = read_changelog()

    match = UNRELEASED_RE.search(content)
    if not match:
        raise SystemExit("Error: no '## [Unreleased]' section found in CHANGELOG.md")

    body = match.group(1)
    if not has_content(body):
        raise SystemExit(
            "Error: '## [Unreleased]' section is empty — nothing to release. "
            "Add changelog entries before cutting a release."
        )

    if section_re(version).search(content):
        raise SystemExit(f"Error: a '## [{version}]' section already exists in CHANGELOG.md")

    replacement = f"## [Unreleased]\n\n## [{version}] — {date}\n{body}"
    updated = content[: match.start()] + replacement + content[match.end() :]

    write_changelog(updated)
    print(f"CHANGELOG.md -> dated '## [{version}] — {date}', reset Unreleased")


def cmd_extract(version: str) -> None:
    content = read_changelog()

    match = section_re(version).search(content)
    if not match:
        raise SystemExit(f"Error: no '## [{version}]' section found in CHANGELOG.md")

    body = match.group(1).strip("\n")
    if not has_content(body):
        raise SystemExit(f"Error: '## [{version}]' section is empty")

    print(body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    release_parser = sub.add_parser("release", help="Date and rename the Unreleased section")
    release_parser.add_argument("version", help='Bare semver, e.g. "1.2.3"')
    release_parser.add_argument(
        "--date",
        default=datetime.date.today().isoformat(),
        help="Release date, YYYY-MM-DD (default: today)",
    )

    extract_parser = sub.add_parser("extract", help="Print a dated section's body")
    extract_parser.add_argument("version", help='Bare semver, e.g. "1.2.3"')

    args = parser.parse_args()
    version = args.version.lstrip("v").strip()

    if args.command == "release":
        cmd_release(version, args.date)
    elif args.command == "extract":
        cmd_extract(version)


if __name__ == "__main__":
    main()
