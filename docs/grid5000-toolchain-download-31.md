# Artefacts Clang et sysroot identifiés

Les paramètres reçus de la révision historique fixent Clang à `344066-1`, sous `chromium-browser-clang/Linux_x64/clang-344066-1.tgz`, et le sysroot à `chrome-linux-sysroot/toolchain/e7c53f04bd88d29d075bfd1f62b073aeb69cbe09/debian_sid_amd64_sysroot.tar.xz` sur commondatastorage.googleapis.com.

Le script `download-chromium71-toolchain.py WORKSPACE` vérifie ces paramètres locaux puis télécharge les deux archives dans un nouveau répertoire temporaire. Chaque archive est limitée à 1 Gio ; le timeout réseau est de 30 secondes par opération bloquante, pas une durée totale garantie. Les fichiers partiels sont conservés en cas d'échec. Il ne lance aucun script historique, ne remplace aucun fichier et n'extrait aucune archive.

Le sysroot est vérifié contre son SHA-1 historique. Clang n'a pas d'empreinte indépendante fournie par les informations examinées : son téléchargement HTTPS à une URL versionnée n'est pas présenté comme une validation cryptographique de provenance. SHA-1 et SHA-256 reçus sont enregistrés pour comparaison et traçabilité. Une inspection des noms et types des entrées tar prépare l'étape d'extraction ; elle ne constitue pas encore une validation des cibles des liens ou une autorisation d'extraction. Attendre les résultats avant d'établir cette politique. Les archives volumineuses restent hors Git.
