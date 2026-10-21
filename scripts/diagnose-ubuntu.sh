#!/usr/bin/env bash
# Read-only prerequisite inventory. No sudo, installation, network or cleanup.
# Usage: bash scripts/diagnose-ubuntu.sh [existing intended build directory]
set -u
build_location="${1:-$PWD}"
if [ ! -d "$build_location" ]; then
  printf 'Erreur : indiquez un répertoire existant pour mesurer le disque.\n' >&2
  exit 2
fi
section() { printf '\n===== %s =====\n' "$1"; }
section 'Système'
if [ -r /etc/os-release ]; then cat /etc/os-release; fi
uname -srmo
if command -v ldd >/dev/null 2>&1; then ldd --version 2>&1 | head -n 1; fi
section 'Mémoire et swap'
free -h
section 'Processeur'
if command -v lscpu >/dev/null 2>&1; then
  LC_ALL=C lscpu | sed -n -E '/^(Architecture|CPU\(s\)|On-line CPU|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|Model name):/p'
fi
if command -v nproc >/dev/null 2>&1; then printf 'CPU utilisables : '; nproc; fi
section 'Disque : emplacement prévu, dossier personnel et temporaire'
df -hT -- "$build_location" "$HOME" /tmp
df -i -- "$build_location"
section 'Outils disponibles et versions'
for tool in git python python2 python2.7 python3 ninja clang clang++ gcc g++ make cmake pkg-config ld ar curl wget xz bzip2 tar patch; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '\n%s : %s\n' "$tool" "$(command -v "$tool")"
    "$tool" --version 2>&1 | head -n 1
  else
    printf '\n%s : absent du PATH\n' "$tool"
  fi
done
section 'Outils Chromium : présence seulement, sans lancement ni mise à jour'
for tool in fetch gclient gn autoninja vpython vpython3 chromium chromium-browser google-chrome d8; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '%s : %s\n' "$tool" "$(command -v "$tool")"
  else
    printf '%s : absent du PATH\n' "$tool"
  fi
done
section 'Limites de processus'
ulimit -n
ulimit -u
printf '\nDiagnostic terminé. Aucun outil Chromium ni module Wasm exécuté.\n'
