# Refaire l'installation et la compilation de MineThrottle — Chromium 71

Ce guide rassemble les commandes de la reproduction réussie sur **Grid5000, Ubuntu 22.04 amd64**, de l'installation des outils à `Chromium 71.0.3578.98 --version`. Il utilise exclusivement C++, Chromium et V8. Les patches originaux ne sont pas modifiés. La compilation se fait sur votre machine, jamais dans l'environnement Codex.

**État vérifié au 21 octobre 2026 :** Chromium complet compile et affiche sa version ; ses bibliothèques partagées sont résolues. Les 12 signatures actives ont passé 72 contrôles synthétiques sous d8. L'exécution d'une page dans Chromium, les profils, les vitesses, la défense et les expériences du dataset restent à valider.

## 1. Versions exactes et portée

| Élément | Version/révision retenue |
|---|---|
| Chromium | `71.0.3578.98` — `c2bec8045f7ad3ece1c5d80236183a21c1fac3f5` |
| V8, extrait du DEPS Chromium | `7.1.302.31` — `b5a5d900a5385d6429edefb11ece72bfa649ca47` |
| depot_tools historique choisi pour cette reproduction | `c6a8d114b060f5f68637e8897712a24252402377` |
| Python des scripts Chromium historiques | Python 2.7.18 ; les scripts de ce dépôt utilisent Python 3 |
| Clang téléchargé par la version historique | `8.0.0 (trunk 344066)`, paquet `344066-1` |
| GN historique | `1463 (e134e493)` |
| Sysroot | Debian sid amd64, SHA-1 `e7c53f04bd88d29d075bfd1f62b073aeb69cbe09` |
| Node pour le build WebUI | `8.9.1` ; polymer-bundler `3.1.1` |
| Outils hôtes observés | Ninja `1.10.1`, ccache `4.5.1`, gperf `3.1`, Bison `3.8.2` |

Le nom d'un dossier `chromium71` ne prouve pas sa version. Vérifier les SHA, pas les noms. La révision depot_tools est notre choix documenté pour rendre la reproduction possible, pas une version explicitement annoncée par les auteurs.

Le parcours principal ci-dessous **réutilise des sources et objets Git déjà disponibles**, comme sur le nœud utilisé. Le démarrage sans aucun objet local est décrit séparément en section 16 et n'a pas été validé de bout en bout. Sur une autre distribution, ne pas appliquer aveuglément la liste APT Ubuntu 22.04.

## 2. Ressources, stockage et précautions

Machine ayant réussi : 376 Gio de RAM, 72 processeurs logiques ; builds effectués avec 8 tâches pour d8 puis 16 pour chrome. Ce sont des ressources observées, pas un minimum requis. Le disque local `/tmp` disposait initialement d'environ 808 Gio libres. L'espace NFS libre ne remplace pas un quota confirmé.

```bash
cat /etc/os-release
uname -m
free -h
nproc
df -hT /tmp
df -i /tmp
```

Pour un autre disque, vérifier également ses droits d'écriture et quotas auprès de Grid5000. Les seuils des scripts (20 Gio pour le checkout initial, 100 Gio pour sync, 30 Gio avant build) sont des garde-fous, **pas une garantie de capacité pour toute la reproduction**. Prévoir plusieurs centaines de Gio disponibles pour une reconstruction complète ; la consommation totale finale n'a pas été mesurée de façon consolidée.

Ne pas supprimer, déplacer, nettoyer ou réinitialiser les sources existantes. Les nouveaux clones empruntent leurs magasins d'objets (`git clone --shared`) : conserver ces magasins et ne pas lancer de garbage collection destructive dessus. Tous les staging `/tmp/minethrottle71-*` liés au workspace doivent rester présents : GN, Clang, sysroot et Node sont reliés par liens symboliques. `/tmp` et les nœuds Grid5000 sont temporaires ; cette procédure permet de reconstruire, elle ne garantit pas la conservation d'un binaire après fin de réservation.

Les sources Chromium, binaires, caches et gros résultats restent hors Git. Conserver aussi les sorties terminal/rapports nécessaires dans votre espace de résultats, sans les ajouter automatiquement au dépôt.

