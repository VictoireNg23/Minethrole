# Chromium 71 compilé avec les patches originaux

Le rapport Grid5000 `chrome-build-nu3mbx0n/result.json` confirme `chrome_build_passed`, code 0, dernière reprise en 396 étapes et 50,22 secondes. Binaire présent, SHA-256 `bd6dcd7be07e09553d1d1eb75d2ea7a2719c828b115c93a2735762b460ec0d22`. Cette réussite valide la compilation de Chromium et des patches V8/content, pas leur fonctionnement complet en navigateur.

Provenance : Chromium 71.0.3578.98, V8 7.1.302.31, patches MineThrottle originaux inchangés. Adaptations séparées : arrêt du timer avant teardown du shell d8 uniquement ; renommage de l'include du parseur Blink pour Bison 3.8.2. Le correctif d8 n'est pas une correction du cycle de vie des renderers Chromium.

Prochaine étape : `check-chromium71-runtime.py WORKSPACE BUILD_REPORT`. Il vérifie le SHA-256 du binaire, conserve le résultat complet de ldd et n'exécute `chrome --version` que si les dépendances partagées sont résolues. Il ne charge aucune page, ne lance aucun module Wasm et n'ajoute pas --no-sandbox. Les bibliothèques nécessaires à la compilation dans le sysroot ne garantissent pas leur présence à l'exécution sur l'hôte.

Après résultat confirmé, préparer une page synthétique locale et les conditions d'exécution non privilégiée avec sandbox, avant toute expérience du dataset. La validation des 72 cas d8 porte sur les compteurs ; les vitesses, profils, seuils et activation de la défense restent à vérifier. La reproduction scientifique complète n'est donc pas encore achevée.
