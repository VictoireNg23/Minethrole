# Capture GDB : renderer non sélectionné

Le rapport `browser-ready-2ssjsi4p` ne contient qu'une capture navigateur. Sa pile dans la boucle d'événements ne révèle pas à elle seule la cause du chargement bloqué. La pile du renderer manque.

La sélection précédente exigeait que `/proc/PID/exe` soit lisible et identique au binaire, ce qui peut exclure un renderer sandboxé non dumpable. Cette explication reste une hypothèse tant que l'erreur précise n'a pas été capturée. La sélection utilise désormais la ligne de commande des seuls descendants du processus lancé, avec correspondance exacte du chemin du binaire et choix explicite d'un navigateur et d'un renderer. Elle ne dépend plus de la lecture du lien exe. Les erreurs de lecture et l'absence de sélection sont rapportées, et GDB conserve tout refus ptrace au lieu de contourner la protection.

Un test couvre la sélection des deux rôles et l'exclusion du zygote ou d'un chemin de binaire seulement préfixé par le nom attendu. Relancer le même diagnostic CDP/GDB ; aucun changement de sandbox, permissions, binaire ou patch n'est demandé. L'essai reste une page locale sans Wasm et s'arrête volontairement. Conserver les anciens journaux.
