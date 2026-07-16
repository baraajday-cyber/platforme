from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'brainburst-secret-2024-changez-moi'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///brainburst.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB

ALLOWED_EXTENSIONS = {'pdf', 'mp4', 'avi', 'mov', 'png', 'jpg', 'jpeg', 'pptx', 'docx', 'zip', 'rar'}
 
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Connectez-vous pour acceder.'

# ═══════════════════════════════════════════════════════════
#                        MODELES
# ═══════════════════════════════════════════════════════════

class User(UserMixin, db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nom           = db.Column(db.String(100), nullable=False)
    prenom        = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password      = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20),  default='eleve')  # admin | enseignant | eleve
    actif         = db.Column(db.Boolean,     default=True)
    bio           = db.Column(db.Text,        default='')
    date_creation = db.Column(db.DateTime,    default=datetime.utcnow)

    # Classe / groupe d’étude (pour les élèves)
    groupe_id     = db.Column(db.Integer, db.ForeignKey('groupe.id'), nullable=True)

    cours_crees  = db.relationship('Cours',       backref='enseignant', lazy=True)
    inscriptions = db.relationship('Inscription', backref='eleve',      lazy=True)
    travaux_rendus = db.relationship('TravauxRendu', backref='eleve',   lazy=True)
    msg_envoyes  = db.relationship('Message', foreign_keys='Message.expediteur_id',   backref='expediteur',   lazy=True)
    msg_recus    = db.relationship('Message', foreign_keys='Message.destinataire_id', backref='destinataire', lazy=True)

class Groupe(db.Model):
    """Classe / groupe universitaire (ex: Débutant/Standard/Excellent ou A/B/C)."""
    id           = db.Column(db.Integer, primary_key=True)
    nom          = db.Column(db.String(80), nullable=False, unique=True)
    description  = db.Column(db.Text)
    date_creation= db.Column(db.DateTime, default=datetime.utcnow)
    actif        = db.Column(db.Boolean, default=True)

    eleves = db.relationship('User', backref='groupe', lazy=True)


