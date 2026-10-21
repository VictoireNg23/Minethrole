# Compteur 0 observé ; validation des douze signatures

L'extrait Grid5000 de `counter-smoke-r6mr70ax/result.json` confirme : contrôle sans signature exécuté, douze compteurs nuls ; signature active 0 exécutée 20 000 fois, compteur 0 exactement à 20 000 et onze autres à zéro. Chaque cas affiché fournit six lignes de mesure. Le statut global et le cas dormant ne sont pas visibles dans l'extrait : le nouveau wrapper exige le statut global `counter_smoke_passed` du rapport complet avant la suite.

`test-chromium71-counters.py --all-signatures --previous-smoke-report RAPPORT` et `d8-all-signatures.js` étendent le test à 24 processus : pour chacun des douze compteurs, un module dont la fonction est instanciée sans appel, puis le même module appelé 20 000 fois. Chaque corps contient exactement une fenêtre de cinq opcodes simples, donc aucun chevauchement d'une autre fenêtre active. Six constantes fournissent les opérandes. Les signatures et leurs clés base 123 sont vérifiées par un test local contre `config/original.json`. Le résultat arithmétique est aussi contrôlé dans chaque exécution.

Attendu : tous les compteurs nuls sans appel ; en cas actif, exactement 20 000 sur le compteur correspondant et zéro sur les onze autres. Les journaux sont séparés, sans exécution du dataset ni activation de la défense. Ce test n'est pas une classification de fichiers : la présence d'une signature dans ces modules bénins démontre l'instrumentation, pas un verdict de minage.

Les maxima lus dans `.count` valident les valeurs finales attendues si les échantillons les observent ; l'absence d'échantillon est un résultat non mesurable. Les profils, vitesses, seuils, branches non parcourues, resets de fenêtre et Chromium complet restent à valider séparément.
