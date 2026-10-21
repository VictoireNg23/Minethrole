# SIGSYS confirmé dans pthread_create : identifier le syscall

L'utilisateur a extrait du journal renderer : `Program received signal SIGSYS, Bad system call.` La pile précédente se trouve dans pthread_create pendant l'initialisation du renderer. Cela confirme un arrêt par appel système interdit, mais le numéro manque encore. Sur Ubuntu 22.04/glibc récente, clone3 est une hypothèse plausible, pas encore une observation de ce test.

Le diagnostic GDB capture désormais `$_siginfo` et les registres orig_rax/rax/rip au point d'arrêt, avant la pile et le détachement. Les lignes utiles sont aussi extraites dans `gdb_captures[].signal_details` pour éviter de transmettre seulement la fin des longues piles. Le numéro et l'architecture de siginfo priment sur une déduction à partir du nom pthread_create.

Relancer uniquement le diagnostic de démarrage du renderer. Aucun changement du filtre seccomp, de la grammaire, des compteurs, des patches ou du dataset n'est effectué. Ne pas ajouter --no-sandbox ni autoriser globalement la création de processus avant d'avoir identifié le syscall. Une éventuelle adaptation devra être séparée, limitée et justifiée par la compatibilité avec la glibc hôte, avec sandbox toujours contrôlé après correction.
