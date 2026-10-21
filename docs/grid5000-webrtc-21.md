# Blocage WebRTC lors de la synchronisation historique

Le journal `sync-nohooks-9m12u26_/sync.log`, lignes 46370–46371, identifie un échec de checkout de WebRTC au commit `0ba24191ee90c70679d2452363676c2d65b6b751` : `fatal: reference is not a tree`. Le garde-fou a refusé la récupération automatique par déplacement/suppression. Ce résultat ne prouve pas à lui seul que le commit a disparu du serveur : il peut manquer dans les références récupérées ou dans un clone partiel/superficiel.

`scripts/diagnose-webrtc-checkout.py` inspecte uniquement les métadonnées des clones WebRTC (cible, clones temporaires du workspace et deux sources locales optionnelles), teste les objets commit/arbre et extrait les lignes pertinentes du journal. Il désactive la récupération implicite d'objets. Aucun checkout, fetch, hook ou déplacement n'est exécuté. Les observations indisponibles et les timeouts restent explicitement signalés.

Attendre les résultats avant de choisir une récupération ciblée du SHA exact. Ne pas remplacer WebRTC par une version récente et ne pas relancer une synchronisation globale à ce stade.
