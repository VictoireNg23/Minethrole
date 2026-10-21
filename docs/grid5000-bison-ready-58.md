# Bison accessible ; reprendre la compilation

L'utilisateur confirme GNU Bison 3.8.2 via le binaire système et via le lanceur historique. La résolution de l'exécutable manquant est vérifiée, mais la compatibilité du code généré avec Blink 71 reste à établir dans le build réel.

Reprendre le wrapper existant, cible chrome, même répertoire GN patché, 16 tâches et timeout 900 secondes. Conserver les objets et tous les dossiers de staging. Si une erreur de génération ou de compilation liée à Bison apparaît, examiner précisément le diagnostic avant de choisir une adaptation ou une version historique de Bison. Aucun remplacement préventif de version ni changement de grammaire n'est demandé.
