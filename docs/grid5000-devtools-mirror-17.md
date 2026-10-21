# Grid5000 : URL disparue et récupération du commit exact depuis un miroir

## Cause initiale confirmée

Le journal utilisateur établit que les clones vers l'ancienne URL échouent avec :

```text
fatal: repository 'https://chromium.googlesource.com/external/github.com/ChromeDevTools/devtools-node-modules/' not found
```

Le code de sortie 128 déclenche ensuite _DeleteOrMove, lequel échoue sur le dossier absent et masque la première erreur. La dépendance n'a pas été récupérée localement pendant la préparation et ne doit pas être ignorée ou remplacée par un npm install récent.

## Recherche effectuée dans Codex, limitée aux métadonnées

- Le dépôt GitHub historique `ChromeDevTools/devtools-node-modules` ne répond pas comme un dépôt accessible à git ls-remote.
- Les emplacements Gitiles devtools/devtools-node-modules et chromium/deps/devtools-node-modules testés ne fournissent pas le commit demandé (HTTP 404).
- Une recherche GitHub par **SHA complet** trouve `bpsinc-native/src_third_party_devtools-node-modules` avec le commit `5f7cd2497d7a643125c3b6eb910d99ba28be6899`.
- La [page du commit](https://github.com/bpsinc-native/src_third_party_devtools-node-modules/commit/5f7cd2497d7a643125c3b6eb910d99ba28be6899) répond avec le titre « Install with npm v5 to address crbug.com/798765 ».
- git ls-remote confirme l'accès au miroir ; son HEAD/master est `a1f65ce099cef6418884ce0fb51b122398d8ce02`, **qui n'est pas la révision retenue**.

Il s'agit d'un **miroir tiers**, pas d'un dépôt officiel des auteurs. La page GitHub est un indice de disponibilité ; la preuve décisive sera la récupération de l'objet Git exact et sa vérification sur le nœud. Aucun code de ce dépôt ni Chromium n'est téléchargé dans Codex. La comparaison repose sur le SHA fixé dans le DEPS original, pas sur une confiance dans la branche du miroir.

## Prochaine étape unique

`scripts/prepare-devtools-exact-mirror.py` propose, avec l'option explicite `--fetch-exact` :

1. Vérifier le HEAD historique de Chromium, la configuration .gclient minimale attendue et l'absence totale du chemin destination (y compris un lien pendant).
2. Créer seulement le nouveau dossier `src/third_party/devtools-node-modules`. Un dossier préexistant, même vide, provoque un arrêt sans modification.
3. Initialiser son Git et récupérer **uniquement le SHA attendu** avec fetch --depth=1 --no-tags. Cela télécharge les objets/fichiers de cette dépendance et non une archive complète de Chromium. Le volume réel n'est pas encore mesuré.
4. Activer les contrôles fetch.fsckObjects/transfer.fsckObjects, lancer git fsck --strict et vérifier le HEAD après checkout détaché. Aucun npm install, script Node ou hook du dépôt n'est exécuté.
5. Créer un **nouveau fichier `.gclient.minethrottle-mirror`**, refusant tout écrasement. Il conserve les paramètres de la solution et ajoute un seul custom_deps qui remplace l'URL de transport pour cette dépendance, toujours épinglée à `5f7cd249...`.
6. Conserver les commandes, leurs sorties et result.json dans un nouveau devtools-exact-mirror-.../. Un échec laisse les fichiers partiels en place et arrête l'étape.

Le fichier **DEPS et la `.gclient` existante restent inchangés**, ainsi que les patches originaux et tous les anciens checkouts. Les échecs ne sont pas contournés par un autre SHA, des paquets non vérifiés, --force ou un nettoyage.

```bash
python3 /chemin/vers/prepare-devtools-exact-mirror.py \
  /tmp/minethrottle71-work-rwkni3hv --fetch-exact
```

Le mode par défaut est un plan seul, sans téléchargement. Ne lancer cette commande qu'une fois, puis transmettre la sortie complète, les journaux et le HEAD obtenu. Si une destination est déjà présente, ne pas la supprimer : communiquer l'erreur pour examen.

## Aucune synchronisation dans cette étape

Le script ne lance pas gclient. **Ne pas relancer l'ancienne commande de sync** : elle lit encore la `.gclient` d'origine qui référence le dépôt disparu. Après vérification de ce résultat, la reprise devra sélectionner explicitement le fichier alternatif avec l'option gclient historique --gclientfile. Elle devra également empêcher la voie de déplacement automatique identifiée, ou s'arrêter avant cette voie avec l'erreur d'origine préservée.

Le choix d'un autre transport pour le **même commit** est une adaptation d'installation, pas un changement du détecteur ou des profils. La validation C++, les hooks et les expériences restent non exécutés.

## Tests locaux

Deux tests vérifient la récupération d'un ancien commit exact plutôt que le HEAD récent d'un dépôt synthétique, la préservation de ce dépôt source, le refus de réutiliser une destination existante et le refus d'une configuration .gclient inattendue. Aucun vrai paquet node_modules ni Chromium n'est récupéré dans ces tests.
