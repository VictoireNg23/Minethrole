# Renderer absent de la sélection à trois secondes : vérifier son identité et son état

Le rapport utilisateur `browser-ready-xeeadsun` sélectionne uniquement le navigateur, sans erreur de lecture de ses descendants au moment de la capture. La seule liste des captures ne permet pas de conclure si le renderer a quitté, est zombie, a changé de parent ou n'est plus accessible.

Le diagnostic conserve désormais PID, UID et starttime /proc du renderer dès sa première observation. À la capture, il vérifie son état indépendamment de l'arbre courant, rapporte PPid/State et la présence dans les descendants, et n'attache GDB que si l'identité (UID/starttime) correspond toujours et si la commande reste celle d'un renderer du binaire de test. Cela évite de confondre une réutilisation de PID ou un reparentage avec le processus initial. Une disparition ou un refus d'accès devient une observation explicite, pas une absence silencieuse.

Le mode reste diagnostic, sans Wasm ni changement du sandbox. Le contrôleur n'attache pas un processus arbitraire : seulement un descendant initialement observé avec la même identité, ou un descendant courant du navigateur lancé. Les journaux et résultats précédents sont conservés. Le prochain retour doit inclure gdb_selection complet et le journal du renderer s'il a pu être capturé.
