# Adaptation clone3 appliquée ; construire Chromium et les tests natifs

Le rapport Grid5000 `clone3-compatibility-b42vx5h3/result.json` confirme l'application de l'adaptation ENOSYS, SHA-256 e34f34c120ebc3dd332bbb5bbdabdeb9a99208b66154241bd4a04cd87dc05f03, sans modification des patches MineThrottle et sans désactivation du sandbox. Les anciens binaires restent non corrigés tant qu'ils n'ont pas été reconstruits.

Le wrapper de build accepte `--clone3-adaptation-report`, compare le diff des deux fichiers sandbox au diff enregistré, et conserve cette provenance avec celles de d8/Bison. `--with-sandbox-tests` ajoute la cible historique `sandbox_linux_unittests` à Ninja avec chrome. Son nom et l'inclusion du fichier baseline_policy_unittest.cc ont été vérifiés dans le BUILD.gn historique. Aucun test natif ni navigateur n'est exécuté par cette compilation.

Avec `--results-run RUN`, les nouveaux journaux et rapports sont écrits directement dans RUN/logs/chrome-build-*. Les rapports d'application des adaptations y sont copiés, et les SHA-256 des binaires chrome et sandbox_linux_unittests sont enregistrés après succès. Les objets de compilation restent dans le workspace local existant ; aucun nettoyage ou déplacement n'est effectué.

Après retour du build, exécuter les tests BPF ciblés (ENOSYS, création de thread et restrictions clone) avec des ressources/permissions préparées. Ne pas lancer le staging navigateur ancien comme s'il utilisait le nouveau filtre : une nouvelle copie avec la nouvelle empreinte sera nécessaire. Le test de page bénigne sera ensuite refait sans pause/debugger et avec observation du sandbox.
