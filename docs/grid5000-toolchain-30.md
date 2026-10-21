# GN validé ; examiner Clang et le sysroot avant préparation

Grid5000 confirme GN `1463 (e134e493)`, code 0, à `/tmp/minethrottle71-gn-jz9srypw/gn`. L'empreinte SHA-1 correspond au fichier historique : `1756964fe6b9f0a865accdf577ae46345847de3b`. SHA-256 de l'artefact reçu : `ac1c42d244af8dc0bff81b42a4c0ea0991774091d97870b46e8d615a5272f761`. Le checkout Chromium n'a pas été modifié. Ne pas remplacer ce binaire par un GN moderne sans preuve de nécessité.

La prochaine inspection lit les sources locales des téléchargeurs Clang, sysroot et binutils : versions épinglées, URL et opérations de remplacement/extraction. Les extraits sont numérotés et peuvent être discontinus ; ce sont des éléments d'analyse, pas une exécution des scripts. Les entrées amd64/x64 de sysroots.json sont aussi affichées si présentes.

Il reste à déterminer les artefacts historiques réellement demandés et leurs contrôles d'intégrité, puis à préparer leur récupération sans écraser de fichiers existants. Aucun appel global aux hooks n'est proposé. Les correctifs originaux ne sont toujours pas appliqués et la compilation n'est pas validée.
