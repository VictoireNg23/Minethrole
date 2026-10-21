# Bibliothèques hôtes manquantes après compilation

Le contrôle Grid5000 `chrome-runtime-check-st8lqjho/result.json` confirme le SHA-256 attendu du binaire, mais ldd indique `libXss.so.1` et `libasound.so.2` absents. Le script n'a donc pas exécuté chrome --version ni ouvert une page. Le build avec sysroot peut réussir sans ces bibliothèques sur l'hôte.

Sur Ubuntu 22.04, installer uniquement les paquets d'exécution correspondants (pas les paquets -dev) :

```bash
apt-get install --no-remove --no-install-recommends libxss1 libasound2
```

Après succès, relancer `check-chromium71-runtime.py` avec le même rapport de build. Une nouvelle vérification ldd déterminera si ces dépendances sont résolues et si d'autres manquent ; chrome --version sera ensuite testé par le script. Aucune recompilation, modification des patches ou désactivation du sandbox n'est nécessaire pour cette correction. Attendre le nouveau rapport avant le test d'une page locale.
