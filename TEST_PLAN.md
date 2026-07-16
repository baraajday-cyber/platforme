# Brainbrust — Plan de test des fonctionnalités (Manuel + Automatisé)

## Contexte
Application Flask (auth Flask-Login + SQLAlchemy). Rôles :
- **admin**
- **enseignant**
- **eleve**

Endpoints clés :
- Auth : `/login`, `/logout`, `/dashboard`
- Admin : `/admin`, `/admin/users`, `/admin/matieres`, `/admin/annonces`, `/admin/calendrier`, `/api/seances`
- Enseignant : `/teacher`, `/teacher/cours/*`, `/teacher/*/ressource/*`, `/teacher/cours/*/travail/*`, `/teacher/calendrier`
- Élève : `/student`, `/cours`, `/cours/*`, `/cours/*/inscrire`, `/cours/*/apprendre`, `/travail/*/rendre`, `/student/calendrier`
- Messages : `/messages`, `/messages/envoyer`
- Profil : `/profil`
- Upload/Download : `/download/<filename>`

---

## A) Checklist de tests manuels (cas de test)

### 0) Préparation (données)
1. Lancer l’app (au besoin) et vérifier la création automatique de l’admin.
   - Admin par défaut : `admin@brainburst.com` / `Admin1234!`
2. Créer via l’UI admin (ou via DB si vous préférez) :
   - 1 enseignant actif
   - 2 élèves actifs
   - 2 matières actives
   - 2 cours **publie=True** + 1 cours **non publié**
   - Pour au moins 1 cours publié :
     - 1 ressource PDF
     - 1 ressource vidéo (ou ressource type `video` via URL externe)
   - 1 séance **future** + 1 séance **passée** (liées à un cours)
   - 1 travail dans un cours (option date limite)

**Critères** : cohérence données -> pages filtrent correctement par rôle et par date.

---

### 1) Auth & contrôle d’accès
**TC-1.1** GET `/login` (non connecté)
- Attendu : page login affichée.

**TC-1.2** POST `/login` (admin valide)
- Attendu : redirection vers `/dashboard` puis `/admin`.

**TC-1.3** POST `/login` (enseignant valide)
- Attendu : redirection vers `/dashboard` puis `/teacher`.

**TC-1.4** POST `/login` (élève valide)
- Attendu : redirection vers `/dashboard` puis `/student`.

**TC-1.5** POST `/login` (mdp incorrect)
- Attendu : flash “Email ou mot de passe incorrect.” et retour sur login.

**TC-1.6** Compte inactif (`actif=False`)
- Attendu : flash “Votre compte est désactivé…” et retour login.

**TC-1.7** Accès sans login
- Attendu : redirection login vers `/login` pour `/admin`, `/teacher`, `/student`, `/messages`, `/download/*`.

**TC-1.8** Rôle interdit
- Exemple : élève tente `/teacher/cours/<cid>`.
- Attendu : “Accès refusé.” + redirection.

---

### 2) Admin
#### 2.1 Dashboard
**TC-2.1.1** GET `/admin`
- Attendu : stats et listes (`users_recent`, `seances_future`, `annonces`).

#### 2.2 Users
**TC-2.2.1** GET `/admin/users` (sans filtres)
- Attendu : liste de tous les users.

**TC-2.2.2** GET `/admin/users?role=eleve` (filtre)
- Attendu : seuls les élèves.

**TC-2.2.3** GET `/admin/users?q=xyz` (recherche)
- Attendu : match nom/email.

**TC-2.2.4** POST `/admin/users/creer`
- email déjà utilisé → flash “Email déjà utilisé.”
- mdp < 6 → flash “Mot de passe trop court…”
- mdp valide → user créé.

**TC-2.2.5** POST `/admin/users/<uid>/editer`
- modifie nom/prénom/email/role/actif
- option mdp change si `new_password` fourni et >=6.

**TC-2.2.6** POST `/admin/users/<uid>/supprimer`
- supprimer autre user → success.
- supprimer soi-même → flash danger “ne pouvez pas supprimer votre propre compte.”

