#!/usr/bin/env bash
# prepare_release.sh — Date the CHANGELOG.md Unreleased section, bump the
# add-on version, and commit the result as "Release vX.Y.Z".
#
# This is a local, human-run script: it commits but never pushes or tags.
# Review the commit (`git show HEAD`), then push to main — either directly
# or via a rebase-merged PR. (Squash-merging rewrites the commit message to
# the PR title, which must then read exactly "Release vX.Y.Z" for the
# push-triggered auto-tag workflow to fire — see ../AGENTS.md section 5.)
#
# Usage:
#   ./scripts/prepare_release.sh <version> [--branch <branch>]
#
# <version> must be a semantic-version string, e.g. "1.2.3". A leading "v"
# is accepted and stripped automatically. --branch defaults to "main".
set -euo pipefail

trap 'echo "Error: prepare_release.sh failed on line $LINENO." >&2' ERR

# ─── Args ──────────────────────────────────────────────────────────────────
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <version> [--branch <branch>]" >&2
  exit 1
fi

version="${1#v}"
shift

branch="main"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch) branch="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if ! [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: version must be in MAJOR.MINOR.PATCH format, got '$version'" >&2
  exit 1
fi

tag="v${version}"
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

# ─── Preconditions ─────────────────────────────────────────────────────────
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Error: working tree is not clean. Commit or stash pending changes first." >&2
  exit 1
fi

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "$branch" ]]; then
  echo "Error: currently on '$current_branch', expected '$branch' (use --branch to override)." >&2
  exit 1
fi

if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
  echo "Error: tag '$tag' already exists locally." >&2
  exit 1
fi

if git remote get-url origin &>/dev/null; then
  if git ls-remote --exit-code --tags origin "$tag" &>/dev/null; then
    echo "Error: tag '$tag' already exists on remote 'origin'." >&2
    exit 1
  fi
fi

# ─── Update CHANGELOG.md and version files ─────────────────────────────────
python3 scripts/update_changelog.py release "$version"

# Unlike release.yml's CI invocation (throwaway, runner-only) and
# build_dev.sh's (local, detached-HEAD, never committed), this bump IS
# committed below — it's the one place bump_version.py's output lands on
# main.
python3 scripts/bump_version.py "$version"

# ─── Commit ──────────────────────────────────────────────────────────────────
# One add-on per repo: the package dir is whichever top-level folder
# contains blender_manifest.toml (see ../AGENTS.md section 2).
package_dir="$(dirname "$(find . -maxdepth 2 -name blender_manifest.toml -print -quit)")"
package_dir="${package_dir#./}"

git add CHANGELOG.md "$package_dir/blender_manifest.toml"
[[ -f "$package_dir/__init__.py" ]] && git add "$package_dir/__init__.py"

# The exact message matters: .github/workflows/auto-tag-release.yml
# pattern-matches on it to decide whether to tag and release.
git commit -m "Release v${version}"

cat <<EOF

Prepared release v${version}. Review it, then:

  git show HEAD
  git push origin ${branch}

Pushing will trigger .github/workflows/auto-tag-release.yml, which creates
and pushes the '${tag}' tag and runs the build/publish pipeline automatically.
If you'd rather do it manually instead:

  git tag ${tag}
  git push origin ${tag}
EOF
