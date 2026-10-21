# Staging prêt ; premier lancement sur page locale sans Wasm

Le rapport utilisateur `provenance/browser-stage-eqnp8u92.json` confirme le staging local `/tmp/minethrottle71-browser-test-e7hcltwq`, compte minethrottle-test UID/GID 998, binaire SHA-256 attendu et ressources copiées. Aucun navigateur n'a encore été lancé par cette préparation.

Clarification du dataset : Dataset1_S est le nom scientifique et `Data/Swamped_10_` son chemin local ; l'identité des 175 contenus est confirmée par SHA-256. Il ne s'agit pas de deux datasets distincts.

Le premier lancement utilise seulement `browser-ready.html` (aucun Wasm, aucun accès au dataset). Le contrôleur root exécute Chrome sous le compte dédié via runuser, en headless, profil local neuf et sans --no-sandbox. La page occupe brièvement le renderer pour permettre l'observation de ses informations /proc. Le test exige une sortie normale, le marqueur DOM final et l'observation d'un renderer non root avec Seccomp=2 et NoNewPrivs=1, sans flag --no-sandbox. Cela démontre des mécanismes observés du sandbox, pas une certification complète de son isolation.

Le processus a un délai de 20 secondes et les core dumps sont désactivés. Les journaux stdout/stderr, échantillons de processus et résultat sont conservés dans un nouveau `raw/browser-ready-*` du run partagé. Le compte dédié écrit seulement dans une nouvelle session locale ; les permissions du stockage partagé restent inchangées. La page et le cache local sont conservés. Aucun lancement sur un module malveillant n'est autorisé par cette étape.

Si le sandbox ou le chargement échoue, analyser stderr avant toute suite ; ne pas ajouter --no-sandbox pour obtenir un succès. Le correctif d'arrêt de d8 ne couvre toujours pas les renderers. Après ce contrôle initial seulement, préparer le fixture Wasm et la collecte des compteurs MineThrottle dans Chromium.
