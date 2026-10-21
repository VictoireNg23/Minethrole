# Dépôt et résultats persistants sur Grid5000

Le dataset réel indiqué pour la prochaine phase est `Dataset_Dynamic/Data/Swamped_10_`. Il ne faut pas l'assimiler sans inventaire à `Dataset1_S`, étudié précédemment : imports, exports, points d'entrée et labels restent à vérifier pour ce chemin.

Organisation proposée sous le dossier partagé Dataset_Dynamic :

```text
Data/Swamped_10_/                     dataset existant, inchangé
tests/Minethrole-reproduction.XXXXXX/ nouveau clone Git des scripts et docs
resultats_minethrottle/
  run-DATEUTC-IDENTIFIANT/
    manifest.json
    provenance/                      versions/configurations, rapport de build
    logs/                            sorties des outils
    raw/                             .count, .stack, sorties par processus
    summaries/                       futurs CSV/JSON synthétiques
    fixtures/                        futurs hôtes/pages de test
```

Le dépôt n'a pas besoin de contenir une copie du dataset pour l'analyser : son chemin absolu suffit. Le nouveau clone est distinct du dossier MineThrottle existant et ne télécharge pas les sources Chromium. Les résultats volumineux restent hors Git ; les scripts/tests/documentations restent publiés sur la branche de travail. Une éventuelle publication de résultats synthétiques sur GitHub sera explicite, pas un ajout automatique de tous les fichiers bruts.

`scripts/prepare-experiment-directory.py` crée uniquement un nouveau sous-dossier de résultats, ses répertoires et un manifeste. Il relève le commit du code, copie les configurations de provenance et, si fourni, le rapport de compilation. Il ne parcourt ni n'exécute le dataset, ne lance aucun navigateur et ne modifie aucun fichier existant. Les résultats sont séparés de l'arbre du dataset. Les sous-dossiers créés par cette préparation root seront initialement privés ; les permissions d'un compte d'exécution dédié seront préparées séparément, sans chmod récursif du stockage partagé.

Le diagnostic sandbox indique user namespaces autorisés et une sonde non privilégiée réussie ; les binaires sont actuellement inaccessibles aux comptes non root à cause des parents /tmp privés, et aucun helper setuid sandbox n'est présent. Ne pas désactiver le sandbox pour contourner ces permissions. Un test synthétique non privilégié sera préparé après l'organisation des sorties.

La persistance des résultats et du code sur NFS ne rend pas les binaires /tmp persistants. Conserver le nœud et les répertoires temporaires pendant les essais ; une sauvegarde autonome du build, de ses ressources et dépendances devra être préparée séparément si nécessaire. Aucun binaire n'est déplacé ici et aucun test malveillant n'est lancé.
