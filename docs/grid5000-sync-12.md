# Grid5000 : première synchronisation historique, sans hooks

## Dernier résultat confirmé par l'utilisateur

Le rapport `/tmp/minethrottle71-work-rwkni3hv/deps-seed-3ch80q_x/result.json` indique : 42 nouveaux clones locaux préparés, un checkout exact conservé (V8), 20 entrées sans commit local confirmé, 157 entrées conditionnelles différées, un chemin non pris en charge et une entrée sans SHA Git exploitable. Aucun conflit de destination occupée n'est signalé dans ce résumé.

Les contextes des patches restent vérifiés mais les patches ne sont pas appliqués. Les dépendances ne sont pas encore complètes.

## Action suivante et changements de périmètre réseau

Cette étape **peut télécharger un volume important et encore inconnu** : sources Git manquantes, dépendances récursives et paquets CIPD sélectionnés par le gclient historique sur le nœud Linux. Les 94 définitions CIPD de l'audit couvraient plusieurs plateformes ; elles ne sont pas toutes nécessairement actives. Le script n'invente pas les valeurs de checkout_linux, checkout_android ou autres conditions : il laisse le gclient épinglé traiter le DEPS et sa configuration minimale existante.

`scripts/sync-chromium71-nohooks.py` n'active le réseau de synchronisation qu'avec **`--sync`**. Le mode par défaut vérifie et affiche le plan sans lancer gclient. Avant l'opération :

- Vérification du SHA depot_tools, de la structure exacte de .gclient et des HEAD Chromium/V8.
- Vérification des HEAD et de l'absence de changements suivis/stagés dans les clones préparés. Les fichiers non suivis ne sont pas supprimés ; ce contrôle ne prétend pas en établir l'absence.
- Refus des conflits de destination déjà identifiés par le rapport de préparation.
- Vérification de 100 Gio libres au minimum dans le workspace ; ce seuil historique n'est pas une garantie de volume suffisant pour l'ensemble des téléchargements ou la compilation. Les inodes et la disponibilité du nœud restent à surveiller.
- Test de `gclient sync --help`, borné à 60 secondes, pour confirmer les options requises avant toute synchronisation.

La commande de synchronisation est :

```text
gclient sync --nohooks --noprehooks --jobs=4 \
  --revision src@c2bec8045f7ad3ece1c5d80236183a21c1fac3f5 \
  --revision src/v8@b5a5d900a5385d6429edefb11ece72bfa649ca47
```

Elle passe par les lanceurs isolés existants. Pas de `--force`, `--reset`, suppression d'arbres non versionnés ou récupération des branch heads. Le script ne met pas depot_tools à jour, ne remplace pas .gclient, ne change aucun lien Python système et n'applique pas les patches.

GIT_CACHE_PATH pointe vers un cache dans le nouveau workspace. Les hooks Git et maintenances automatiques des sous-commandes Git sont désactivés via des options de processus, sans écrire de configuration globale. Les contrôles de signature/checksum/TLS restent actifs. Les écritures Git se font dans les nouveaux clones/caches ; les magasins alternatifs d'origine sont consultés en lecture et doivent être conservés. Les caches usuels du bootstrap CIPD/vpython peuvent aussi être utilisés par les outils historiques.

## Exécution proposée

```bash
python3 /chemin/vers/sync-chromium71-nohooks.py \
  /tmp/minethrottle71-work-rwkni3hv \
  /tmp/minethrottle71-work-rwkni3hv/deps-seed-3ch80q_x/result.json \
  --sync
```

Le délai maximal est de 3600 secondes par défaut pour cette première tentative, modifiable avec `--timeout`. Les journaux sont affichés au fil de l'exécution et conservés dans un nouveau `sync-nohooks-.../` : sync-help.log, sync.log et result.json. stdin est fermé pour éviter les invites d'authentification bloquantes. Un échec d'accès public sera diagnostiqué, pas contourné avec des identifiants inventés.

Un timeout ou Ctrl+C arrête seulement le groupe de processus créé par le test. Les fichiers partiels restent en place et ne sont pas nettoyés. Le code réel du processus est conservé. Ne pas relancer inchangé en cas d'échec : transmettre la fin des erreurs et le chemin des journaux pour une correction ciblée. Le script de premier passage reste conservateur vis-à-vis de modifications locales apparues ; il ne faut pas contourner ses gardes pour reprendre.

## Résultat à transmettre

Envoyer la fin du journal, la synthèse finale et le chemin de result.json. En cas de téléchargement long, conserver le terminal/la réservation du nœud et surveiller l'espace disponible depuis un autre terminal ; ne pas démarrer une deuxième synchronisation simultanée.

Un succès signifie uniquement « gclient sync a terminé avec code zéro, HEAD Chromium/V8 revérifiés, hooks désactivés ». Il ne prouve pas le succès des hooks, la complétude du sysroot/toolchain, la compatibilité C++ ni les résultats expérimentaux. Après retour nous préparerons les bibliothèques système, les hooks contrôlés et la configuration GN, avant toute compilation.

## Tests dans Codex

Trois tests supplémentaires portent sur les arguments épinglés et l'absence d'options destructives, le refus d'une configuration .gclient inattendue sans l'exécuter, et la conservation des sorties/codes d'erreur/timeouts. La synchronisation réelle n'est pas exécutée dans Codex ; aucun Chromium n'y est téléchargé ni compilé.
