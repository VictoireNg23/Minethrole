#!/usr/bin/env bash
# Read-only follow-up after historical patch context checks passed.
# No package update/install, depot_tools execution, Git fetch or source checkout.
set -u
project=${1:-}
if [[ -z "$project" || ! -d "$project" || $# -ne 1 ]]; then
  printf 'Usage: bash %s EXISTING_MINETHROTTLE_DIRECTORY\n' "$0" >&2
  exit 2
fi
if ! command -v timeout >/dev/null; then
  printf 'timeout missing; no changes made\n' >&2
  exit 2
fi
project=$(readlink -f -- "$project")
depot="$(dirname -- "$project")/depot_tools"
section() { printf '\n===== %s =====\n' "$*"; }
run() {
  timeout 20s "$@"
  local code=$?
  if (( code != 0 )); then printf '[exit=%s; observation unavailable]\n' "$code"; fi
  return 0
}
section 'Exact OS and current identity'
[[ ! -r /etc/os-release ]] || cat /etc/os-release
run id
section 'Storage and temporary space'
for path in "$project" /tmp /var/tmp /local /scratch; do
  [[ -d "$path" ]] || continue
  run df -hT -- "$path"
  run df -i -- "$path"
  run stat -c '%n owner=%U group=%G permissions=%A' -- "$path"
  if command -v findmnt >/dev/null; then run findmnt -T "$path" -o TARGET,FSTYPE; fi
done
section 'Quotas (root quota is not necessarily the storage owner quota)'
if command -v quota >/dev/null; then
  run quota -s
  if [[ $(id -u) = 0 ]]; then run quota -s -u killerdroid; fi
else printf 'quota missing; per-user storage quota remains unknown\n'; fi
section 'Local APT candidates; package indexes are NOT refreshed'
if command -v apt-cache >/dev/null; then
  run apt-cache policy python2 python2.7 python2-minimal python2.7-minimal ninja-build pkg-config ccache
else printf 'apt-cache absent\n'; fi
section 'System tools independently of depot_tools PATH wrappers'
for tool in /usr/bin/python2 /usr/bin/python2.7 /usr/bin/ninja /usr/bin/pkg-config /usr/bin/ccache; do
  if [[ -x "$tool" ]]; then run "$tool" --version; else printf '%s absent/not executable\n' "$tool"; fi
done
section 'Expected sibling depot_tools, metadata only'
printf 'Directory: %s\n' "$depot"
if [[ -d "$depot" ]]; then
  run stat -c '%n owner=%U group=%G permissions=%A' -- "$depot"
  if command -v git >/dev/null; then
    # No log or status: these timed out on the large historical source stores.
    run git --no-optional-locks -c core.fsmonitor=false -C "$depot" rev-parse --show-toplevel
    run git --no-optional-locks -c core.fsmonitor=false -C "$depot" rev-parse --verify HEAD
  fi
  for name in fetch gclient gclient.py vpython vpython3 ninja gn autoninja; do
    if [[ -e "$depot/$name" ]]; then run stat -c '%n type=%F permissions=%A' -- "$depot/$name"; fi
  done
else printf 'Expected sibling directory missing; provide actual depot_tools location\n'; fi
printf '\nEND: no installation, package refresh, fetch, patch application or build performed.\n'