**TC-2.2.7** POST `/admin/users/<uid>/toggle`
- Attendu : `actif` bascule et impact direct sur la connexion.

#### 2.3 Matières
**TC-2.3.1** GET `/admin/matieres`
- Attendu : liste matières.

**TC-2.3.2** POST `/admin/matieres/creer`
- Attendu : matière ajoutée.

**TC-2.3.3** POST `/admin/matieres/<mid>/editer`
- Attendu : maj champs + `actif` si checkbox.

**TC-2.3.4** POST `/admin/matieres/<mid>/supprimer`
- Attendu : suppression.

#### 2.4 Annonces
**TC-2.4.1** POST `/admin/annonces`
- Attendu : annonce créée.

**TC-2.4.2** GET `/` affiche 3 dernières annonces
- Attendu : les 3 plus récentes.

**TC-2.4.3** POST `/admin/annonces/<aid>/supprimer`
- Attendu : annonce supprimée.

#### 2.5 Calendrier admin + API
**TC-2.5.1** POST `/admin/seance/creer`
- date valide `%Y-%m-%dT%H:%M` → séance créée.
- date invalide → flash “Date invalide.”

**TC-2.5.2** POST `/admin/seance/<sid>/supprimer`
- Attendu : suppression.

**TC-2.5.3** GET `/api/seances` (admin)
- Attendu : JSON array events.
- Vérifier keys : `id,title,start,url,color,extendedProps`.

---

### 3) Enseignant
#### 3.1 Dashboard enseignant
**TC-3.1.1** GET `/teacher`
- Attendu :
  - cours = `Cours.enseignant_id = current_user.id`
  - `seances` = uniquement séances futures (date >= now) triées.
  - `msg_non_lus` = messages reçus destinés à l’enseignant non lus.

#### 3.2 Cours
**TC-3.2.1** GET `/teacher/cours/creer` puis POST
- Attendu : cours créé.

**TC-3.2.2** Editer cours
- Attendu : persistance modifs.
- Sécurité : autre enseignant ne doit pas pouvoir éditer/supprimer.

**TC-3.2.3** Publier/unpublier
- Attendu : cours publie apparaît dans `/cours` ; non publié n’apparaît pas.

**TC-3.2.4** Supprimer cours
- Attendu : suppression et disparition de l’UI enseignant.

#### 3.3 Ressources
**TC-3.3.1** POST `/teacher/cours/<cid>/ressource/ajouter`
- avec fichier extension autorisée → ressource créée.
- avec extension interdite → pas de création / comportement sûr (vérifier que l’app ne crash pas).

**TC-3.3.2** Ajout avec `url_externe` sans fichier
- Attendu : `type_fichier` forcé à `video`.

**TC-3.3.3** Supprimer ressource
- Attendu : suppression uniquement si ressource appartient au cours de l’enseignant.

#### 3.4 Travaux & notes
**TC-3.4.1** POST `/teacher/cours/<cid>/travail/creer`
- date_limite vide → OK.
- date_limite invalide → vérifier que l’app reste stable et observe la date (dans le code elle peut rester None).

**TC-3.4.2** GET `/teacher/travail/<tid>/rendus`
- Attendu : page pour le travail.

**TC-3.4.3** POST `/teacher/rendu/<rid>/noter`
- Attendu : `note`, `feedback`, `note_date` mis à jour.

**TC-3.4.4** Supprimer travail
- Attendu : uniquement si cours du bon enseignant.

#### 3.5 Calendrier enseignant
**TC-3.5.1** GET `/teacher/calendrier`
- Attendu : toutes séances des cours de l’enseignant triées.

---

### 4) Élève
#### 4.1 Dashboard
**TC-4.1.1** GET `/student`
- Attendu :
  - inscriptions = cours où élève inscrit
  - séances à venir uniquement
  - `travaux_pending` = travaux sans rendu pour cet élève
  - messages non lus comptés.

