#!/usr/bin/env bash
# Ubuntu 22.04 node only. Never touches Chromium, depot_tools or project files.
# Default is APT simulation against current lists. Explicit --install refreshes
# package indexes, then installs four tools with normal APT confirmation.
set -euo pipefail
mode=${1:---simulate}
if [[ $# -gt 1 ]]; then printf 'Usage: bash %s [--simulate|--install|--help]\n' "$0" >&2; exit 2; fi
case "$mode" in
  --help) printf 'Usage: bash %s [--simulate|--install]\nDefault: simulate only. --install: Ubuntu 22.04, root, APT update and four packages.\n' "$0"; exit 0;;
  --simulate|--install) ;;
  *) printf 'Unknown option: %s\n' "$mode" >&2; exit 2;;
esac
if [[ ! -r /etc/os-release ]]; then printf 'Cannot identify OS; stopping\n' >&2; exit 1; fi
# System distribution metadata, never project-supplied configuration.
. /etc/os-release
if [[ ${ID:-} != ubuntu || ${VERSION_ID:-} != 22.04 ]]; then
  printf 'Expected Ubuntu 22.04, found %s %s; no installation attempted\n' "${ID:-unknown}" "${VERSION_ID:-unknown}" >&2
  exit 1
fi
packages=(python2 ninja-build pkg-config ccache)
if [[ "$mode" = --simulate ]]; then
  printf 'SIMULATION ONLY: no package lists refreshed and no packages installed.\n'
  /usr/bin/apt-get --simulate --no-remove --no-install-recommends install "${packages[@]}"
  exit 0
fi
if (( EUID != 0 )); then printf '--install requires root on the compute node; stopping\n' >&2; exit 1; fi
printf 'Installing base tools only. No Chromium/depot_tools operation will run.\n'
# Retain normal signature/TLS checks; stop if the index refresh fails.
/usr/bin/apt-get -o APT::Update::Error-Mode=any update
/usr/bin/apt-get --no-remove --no-install-recommends install "${packages[@]}"
printf '\n=== Verification of system binaries (PATH wrappers bypassed) ===\n'
/usr/bin/python2 --version
/usr/bin/python2 -c 'import sys, ssl, json, subprocess; print(sys.executable); print(ssl.OPENSSL_VERSION)'
/usr/bin/ninja --version
/usr/bin/pkg-config --version
/usr/bin/ccache --version
printf '\nEND: base tools verified. Chromium/depot_tools compatibility and full build dependencies remain unverified.\n'
