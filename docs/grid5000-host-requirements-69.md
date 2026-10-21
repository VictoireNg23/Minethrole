# Métadonnées Swamped lues ; analyser les hôtes par fichier

Le résumé utilisateur confirme 175 candidats et 175 `metadata_parsed_not_validated`, sans erreur de métadonnées. Les namespaces incluent env/a/i (ambigus), WASI, Go, wbg et des modules JavaScript relatifs. Les nombres d'import sont des occurrences d'imports, pas des nombres de modules ; ne pas les interpréter comme des tailles de classes de fichiers.

Le nouveau rapport par fichier conserve les noms d'import exacts et les signatures des exports. Les catégories d'hôte sont des indices fondés sur les noms observés, peuvent se chevaucher et ne sont jamais des caractéristiques de détection MineThrottle. Env seul n'est pas considéré comme preuve d'Emscripten. WASI n'est pas automatiquement disponible dans Chromium : il nécessiterait un hôte approprié. Wbg/chemins relatifs indiquent des bindings à fournir, sans prouver qu'ils exigent tous le DOM ou un navigateur. Les fonctions main/_start/_initialize sont des noms conventionnels seulement, pas des appels automatiquement autorisés avec des arguments inventés.

Le rapport compare aussi le multiensemble SHA-256 avec l'inventaire historique Dataset1_S pour établir une éventuelle identité des fichiers, sans propager automatiquement des labels ou conclure à une exécution minière. Aucun Wasm n'est exécuté. Les sorties sont placées dans un nouveau dossier `summaries/hosts-*`, avec la révision du code ; le dataset et les inventaires restent inchangés.

Attendre les résultats avant de choisir les modules exécutables et leurs hôtes. Le test navigateur synthétique et l'organisation du compte non privilégié/sandbox restent à préparer ; le présent rapport ne les remplace pas.
