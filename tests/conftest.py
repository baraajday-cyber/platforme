"""Fixtures pytest pour l'application BrainBurst."""
import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

# Désactiver l'initialisation automatique de la DB au chargement d'app.py
os.environ['BRAINBURST_NO_INIT'] = '1'

# Permettre l'import de app.py depuis la racine du projet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from app import db
from app import User, Groupe, Matiere, Cours, Ressource, Travail, Seance, Inscription, Message
from werkzeug.security import generate_password_hash


@pytest.fixture()
def app():
    """Application Flask configurée sur une base SQLite temporaire."""
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI='sqlite:///' + db_path,
        UPLOAD_FOLDER=os.path.join(tempfile.gettempdir(), 'brainburst_test_uploads'),
    )
    os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture()
def client(app):
    """Client de test."""
    return app.test_client()


def make_user(nom, prenom, email, password, role, **kwargs):
    """Crée un utilisateur en base."""
    u = User(
        nom=nom,
        prenom=prenom,
        email=email,
        password=generate_password_hash(password),
        role=role,
        actif=kwargs.get('actif', True),
        groupe_id=kwargs.get('groupe_id'),
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def seed(app):
    """Jeu de données complet pour les tests."""
    with app.app_context():
        admin = make_user('Admin', 'Super', 'admin@test.com', 'Admin1234!', 'admin')
        ens = make_user('Pro', 'Mme', 'ens@test.com', 'Ens1234!', 'enseignant')
        eleve = make_user('Eleve', 'M.', 'eleve@test.com', 'Eleve1234!', 'eleve')

        matiere = Matiere(nom='Mathématiques', couleur='#4D96FF', icone='📐', actif=True)
        db.session.add(matiere)
        db.session.commit()

        cours_publie = Cours(
            titre='Algèbre niveau 1',
            description='Cours d\'algèbre de base',
            niveau='Débutant',
            publie=True,
            enseignant_id=ens.id,
            matiere_id=matiere.id,
        )
        cours_brouillon = Cours(
            titre='Brouillon secret',
            description='Cours non publié',
            niveau='Débutant',
            publie=False,
            enseignant_id=ens.id,
            matiere_id=matiere.id,
        )
        db.session.add_all([cours_publie, cours_brouillon])
        db.session.commit()

        ressource = Ressource(
            titre='Cours PDF',
            description='Support de cours',
            type_fichier='pdf',
            nom_fichier='cours1.pdf',
            cours_id=cours_publie.id,
        )
        db.session.add(ressource)

        travail = Travail(
            titre='Exercice 1',
            description='Faire les exercices 1 à 5',
            date_limite=datetime.utcnow() + timedelta(days=7),
            cours_id=cours_publie.id,
        )
        db.session.add(travail)

        seance = Seance(
            titre='Séance 1',
            description='Présentation',
            date_seance=datetime.utcnow() + timedelta(days=2),
            duree=60,
            lien_meet='https://meet.google.com/abc-defg-hij',
            cours_id=cours_publie.id,
        )
        db.session.add(seance)
        db.session.commit()

        # Charger les clés primaires AVANT de fermer le contexte
        # (sinon l'accès à `.id` hors session lève DetachedInstanceError)
        _ = [admin.id, ens.id, eleve.id, matiere.id,
             cours_publie.id, cours_brouillon.id,
             ressource.id, travail.id, seance.id]

        return {
            'admin': admin,
            'enseignant': ens,
            'eleve': eleve,
            'matiere': matiere,
            'cours_publie': cours_publie,
            'cours_brouillon': cours_brouillon,
            'ressource': ressource,
            'travail': travail,
            'seance': seance,
        }


def login(client, email, password):
    """Helper : connecte un utilisateur."""
    return client.post('/login', data={'email': email, 'password': password},
                       follow_redirects=True)