## 3. Installer les dépendances système connues

Commandes APT à exécuter avec les droits d'administration du **nœud de calcul**, pas sur le stockage partagé. Sur un PC Ubuntu, utiliser `sudo` si nécessaire. Lire la proposition APT et arrêter en cas d'erreur ; ne pas poursuivre après une installation incomplète.

```bash
apt-get update
apt-get install --no-remove --no-install-recommends \
  ca-certificates curl git python3 python2 \
  build-essential ninja-build pkg-config ccache \
  tar xz-utils unzip gperf bison \
  libxss1 libasound2
```

La liste réunit les outils employés et les dépendances qui ont effectivement manqué. Les autres bibliothèques d'exécution déjà présentes sur le nœud seront contrôlées par `ldd` à la fin : ce n'est pas une liste exhaustive garantie pour toute image Ubuntu minimale. Les bibliothèques de compilation GTK/NSS/etc. sont fournies en grande partie par le **sysroot historique**, ne pas confondre avec les bibliothèques hôtes requises pour exécuter chrome.

```bash
/usr/bin/python2 --version
/usr/bin/python2 -c 'import ssl; print(ssl.OPENSSL_VERSION)'
python3 --version
git --version
/usr/bin/ninja --version
/usr/bin/pkg-config --version
/usr/bin/ccache --version
gperf --version
bison --version
```

Ne pas remplacer `/usr/bin/python` globalement. Le snapshot isolé fournit son propre lanceur `python` vers Python 2 et un accès au Ninja système. Un Ninja présent dans depot_tools peut n'être qu'un wrapper inutilisable avant préparation.

GDB sert au diagnostic du crash d8, pas à compiler : installation optionnelle si besoin, `apt-get install --no-remove --no-install-recommends gdb`.

## 4. Récupérer les scripts et définir les chemins

Les commandes suivantes créent uniquement de nouveaux dossiers. **Ne pas réutiliser un ancien dossier comme s'il était vide.** Garder le même shell pour les variables. Exécuter chaque bloc séparément et vérifier son résultat avant le suivant.

```bash
BASE=$(mktemp -d /tmp/minethrottle71-reproduction.XXXXXX)
CODE="$BASE/Minethrole"
RUNLOGS="$BASE/logs"
mkdir "$RUNLOGS"

git clone --single-branch --branch diagnostics/grid5000-chromium71 \
  https://github.com/VictoireNg23/Minethrole.git "$CODE"
git -C "$CODE" checkout --detach 468e3babeed90fd95a416b960f0992d101353b1c
```

Cette révision épingle les scripts et correctifs utilisés dans ce guide. Les ajouts documentaires ultérieurs ne changent pas les commandes. Pour voir une documentation plus récente, consulter la branche ; ne pas mélanger silencieusement des versions de scripts dans une expérience.

Définir les **sources existantes à réutiliser**. Adapter les deux chemins si vous êtes sur un autre nœud ou PC :

```bash
SOURCE_PROJECT='/srv/storage/killerdroid@storage3.rennes.grid5000.fr/datasets/Andromatch_Paper/SOK_WebAsssembly_2025_Grid5000/DualGraphWasm/Dataset_Dynamic/tests/MineThrottle'
DEPOT_EXISTING='/srv/storage/killerdroid@storage3.rennes.grid5000.fr/datasets/Andromatch_Paper/SOK_WebAsssembly_2025_Grid5000/DualGraphWasm/Dataset_Dynamic/tests/depot_tools'
```

Le premier chemin doit contenir `patches/`, `chromium/src/.git` et `chromium/src/v8/.git`. Ces sources ne seront pas mises à une autre révision ; seul le nouveau workspace sera modifié. Le second est un dépôt Git contenant le commit depot_tools historique.

Helpers de journalisation : ils conservent le vrai code de sortie d'une commande, même avec `tee`. **Si `run_step` échoue, arrêter la procédure et examiner son journal.** Un rapport JSON peut exister après un échec : sa présence seule ne prouve pas un succès.

