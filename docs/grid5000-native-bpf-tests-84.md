# Nouveau staging prêt : exécuter trois tests BPF natifs

Le rapport utilisateur `provenance/browser-stage-sn2qbkqv.json` confirme la nouvelle copie `/tmp/minethrottle71-browser-test-_ysw60o_`, compte UID/GID 998 réutilisé, chrome et sandbox_linux_unittests aux empreintes du rebuild. L'ancien staging est conservé et ne doit plus être utilisé pour valider l'adaptation clone3.

Le contrôleur `test-chromium71-sandbox-native.py --stage-report RAPPORT` vérifie l'empreinte du binaire de tests, crée une nouvelle session locale et exécute sous minethrottle-test uniquement : BaselinePolicy.Clone3ReturnsEnosys, BaselinePolicy.CreateThread, BaselinePolicy.DisallowedCloneFlagCrashes. Le troisième est un death test : le processus enfant doit être arrêté comme attendu par le test, sans considérer cela comme un crash du contrôleur. Aucun navigateur ni dataset n'est lancé.

Les tests ont 60 secondes, avec arrêt contrôlé du groupe en cas de dépassement et core dumps désactivés. Le XML GoogleTest doit contenir exactement les trois cas attendus, exécutés sans failure/error/skipped ; un code 0 sans ces résultats ne suffit pas. Stdout, XML et résumé sont conservés dans `raw/sandbox-native-*`. Le test local du parseur couvre l'absence de tests et un échec dans un des cas.

Ce résultat reste à obtenir sur Grid5000. Une absence de tests, une erreur de ressources ou un refus de sandbox sera conservé comme incomplet/échec, pas contourné. Après les trois succès, retester la page locale normale sans pause GDB et exiger toujours les protections observées du renderer.
