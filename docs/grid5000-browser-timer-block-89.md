# Instanciation Wasm bloquée par le timer original

Le rapport Grid5000 `raw/browser-ready-vs130tw1/result.json` montre le renderer arrêté dans `v8::internal::wasm::SetTimer()` : `setitimer`, syscall x86_64 38 (affiché 0038), est refusé par seccomp. Le navigateur principal sort avec 0 malgré la terminaison anormale du renderer. Aucun marqueur d'exécution, aucune ligne de compteur et aucun artefact original ne permettent de valider le test actif. Aucun module du dataset n'a été exécuté.

Le correctif clone3 et la désactivation locale de rseq ont permis la page simple ; ils ne résolvent pas les besoins du timer du patch original. Ne pas convertir ce résultat en succès et ne pas autoriser globalement les syscalls. `SetTimer` ouvre aussi directement un fichier PID.count avant d'armer le timer ; l'absence de fichier exige de vérifier également cette collecte avant de choisir une adaptation.

`scripts/inspect-chromium71-timer-block.py WORKSPACE RAPPORT_ECHEC` lit les extraits des politiques présentes, le code V8 et stdout conservé, puis écrit uniquement un nouveau rapport persistant à côté des autres essais. Il ne lance aucun navigateur et ne modifie aucun source. Cette inspection prépare une décision documentée sur la collecte et les permissions nécessaires ; elle ne constitue pas une validation.
