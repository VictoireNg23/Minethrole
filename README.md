# Reproduire MineThrottle avec Chromium 71

**Installation et compilation réussies sur Grid5000 / Ubuntu 22.04 amd64.** Le binaire affiche `Chromium 71.0.3578.98` et ses bibliothèques partagées sont résolues. Le projet reste en C++ / Chromium / V8 ; Rust et Wasmtime ne sont pas utilisés.

➡ **[Guide complet : installation, dépendances, sources historiques, patches, compilation et vérification](docs/README-reproduction-chromium71.md)**

Le guide fournit les commandes dans l'ordre, les chemins à adapter, les résultats attendus, les reprises sans nettoyage et les solutions aux erreurs rencontrées. Il distingue la procédure validée avec réutilisation des objets Git existants d'un téléchargement initial depuis zéro, qui reste à vérifier sur une nouvelle machine. Il faut exécuter les étapes séparément et vérifier leur résultat avant de poursuivre.

Les deux patches originaux sont conservés dans `patches/`. Les adaptations d'arrêt d8 et de compatibilité Bison sont séparées dans `patches/chromium71/`. Les 12 signatures actives ont passé 72 tests synthétiques de compteurs sous d8. Les profils, les vitesses, la défense et les expériences en navigateur sur le dataset restent à valider.

Organisation des ajouts : `scripts/` pour la préparation et les builds, `tests/` pour les contrôles, `config/` pour les paramètres/provenances, `docs/` pour les analyses, le papier et les inventaires. Les sources/binaires Chromium, caches et gros résultats ne sont pas ajoutés à Git.

Vérification locale des scripts, sans téléchargement ni compilation Chromium :

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Les instructions et attributions originales sont conservées ci-dessous pour provenance. Pour refaire le parcours testé sur Ubuntu 22.04, utiliser le guide ci-dessus plutôt que lancer directement le script historique `--all`. Les commandes historiques avec `--no-sandbox` ne constituent pas la procédure de validation du dataset.

---

# MineThrottle

MineThrottle is a browser-based defense mechanism against Wasm cryptojacking. MineThrottle instruments Wasm code on the fly to detect mining behavior using block-level program profiling. It then throttles drive-by mining behavior based on a user-configurable policy.

MineThrottle is implemented on Google Chromium (version 71.0.3578.98).



## Build
MineThrottle has been tested on debian 9 (kernel 4.19).

```shell
# Install depot_tools
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
export PATH=$PATH:/path/to/depot_tools

# Fetch source and build
./build_minethrottle.sh --all
```

The above command will fetch the source code of Chromium version 71.0.3578.98, apply our patches to it, and build MineThrottle.

```shell
# More information about the options
./build_minethrottle.sh --help
```



## Run
Notice that MineThrottle's defense against cryptojacking is disabled by default.

### Interpreting Mode
In case you need to generate Wasm instruction execution traces for analysis, you can run MineThrottle with the following command.

```shell
./chrome --no-sandbox --js-flags="--webassembly-interpret-all" URL
```
The above command will force Chromium to interpret the Wasm code and generate the log named `wasm_dump_*.log`.


### Detection and Defense Mode

If you need defensive mode on, please make sure:

```c++
bool is_defensive = true;
```

By modifying the value of the boolean variable `is_defensive` in `v8/src/wasm/module-compiler.cc`, you can control the defense mode on and off.

```shell
./chrome --no-sandbox URL
```

The above command may generate four types of files.
- `*.txt` records the information about main frames and sub frames (if any).
- `*.stack` records the Wasm API(s) call stack.
- `*.asmjs` indicates whether the target URL includes asm.js or not.
- `*.count` records the run time statistical information about the Wasm program, which can be used for offline analysis. In each sampling point, we will first record `the number of active threads`, `system time`, and then we will record the `process ID`, `thread ID`, `cpu time`, `mining flags` and `global counters` for each thread.



## Copyright Information

Copyright (c) 2020 The Chinese University of Hong Kong


### Additional Notes

Notice that some files in MineThrottle may carry their own copyright notices. In particular, MineThrottle's code release contains modifications to source files from the Google Chromium project (https://www.chromium.org), which are distributed under their own original license.



## License
MineThrottle is licensed under the [MIT License](LICENSE).



## Publication
You can find more information about MineThrottle in our [WWW 2020 paper](https://seclab.cse.cuhk.edu.hk/papers/www20_minethrottle.pdf).

```
@inproceedings{bian2020minethrottle,
  title={Minethrottle: Defending against wasm in-browser cryptojacking},
  author={Bian, Weikang and Meng, Wei and Zhang, Mingxue},
  booktitle={Proceedings of The Web Conference 2020},
  pages={3112--3118},
  year={2020}
}
```



## Contact
[Weikang Bian](https://wkbian.github.io/) <wkbian@cse.cuhk.edu.hk>

[Wei Meng](https://www.cse.cuhk.edu.hk/~wei/) <wei@cse.cuhk.edu.hk>