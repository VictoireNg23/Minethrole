# Grid5000 : correction ciblée de l'extraction des liens internes

## Cause confirmée par inspection de l'archive existante

Le commentaire Git de `/tmp/minethrottle71-tools-w_exm4gk/depot_tools.tar` est bien `c6a8d114b060f5f68637e8897712a24252402377`.

Quatre entrées sont des liens symboliques (`type b'2'`) :

```text
cbuildbot       -> support/chromite_wrapper
chrome_set_ver  -> support/chromite_wrapper
cros            -> support/chromite_wrapper
cros_sdk        -> support/chromite_wrapper
```

Le rejet précédent venait du refus de tous les liens par notre extracteur, et non d'une incompatibilité Python, de gclient ou de Chromium. Les cibles annoncées sont internes ; le script corrigé vérifiera encore que leur cible existe comme fichier ordinaire dans cette même archive.

## Correction

`scripts/prepare-historical-depot-tools.py` accepte désormais les liens symboliques dont la cible se normalise vers un fichier ordinaire présent à l'intérieur du snapshot. L'ensemble des entrées est validé avant toute extraction de contenu. Les fichiers et dossiers sont extraits en premier ; les liens ne sont créés qu'après toutes les écritures de fichiers.

Les chemins traversants, les liens vers l'extérieur, les liens pendants, les chaînes de liens, les liens durs, les fichiers spéciaux, les doublons et les entrées qui écriraient sous un lien restent refusés. Aucun contrôle de TLS ou d'intégrité n'est supprimé. Les quatre liens ne sont ni supprimés ni remplacés par du code différent ; leur nom et cible sont conservés dans `provenance.json`.

L'option `--archive` réutilise l'archive existante sans réexécuter git archive. Elle vérifie son commentaire de commit, puis prépare un **nouveau** répertoire unique. L'ancienne archive et le dossier partiel restent intacts. Aucun fichier existant n'est écrasé.

```bash
python3 /chemin/vers/prepare-historical-depot-tools.py \
  "$depot_tools_existant" \
  --archive /tmp/minethrottle71-tools-w_exm4gk/depot_tools.tar
```

Le reste de l'étape est inchangé : création des lanceurs locaux Python 2 et Ninja, auto-update désactivé, vérification de leurs versions uniquement. Aucune exécution de chromite_wrapper, gclient, vpython, CIPD, hook ou build. Le snapshot reste sans métadonnées Git et sa compatibilité avec gclient sera testée dans une étape ultérieure, après retour de cette préparation.

## Validation locale et résultat attendu

Les tests couvrent les quatre liens observés, la préservation de l'archive réutilisée, le maintien des données du répertoire source, le relevé des liens dans la provenance et les différents cas de refus cités ci-dessus. Ces tests utilisent des archives synthétiques ; l'extraction réelle sur Grid5000 reste à exécuter.

Transmettre toute la sortie : quatre messages de conservation des liens si l'archive est conforme, versions Python/Ninja, chemin du nouveau répertoire et message final de préparation. Un échec reste un résultat incomplet, sans suppression automatique des fichiers créés.
