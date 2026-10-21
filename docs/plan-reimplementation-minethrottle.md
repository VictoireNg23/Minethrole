# Plan technique de réimplémentation fidèle de MineThrottle

> Document historique conservé. La piste Rust/Wasmtime décrite ici est abandonnée à la demande de l’utilisateur. La priorité actuelle est Chromium 71 et les patches C++ originaux ; voir [le diagnostic Ubuntu](diagnostic-ubuntu-chromium71.md).

Analyse du 21 octobre 2026. Périmètre : analyse et conception uniquement ; aucun moteur installé, aucun Wasm exécuté, aucune compilation. Les patches et le script original restent intacts.

## 1. Sources et niveau de preuve

Révision analysée : `4aec56dbcaa9ccca39a6455101c1a60bef024dd5`.

Sources locales : `patches/v8.patch`, `patches/content.patch`, `build_minethrottle.sh`, `README.md`, et les 175 fichiers de `Dataset/Dataset1_S`.

Empreintes SHA-256 des originaux :

| Fichier | SHA-256 |
| --- | --- |
| v8.patch | 72c3adef6f566e7de6b6b7f0d1c6a12f0384098be3601fbcbe2272f1861ee563 |
| content.patch | 7401d2c063f7b4f5b3239dd7b2eb61e3b005123dda6395d1a7e17626e5b06b22 |
| build_minethrottle.sh | cc4a31a160114a282fca4709eeb6480d0a2a548b716b0809603a4271273d9c65 |

Références externes consultées, limitées à des fichiers de référence :

