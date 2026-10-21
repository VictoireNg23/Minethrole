# Synchronisation historique sans hooks validée

Le rapport Grid5000 `sync-nohooks-3svh862l/result.json` confirme une fin normale, code 0, après 31,5 secondes, avec les révisions principales vérifiées : Chromium `c2bec8045f7ad3ece1c5d80236183a21c1fac3f5` et V8 `b5a5d900a5385d6429edefb11ece72bfa649ca47`. La configuration du miroir DevTools exact est sélectionnée, le cache résolu est nul et le garde-fou est actif. Les hooks et pré-hooks sont désactivés, aucun build n'est exécuté.

Cela valide cette étape de synchronisation, pas la présence du compilateur historique, du sysroot, de GN ni la compilation des patches. Les magasins d'objets partagés doivent rester disponibles.

Prochaine étape en lecture seule : `scripts/inspect-chromium71-hooks.py WORKSPACE SYNC_REPORT`. Le script lit les définitions des hooks dans les DEPS réellement présents sans exécuter ces fichiers, vérifie l'existence de quelques outils et consulte les paquets locaux. Les conditions des hooks ne sont pas évaluées par cette inspection ; la sélection des actions devra tenir compte de Linux et des variables DEPS. Ne pas lancer aveuglément tous les hooks historiques ni `install-build-deps.sh` sur Ubuntu 22.04. Examiner les sorties avant de préparer les téléchargements et installations ciblés.
