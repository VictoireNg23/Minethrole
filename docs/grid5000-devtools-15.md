# Grid5000 : cache désactivé, échec ciblé sur devtools-node-modules

## Résultat reçu

La nouvelle sonde a confirmé `MINETHROTTLE_CACHE_PROBE={"cache_path": null}`. La synchronisation verbose a quitté avec code 1 après 73,55 secondes, sans timeout, dans `/tmp/minethrottle71-work-rwkni3hv/sync-nohooks-brdu1qn4`.

Le journal fourni montre un fetch Git réussi de glslang depuis `https://chromium.googlesource.com/external/github.com/google/glslang`, puis le maintien du checkout à `ec1476b7060306fd9109faf7a4c70a20ea3b538c`. L'accès Git à ce dépôt fonctionne ; cela ne prouve pas encore l'accès à tous les artefacts Git/CIPD.

L'autre tâche a échoué avec :

```text
gclient_scm.py, update, ligne 549 : self._DeleteOrMove(options.force)
gclient_scm.py, _DeleteOrMove, ligne 204 : shutil.move(self.checkout_path, dest_path)
IOError: [Errno 2] No such file or directory:
/tmp/minethrottle71-work-rwkni3hv/src/third_party/devtools-node-modules
```

L'erreur finale ne dit pas à elle seule pourquoi gclient a décidé d'appeler _DeleteOrMove : type d'entrée, checkout incomplet, URL divergente ou autre condition sont encore à distinguer. Un lien pendant est une hypothèse, pas un fait établi.

**Correction de notre précaution :** l'absence de --force/--reset dans une commande gclient ne garantit pas l'absence de déplacement automatique. Le gclient historique a ici tenté un déplacement interne. La nouvelle procédure ne doit pas recommencer cette opération sans compréhension et accord explicite sur une éventuelle modification d'un fichier existant. Aucune suppression, déplacement, création d'un dossier vide pour masquer l'erreur ou installation forcée ne sera proposée avant ce diagnostic.

## Étape suivante : lecture seule

`scripts/diagnose-devtools-dependency.py` lit :

- Le contexte autour de devtools-node-modules et de l'erreur dans sync.log, pas seulement le traceback final.
- lstat/lexists, le type et l'éventuelle cible du lien, le parent et les métadonnées .git de cette entrée. Un lien pendant est détecté même si exists retourne false.
- Les entrées correspondantes dans l'arbre Git et l'index Chromium, sans les changer.
- La définition exacte de la dépendance dans les rapports d'audit, son statut dans les rapports de préparation locale et la valeur littérale de .gclient_entries si présente (ce fichier n'est pas exécuté).
- Le type de la même entrée dans l'ancien arbre d'origine.
- La liste immédiate des dossiers _bad_scm existants dans le nouveau workspace.
- Les blocs historiques de _DeleteOrMove et update comme texte.

```bash
python3 /chemin/vers/diagnose-devtools-dependency.py \
  /tmp/minethrottle71-work-rwkni3hv \
  /tmp/minethrottle71-work-rwkni3hv/sync-nohooks-brdu1qn4
```

Le seul nouveau fichier est un rapport dans `devtools-diagnostic-.../report.json`. Aucun gclient, fetch, hook, patch, déplacement, suppression ou build. Les lectures Git sont bornées à 20 secondes ; une erreur est une observation indisponible.

Transmettre toute la sortie et le chemin du rapport. Nous pourrons ensuite préparer une correction précise et empêcher explicitement les déplacements automatiques lors des prochaines reprises si nécessaire. Le cache partiel et son verrou restent intacts ; les magasins d'objets d'origine et les patches restent conservés.

Deux tests nouveaux vérifient le traitement d'un lien pendant sans mutation, la lecture sans exécution de .gclient_entries et la conservation du contexte précédant l'erreur. Aucun gclient historique réel n'est exécuté dans Codex.
