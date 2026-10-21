# Contrôle de point d'entrée corrigé ; réutiliser le staging

L'inspection confirme `polymer-bundler` 3.1.1 avec `bin.polymer-bundler = lib/bin/polymer-bundler.js`. Notre premier contrôle cherchait seulement un fichier physique sans extension et a arrêté l'intégration, malgré une extraction et un Node valides. Aucun lien n'a été créé. Ne pas conclure à une archive incomplète ou remplacer la dépendance par npm.

Le script de staging accepte `--reuse-stage-report` uniquement pour cet état d'arrêt précis, avec liste des liens vide. Il conserve les anciens fichiers et rapports, crée un nouveau sous-répertoire de validation, vérifie l'entrée déclarée par package.json, puis teste `node CHEMIN_SANS_EXTENSION --help`, conformément à l'invocation observée dans le build. Node peut résoudre le suffixe `.js` ; cette étape le vérifie avec le binaire historique au lieu de supposer le succès. Aucun alias ni changement du paquet n'est introduit.

Si l'aide fonctionne et le code de sortie est nul, les deux liens sont créés aux destinations encore absentes. Sinon, conserver le journal et analyser avant toute intégration. L'aide ne valide pas encore la génération complète des ressources WebUI. Le répertoire réutilisé est `/tmp/minethrottle71-node-stage-7rm44qda`, rapport initial conservé intact.
