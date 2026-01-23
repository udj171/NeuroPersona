# ============================================================================
# SCRIPT 19: conftest.py - Pytest Configuration & Fixtures
# ============================================================================

conftest_code = '''
import pytest
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from app import create_app
from models import db, User, Assessment, Result
from config import TestingConfig

@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    return app

@pytest.fixture(scope='function')
def client(app):
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()

@pytest.fixture
def sample_user(db_session):
    user = User(age=30, sex='M')
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_assessment(db_session, sample_user):
    assessment = Assessment(
        user_id=sample_user.id,
        ip_address='127.0.0.1',
        user_agent='pytest',
    )
    db_session.add(assessment)
    db_session.commit()
    return assessment

@pytest.fixture
def sample_responses():
    import numpy as np
    np.random.seed(42)
    return np.random.randint(0, 11, size=35).tolist()

@pytest.fixture
def sample_scoring_result(sample_responses):
    return {
        'raw_domain_scores': {
            'R': 5.0, 'S': 5.0, 'C': 5.0,
            'A': 5.0, 'O': 5.0, 'E': 5.0
        },
        'deception_susceptibility': 0.5,
        'corrected_domain_scores': {
            'R': 4.9, 'S': 5.0, 'C': 5.1,
            'A': 4.8, 'O': 5.2, 'E': 5.0
        },
        'domain_biases': {
            'R': 0.1, 'S': 0.0, 'C': -0.1,
            'A': 0.2, 'O': -0.2, 'E': 0.0
        },
        'vae_input': [4.9, 5.0, 5.1, 4.8, 5.2, 5.0, 0.5, 1.5, 0.2],
    }
'''
