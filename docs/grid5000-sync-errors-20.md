# Synchronisation : rechercher la cause du code 1

La tentative `sync-nohooks-9m12u26_` s'est terminée après 582,48 secondes avec le code 1, sans timeout. Le cache résolu est nul, le garde-fou est actif et la configuration du miroir exact est sélectionnée. Le checkout final visible a réussi ; il ne permet pas d'identifier la dépendance en échec dans cette exécution parallèle.

Avant toute reprise, lire le journal existant :

```bash
python3 scripts/show-gclient-errors.py /tmp/minethrottle71-work-rwkni3hv/sync-nohooks-9m12u26_/sync.log
```

Le script ouvre uniquement le journal en lecture et affiche les contextes des 40 premières correspondances d'erreur avec leurs numéros de lignes. Chaque ligne est limitée à 2 000 caractères ; le nombre total de correspondances est indiqué. Les motifs sont heuristiques : une correspondance peut être sans gravité et leur absence ne prouve pas le succès. En cas de troncature, examiner les passages supplémentaires avant de conclure.

Aucune synchronisation, aucun hook et aucune compilation ne sont lancés. La cause précise reste à établir à partir de la sortie fournie par l'utilisateur. Les tests locaux vérifient l'extraction dans un journal synthétique, pas la synchronisation Grid5000.
