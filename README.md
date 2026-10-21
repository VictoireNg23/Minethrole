> **Grid5000 :** pour examiner les sources déjà présentes sans les modifier, suivre [le diagnostic complémentaire Chromium 71](docs/diagnostic-grid5000-chromium71.md).

> **Travail en cours : Chromium 71 / C++ / V8.** La piste Rust/Wasmtime est abandonnée. Avant toute installation sur votre PC Ubuntu, consulter [le diagnostic initial](docs/diagnostic-ubuntu-chromium71.md) et exécuter `bash scripts/diagnose-ubuntu.sh` depuis le disque prévu pour la compilation. La procédure sera adaptée après lecture de la sortie. Les instructions originales des auteurs sont conservées ci-dessous ; leur compatibilité avec votre machine reste à vérifier.

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