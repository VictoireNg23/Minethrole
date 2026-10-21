# Grid5000 : première synchronisation arrêtée au délai maximal

## Résultat fourni par l'utilisateur

La synchronisation précédente est **incomplète**, avec :

- Répertoire de diagnostic : `/tmp/minethrottle71-work-rwkni3hv/sync-nohooks-n5r3py1y`.
- Dernier message périodique : `Still working on: src`.
- Statut du processus : `timeout`.
- Code de sortie sous-jacent : `-15`.
- Durée : `3600.21` secondes.
- Hooks et pré-hooks désactivés ; aucune compilation.

Le code -15 correspond ici au SIGTERM envoyé par notre gestionnaire de délai. Ce n'est pas une erreur Chromium ou une preuve de corruption. Les lignes périodiques ne précisent pas si gclient attendait un fetch, un miroir de cache, un verrou ou une opération locale. Aucune cause précise ne peut être conclue de cet extrait seul.

## Action suivante : diagnostic en lecture seule

Ne pas relancer immédiatement la même synchronisation ni seulement allonger le délai. Ne supprimer aucun verrou et ne nettoyer aucun fichier partiel.

`scripts/diagnose-sync-timeout.py` lit :

1. Le résultat existant et le début du journal sync.log.
2. Les dernières lignes significatives en excluant les messages périodiques d'attente sur src, et les lignes évoquant fetch/clone/cache/erreurs.
3. Les HEAD actuels et l'état shallow de src/V8, via commandes Git bornées à 15 secondes, sans log/status ni parcours d'historique.
4. Les noms/tailles des fichiers de pack locaux et la présence de quelques verrous (sans les enlever), ainsi que la liste de premier niveau du nouveau cache Git.
5. Les PID/noms/cwd de processus encore présents dans le workspace ou la copie des outils, sans imprimer leurs arguments ou variables d'environnement et sans les arrêter.
6. Quelques extraits du code historique gclient_scm.py liés aux décisions update/fetch/cache. Ces fichiers sont lus comme texte, jamais importés ni exécutés.

```bash
python3 /chemin/vers/diagnose-sync-timeout.py \
  /tmp/minethrottle71-work-rwkni3hv \
  /tmp/minethrottle71-work-rwkni3hv/sync-nohooks-n5r3py1y
```

Seul un nouveau rapport `sync-timeout-diagnostic-.../report.json` est créé dans le workspace. Aucune requête réseau, récupération Git, synchronisation, hook, compilation, suppression de verrou ou interruption d'un processus n'est exécutée. Transmettre toute la sortie, avec le chemin du rapport.

## Hypothèses à départager

- Une opération distante forcée pour src malgré la présence de son commit épinglé.
- La préparation ou mise à jour d'un miroir de cache, éventuellement encouragée par GIT_CACHE_PATH défini par notre script. Si cette option est la cause, corriger notre orchestration au lieu de l'attribuer à Chromium.
- Un accès lent aux objets empruntés sur le stockage partagé.
- Un verrou ou une autre opération locale ; la présence d'un fichier .lock seule ne prouve pas qu'il était le blocage.

La suite dépendra du journal et du code exact : aucune hypothèse n'autorise à désactiver les contrôles de TLS, à changer de révision de Chromium, à forcer une réinitialisation ou à ignorer une dépendance. Les clones et caches déjà préparés restent conservés.

Un nouveau test vérifie qu'un millier de lignes de progression n'effacent pas du diagnostic la commande fetch initiale, et que le journal original demeure identique. Ce test ne détermine pas la cause du timeout réel de Grid5000.