- [V8 7.1.302.31, wasm-opcodes.h](https://github.com/v8/v8/blob/7.1.302.31/src/wasm/wasm-opcodes.h).
- [V8 7.1.302.31, wasm-opcodes.cc](https://github.com/v8/v8/blob/7.1.302.31/src/wasm/wasm-opcodes.cc) : `GetSimpleOpcodeSig` construit `kSimpleOpcodeSigs` exclusivement avec `FOREACH_SIMPLE_OPCODE`.
- [Wasmtime, exemple d'intégration Rust](https://github.com/bytecodealliance/wasmtime/blob/main/examples/hello.rs) et [API Store](https://github.com/bytecodealliance/wasmtime/blob/main/crates/wasmtime/src/runtime/store.rs). La branche main est une référence de conception, pas une version de dépendance retenue.

La correspondance avec le commit V8 exact de la construction Chromium des auteurs devra être vérifiée sur le PC à partir de ses métadonnées DEPS. Les fichiers V8 consultés permettent de préciser la table d'opcodes de la série 7.1, sans télécharger un arbre Chromium.

**Papier intégral consulté :** Bian, Meng et Zhang, « MineThrottle: Defending against Wasm In-Browser Cryptojacking », WWW 2020, pp. 3112–3118, DOI `10.1145/3366423.3380085`. Les URL CUHK et `https://zhangmx1997.github.io/papers/www20_minethrottle.pdf` renvoient HTTP 403. Le fichier a été récupéré depuis le [dépôt GitHub du site de l'auteur](https://raw.githubusercontent.com/zhangmx1997/zhangmx1997.github.io/master/papers/www20_minethrottle.pdf), sans désactiver les vérifications TLS. Une copie consultable est conservée dans `references/www20_minethrottle.pdf` (7 pages, 458 394 octets, SHA-256 `bccf6a60ea8df76fb8e442831732c52e38a328f9cd7464d82a8f06e9317bcd10`). Attribution : auteurs ci-dessus, publication sous CC BY 4.0 selon sa première page. Les pages citées ci-dessous sont les pages imprimées ACM.

## 2. Répartition des responsabilités du code original

| Élément | Fonction observée |
| --- | --- |
| `function-body-decoder-impl.h` dans v8.patch, lignes 49–264 | Tables de signatures, fenêtres statiques d'opcodes, insertion des incréments lors du décodage/compilation |
| `module-decoder.cc`, lignes 604–654 | Ajout de globals i64 mutables, initialisés à zéro, après les globals existants |
| `wasm-module.h`, lignes 829–850 | Paramètres : fenêtre 5, trois compteurs par profil, quatre profils |
| `module-compiler.cc`, lignes 265–603 | Adresse des compteurs, horloge CPU, échantillonnage, comparaison aux références, suspension des threads |
| `wasm-interpreter.cc`, lignes 668–708 | Trace dynamique des opcodes bruts via `%c`, sans opérandes, dans `wasm_dump_<timestamp>.log` |
| `wasm-js.cc`, lignes 709–828 | Journalisation des appels API Wasm et URL des frames JS supérieure/inférieure dans `<pid>.stack` |
| `asm-js.cc`, lignes 14–48 | Journal d'instanciation asm.js dans `<pid>.asmjs` |
| `BUILD.gn` | Activation du désassembleur V8 |
| `wasm-code-manager.h` | Champ `counter = 0`, sans usage ajouté visible dans le patch |
| content.patch | Journal des URL de frames principales/secondaires et dates dans `<pid>.txt` ; aucune signature ni règle de détection |

Le traceur de l'interpréteur et l'instrumentation du compilateur sont deux chemins distincts. Les patches ne fournissent pas de script qui transforme les traces en signatures ou recalcule les profils statistiques. Ne pas supposer que le mode interprété reproduit le chemin de comptage compilé sans comparaison expérimentale.

### Script de construction

Un seul script est fourni. Il cible Chromium `71.0.3578.98`, utilise depot_tools et `GCLIENT_PY3=0`, récupère Chromium, synchronise les dépendances, installe les dépendances système, applique les deux patches, exécute les hooks, puis lance GN et autoninja pour la cible `chrome`.

Arguments GN : `cc_wrapper="ccache" use_jumbo_build=true is_debug=false enable_nacl=false`. Les 32 threads configurés concernent `gclient sync`, pas une limite explicite du parallélisme de compilation. `TMPFS_SIZE` et `FAILURE_THRESHOLD` sont déclarés mais ne sont pas exploités dans les fonctions présentes.

Le script suppose son répertoire courant égal à la racine du dépôt. Même `--help` crée un répertoire `chromium`. Il utilise `set -o nounset`, mais pas `set -e` : une étape échouée ne garantit pas l'arrêt de `--all`. Les patches sont appliqués avec `patch -p1`, sans garde d'idempotence. Il crée une branche `dev`, ce qui peut échouer lors d'une répétition. Aucune commande de test automatisé ni extraction des profils n'est fournie. Sur le PC, contrôler les codes de retour de chaque étape séparément ; ne pas modifier le script original pour cette réimplémentation.

## 3. Signatures exactes

### 3.1 Domaine et fenêtres

Les opcodes retenus sont ceux de `kSimpleOpcodeSigs` : pour la table V8 7.1 consultée, les opérations numériques `0x45` à `0xbf` incluses, soit 123 valeurs. Cela comprend comparaisons, calculs, conversions et réinterprétations. Les extensions prototypes `0xc0` et suivantes ne font pas partie de cette table simple.

Une fenêtre est construite **statiquement dans chaque corps de fonction**, et non en concaténant la trace dynamique. Après chaque opcode simple, l'opcode est ajouté au groupe ; à cinq éléments, la clé est calculée, une éventuelle incrémentation est insérée après l'opération, puis le premier élément du groupe est retiré. Les fenêtres se chevauchent avec un pas de un opcode simple.

La fenêtre est vidée explicitement sur : `nop`, `block`, `loop`, `if`, `else`, `end`, `br`, `br_if`, `br_table`, `return`, `unreachable`, `call`, `call_indirect`.

Les instructions locales/globales, constantes, lectures/écritures mémoire, `drop`, `select`, etc. ne sont pas ajoutées au groupe et ne le vident pas dans les changements présents. Ainsi, la fenêtre peut traverser ces instructions intermédiaires. Elle ne traverse pas un appel ou un branchement. Les instructions de nouvelles propositions Wasm devront faire l'objet d'une politique explicite ; ne pas leur attribuer arbitrairement une sémantique V8 71.

Une occurrence statique correspond à un point d'instrumentation. Son compteur augmente **à chaque exécution** de ce point. Une occurrence jamais exécutée ne compte pas ; une boucle peut compter des millions de fois. Une opération qui déclenche un trap avant l'incrément ne doit pas être comptée. L'insertion originale utilise les interfaces `IF_REACHABLE` ; il faudra traiter le code structurellement inaccessible et vérifier la correspondance avec V8.

### 3.2 Encodage

Pour les opcodes `o[0..w-1]`, le patch calcule :

```text
key = 0
pour chaque o : key = key * 123 + (o - 0x45)
```

La clé est un `uint64_t`. Pour les fenêtres stockées de longueur au plus neuf, la base 123 tient dans 64 bits. La conversion inverse utilise les chiffres en base 123, puis ajoute `0x45`, en conservant la longueur de fenêtre connue.

### 3.3 Les douze signatures actives par défaut

Ordre des compteurs : `3 * profil + rang`, profils 0 à 3 et rangs 0 à 2.

| Compteur | Profil original | Clé décimale | Opcodes hexadécimaux | Instructions |
| --- | --- | --- | --- | --- |
| 0 | coinhive | 10159038433 | 71 74 6a 73 76 | i32.and, i32.shl, i32.add, i32.xor, i32.shr_u |
| 1 | coinhive | 11298039217 | 76 71 74 6a 73 | i32.shr_u, i32.and, i32.shl, i32.add, i32.xor |
| 2 | coinhive | 10620639463 | 73 76 71 74 6a | i32.xor, i32.shr_u, i32.and, i32.shl, i32.add |
| 3 | cryptoloot | 10827225958 | 74 6a 73 74 6a | i32.shl, i32.add, i32.xor, i32.shl, i32.add |
| 4 | cryptoloot | 8555121259 | 6a 73 74 6a 73 | i32.add, i32.xor, i32.shl, i32.add, i32.xor |
| 5 | cryptoloot | 10616811713 | 73 74 6a 73 74 | i32.xor, i32.shl, i32.add, i32.xor, i32.shl |
| 6 | unknown_algorithm_1 | 10827195700 | 74 6a 71 74 6a | i32.shl, i32.add, i32.and, i32.shl, i32.add |
| 7 | unknown_algorithm_1 | 10827225844 | 74 6a 73 73 73 | i32.shl, i32.add, i32.xor, i32.xor, i32.xor |
| 8 | unknown_algorithm_1 | 8555107237 | 6a 73 73 73 73 | i32.add, i32.xor, i32.xor, i32.xor, i32.xor |
| 9 | unknown_algorithm_2 | 8560659694 | 6a 76 71 74 6a | i32.add, i32.shr_u, i32.and, i32.shl, i32.add |
| 10 | unknown_algorithm_2 | 10827270986 | 74 6a 76 71 74 | i32.shl, i32.add, i32.shr_u, i32.and, i32.shl |
| 11 | unknown_algorithm_2 | 11298039220 | 76 71 74 6a 76 | i32.shr_u, i32.and, i32.shl, i32.add, i32.shr_u |

Les noms `unknown_algorithm_1/2` sont conservés. Le code ne justifie pas de leur attribuer un algorithme de hachage particulier.

### 3.4 Tables présentes mais non toutes actives

Le fichier joint `signatures-originales.csv` inventorie les **193 clés stockées**, leur longueur, leur rang, leur décodage et leur activation par défaut :

- Coinhive : neuf lignes de dix clés, fenêtres 1 à 9 ; sélection `window_size - 1`.
- Cryptoloot et unknown_algorithm_1 : cinq lignes de dix clés chacun, longueurs encodées 1, 3, 5, 7, 9 ; sélection `(window_size - 1) / 2`.
- unknown_algorithm_2 : trois clés fixes de longueur cinq, sans sélection selon la fenêtre.

Avec `num_injected_globals=3`, seules les trois premières clés de chaque ligne sélectionnée sont utilisées. Les autres clés stockées ne sont pas des compteurs actifs. Un changement de fenêtre ou de nombre de compteurs n'est pas une configuration généralement cohérente : quatrième profil fixé à cinq, tableaux statistiques fixes 4×3, risque de dépassement du tableau de trois clés.

L'insertion utilise `std::map::insert` dans l'ordre Coinhive, Cryptoloot, unknown1, unknown2. Une clé identique déjà insérée garde le premier compteur et n'incrémente pas tous les profils. Les douze clés actives par défaut sont distinctes ; cette priorité reste nécessaire pour les autres configurations et les tests.

## 4. Profils et décision exacte du code

### 4.1 Références numériques

Les constantes sont dans v8.patch, lignes 291–293. L'ordre des triplets correspond aux signatures de chaque profil.

| Profil | Moyennes `mu` | Écarts-types `sigma` | Vecteur normalisé fourni `b` |
| --- | --- | --- | --- |
| coinhive | (96406.42630749, 78428.75105923, 78428.7930022) | (31325.22361171, 25846.67274627, 25846.66822102) | (0.65601817, 0.53368523, 0.53368552) |
| cryptoloot | (163251.74200967, 161127.55323276, 82687.87474725) | (98266.49642881, 98859.45212208, 48842.10807107) | (0.66954543, 0.66083348, 0.33912832) |
| unknown_algorithm_1 | (55807.11561617, 44197.36864725, 41896.03206607) | (29273.62299923, 22507.89459648, 21304.64701362) | (0.67561316, 0.53506302, 0.50720254) |
| unknown_algorithm_2 | (62494.68955703, 62494.57347204, 39258.05126357) | (16477.6506124, 16477.61705602, 10583.10407066) | (0.6462234, 0.6462222, 0.40594603) |

Les unités déduites du calcul sont des occurrences par **milliseconde CPU du thread**. Préserver les décimales des vecteurs normalisés fournis ; ne pas les recalculer à partir des moyennes en prétendant obtenir strictement les mêmes résultats.

### 4.2 Temps et calcul

Un timer `ITIMER_REAL` est réarmé à 50 000 microsecondes à la fin du gestionnaire : réveil nominal toutes les 50 ms murales, avec dérive possible. Chaque enregistrement conserve l'horloge CPU du thread obtenue par `pthread_getcpuclockid` à l'instanciation.

Le temps de calcul de la décision est :

```text
dt_ms = (sec - old_sec) * 1000 + trunc_vers_zero((nsec - old_nsec) / 1000000)
```

La division des nanosecondes est une division entière C++ avant affectation au double. Ce détail peut produire une différence d'une milliseconde près d'un changement de seconde. Décision uniquement si `dt_ms >= 500` et `is_defensive=true`.

`old_ts` commence à zéro, et non à l'instant d'instanciation. Le premier intervalle inclut donc le temps CPU antérieur du thread. Les anciens compteurs commencent à zéro. Les références de temps et compteurs ne sont mises à jour que lorsque le garde-fou des vitesses accepte l'échantillon.

Pour le profil m et ses trois compteurs :

```text
s[j] = (C[m,j] - C_old[m,j]) / dt_ms
norme = sqrt(sum_j pow(s[j], 2.0))
cos = -1 si norme == 0, sinon sum_j ((s[j] / norme) * b[m,j])
k = (sum_j ((s[j] - mu[m,j]) / sigma[m,j])) / 3
```

`k` est une moyenne de scores standardisés signés. Ce n'est ni une distance absolue, ni une distance euclidienne, ni trois tests indépendants, ni une probabilité.

| Condition | Drapeau |
| --- | --- |
| cos >= 0.99 et k >= -3 | +1, positif |
| cos >= 0.99 et k < -3 | -1, profil similaire mais vitesse trop faible |
| cos < 0.99, y compris norme nulle | 0 |
| Pas d'intervalle suffisant, garde-fou refusé ou défense désactivée | 0 dans la sortie, sans décision effectivement évaluée |

Il faut distinguer dans le nouveau rapport « non évalué » et « évalué négatif », même si le journal original emploie zéro pour les deux. Conserver aussi le drapeau original pour les comparaisons.

### 4.3 Action de défense

`is_defensive=false` par défaut : les compteurs sont installés et journalisés, mais la décision n'est pas calculée et aucune suspension n'est déclenchée. Activer la détection dans le portage doit être un choix explicite enregistré dans le rapport.

Un positif incrémente `positive_count[m]`, jamais remis à zéro par ce code. La condition `positive_count[m] > 0` est vraie dès le premier positif : aucun vote sur plusieurs fenêtres, aucun apprentissage, aucune hystérésis. Le code envoie `SIGUSR1` au thread enregistré ; son gestionnaire appelle `sleep(10)`. Le comportement réel des signaux peut fusionner plusieurs événements et interrompre un sommeil : ne pas promettre exactement dix secondes de pause effective par profil positif.

### 4.4 Particularités et anomalies à ne pas corriger silencieusement

1. Le garde-fou remplit `speeds[j + mode*3]` mais examine `speeds[j]` : il ne contrôle que les trois premières composantes, répétées pour chaque profil.
2. La mise à jour de `max_speed` compare à `min_speed`, pas au maximum courant. Elle réaffecte la valeur courante ; ce n'est pas un maximum. La condition finale est `min_speed >= 0 && max_speed < 10000000`. Une reproduction doit simuler l'ordre des boucles, pas remplacer ce code par min/max sur douze vitesses.
3. Les horloges et comptes sont associés à des **instances de modules**, stockées dans une liste, bien que le commentaire/documentation évoque des threads. Plusieurs instances sur le même thread créent plusieurs enregistrements. Le thread retenu est celui de l'instanciation, pas nécessairement celui d'une future exécution.
4. Les fonctions `GetTotalCpuTime` et `GetCpuUsage` existent, mais le gestionnaire de signal ajouté ne les appelle pas : les champs CPU correspondants sont écrits à zéro. Il utilise néanmoins l'horloge CPU pour `dt`. La description du README ne suffit donc pas à décrire exactement les champs réellement écrits.
5. Les adresses de globals et la liste sont consultées sans synchronisation visible depuis un signal. Allocation/libération des instances, données concurrentes, fonctions non sûres dans un gestionnaire de signal et absence de retrait explicite des instances constituent des limites du code. Pas de promesse de reproduire ces comportements indéfinis.
6. Les compteurs Wasm i64 s'incrémentent modulo 2^64 ; la lecture et la soustraction hôtes sont en `int64_t` et un débordement signé C++ n'a pas de résultat portable. Définir le domaine de fidélité avant débordement et signaler la sortie de ce domaine.
7. content.patch utilise `std::to_string(...).c_str()` dans un pointeur dont le temporaire est détruit avant `sprintf` : durée de vie incorrecte. Ce journal navigateur ne doit pas être porté dans le noyau du détecteur.

Le futur mode de compatibilité reprendra les calculs déterminés et ces gardes tels qu'ils sont écrits. Toute variante corrigeant l'initialisation du temps ou le garde-fou devra porter un identifiant distinct et afficher les écarts, sans devenir le résultat « original ».

## 5. Ce que contient réellement Dataset1_S

Lecture des en-têtes et sections de types, imports, fonctions, exports, mémoire et start, sans exécution ni validation complète des instructions. Détail par module dans `dataset1_s-inventaire.csv` : chemin, SHA-256, taille, imports typés, exports typés, start, limites mémoire. Les champs structurés sont du JSON dans le CSV ; certains champs dépassent 128 Kio, donc augmenter `csv.field_size_limit` pour une lecture Python.

| Observation | Benign | Malware |
| --- | --- | --- |
| Modules | 88 | 87 |
| Octets | 50 545 638 | 18 574 396 |
| SHA-256 distincts au sein du groupe | 88 | 87 |
| En-tête Wasm version 1 | 88 | 87 |
| Sans aucun import | 8 | 0 |
| Avec fonction start | 5 | 0 |
| Avec au moins une fonction exportée | 88 | 87 |
| Avec mémoire partagée déclarée/importée | 1 | 0 |

Tous les modules Malware importent `env.memory` et `env.table`. 84 importent notamment `STACKTOP`, `DYNAMICTOP_PTR`, `enlargeMemory` et `getTotalMemory`. Les adaptateurs Emscripten sont nécessaires ; WASI seul ne résout pas ces imports. Les Benign utilisent aussi wasm-bindgen, Go, des fonctions graphiques et quelques imports WASI. Aucun fichier JS d'accompagnement n'est présent dans Dataset1_S.

**Premiers cas proposés :**

- `Benign/1221-www_hellorust_com_10d264faeb0f50ac.wasm` : aucun import, export `fact : (i32) -> i64`. Candidat pour comparer résultat et compteurs avant/après instrumentation ; vérifier sa sémantique avant de fixer l'oracle `fact(5)=120`.
- `Benign/hs-anhalt.de_f97baec0d132a482.ok.wasm` : aucun import, export `test : (i32) -> i32` ; résultat attendu à établir, pas à inventer.
- `Malware/03d1b473fc9c87fc115fc21075019b488fe07140f3c603406bfb0af95c8ac4e6_stackOP_insertion_memory.wasm` : exports `_cryptonight_create() -> i32`, `_cryptonight_hash(i32,i32,i32,i32)`, `_cryptonight_destroy(i32)`. Candidat pour un adaptateur de famille ; les quatre arguments ne sont pas documentés par leur simple type.

30 modules Malware possèdent un export dont le nom contient `_cryptonight`, 53 un export contenant `_hash`, six `_main`. Cela n'établit ni leur ABI exacte ni leur exécutabilité. Ne pas appeler automatiquement tous les exports avec des zéros.

Les noms de mutations (insertion, clonage, etc.) sont des indices de provenance, pas des garanties sur l'effet des transformations. Les étiquettes de répertoires servent uniquement à l'évaluation et ne seront jamais une entrée de décision.

## 6. Architecture proposée pour des Wasm autonomes

### 6.1 Moteur retenu pour le premier prototype : Wasmtime intégré en Rust

Wasmtime exécute des modules core Wasm sans navigateur ni JavaScript, fournit un linker pour imports hôtes et permet d'accéder aux globals exportés. Rust permet de partager l'analyse binaire avec `wasmparser` et la réécriture avec `wasm-encoder`/son mécanisme de réencodage. Une version stable compatible de ces dépendances sera choisie, épinglée et testée lors de l'implémentation ; aucune dépendance n'est installée dans cette phase.

Wasmtime/Cranelift et V8/Liftoff/TurboFan n'ont pas les mêmes optimisations, coûts des globals, démarrage ni ordonnancement. Les compteurs peuvent être identiques pour une même exécution sémantique ; les vitesses CPU et les décisions basées sur les références des auteurs ne sont pas garanties identiques. Un interpréteur comme wasmi serait utile comme oracle secondaire sur de petits cas mais amplifierait la différence de vitesses. Wasmtime est le choix principal proposé pour un chemin compilé.

Le fuel Wasmtime n'est **pas** le compteur MineThrottle et ne remplace ni le temps CPU ni les signatures. Les epochs servent uniquement aux interruptions/points de contrôle, pas à la classification.

### 6.2 Composants et contrats

```text
Wasm original + scénario d'appel explicite
  -> lecteur/validateur + audit des fonctionnalités/imports
  -> extracteur statique des points correspondant aux 12 signatures
  -> copie instrumentée en cache, jamais écriture sur le Dataset
  -> worker Wasmtime + adaptateur hôte explicitement identifié
  -> snapshots des 12 compteurs + horloge CPU du worker
  -> calcul pur compatible avec les constantes originales
  -> rapport de scores et drapeaux ; suspension optionnelle séparée
```

1. **Catalogue original immuable.** Clés, ordre d'insertion, constantes et seuils extraits des patches et reliés à leurs empreintes. Mode par défaut pour la fidélité : `w=5`, quatre profils, trois compteurs. Aucun entraînement ni génération de nouvelles signatures à partir du Dataset.
2. **Analyse des opérateurs.** Décoder les instructions et leurs immédiats ; ne jamais rechercher des suites d'octets dans le fichier brut. Construire les fenêtres selon §3 et produire `(fonction, offset original, clé, compteur)` pour chaque correspondance. Les nombres statiques sont uniquement un diagnostic d'instrumentation, pas un verdict.
3. **Réécriture.** Ajouter douze globals i64 mutables initialisés à zéro à la fin des globals existants ; ajouter des exports réservés sans collision. Après chaque point correspondant : `global.get C; i64.const 1; i64.add; global.set C`. Conserver les valeurs déjà présentes sur la pile. Ne pas réanalyser les instructions ajoutées pour créer de nouvelles correspondances. Conserver une carte des offsets.
4. **Préservation du module.** Créer correctement une section globale absente et respecter l'ordre des sections, les imports de globals et les indices existants. L'ajout de globals définis en fin ne décale pas les indices de fonctions. L'éventuel ajout de fonctions/imports de checkpoint, en revanche, impose de réencoder tous les indices affectés, appels, exports, start, éléments, `ref.func`, et métadonnées concernées. Commencer par la variante sans ajout d'import de checkpoint.
5. **Scénarios.** Un manifeste par famille décrit imports, mémoire, table, initialisation, export d'entrée, arguments, blocs d'entrée et résultat attendu. Un module peut être exécuté sans JS seulement si ce contrat est connu et réalisable par des fonctions hôtes. Un import navigateur/DOM non reproduit donne le statut « adaptateur manquant », pas « bénin ». Les fonctions hôtes non implémentées échouent explicitement ; pas de stubs universels retournant zéro.
6. **Travailleur et collecte.** Un worker isolé par scénario, initialement un thread et une instance. Au premier jalon, lire les globals avant/après un appel fini et tester la décision par rejeu d'échantillons : cela valide le comptage mais pas la détection périodique pendant un long appel. Au jalon suivant, déclencher des epochs nominales de 50 ms et utiliser un callback sûr sur le thread propriétaire du Store pour relever les globals et `CLOCK_THREAD_CPUTIME_ID`. La possibilité exacte de lire les globals depuis le callback doit être validée sur la version épinglée. Ne pas partager un Store entre un moniteur lecteur et un thread en cours d'exécution. Si l'API ne le permet pas, prévoir des checkpoints coopératifs instrumentés et documenter leur surcoût et leur remappage d'indices. Un trap de timeout n'est pas un mécanisme de reprise préservant automatiquement l'état.
7. **Décision pure.** Prendre douze compteurs et timestamps, produire `dt`, vitesses, normes, cosinus, `k`, gardes, flags et état suivant. Reproduire les opérations double dans le même ordre ; pas de réduction parallèle, fast-math ou normalisation différente. Les comparaisons près des seuils doivent être testées explicitement. Le rapport distingue observation seule, décision activée et suspension activée.
8. **Limitation d'exécution.** Dans un premier temps, détection en observation sans pause pour faciliter la comparaison. Ensuite, suspension coopérative du worker pendant dix secondes nominales dès un positif. C'est une adaptation de `SIGUSR1`, distincte des calculs originaux. Budget de durée externe et limites de mémoire évitent qu'un scénario sans retour monopolise l'évaluation ; expiration = « incomplet », jamais négatif.
9. **Rapport reproductible.** SHA-256 original/instrumenté, version moteur et options, OS/CPU, adaptateur, entrées, nombre d'appels, couverture de l'initialisation/start, étapes non prises en charge, snapshots et raisons de chaque décision. L'initialisation hôte et les checkpoints consomment du CPU : indiquer leur inclusion dans l'horloge. Les pauses ne doivent pas être ajoutées au temps CPU de calcul.

Le lancement d'un start pendant l'instanciation nécessite un traitement particulier : préparer la collecte avant sa possible exécution et vérifier quand les exports/globals deviennent accessibles. Une longue fonction start ne doit pas échapper silencieusement au suivi.

### 6.3 Résultats qu'on peut raisonnablement revendiquer

| Élément | Fidélité visée / limite |
| --- | --- |
| 193 clés stockées et 12 actives | Reproduction exacte des constantes et de leur sélection par défaut |
| Fenêtres et points statiques | Exactitude visée dans le sous-ensemble d'opcodes V8 original, avec tests de frontières |
| Compteurs dynamiques | Exactitude visée si mêmes entrées, imports et parcours d'exécution ; à vérifier aussi sur traps et code inaccessible |
| Décision sur snapshots fixés | Reproductible avec constantes originales, arithmétique double et gardes originales ; tolérances et cas limites documentés |
| Débordement signé, courses et signaux non sûrs | Aucune exactitude portable promise pour un comportement indéfini |
| Vitesses mesurées en direct | Adaptées au moteur, CPU, initialisation et coût d'instrumentation ; valeurs V8 non promises |
| Verdict en direct avec profils originaux | Calcul original conservé, mais performances de détection à mesurer, pas présumées |
| Multiworkers JS, environnement navigateur | Adaptateurs ou exclusion explicitement motivée ; première version limitée à un thread |
| URL, DOM, stack JavaScript, asm.js | Hors du noyau autonome ; remplacer seulement l'identification de l'entrée par le chemin/SHA, sans prétendre reproduire ces signaux navigateur |
| Génération initiale des profils | Non reproductible depuis ce seul dépôt : traces de référence, protocole et scripts absents |

Une éventuelle calibration des vitesses pour Wasmtime serait une expérimentation distincte, jamais substituée aux profils originaux ni présentée comme reproduction exacte. Elle n'est pas incluse dans ce premier plan.

## 7. Confrontation au papier intégral

### 7.1 Méthode publiée

En §3.1, pp. 3113–3114, les auteurs étudient les blocs qui totalisent 90 % du coût, approximé par leur nombre d'instructions exécutées. Le tableau 1 compare notamment CoinHive, CryptoLoot, LightMiner, Crypto Webminer et Coin Web Mining aux programmes bénins. Ils identifient **huit instructions discriminantes**, puis utilisent leur proportion dans un bloc et la taille du bloc. Le seuil est obtenu en apprenant un modèle linéaire ; les NOP sont exclus du ratio, le seuil diminue pour les grands blocs, et un critère de nombre absolu d'instructions discriminantes couvre les petits blocs. Le texte ne donne ni la liste explicite des huit opcodes ni les coefficients permettant de reconstruire ce classificateur.

En §3.2, p. 3114, et §4.2, p. 3115, un déclencheur ajouté à la fin de chaque bloc identifié incrémente **un compteur global par module de la taille du bloc**. Le texte dit : « increment a global performance counter by the number of instructions ». La vitesse est le delta de ce compteur divisé par le temps CPU du thread. L'équation (1) est scalaire :

```text
speed >= S - T_sigma * sigma
```

En §5.2, pp. 3115–3116, les références sont apprises à partir de cinq sites mineurs sélectionnés aléatoirement. Le tableau 2 fournit, respectivement aux intervalles 100, 250, 500 et 1000 ms : moyennes `2118789, 2276725, 2275011, 2277306` et écarts-types `1069980, 327670, 280611, 182818`. Le tableau ne suffit pas à convertir ces valeurs en références pour les compteurs de signatures du patch ; la longueur des blocs et les sites/charges sources manquent. Ne pas confondre ces nombres de vitesse avec ceux du §4 de ce document.

Le protocole §5.2, p. 3116, précise : « at least 5 times of a thread » pour rapporter un site comme mineur. Il ne précise pas que ces cinq observations doivent être consécutives. Les valeurs de T_sigma étudiées sont 0.3, 1 et 3. La défense §4.3 utilise SIGUSR1 et sleep ; §6 étudie des pauses de 5 ou 10 secondes et utilise T_sigma=1.

### 7.2 Comparaison explicite

| Sujet | Papier et passage | Patches fournis | Conclusion |
| --- | --- | --- | --- |
| Extraction initiale | §3.1, pp. 3113–3114 : top blocs couvrant 90 %, huit instructions discriminantes | Tables de clés, sans scripts d'extraction | Procédure de production des tables non livrée ; lien entre cette procédure et les clés non démontré |
| Identification des blocs | §3.1, p. 3114 : ratio d'instructions discriminantes, taille, seuil linéaire, critère absolu pour petits blocs | Fenêtres ordonnées de cinq opcodes simples, correspondance exacte avec douze clés | **Différence de mécanisme** ; aucun calcul de ratio, de taille de bloc ou de seuil linéaire dans le chemin ajouté |
| NOP et code intercalé | §3.1, p. 3114 : NOP exclus du ratio | `nop` vide la fenêtre ; locals/constantes/mémoire sont ignorés sans la vider | **Différence concrète** pour la robustesse aux insertions ; ne pas attribuer au patch les garanties du ratio publié |
| Compteurs | §3.2 et §4.2, pp. 3114–3115 : un compteur, ajout de la taille du bloc | Douze globals, incrément de **1** à chaque correspondance exécutée | **Différence d'unité et de dimension** ; le patch compte des occurrences de signatures, pas les instructions de blocs entiers |
| Référence | §5.2 et tableau 2, p. 3115 : moyenne/écart-type scalaires selon quatre intervalles | Quatre profils de trois valeurs, une seule table de constantes statistiques | **Références différentes**, aucune équivalence numérique établie ; aucune sélection de table selon INTERVAL dans le patch |
| Condition | Équation (1), §3.2, p. 3114 : `speed >= S - T_sigma*sigma` | cosinus >=0.99 ET moyenne de trois z-scores >=-3 | **Différence de règle** : condition vectorielle supplémentaire et moyenne de scores ; ni le cosinus 0.99 ni cette formule vectorielle ne sont spécifiés dans le papier |
| Horloge | §3.2 et §4.2 : temps CPU du thread, pas temps mural ; intervalle depuis la dernière mesure | Même principe CPU, avec timer mural nominal 50 ms, seuil fixé 500 ms et ancien timestamp initialement nul | Principe cohérent ; initialisation et arrondi du patch particularisent l'implémentation |
| Répétition des positifs | §5.2, p. 3116 : cinq observations pour rapporter un site mineur | `positive_count > 0` entraîne une suspension dès le premier positif | **Écart avec le protocole de rapport du papier** ; aucune agrégation de cinq positifs visible dans les patches. Le critère de rapport d'un site et le déclenchement d'une pause sont toutefois des opérations distinctes |
| Modes | §4, p. 3115 : interprétation, détection et défense séparées | Trace interpréteur séparée, mais `is_defensive` active à la fois décision et pause | Modes de détection seule/ défense non séparés dans ce chemin ; le rejeu hors ligne n'est pas fourni |
| Suspension | §4.3, p. 3115 : SIGUSR1 et sommeil, configurable | Même primitive, sommeil fixé à dix secondes ; défaut désactivé | **Principe reproduit**, configuration moins générale ; pas d'ajustement dynamique du sommeil visible |
| Attribution Web | §5.1, p. 3115 : journalisation par site/frame | content.patch journalise URL, frame, date ; wasm-js.cc journalise les piles JS | Cohérent avec l'attribution expérimentale, sans fournir des critères de décision supplémentaires |
| Mesure CPU externe | §6.1, p. 3116 : mpstat et pidstat | Fonctions /proc présentes mais non appelées dans le gestionnaire ajouté | Ne pas confondre les métriques d'évaluation externe avec les champs zéro du journal `.count` |
| Résultats | §5 et §8 : 659 sites Wasm, 109 sites mineurs, deux échecs de chargement ; FPR/FNR selon les réglages | Dataset1_S : 175 fichiers Wasm étiquetés, sans pages, JS et protocole source | **Corpus et unité d'évaluation différents** ; les taux publiés ne sont pas transposables à ces fichiers |

### 7.3 Conséquence sur la réimplémentation

La cible demandée sera **le comportement déterminé des patches originaux présents dans ce dépôt**. Elle ne sera pas décrite comme une reproduction intégrale de la méthode publiée. Refaire le classificateur de blocs du papier exigerait des artefacts absents et un autre mécanisme que les signatures du patch : cela n'est pas inclus. Aucun nouveau modèle de machine learning ne sera créé.

Les cinq positifs du protocole de sites peuvent être consignés comme une statistique séparée pour comparaison, sans modifier la règle de pause du patch et sans prétendre qu'un fichier Wasm isolé prouve un cryptojacking sans consentement. Le consentement, les communications et le déclenchement automatique du navigateur ne sont pas observables à partir du binaire seul.

L'origine exacte de l'écart papier/code (version expérimentale, révision, simplification ou autre) n'est pas établie par les fichiers analysés ; aucune cause n'est inventée. Les anomalies du §4.4 sont identifiables dans le code, mais le papier ne permet pas d'inférer leur présence dans toutes les expériences publiées.

## 8. Plan des tests de fidélité

Tests prévus, non implémentés et non exécutés dans cette phase.

| Groupe | Cas et oracle |
| --- | --- |
| Catalogue | Comparer indépendamment toutes les constantes au patch ; 193 clés, 12 sélectionnées, ordre des profils et SHA originaux |
| Encodage | Décoder/réencoder les 12 signatures ; vecteur manuel `71 74 6a 73 76 -> 10159038433` ; fenêtres longues et chiffres zéro |
| Sélection | Fenêtres chevauchantes, moins de cinq opcodes, changement de fonction, priorité du premier insert en cas de clé dupliquée |
| Frontières | Chaque séparateur du §3 annule une fenêtre ; constantes/locals/globals/mémoire/drop/select ne l'annulent pas ; immédiats ressemblant aux signatures ignorés |
| Exécution | Nombre de passages d'une boucle connu, chemins pris/non pris, appels séparés, récursion, globals existants/importés, deux instances indépendantes |
| Sémantique | Comparer résultats, mémoire et traps entre original et copie instrumentée ; ne compter ni opération après trap ni instrumentation comme opcode source |
| Compatibilité | Module sans section globale/export, collision de nom réservé, code inaccessible ; propositions modernes prises en charge explicitement ou rejetées |
| Temps | 499/500/501 ms, ancien timestamp zéro, nanosecondes négatives lors du franchissement d'une seconde, intervalle rejeté ne mettant pas l'état à jour |
| Statistiques | Norme nulle -> cos=-1 ; vitesses égales à mu -> k=0 ; vitesses égales à mu-3*sigma -> k voisin de -3 ; calcul indépendant des valeurs attendues en double |
| Seuils | Valeurs juste en dessous/au-dessus de 0.99 et -3 ; comparaisons inclusives ; exclure les NaN/infinis non définis du domaine valide avec diagnostic |
| Garde original | Vecteurs où le premier profil est normal et les autres extrêmes ; cas révélant la comparaison max/min erronée ; égalités à 0 et 10000000 |
| État et défense | Défense désactivée : compteurs observés, aucune décision ; positif dès la première fenêtre ; compte positif non remis à zéro ; flags -1 distincts de +1 |
| Dataset autonome | Premier cas Rust sans import ; sortie attendue après établissement de l'ABI/sémantique, compteurs original/instrumenté et répétabilité |
| Dataset avec imports | Cas Cryptonight après adaptateur validé par une sortie de hachage connue ; pas de succès fondé sur la seule instanciation |
| Rejeu inter-moteurs | Même suite de compteurs/timestamps -> mêmes scores et flags ; ne pas exiger l'égalité des temps CPU mesurés entre moteurs |

Pour les seuils, les valeurs attendues doivent venir d'un calcul indépendant, pas d'un arrondi anticipé qui transforme accidentellement une frontière. Conserver les constantes normalisées tronquées des auteurs et l'ordre des additions.

Les tests synthétiques garantissent les règles ; Dataset1_S sert aux essais d'intégration. Tous les 175 modules auront un statut explicite : validé statiquement, exécuté avec scénario vérifié, adaptateur manquant, fonctionnalité non prise en charge, trap, ou budget expiré. Seuls les essais dynamiques complets avec charge connue entreront dans une matrice de détection, et les exclusions seront publiées séparément.

## 9. Séquence de réalisation proposée

1. **Geler la spécification** : relire ce plan et les divergences sourcées du §7 ; confirmer la révision V8 depuis le PC lors de la comparaison finale. Sortie : contrat de fidélité prenant les patches comme référence, sans modification des originaux. Le papier intégral a été lu dans cette phase.
2. **Noyau pur** : catalogue original, encodage/fenêtres, calcul des scores et rejeu temporel. Sortie : tests unitaires des constantes, frontières, anomalies et décisions. Aucun moteur requis pour valider les formules.
3. **Instrumentation binaire** : validation et copies instrumentées, carte des points, tests de préservation. Sortie : correspondances vérifiables et modules toujours valides.
4. **Premier Wasm autonome** : intégrer Wasmtime épinglé, exécuter un scénario Benign sans import, comparer sorties et compteurs. Sortie : fidélité dynamique simple démontrée ; pas encore de revendication de détection périodique.
5. **Suivi temporel** : snapshots pendant les longs appels, horloge CPU, tests des callbacks et des start, observation seule puis pause optionnelle. Sortie : chemin périodique testé avec délais réels explicitement mesurés.
6. **Famille Emscripten de Dataset1_S** : reconstruire un contrat d'initialisation et d'appel à partir des modules et d'éventuels fichiers d'origine fournis ; valider le hachage avant d'interpréter les compteurs. Sortie : premier scénario Malware fidèle. Un ABI non établi bloque ce scénario sans bloquer les modules déjà autonomes.
7. **Évaluation et comparaison PC** : étendre les adaptateurs, traiter les 175 entrées et comparer aux compteurs/logs du V8 original que vous pourrez construire localement. Comparer d'abord les comptes à charge identique, puis scores sur snapshots identiques, enfin décisions en temps réel avec leurs différences de performance.

Le premier développement pourra se limiter aux jalons 2 et 3. La correspondance exacte du V8 original et l'ABI des modules Emscripten restent des points de vérification ciblés, sans empêcher le travail indépendant sur les constantes et les calculs du patch. Aucun téléchargement de Chromium, aucune compilation et aucun changement des patches ne font partie de cette phase de planification.
