# Trois tests BPF réussis ; retester le navigateur sans debugger

Le rapport `raw/sandbox-native-wyp15v5i/result.json` confirme les trois tests natifs exécutés et réussis, code 0, sans timeout : Clone3ReturnsEnosys, CreateThread, DisallowedCloneFlagCrashes. Binaire de tests c7d8497e41eb6a4bf6d963592796dd5fc0b8fbcc7c0d9dcd9d9b70fd7c2bec04, compte UID 998, environnement `GLIBC_TUNABLES=glibc.pthread.rseq=0`. Cela valide le scénario ciblé de création de thread et la restriction clone testée, pas toute la politique seccomp.

La nouvelle tentative navigateur doit utiliser `browser-stage-sn2qbkqv.json`, donc chrome 59e77231028f446d0abe03342ab6b2c2e17687a99aa86b58ca82f4118fb9218c, avec le même réglage rseq. Le contrôleur exige désormais un rapport BPF réussi correspondant au staging pour ce navigateur adapté et refuse une configuration rseq différente. La provenance et le réglage glibc sont conservés dans le rapport du navigateur.

Exécuter le test normal de page locale, sans options diagnostic-cdp/gdb/renderer-startup. Il doit terminer normalement, produire le marqueur DOM et montrer un renderer non root avec Seccomp=2 et NoNewPrivs=1. Aucun Wasm ni dataset n'est chargé par cette page. Les sorties restent dans un nouveau raw/browser-ready-* ; les échecs antérieurs ne sont pas effacés.

L'environnement glibc est un paramètre expérimental à conserver. La réussite de ce contrôle ne validera pas encore les compteurs MineThrottle en navigateur, les profils, seuils ou le cycle de vie de plusieurs instances. Ne pas déclarer la défense active : le patch original la désactive par défaut.
