# Page normale réussie ; premier compteur Wasm dans Chromium

Le rapport utilisateur `raw/browser-ready-nxin4hrj/result.json` confirme sortie 0, sans timeout, marqueur DOM présent, renderer UID 998 avec Seccomp=2 et NoNewPrivs=1. Le binaire corrigé et `glibc.pthread.rseq=0` sont identifiés. Le message GPU Lost UI shared context n'a pas empêché cette exécution ; il n'était pas à lui seul la cause démontrée des essais précédents.

Le nouveau mode `--wasm-counter-case active` charge uniquement une page locale avec un module arithmétique bénin, sans imports : signature originale du compteur 0, 20 000 appels, résultat arithmétique contrôlé, courte attente pour le timer réel. Un rapport de page normale réussi du même staging et de la même configuration glibc est exigé. Les modes dormant/négatif sont disponibles pour les contrôles ultérieurs.

Le contrôleur distingue la preuve DOM d'exécution et la mesure par les fichiers originaux .count. Il copie les artefacts .count/.stack/.txt/.asmjs accessibles dans le répertoire de session vers le nouveau dossier raw du run persistant. Une sortie correcte sans lignes de mesure ne vaut pas succès : absence d'artefact, crash, trap et timeout restent failed_or_unmeasurable, jamais un verdict bénin. Aucun fichier Dataset1_S n'est exécuté.

Limite à vérifier : le patch original ouvre directement des fichiers dans le renderer et utilise SIGALRM/clock_gettime. Ces opérations peuvent être refusées par le sandbox standard. Cette première tentative garde le sandbox et rapporte ce blocage éventuel ; elle ne le contourne pas. Les commandes historiques des auteurs utilisaient --no-sandbox, ce qui devra être distingué si une adaptation de collecte ou une isolation extérieure devient nécessaire. Le correctif d'arrêt d8 ne protège pas la durée de vie des instances du renderer.

Les profils, vitesses, seuils et défense restent non validés. Ce test est la vérification d'un compteur, pas une détection de minage : la fixture est bénigne bien qu'elle contienne une signature.
