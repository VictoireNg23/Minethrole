# Adaptation Bison appliquée ; reprise avec provenance

Le rapport Grid5000 `bison-include-fix-fdbv12h8/result.json` confirme l'application de l'adaptation séparée SHA-256 `0e9df1fc7f21ef392fef3dd1a27e603d2149d22eb57f501084a65acd34e3639f`. Les patches originaux restent inchangés. La compilation n'est pas encore retestée.

Le wrapper de build accepte `--bison-adaptation-report`. Il vérifie le statut, l'empreinte de l'adaptation et l'égalité du diff courant du wrapper avec le diff enregistré lors de l'application. Ces éléments sont conservés dans le nouveau rapport, à côté de l'adaptation d'arrêt d8. Reprendre la cible chrome dans le même répertoire, 16 tâches et timeout 900 secondes. Le changement du script de génération devrait provoquer la régénération Ninja du parseur ; aucun fichier généré ni objet n'est supprimé manuellement.

Attendre le résultat réel, notamment la disparition de l'include `.hh` manquant, avant de considérer cette adaptation validée. Aucun navigateur ne sera lancé. Une nouvelle erreur doit être traitée à partir du nouveau journal, sans supposer qu'elle implique MineThrottle.
