# Crash du cas dormant : validation interrompue

Le rapport complet du premier smoke test n'est pas un succès : le cas dormant affiche `SMOKE_OK` puis reçoit SIGSEGV. Les cas négatif et actif affichés ont réussi, mais cela n'autorise pas la validation globale ni les douze signatures. Le prérequis du nouveau test a correctement arrêté son exécution.

Le patch conserve des adresses brutes de globals dans `module_info_list`, installe SIGALRM et réarme le timer toutes les 50 ms. Son handler lit ces adresses et utilise notamment fprintf/fflush, qui ne sont pas des opérations garanties async-signal-safe. Un conflit de durée de vie pendant la destruction V8 ou la fin du processus est une hypothèse cohérente avec l'ordre des messages, pas une cause démontrée. La stack brute ne permet pas à elle seule d'identifier la ligne fautive avec PIE/ASLR.

`diagnose-d8-shutdown.py` répète trois fois chacun des cas synthétiques originaux sans modifier le binaire ni masquer les codes de sortie. Les journaux sont séparés et les gros core dumps désactivés pour ces processus. Si GDB est déjà installé, un essai dormant supplémentaire est exécuté sous GDB en laissant passer SIGALRM normalement, avec backtraces et mappings. Le debugger peut modifier la temporisation : une non-reproduction sous GDB ne prouve pas l'absence du défaut. Sans GDB, aucune installation automatique n'est effectuée. Aucun module du dataset n'est exécuté.

Ne pas remplacer le statut global par passed, ignorer SIGALRM, quitter prématurément d8 ou modifier les patches pour faire passer le test. Après diagnostic, une éventuelle correction de durée de vie devra être isolée dans un patch d'adaptation distinct, avec justification et contrôle de conservation de la logique des compteurs. Les originaux restent intacts.
