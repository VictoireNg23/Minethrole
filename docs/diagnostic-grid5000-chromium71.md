# Grid5000 : diagnostic complémentaire, avant récupération de Chromium 71

## État connu et limites

Les résultats fournis sur `roazhon13-6` indiquent 376 Gio de RAM, 72 processeurs logiques et 1,8 To libres sur un stockage partagé occupé à 95 %. Ces capacités semblent suffisantes par rapport au minimum historique documenté de 100 Go de disque et 8 Go de RAM, mais ne prouvent ni le quota disponible pour votre compte, ni l'autorisation d'une compilation sur ce stockage. Ne pas dimensionner 72 tâches de compilation sans vérifier l'allocation réelle et les contraintes du service.

Les révisions communiquées de Chromium (`d327674bd939b`, 2026-10-18) et V8 (`94bfc15fbee`, version 15.8.18) sont récentes. Aucune application des patches historiques n'est justifiée sur ces arbres en l'état.

Le script original des auteurs fixe **Chromium 71.0.3578.98**. Il ne fixe pas un SHA V8 séparé : c'est le fichier **DEPS de cette révision exacte** qui détermine ce SHA. Le tag V8 7.1.302.31 consulté lors de l'analyse est une référence documentaire ; il ne remplace pas la vérification de DEPS. Le diagnostic extrait le SHA complet si les objets locaux le permettent, puis lit le fichier `include/v8-version.h` de ce commit V8. Aucune supposition n'est faite à partir du nom `chromium71`.

## Commande à exécuter sur le nœud

Utiliser le script de cette branche, dans un emplacement distinct de votre checkout existant. Il est autonome : aucun paquet Python ni fichier auxiliaire n'est nécessaire. `git`, `timeout` et Bash sont requis. Python 3 est optionnel pour lire les métadonnées de `.gclient` sans exécuter cette configuration.

```bash
projet_minethrottle='/srv/storage/killerdroid@storage3.rennes.grid5000.fr/datasets/Andromatch_Paper/SOK_WebAsssembly_2025_Grid5000/DualGraphWasm/Dataset_Dynamic/tests/MineThrottle'
bash /chemin/vers/diagnose-grid5000-chromium71.sh "$projet_minethrottle"
```

Pour inclure quatre petites requêtes HTTPS HEAD, sans récupérer de sources :

```bash
bash /chemin/vers/diagnose-grid5000-chromium71.sh "$projet_minethrottle" --network
```

Transmettre stdout **et stderr**, y compris les erreurs de quota, permissions, Git ou réseau. Les chemins/noms de compte peuvent être anonymisés. Ne pas transmettre de contenu de fichiers d'authentification ni de valeurs de proxy. Le script ne les demande pas.

## Ce que le script vérifie

- Système, mémoire, CPU visibles, limites de processus ; présence de variables d'allocation et de proxy sans leurs valeurs.
- Espace/inodes et permissions annoncées sur le projet, HOME et les emplacements temporaires déjà présents ; type de montage ; `quota -s` si disponible. Aucun fichier test de permission n'est écrit. `test -w` n'est pas une preuve de quota suffisant et `df` ne mesure pas le quota individuel.
- Liste immédiate des dossiers `chromium/`, `chromium71/` et `_bad_scm/`, sans parcours coûteux de leur contenu. `_bad_scm/` reste intact.
- Présence et taille des fichiers `.gclient`, `.gclient_entries`, `.gcs_entries`. Les solutions littérales de `.gclient` sont examinées par AST, sans exécuter le fichier ; URL limitée à hôte/chemin, sans identifiants ni paramètres. Les configurations calculées dynamiquement peuvent nécessiter une analyse ultérieure.
- Paramètres du script original lus comme texte, sans le lancer, même avec `--help` (cet argument créerait un répertoire avec le script original).
- HEAD, branche et changements suivis de MineThrottle et des arbres Chromium/V8 ; état shallow/partial clone, statistiques d'objets et magasins alternatifs. Les fichiers non suivis/ignorés ne sont ni parcourus ni supprimés. Leur absence du rapport ne signifie pas que les arbres sont vides de travail local.
- Présence locale du tag Chromium attendu, du commit et du blob DEPS ; disponibilité du commit V8 correspondant. Les lectures Git interdisent la récupération paresseuse des objets, désactivent les verrous optionnels, fsmonitor, hooks et maintenance automatiques.
- `git apply --check` pour les patches originaux **uniquement si le HEAD de l'arbre est déjà la révision historique correspondante**. C'est un contrôle de contexte sans application. Un arbre récent donne un contrôle reporté, jamais un succès implicite.
- Versions des outils de compilation, Python 2/2.7, paquets de développement Debian/Ubuntu et présence de depot_tools dans PATH. Les lanceurs gclient/fetch/vpython/gn/autoninja ne sont pas exécutés. Si `fetch` est présent, le HEAD Git de son dossier est relevé sans mise à jour.
- Avec `--network` seulement : codes HTTP et codes de sortie curl pour Chromium Gitiles, CIPD et deux domaines d'artefacts Google, avec délais bornés. Pas de redirection ni affichage de corps HTTP. Un 403/404 d'un chemin racine de service n'a pas la même signification qu'un refus de tunnel : fournir aussi stderr. Ces sondes ne prouvent pas l'accès à tous les artefacts historiques.

