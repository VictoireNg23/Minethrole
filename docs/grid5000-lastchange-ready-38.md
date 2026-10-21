# Métadonnées LASTCHANGE générées ; reprise de GN

Le rapport Grid5000 `lastchange-stage-d8x96aip/result.json` confirme `original_lastchange_outputs_prepared`, code 0, avec :

```text
LASTCHANGE=15234034d19b85dcd9a03b164ae89d04145d8368-refs/branch-heads/3578@{#897}
LASTCHANGE.committime: 1544577020
```

Ces valeurs sont la sortie du générateur historique, pas des constantes substituées par notre script. LASTCHANGE n'est pas utilisé comme remplacement du HEAD Chromium épinglé : le générateur peut représenter les métadonnées de commit/position selon sa logique originale. Aucun hook global ni build n'a été exécuté.

Prochaine étape : relancer `configure-chromium71.py` (version corrigée avec racine explicite), workspace `/tmp/minethrottle71-work-rwkni3hv`, rapport des outils `tools-link-m2r24lb6/result.json`. Chaque tentative garde son propre répertoire de sortie et ses journaux. Ne pas relancer le générateur LASTCHANGE : ses destinations sont maintenant occupées et seraient volontairement refusées.

Le succès de génération GN reste à établir. Les patches originaux ne sont toujours pas appliqués ; aucune compilation Ninja n'est demandée à ce stade.
