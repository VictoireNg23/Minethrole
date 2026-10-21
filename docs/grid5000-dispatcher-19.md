# Grid5000 : correction de l'ordre des arguments du gclient historique

## Résultat utilisateur

La tentative dans `/tmp/minethrottle71-work-rwkni3hv/sync-nohooks-i3t08i_t` affiche le marqueur de préservation puis l'aide générale gclient et se termine par `Sync NOT launched: CLI checks incomplete`. La synchronisation n'a donc pas été lancée ; aucune sonde de cache n'a encore été exécutée par cette tentative.

L'erreur est dans notre lanceur, pas dans Chromium : --gclientfile était placé avant la sous-commande sync. Le test précédent de délégation vérifiait un faux point d'entrée trop permissif et ne détectait pas cette contrainte du dispatcher historique.

## Vérification de la cause

Le fichier [subcommand.py au commit exact depot_tools](https://chromium.googlesource.com/chromium/tools/depot_tools/+/c6a8d114b060f5f68637e8897712a24252402377/subcommand.py) a été consulté séparément comme référence d'outillage, sans télécharger Chromium ni une copie complète de depot_tools.

Dans CommandDispatcher.execute, lignes 236–258, la commande est choisie via find_nearest_command(args[0]) avant le traitement des options. Un premier argument --gclientfile n'est pas une commande connue, donc le dispatcher appelle l'aide générale. Les cas --help cmd et help cmd ont des traitements particuliers, mais pas les options générales arbitraires avant le nom de commande.

Un contrôle local avec le dispatcher historique inchangé et des handlers sans effets de bord a confirmé :

```text
--gclientfile=... sync --help -> general_help
sync --gclientfile=... --help -> sync
```

Seule la résolution de commande a été exercée ; aucune synchronisation réelle n'a été lancée dans Codex.

## Correction

Le constructeur commun gclient_arguments du script `scripts/sync-chromium71-nohooks.py` place désormais sync en premier, puis --gclientfile. Le même constructeur sert au contrôle d'aide et à la commande effective :

```text
sync --gclientfile=.gclient.minethrottle-mirror --help
sync --gclientfile=.gclient.minethrottle-mirror --verbose --nohooks ...
```

Le préfixe du driver ne contient plus --gclientfile. Aucun fichier .gclient ni historique n'est réécrit. La méthode _DeleteOrMove reste bloquée en mémoire, le cache reste désactivé avec sonde préalable, le miroir devtools reste épinglé au même commit, et les limites/restrictions de hooks restent identiques.

Le nouveau test de non-régression exige sync en premier pour les deux commandes, et les tests de délégation et de blocage de récupération passent maintenant par ce constructeur commun au lieu de coder l'ancien ordre erroné.

## Reprise proposée

Relancer uniquement la nouvelle version du script avec les mêmes paramètres explicites :

```bash
python3 /chemin/vers/sync-chromium71-nohooks.py \
  /tmp/minethrottle71-work-rwkni3hv \
  /tmp/minethrottle71-work-rwkni3hv/deps-seed-3ch80q_x/result.json \
  --gclientfile .gclient.minethrottle-mirror --sync --timeout 900
```

Le contrôle préalable doit afficher cette fois les options propres à sync, notamment --nohooks/--noprehooks/--revision, puis la sonde du cache. Si un contrôle échoue, le script conserve son comportement d'arrêt sans synchronisation. La reprise réseau n'est pas présumée réussie : transmettre les marqueurs de début, les erreurs éventuelles, la synthèse et le chemin des nouveaux journaux.
