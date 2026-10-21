# Archives reçues et préparation de Clang

Le sysroot reçu (62 001 608 octets) correspond au SHA-1 historique `e7c53f04bd88d29d075bfd1f62b073aeb69cbe09`, SHA-256 `6964fc4327837d4eab3799a29d843b9cdd6b68edfdce170e1a40ca723f4ad6c5`. Clang reçu a pour SHA-256 `25e795bb6464013d0a5b6c84bd31d0b04ab4f1d58b1a16821c474b1139da979f` (empreinte de provenance, sans empreinte indépendante attendue). Archives conservées à `/tmp/minethrottle71-toolchain-download-zr92kd3u`.

Le script de staging vérifie que les deux fichiers correspondent toujours aux SHA-256 du rapport, valide le manifeste Clang et l'extrait dans un nouveau répertoire. Il refuse les chemins sortants, doublons, liens absolus, cycles, cibles absentes et entrées sous un lien symbolique. Seuls les fichiers, répertoires et liens symboliques internes sont acceptés ; aucun propriétaire ni bit setuid n'est restauré. Seul `clang --version` est lancé, sans compilation.

Le sysroot reste non extrait : ses 505 liens nécessitent une politique adaptée. Le script écrit leur liste complète dans son nouveau répertoire et affiche des exemples ainsi que les liens absolus éventuels. Aucun fichier du checkout Chromium ni des sources partagées n'est modifié. Attendre les sorties avant d'intégrer ces outils ou d'extraire le sysroot.
