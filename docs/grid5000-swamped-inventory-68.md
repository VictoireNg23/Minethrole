# Dépôt et résultats prêts ; inventorier Swamped_10_ sans exécution

L'utilisateur confirme le clone propre au commit cf21710 dans `tests/Minethrole-reproduction.GPLllk` et le run persistant `resultats_minethrottle/run-20261021T150736Z-u4tlcbi3`. Le manifeste identifie le dataset `Data/Swamped_10_` et le build Chromium vérifié. Aucun module n'est exécuté.

Le script `inventory-wasm-experiment.py --run CHEMIN_RUN` lit ce manifeste, parcourt les fichiers .wasm sans suivre les liens et écrit un nouveau dossier `summaries/inventory-*` avec CSV, JSONL détaillé et résumé JSON. Il ne change ni le manifeste initial ni les données. Chaque résultat garde le chemin relatif, le SHA-256 pour les fichiers lus, les imports avec types, exports avec types, mémoire et fonction start éventuelle. La révision du script est enregistrée séparément de la révision de préparation initiale.

Le lecteur traite les métadonnées courantes de modules de type MVP ; il ne valide pas les corps de fonctions ni toutes les propositions récentes et ne prouve pas la compatibilité V8 7.1. Les limites de fichier (64 Mio par défaut), erreurs et fonctionnalités non prises en charge sont des statuts distincts. Aucun de ces statuts n'est un verdict bénin. Un export de fonction ou une section start n'est pas assimilé à un point d'entrée minier déjà identifié.

Après mise à jour du clone partagé par fast-forward uniquement, lancer cet inventaire depuis le dépôt local. Il ne compile rien, ne lance pas Chromium et n'a pas besoin d'accès réseau. Transmettre le résumé pour préparer les environnements hôtes à partir des imports réellement observés. Les droits de l'utilisateur d'exécution sandbox seront organisés avant le premier test navigateur, sans chmod récursif du stockage partagé.
