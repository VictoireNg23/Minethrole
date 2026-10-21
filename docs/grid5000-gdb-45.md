# Crash dormant reproduit ; capture de pile nécessaire

Les neuf répétitions Grid5000 montrent deux SIGSEGV sur trois cas dormants, après le marqueur de fin du fixture ; les trois cas négatifs et trois cas actifs finissent avec code 0. Ce résultat confirme l'intermittence et bloque la validation globale, sans démontrer encore la cause. GDB est absent du nœud.

Installer seulement le debugger sur le nœud via `apt-get install --no-remove --no-install-recommends gdb`, puis vérifier `gdb --version`. Ne pas rafraîchir aveuglément le système ni accepter une suppression de paquets. L'installation peut ajouter/mettre à jour des dépendances système indiquées par APT ; en cas d'erreur, transmettre la sortie avant toute autre correction. Cette opération ne touche pas aux sources partagées ou aux patches.

Le diagnostic accepte `--gdb-only` pour ne pas répéter les neuf exécutions directes. Il conserve le passage normal de SIGALRM et capture les piles des threads, le symbole et l'instruction au PC arrêté. Une fin normale sous GDB ne suffit pas à lever le défaut ; répéter la capture si nécessaire, en conservant les essais précédents. Aucun nouveau succès de test n'est déclaré parce qu'une répétition isolée passe.
