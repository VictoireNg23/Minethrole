# Version Chromium confirmée ; préparer un test navigateur non privilégié

Le dernier retour utilisateur confirme à nouveau `chrome_dependencies_and_version_passed`, aucune bibliothèque manquante et `Chromium 71.0.3578.98`. Aucune page ni module Wasm n'a encore été chargé par le navigateur.

Avant une page synthétique locale, examiner les permissions et le support de namespaces : l'utilisateur est root, et les répertoires mktemp sont généralement privés. Le script `diagnose-chromium71-sandbox.py REPERTOIRE_BUILD` lit les paramètres noyau, identifie les outils disponibles, inspecte les permissions de traversée et la présence d'un helper sandbox, puis essaie un user namespace éphémère sous nobody si runuser/unshare sont présents. Le compte nobody n'est utilisé que pour cette sonde, pas choisi automatiquement comme compte d'expérience. Un échec getent pour un compte absent est attendu et ne constitue pas un échec Chromium.

Aucun compte n'est créé, aucune permission n'est changée, aucune page n'est ouverte. Le résultat permettra de préparer un compte dédié et un répertoire de lancement local avec droits adaptés, sans chmod récursif des sources partagées ni ajout de --no-sandbox. Une sonde namespace réussie est un prérequis observé, pas une validation complète du sandbox Chromium 71.

Le futur test utilisera uniquement un module synthétique bénin, pas le dataset. Le correctif de fin de vie d8 n'agit pas sur les renderers Chromium ; leur comportement et leurs fichiers de compteurs restent à vérifier.
