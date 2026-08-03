# BrainBurst — Revue de stabilité & correction des bugs

> Décision de design : l'ADMIN gère l'accès des étudiants (statut `paid`) via une nouvelle vue.

## Étapes
- [x] 1. Créer la suite de tests `tests/test_core_flows.py` (pytest)
- [x] 2. Ajouter la vue admin de gestion des inscriptions (`/admin/inscriptions`) + toggle `paid`
- [x] 3. Corriger `init_db()` pour être compatible gunicorn (exécution au chargement du module)
- [ ] 4. Conversions sûres (`try/except`) sur tous les `int()`/`float()` d'entrées utilisateur
- [ ] 5. Corriger `admin_user_editer` (email dupliqué + nettoyage EnseignantMatiere si rôle changé)
- [ ] 6. Corriger les suppressions avec dépendances (matière, groupe) + suppression fichiers orphelins
- [ ] 7. Ajouter contrôles de sécurité manquants (inscription requise pour rendre un travail, cours publié)
- [ ] 8. Mettre à jour TEST_PLAN.md / TODO.md et exécuter la suite de tests + lancer l'app

