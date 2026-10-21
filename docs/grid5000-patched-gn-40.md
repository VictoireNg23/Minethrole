# Patches appliqués ; génération GN sur les sources patchées

Le rapport Grid5000 `original-patches-0w04nngl/result.json` confirme les deux contrôles préalables puis l'application de `v8.patch` et `content.patch` originaux. Aucune compilation n'est exécutée.

`configure-chromium71.py` accepte désormais `--patch-report RAPPORT`. Ce mode exige le statut d'application des deux patches, revérifie leurs SHA-256 et lance `git apply --reverse --check` pour chacun, sans réellement inverser les patches. Il vérifie ainsi que leurs contextes appliqués sont toujours présents avant de générer GN dans un nouveau répertoire. Ce contrôle ne remplace pas une revue complète des différences ni la compilation. Les arguments des auteurs restent inchangés.

Le résultat distingue maintenant `gn_generation_passed_patched` de `gn_generation_passed_unpatched`. Après validation Grid5000, préparer une première compilation limitée de V8/d8 avant Chromium complet permettra de traiter les erreurs C++ de l'instrumentation. Cela ne remplace pas la validation ultérieure de `content.patch` avec la cible chrome. Ne pas lancer Ninja avant le retour de cette génération.
