# Grid5000 : l'erreur de clone est masquée par le mécanisme de reprise

## Précision apportée par le code historique transmis

L'extrait update de gclient_scm.py fourni par l'utilisateur contient :

```python
try:
  self._Clone(revision, url, options)
except subprocess2.CalledProcessError:
  self._DeleteOrMove(options.force)
  self._Clone(revision, url, options)
```

La ligne 549 du traceback précédent est l'appel à _DeleteOrMove dans ce bloc except. L'échec de _Clone précède donc l'erreur shutil.move/ENOENT. Le déplacement d'un chemin inexistant est une erreur secondaire de récupération qui masque la cause initiale. Il ne démontre pas un conflit de fichiers, un lien pendant ou un défaut de MineThrottle.

Le DEPS attend exactement :

```text
https://chromium.googlesource.com/external/github.com/ChromeDevTools/devtools-node-modules
5f7cd2497d7a643125c3b6eb910d99ba28be6899
```

L'audit avait constaté l'absence de ce dossier dans les deux anciens arbres, et la préparation locale l'avait classé no_confirmed_local_commit. Son téléchargement était donc attendu ; l'extrait actuel ne dit pas pourquoi ce téléchargement a échoué.

## Information nécessaire avant correction

La sortie fournie contient matching_audits, matching_seed_results et historical_code, mais pas le bloc log_context qui doit contenir la première commande et l'erreur Git. Récupérer cette partie du rapport déjà enregistré ou les lignes correspondantes dans :

```text
/tmp/minethrottle71-work-rwkni3hv/sync-nohooks-brdu1qn4/sync.log
```

Les sorties décisives sont la commande de clone et ses lignes fatal/error/HTTP précédant le traceback. Sans elles, on ne peut pas distinguer accès réseau, URL indisponible, révision inaccessible ou autre problème local. Ne pas remplacer l'URL/révision ni retirer la dépendance à ce stade.

Aucune nouvelle synchronisation, création de dossier de substitution, suppression ou déplacement n'est requis pour récupérer ces lignes. Après diagnostic de la cause initiale, préparer une récupération explicite et bornée de cette dépendance, puis une reprise dont les déplacements automatiques sont bloqués ou traités explicitement. Cette modification d'outillage doit rester séparée des patches originaux.
