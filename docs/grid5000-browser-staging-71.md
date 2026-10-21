# Hôtes analysés ; préparer le test navigateur synthétique non privilégié

Le rapport utilisateur `hosts-hfglmerd/summary.json` confirme les 175 fichiers identiques par multiensemble SHA-256 à Dataset1_S. Groupes indicatifs superposables : Emscripten 100, WASI 8, bindings JS 19, Go 2, sans imports 8 ; 142 comportent au moins un namespace non résolu. Cela ne signifie pas que tous ces fichiers sont exécutables ni que leurs points d'entrée miniers sont connus. Aucun module du dataset n'est exécuté.

Le script `stage-chromium71-browser-test.py --run RUN --create-dedicated-user` prépare seulement le premier test synthétique. Il crée explicitement le compte système `minethrottle-test` sans login/home et refuse de réutiliser un compte homonyme déjà présent. Il vérifie l'empreinte du binaire, copie les fichiers d'exécution du build dans un nouveau dossier local /tmp, sans obj/gen, et crée un espace de session appartenant au compte dédié. Les fichiers du navigateur copiés restent root-owned et non modifiables par ce compte.

Seules les permissions de ce nouveau staging sont définies. Aucun chmod/chown des sources ou du stockage partagé, aucun déplacement des originaux. Les résultats/provenances de préparation sont écrits dans un nouveau fichier du run persistant. La copie des ressources nécessaires sera validée lors du lancement réel ; cette sélection n'est pas présentée comme un paquet Chromium distribuable complet. Les bibliothèques système restent fournies par l'hôte.

Le script ne démarre pas Chromium, ne désactive pas le sandbox, ne lit pas les fichiers du dataset et ne crée pas de helper setuid. La sonde de namespace non privilégiée a réussi sur le nœud ; le sandbox Chromium lui-même reste à tester. Si la préparation échoue après création du compte, elle indique les éléments créés : conserver le rapport et analyser avant reprise, sans supprimer automatiquement compte ou dossiers.

Le futur test navigateur conservera ses journaux et compteurs sur le run partagé après exécution dans la session locale ; aucun module malveillant ne sera lancé pour cette validation initiale. L'isolation et les limites des expériences du dataset nécessitent une préparation distincte.
