# WebRTC : état sans checkout confirmé

L'inspection Grid5000 montre 7 623 statuts `D `, un index vide et uniquement `.git` dans la cible. Cet état correspond à un clone sans checkout, pas à des fichiers locaux présents qu'il faudrait écraser.

Le script d'intégration accepte désormais cette exception strictement vérifiée : toutes les lignes de statut doivent être des suppressions indexées (`D  chemin`), `git ls-files --stage` doit être vide et le répertoire ne doit contenir que `.git`. Tout autre état non propre reste refusé. Il importe ensuite le SHA exact depuis le dépôt temporaire déjà vérifié et effectue le checkout détaché sans force. Aucun reset, nettoyage, déplacement ni modification des sources partagées n'est nécessaire.

Un test Git local reproduit un véritable clone `--no-checkout` puis vérifie que l'intégration peuple le fichier attendu et laisse un statut propre. Le test de refus d'un fichier non suivi reste présent. La validation du checkout réel sur Grid5000 reste à obtenir avant reprise de gclient.
