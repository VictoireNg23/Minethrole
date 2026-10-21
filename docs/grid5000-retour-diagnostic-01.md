# Grid5000 : analyse du premier retour et contrôle historique ciblé

## Résultats reçus, non exécutés à distance par Codex

Le retour de l'utilisateur établit les références suivantes sur les objets présents :

- Tag Chromium `71.0.3578.98` : `c2bec8045f7ad3ece1c5d80236183a21c1fac3f5`.
- Révision V8 extraite du DEPS historique : `b5a5d900a5385d6429edefb11ece72bfa649ca47`.
- Version lue dans ce commit V8 : **7.1.302.31**.
- Les empreintes SHA-256 des patches V8/content et du script original correspondent exactement aux références conservées dans ce dépôt.

Ces observations ne prouvent pas que tous les objets ou dépendances historiques nécessaires au build sont disponibles. Les dossiers de travail restent à des révisions non confirmées par ce diagnostic ; aucun contrôle d'application des patches n'y a été validé.

L'arbre `chromium/src` contient environ 66,4 Gio de pack Git Chromium et 2,0 Gio de pack V8. Un deuxième pack Chromium de taille semblable est signalé sous `chromium71/src`. Il ne faut pas les supprimer, déplacer ou recopier intégralement pour ce diagnostic. Leur présence autorise une tentative de lecture ciblée de blobs historiques, pas une conclusion sur l'intégrité de tous les objets.

## Dépendances et erreurs observées

Les versions GCC 11.4, Clang 14, Python 3.10.12 et glibc 2.35 sont cohérentes avec Ubuntu 22.04 ; la version OS exacte reste à confirmer avec `/etc/os-release` si elle n'a pas été transmise. Elles ne remplacent pas automatiquement la chaîne Clang/sysroot et les scripts Python 2 attendus historiquement.

- `build-essential`, libc6-dev, libexpat1-dev et zlib1g-dev sont installés.
- Python 2/2.7 ne sont pas installés selon dpkg-query ; une installation hors paquets reste possible et devra être vérifiée si nécessaire.
- `pkg-config` et `ccache` sont absents du PATH.
- Les paquets de développement audio, GTK, NSS et X11 listés dans le diagnostic sont absents ou non installés (`un` pour libgtk-3-dev). La liste finale doit être adaptée à la chaîne historique ; aucune installation n'est lancée maintenant.
- Le `ninja` trouvé dans depot_tools est un lanceur qui ne trouve pas de vrai binaire dans ce contexte. Ce message n'établit pas que Ninja sera introuvable dans un futur checkout correctement préparé ; un binaire utilisable devra être vérifié séparément.
- `vpython` est absent du PATH, tandis que `vpython3` est présent. L'actuel depot_tools n'a pas encore été caractérisé pour la chaîne Python 2 ; ne pas le rétrograder ni le mettre à jour automatiquement.

Les commandes `git log` ont expiré (code 124). La ligne « detached or unavailable » peut donc signifier une observation indisponible, pas nécessairement un HEAD détaché. L'origine des lenteurs reste inconnue : stockage partagé, accès aux objets ou configuration Git sont à distinguer. Le contrôle suivant évite log, status et parcours d'historique.

Les indicateurs `M` sur les originaux ne contredisent pas les empreintes identiques de trois fichiers : leurs permissions exécutables ou la référence Git de comparaison peuvent différer. LICENSE et README n'ont pas été comparés par empreinte dans ce retour. Ne rien réinitialiser pour faire disparaître ces indicateurs.

Côté réseau, les quatre réponses sont HTTP 503, 405, 400 et 400 avec curl exit=0. Sans `--fail`, curl peut réussir malgré un statut HTTP d'erreur. Une réponse d'erreur sur une racine de service n'établit ni accès aux artefacts ni blocage général. La réponse Chromium 503 doit être investiguée avec une requête ciblée lors de l'étape réseau, pas en lançant un fetch volumineux.

Les quotas, politiques de stockage et disponibilités temporaires ne figurent pas dans cet extrait ; ils restent non confirmés. Ils seront nécessaires avant de préparer le checkout complet et sa compilation.

## Étape suivante : vérifier les contextes des patches hors des arbres existants

Script : `scripts/check-chromium71-patches.py`.

Il lit les objets locaux du dossier `chromium/src` par défaut, vérifie le lien DEPS→V8, puis extrait **neuf fichiers V8 et un fichier content** dans un répertoire temporaire nouveau. Il y copie les patches vérifiés par empreinte et exécute seulement `git apply --check --verbose`. Il n'applique pas les patches. Il n'utilise ni checkout ni worktree, ne télécharge rien et ne compile rien.

Le répertoire diagnostic est conservé. Les éventuels fichiers partiellement extraits après erreur restent dans ce nouveau répertoire ; aucun nettoyage automatique n'est effectué. Chaque extraction est annoncée et dispose d'un délai de 90 secondes, modifiable avec `--timeout`. Il n'est pas nécessaire de relancer le diagnostic général lent.

Depuis une copie de ce script, exécuter :

```bash
projet_minethrottle='/srv/storage/killerdroid@storage3.rennes.grid5000.fr/datasets/Andromatch_Paper/SOK_WebAsssembly_2025_Grid5000/DualGraphWasm/Dataset_Dynamic/tests/MineThrottle'
python3 /chemin/vers/check-chromium71-patches.py "$projet_minethrottle"
```

Si /tmp manque d'espace ou n'est pas accessible, fournir avec `--temporary-parent` un autre répertoire **déjà existant** où la création de ce nouveau dossier diagnostic est autorisée. `--sources chromium71` sélectionne le second arbre, mais ne le lancer qu'après analyse d'une éventuelle erreur du premier : ne pas boucler sur les mêmes lectures expirées sans nouvelle hypothèse.

Résultat attendu : deux messages `PASS context only`, puis le message final confirmant les deux contrôles. Un échec ou timeout est un contrôle incomplet/échoué, jamais un succès. Transmettre toute la sortie et le chemin du nouveau dossier. Même un succès ne valide pas le C++, les hooks, les dépendances ou l'instrumentation à l'exécution.

## Vérification locale du nouveau script

Trois tests supplémentaires utilisent de minuscules dépôts synthétiques :

- Rejet des chemins traversants et reconnaissance des neuf fichiers V8 et du fichier content.
- Vérification positive sur les blobs d'un ancien commit tout en préservant HEAD, index et modifications du checkout moderne.
- Échec explicite sur un contexte incompatible et refus d'écraser un dossier d'export existant.

Les tests de compatibilité sur les véritables objets Chromium/V8 de Grid5000 restent à exécuter par l'utilisateur. Aucun objet Chromium n'a été téléchargé dans Codex.

Après réception de ces contrôles, nous préparerons la chaîne Python/depot_tools et le nouveau répertoire de construction en fonction des permissions et quotas. Aucun passage à Chromium récent, Rust ou Wasmtime n'est engagé.