Les commandes potentiellement lentes sont bornées à 45 secondes chacune. Un délai expiré ou une erreur signifie « observation indisponible », pas « prérequis absent ». Aucun `du` récursif, `git fsck`, récupération réseau Git, hook Chromium ni compilation n'est lancé.

## Interprétation et prochaine étape, après vos résultats

1. **Tag et objets disponibles :** envisager un nouveau répertoire indépendant, avec réutilisation locale des objets pour réduire le trafic. Ne pas modifier le checkout moderne. Un clone avec références partagées peut rester dépendant du magasin source ; choisir explicitement une stratégie d'indépendance et son coût disque avant toute création. Aucun worktree n'est créé à cette étape.
2. **Tag absent :** cela ne démontre pas que les objets historiques sont absents. Il faudra d'abord résoudre la référence distante par une petite lecture de métadonnées autorisée, puis tester ce SHA localement avant de choisir une récupération ciblée. Ne pas démarrer un fetch complet ni un approfondissement massif automatiquement.
3. **Objets manquants :** dimensionner et proposer une récupération ciblée de la révision historique et de ses dépendances. L'historique Chromium et les artefacts d'anciennes chaînes Python/depot_tools peuvent poser des problèmes distincts ; les constater, puis les corriger séparément.
4. **Compatibilité des patches :** tester leur contexte dans le nouveau checkout historique avant GN, hooks de téléchargement ou compilation. Un contrôle de contexte réussi ne prouve pas la compatibilité C++ ni la validité dynamique de l'instrumentation. Conserver les patches originaux et documenter séparément toute correction nécessaire.
5. **Environnement hôte :** adapter les dépendances à l'OS réellement observé (Grid5000 n'est pas supposé utiliser Ubuntu), vérifier les quotas auprès du service si `quota` est non concluant, et choisir stockage de sources, sorties et temporaires. Le stockage partagé ne sera pas nettoyé ni utilisé comme scratch implicitement.

Cette procédure s'arrête au diagnostic. Aucun téléchargement volumineux, changement de branche des sources, déplacement, écrasement, suppression ou compilation n'est autorisé par le script. La validation des patchs, la chaîne historique et l'exécution réelle des modules restent à effectuer après retour des résultats.

## Vérifications du script réalisées dans Codex

Trois tests automatisés couvrent la syntaxe Bash, le refus d'un répertoire absent et l'inspection de dépôts Git synthétiques contenant un ancien tag et des HEAD modernes. Le dernier test vérifie que les HEAD, index et modifications locales sont préservés, que `.gclient` n'est pas exécuté et que les identifiants d'une URL de test ne sont pas affichés. Ces tests ne téléchargent ni ne compilent Chromium et ne constituent pas une validation sur Grid5000.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_grid5000_diagnostic.py' -v
```
