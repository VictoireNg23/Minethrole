# Sysroot validé et intégration des outils par liens

Le rapport Grid5000 `minethrottle71-sysroot-stage-vgj9pyhu/result.json` confirme l'extraction du sysroot historique, avec 8 395 entrées, 505 liens et 308 616 896 octets de fichiers. Aucun fichier Chromium n'a été modifié. GN et Clang ont précédemment démarré avec leurs versions historiques attendues.

Le script `link-chromium71-tools.py WORKSPACE GN_REPORT CLANG_REPORT SYSROOT_REPORT` vérifie les rapports, revérifie l'empreinte GN et crée uniquement les liens suivants dans le workspace isolé :

- `src/buildtools/linux64/gn` vers le GN préparé ;
- `src/third_party/llvm-build/Release+Asserts` vers Clang préparé ;
- `src/build/linux/debian_sid_amd64-sysroot` vers le sysroot préparé.

Toutes les destinations sont vérifiées avant la création du premier lien. Toute destination occupée différente est refusée ; un lien identique est accepté pour une reprise. Aucun contenu existant n'est remplacé ou déplacé. Le script ne lance ni hook, ni génération GN, ni compilation. Le test local vérifie l'idempotence et la préservation d'un fichier existant.

Ces liens dépendent des répertoires temporaires : les conserver pendant les expériences. Ils ne sont pas ajoutés à Git, seulement le script et la documentation le sont. Les outils supplémentaires (binutils, Node), fichiers générés et dépendances nécessaires devront être vérifiés avant la génération du build. Les patches originaux restent inchangés et non appliqués.