class Matiere(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    nom         = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    couleur     = db.Column(db.String(20), default='#4D96FF')
    icone       = db.Column(db.String(10), default='📚')
    actif       = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    cours = db.relationship('Cours', backref='matiere', lazy=True)

class Cours(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    titre         = db.Column(db.String(200), nullable=False)
    description   = db.Column(db.Text,        nullable=False)
    niveau        = db.Column(db.String(50),   nullable=False)
    publie        = db.Column(db.Boolean,      default=False)
    date_creation = db.Column(db.DateTime,     default=datetime.utcnow)
    enseignant_id = db.Column(db.Integer,      db.ForeignKey('user.id'),    nullable=False)
    matiere_id    = db.Column(db.Integer,      db.ForeignKey('matiere.id'), nullable=True)

    ressources   = db.relationship('Ressource',   backref='cours', lazy=True, cascade='all, delete-orphan')
    inscriptions = db.relationship('Inscription', backref='cours', lazy=True, cascade='all, delete-orphan')
    travaux      = db.relationship('Travail',     backref='cours', lazy=True, cascade='all, delete-orphan')
    seances      = db.relationship('Seance',      backref='cours', lazy=True, cascade='all, delete-orphan')

class Ressource(db.Model):
    """Fichiers déposés dans un cours : PDF, vidéo, etc."""
    id          = db.Column(db.Integer, primary_key=True)
    titre       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    type_fichier= db.Column(db.String(20))   # pdf | video | autre
    nom_fichier = db.Column(db.String(300))
    url_externe = db.Column(db.String(500))   # lien YouTube/Drive optionnel
    ordre       = db.Column(db.Integer, default=0)
    date_depot  = db.Column(db.DateTime, default=datetime.utcnow)
    cours_id    = db.Column(db.Integer, db.ForeignKey('cours.id'), nullable=False)

class Travail(db.Model):
    """Travaux à faire déposés par l'enseignant."""
    id           = db.Column(db.Integer, primary_key=True)
    titre        = db.Column(db.String(200), nullable=False)
    description  = db.Column(db.Text,        nullable=False)
    date_limite  = db.Column(db.DateTime)
    nom_fichier  = db.Column(db.String(300))   # fichier joint optionnel
    date_depot   = db.Column(db.DateTime, default=datetime.utcnow)
    cours_id     = db.Column(db.Integer, db.ForeignKey('cours.id'), nullable=False)
    rendus       = db.relationship('TravauxRendu', backref='travail', lazy=True, cascade='all, delete-orphan')

class TravauxRendu(db.Model):
    """Rendu d'un élève pour un travail."""
    id          = db.Column(db.Integer, primary_key=True)
    eleve_id    = db.Column(db.Integer, db.ForeignKey('user.id'),    nullable=False)
    travail_id  = db.Column(db.Integer, db.ForeignKey('travail.id'), nullable=False)
    nom_fichier = db.Column(db.String(300))
    commentaire = db.Column(db.Text)
    note        = db.Column(db.Float)
    feedback    = db.Column(db.Text)
    date_rendu  = db.Column(db.DateTime, default=datetime.utcnow)
    note_date   = db.Column(db.DateTime)

class Seance(db.Model):
    """Séance en ligne planifiée."""
    id          = db.Column(db.Integer, primary_key=True)
    titre       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date_seance = db.Column(db.DateTime,    nullable=False)
    duree       = db.Column(db.Integer,     default=60)   # minutes
    lien_meet   = db.Column(db.String(500))                # lien Google Meet / Zoom
    cours_id    = db.Column(db.Integer, db.ForeignKey('cours.id'), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

class Offre(db.Model):
    id                = db.Column(db.Integer, primary_key=True)
    nom               = db.Column(db.String(100), nullable=False)
    frequence         = db.Column(db.String(30), nullable=False)  # mensuel | trimestriel | annuel | special
    prix_stripe_price_id = db.Column(db.String(100), nullable=False)
    actif             = db.Column(db.Boolean, default=True)
    date_creation     = db.Column(db.DateTime, default=datetime.utcnow)


class Inscription(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    eleve_id         = db.Column(db.Integer, db.ForeignKey('user.id'),  nullable=False)
    cours_id         = db.Column(db.Integer, db.ForeignKey('cours.id'), nullable=False)
    date_inscription = db.Column(db.DateTime, default=datetime.utcnow)
    progression      = db.Column(db.Integer,  default=0)

    # Paiement
    paid             = db.Column(db.Boolean, default=False, nullable=False)
    paid_at          = db.Column(db.DateTime)
    offre_id         = db.Column(db.Integer, db.ForeignKey('offre.id'), nullable=True)
    stripe_checkout_session_id = db.Column(db.String(200))


class Message(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    contenu         = db.Column(db.Text,    nullable=False)
    expediteur_id   = db.Column(db.Integer, db.ForeignKey('user.id'))
    destinataire_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_envoi      = db.Column(db.DateTime, default=datetime.utcnow)
    lu              = db.Column(db.Boolean,  default=False)

class Annonce(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    titre         = db.Column(db.String(200), nullable=False)
    contenu       = db.Column(db.Text,        nullable=False)
    auteur_id     = db.Column(db.Integer, db.ForeignKey('user.id'))
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    auteur        = db.relationship('User', backref='annonces')

# ═══════════════════════════════════════════════════════════
#                      HELPERS
# ═══════════════════════════════════════════════════════════

@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(field):
    f = request.files.get(field)
    if f and f.filename and allowed_file(f.filename):
        fname = secure_filename(f.filename)
        # Ajouter timestamp pour éviter les doublons
        fname = f"{int(datetime.utcnow().timestamp())}_{fname}"
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        return fname
    return None

def require_role(*roles):
    """Vérifie que l'utilisateur a le bon rôle."""
    if current_user.role not in roles:
        flash('Accès non autorisé.', 'danger')
        return False
    return True

def get_file_type(filename):
    if not filename: return 'autre'
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext == 'pdf': return 'pdf'
    if ext in ('mp4','avi','mov','mkv'): return 'video'
    return 'autre'

# ═══════════════════════════════════════════════════════════
#                   AUTH — CONNEXION
# ═══════════════════════════════════════════════════════════

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    annonces = Annonce.query.order_by(Annonce.date_creation.desc()).limit(3).all()
    stats = {
        'cours':       Cours.query.filter_by(publie=True).count(),
        'eleves':      User.query.filter_by(role='eleve', actif=True).count(),
        'enseignants': User.query.filter_by(role='enseignant', actif=True).count(),
        'matieres':    Matiere.query.filter_by(actif=True).count(),
    }
    return render_template('index.html', annonces=annonces, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email','').strip()
        password = request.form.get('password','')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if not user.actif:
                flash('Votre compte est désactivé. Contactez l\'administrateur.', 'danger')
                return redirect(url_for('login'))
            login_user(user, remember=bool(request.form.get('remember')))
            flash(f'Bienvenue, {user.prenom} ! 👋', 'success')
            return redirect(url_for('dashboard'))
        flash('Email ou mot de passe incorrect.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnecté avec succès.', 'info')
    return redirect(url_for('index'))

# ═══════════════════════════════════════════════════════════
#                     DASHBOARD
# ═══════════════════════════════════════════════════════════

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'enseignant':
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

# ═══════════════════════════════════════════════════════════
#                 ADMIN — GESTION COMPLÈTE
# ═══════════════════════════════════════════════════════════

@app.route('/admin')
@login_required
def admin_dashboard():
    if not require_role('admin'): return redirect(url_for('dashboard'))
    stats = {
        'eleves':      User.query.filter_by(role='eleve').count(),
        'enseignants': User.query.filter_by(role='enseignant').count(),
        'cours':       Cours.query.count(),
        'matieres':    Matiere.query.count(),
        'seances':     Seance.query.count(),
    }
    users_recent   = User.query.order_by(User.date_creation.desc()).limit(5).all()
    seances_future = Seance.query.filter(Seance.date_seance >= datetime.utcnow()).order_by(Seance.date_seance).limit(5).all()
    annonces       = Annonce.query.order_by(Annonce.date_creation.desc()).limit(3).all()
    return render_template('admin/admin_dashboard.html', stats=stats,
                           users_recent=users_recent, seances_future=seances_future, annonces=annonces)

# ── GESTION UTILISATEURS ────────────────────────────────────

@app.route('/admin/users')
@login_required
def admin_users():
    if not require_role('admin'): return redirect(url_for('dashboard'))
    role   = request.args.get('role', '')
    search = request.args.get('q', '')
    q = User.query
    if role:   q = q.filter_by(role=role)
    if search: q = q.filter(User.nom.ilike(f'%{search}%') | User.email.ilike(f'%{search}%'))
    users = q.order_by(User.date_creation.desc()).all()
    return render_template('admin/admin_users.html', users=users, role=role, search=search)

@app.route('/admin/users/creer', methods=['GET','POST'])
@login_required
def admin_user_creer():
    if not require_role('admin'): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        if User.query.filter_by(email=email).first():
            flash('Email déjà utilisé.', 'danger')
            return redirect(url_for('admin_user_creer'))
        pwd = request.form.get('password','')
        if len(pwd) < 6:
            flash('Mot de passe trop court (min 6 caractères).', 'danger')
            return redirect(url_for('admin_user_creer'))
        user = User(
            nom    = request.form.get('nom','').strip(),
            prenom = request.form.get('prenom','').strip(),
            email  = email,
            password = generate_password_hash(pwd),
            role   = request.form.get('role','eleve'),
            actif  = True,
            groupe_id = request.form.get('groupe_id') or None
        )
        db.session.add(user); db.session.commit()
        flash(f'Compte créé pour {user.prenom} {user.nom} ! ✅', 'success')
        return redirect(url_for('admin_users'))
    groupes = Groupe.query.filter_by(actif=True).order_by(Groupe.nom).all()
    return render_template('admin/admin_user_form.html', user=None, groupes=groupes)

@app.route('/admin/users/<int:uid>/editer', methods=['GET','POST'])
@login_required
def admin_user_editer(uid):
    if not require_role('admin'): return redirect(url_for('dashboard'))
    user = User.query.get_or_404(uid)
    if request.method == 'POST':
        user.nom    = request.form.get('nom', user.nom).strip()
        user.prenom = request.form.get('prenom', user.prenom).strip()
        user.email  = request.form.get('email', user.email).strip()
        user.role   = request.form.get('role', user.role)
        user.actif  = 'actif' in request.form
        user.groupe_id = request.form.get('groupe_id') or None
        nouveau_mdp = request.form.get('new_password','').strip()
        if nouveau_mdp:
            if len(nouveau_mdp) < 6:
                flash('Mot de passe trop court.', 'danger')
                return redirect(url_for('admin_user_editer', uid=uid))
            user.password = generate_password_hash(nouveau_mdp)
        db.session.commit()
        flash('Utilisateur mis à jour. ✅', 'success')
        return redirect(url_for('admin_users'))
    groupes = Groupe.query.filter_by(actif=True).order_by(Groupe.nom).all()
    return render_template('admin/admin_user_form.html', user=user, groupes=groupes)

@app.route('/admin/users/<int:uid>/supprimer', methods=['POST'])
@login_required
def admin_user_supprimer(uid):
    if not require_role('admin'): return redirect(url_for('dashboard'))
    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin_users'))
    db.session.delete(user); db.session.commit()
    flash('Utilisateur supprimé.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:uid>/toggle', methods=['POST'])
@login_required
def admin_user_toggle(uid):
    if not require_role('admin'): return redirect(url_for('dashboard'))
    user = User.query.get_or_404(uid)
    user.actif = not user.actif
    db.session.commit()
    flash(f'Compte {"activé" if user.actif else "désactivé"}.', 'success')
    return redirect(url_for('admin_users'))

# ── GESTION MATIÈRES ────────────────────────────────────────

@app.route('/admin/matieres')
@login_required
def admin_matieres():
    if not require_role('admin'): return redirect(url_for('dashboard'))
    matieres = Matiere.query.order_by(Matiere.nom).all()
    return render_template('admin/admin_matieres.html', matieres=matieres)

@app.route('/admin/matieres/creer', methods=['GET','POST'])
@login_required
def admin_matiere_creer():
    if not require_role('admin'): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        m = Matiere(
            nom         = request.form.get('nom','').strip(),
            description = request.form.get('description','').strip(),
            couleur     = request.form.get('couleur','#4D96FF'),
            icone       = request.form.get('icone','📚'),
        )
        db.session.add(m); db.session.commit()
        flash(f'Matière "{m.nom}" créée ! ✅', 'success')
        return redirect(url_for('admin_matieres'))
    return render_template('admin/admin_matiere_form.html', matiere=None)

@app.route('/admin/matieres/<int:mid>/editer', methods=['GET','POST'])
@login_required
def admin_matiere_editer(mid):
    if not require_role('admin'): return redirect(url_for('dashboard'))
    m = Matiere.query.get_or_404(mid)
    if request.method == 'POST':
        m.nom         = request.form.get('nom', m.nom).strip()
        m.description = request.form.get('description', m.description or '').strip()
        m.couleur     = request.form.get('couleur', m.couleur)
        m.icone       = request.form.get('icone', m.icone)
        m.actif       = 'actif' in request.form
        db.session.commit()
        flash('Matière mise à jour. ✅', 'success')
        return redirect(url_for('admin_matieres'))
    return render_template('admin/admin_matiere_form.html', matiere=m)

@app.route('/admin/matieres/<int:mid>/supprimer', methods=['POST'])
@login_required
def admin_matiere_supprimer(mid):
    if not require_role('admin'): return redirect(url_for('dashboard'))
    m = Matiere.query.get_or_404(mid)
    db.session.delete(m); db.session.commit()
    flash('Matière supprimée.', 'success')
    return redirect(url_for('admin_matieres'))

# ── GESTION ANNONCES ────────────────────────────────────────

@app.route('/admin/annonces', methods=['GET','POST'])
@login_required
def admin_annonces():
    if not require_role('admin'): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        a = Annonce(
            titre    = request.form.get('titre','').strip(),
            contenu  = request.form.get('contenu','').strip(),
            auteur_id= current_user.id
        )
        db.session.add(a); db.session.commit()
        flash('Annonce publiée ! ✅', 'success')
        return redirect(url_for('admin_annonces'))
    annonces = Annonce.query.order_by(Annonce.date_creation.desc()).all()
    return render_template('admin/admin_annonces.html', annonces=annonces)

@app.route('/admin/annonces/<int:aid>/supprimer', methods=['POST'])
@login_required
def admin_annonce_supprimer(aid):
    if not require_role('admin'): return redirect(url_for('dashboard'))
    a = Annonce.query.get_or_404(aid)
    db.session.delete(a); db.session.commit()
    flash('Annonce supprimée.', 'success')
    return redirect(url_for('admin_annonces'))

# ── CALENDRIER ADMIN ─────────────────────────────────────────

@app.route('/admin/calendrier')
@login_required
def admin_calendrier():
    if not require_role('admin'): return redirect(url_for('dashboard'))
    seances = Seance.query.order_by(Seance.date_seance).all()
    cours_list = Cours.query.filter_by(publie=True).all()
    return render_template('admin/admin_calendrier.html', seances=seances, cours_list=cours_list)

@app.route('/admin/seance/creer', methods=['POST'])
@login_required
def admin_seance_creer():
    if not require_role('admin'): return redirect(url_for('dashboard'))
    try:
        dt = datetime.strptime(request.form.get('date_seance',''), '%Y-%m-%dT%H:%M')
    except:
        flash('Date invalide.', 'danger')
        return redirect(url_for('admin_calendrier'))
    s = Seance(
        titre       = request.form.get('titre','').strip(),
        description = request.form.get('description','').strip(),
        date_seance = dt,
        duree       = int(request.form.get('duree', 60)),
        lien_meet   = request.form.get('lien_meet','').strip(),
        cours_id    = int(request.form.get('cours_id'))
    )
    db.session.add(s); db.session.commit()
    flash('Séance planifiée ! ✅', 'success')
    return redirect(url_for('admin_calendrier'))

@app.route('/admin/seance/<int:sid>/supprimer', methods=['POST'])
@login_required
def admin_seance_supprimer(sid):
    if not require_role('admin'): return redirect(url_for('dashboard'))
    s = Seance.query.get_or_404(sid)
    db.session.delete(s); db.session.commit()
    flash('Séance supprimée.', 'success')
    return redirect(url_for('admin_calendrier'))

# ── API CALENDRIER JSON ───────────────────────────────────────

@app.route('/api/seances')
@login_required
def api_seances():
    if current_user.role == 'admin':
        seances = Seance.query.all()
    elif current_user.role == 'enseignant':
        ids = [c.id for c in current_user.cours_crees]
        seances = Seance.query.filter(Seance.cours_id.in_(ids)).all()
    else:
        ids = [i.cours_id for i in current_user.inscriptions]
        seances = Seance.query.filter(Seance.cours_id.in_(ids)).all()

    events = []
    for s in seances:
        events.append({
            'id':    s.id,
            'title': f"🎥 {s.titre}",
            'start': s.date_seance.strftime('%Y-%m-%dT%H:%M:00'),
            'url':   s.lien_meet or '#',
            'color': s.cours.matiere.couleur if s.cours.matiere else '#4D96FF',
            'extendedProps': {
                'cours':       s.cours.titre,
                'duree':       s.duree,
                'lien':        s.lien_meet or '',
                'description': s.description or '',
            }
        })
    return jsonify(events)

# ═══════════════════════════════════════════════════════════
#              ENSEIGNANT — COURS & RESSOURCES
# ═══════════════════════════════════════════════════════════

@app.route('/teacher/cours/creer_deposer', methods=['GET','POST'])
@login_required
def teacher_cours_creer_deposer():
    if not require_role('enseignant'):
        return redirect(url_for('dashboard'))

    matieres = Matiere.query.filter_by(actif=True).order_by(Matiere.nom).all()

    if request.method == 'POST':
        # 1) Créer le cours
        niveau = request.form.get('niveau','Débutant').strip()
        c = Cours(
            titre=request.form.get('titre','').strip(),
            description=request.form.get('description','').strip(),
            niveau=niveau,
            matiere_id=request.form.get('matiere_id') or None,
            publie='publie' in request.form,
            enseignant_id=current_user.id
        )
        db.session.add(c)
        db.session.commit()

        # 2) Ajouter ressources (fichiers)
        titres_base = request.form.get('titre_ressources','').strip()
        desc_base = request.form.get('description_ressources','').strip()

        fichs = request.files.getlist('fichiers')
        for f in fichs:
            if not f or not f.filename:
                continue
            if not allowed_file(f.filename):
                flash(f"Extension non autorisée : {f.filename}", 'danger')
                continue

            # Reuse save_upload logic but with provided file
            fname = secure_filename(f.filename)
            fname = f"{int(datetime.utcnow().timestamp())}_{fname}"
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))

            r = Ressource(
                titre=titres_base or f"Ressource {fname}",
                description=desc_base,
                type_fichier=get_file_type(fname),
                nom_fichier=fname,
                url_externe=None,
                cours_id=c.id,
                ordre=Ressource.query.filter_by(cours_id=c.id).count()
            )
            db.session.add(r)

        # 3) Ajouter ressources (liens externes)
        url_list_raw = request.form.get('url_externe_list','')
        url_lines = [u.strip() for u in url_list_raw.splitlines() if u.strip()]
        for url in url_lines:
            r = Ressource(
                titre=titres_base or 'Ressource lien externe',
                description=desc_base,
                type_fichier='video',
                nom_fichier=None,
                url_externe=url,
                cours_id=c.id,
                ordre=Ressource.query.filter_by(cours_id=c.id).count()
            )
            db.session.add(r)

        db.session.commit()
        flash('Cours créé et ressources déposées ✅', 'success')
        return redirect(url_for('teacher_cours_contenu', cid=c.id))

    return render_template('teacher/teacher_cours_import_deposer.html', matieres=matieres)

@app.route('/teacher')
@login_required
def teacher_dashboard():
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    mes_cours = Cours.query.filter_by(enseignant_id=current_user.id).order_by(Cours.date_creation.desc()).all()
    total_eleves = sum(len(c.inscriptions) for c in mes_cours)
    travaux_recents = []
    for c in mes_cours:
        for t in c.travaux:
            for r in t.rendus:
                if not r.note:
                    travaux_recents.append({'travail': t, 'rendu': r, 'cours': c})
    seances = []
    for c in mes_cours:
        for s in c.seances:
            if s.date_seance >= datetime.utcnow():
                seances.append(s)
    seances.sort(key=lambda x: x.date_seance)
    msg_non_lus = Message.query.filter_by(destinataire_id=current_user.id, lu=False).count()
    return render_template('teacher/teacher_dashboard.html',
                           mes_cours=mes_cours, total_eleves=total_eleves,
                           travaux_recents=travaux_recents[:5],
                           seances=seances[:5], msg_non_lus=msg_non_lus)

# ── COURS ENSEIGNANT ─────────────────────────────────────────

@app.route('/teacher/cours/creer', methods=['GET','POST'])
@login_required
def teacher_cours_creer():
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        c = Cours(
            titre         = request.form.get('titre','').strip(),
            description   = request.form.get('description','').strip(),
            niveau        = request.form.get('niveau','Débutant'),
            matiere_id    = request.form.get('matiere_id') or None,
            publie        = 'publie' in request.form,
            enseignant_id = current_user.id
        )
        db.session.add(c); db.session.commit()
        flash('Cours créé ! ✅', 'success')
        return redirect(url_for('teacher_cours_contenu', cid=c.id))
    matieres = Matiere.query.filter_by(actif=True).order_by(Matiere.nom).all()
    return render_template('teacher/teacher_cours_form.html', cours=None, matieres=matieres)

@app.route('/teacher/cours/<int:cid>/editer', methods=['GET','POST'])
@login_required
def teacher_cours_editer(cid):
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    c = Cours.query.get_or_404(cid)
    if c.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    if request.method == 'POST':
        c.titre       = request.form.get('titre', c.titre).strip()
        c.description = request.form.get('description', c.description).strip()
        c.niveau      = request.form.get('niveau', c.niveau)
        c.matiere_id  = request.form.get('matiere_id') or None
        c.publie      = 'publie' in request.form
        db.session.commit()
        flash('Cours mis à jour. ✅', 'success')
        return redirect(url_for('teacher_cours_contenu', cid=cid))
    matieres = Matiere.query.filter_by(actif=True).order_by(Matiere.nom).all()
    return render_template('teacher/teacher_cours_form.html', cours=c, matieres=matieres)

@app.route('/teacher/cours/<int:cid>/supprimer', methods=['POST'])
@login_required
def teacher_cours_supprimer(cid):
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    c = Cours.query.get_or_404(cid)
    if c.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    db.session.delete(c); db.session.commit()
    flash('Cours supprimé.', 'success')
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/cours/<int:cid>/contenu')
@login_required
def teacher_cours_contenu(cid):
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    c = Cours.query.get_or_404(cid)
    if c.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    return render_template('teacher/teacher_cours_contenu.html', cours=c)

# ── RESSOURCES ───────────────────────────────────────────────

@app.route('/teacher/cours/<int:cid>/ressource/ajouter', methods=['POST'])
@login_required
def teacher_ressource_ajouter(cid):
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    c = Cours.query.get_or_404(cid)
    if c.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    fname    = save_upload('fichier')
    ftype    = get_file_type(fname) if fname else 'autre'
    url_ext  = request.form.get('url_externe','').strip()
    if url_ext and not fname:
        ftype = 'video'
    r = Ressource(
        titre       = request.form.get('titre','').strip(),
        description = request.form.get('description','').strip(),
        type_fichier= ftype,
        nom_fichier = fname,
        url_externe = url_ext or None,
        cours_id    = cid,
        ordre       = Ressource.query.filter_by(cours_id=cid).count()
    )
    db.session.add(r); db.session.commit()
    flash('Ressource ajoutée ! ✅', 'success')
    return redirect(url_for('teacher_cours_contenu', cid=cid))

@app.route('/teacher/ressource/<int:rid>/supprimer', methods=['POST'])
@login_required
def teacher_ressource_supprimer(rid):
    r = Ressource.query.get_or_404(rid)
    cid = r.cours_id
    if r.cours.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    db.session.delete(r); db.session.commit()
    flash('Ressource supprimée.', 'success')
    return redirect(url_for('teacher_cours_contenu', cid=cid))

# ── TRAVAUX ──────────────────────────────────────────────────

@app.route('/teacher/cours/<int:cid>/travail/creer', methods=['GET','POST'])
@login_required
def teacher_travail_creer(cid):
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    c = Cours.query.get_or_404(cid)
    if c.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    if request.method == 'POST':
        dl = None
        dl_str = request.form.get('date_limite','').strip()
        if dl_str:
            try: dl = datetime.strptime(dl_str, '%Y-%m-%dT%H:%M')
            except: pass
        fname = save_upload('fichier')
        t = Travail(
            titre       = request.form.get('titre','').strip(),
            description = request.form.get('description','').strip(),
            date_limite = dl,
            nom_fichier = fname,
            cours_id    = cid
        )
        db.session.add(t); db.session.commit()
        flash('Travail publié ! ✅', 'success')
        return redirect(url_for('teacher_cours_contenu', cid=cid))
    return render_template('teacher/teacher_travail_form.html', cours=c)

@app.route('/teacher/travail/<int:tid>/rendus')
@login_required
def teacher_travail_rendus(tid):
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    t = Travail.query.get_or_404(tid)
    if t.cours.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    return render_template('teacher/teacher_travail_rendus.html', travail=t)

@app.route('/teacher/rendu/<int:rid>/noter', methods=['POST'])
@login_required
def teacher_noter_rendu(rid):
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    r = TravauxRendu.query.get_or_404(rid)
    if r.travail.cours.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    r.note     = float(request.form.get('note', 0))
    r.feedback = request.form.get('feedback','').strip()
    r.note_date = datetime.utcnow()
    db.session.commit()
    flash('Note enregistrée ! ✅', 'success')
    return redirect(url_for('teacher_travail_rendus', tid=r.travail_id))

@app.route('/teacher/travail/<int:tid>/supprimer', methods=['POST'])
@login_required
def teacher_travail_supprimer(tid):
    t = Travail.query.get_or_404(tid)
    cid = t.cours_id
    if t.cours.enseignant_id != current_user.id:
        flash('Accès refusé.', 'danger'); return redirect(url_for('dashboard'))
    db.session.delete(t); db.session.commit()
    flash('Travail supprimé.', 'success')
    return redirect(url_for('teacher_cours_contenu', cid=cid))

# ── CALENDRIER ENSEIGNANT ─────────────────────────────────────

@app.route('/teacher/calendrier')
@login_required
def teacher_calendrier():
    if not require_role('enseignant'): return redirect(url_for('dashboard'))
    seances = []
    for c in current_user.cours_crees:
        seances.extend(c.seances)
    seances.sort(key=lambda x: x.date_seance)
    return render_template('teacher/teacher_calendrier.html', seances=seances)

# ═══════════════════════════════════════════════════════════
#                  ÉLÈVE — ESPACE APPRENANT
# ═══════════════════════════════════════════════════════════

@app.route('/student')
@login_required
def student_dashboard():
    if not require_role('eleve'): return redirect(url_for('dashboard'))
    inscriptions = Inscription.query.filter_by(eleve_id=current_user.id).all()
    # Séances à venir pour les cours auxquels l'élève est inscrit
    ids_cours = [i.cours_id for i in inscriptions]
    seances = Seance.query.filter(
        Seance.cours_id.in_(ids_cours),
        Seance.date_seance >= datetime.utcnow()
    ).order_by(Seance.date_seance).limit(5).all()
    # Travaux non rendus
    travaux_pending = []
    for insc in inscriptions:
        for t in insc.cours.travaux:
            rendu = TravauxRendu.query.filter_by(eleve_id=current_user.id, travail_id=t.id).first()
            if not rendu:
                travaux_pending.append({'travail': t, 'cours': insc.cours})
    annonces = Annonce.query.order_by(Annonce.date_creation.desc()).limit(3).all()
    msg_non_lus = Message.query.filter_by(destinataire_id=current_user.id, lu=False).count()
    return render_template('student/student_dashboard.html',
                           inscriptions=inscriptions, seances=seances,
                           travaux_pending=travaux_pending[:5],
                           annonces=annonces, msg_non_lus=msg_non_lus)

# ── CATALOGUE & INSCRIPTION ──────────────────────────────────

@app.route('/cours')
@login_required
def liste_cours():
    q         = request.args.get('q','')
    matiere_id= request.args.get('matiere_id','')
    niveau    = request.args.get('niveau','')
    query     = Cours.query.filter_by(publie=True)
    if q:          query = query.filter(Cours.titre.ilike(f'%{q}%'))
    if matiere_id: query = query.filter_by(matiere_id=int(matiere_id))
    if niveau:     query = query.filter_by(niveau=niveau)
    # Filtrage par groupe pour les élèves
    if current_user.role == 'eleve' and current_user.groupe_id is not None:
        query = query.filter_by(groupe_id=current_user.groupe_id)
    cours     = query.order_by(Cours.date_creation.desc()).all()
    matieres  = Matiere.query.filter_by(actif=True).order_by(Matiere.nom).all()
    inscriptions_ids = [i.cours_id for i in current_user.inscriptions] if current_user.role=='eleve' else []
    return render_template('cours_liste.html', cours=cours, matieres=matieres,
                           q=q, matiere_id=matiere_id, niveau=niveau, inscriptions_ids=inscriptions_ids)

@app.route('/cours/<int:cid>')
@login_required
def cours_detail(cid):
    c = Cours.query.get_or_404(cid)
    inscription = None
    if current_user.role == 'eleve':
        inscription = Inscription.query.filter_by(eleve_id=current_user.id, cours_id=cid).first()
    return render_template('cours_detail.html', cours=c, inscription=inscription)

@app.route('/cours/<int:cid>/inscrire', methods=['POST'])
@login_required
def cours_inscrire(cid):
    if current_user.role != 'eleve':
        flash('Réservé aux élèves.', 'warning'); return redirect(url_for('cours_detail', cid=cid))
    if not Inscription.query.filter_by(eleve_id=current_user.id, cours_id=cid).first():
        db.session.add(Inscription(eleve_id=current_user.id, cours_id=cid))
        db.session.commit()
        flash('Inscrit avec succès ! 🎉', 'success')
    return redirect(url_for('cours_detail', cid=cid))


# ── ESPACE D'APPRENTISSAGE ───────────────────────────────────

@app.route('/cours/<int:cid>/apprendre')
@login_required
def cours_apprendre(cid):
    c = Cours.query.get_or_404(cid)
    if current_user.role == 'eleve' and current_user.groupe_id is not None and c.groupe_id is not None and c.groupe_id != current_user.groupe_id:
        flash('Accès refusé pour ce cours (groupe incompatible).', 'danger')
        return redirect(url_for('cours_detail', cid=cid))
    if current_user.role == 'eleve':
        insc = Inscription.query.filter_by(eleve_id=current_user.id, cours_id=cid).first()
        if not insc:
            flash('Inscrivez-vous d\'abord.', 'warning')
            return redirect(url_for('cours_detail', cid=cid))
        if not insc.paid:
            flash('Paiement requis pour accéder au contenu du cours.', 'warning')
            return redirect(url_for('cours_detail', cid=cid))

    # Ressources classées par type
    pdfs   = [r for r in c.ressources if r.type_fichier == 'pdf']
    videos = [r for r in c.ressources if r.type_fichier == 'video']
    autres = [r for r in c.ressources if r.type_fichier == 'autre']
    # Travaux avec état rendu
    travaux_info = []
    for t in c.travaux:
        rendu = None
        if current_user.role == 'eleve':
            rendu = TravauxRendu.query.filter_by(eleve_id=current_user.id, travail_id=t.id).first()
        travaux_info.append({'travail': t, 'rendu': rendu})
    # Séances futures
    seances = Seance.query.filter_by(cours_id=cid).order_by(Seance.date_seance).all()
    return render_template('cours_apprendre.html', cours=c,
                           pdfs=pdfs, videos=videos, autres=autres,
                           travaux_info=travaux_info, seances=seances)

# ── RENDU TRAVAIL ────────────────────────────────────────────

@app.route('/travail/<int:tid>/rendre', methods=['POST'])
@login_required
def student_rendre_travail(tid):
    if current_user.role != 'eleve':
        flash('Réservé aux élèves.', 'warning'); return redirect(url_for('dashboard'))
    t = Travail.query.get_or_404(tid)
    existant = TravauxRendu.query.filter_by(eleve_id=current_user.id, travail_id=tid).first()
    fname = save_upload('fichier')
    if existant:
        if fname: existant.nom_fichier = fname
        existant.commentaire = request.form.get('commentaire','').strip()
        existant.date_rendu  = datetime.utcnow()
        db.session.commit()
        flash('Rendu mis à jour ! ✅', 'success')
    else:
        r = TravauxRendu(
            eleve_id    = current_user.id,
            travail_id  = tid,
            nom_fichier = fname,
            commentaire = request.form.get('commentaire','').strip()
        )
        db.session.add(r); db.session.commit()
        flash('Travail rendu ! ✅ Bien joué 💪', 'success')
    return redirect(url_for('cours_apprendre', cid=t.cours_id))

# ── CALENDRIER ÉLÈVE ─────────────────────────────────────────

@app.route('/student/calendrier')
@login_required
def student_calendrier():
    if not require_role('eleve'): return redirect(url_for('dashboard'))
    ids = [i.cours_id for i in current_user.inscriptions]
    seances = Seance.query.filter(Seance.cours_id.in_(ids)).order_by(Seance.date_seance).all()
    return render_template('student/student_calendrier.html', seances=seances)

# ── TÉLÉCHARGEMENT FICHIERS ──────────────────────────────────

@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    # Enseignant/admin: libre (auth seulement)
    if current_user.role in ('admin', 'enseignant'):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

    # Élève: sécurité stricte (ne pas exposer n'importe quel fichier)
    if current_user.role == 'eleve':
        r = Ressource.query.filter_by(nom_fichier=filename).first()
        t = None
        if not r:
            t = Travail.query.filter_by(nom_fichier=filename).first()
        
        # Si fichier inconnu -> bloquer
        if not r and not t:
            flash('Fichier introuvable ou accès refusé.', 'danger')
            return redirect(url_for('student_dashboard'))


        # Déterminer le cours
        cours_id = r.cours_id if r else t.cours_id
        insc = Inscription.query.filter_by(eleve_id=current_user.id, cours_id=cours_id).first()
        if not insc:
            flash('Inscription requise pour télécharger ce contenu.', 'warning')
            return redirect(url_for('cours_detail', cid=cours_id))

        # Strict: l'élève doit payer (paid=True)
        if not insc.paid:
            flash('Paiement requis pour télécharger ce contenu.', 'warning')
            return redirect(url_for('cours_detail', cid=cours_id))

        # Envoie le fichier (PDF/vidéo inclus)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


    flash('Accès non autorisé.', 'danger')
    return redirect(url_for('dashboard'))


# ═══════════════════════════════════════════════════════════
#              MESSAGERIE (tous les rôles)
# ═══════════════════════════════════════════════════════════

@app.route('/messages')
@login_required
def messages():
    recus = Message.query.filter_by(destinataire_id=current_user.id).order_by(Message.date_envoi.desc()).all()
    for m in recus: m.lu = True
    db.session.commit()
    if current_user.role == 'eleve':
        users = User.query.filter(User.role.in_(['enseignant','admin']), User.actif==True).all()
    elif current_user.role == 'enseignant':
        users = User.query.filter(User.role.in_(['eleve','admin']), User.actif==True).all()
    else:
        users = User.query.filter(User.id != current_user.id, User.actif==True).all()
    return render_template('messages.html', messages=recus, users=users)

@app.route('/messages/envoyer', methods=['POST'])
@login_required
def message_envoyer():
    dest = request.form.get('destinataire_id')
    txt  = request.form.get('contenu','').strip()
    if dest and txt:
        db.session.add(Message(contenu=txt, expediteur_id=current_user.id, destinataire_id=int(dest)))
        db.session.commit()
        flash('Message envoyé ! ✉️', 'success')
    return redirect(url_for('messages'))

# ═══════════════════════════════════════════════════════════
#                      PROFIL
# ═══════════════════════════════════════════════════════════

@app.route('/profil', methods=['GET','POST'])
@login_required
def profil():
    if request.method == 'POST':
        current_user.prenom = request.form.get('prenom', current_user.prenom).strip()
        current_user.nom    = request.form.get('nom',    current_user.nom).strip()
        current_user.bio    = request.form.get('bio',    current_user.bio or '').strip()
        nouveau_mdp = request.form.get('new_password','').strip()
        if nouveau_mdp:
            if len(nouveau_mdp) < 6:
                flash('Mot de passe trop court.', 'danger')
                return redirect(url_for('profil'))
            current_user.password = generate_password_hash(nouveau_mdp)
        db.session.commit()
        flash('Profil mis à jour. ✅', 'success')
        return redirect(url_for('profil'))
    return render_template('profil.html')

# ═══════════════════════════════════════════════════════════
#                    INIT DB
# ═══════════════════════════════════════════════════════════

# Injecter datetime.utcnow dans tous les templates
@app.context_processor
def inject_globals():
    return {'now': datetime.utcnow, 'current_year': datetime.utcnow().year}

def init_db():
    with app.app_context():
        # Migration SQLite minimale : ajouter les colonnes manquantes sans casser l’existant
        # (pas une vraie migration, mais évite l’erreur « no such column » après changement de modèle)
        db.create_all()
        # Migration SQLite : ajouter les colonnes manquantes (si nécessaire)
        if db.engine.dialect.name == 'sqlite':
            inspector = db.inspect(db.engine)
            cols = []
            try:
                cols = [c['name'] for c in inspector.get_columns('user')]
            except Exception:
                cols = []
            # SQLAlchemy peut encore utiliser l’ancienne table tant qu’elle n’est pas reflétée.
            # On force une réexécution/refresh du schéma SQLAlchemy après ALTER.
            if 'groupe_id' not in cols:
                try:
                    db.engine.execute('ALTER TABLE user ADD COLUMN groupe_id INTEGER')
                    db.session.remove()
                    db.reflect()
                except Exception:
                    pass



        # Créer un compte admin par défaut s'il n'existe pas
        if not User.query.filter_by(role='admin').first():

            admin = User(
                nom      = 'Admin',
                prenom   = 'Super',
                email    = 'admin@brainburst.com',
                password = generate_password_hash('Admin1234!'),
                role     = 'admin',
                actif    = True
            )
            db.session.add(admin)
            db.session.commit()
            print('Compte admin créé :')
            print('  Email    : admin@brainburst.com')
            print('  Password : Admin1234!')
        print('Base de données prête.')
        print('Ouvrez http://localhost:5000')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
