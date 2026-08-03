# BrainBurst — Revue de stabilité & correction des bugs (plan)

## Suivi des étapes

### Étape 4 : Conversions sûres sur toutes les entrées utilisateur
- [x] Ajouter helpers `to_int` / `to_float` (app.py)
- [x] Remplacer les `int()` / `float()` non protégés dans les routes (login, seances, rendu note, messages, catalogue)
- [ ] Sécuriser `int(matiere_id)` dans `teacher_cours_creer_deposer`, `teacher_cours_creer`, `teacher_cours_editer`
- [ ] Sécuriser `groupe_id` (formulaire utilisateur)

### Étape 5 : Corriger `admin_user_editer`
- [ ] Vérifier doublon email avant mise à jour
- [ ] Nettoyer les associations `EnseignantMatiere` si le rôle n'est plus enseignant

### Étape 6 : Suppressions avec dépendances
- [ ] Supprimer une matière → détacher les cours (matiere_id = NULL) + fichiers
- [ ] Supprimer un groupe → détacher les élèves + GroupEnseignant
- [ ] Supprimer un utilisateur → nettoyer cours/inscriptions/travaux/messages + fichiers orphelins
- [ ] Supprimer un cours → supprimer les fichiers des ressources
- [ ] Supprimer une ressource → supprimer le fichier du disque
- [ ] Supprimer un travail → supprimer le fichier + fichiers des rendus

### Étape 7 : Contrôles de sécurité manquants
- [ ] Bloquer l'accès à un cours non publié (`cours_detail`, `cours_apprendre`)
- [ ] Exiger inscription + `paid` pour rendre un travail
- [ ] Vérifier que l'élève est bien inscrit au cours du travail avant de rendre

### Étape 8 : Tests & documentation
- [ ] Corriger `tests/conftest.py` (fixture `seed` — `DetachedInstanceError`)
- [ ] Corriger les assertions Unicode dans `tests/test_core_flows.py`
- [ ] Exécuter la suite de tests (pytest) — tous verts
- [ ] Lancer l'application (vérifier démarrage + init_db)
- [ ] Mettre à jour TEST_PLAN.md / TODO_REVIEW.md