#### 4.2 Catalogue cours & inscription
**TC-4.2.1** GET `/cours`
- Attendu : uniquement cours publie=True.

**TC-4.2.2** Filtres `q`, `matiere_id`, `niveau`
- Attendu : correspondances appliquées.

**TC-4.2.3** POST `/cours/<cid>/inscrire`
- premier clic → inscription créée.
- second clic → pas de double inscription (même si code ne vérifie pas explicitement au niveau unique, la requête vérifie la première existence).

**TC-4.2.4** Sécurité
- Attendu : si rôle != eleve → warning + pas d’inscription.

#### 4.3 Apprentissage
**TC-4.3.1** GET `/cours/<cid>/apprendre` (non inscrit)
- Attendu : flash “Inscrivez-vous d’abord.” + redirection.

**TC-4.3.2** GET `/cours/<cid>/apprendre` (inscrit)
- Attendu :
  - ressources réparties par type (`pdfs/videos/autres`)
  - `travaux_info` contient rendu ou None
  - `seances` listées (toutes les séances du cours, pas seulement futures dans ce template).

#### 4.4 Rendre un travail
**TC-4.4.1** POST `/travail/<tid>/rendre` (première fois)
- Attendu : création TravauxRendu + commentaire.

**TC-4.4.2** POST `/travail/<tid>/rendre` (deuxième fois)
- Attendu : mise à jour (fichier si fourni, commentaire, date_rendu).

#### 4.5 Calendrier élève
**TC-4.5.1** GET `/student/calendrier`
- Attendu : séances des cours inscrits triées.

---

### 5) Messages
**TC-5.1** GET `/messages`
- Attendu :
  - messages marqués comme lus
  - liste utilisateurs selon rôle.

**TC-5.2** POST `/messages/envoyer`
- destinataire valide + contenu non vide → message créé.
- contenu vide ou dest invalide → pas de message.

---

### 6) Profil
**TC-6.1** GET/POST `/profil`
- Attendu : maj prénom/nom/bio.
- nouveau mdp < 6 → flash danger, mdp non changé.
- nouveau mdp valide → hash modifié.

---

### 7) Upload/Download
**TC-7.1** GET `/download/<filename>` sans login
- Attendu : redirection login.

**TC-7.2** GET `/download/<filename>` login
- Attendu : fichier renvoyé `as_attachment`.

---

## B) Automatisation (pytest) — proposition d’implémentation

### Objectif
Écrire une suite pytest qui teste les cas critiques via **Flask test client** et une base SQLite isolée.

### Étapes d’implémentation (à réaliser ensuite)
1. Ajouter dépendances : `pytest`, `pytest-flask` (optionnel), `requests` (optionnel), `flask-testing` (optionnel).
2. Créer un fichier `tests/test_core_flows.py`.
3. Activer un mode test :
   - `app.config['TESTING']=True`
   - `SQLALCHEMY_DATABASE_URI='sqlite:///:memory:'` ou un fichier temporaire
4. Seeding données : créer users/cours/matières/inscriptions/séances/travaux.
5. Tests recommandés :
   - `test_login_success_admin`
   - `test_login_invalid_credentials`
   - `test_role_protection_admin_routes`
   - `test_student_course_catalog_only_published`
   - `test_student_can_inscribe_and_access_apprendre`
   - `test_student_render_updates_existing_rendu`
   - `test_api_seances_shape`
   - `test_messages_mark_as_read`

> Remarque : l’app actuelle n’expose pas explicitement une fabrique app (`create_app`). L’automatisation devra soit :
> - modifier légèrement `app.py` pour permettre un `init_app/config`, soit
> - importer `app` et patcher `app.config`/DB avant `db.create_all()`.

---

## Faits à vérifier avant automatisation
- `SECRET_KEY` constant (OK pour tests)
- `init_db()` crée un admin si absent : en tests, éviter collision.
- Upload : les tests peuvent éviter d’émettre de vrais fichiers (tester le comportement sans fichier).

