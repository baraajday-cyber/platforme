"""Tests des flux critiques de l'application BrainBurst.

Couvre : authentification, contrôle d'accès par rôle, catalogue,
inscription élève, accès au contenu (paid), rendu de travail, API séances,
messagerie.
"""
from conftest import login, make_user
from app import db, Inscription, TravauxRendu, Message


# ═══════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════

def test_login_success_admin(client, seed):
    r = client.post('/login', data={'email': 'admin@test.com', 'password': 'Admin1234!'})
    assert r.status_code == 302
    r2 = client.get('/dashboard', follow_redirects=True)
    assert b'Tableau de bord' in r2.data


def test_login_invalid_credentials(client):
    r = client.post('/login', data={'email': 'inconnu@test.com', 'password': 'mauvais'})
    assert r.status_code == 200
    assert 'Email ou mot de passe incorrect'.encode('utf-8') in r.data


def test_login_inactive_account(client, app):
    with app.app_context():
        make_user('Test', 'Inactif', 'inactif@test.com', 'Test1234!', 'eleve', actif=False)
    r = client.post('/login', data={'email': 'inactif@test.com', 'password': 'Test1234!'}, follow_redirects=True)
    assert 'désactivé'.encode('utf-8') in r.data


def test_access_protected_without_login(client):
    for path in ['/admin', '/teacher', '/student', '/messages', '/download/test.pdf']:
        r = client.get(path)
        assert r.status_code in (301, 302), f'{path} doit rediriger vers /login'


# ═══════════════════════════════════════════
# RÔLES
# ═══════════════════════════════════════════

def test_eleve_cannot_access_teacher_route(client, seed):
    login(client, 'eleve@test.com', 'Eleve1234!')
    r = client.get('/teacher', follow_redirects=True)
    assert 'Accès non autorisé'.encode('utf-8') in r.data


def test_eleve_cannot_access_admin_route(client, seed):
    login(client, 'eleve@test.com', 'Eleve1234!')
    r = client.get('/admin', follow_redirects=True)
    assert 'Accès non autorisé'.encode('utf-8') in r.data


# ═══════════════════════════════════════════
# CATALOGUE COURS
# ═══════════════════════════════════════════

def test_catalog_only_published(client, seed):
    login(client, 'eleve@test.com', 'Eleve1234!')
    r = client.get('/cours')
    assert r.status_code == 200
    assert 'Algèbre niveau 1'.encode('utf-8') in r.data
    assert b'Brouillon secret' not in r.data


def test_catalog_filter_matiere_invalid(client, seed):
    """matiere_id non numérique ne doit PAS crasher."""
    login(client, 'eleve@test.com', 'Eleve1234!')
    r = client.get('/cours?matiere_id=abc')
    assert r.status_code == 200


# ═══════════════════════════════════════════
# INSCRIPTION & ACCÈS CONTENU
# ═══════════════════════════════════════════

def test_student_can_inscribe(client, seed):
    login(client, 'eleve@test.com', 'Eleve1234!')
    cid = seed['cours_publie'].id
    r = client.post(f'/cours/{cid}/inscrire', follow_redirects=True)
    assert r.status_code == 200
    with client.application.app_context():
        assert Inscription.query.filter_by(eleve_id=seed['eleve'].id, cours_id=cid).first() is not None


def test_apprendre_blocked_when_not_paid(client, seed):
    """Sans paid=True, l'élève inscrit ne doit PAS accéder au contenu."""
    login(client, 'eleve@test.com', 'Eleve1234!')
    cid = seed['cours_publie'].id
    client.post(f'/cours/{cid}/inscrire')
    r = client.get(f'/cours/{cid}/apprendre', follow_redirects=True)
    assert b'Paiement requis' in r.data


def test_apprendre_allowed_when_paid(client, seed):
    login(client, 'eleve@test.com', 'Eleve1234!')
    cid = seed['cours_publie'].id
    client.post(f'/cours/{cid}/inscrire')
    with client.application.app_context():
        insc = Inscription.query.filter_by(eleve_id=seed['eleve'].id, cours_id=cid).first()
        insc.paid = True
        db.session.commit()
    r = client.get(f'/cours/{cid}/apprendre')
    assert r.status_code == 200
    assert 'Algèbre niveau 1'.encode('utf-8') in r.data


# ═══════════════════════════════════════════
# RENDU TRAVAIL
# ═══════════════════════════════════════════

def test_student_render_travail(client, seed):
    login(client, 'eleve@test.com', 'Eleve1234!')
    tid = seed['travail'].id
    client.post(f'/cours/{seed["cours_publie"].id}/inscrire')
    with client.application.app_context():
        insc = Inscription.query.filter_by(eleve_id=seed['eleve'].id, cours_id=seed['cours_publie'].id).first()
        insc.paid = True
        db.session.commit()
    r = client.post(f'/travail/{tid}/rendre',
                    data={'commentaire': 'Voici mon travail'},
                    follow_redirects=True)
    assert r.status_code == 200
    with client.application.app_context():
        rendu = TravauxRendu.query.filter_by(eleve_id=seed['eleve'].id, travail_id=tid).first()
        assert rendu is not None
        assert rendu.commentaire == 'Voici mon travail'


def test_student_render_updates_existing(client, seed):
    login(client, 'eleve@test.com', 'Eleve1234!')
    tid = seed['travail'].id
    cid = seed['cours_publie'].id
    client.post(f'/cours/{cid}/inscrire')
    with client.application.app_context():
        insc = Inscription.query.filter_by(eleve_id=seed['eleve'].id, cours_id=cid).first()
        insc.paid = True
        db.session.commit()
    client.post(f'/travail/{tid}/rendre', data={'commentaire': 'Version 1'}, follow_redirects=True)
    r = client.post(f'/travail/{tid}/rendre', data={'commentaire': 'Version 2'}, follow_redirects=True)
    assert r.status_code == 200
    with client.application.app_context():
        rendus = TravauxRendu.query.filter_by(eleve_id=seed['eleve'].id, travail_id=tid).all()
        assert len(rendus) == 1
        assert rendus[0].commentaire == 'Version 2'


# ═══════════════════════════════════════════
# API SÉANCES
# ═══════════════════════════════════════════

def test_api_seances_shape(client, seed):
    login(client, 'admin@test.com', 'Admin1234!')
    r = client.get('/api/seances')
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    ev = data[0]
    for key in ['id', 'title', 'start', 'url', 'color', 'extendedProps']:
        assert key in ev


# ═══════════════════════════════════════════
# MESSAGERIE
# ═══════════════════════════════════════════

def test_messages_mark_as_read(client, seed):
    with client.application.app_context():
        db.session.add(Message(contenu='Bonjour', expediteur_id=seed['enseignant'].id,
                               destinataire_id=seed['eleve'].id))
        db.session.commit()
    login(client, 'eleve@test.com', 'Eleve1234!')
    r = client.get('/messages')
    assert r.status_code == 200
    with client.application.app_context():
        msg = Message.query.first()
        assert msg.lu is True


def test_message_envoyer(client, seed):
    login(client, 'eleve@test.com', 'Eleve1234!')
    r = client.post('/messages/envoyer',
                    data={'destinataire_id': seed['enseignant'].id, 'contenu': 'Question sur le cours'},
                    follow_redirects=True)
    assert r.status_code == 200
    with client.application.app_context():
        assert Message.query.count() == 1

