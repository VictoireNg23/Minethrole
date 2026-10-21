# Neuf contrôles réussis après adaptation d'arrêt

L'utilisateur confirme le rapport `/tmp/minethrottle71-work-rwkni3hv/counter-smoke-gq1h0mbb/result.json` : statut global `counter_smoke_passed`, neuf cas présents, neuf `passed`. Le rapport précédemment reçu identifie le binaire SHA-256 `47e4eba6ed766e77cc6ef051c649a73b6448c95184ff34a617a0f3ac0a593b0e` et l'adaptation d'arrêt distincte. Trois cas dormants, trois négatifs et trois actifs ont donc satisfait les compteurs et le code de sortie attendus.

Le SIGSEGV initial n'est plus observé dans ces répétitions. Il ne s'agit pas d'une preuve générale d'absence de défaut de durée de vie, notamment pour plusieurs instances, workers ou Chromium.

Étape suivante : exécuter `test-chromium71-counters.py` avec `d8-all-signatures.js`, `--all-signatures --repeat 3` et le rapport complet précédent comme prérequis. Soit 72 processus indépendants : pour chacun des douze compteurs, trois cas dormants et trois actifs. Les séquences originales sont inchangées ; chaque cas actif attend 20 000 incréments uniquement sur le compteur associé. Le binaire est vérifié contre le rapport du rebuild corrigé.

Profils, vitesses, règles de décision, défense et Chromium complet restent non validés. Aucun module du dataset n'est exécuté par cette étape.
