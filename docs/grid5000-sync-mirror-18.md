# Grid5000 : commit devtools exact vérifié, reprise sous garde-fou

## Résultat utilisateur confirmé

La récupération depuis le miroir tiers a terminé avec :

- SHA attendu et HEAD réel : `5f7cd2497d7a643125c3b6eb910d99ba28be6899`.
- git fsck --strict terminé avant checkout sans erreur bloquante.
- Configuration alternative créée : `/tmp/minethrottle71-work-rwkni3hv/.gclient.minethrottle-mirror`.
- Rapport : `/tmp/minethrottle71-work-rwkni3hv/devtools-exact-mirror-rtzgdkzf/result.json`.
- DEPS et .gclient d'origine inchangés ; aucun gclient sync ou build dans cette récupération.

Les notices unborn HEAD, no default references et dangling commit sont cohérentes avec l'ordre des commandes : le commit venait d'être récupéré dans FETCH_HEAD, avant d'être attaché au HEAD détaché par checkout. Le checkout final place HEAD au bon SHA ; ces notices ne constituent pas une corruption démontrée. Ne pas changer init.defaultBranch globalement pour faire disparaître un simple message d'aide.

## Reprise préparée

Le script `scripts/sync-chromium71-nohooks.py` accepte maintenant :

```text
--gclientfile .gclient.minethrottle-mirror
```

Il valide la configuration alternative comme une donnée littérale : exactement les paramètres attendus, et uniquement le custom_deps pour l'URL du miroir tiers épinglée au SHA original. Aucun @HEAD, autre révision ou autre override n'est accepté. Il vérifie également le HEAD, l'absence de changements suivis/stagés et l'origin du checkout devtools avant reprise.

La .gclient d'origine n'est pas réécrite. Le fichier alternatif est sélectionné par l'option gclient historique --gclientfile. Les SHA Chromium/V8 restent explicitement épinglés ; le cache miroir reste désactivé et sa sonde doit toujours confirmer cache_path=null.

## Adaptateur de préservation, distinct des patches MineThrottle

Le gclient historique peut déplacer automatiquement un chemin même sans --force. Le nouveau script génère dans le dossier de journaux un petit `guarded-gclient.py` qui :

1. Utilise le Python 2 du lanceur déjà préparé.
2. Importe gclient_scm depuis le snapshot historique exact.
3. Remplace **en mémoire uniquement** SCMWrapper._DeleteOrMove par une méthode qui lève une erreur explicite. Si elle est appelée pendant une exception, le texte de l'exception initiale est inclus dans ce diagnostic.
4. Lance ensuite le gclient.py historique par runpy, avec les arguments épinglés.

Le marqueur `MINETHROTTLE_PRESERVATION_GUARD=enabled` doit apparaître pendant le contrôle d'aide avant toute synchronisation. Si la méthode historique attendue n'existe pas ou que le démarrage échoue, la synchronisation n'est pas lancée.

Aucun fichier du snapshot depot_tools ni des patches des auteurs n'est modifié. Il s'agit d'une adaptation de l'orchestration d'installation, pas du détecteur. L'appel direct à gclient.py remplace le wrapper de lancement pour ce processus ; il ne définit pas VPYTHON_BYPASS et ne désactive aucune vérification de paquets. Le snapshot et les interpréteurs ont été préparés dans les étapes précédentes ; les outils CIPD/vpython invoqués ultérieurement conservent leurs vérifications normales.

Ce garde-fou bloque **la méthode de récupération identifiée**, pas toutes les écritures normales d'une synchronisation ni tous les appels filesystem possibles dans l'ensemble des outils. Une synchronisation continue de créer et mettre à jour les nouveaux checkouts du workspace. Les anciens magasins d'objets sont conservés en lecture et ne doivent pas être nettoyés.

## Commande proposée

```bash
python3 /chemin/vers/sync-chromium71-nohooks.py \
  /tmp/minethrottle71-work-rwkni3hv \
  /tmp/minethrottle71-work-rwkni3hv/deps-seed-3ch80q_x/result.json \
  --gclientfile .gclient.minethrottle-mirror --sync --timeout 900
```

Cette reprise peut télécharger les dépendances manquantes Git/CIPD. Elle reste bornée à quinze minutes, à quatre tâches et sans hooks/pré-hooks. Aucun --force, --reset, suppression de fichiers partiels ou build. Des fichiers de suivi gclient propres au nom de configuration alternatif peuvent être créés dans le nouveau workspace.

Envoyer la sortie de début (garde-fou et sonde), la fin des erreurs ou la synthèse finale, et le nouveau chemin de journaux. Le succès du fetch devtools ne garantit pas que toutes les autres URL historiques existent ; chaque nouvel échec sera traité séparément, sans retirer la dépendance ni changer la logique du détecteur.

## Tests locaux

Trois nouveaux tests vérifient l'acceptation exclusive de l'override exact, la délégation normale de l'aide et l'interception d'une tentative de déplacement tout en conservant l'erreur de clone initiale. Ils vérifient que la méthode originale simulée ne s'exécute pas et que son fichier source reste intact. Ces tests n'exécutent pas le gclient historique réel dans Codex et ne remplacent pas la reprise sur Grid5000.
