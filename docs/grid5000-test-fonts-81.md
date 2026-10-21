# Construction des tests sandbox : police Ahem manquante

La tentative `logs/chrome-build-6tunxmuc/result.json` s'arrête avant compilation (1,72 seconde), avec `third_party/test_fonts/test_fonts/Ahem.ttf` absent et aucune règle de génération connue. La cible sandbox_linux_unittests nécessite des données de test qui n'étaient pas requises pour le build chrome seul. Le binaire chrome existant reste celui du build antérieur ; le statut failed ne doit pas être transformé en succès par binary_exists=true.

Le script de préparation lit l'action originale test_fonts et son SHA-1, télécharge uniquement cet objet du bucket chromium-fonts, vérifie l'empreinte puis extrait dans un nouveau staging local. Les entrées sont limitées aux fichiers/répertoires sous test_fonts, sans lien, chemin sortant ou doublon. Les tailles sont bornées (512 Mio compressés, 1 Gio décompressé). Après contrôle de Ahem.ttf, un lien est créé vers la destination encore absente, sans écrasement. Conserver le staging.

Les journaux et la provenance sont écrits dans le run persistant. Aucun hook global, build, test natif, navigateur ou dataset n'est exécuté à cette étape. Après retour, reprendre la construction des deux cibles, puis exécuter les tests BPF. La disponibilité et le contenu exact du bucket restent à confirmer sur Grid5000.
