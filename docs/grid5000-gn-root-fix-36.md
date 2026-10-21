# Correction du répertoire source GN

La première génération s'arrête immédiatement avec `Can't find source root`. Le lanceur `with-tools.sh` positionne son processus à la racine du workspace pour les opérations gclient. Cela annule le cwd `src` demandé par le wrapper de génération GN. L'erreur relève de notre orchestration, pas d'une incompatibilité de Chromium 71.

La commande GN reçoit désormais explicitement `--root=WORKSPACE/src`. Les arguments de build des auteurs restent inchangés. Le script vérifie aussi la présence de `src/.gn` et crée toujours un nouveau répertoire de sortie ; l'essai échoué est conservé. Aucun lanceur partagé ni source des auteurs n'est modifié. Le test vérifie le passage de la racine en un argument distinct, y compris avec des espaces dans le chemin.

Relancer uniquement le script de configuration corrigé, attendre son journal et ne pas lancer Ninja. Aucun succès de génération ou de compilation n'est encore établi.
