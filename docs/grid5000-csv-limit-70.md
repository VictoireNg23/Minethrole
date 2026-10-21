# Analyse des hôtes : limite CSV du lecteur de référence

L'analyse par fichier s'est arrêtée à la comparaison avec `docs/dataset1_s-inventaire.csv` : un champ de métadonnées dépasse la limite CSV Python par défaut (131 072 caractères). Cela n'est pas une erreur de lecture du dataset Wasm ni un résultat de détection.

La fonction de lecture du CSV de référence utilise désormais une limite explicite de 64 Mio par champ et restaure ensuite la limite précédente. Un test couvre un champ de 200 000 caractères et la conservation du comptage des empreintes dupliquées. Cette correction ne change pas les critères d'hôte, les données ou MineThrottle.

Mettre à jour le clone par fast-forward et relancer la même analyse. Elle crée un nouveau dossier de sortie ; les fichiers partiels du premier essai ne sont pas supprimés et ne doivent pas être interprétés comme un rapport complet en l'absence de summary.json. Aucun module n'est exécuté.
