# GN patché validé ; première compilation V8/d8

Grid5000 confirme `gn_generation_passed_patched`, code 0, dans `src/out/MineThrottle71-config-cp8f0qce`, avec 10 601 cibles générées. Les contextes appliqués des deux patches ont été vérifiés avant génération.

Prochaine étape : compiler uniquement `d8` avec le Ninja système, 8 tâches, arrêt après une erreur (`-k 1`), timeout de 900 secondes et cache ccache dédié au workspace (plafond 10 Gio). Le script `build-chromium71-d8.py WORKSPACE GN_REPORT` exige un rapport GN patché réussi et au moins 30 Gio libres. Il écrit le build dans le répertoire préparé, sans nettoyage ni modification des patches. Le journal complet et le résultat sont conservés ; seule sa fin est affichée. Une autre session peut suivre le journal avec `tail -f CHEMIN_DU_JOURNAL` affiché au démarrage.

Un timeout ou une interruption arrête le groupe de processus lancé par ce script, conserve les objets partiels et reste un résultat incomplet. Une reprise devra réutiliser ce répertoire après analyse. Les éventuelles erreurs de dépendances ou de compilation seront traitées à partir du journal réel, sans substitutions automatiques du compilateur.

Le succès de d8 validerait seulement une compilation de V8 instrumenté. Il faudra ensuite tester l'exécution WebAssembly et les compteurs, puis compiler et tester Chromium pour valider `content.patch`. Aucun module du dataset ni chrome n'est lancé par ce script. La compilation se fait uniquement sur Grid5000, pas dans Codex.
