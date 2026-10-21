# Page headless : sandbox observé, sortie DOM non obtenue

Le test `raw/browser-ready-cy4_iyuy/result.json` dépasse 20 secondes, puis son groupe est arrêté par le contrôleur (code -15). Il n'a pas obtenu le marqueur DOM. Un renderer UID 998 avec Seccomp=2 et NoNewPrivs=1 a été observé, sans --no-sandbox. Le seul message GPU `Lost UI shared context` ne démontre pas à lui seul la cause du blocage. Aucun Wasm n'a été exécuté.

Le mode `--diagnostic-cdp` conserve le binaire et le sandbox, remplace seulement dump-dom par un port DevTools local éphémère et lit `/json/list` pendant six secondes. La page écrit désormais son marqueur final aussi dans le titre : les snapshots peuvent montrer si son JavaScript s'est terminé, indépendamment de l'attente de dump-dom. Le port est lu dans le profil neuf ; les sondes utilisent uniquement 127.0.0.1. Le script ne crée ni serveur externe ni dépendance Python supplémentaire.

Cette capture arrête volontairement le groupe de processus après observation ; elle est étiquetée diagnostic, jamais succès du test de sortie normale. Les codes de sortie et le motif d'arrêt sont conservés. Le script retourne non nul pour ne pas confondre ce mode avec une validation réussie. Le navigateur ne charge que la page locale synthétique sans Wasm. Les snapshots et journaux restent dans un nouveau dossier raw/browser-ready-* ; l'ancien résultat n'est pas écrasé.

Le code headless historique a été relu à la révision exacte : dump-dom dépend de l'état de chargement/événements Page puis d'une évaluation DevTools. Il faut distinguer un blocage du chargement, un renderer arrêté, un JavaScript qui ne finit pas et une attente de cette séquence. Ne pas contourner le résultat en ajoutant no-sandbox ou en déclarant le message GPU fatal sans preuve.
