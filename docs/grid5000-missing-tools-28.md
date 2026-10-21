# Outils historiques absents après synchronisation sans hooks

L'inspection utilisateur indique l'absence des chemins testés pour le sysroot, Clang historique, GN et Node, ainsi que plusieurs paquets de développement système. L'espace local disponible est de 795 967 541 248 octets. Ces absences sont compatibles avec une synchronisation sans hooks ; elles ne constituent pas un échec de synchronisation.

L'extrait reçu ne contient que la fin des hooks V8, pas les actions principales de Chromium. Avant de choisir les téléchargements, `scripts/summarize-chromium71-hooks.py` résume les noms, conditions et actions de tous les hooks des deux DEPS avec l'AST Python, sans exécuter leur code. Les expressions non littérales sont conservées comme texte, et les conditions ne sont pas évaluées. Cela permet de transmettre une sortie compacte sans les commentaires volumineux.

Ne pas déduire des paquets absents une liste d'installation universelle : le sysroot historique peut fournir une partie des bibliothèques de compilation. L'installation des bibliothèques hôtes ou d'exécution doit être préparée après examen des scripts et options historiques. Aucun hook global, script d'installation historique ou build n'est encore lancé.
