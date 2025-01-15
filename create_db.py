from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os
from werkzeug.security import generate_password_hash
from datetime import datetime
import uuid

# Create a minimal application
app = Flask(__name__)

# Configure the database URI for PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@quizops-db:5432/quizops'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,
    'pool_timeout': 30,
    'pool_recycle': 300,
    'max_overflow': 10,
    'pool_pre_ping': True,
    'pool_use_lifo': True,
    'echo_pool': True,
    'connect_args': {
        'connect_timeout': 10,
        'application_name': 'quizops',
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
        'options': '-c statement_timeout=30000'
    }
}

# Initialize database
db = SQLAlchemy(app)

# Import models
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6))
    verification_code_expires = db.Column(db.DateTime)
    reset_password_token = db.Column(db.String(100), unique=True)
    reset_password_expires = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)
    private_profile = db.Column(db.Boolean, default=False)
    
    # Social media fields
    twitter_username = db.Column(db.String(64))
    bluesky_handle = db.Column(db.String(64))
    linkedin_url = db.Column(db.String(128))
    website_url = db.Column(db.String(128))
    github_username = db.Column(db.String(64))
    gitlab_username = db.Column(db.String(64))
    dockerhub_username = db.Column(db.String(64))
    stackoverflow_url = db.Column(db.String(128))
    medium_username = db.Column(db.String(64))
    dev_to_username = db.Column(db.String(64))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class QuizResult(db.Model):
    __tablename__ = 'quiz_result'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.String(64), nullable=False)
    quiz_title = db.Column(db.String(256))
    category = db.Column(db.String(256), nullable=False)
    level = db.Column(db.String(16), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    answers = db.Column(db.JSON)
    time_spent = db.Column(db.Integer)

    @property
    def percentage(self):
        """Calcule le pourcentage de réussite"""
        try:
            return round((self.score / self.max_score) * 100, 1)
        except (ZeroDivisionError, TypeError):
            return 0.0

class Quiz(db.Model):
    __tablename__ = 'quiz'
    id = db.Column(db.String(64), primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(32), nullable=False)
    level = db.Column(db.String(16), nullable=False)
    questions = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

def create_admin_user():
    existing_admin = User.query.filter_by(is_admin=True).first()
    if existing_admin:
        print('An admin user already exists. No action taken.')
        return

    admin = User(
        username='PAPAMICA',
        email='mickael@papamica.com',
        email_verified=True,
        is_admin=True,
        private_profile=False
    )
    admin.set_password('admin')
    db.session.add(admin)
    db.session.commit()
    print('\nAdmin user created:')
    print('Username: PAPAMICA')
    print('Password: admin')
    print('Email: mickael@papamica.com')

def init_db():
    # Create the database if it does not exist
    db.create_all()

    print('Création des tables...')

    # Vérification des tables créées
    tables = db.engine.table_names()
    print('\nTables créées:')
    for table in tables:
        print(f'- {table}')

    # Vérification des tables attendues
    expected_tables = {'user', 'quiz_result', 'quiz'}
    actual_tables = set(tables)

    if expected_tables == actual_tables:
        print('\nToutes les tables attendues ont été créées avec succès!')
        print(f'Base de données créée à: quizops')

        # Vérifie si l'utilisateur admin existe déjà
        existing_admin = User.query.filter_by(username='admin').first()
        if not existing_admin:
            # Création de l'utilisateur admin
            create_admin_user()
        else:
            print('L\'utilisateur admin existe déjà.')
    else:
        missing = expected_tables - actual_tables
        extra = actual_tables - expected_tables
        if missing:
            print(f'\nTables manquantes: {missing}')
        if extra:
            print(f'\nTables inattendues: {extra}')

if __name__ == '__main__':
    init_db()