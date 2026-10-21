# Compilation Chromium : gperf manquant

Le rapport Grid5000 `chrome-build-hvl6woa8/result.json` confirme un code 1 après 28,24 secondes, avec environ 1 675 étapes exécutées dans cette tentative. L'action Blink `platform:color_data` échoue dans `gperf.py` : commande introuvable, code 127. Le wrapper était appelé avec `gperf` comme exécutable. Ce blocage relève des dépendances système, pas d'une erreur C++ démontrée des patches.

Installer uniquement la dépendance identifiée, sans suppression de paquets :

```bash
apt-get install --no-remove --no-install-recommends gperf
```

Après succès, vérifier le binaire système et sa visibilité dans l'environnement de compilation :

```bash
/usr/bin/gperf --version
/tmp/minethrottle71-work-rwkni3hv/with-tools.sh gperf --version
```

Transmettre les sorties avant reprise du build. En cas d'erreur APT ou de différence de résolution du PATH, analyser la sortie sans modifier les patches. Conserver le répertoire de build et ses objets. Aucune compilation n'est relancée par ces commandes et aucun nettoyage n'est nécessaire. La compatibilité du générateur avec le gperf fourni par Ubuntu sera vérifiée lors du prochain build.
