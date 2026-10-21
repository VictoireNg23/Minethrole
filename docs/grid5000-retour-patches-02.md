# Grid5000 : contrôle historique des patches réussi

## Preuve fournie par l'utilisateur

L'exécution de `scripts/check-chromium71-patches.py` sur `roazhon13-6` a terminé avec :

```text
New diagnostic directory (retained): /tmp/minethrottle71-patchcheck-sf53k34i
PASS context only: v8
PASS context only: content
PASS: both original patches match the exported historical file contexts.
No patch applied. This does NOT validate C++ compilation or runtime behavior.
```

Les neuf fichiers V8 proviennent de `b5a5d900a5385d6429edefb11ece72bfa649ca47` (V8 7.1.302.31). Le fichier `content/renderer/render_frame_impl.cc` provient de `c2bec8045f7ad3ece1c5d80236183a21c1fac3f5` (Chromium 71.0.3578.98). Le lien entre ces révisions a été vérifié dans DEPS par le script avant extraction.

**Conclusion :** applicabilité textuelle des patches originaux validée sur les fichiers historiques exacts, sans modification des sources existantes. Ce succès ne démontre ni la présence de toutes les dépendances, ni la compatibilité C++, ni le fonctionnement des compteurs à l'exécution. Chromium récent n'est pas nécessaire pour résoudre un conflit de contexte : aucun conflit n'a été trouvé à cette étape.

## Prochaine étape : choisir l'environnement historique sans modifier l'existant

Un contrôle court est enregistré dans `scripts/diagnose-chromium71-host.sh`. Il ne relance ni l'analyse Git des arbres volumineux ni les sondes réseau. Il fournit les informations encore nécessaires :

- Version exacte de l'OS et identité de l'utilisateur courant.
- Capacité temporaire, inodes, type et propriétaire des montages.
- Quota courant et, si la commande est disponible sous root, quota du compte `killerdroid`. Une session root et un `df` de stockage partagé ne démontrent pas le quota utilisable par ce compte.
- Candidats locaux APT pour Python 2.7, Ninja, pkg-config et ccache, sans actualiser les index ni installer de paquet. L'absence de candidat peut venir de dépôts ou listes APT indisponibles, et ne suffit pas à conclure à l'impossibilité d'installer Python 2.
- Présence des binaires système indépendamment des wrappers depot_tools.
- Racine et SHA Git de `../depot_tools`, sans lancer ses wrappers ni le mettre à jour. Si ce chemin n'est pas un dépôt accessible, la sortie sera conservée pour diagnostic ; aucune configuration Git de confiance n'est modifiée.

Commande, avec le script récupéré dans un nouveau fichier distinct :

```bash
bash /chemin/vers/diagnose-chromium71-host.sh "$projet_minethrottle"
```

Le script est en lecture seule et ne nécessite pas de nouvelle installation. Les erreurs/timeouts restent des observations indisponibles. Les sorties de quota peuvent nécessiter une confirmation auprès du service de stockage ; ne pas considérer une sortie vide comme quota illimité.

Après ces résultats, préparer une procédure adaptée pour les dépendances et une copie isolée de depot_tools compatible avec Python 2. Le choix de sa révision historique et les prérequis Clang/sysroot devront être établis avant de lancer gclient ou les hooks. Ensuite seulement proposer un nouveau répertoire de sources, en réutilisant les objets présents selon les quotas et la stratégie de conservation. Aucun checkout moderne ni magasin Git partagé ne sera rétrogradé, déplacé ou nettoyé.

## État courant

| Vérification | État |
| --- | --- |
| Révisions Chromium/V8 historiques identifiées | Confirmé par sortie utilisateur |
| Contexte des patches originaux | Réussi pour V8 et content |
| Patches appliqués | Non |
| Dépendances hôtes complètes | Non |
| Compatibilité de depot_tools historique | À déterminer |
| Quotas et espace temporaire utilisables | À confirmer |
| Compilation C++ | Non exécutée |
| Instrumentation dynamique Wasm | Non validée |
