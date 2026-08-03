# Tracking - ADDENDUM_ASSIGNMENTS.md

- [x] 1) Ajouter modele GroupEnseignant (table group_teacher) dans app.py
- [x] 2) Ajouter routes admin /admin/groupes/<gid>/enseignants (GET/POST) dans app.py
- [x] 3) UI admin : remplacer matiere_ids (multiple) par matiere_id unique dans templates/admin/admin_user_form.html
- [x] 4) Back-end admin : valider "exactement 1 matiere" pour les comptes enseignant dans admin_user_creer et admin_user_editer (mise a jour EnseignantMatiere)
- [x] 5) Filtrage eleve : mettre a jour /cours et /cours/<cid>/apprendre pour autoriser uniquement les cours des enseignants affectes au groupe de l'eleve
- [x] 6) Creer template admin pour assigner enseignants a un groupe (admin_groupe_enseignants.html)
- [x] 7) DB : init_db() cree automatiquement la table group_teacher via db.create_all() OK
- [ ] 8) Tests manuels : admin cree matieres/enseignants/groupes + affectations ; verifier le filtrage cote eleve
