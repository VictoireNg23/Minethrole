#!/usr/bin/env bash
# Read-only: no fetch, checkout, hooks, build, installation or filesystem writes.
# Usage: bash diagnose-grid5000-chromium71.sh EXISTING_MINETHROTTLE [--network]
set -u
export LC_ALL=C GIT_OPTIONAL_LOCKS=0 GIT_NO_LAZY_FETCH=1 GIT_TERMINAL_PROMPT=0
base=${1:-}
network=${2:-}
if [[ -z "$base" || ! -d "$base" || ( -n "$network" && "$network" != --network ) || $# -gt 2 ]]; then
  printf 'Usage: bash %s EXISTING_MINETHROTTLE [--network]\n' "$0" >&2
  exit 2
fi
if ! command -v timeout >/dev/null || ! command -v git >/dev/null; then
  printf 'Required diagnostic tools missing: git and timeout must be in PATH. No installation performed.\n' >&2
  exit 2
fi
section() { printf '\n===== %s =====\n' "$*"; }
# Every potentially slow command is bounded; failure is reported, not hidden.
run() {
  timeout 45s "$@"
  local result=$?
  if (( result != 0 )); then printf '[command exit=%s; unavailable, denied or timed out]\n' "$result"; fi
  return 0
}
base=$(readlink -f -- "$base")
section 'System and allocation'
[[ ! -r /etc/os-release ]] || cat /etc/os-release
uname -srmo
run id
run free -h
run nproc
if command -v lscpu >/dev/null; then
  lscpu | sed -n -E '/^(Architecture|CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|Model name):/p'
fi
for name in OAR_JOB_ID OAR_NODEFILE TMPDIR CCACHE_DIR DEPOT_TOOLS_UPDATE HTTP_PROXY HTTPS_PROXY ALL_PROXY; do
  if [[ -v "$name" ]]; then printf '%s: set (value not printed)\n' "$name"; else printf '%s: unset\n' "$name"; fi
done
ulimit -n
ulimit -u
section 'Storage, permissions, existing temporary directories'
for path in "$base" "$HOME" /tmp /var/tmp /local /scratch; do
  [[ -d "$path" ]] || continue
  printf '\nPath: %s\n' "$path"
  run df -hT -- "$path"
  run df -i -- "$path"
  run stat -c 'permissions=%A owner=%U group=%G' -- "$path"
  for perm in r w x; do
    case "$perm" in r) [[ -r "$path" ]];; w) [[ -w "$path" ]];; x) [[ -x "$path" ]];; esac
    result=$?; printf 'access -%s: %s\n' "$perm" "$((1-result))"
  done
  if command -v findmnt >/dev/null; then run findmnt -T "$path" -o TARGET,FSTYPE; fi
done
if [[ -n ${TMPDIR:-} && -d ${TMPDIR:-} && ${TMPDIR:-} != /tmp ]]; then run df -hT -- "$TMPDIR"; fi
if command -v quota >/dev/null; then run quota -s; else printf 'quota: not in PATH; quota remains unknown\n'; fi
section 'Project structure (one directory level only)'
for path in "$base" "$base/chromium" "$base/chromium71" "$base/chromium/_bad_scm" "$base/chromium71/_bad_scm"; do
  [[ -d "$path" ]] || continue
  printf '\nDirectory: %s\n' "$path"
  run find "$path" -mindepth 1 -maxdepth 1 -printf '%f\n'
done
if [[ -r "$base/build_minethrottle.sh" ]]; then
  printf '\nOriginal script settings (script NOT executed):\n'
  sed -n -E '/^(VERSION|NTHREADS|TMPFS_SIZE|BUILD_DIR|PATCH_DIR)=/p' "$base/build_minethrottle.sh"
fi
section 'gclient configuration metadata (parsed, never executed)'
if command -v python3 >/dev/null; then
  timeout 15s python3 - "$base" <<'PYMETA'
import ast, pathlib, sys, urllib.parse
for directory in ('chromium', 'chromium71'):
    root = pathlib.Path(sys.argv[1]) / directory
    for name in ('.gclient', '.gclient_entries', '.gcs_entries'):
        path = root / name
        if not path.is_file():
            continue
        print(str(path), 'bytes=', path.stat().st_size)
        if name != '.gclient':
            continue
        if path.stat().st_size > 1048576:
            print('Configuration too large; inspection deferred')
            continue
        try:
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'solutions' for t in node.targets):
                    for item in ast.literal_eval(node.value):
                        url = urllib.parse.urlsplit(item.get('url', ''))
                        print('solution name=', item.get('name'), 'host=', url.hostname, 'path=', url.path,
                              'managed=', item.get('managed'), 'custom_deps_count=', len(item.get('custom_deps', {})))
        except (OSError, ValueError, TypeError, SyntaxError) as exc:
            print('Literal metadata extraction unavailable:', type(exc).__name__)
