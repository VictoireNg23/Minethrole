# Premier build Chromium : Node historique manquant

Le journal fourni confirme `chrome_build_failed`, code 1 après 15,71 secondes, rapport `chrome-build-c9hzhsk5/result.json`. L'action `md_bookmarks:build` s'arrête dans `optimize_webui.py` : `/bin/sh: ...third_party/node/linux/node-linux-x64/bin/node: not found`. La compilation a progressé jusqu'à environ 237/19 814 étapes. Ce blocage ne démontre pas une erreur C++ des patches.

Les hooks Node/WebUI étaient volontairement non exécutés. Préparer les deux archives historiques est nécessaire : Node Linux dans `chromium-nodejs/8.9.1` et les modules WebUI dans `chromium-nodejs`, chacun sélectionné par son fichier `.sha1` du checkout exact. Le script `download-chromium71-node.py` lit les actions de hooks avec AST sans exécuter DEPS, exige les deux chemins et buckets attendus, puis télécharge dans un nouveau répertoire. Il vérifie les empreintes SHA-1 et enregistre SHA-256 et le manifeste résumé. Limite : 512 Mio par archive ; timeout réseau de 30 secondes par opération bloquante.

Aucune archive n'est extraite et aucun fichier source n'est modifié. Ne pas utiliser un Node/npm récent ni lancer npm install pour remplacer les modules historiques. Examiner le contenu avant une extraction isolée et une intégration sans écrasement. Les objets déjà compilés restent disponibles ; ne pas nettoyer le build.
