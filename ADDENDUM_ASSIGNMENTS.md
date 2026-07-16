# Ajout demandé : affectations Admin → enseignant → matière + groupes

## But
Réaliser la logique suivante :
- L’admin crée un **enseignant** et lui attribue **exactement 1 matière**.
- L’admin crée des **groupes/classes**.
- L’admin attribue à chaque groupe **un ou plusieurs enseignants**.
- Les cours et l’accès élève doivent respecter ces affectations.

## Décisions
- Enseignant ⇢ **1 seule** matière.
- Enseignant ⇢ **1 ou plusieurs** groupes.

## Impacts attendus
- Ajout/évolution de la DB :
  - Enregistrer `matiere_id` côté enseignant (ou table TeacherSubject).
  - Créer une table d’association `group_teacher`.
- UI admin :
  - Ajout d’un champ *matière* au formulaire création/édition d’enseignant.
  - Ajout d’un multi-select *groupes* pour chaque enseignant, ou une vue inverse : choisir enseignants par groupe.
- Logique d’accès :
  - Filtrer les cours par `cours.groupe_id` (à implémenter si absent) et/ou autoriser uniquement les enseignants associés.

## Prochaines étapes
1. Revoir le schéma actuel (présence/absence de `Cours.groupe_id`).
2. Implémenter la relation DB Enseignant⇢Matière (1 seule).
3. Implémenter la relation DB Groupe⇢Enseignants (n-n).
4. Ajouter les écrans admin nécessaires.
5. Mettre à jour la logique cours/affichage.

