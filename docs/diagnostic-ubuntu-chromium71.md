# Chromium 71 : première étape, diagnostic Ubuntu

La cible actuelle est Chromium 71.0.3578.98 avec les patches C++ originaux de MineThrottle. La piste Rust/Wasmtime du plan antérieur est abandonnée à la demande de l'utilisateur. Aucun téléchargement ni compilation de Chromium ne doit être réalisé dans Codex.

## Objectif

Identifier le système réel avant de choisir une procédure d'installation. L'environnement Codex n'est pas représentatif du PC de l'utilisateur. La compatibilité des patches avec un checkout exact n'a pas encore été vérifiée ; aucune installation ou compilation locale n'est déclarée réussie.

Depuis une copie de cette branche, exécuter :

```bash
bash scripts/diagnose-ubuntu.sh
```

Le répertoire courant sert à mesurer le disque prévu pour la compilation. Si les sources doivent résider sur un autre disque, fournir un répertoire **déjà existant** :

```bash
bash scripts/diagnose-ubuntu.sh /chemin/existant/sur/le/disque/prevu
```

Le script ne crée ni ne supprime de fichier, ne demande pas sudo et ne fait aucune requête réseau. Il affiche les versions des outils de développement et vérifie uniquement la présence des lanceurs Chromium : exécuter gclient, fetch ou vpython pour obtenir une version pourrait déclencher une mise à jour automatique et n'est donc pas utilisé ici. Les chemins des outils peuvent révéler le nom du compte utilisateur ; ils peuvent être anonymisés avant partage.

## Informations attendues

- Version Ubuntu, architecture, noyau et version glibc.
- RAM, mémoire disponible et swap.
- Modèle CPU, cœurs, threads et nombre de CPU utilisables.
- Espace et inodes libres du disque prévu, du dossier personnel et de /tmp.
- Présence et versions de Git, Python/Python 2/Python 3, Ninja, Clang, GCC, Make et outils associés.
- Présence dans PATH de depot_tools/fetch/gclient, GN, autoninja, vpython, Chromium et d8. Une absence du PATH ne démontre pas l'absence de fichiers ailleurs sur le disque.

Transmettre la sortie complète. L'étape suivante sera préparée seulement après examen de ces résultats. Elle précisera les dépendances et la chaîne historique Python/depot_tools, le mode de récupération des sources et les ressources nécessaires ; aucune commande d'installation n'est à lancer pour l'instant. Aucun passage à Chromium récent ne sera engagé automatiquement.

## Sauvegarde et provenance

Les patches originaux, le script de construction original et LICENSE restent inchangés. Le document d'analyse antérieur et le papier sont conservés comme provenance, mais l'architecture Wasmtime de ce document n'est plus la feuille de route courante.

L'inventaire des imports et l'extraction des constantes sont indépendants du moteur. Les contrôles effectués avant le changement de direction ont confirmé 193 clés stockées, dont 12 actives, et classé les dépendances déclarées des 87 modules Malware : 84 avec marqueurs Emscripten historiques, trois avec imports mixtes JavaScript/navigateur, aucun import WASI. Ces catégories ne garantissent pas l'exécutabilité ; 26 modules ont des noms d'imports évoquant le navigateur, y compris dans la catégorie Emscripten. Aucun module n'a été exécuté et aucun point d'entrée minier n'a été validé.
