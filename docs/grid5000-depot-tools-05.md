# Grid5000 : préparation isolée du candidat depot_tools historique

## Référence confirmée par le retour utilisateur

- HEAD actuel : `d38909eb68d85b91259f4bf20fe5ebcd38461bc2`.
- Dépôt non superficiel : `false` pour is-shallow-repository.
- Candidat local antérieur au 14 décembre 2018 : **`c6a8d114b060f5f68637e8897712a24252402377`**.
- Recherche terminée avec code zéro.

Ce SHA fixe le candidat de la première tentative. Il n'est pas une révision explicitement imposée par les auteurs et sa compatibilité reste à éprouver. Les quatre outils système et les contextes des patches ont déjà été validés dans les étapes précédentes.

## Action limitée proposée

Exécuter `scripts/prepare-historical-depot-tools.py` avec Python 3, en lui passant le chemin du depot_tools existant. Il nécessite les binaires `/usr/bin/python2` et `/usr/bin/ninja` vérifiés par vos sorties précédentes.

```bash
python3 /chemin/vers/prepare-historical-depot-tools.py /chemin/existant/vers/depot_tools
```

Le script :

1. Vérifie que le commit candidat existe dans les objets locaux, sans fetch ni récupération paresseuse.
2. Crée un répertoire unique `/tmp/minethrottle71-tools-...`. Il n'écrase jamais un ancien dossier et ne nettoie aucun fichier.
3. Exporte les fichiers suivis de cette révision avec git archive, puis extrait l'archive dans son nouveau sous-répertoire depot_tools. Les chemins traversants, liens et fichiers spéciaux sont refusés explicitement. Un tel refus nécessite une analyse de l'entrée concernée, pas un contournement des protections.
4. Enregistre `provenance.json` avec le SHA d'origine et l'empreinte de l'archive, laquelle est conservée.
5. Crée un petit `bin/python` qui appelle `/usr/bin/python2`, ainsi que des liens locaux pour Python 2 et Ninja. Aucun lien système n'est modifié.
6. Crée `env.sh` et `with-env.sh`, avec `DEPOT_TOOLS_UPDATE=0`, `GCLIENT_PY3=0` et les outils isolés prioritaires dans PATH. Le chemin de l'ancien depot_tools est retiré de ce PATH généré. Les profils shell existants sont intacts.
7. Vérifie uniquement `python --version` et `ninja --version` dans cet environnement.

**Limite volontaire :** il s'agit d'un snapshot sans répertoire .git, indépendant du magasin d'objets après export. Il ne sera pas mis à jour. Des outils historiques qui exigeraient des métadonnées Git du depot_tools pourraient nécessiter une préparation différente ; la compatibilité avec gclient n'est pas présumée. Ne pas déplacer le nouveau dossier : les lanceurs utilisent ses chemins absolus.

Les sources Chromium/V8, les patches et le depot_tools existant ne sont pas modifiés. Aucun gclient, fetch, gn, vpython, update_depot_tools, bootstrap CIPD, hook ou build n'est exécuté. Le script n'utilise pas VPYTHON_BYPASS et ne désactive aucune vérification TLS ou d'artefact.

## Sortie à transmettre

Envoyer la sortie complète, notamment le chemin `/tmp/minethrottle71-tools-...`, les deux versions et le message final. En cas d'échec, le nouveau répertoire partiel reste conservé, et son chemin est affiché. Ne pas effacer ni modifier ce dossier avant analyse.

Si l'étape réussit, la suivante sera un test borné des lanceurs historiques et de leur bootstrap, avec les éventuels téléchargements nécessaires explicitement annoncés. Il ne faut pas lancer gclient sync, fetch Chromium ni le script original --all de sa propre initiative à cette étape.

## Tests locaux

Le nouveau test exporte un ancien commit d'un minuscule dépôt synthétique et vérifie que HEAD, index et modifications locales de l'arbre actuel restent identiques. Il vérifie aussi le lanceur d'environnement sans exécuter de depot_tools réel. Les tests n'utilisent pas Chromium et ne valident pas encore le candidat réel sur Grid5000.

/tmp fournit selon vos résultats 808 Go libres sur ext4. C'est une capacité locale intéressante, mais son contenu peut disparaître avec le nœud ou la fin de l'allocation. Les scripts et la provenance scientifique sont versionnés sur GitHub ; aucun répertoire temporaire n'est assimilé à une sauvegarde persistante. Les quotas du stockage partagé restent à vérifier avant la préparation d'un arbre Chromium complet.
