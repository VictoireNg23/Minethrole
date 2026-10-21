# Polices historiques prêtes ; reprendre les deux cibles

Le rapport Grid5000 `logs/test-fonts-gcl9exb0/result.json` confirme `historical_test_fonts_prepared`. L'archive vérifie SHA-1 `a22de844e32a3f720d219e3911c3da3478039f89`, SHA-256 `6e331676d098a57c53c1250821dc47ed84c47f823901bf30c4704df90d8a34be`, 30 entrées, 23 477 380 octets décompressés. Le lien vers `/tmp/minethrottle71-test-fonts-3859otdh/test_fonts` est préparé. Conserver ce staging.

Reprendre la commande de compilation chrome + sandbox_linux_unittests avec le même rapport GN, les trois rapports d'adaptation et le run persistant, 16 tâches et timeout 900 secondes. Aucun nettoyage, nouveau sync, hook global ou modification du code n'est requis par ce prérequis. Les nouveaux journaux restent dans le dossier partagé.

Aucun succès de rebuild corrigé n'est encore établi. Après un code 0, vérifier les empreintes des deux binaires puis exécuter séparément les tests BPF ciblés avant un nouveau staging navigateur. Le staging navigateur précédent conserve volontairement son ancien binaire.
