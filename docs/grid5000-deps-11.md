# Grid5000 : réutilisation locale conservative des dépendances Git

## Audit reçu

Le rapport `/tmp/minethrottle71-work-rwkni3hv/deps-audit-w8n1kuy2/report.json` indique :

- 127 définitions Git inspectées dans le DEPS primaire.
- 94 définitions CIPD recensées, non testées.
- Un chemin non pris en charge.
- 54 dépendances avec au moins un commit candidat présent localement.
- Aucune définition non résolue par le lecteur AST.

Ces nombres incluent les conditions de toutes les plateformes et ne représentent pas le nombre définitif de dépendances du build Linux. Un commit présent ne prouve pas encore que tous ses blobs seront disponibles au checkout. Les erreurs `commit_unavailable_or_git_error` restent non concluantes sur leur cause ; ne pas les assimiler à une corruption.

## Étape suivante : clones locaux des seules entrées inconditionnelles

`scripts/seed-chromium71-deps.py` prend le workspace historique et le rapport d'audit. Le mode par défaut produit seulement un plan ; `--apply` prépare les clones locaux autorisés par ce plan.

Sont retenues seulement les entrées du dictionnaire principal `deps`, sans condition (ou à condition constante True), avec URL HTTPS épinglée à un SHA complet et présence locale du commit confirmée. Les groupes deps_os et les conditions comme checkout_linux sont différés, même si leur nom paraît évident : ils seront traités avec la sélection de plateforme de gclient, sans inventer de variables.

Toutes les entrées CIPD, sans SHA Git, les chemins hors de src et les dépendances sans objet local confirmé sont différées. Le chemin non pris en charge et les conditions différées sont imprimés dans le résumé pour éclaircir la suite.

```bash
python3 /chemin/vers/seed-chromium71-deps.py \
  /tmp/minethrottle71-work-rwkni3hv \
  /tmp/minethrottle71-work-rwkni3hv/deps-audit-w8n1kuy2/report.json \
  --apply
```

Le script vérifie à nouveau les dépôts candidats et la présence du commit avant de les utiliser. Il clone avec `--local --shared --no-checkout --no-tags` puis positionne les nouveaux clones sur les SHA exacts, sans force et sans sous-modules récursifs. Il ne recopie pas les gros magasins Git et ne contacte pas les URL distantes. Les origin des nouveaux clones seulement sont définis d'après le DEPS.

Les destinations déjà occupées sont laissées intactes : un dépôt déjà au bon HEAD est recensé comme `existing_exact_checkout_untouched`, sinon `occupied_destination_untouched`. Ce premier statut confirme le HEAD, pas la propreté de l'arbre. Les liens symboliques dans les chemins de destination sont différés. Aucun fichier existant n'est nettoyé ou remplacé pour faire réussir une dépendance.

## Conservation et sorties

Le nouveau sous-dossier `deps-seed-.../result.json` conserve le plan puis les résultats au fil de l'exécution. Le script imprime le chemin du rapport avant toute opération. Chaque clone/checkout est borné à 900 secondes ; un échec arrête la passe et laisse les clones partiels en place avec un rapport incomplet. Ne pas effacer ces fichiers ou forcer la suite après un échec.

**Les clones restent dépendants des magasins d'objets d'origine** recensés dans le rapport. Ne pas supprimer, déplacer ou nettoyer ces magasins. Les écritures se limitent au nouveau workspace dans /tmp ; les deux arbres d'origine restent inchangés. Des fichiers de travail supplémentaires sont matérialisés, donc cette étape consomme du disque local même sans téléchargement et sans duplication des packs.

Transmettre la sortie complète : résumé initial, chemin non pris en charge, conditions différées, clones effectués, résumé final et chemin du résultat. `local_pass_completed_not_dependency_readiness` signifie que cette passe s'est terminée, pas que toutes les dépendances sont prêtes. Aucun gclient sync, téléchargement CIPD, hook, patch ou compilation n'est exécuté.

## Après ce retour

Le rapport permettra de préparer la sélection Linux et une synchronisation gclient épinglée, sans hooks et avec parallélisme modéré, en annonçant explicitement les accès réseau restants. L'absence de commit WebRTC ou d'autres dépôts dans cet extrait de l'audit n'est pas un motif de passage à Chromium récent. Les hooks et la chaîne de compilation restent des validations séparées.

Trois tests supplémentaires vérifient les exclusions de plateforme/CIPD, la préservation des sources et destinations occupées, le clone local épinglé et le refus des chemins traversants ou symboliques. Ils utilisent de petits dépôts synthétiques et ne constituent pas une synchronisation réelle de Chromium.
