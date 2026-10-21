# Vérifier la disponibilité du commit WebRTC exact

Les clones locaux inspectés ne contiennent ni le commit `0ba24191ee90c70679d2452363676c2d65b6b751`, ni son arbre. Les sources originales sont non superficielles, mais récupérer les branches ne garantit pas de récupérer un commit historique qui n'est plus accessible depuis ces branches.

Prochaine opération : `python3 scripts/fetch-webrtc-exact.py`. Elle crée un nouveau dépôt temporaire et demande au serveur officiel uniquement le SHA requis avec `--depth=1 --no-tags`. Elle ne modifie aucun checkout existant, n'applique aucun patch et ne relance pas gclient. Le dépôt et les journaux sont conservés même en cas d'échec. Chaque commande est limitée à 180 secondes. Le volume reste celui de l'arbre WebRTC et de ses objets nécessaires, pas de tout son historique ; une taille exacte n'est pas connue à l'avance.

Le script vérifie le SHA de FETCH_HEAD, la présence de l'arbre et l'intégrité avec fsck. Les messages de branche non née ou de commit dangling peuvent apparaître : aucun checkout ni branche n'est créé. Un succès confirme seulement la récupération des objets, pas la préparation des dépendances ni la compilation. Attendre la sortie avant de préparer l'intégration dans le nouveau workspace. En cas d'échec, analyser la réponse du serveur avant de chercher un miroir conservant le même SHA.
