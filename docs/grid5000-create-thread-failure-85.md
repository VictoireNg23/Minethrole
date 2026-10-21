# Tests BPF : deux succès, CreateThread échoue

Le rapport `raw/sandbox-native-5mia0u69/result.json` contient les trois tests exécutés : Clone3ReturnsEnosys et DisallowedCloneFlagCrashes passent, CreateThread échoue car le sous-processus ne termine pas normalement. Le code global est 1. Le retour ENOSYS demandé fonctionne donc dans ce test, et la restriction clone contrôlée reste effective ; la création de thread n'est pas encore compatible avec l'environnement hôte.

Le mode `--diagnostic-gdb` du contrôleur natif lance uniquement CreateThread sous GDB, lui-même sous le compte dédié. `follow-fork-mode child` suit le sous-processus qui installe la politique BPF ; au prochain arrêt, siginfo, numéro de syscall et piles sont conservés. Aucun filtre n'est assoupli, aucune hypothèse de syscall supplémentaire n'est transformée en patch sans observation. Une erreur ptrace, un timeout ou un arrêt non fatal reste un résultat diagnostique, pas un succès.

La capture complète reste dans stdout.log du nouveau dossier raw/sandbox-native-*. Les lignes de signal sont aussi extraites dans signal_details. Un éventuel XML incomplet après détachement n'est pas interprété comme réussite ; les tests normaux devront tous être rejoués après résolution. Aucun navigateur ou module du dataset n'est lancé.
