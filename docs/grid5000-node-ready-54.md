# Node et bundler intégrés ; reprendre Chromium

Le rapport Grid5000 `/tmp/minethrottle71-node-stage-7rm44qda/node-stage-validation-rh3929o5/result.json` confirme `historical_node_and_webui_staged_and_linked`, Node `v8.9.1` code 0 et polymer-bundler `3.1.1` avec aide code 0. L'appel sans extension utilisé par Chromium est résolu par Node sans alias ni modification du paquet. Les liens attendus vers Node et node_modules sont créés.

Reprendre la compilation incrémentale `--target chrome` dans le répertoire GN patché existant avec le rapport d'adaptation d8, 16 tâches, arrêt à la première erreur et timeout 900 secondes. Ne pas supprimer les objets ni les répertoires de staging : les liens en dépendent. Le script de build conserve un nouveau journal et un nouveau rapport à chaque tentative.

L'aide du bundler confirme son démarrage, pas encore le succès de la génération complète des ressources WebUI. Si une autre dépendance manque, analyser le nouvel échec avant de poursuivre. Aucun changement des patches n'est nécessaire pour lever le blocage Node observé. La compilation complète, l'exécution du navigateur et les calculs de décision restent à valider.
