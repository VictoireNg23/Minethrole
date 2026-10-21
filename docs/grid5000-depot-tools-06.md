# Grid5000 : arrêt de l'extraction sur l'entrée cbuildbot

## Résultat reçu

```text
New directory (retained even on failure): /tmp/minethrottle71-tools-w_exm4gk
FAILED / INCOMPLETE: Unsupported/unsafe archive entry: cbuildbot
```

L'export Git dans `depot_tools.tar` s'est terminé : l'erreur provient de la validation des entrées avant extraction. Le script de préparation initial refuse tous les liens, même légitimes. Cette règle volontairement conservatrice est trop restrictive pour un snapshot contenant des liens symboliques ; elle n'établit pas que le dépôt ou son archive sont corrompus.

Le type et la cible réels de `cbuildbot` restent à lire. Ne pas remplacer immédiatement l'extraction par un `tar xf` non contrôlé, ne pas suivre aveuglément les liens et ne pas supprimer l'entrée dans le dépôt source. Le script valide l'ensemble des entrées avant de commencer leur extraction : le snapshot, les lanceurs et le bootstrap ne sont donc pas préparés à cette étape.

## Prochaine action, lecture seule

Inspecter l'archive **déjà créée**, sans refaire git archive ni créer un nouveau dossier :

```bash
python3 /chemin/vers/inspect-depot-tools-archive.py \
  /tmp/minethrottle71-tools-w_exm4gk/depot_tools.tar
```

Le script `scripts/inspect-depot-tools-archive.py` affiche l'empreinte de l'archive, son commentaire Git (normalement le commit exporté), et tous les liens ou entrées spéciales avec leur cible. Il ne fait aucune extraction, ne suit aucun lien et n'exécute rien. Transmettre sa sortie complète.

À partir de cette liste, adapter précisément la préparation : les liens internes nécessaires doivent être validés sans écriture via un lien ; les références externes doivent être comprises et traitées explicitement, notamment si elles concernent des outils hors du périmètre Chromium. Aucun lien n'est supprimé ou ignoré automatiquement par cette étape de diagnostic. Une archive privée de certains outils ne sera jamais présentée comme une copie complète sans mention de ces exclusions.

L'archive partielle et le depot_tools existant restent en place. Aucun CIPD, gclient, hook, source Chromium ou build n'est lancé.

## Validation locale

Un test synthétique vérifie l'affichage d'un lien externe sans le suivre, la préservation de l'archive et l'absence d'extraction d'un chemin traversant. Il ne remplace pas l'inspection de l'archive réelle produite sur Grid5000.