PYMETA
fi
section 'Installed tool versions (Chromium wrappers NOT executed)' 
for tool in git python python2 python2.7 python3 gcc g++ clang clang++ make ninja cmake pkg-config patch curl ccache ld; do
  if command -v "$tool" >/dev/null; then
    printf '\n%s: %s\n' "$tool" "$(command -v "$tool")"
    timeout 10s "$tool" --version 2>&1 | head -n 1
  else printf '%s: not in PATH\n' "$tool"; fi
done
for tool in fetch gclient gn autoninja vpython vpython3 cipd d8; do
  if command -v "$tool" >/dev/null; then printf '%s: %s\n' "$tool" "$(command -v "$tool")"; else printf '%s: not in PATH\n' "$tool"; fi
done
section 'Installed development packages (Debian/Ubuntu only; no installation)'
if command -v dpkg-query >/dev/null; then
  run dpkg-query -W -f='${binary:Package} ${db:Status-Abbrev} ${Version}\n' build-essential python2 python2.7 libc6-dev libasound2-dev libatk1.0-dev libcups2-dev libdbus-1-dev libexpat1-dev libfontconfig1-dev libfreetype6-dev libglib2.0-dev libgtk-3-dev libnss3-dev libpci-dev libx11-dev libxcomposite-dev libxcursor-dev libxdamage-dev libxext-dev libxfixes-dev libxi-dev libxrandr-dev libxrender-dev libxss-dev libxtst-dev zlib1g-dev