```bash
set -o pipefail

run_step() {
  local label="$1"
  shift
  LAST_LOG=$(mktemp "$RUNLOGS/${label}.XXXXXX.log")
  if "$@" 2>&1 | tee "$LAST_LOG"; then
    printf '\nJournal : %s\n' "$LAST_LOG"
  else
    printf '\nSTOP : étape échouée ; journal : %s\n' "$LAST_LOG" >&2
    return 1
  fi
}

log_value() {
  python3 - "$LAST_LOG" "$1" <<'PY'
import sys
from pathlib import Path
prefix = sys.argv[2]
values = [line[len(prefix):].strip()
          for line in Path(sys.argv[1]).read_text().splitlines()
          if line.startswith(prefix)]
if not values:
    raise SystemExit('Valeur absente du journal : ' + prefix)
print(values[-1])
PY
}
```

## 5. Vérifier les objets locaux et les patches

Ces vérifications ne téléchargent rien :

```bash
GIT_NO_LAZY_FETCH=1 git -C "$SOURCE_PROJECT/chromium/src" \
  cat-file -t c2bec8045f7ad3ece1c5d80236183a21c1fac3f5
GIT_NO_LAZY_FETCH=1 git -C "$SOURCE_PROJECT/chromium/src/v8" \
  cat-file -t b5a5d900a5385d6429edefb11ece72bfa649ca47
GIT_NO_LAZY_FETCH=1 git -C "$DEPOT_EXISTING" \
  cat-file -t c6a8d114b060f5f68637e8897712a24252402377
sha256sum "$SOURCE_PROJECT/patches/v8.patch" \
  "$SOURCE_PROJECT/patches/content.patch"
```

Attendre `commit` pour les trois objets. Empreintes des originaux :

```text
v8.patch      72c3adef6f566e7de6b6b7f0d1c6a12f0384098be3601fbcbe2272f1861ee563
content.patch 7401d2c063f7b4f5b3239dd7b2eb61e3b005123dda6395d1a7e17626e5b06b22
```

En cas d'objet absent, arrêter et préparer une récupération ciblée, sans checkout forcé des sources existantes. Les scripts recontrôlent les révisions/empreintes avant mutation.

## 6. Préparer depot_tools historique et le workspace isolé

```bash
run_step tools python3 "$CODE/scripts/prepare-historical-depot-tools.py" \
  "$DEPOT_EXISTING" --temporary-parent "$BASE"
TOOLS_ROOT=$(dirname "$(log_value 'Prepared snapshot:')")

run_step gclient-help python3 "$CODE/scripts/check-historical-gclient.py" \
  "$TOOLS_ROOT"
```

Attendu : snapshot préparé, Python 2 et Ninja vérifiés, puis `help_completed`. L'avertissement d'exécution root n'est pas un échec du help. La compatibilité de sync sera vérifiée ensuite. Le snapshot désactive son auto-mise à jour et conserve les liens internes historiques.

```bash
run_step workspace python3 "$CODE/scripts/prepare-chromium71-local.py" \
  "$SOURCE_PROJECT" --tools-root "$TOOLS_ROOT" --temporary-parent "$BASE"
WORK=$(log_value 'NEW WORKSPACE (retained on failure):')

run_step audit python3 "$CODE/scripts/audit-chromium71-deps.py" \
  "$WORK" "$SOURCE_PROJECT"
AUDIT_REPORT=$(log_value 'Report:')

run_step seed python3 "$CODE/scripts/seed-chromium71-deps.py" \
  "$WORK" "$AUDIT_REPORT" --apply
SEED_REPORT=$(log_value 'Report:')
```

Attendu : checkouts Chromium/V8 exacts et vérification des contextes des deux patches ; puis audit/seed local terminés. Les dépendances non disponibles, conditionnelles ou CIPD ne sont pas déclarées prêtes par le seed.

## 7. Dépendance DevTools dont l'ancienne URL a disparu

La révision historique attend `5f7cd2497d7a643125c3b6eb910d99ba28be6899`. L'URL googlesource d'origine était indisponible pendant notre tentative. Le script utilise le miroir tiers `bpsinc-native/src_third_party_devtools-node-modules`, **uniquement avec ce SHA exact**, jamais sa branche courante. Les objets sont vérifiés par Git fsck.

