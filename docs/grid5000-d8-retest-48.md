# d8 corrigé reconstruit ; répétition du test complet

Grid5000 confirme la recompilation incrémentale en deux étapes, code 0 après 8,14 secondes. Rapport : `d8-build-_sdvyn2t/result.json`. SHA-256 du nouveau d8 : `47e4eba6ed766e77cc6ef051c649a73b6448c95184ff34a617a0f3ac0a593b0e`. Le rapport référence l'adaptation d'arrêt séparée. La correction du crash n'est pas encore validée à l'exécution.

Le smoke test accepte maintenant `--repeat 3` : neuf processus distincts (trois dormants, trois négatifs, trois actifs), chacun avec contrôle des compteurs et du code de sortie. Cela reproduit les trois répétitions du diagnostic initial avec une vérification des valeurs en plus. Un signal après SMOKE_OK reste un échec, même avec les compteurs attendus. Le test local vérifie explicitement ce refus.

Le wrapper calcule le SHA-256 du binaire avant le test et le compare au rapport de build si l'empreinte y figure ; il revérifie à la fin que le binaire n'a pas changé. La provenance du build, l'adaptation et les répétitions sont enregistrées dans le nouveau rapport, avec les anciens rapports conservés. Aucun dataset ni défense n'est exécuté.

Neuf succès observés apporteraient une validation limitée du scénario reproduit, pas une preuve d'absence de tous les défauts de durée de vie. Après résultat complet, poursuivre les douze signatures. Chromium complet et son cycle de vie restent à valider séparément.
