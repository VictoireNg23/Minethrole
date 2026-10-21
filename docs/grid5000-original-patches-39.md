# GN non patché validé ; appliquer les patches originaux

Le rapport Grid5000 `gn-config-a4m2ev2z/result.json` confirme la génération GN, code 0 : 10 601 cibles depuis 1 756 fichiers, avec les arguments originaux. Cela valide la configuration non patchée, pas la compilation.

Prochaine étape : `apply-chromium71-original-patches.py WORKSPACE GN_REPORT`. Le script utilise les copies originales `v8.patch` et `content.patch` conservées à la racine du workspace, contrôle leurs SHA-256, les HEAD historiques et l'absence de différences indexées/non indexées sur les fichiers concernés. Il refuse les fichiers concernés qui sont des liens symboliques. Il vérifie les deux patches avec `git apply --check` avant de commencer les écritures, puis applique sans force ni correction automatique des espaces. `content.patch` est appliqué depuis `src` avec `--directory=content` ; V8 depuis son dépôt propre.

Les patches de référence eux-mêmes restent inchangés. Seuls les fichiers sources ciblés du workspace isolé sont modifiés, comme prévu par la reproduction originale. Aucun reset, nettoyage, déplacement, hook ou build n'est exécuté. En cas d'échec après le premier patch, le rapport indique explicitement les patches déjà appliqués : ne pas relancer aveuglément ou annuler automatiquement ; examiner le résultat.

Après confirmation de l'application, il faudra régénérer GN sur les sources patchées puis préparer une première compilation contrôlée. Le script de configuration actuel décrit encore son résultat comme non patché : cette distinction devra être adaptée avant sa réutilisation. Les signatures, compteurs, formules, profils et seuils ne sont pas modifiés par cette étape.