```bash
run_step devtools python3 "$CODE/scripts/prepare-devtools-exact-mirror.py" \
  "$WORK" --fetch-exact
DEVTOOLS_REPORT=$(log_value 'Report:')
```

Attendu : `exact_commit_verified_alternative_config_prepared`. `.gclient` et DEPS originaux restent intacts ; la configuration créée est `.gclient.minethrottle-mirror`. **Toutes les commandes sync suivantes doivent sélectionner cette configuration.** Si le miroir disparaît ou refuse le SHA, arrêter au lieu d'utiliser une autre révision.

## 8. Synchroniser les dépendances sans hooks

```bash
run_step sync python3 "$CODE/scripts/sync-chromium71-nohooks.py" \
  "$WORK" "$SEED_REPORT" \
  --gclientfile .gclient.minethrottle-mirror --sync --timeout 900
SYNC_REPORT=$(log_value 'Report:')
```

Attendu : `sync_exit_zero_primary_heads_verified_nohooks`, code 0 ; cache résolu `null`, garde-fou actif, hooks/pré-hooks désactivés. Le script conserve une configuration épinglée et bloque la récupération historique par déplacement/suppression automatique. Ne pas appeler directement un sync avec force/reset pour contourner un échec.

### Si WebRTC échoue avec « reference is not a tree »

C'était le cas sur notre nœud : le SHA n'était pas atteint par un simple fetch des branches. Ne pas considérer cela comme une disparition de Chromium 71. Arrêter la sync, puis :

```bash
run_step webrtc-fetch python3 "$CODE/scripts/fetch-webrtc-exact.py"
WEBRTC_FETCH_REPORT=$(log_value 'Report:')
```

Le serveur officiel doit fournir `0ba24191ee90c70679d2452363676c2d65b6b751`, son arbre, et fsck doit réussir. Puis, **si la cible WebRTC existe comme dépôt Git issu de la tentative échouée**, intégrer les objets locaux :

```bash
run_step webrtc-integrate python3 "$CODE/scripts/integrate-webrtc-exact.py" \
  "$WORK" "$WEBRTC_FETCH_REPORT"
```

Le script accepte un dépôt propre ou l'état strict « seulement .git, index vide, suppressions indexées » d'un clone sans checkout. Tout autre contenu reste refusé. Si la cible est absente, conserver les rapports et faire préparer un nouveau dépôt cible ; ce script n'autorise pas à remplacer un dossier quelconque. Les sources partagées ne sont pas modifiées.

Après intégration réussie, relancer le bloc sync précédent et enregistrer **son nouveau rapport réussi** dans `SYNC_REPORT`. Autres échecs : utiliser `scripts/show-gclient-errors.py CHEMIN_DU_SYNC_LOG` et corriger la cause avant reprise. Un timeout conserve les objets et reste incomplet ; ne pas lancer les hooks.

## 9. Télécharger et préparer GN, Clang, sysroot

```bash
run_step gn python3 "$CODE/scripts/prepare-chromium71-gn.py" "$WORK"
GN_REPORT=$(log_value 'Report:')

run_step toolchain-download python3 "$CODE/scripts/download-chromium71-toolchain.py" "$WORK"
TOOLCHAIN_REPORT=$(log_value 'Report:')

run_step clang python3 "$CODE/scripts/stage-chromium71-clang.py" "$TOOLCHAIN_REPORT"
CLANG_REPORT=$(log_value 'Report:')

run_step sysroot python3 "$CODE/scripts/stage-chromium71-sysroot.py" "$TOOLCHAIN_REPORT"
SYSROOT_REPORT=$(log_value 'Report:')

run_step tools-link python3 "$CODE/scripts/link-chromium71-tools.py" \
  "$WORK" "$GN_REPORT" "$CLANG_REPORT" "$SYSROOT_REPORT"
TOOLS_REPORT=$(log_value 'Report:')
```

Attendre chaque succès avant la commande suivante. GN et le sysroot sont comparés à leurs SHA-1 historiques ; Clang est un artefact officiel HTTPS versionné `344066-1`, mais aucune empreinte indépendante attendue n'avait été fournie par les métadonnées examinées. Son SHA-256 reçu est conservé pour provenance, sans le présenter comme une authentification indépendante.

