# Renderer disparu : attacher avant sa sortie

Le rapport utilisateur confirme que le renderer PID 224470, initialement observé, n'existe plus dans /proc à trois secondes. Ce résultat établit sa disparition, pas encore son signal ou motif de sortie. Aucun module Wasm n'a été chargé dans ce test.

Le mode diagnostic renderer-startup utilise le switch Chromium 71 `--renderer-startup-dialog`. Le code historique `content/common/content_switches_internal.cc` a été relu à la révision exacte : sur Linux il installe un handler SIGUSR1 puis appelle pause ; `renderer_main.cc` le déclenche avant l'initialisation du renderer. GDB s'attache au renderer arrêté dès environ une seconde, puis lui transmet SIGUSR1 pour reprendre l'exécution sous contrôle du debugger. Les piles suivantes peuvent alors identifier un arrêt fatal avant la disparition. Ce n'est pas une modification du binaire ou une désactivation du sandbox, mais la temporisation et la phase d'attachement diffèrent du lancement normal.

Le SIGUSR1 de reprise est envoyé uniquement dans ce mode, au renderer sous le switch prévu ; aucun Wasm/timer MineThrottle n'est initialisé par la page. Ne pas réutiliser cette manipulation comme une commande de contrôle de la défense. Le test local vérifie que la reprise n'est pas appliquée aux captures normales ou au navigateur.

Si l'attachement est refusé, conserver l'erreur ; si le renderer ne s'arrête plus, la capture peut atteindre son timeout et rester diagnostique. Aucun de ces cas ne vaut réussite du navigateur. Les logs complets sont conservés, sans modification des restrictions ptrace globales. Le contrôleur finit en arrêt volontaire du groupe de test, et aucun dataset n'est exécuté.