else printf 'dpkg-query absent; package assessment requires OS-specific follow-up\n'; fi
# Disable every configured promisor remote before object probes, including on
# older Git versions which might not implement GIT_NO_LAZY_FETCH.
g() { timeout 45s git --no-optional-locks --no-replace-objects "${git_flags[@]}" -C "$repo" "$@"; }
setup_git() {
  git_flags=(-c core.fsmonitor=false -c core.hooksPath=/dev/null -c gc.auto=0 -c maintenance.auto=false)
  local remote
  while IFS= read -r remote; do
    [[ -z "$remote" ]] || git_flags+=(-c "remote.$remote.promisor=false")
  done < <(timeout 10s git -C "$repo" remote)
}
inspect_repo() {
  local repo=$1 expected=${2:-} root head rev deps v8_revision pattern common
  [[ -d "$repo" ]] || { printf '\nAbsent directory: %s\n' "$repo"; return; }
  setup_git
  section "Git tree: $repo"
  root=$(g rev-parse --show-toplevel 2>/dev/null) || { printf 'Not an accessible Git tree\n'; return; }
  # A directory nested in the MineThrottle checkout is not a Chromium repository.
  if [[ $(readlink -f -- "$root") != $(readlink -f -- "$repo") ]]; then
    printf 'Not a separate checkout; enclosing root: %s\n' "$root"; return
  fi
  run git --no-optional-locks "${git_flags[@]}" -C "$repo" log -1 --format='%H %cs %s'
  head=$(g rev-parse --verify HEAD 2>/dev/null) || head=unavailable
  printf 'Branch: '; g symbolic-ref --quiet --short HEAD || printf '(detached or unavailable)\n'
  printf 'Tracked changes only; ignored/untracked files deliberately not traversed:\n'
  g status --short --untracked-files=no --ignore-submodules=all || printf 'Status unavailable\n'
  printf 'Shallow: '; g rev-parse --is-shallow-repository
  printf 'Object storage (KiB):\n'; g count-objects -v
  printf 'Partial-clone remote declarations (names/booleans only):\n'
  g config --get-regexp '^remote\..*\.promisor$' || :
  common=$(g rev-parse --git-common-dir 2>/dev/null) || common=''
  if [[ -n "$common" ]]; then
    [[ "$common" = /* ]] || common="$repo/$common"
    if [[ -r "$common/objects/info/alternates" ]]; then
      printf 'Local alternate object stores:\n'; sed -n '1,20p' "$common/objects/info/alternates"
    fi
  fi
  if [[ -n "$expected" ]]; then
    rev=$expected
    printf 'Expected V8 commit from historical Chromium DEPS: %s\n' "$rev"
  else
    rev=$(g rev-parse --verify 'refs/tags/71.0.3578.98^{commit}' 2>/dev/null) || rev=''
    if [[ -z "$rev" ]]; then
      printf 'Historical Chromium tag NOT resolved locally; no fetch attempted.\n'
      printf 'Other local references naming the release:\n'
      g for-each-ref --format='%(refname) %(objectname)' '*71.0.3578.98*'
      return
    fi
    printf 'Historical Chromium tag resolves locally: %s\n' "$rev"
  fi
  if ! g cat-file -e "$rev^{commit}" 2>/dev/null; then
    printf 'Historical commit object unavailable locally; no lazy fetch attempted.\n'; return
  fi
  printf 'Historical commit metadata: '; g show -s --format='%H %cs %s' "$rev"
  if [[ -z "$expected" ]]; then
    deps=$(g show "$rev:DEPS" 2>/dev/null) || { printf 'Historical DEPS blob unavailable locally\n'; return; }
    pattern="[\"']v8_revision[\"'][[:space:]]*:[[:space:]]*[\"']([0-9a-f]{40})[\"']"
    if [[ "$deps" =~ $pattern ]]; then
      v8_revision=${BASH_REMATCH[1]}
      inspect_repo "$repo/v8" "$v8_revision"
      setup_git # Restore parent repository settings after recursive inspection.
    else printf 'Literal v8_revision not extracted from DEPS; needs manual inspection (no execution of DEPS).\n'; fi
    if [[ "$head" = "$rev" && -r "$base/patches/content.patch" ]]; then
      printf 'content.patch applicability on CURRENT historical worktree (check only):\n'
      g apply --check --directory=content "$base/patches/content.patch" || printf 'CHECK FAILED: do not apply patch\n'
    else printf 'content.patch context check deferred: worktree not confirmed at the target revision.\n'; fi
  else
    printf 'V8 version header at expected historical revision:\n'
    g show "$rev:include/v8-version.h" | sed -n '/^#define V8_.*VERSION/p; /^#define V8_BUILD_NUMBER/p; /^#define V8_PATCH_LEVEL/p'
    if [[ "$head" = "$rev" && -r "$base/patches/v8.patch" ]]; then
      printf 'v8.patch applicability on CURRENT historical worktree (check only):\n'
      g apply --check "$base/patches/v8.patch" || printf 'CHECK FAILED: do not apply patch\n'
    else printf 'v8.patch context check deferred: worktree not at the expected historical revision.\n'; fi
  fi
}
section 'MineThrottle checkout metadata'
repo="$base"; setup_git
if g rev-parse --verify HEAD >/dev/null 2>&1; then
  g log -1 --format='%H %cs %s'
  g status --short --untracked-files=no --ignore-submodules=all
  if command -v sha256sum >/dev/null; then
    for path in "$base/patches/v8.patch" "$base/patches/content.patch" "$base/build_minethrottle.sh"; do
      [[ ! -r "$path" ]] || sha256sum -- "$path"
    done
  fi
else printf 'MineThrottle Git metadata unavailable\n'; fi
for checkout in "$base/chromium/src" "$base/chromium71/src"; do
  inspect_repo "$checkout"
  # Also identify current V8, even when the historical tag is missing.
  if [[ -d "$checkout/v8" ]]; then
    repo="$checkout/v8"; setup_git
    section "Current V8 metadata: $repo"
    g log -1 --format='%H %cs %s'
    g status --short --untracked-files=no --ignore-submodules=all
  fi
done
section 'depot_tools Git metadata when fetch is present in PATH'
if command -v fetch >/dev/null; then
  path=$(command -v fetch)
  path=$(readlink -f -- "$path")
  repo=$(dirname -- "$path"); setup_git
  g log -1 --format='%H %cs %s' || printf 'Wrapper location is not an accessible depot_tools Git checkout\n'
fi
section 'Optional small HTTPS connectivity probes'
if [[ "$network" = --network ]]; then
  if command -v curl >/dev/null; then
    for url in https://chromium.googlesource.com/chromium/src/ https://chrome-infra-packages.appspot.com/ https://storage.googleapis.com/ https://commondatastorage.googleapis.com/; do
      printf '\n%s\n' "$url"
      # No redirects, credentials, proxy values or response bodies are printed.
      timeout 12s curl -q --head --silent --show-error --max-time 10 --output /dev/null --write-out 'HTTP=%{http_code}\n' "$url"
      result=$?; printf 'curl exit=%s\n' "$result"
    done
  else printf 'curl missing; network not tested\n'; fi
else printf 'Not requested. Re-run with --network for four HEAD requests, no source download.\n'; fi
printf '\nEND. No checkout, fetch, sync, patch application, installation or build performed.\n'
