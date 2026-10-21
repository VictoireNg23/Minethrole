# Grid5000 : reprise sans nouveau miroir Git

## Éléments reçus

L'extrait transmis dans la pièce jointe est conservé dans `evidence/grid5000-sync-timeout-cache.txt`. Il indique :

- Aucun verrou parmi ceux inspectés dans src/V8 ; aucun nouveau pack dans leurs magasins locaux.
- Sous `git-cache`, un répertoire `_cache_tmp0HwNNcchromium.googlesource.com-chromium-src` et le fichier `chromium.googlesource.com-chromium-src.lock`.
- Aucun processus détecté avec cwd dans le workspace ou les outils au moment du diagnostic.
- Le code historique gclient_scm.GetCacheMirror utilise git_cache.Mirror si un cache est configuré. `_UpdateMirrorIfNotContains` peut appeler `mirror.populate` si le miroir ne possède pas le SHA recherché.

Notre script avait explicitement défini `GIT_CACHE_PATH=<workspace>/git-cache`. Cela activait un cache neuf alors que Chromium était déjà présent dans les objets empruntés. C'était un choix inadapté à cette stratégie de réutilisation locale. La préparation d'un cache Chromium est confirmée par son dossier temporaire. Le début de sync.log n'est pas inclus dans la pièce jointe reçue : la sous-commande exacte qui a occupé l'heure et la part réseau/attente restent inconnues. Il ne faut pas présenter le blocage comme une corruption ou comme un défaut des patches.

## Correction de notre orchestration

`scripts/sync-chromium71-nohooks.py` :

1. Ne définit plus GIT_CACHE_PATH et retire aussi une éventuelle valeur héritée pour ce processus seulement. Le shell appelant et les fichiers de configuration restent inchangés.
2. Demande au module **git_cache du snapshot historique exact** ce que retourne `Mirror.GetCachePath`, en le lançant avec le Python 2 isolé. Le module est importé pour lire le résolveur de cache ; aucun mirror.populate, fetch ou gclient sync n'est lancé par cette sonde. Une absence de cache (RuntimeError de ce résolveur) est enregistrée comme cache_path=null. Si un autre cache reste sélectionné, si l'import échoue ou si la sonde n'est pas concluante, la synchronisation n'est pas lancée.
3. Vérifie les origin des nouveaux checkouts contre les URL attendues. Si un origin a été modifié vers un miroir pendant la tentative précédente, le script s'arrête sans réécrire cette configuration. Ce cas devra être corrigé explicitement après examen.
4. Active `--verbose` pour que la reprise expose les décisions Git plutôt que seulement les messages d'attente.
5. Conserve les SHA exacts, quatre tâches, --nohooks, --noprehooks, les contrôles d'arbre et les journaux dans un nouveau sous-dossier.

L'ancien cache, son verrou et les fichiers partiels sont laissés intacts. Aucun lien Python, magasin d'origine, .gclient ou patch n'est modifié par cette correction. Les contrôles de signature/checksum/TLS ne sont pas affectés. Aucun --force, --reset ou nettoyage n'est ajouté.

## Nouvelle tentative bornée

Une reprise réseau est justifiée par ce changement concret de configuration, pas par une augmentation du temps. Proposer une première reprise limitée à **900 secondes** pour observer si src est franchi et obtenir des traces détaillées, sans attendre à nouveau une heure sans commande visible :

```bash
python3 /chemin/vers/sync-chromium71-nohooks.py \
  /tmp/minethrottle71-work-rwkni3hv \
  /tmp/minethrottle71-work-rwkni3hv/deps-seed-3ch80q_x/result.json \
  --sync --timeout 900
```

Le contrôle CLI et la nouvelle sonde précèdent la synchronisation. Le résultat comporte cache_probe_process et cache_probe quand la sonde est concluante. Un cache non nul produit `cache_probe_failed_sync_not_launched`. Les bibliothèques manquantes du snapshot ou un origin inattendu sont des blocages explicites, sans modification automatique destinée à les contourner.

La reprise peut télécharger les dépendances Git/CIPD réellement manquantes. Elle ne garantit pas que toute la synchronisation puisse tenir en quinze minutes. Un éventuel nouveau timeout pourra être distingué d'une erreur grâce au journal détaillé ; les fichiers téléchargés restent conservés. Ne pas lancer une seconde synchronisation en parallèle, ni retirer le verrou de l'ancien cache.

Transmettre le résultat de la sonde et les premières commandes détaillées, puis la synthèse/erreur et le nouveau chemin de journaux. Si src se bloque de nouveau, le début de la commande verbale et sa sortie seront particulièrement utiles pour distinguer fetch, accès NFS et autre cause. Aucun hook ou build ne sera lancé avant examen du résultat.

## Validation locale

Les tests supplémentaires vérifient la suppression d'un GIT_CACHE_PATH hérité, le refus d'une sonde manquante/non nulle, l'appel d'un faux module historique sans réseau, le refus d'un origin de miroir sans réécriture et l'activation des traces. Le test réel du résolveur historique puis la reprise réseau doivent être exécutés par l'utilisateur sur Grid5000. Aucun Chromium n'est téléchargé ou compilé dans Codex.
