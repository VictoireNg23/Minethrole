# Clang validé ; extraction isolée du sysroot

Grid5000 confirme Clang `8.0.0 (trunk 344066)`, cible `x86_64-unknown-linux-gnu`, code 0 dans `/tmp/minethrottle71-clang-stage-ytr8ddcf/clang`. Les 505 liens du sysroot sont relatifs ; aucun lien absolu n'a été observé. Ce test vérifie le démarrage de Clang, pas encore sa capacité à compiler Chromium.

`scripts/stage-chromium71-sysroot.py RAPPORT_TELECHARGEMENT` revérifie le SHA-1 historique puis extrait dans un nouveau répertoire temporaire. La validation complète du manifeste précède toute extraction : chemins sortants, doublons, types spéciaux, liens absolus, entrées sous un lien et traversées de liens intermédiaires sont refusés. Le volume décompressé des fichiers est limité à 4 Gio. Les liens relatifs internes peuvent être pendants, ce qui est conservé sans les remplacer par des fichiers hôtes. Aucun propriétaire ni bit setuid n'est restauré.

L'extraction ne remplace pas le sysroot du checkout, n'installe aucun paquet, ne modifie aucune source partagée et ne lance pas de compilation. Les sorties et les éventuels fichiers partiels restent dans le nouveau répertoire en cas d'échec. Attendre le résultat avant d'intégrer GN, Clang et le sysroot aux chemins de compilation. Les tests locaux couvrent une racine tar `.` avec un lien interne pendant et le refus d'une cible sortante.
