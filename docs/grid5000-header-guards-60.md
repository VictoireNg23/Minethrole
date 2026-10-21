# Corriger les gardes générées à partir des chemins temporaires

Le rapport utilisateur montre des gardes `_TMP_MINETHROTTLE71-WORK-...` contenant des tirets. Notre redirection vers un chemin absolu temporaire a modifié le nom généré par lastchange.py ; il ne s'agit pas d'un identifiant C++ valide. La génération des métadonnées a réussi mais ces headers ne doivent pas être considérés prêts à compiler. Cette erreur relève de notre wrapper.

Le script de réparation appelle le générateur historique depuis un nouveau staging en conservant exactement les chemins relatifs `src/gpu/config/gpu_lists_version.h` et `src/skia/ext/skia_commit_hash.h` des hooks. Le lanceur d'environnement seul est utilisé, car with-tools.sh changerait cwd. Les sources Git sont indiquées par chemins absolus. Les gardes sont validées comme identifiants C++, et les valeurs GPU_LISTS_VERSION/SKIA_COMMIT_HASH doivent rester inchangées.

Par défaut, seuls les headers corrigés et sauvegardes sont préparés. Le flag explicite `--replace-recorded-generated-headers` remplace uniquement les deux sorties connues de notre étape précédente : leur contenu doit correspondre exactement au rapport fourni, sans lien symbolique ni autre changement. Les originaux sont sauvegardés avant remplacement dans le nouveau staging. Aucun patch des auteurs, fichier source écrit à la main, objet compilé ou autre header n'est modifié. Une interruption pourrait laisser une réparation partielle : examiner le rapport et préserver les sauvegardes.

Après résultat de réparation confirmé, reprendre seulement le build incrémental. Ne pas contourner les warnings de préprocesseur en désactivant Werror. Les scripts historiques des auteurs restent inchangés.