Les extractions contrôlent chemins/liens et ne remplacent aucun dossier existant. Attendu : GN `1463 (e134e493)`, Clang `8.0.0 (trunk 344066)`, sysroot extrait, trois liens créés. Ne pas exécuter globalement `gclient runhooks`, `landmines` ou des scripts de nettoyage pour obtenir ces fichiers.

## 10. Préparer Node et les métadonnées normalement générées par les hooks

Préparer dès maintenant les dépendances qui avaient arrêté les premiers builds :

```bash
run_step node-download python3 "$CODE/scripts/download-chromium71-node.py" "$WORK"
NODE_DOWNLOAD_REPORT=$(log_value 'Report:')

run_step node-stage python3 "$CODE/scripts/stage-chromium71-node.py" \
  "$WORK" "$NODE_DOWNLOAD_REPORT"
NODE_REPORT=$(log_value 'Report:')

run_step lastchange python3 "$CODE/scripts/prepare-chromium71-lastchange.py" "$WORK"
LASTCHANGE_REPORT=$(log_value 'Report:')

run_step version-headers python3 "$CODE/scripts/prepare-chromium71-version-headers.py" "$WORK"
HEADERS_REPORT=$(log_value 'Report:')
```

Attendu : Node `v8.9.1`, bundler `3.1.1`, appel sans extension testé et liens créés ; LASTCHANGE et timestamp produits par le générateur historique ; headers GPU/Skia produits avec gardes valides. Les scripts actuels corrigent directement les erreurs de contrôle du bundler et de gardes rencontrées pendant la mise au point : **ne pas reproduire ces erreurs comme des étapes nécessaires**.

Les sorties existantes ne sont pas écrasées. En cas de reprise d'un workspace déjà préparé, ne pas relancer aveuglément les scripts de création : utiliser les rapports existants après inspection. Aucun `npm install`, aucune substitution par Node récent, aucune valeur de commit/timestamp inventée.

## 11. Configurer puis appliquer les patches originaux

Les arguments des auteurs sont conservés :

```text
cc_wrapper="ccache" use_jumbo_build=true is_debug=false enable_nacl=false
```

Une première génération sur sources non patchées sert de prérequis au script d'application :

```bash
run_step gn-unpatched python3 "$CODE/scripts/configure-chromium71.py" \
  "$WORK" "$TOOLS_REPORT"
GN_UNPATCHED_REPORT=$(log_value 'Report:')

run_step original-patches python3 "$CODE/scripts/apply-chromium71-original-patches.py" \
  "$WORK" "$GN_UNPATCHED_REPORT"
ORIGINAL_PATCH_REPORT=$(log_value 'Report:')
```

Attendu : `gn_generation_passed_unpatched`, puis `original_patches_applied_compilation_unvalidated`. Les deux empreintes et les contextes sont contrôlés avant application. Les fichiers sources du **nouveau** workspace sont modifiés ; les patches de référence restent intacts. Une application partielle doit être analysée, pas annulée par reset.

## 12. Appliquer les deux adaptations séparées de cette reproduction

### Arrêt de d8

Le patch original échantillonnait encore les compteurs pendant exit ; GDB a confirmé un SIGSEGV dans SignalHandler. L'adaptation arrête SIGALRM/ITIMER_REAL avant la destruction finale du shell d8. Elle ne modifie pas les signatures, profils, formules ou seuils et ne prétend pas corriger le cycle de vie des renderers Chromium.

```bash
run_step d8-shutdown-adaptation python3 "$CODE/scripts/apply-chromium71-d8-shutdown-fix.py" \
  "$WORK" "$CODE/patches/chromium71/d8-stop-timer-before-teardown.patch"
D8_ADAPTATION_REPORT=$(log_value 'Report:')
```

### Bison 3.8.2 / Blink historique

Le wrapper renomme le header généré en `.h`, alors que le C++ récent inclut encore `.hh`. L'adaptation réécrit cet include uniquement, sans changer la grammaire ni MineThrottle.

