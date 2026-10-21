# Grid5000 : snapshot historique prêt, premier test de gclient

## Préparation confirmée par l'utilisateur

Le script corrigé a terminé avec succès sur le nœud :

```text
Prepared snapshot: /tmp/minethrottle71-tools-li2ldh40/depot_tools
Environment file: /tmp/minethrottle71-tools-li2ldh40/env.sh
Launcher: /tmp/minethrottle71-tools-li2ldh40/with-env.sh
Python 2.7.18
1.10.1
PASS: snapshot and Python/Ninja launchers prepared. Historical depot_tools compatibility NOT validated.
```

Les quatre liens internes vers `support/chromite_wrapper` ont été conservés. L'ancien depot_tools et le dossier partiel précédent restent intacts. Le SHA candidat reste `c6a8d114b060f5f68637e8897712a24252402377`.

## Prochaine action : gclient --help, sans synchronisation de sources

`scripts/check-historical-gclient.py` lance uniquement le gclient du snapshot par le lanceur isolé, avec l'argument `--help`. Il ne modifie pas l'environnement du terminal appelant. La commande peut déclencher les téléchargements nécessaires au bootstrap CIPD/vpython historique dans la copie isolée et ses caches habituels ; elle n'est donc plus une simple inspection hors ligne. Elle n'exécute ni fetch Chromium, ni gclient sync, ni hooks, ni construction.

```bash
python3 /chemin/vers/check-historical-gclient.py \
  /tmp/minethrottle71-tools-li2ldh40
```

L'auto-update de depot_tools reste désactivé par le lanceur préparé. Aucun VPYTHON_BYPASS, contournement TLS, modification de checksum ou clé inventée n'est utilisé. Le script refuse de continuer si un VPYTHON_BYPASS non vide est hérité. Il ne modifie pas la configuration ou le code historique pour contourner un échec.

Une nouvelle sous-directory `gclient-help-check-...` conserve stdout.log, stderr.log et result.json. La commande s'exécute depuis ce nouveau dossier, avec stdin fermé pour éviter une demande interactive bloquante. Elle dispose de 180 secondes par défaut. En cas de délai expiré, seul le groupe de processus créé pour ce test est arrêté ; aucun service ou autre tâche utilisateur n'est arrêté. Les éventuels fichiers de bootstrap restent conservés pour analyse.

Les statuts sont distincts : `help_completed`, `failed`, `timeout`, `help_output_not_recognized`. Le code de sortie réel du processus est enregistré ; un zéro sans aide reconnaissable n'est pas traité comme un succès. L'affichage limite chaque journal aux 20 000 derniers caractères si nécessaire, mais le fichier complet demeure sur le nœud.

Transmettre la sortie complète et le chemin des journaux. Un succès validera seulement le démarrage et l'aide de gclient. Il ne prouvera pas l'accès à toutes les dépendances historiques, le fonctionnement de la synchronisation, la compatibilité C++ ou l'exécution des compteurs. Un échec permettra de distinguer dépendance à .git, interpréteur, bootstrap réseau ou autre cause avant toute correction ciblée.

## Tests locaux

Les trois nouveaux tests utilisent un faux gclient local : succès avec aide, échec/absence d'aide malgré code zéro, et timeout explicite. Aucun gclient historique réel, bootstrap distant ou Chromium n'a été exécuté dans Codex.
