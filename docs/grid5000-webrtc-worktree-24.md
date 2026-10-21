# Intégration WebRTC refusée : inspecter avant toute correction

L'exécution `webrtc-integrate-w7od7tfr` a refusé la cible parce que `git status --porcelain=v1 --untracked-files=all` n'est pas vide. Le refus intervient avant le fetch local et le checkout. Aucun succès d'intégration n'est établi.

Le script `inspect-webrtc-worktree.py` lit HEAD, l'arbre, le statut, l'index et les entrées de premier niveau. Le statut et l'index sont limités aux 60 premières lignes, avec le total ; les catégories de statut sont comptées sur la sortie entière. Les rafraîchissements optionnels de l'index, fsmonitor et la récupération implicite sont désactivés. Il ne parcourt pas les sources partagées.

Une cible issue d'un clone `--no-checkout` peut présenter un index ou un arbre de travail incomplet. Il faut le vérifier dans les résultats, sans assimiler automatiquement toutes les différences à des fichiers jetables. Aucune suppression, aucun déplacement et aucune réinitialisation ne sont proposés à ce stade. Attendre les résultats de l'inspection pour choisir entre une réparation non destructive et une nouvelle cible de travail.
