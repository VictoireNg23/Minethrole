# Incompatibilité de nom d'en-tête généré avec Bison récent

Le build `chrome-build-h7z4cs0t` échoue après 235,29 secondes : le C++ généré inclut `xpath_grammar.hh`, absent. Le wrapper historique relu à la révision exacte produit d'abord `.hh`/`.hpp`, lit et supprime ce fichier, puis écrit `xpath_grammar.h` avec gardes. Les Bison récents incluent explicitement le nom temporaire dans le `.cc`, que ce wrapper ne met pas à jour. Ce mécanisme explique l'erreur observée ; la grammaire et MineThrottle ne sont pas impliqués.

L'adaptation séparée `patches/chromium71/blink-bison-generated-header-include.patch` met à jour uniquement cet include dans le C++ généré pour correspondre au nom final `.h`. Elle conserve la commande Bison, la grammaire et le reste du parseur généré. Le wrapper modifié est une dépendance de l'action Ninja : la reprise devrait régénérer le parseur sans supprimer manuellement les sorties. Un test exécute le bloc ajouté sur un petit C++ synthétique et vérifie la conservation du reste.

Le script d'application contrôle le HEAD Chromium, l'empreinte du patch, l'absence de modifications du wrapper et le contexte d'application. Il conserve une copie préalable et un diff. Les patches originaux MineThrottle ne sont pas modifiés. Les mentions de licence BSD du wrapper sont conservées. Le fichier historique a été lu depuis le miroir officiel Chromium GitHub à la révision exacte, sans téléchargement d'un arbre Chromium ou compilation dans Codex.

Attendre le résultat de l'application avant la reprise du build. Une réussite du correctif ne prouve pas la compatibilité complète du parseur Bison 3.8.2 ; toute erreur supplémentaire devra être examinée. Aucun affaiblissement de Werror ni remplacement de grammaire n'est effectué.
