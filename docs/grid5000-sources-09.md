# Grid5000 : gclient démarre, préparation locale des sources historiques

## Résultat reçu

Le candidat depot_tools `c6a8d114b060f5f68637e8897712a24252402377` a affiché l'aide complète de gclient avec `status=help_completed` et `underlying_exit_code=0`. Les journaux sont sous `/tmp/minethrottle71-tools-li2ldh40/gclient-help-check-8uf79q31`.

Le message « Running depot tools as root is sad » n'est pas un échec de cette commande. L'avertissement metrics.cfg signale une configuration absente/invalide et sa création par l'outil ; son chemin n'est pas indiqué par cette sortie. Ne pas modifier les sources pour supprimer ces avertissements. Le démarrage de l'aide ne démontre pas que tous les téléchargements CIPD, hooks et dépendances historiques fonctionneront.

## Objectif de la prochaine étape

Préparer deux checkouts historiques dans un répertoire unique `/tmp/minethrottle71-work-...`, en réutilisant les objets des dépôts **existants** :

- `MineThrottle/chromium/src` pour Chromium `c2bec8045f7ad3ece1c5d80236183a21c1fac3f5`.
- `MineThrottle/chromium/src/v8` pour V8 `b5a5d900a5385d6429edefb11ece72bfa649ca47`.

Aucune récupération réseau des sources. En revanche, l'écriture des fichiers de travail représente plusieurs Go possibles et de nombreux inodes ; cette étape n'est pas une simple lecture de métadonnées. /tmp a été signalé avec 808 Go libres sur ext4 ; le script relit sa capacité avant création et s'arrête en dessous de 20 Gio libres, seuil de prudence pour cette étape seulement, pas une estimation suffisante pour la compilation future. La vitesse dépend du stockage et des packs d'origine.

## Script et garde-fous

`scripts/prepare-chromium71-local.py` :

1. Vérifie les objets de commit locaux, l'identité du depot_tools isolé et les empreintes des patches originaux.
2. Crée un nouveau répertoire unique, sans réutiliser ni nettoyer un dossier existant.
3. Effectue deux clones **locaux avec `--shared --no-checkout --no-tags`**. Les magasins de dizaines de Go ne sont pas recopiés : ils sont référencés par des alternates dans les nouveaux clones.
4. Positionne seulement ces nouveaux clones sur les SHA historiques, sans force et sans sous-modules récursifs. Les hooks Git et la maintenance automatique sont désactivés dans ces clones.
5. Définit leurs nouveaux origin vers les URL HTTPS Chromium/V8 attendues pour les étapes futures. Leurs anciens origin ne sont pas changés.
6. Vérifie à nouveau les patches par `git apply --check` sur ces nouveaux arbres. Aucun patch n'est appliqué.
7. Prépare `.gclient` avec une solution `src` unmanaged (`managed=False`) pour éviter un suivi implicite de HEAD récent. Les futures synchronisations devront rester explicitement épinglées à la révision historique ; aucune synchronisation n'est exécutée ici.
8. Enregistre `preparation.json` et un lanceur `with-tools.sh` réutilisant le depot_tools historique déjà préparé.

La première commande de checkout peut prendre plusieurs minutes. Chaque opération longue est bornée à 900 secondes et un échec arrête la procédure. Le répertoire partiel reste conservé ; les étapes terminées sont consignées. Ne pas supprimer un `.git/index.lock` ou autre fichier après un échec sans en analyser la cause.

## Dépendance des clones partagés

**Ces nouveaux clones ne sont pas des sauvegardes indépendantes.** Ils dépendent des magasins d'objets de l'ancien projet. Ne pas supprimer, déplacer ou lancer un nettoyage/pruning de ces magasins pendant les expériences. Les modifications de fichiers du nouvel arbre restent séparées des fichiers des anciens checkouts, mais l'accès aux objets reste partagé en lecture. Le chemin et le magasin emprunté figurent dans preparation.json.

Une copie indépendante pourra être préparée plus tard si nécessaire et si l'espace le permet. Elle n'est pas effectuée implicitement : une dissociation recopierait beaucoup d'objets. Aucun git worktree n'est créé. Le stockage partagé à 95 % n'est ni nettoyé ni utilisé pour de nouvelles sorties volumineuses dans cette étape.

## Exécution proposée

```bash
python3 /chemin/vers/prepare-chromium71-local.py "$projet_minethrottle" \
  --tools-root /tmp/minethrottle71-tools-li2ldh40
```

Ne pas lancer gclient sync, les hooks, --all ou la compilation après cette commande. Transmettre toute la sortie, notamment le nouveau chemin, les SHA vérifiés, les magasins empruntés et les erreurs éventuelles. Un succès signifie uniquement « sources principales et V8 positionnés, contextes des patches vérifiés ». Les autres dépôts DEPS, binaires de toolchain et dépendances système restent à préparer.

## Validation effectuée dans Codex

Un test de minuscules dépôts synthétiques vérifie le checkout d'un ancien commit dans un clone partagé local, l'enregistrement des alternates, la modification du remote du clone uniquement, le refus de réutiliser une destination non vide et la préservation du HEAD, de l'index et des modifications locales du dépôt source. Aucun Chromium n'est téléchargé ni compilé dans Codex.
