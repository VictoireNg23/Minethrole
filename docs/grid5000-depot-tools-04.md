# Grid5000 : outils de base vérifiés, recherche d'un depot_tools historique

## Installation confirmée par le terminal utilisateur

L'installation APT s'est terminée et le script a atteint ses vérifications finales :

| Outil | Résultat |
| --- | --- |
| `/usr/bin/python2` | Python 2.7.18 |
| Module ssl Python 2 | OpenSSL 3.0.2, import réussi |
| `/usr/bin/ninja` | 1.10.1 |
| `/usr/bin/pkg-config` | 0.29.2 |
| `/usr/bin/ccache` | 4.5.1 |

Les versions ne sont plus seulement des candidats APT. Les messages needrestart indiquent des redémarrages de services différés, pas un échec des quatre outils. Il n'est pas nécessaire de redémarrer ces services pour examiner des objets Git et préparer la chaîne de build ; aucun redémarrage n'est demandé à cette étape. L'installation concerne l'image du nœud et peut devoir être reproduite si cette image est remplacée.

Les dépendances complètes de Chromium, le sysroot et Clang historiques ne sont pas encore préparés. La présence de Python 2 et de ssl ne valide ni vpython, ni gclient, ni CIPD. Le PATH continue à contenir des wrappers depot_tools modernes ; utiliser les chemins système explicites jusqu'à préparation d'un lanceur dédié.

## Étape unique suivante : inspecter un candidat historique local

Le depot_tools existant a pour HEAD observé `d38909eb68d85b91259f4bf20fe5ebcd38461bc2`. Ne pas le rétrograder et ne pas lancer son auto-update.

`scripts/inspect-historical-depot-tools.sh` cherche dans son historique local first-parent le dernier commit précédant le **14 décembre 2018 UTC**, repère temporel choisi pour une première tentative proche de la version Chromium 71.0.3578.98. Cette date ne représente pas une révision depot_tools officielle imposée par les auteurs, et la sélection chronologique ne prouve pas sa compatibilité. Le script affiche un SHA complet que nous pourrons examiner et épingler pour une tentative reproductible.

Il lit ensuite quelques lignes des fichiers historiques gclient, fetch, vpython, ninja, gn et des fichiers de bootstrap s'ils existent. Aucun de ces fichiers n'est exécuté. Il ne crée pas de nouvel arbre, ne lance pas gclient, ne récupère aucun objet et ne change ni HEAD, ni branche, ni index, ni fichiers du depot_tools existant. Il désactive la récupération paresseuse des objets et borne les lectures Git à 90 secondes. Une erreur ou un délai expiré ne démontre pas l'absence de l'historique.

Commande :

```bash
bash /chemin/vers/inspect-historical-depot-tools.sh /chemin/existant/vers/depot_tools
```

Si aucun candidat local n'est accessible, arrêter et transmettre la sortie : nous préparerons ensuite une petite résolution de référence distante, sans cloner l'historique entier ni toucher au depot_tools existant. Ne pas contourner un problème de bootstrap en désactivant TLS ou les contrôles d'artefacts.

Le script affiche aussi l'espace et les inodes de /tmp ainsi que l'espace du parent depot_tools, afin de disposer de ces informations avant une éventuelle copie isolée des outils. Ces sorties ne démontrent toujours pas le quota applicable au service de stockage partagé.

## Validation du script et critères de continuation

Un test sur un dépôt synthétique contenant un ancien et un nouveau commit vérifie la sélection de l'ancien SHA et la préservation du HEAD moderne, de l'index et des modifications locales. Il vérifie aussi que le faux wrapper n'est jamais exécuté. Aucun depot_tools historique réel n'a été téléchargé ou exécuté dans Codex.

Après retour du SHA candidat et des lignes de bootstrap, décider de la révision historique à retenir, puis préparer sa copie dans un nouveau répertoire distinct et le lancement avec l'interpréteur adapté. Ne pas confondre l'inspection réussie d'un candidat avec son installation ou sa validation. Le clone de sources Chromium et les hooks restent reportés ; les quotas et la capacité temporaire pour une compilation devront être confirmés avant les opérations volumineuses.
