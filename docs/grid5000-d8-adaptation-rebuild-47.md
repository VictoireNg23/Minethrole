# Adaptation d'arrêt appliquée ; reconstruire d8 avec provenance

Le rapport Grid5000 `d8-shutdown-fix-eeqg6xh7/result.json` confirme l'application de l'adaptation séparée SHA-256 `52b887813a9351dca6e606e6732686f4ca8f7ef775a25b920f2ffea3e53d9da4`, avec patches originaux inchangés. Aucune compilation n'est encore réalisée après cette modification.

Le script de build accepte `--adaptation-report`. Il exige le statut et l'empreinte attendus, compare le diff actuel de d8.cc à celui enregistré lors de l'application, puis lance la compilation incrémentale de la seule cible d8 dans le répertoire GN déjà préparé. Les mêmes limites de tâches, timeout et cache dédié s'appliquent. Aucun nettoyage ni nouvelle application du patch n'est effectué. Le rapport conserve l'identité de l'adaptation et, après succès, le SHA-256 du binaire d8 reconstruit.

Cette empreinte ne doit pas être attribuée à un binaire dont la compilation échoue. Conserver les anciens rapports : leur statut de compilation réussi concerne l'ancien état des sources. Après recompilation confirmée, répéter le diagnostic des neuf cas et le smoke test complet, sans qualifier une compilation réussie de correction validée du crash. Puis seulement poursuivre les douze signatures.