```bash
run_step bison-adaptation python3 "$CODE/scripts/apply-chromium71-bison-include-fix.py" \
  "$WORK" "$CODE/patches/chromium71/blink-bison-generated-header-include.patch"
BISON_ADAPTATION_REPORT=$(log_value 'Report:')
```

Les scripts sauvegardent chaque fichier source modifié et son diff dans un nouveau dossier. Ces adaptations sont nécessaires au parcours observé, pas des modifications silencieuses des patches originaux. Elles conservent les licences des fichiers concernés.

Régénérer GN avec contrôle des patches appliqués :

```bash
run_step gn-patched python3 "$CODE/scripts/configure-chromium71.py" \
  "$WORK" "$TOOLS_REPORT" --patch-report "$ORIGINAL_PATCH_REPORT"
GN_PATCHED_REPORT=$(log_value 'Report:')
```

Attendu : `gn_generation_passed_patched`. Le script fournit explicitement `--root=.../src`, car le lanceur historique change le répertoire courant. La génération se fait dans un nouveau `src/out/MineThrottle71-config-*` ; son chemin figure dans le rapport.

## 13. Compiler d8 et valider les compteurs

```bash
run_step build-d8 python3 "$CODE/scripts/build-chromium71-d8.py" \
  "$WORK" "$GN_PATCHED_REPORT" \
  --target d8 --adaptation-report "$D8_ADAPTATION_REPORT" \
  --bison-adaptation-report "$BISON_ADAPTATION_REPORT" \
  --jobs 8 --timeout 900
D8_BUILD_REPORT=$(log_value 'Report:')
```

Attendu : `d8_build_passed`, code 0 et SHA-256 du binaire. Cache ccache dédié au workspace, plafond 10 Gio. Les builds ne sont pas lancés via `autoninja` moderne.

```bash
run_step smoke python3 "$CODE/scripts/test-chromium71-counters.py" \
  "$WORK" "$D8_BUILD_REPORT" "$CODE/tests/fixtures/d8-counter-smoke.js" --repeat 3
SMOKE_REPORT=$(log_value 'Report:')

run_step signatures python3 "$CODE/scripts/test-chromium71-counters.py" \
  "$WORK" "$D8_BUILD_REPORT" "$CODE/tests/fixtures/d8-all-signatures.js" \
  --all-signatures --repeat 3 --previous-smoke-report "$SMOKE_REPORT"
SIGNATURES_REPORT=$(log_value 'Report:')
```

Attendu : `counter_smoke_passed`, neuf cas puis 72 cas réussis. Chaque signature est exécutée 20 000 fois et doit incrémenter uniquement son compteur. Les cas dormants vérifient qu'instancier sans appeler ne suffit pas. Les modules sont synthétiques et bénins, sans dataset ni réseau.

Un SIGSEGV après `SMOKE_OK` reste un échec : le marqueur ne suffit pas. Absence de mesures, trap et timeout ne sont jamais assimilés à du bénin. Les rapports vérifient l'empreinte du binaire et conservent la provenance des adaptations. Le résultat ne valide pas encore les profils ou la défense.

## 14. Compiler Chromium complet

```bash
run_step build-chrome python3 "$CODE/scripts/build-chromium71-d8.py" \
  "$WORK" "$GN_PATCHED_REPORT" \
  --target chrome --adaptation-report "$D8_ADAPTATION_REPORT" \
  --bison-adaptation-report "$BISON_ADAPTATION_REPORT" \
  --jobs 16 --timeout 900
CHROME_BUILD_REPORT=$(log_value 'Report:')
```

Le fichier du wrapper s'appelle toujours `build-chromium71-d8.py` pour compatibilité avec les commandes publiées, mais `--target chrome` sélectionne explicitement Chromium complet. Attendu : `chrome_build_passed`, code 0, binaire présent et SHA-256 enregistré.

Chaque tentative conserve son journal. Le délai de 900 secondes n'est pas une estimation de durée totale : un build complet peut nécessiter plusieurs tentatives selon la machine. En cas de timeout, le script arrête son groupe de processus et conserve les objets. Après vérification de la cause et de l'espace disponible, relancer **le même bloc avec le même rapport GN**, sans nettoyage, pour une reprise incrémentale. En cas d'erreur, analyser le journal avant reprise ; ne pas traiter toute erreur comme un simple timeout.

