# TODO (BrainBurst)

## Objectif
Ajouter une logique efficace d’organisation via :
- association **enseignant ↔ matière**
- association **élève ↔ groupe**
- association **élève ↔ niveau** (Débutant / Standard / Excellent)
- et en déduire : accès/filtrage des cours et possibilité de créer des groupes/niveaux.

## Etapes
- [ ] 1) Ajouter/mettre en place dans le modèle : tables/colonnes pour **Groupe** et **niveau** (selon design retenu)
- [ ] 2) Ajouter relation **enseignant ↔ matière** (option simple via Cours.matiere_id déjà existant, sinon table dédiée)
- [ ] 3) Mettre à jour les routes admin de création/édition utilisateurs pour choisir groupe/niveau
- [ ] 4) Mettre à jour la logique d’accès élève : cours filtrés par **matière + niveau + groupe**
- [ ] 5) Mettre à jour l’UI (templates) : formulaires admin + filtres cours catalogue
- [ ] 6) Migration DB/compatibilité (sqlite) + init_db pour valeurs par défaut
- [ ] 7) Revalider les flows existants (login, admin, teacher, student, download, rendu, API)

## Remarque
Si l’on choisit une implémentation minimale sans ajouter de nouvelles tables relationnelles, on peut réutiliser `Cours.niveau` (déjà présent) et ajouter seulement `User.groupe_id` + `User.niveau` (ou équivalent) puis filtrer le catalogue.

