#!/usr/bin/env bash
# Read local Git objects only. Never executes depot_tools or fetches anything.
# Candidate date is a starting point, NOT a proven compatible release.
set -euo pipefail
repo=${1:-}
if [[ $# -ne 1 || ! -d "$repo" ]]; then
  printf 'Usage: bash %s EXISTING_DEPOT_TOOLS_DIRECTORY\n' "$0" >&2
  exit 2
fi
for tool in git timeout readlink; do
  command -v "$tool" >/dev/null || { printf '%s missing; stopping\n' "$tool" >&2; exit 2; }
done
repo=$(readlink -f -- "$repo")
export GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 GIT_TERMINAL_PROMPT=0 LC_ALL=C
# Avoid inherited overrides pointing to an unrelated repository/index.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES
flags=(-c core.fsmonitor=false -c core.hooksPath=/dev/null -c gc.auto=0 -c maintenance.auto=false)
remotes=$(timeout 15s git -C "$repo" remote) || { printf 'Cannot inspect remotes; no object probes attempted\n' >&2; exit 1; }
while IFS= read -r remote; do
  [[ -z "$remote" ]] || flags+=(-c "remote.$remote.promisor=false")
done <<< "$remotes"
g() { timeout 90s git --no-optional-locks --no-replace-objects "${flags[@]}" -C "$repo" "$@"; }
root=$(g rev-parse --show-toplevel)
if [[ $(readlink -f -- "$root") != "$repo" ]]; then printf 'Not a separate depot_tools checkout; stopping\n' >&2; exit 1; fi
printf 'Existing depot_tools: %s\n' "$repo"
printf 'Current full HEAD: '; g rev-parse --verify HEAD
printf 'Shallow repository: '; g rev-parse --is-shallow-repository
printf '\nSearching local first-parent history before 2018-12-14 UTC (no fetch)...\n'
if ! candidate=$(g rev-list --max-count=1 --first-parent --before=2018-12-14T00:00:00Z HEAD); then
  printf 'Historical lookup incomplete (error/timeout); do not infer absence\n' >&2
  exit 1
fi
if [[ -z "$candidate" ]]; then
  printf 'No candidate found in accessible local first-parent history. No download attempted.\n'
  exit 3
fi
printf 'Candidate SHA (compatibility NOT validated): %s\n' "$candidate"
printf '\nCandidate commit metadata:\n'
g cat-file commit "$candidate" | sed -n '1,16p'
# Probe files as data only. No wrapper, Python module or update script is run.
for path in gclient gclient.py fetch vpython ninja gn update_depot_tools .cipd_client bootstrap/manifest.txt; do
  printf '\n--- Historical file: %s ---\n' "$path"
  if g cat-file -e "$candidate:$path" 2>/dev/null; then
    # Only selected entry/configuration lines; stop output at 25 selected lines.
    g show "$candidate:$path" | sed -n -E '/^#!|python|vpython|DEPOT_TOOLS_UPDATE|CIPD|cipd|bootstrap|ensure_bootstrap|https:\/\//p' | sed -n '1,25p' || {
      printf 'File inspection incomplete; retain stderr for diagnosis\n' >&2
      exit 1
    }
  else
    printf 'Not present or object unavailable; no lazy fetch attempted.\n'
  fi
done
printf '\nSpace for a future isolated tools directory (nothing created):\n'
df -hT -- /tmp "$(dirname -- "$repo")"
df -i -- /tmp
printf '\nEND: candidate inspection only; no checkout, archive extraction, update or bootstrap performed.\n'
