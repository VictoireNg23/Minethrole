# Grid5000 : installation initiale des quatre outils de base

## Résultats reçus

L'utilisateur confirme les candidats suivants dans les listes APT locales Ubuntu Jammy :

| Paquet | Candidat observé |
| --- | --- |
| python2 | 2.7.18-3 |
| python2.7 | 2.7.18-13ubuntu1.5 |
| ninja-build | 1.10.1-1 |
| pkg-config | 0.29.2-1ubuntu3 |
| ccache | 4.5.1-1 |

Les binaires `/usr/bin/python2`, `/usr/bin/python2.7`, `/usr/bin/ninja`, `/usr/bin/pkg-config`, `/usr/bin/ccache` sont absents. Le dépôt depot_tools existant est accessible et son HEAD est `d38909eb68d85b91259f4bf20fe5ebcd38461bc2`. Sa compatibilité avec Chromium 71 n'est pas démontrée ; il ne sera ni rétrogradé ni mis à jour.

La requête `quota -s -u killerdroid` échoue parce que ce nom ne correspond pas à un utilisateur local du nœud. Le nom présent dans le chemin du stockage ne doit pas être assimilé à un compte local. Cette erreur n'établit ni l'absence de quota côté service ni un quota illimité. La capacité temporaire et le quota applicable doivent toujours être confirmés avant de créer un checkout complet ou des sorties de compilation.

## Objectif limité de cette étape

Installer Python 2, un vrai Ninja système, pkg-config et ccache dans l'image Ubuntu du nœud. Cela ne constitue pas l'installation de toutes les bibliothèques nécessaires à Chromium. Le script ne modifie aucun fichier des projets existants, ne touche pas à depot_tools et ne change aucun lien `python`/`python3` ou configuration `update-alternatives`.

Les paquets sont choisis d'après les candidats effectivement signalés. La résolution et les versions installées peuvent changer après rafraîchissement des index ; la sortie APT puis les versions finales feront foi. Aucune vérification de signature, checksum ou TLS n'est désactivée. Les éventuelles dépendances APT sont installées normalement ; `--no-remove` refuse un plan exigeant la suppression de paquets. L'installation concerne le système du nœud, et non le stockage des sources partagé.

## Script et commandes

Script : `scripts/install-chromium71-base-tools.sh`.

Une simulation seule est disponible, sans rafraîchissement réseau des listes :

```bash
bash /chemin/vers/install-chromium71-base-tools.sh --simulate
```

Pour l'installation demandée à cette étape, depuis votre session root :

```bash
bash /chemin/vers/install-chromium71-base-tools.sh --install
```

Le script vérifie Ubuntu 22.04, actualise les index APT en arrêtant l'exécution si une source échoue, puis propose l'installation avec la confirmation normale d'APT. Il n'appelle ni autoremove ni clean ni purge. Si la résolution propose une action inattendue, répondre non et transmettre la sortie. Il vérifie ensuite les binaires via leurs chemins `/usr/bin`, afin d'éviter le lanceur Ninja de depot_tools actuellement prioritaire dans PATH. Le PATH n'est pas modifié à cette étape.

Python 2 doit pouvoir importer ssl/json/subprocess pour cette vérification initiale. Cela ne prouve pas encore le fonctionnement de gclient/vpython historiques ni l'accès CIPD. Si un téléchargement ou une installation échoue, transmettre les erreurs et arrêter ; ne pas ajouter d'option autorisant des paquets non authentifiés et ne pas changer de miroir sans analyse.

## À transmettre et limite de validation

Transmettre la sortie complète du script, en particulier les versions installées et tout avertissement/échec APT. Le script a été vérifié syntaxiquement dans Codex et son aide/gestion d'arguments ont été contrôlées. L'installation Ubuntu n'a pas été exécutée dans Codex ; aucune réussite sur le nœud n'est présumée.

Après réception des versions finales, préparer séparément un depot_tools historique compatible et l'environnement de dépendances de Chromium 71. Les patches ont déjà passé leur contrôle de contexte sur les bons commits. Aucun nouveau checkout, hook ou build n'est lancé à cette étape. La création future de sources/sorties attend toujours une vérification explicite de l'espace temporaire et du quota du service partagé.
