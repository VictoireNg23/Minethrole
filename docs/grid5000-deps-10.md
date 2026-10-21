# Grid5000 : sources principales prêtes, audit des dépendances réutilisables

## Préparation confirmée

L'utilisateur a préparé `/tmp/minethrottle71-work-rwkni3hv`, avec :

- Chromium à `c2bec8045f7ad3ece1c5d80236183a21c1fac3f5`.
- V8 à `b5a5d900a5385d6429edefb11ece72bfa649ca47`.
- Vérifications `git apply --check` réussies pour les deux patches originaux, non appliqués.
- `preparation.json` décrivant les magasins d'objets empruntés aux deux arbres du stockage partagé.

Les messages Git « leaving commits behind » sont produits lors du positionnement des nouveaux clones détachés. Ils concernent leurs références locales, et ne signifient pas que les anciens arbres ont changé de HEAD ou que leurs modifications ont été effacées. Aucune branche de sauvegarde supplémentaire n'est nécessaire dans les sources d'origine pour expliquer ce message. Les nouveaux clones restent toutefois dépendants des magasins d'objets empruntés : ne pas déplacer ni nettoyer ces magasins.

La présence de src et v8 ne signifie pas que tous les dépôts et artefacts DEPS sont prêts. Aucun sync, hook, patch appliqué ou build n'a encore été lancé.

## Prochaine étape : audit local du DEPS primaire

`scripts/audit-chromium71-deps.py` lit le blob DEPS du commit Chromium historique, sans exécuter son code. Le lecteur AST reconnaît des constantes, dictionnaires/listes, concaténations et références Var aux variables littérales ; les expressions non prises en charge sont signalées, et les mutations supplémentaires de niveau supérieur provoquent un arrêt plutôt qu'une interprétation incomplète annoncée comme exhaustive.

Pour chaque dépendance Git portant un SHA complet reconnaissable, le script examine le chemin correspondant sous les deux anciens arbres `chromium/` et `chromium71/`. Il vérifie que ce chemin est une racine Git distincte, puis teste la présence du commit local. Il ne lit pas le statut des fichiers, ne parcourt pas l'historique et ne récupère aucun objet manquant. Les lectures sont bornées ; un échec ou timeout reste distinct d'une présence confirmée.

Les dépendances CIPD sont recensées sans tester leur installation. Les conditions de plateforme sont **conservées mais non évaluées** : le rapport peut donc inclure Android, Windows ou d'autres configurations inactives pour notre futur build Linux. Les DEPS imbriqués ne sont pas lus. Le rapport n'est pas une liste définitive de tout ce qu'il faudra synchroniser.

```bash
python3 /chemin/vers/audit-chromium71-deps.py \
  /tmp/minethrottle71-work-rwkni3hv "$projet_minethrottle"
```

Un nouveau sous-dossier `deps-audit-.../report.json` conserve les définitions, conditions et résultats par candidat. Transmettre la sortie complète, le résumé et le chemin du rapport. Si des définitions ne sont pas résolues, leurs raisons sont affichées et devront être analysées avant d'en déduire une couverture complète.

Aucun clone supplémentaire, fetch, gclient, hook, patch ou compilation. Les seules écritures sont le nouveau rapport dans le nouvel espace de travail. La durée dépend du nombre de chemins présents et des accès au stockage partagé ; ne pas lancer plusieurs audits simultanés sur les mêmes magasins pour tenter d'accélérer une lecture lente.

## Suite prévue après lecture du rapport

Sélectionner les dépendances pertinentes pour Linux et préparer la réutilisation des objets disponibles, puis seulement proposer une synchronisation gclient épinglée, à parallélisme modéré et sans hooks. Les objets manquants et paquets CIPD nécessiteront des accès réseau qui seront explicitement annoncés. Ne pas lancer gclient sync par anticipation : il pourrait télécharger beaucoup de données et les hooks n'ont pas encore été préparés.

Les trois nouveaux tests couvrent la résolution de Var/concaténations, la conservation des conditions/CIPD, le refus de mutations supplémentaires et l'absence d'exécution d'une expression arbitraire. Aucun vrai DEPS Chromium n'est téléchargé ou exécuté dans Codex.
