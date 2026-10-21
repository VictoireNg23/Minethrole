# Compilation Chromium : bison introuvable

Le journal Grid5000 `chrome-build-4q6sm1_q/build.log` confirme un échec après 201,76 secondes, code 1. Blink `make_core_generated_bison` appelle `rule_bison.py` avec l'exécutable `bison`, puis subprocess échoue avec ENOENT au lancement. Les actions exécutées ont progressé jusqu'à environ 4 413/17 904 dans cette tentative ; les totaux Ninja changent avec les objets déjà construits.

Installer la dépendance identifiée :

```bash
apt-get install --no-remove --no-install-recommends bison
```

Après succès, vérifier les deux résolutions :

```bash
/usr/bin/bison --version
/tmp/minethrottle71-work-rwkni3hv/with-tools.sh bison --version
```

Transmettre les sorties avant de reprendre le build. La présence et la version ne suffiront pas à valider la génération du parseur historique : le prochain build la vérifiera. Ne pas modifier la grammaire ni les patches pour contourner une simple commande absente. Aucun nettoyage, téléchargement de sources Chromium, hook global ou compilation n'est demandé par cette étape. Conserver les objets déjà compilés et les répertoires des outils.