Le contrôle minimal d'espace libre ne remplace pas une surveillance du disque. Une autre session peut suivre le chemin `Log:` affiché : `tail -f CHEMIN_DU_BUILD_LOG`. Ne pas lancer deux Ninja concurrents dans le même répertoire.

## 15. Vérifier le binaire et la version, sans page

```bash
run_step chrome-runtime python3 "$CODE/scripts/check-chromium71-runtime.py" \
  "$WORK" "$CHROME_BUILD_REPORT"
CHROME_RUNTIME_REPORT=$(log_value 'Report:')
```

Attendu :

```text
status: chrome_dependencies_and_version_passed
missing_libraries: []
version_exit_code: 0
version_output: Chromium 71.0.3578.98
```

Le script compare le binaire au SHA-256 du rapport, exécute ldd puis seulement `chrome --version`. Il n'ouvre aucune page et ne désactive pas le sandbox. Si ldd trouve d'autres bibliothèques absentes sur une autre image système, identifier leurs paquets avant une nouvelle tentative. Ne pas pointer le navigateur vers les bibliothèques du sysroot pour contourner cela.

**Arrêt du guide : installation et compilation réussies, binaire vérifié.** Un test de page locale non privilégié avec sandbox sera une étape distincte. Ne pas lancer directement les commandes historiques `--no-sandbox` sur les modules malveillants du dataset.

### Retrouver les sorties et rapports dans le shell courant

```bash
printf 'Scripts : %s\nWorkspace : %s\nJournaux : %s\n' "$CODE" "$WORK" "$RUNLOGS"
printf 'Build Chromium : %s\nVérification : %s\n' "$CHROME_BUILD_REPORT" "$CHROME_RUNTIME_REPORT"
python3 - "$CHROME_BUILD_REPORT" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
command = r['command']
print('Répertoire du binaire :', command[command.index('-C') + 1])
print('SHA-256 :', r.get('binary_sha256'))
PY
```

Conserver ces chemins avec les journaux de l'expérience. Ils changent d'une reproduction à l'autre : ne pas réutiliser les suffixes aléatoires de l'ancien nœud.

## 16. Si aucune source n'est disponible localement

Ce cas **n'est pas le parcours validé sur Grid5000**. Les scripts de réutilisation ne téléchargent pas automatiquement Chromium et ne constituent pas un installateur universel depuis zéro. Il faut d'abord préparer de nouveaux dépôts sources contenant les objets exacts attendus, sans toucher à des dossiers existants.

Pour vérifier l'accès avant un téléchargement important :

```bash
curl --head --location --max-time 30 \
  https://chromium.googlesource.com/chromium/src/
curl --head --location --max-time 30 \
  https://webrtc.googlesource.com/src/
curl --head --location --max-time 30 \
  https://storage.googleapis.com/
```

Des réponses 400/405 sur une racine de stockage ne prouvent ni l'absence du service ni la disponibilité d'un artefact précis. Un 503 peut être temporaire ; ne pas relancer un téléchargement massif sans diagnostic.

Pour un nouveau téléchargement Chromium, le tag à cibler est **71.0.3578.98**, pas master. Une possibilité à examiner sur votre machine est un clone sans checkout du tag, par exemple `git clone --no-checkout --single-branch --branch 71.0.3578.98 URL NOUVEAU_DOSSIER`. Cela peut transférer un historique volumineux. Une variante superficielle ne garantit pas l'accès aux métadonnées de commit utilisées par lastchange ni la compatibilité de tous les scripts de clonage partagé : elle doit être testée séparément. Il faut aussi récupérer le SHA V8 exact dans un dépôt propre et les objets depot_tools historiques avant de revenir à la section 5.

Ne pas présenter ces possibilités comme déjà validées. L'accès googlesource était bloqué dans l'environnement Codex ; aucun arbre Chromium n'y a été téléchargé ni compilé. Le nœud Grid5000, lui, a pu récupérer les dépendances et le commit WebRTC demandé explicitement. Un nouvel échec réseau ne justifie pas de passer automatiquement à Chromium récent, Rust ou Wasmtime.

