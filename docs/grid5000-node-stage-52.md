# Archives Node et WebUI vérifiées : staging et liaison

Grid5000 confirme les SHA-1 historiques : Node Linux `1bdce2f7303ac1db18166035a0c4035134d46bbc`, modules WebUI `dc855853e383fc88c56845f772c259f25a3ed045`. Les archives de 18 070 433 et 4 283 647 octets ne contiennent que des fichiers/répertoires. Elles sont conservées dans `/tmp/minethrottle71-node-download-5eqt514g`.

`stage-chromium71-node.py WORKSPACE DOWNLOAD_REPORT` revérifie les empreintes contre les fichiers du checkout, refuse les destinations occupées, puis extrait dans un nouveau répertoire. Les seules racines acceptées sont `node-linux-x64` et `node_modules` ; les chemins sortants, doublons, liens et autres types spéciaux sont refusés avant extraction de chaque archive. Volume décompressé limité à 512 Mio par archive. Aucun propriétaire ni bit setuid n'est restauré.

Après `node --version` égal à `v8.9.1` et vérification de la présence du bundler WebUI, le script crée des liens vers ces deux répertoires aux chemins attendus dans `src/third_party/node/`. Les ouvertures et créations ne remplacent pas les destinations existantes. Si la seconde liaison échoue après la première, le rapport indique le lien déjà créé : préserver l'état et analyser, sans suppression automatique. Conserver le dossier de staging pendant le build.

Aucun npm install, hook global ou compilation n'est exécuté. Le test Node vérifie seulement le démarrage ; la compatibilité du bundler et de ses entrées sera vérifiée lors de la reprise incrémentale du build, après retour de cette étape.