## 17. Erreurs rencontrées et solutions retenues

| Symptôme | Cause constatée / correction |
|---|---|
| Dossier nommé chromium71 mais V8 15.x | Mauvaise révision ; nouveaux checkouts aux SHA historiques |
| Ninja depot_tools ne trouve pas son binaire | `/usr/bin/ninja`, installé par ninja-build |
| Python 2 absent | paquet python2 Ubuntu 22.04 + lanceur isolé, sans modifier Python système global |
| Sync bloquée sur src | cache miroir involontaire ; cache désactivé et resolver vérifié null |
| Ancienne URL devtools-node-modules introuvable | miroir tiers au SHA exact, configuration alternative conservant DEPS |
| WebRTC « reference is not a tree » | fetch du SHA exact depuis le serveur officiel, intégration locale |
| Git affiche des milliers de suppressions dans un clone échoué | index/worktree vide issu de --no-checkout ; ne pas nettoyer aveuglément |
| GN ne trouve pas .gn | `--root=WORK/src` explicite |
| LASTCHANGE.committime absent | générateur lastchange original, avec source explicite |
| SIGSEGV d8 après SMOKE_OK | GDB : handler timer pendant exit ; adaptation d8 séparée puis répétitions |
| Node introuvable pendant optimize_webui | archives Node 8.9.1 et modules exacts, SHA-1 vérifiés, liens isolés |
| Bundler « absent » au staging | contrôle de notre script trop strict ; l'entrée .js existe, Node résout le nom sans extension |
| gperf / bison introuvables | paquets hôtes gperf et bison |
| gpu_lists_version.h absent | hooks ciblés GPU/Skia, pas une valeur inventée |
| Gardes générées contenant des tirets | notre staging absolu modifiait les gardes ; génération corrigée avec chemins relatifs |
| xpath_grammar.hh absent | wrapper renomme en .h ; adaptation séparée de l'include généré pour Bison récent |
| libXss.so.1 / libasound.so.2 absentes | paquets d'exécution libxss1/libasound2 ; aucune recompilation |

Ne pas recopier les essais ayant échoué comme une procédure obligatoire. Les commandes précédentes utilisent les scripts corrigés. Les rapports historiques restent dans `docs/grid5000-*.md` pour la traçabilité.

## 18. Dernier état validé et limites scientifiques

Sur le nœud ayant servi à cette reproduction :

```text
Workspace : /tmp/minethrottle71-work-rwkni3hv
Binaire   : /tmp/minethrottle71-work-rwkni3hv/src/out/MineThrottle71-config-cp8f0qce/chrome
Build     : /tmp/minethrottle71-work-rwkni3hv/chrome-build-nu3mbx0n/result.json
Runtime   : /tmp/minethrottle71-work-rwkni3hv/chrome-runtime-check-jyofi4aa/result.json
Version   : Chromium 71.0.3578.98
SHA-256   : bd6dcd7be07e09553d1d1eb75d2ea7a2719c828b115c93a2735762b460ec0d22
```

Cette empreinte identifie **ce build**, pas une valeur universelle attendue pour toute recompilation (chemins, métadonnées et environnement peuvent influer sur les binaires).

Validé : sources historiques, contextes/application des patches originaux, compilation d8 et chrome, douze signatures avec compteurs dynamiques sur fixtures, bibliothèques hôtes et affichage de version. Non validé : navigateur sur page Wasm, cycle de vie des renderers, douze compteurs sur tous les chemins de contrôle, temps CPU/vitesses, profils/seuils, défense, exécution effective et classification du dataset. La défense originale reste désactivée par défaut. Aucun échec d'exécution du dataset ne devra être classé bénin.

MineThrottle original : copyright 2020 The Chinese University of Hong Kong, licence MIT du dépôt. Chromium, V8 et leurs dépendances gardent leurs licences respectives. Les adaptations historiques séparées se trouvent dans `patches/chromium71/`, les originaux dans `patches/v8.patch` et `patches/content.patch`. Le papier, le plan et les inventaires sont conservés dans `docs/`.

Pour vérifier les scripts sur une machine ayant Python 3, sans compiler Chromium :

```bash
cd "$CODE"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```
