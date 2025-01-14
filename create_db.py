from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os
from werkzeug.security import generate_password_hash
from datetime import datetime
from app import create_app, db
from app.models.user import User, QuizResult

# Create a minimal application
app = Flask(__name__)

# Configure the database URI for PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@db:5432/quizops'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Import models
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6))
    verification_code_expires = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

class QuizResult(db.Model):
    __tablename__ = 'quiz_result'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.String(64), nullable=False)
    quiz_title = db.Column(db.String(128))
    category = db.Column(db.String(32), nullable=False)
    level = db.Column(db.String(16), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    answers = db.Column(db.JSON)
    time_spent = db.Column(db.Integer)

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
    admin = User(
        username='admin',
        email='admin@quizops.local',
        email_verified=True,  # L'admin est vérifié par défaut
        is_admin=True
    )
    admin.set_password('admin')  # À changer en production !
    db.session.add(admin)
    db.session.commit()
    print('\nUtilisateur admin créé:')
    print('Username: admin')
    print('Password: admin')
    print('Email: admin@quizops.local')

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

        # Création de l'utilisateur admin
        create_admin_user()
    else:
        missing = expected_tables - actual_tables
        extra = actual_tables - expected_tables
        if missing:
            print(f'\nTables manquantes: {missing}')
        if extra:
            print(f'\nTables inattendues: {extra}')

if __name__ == '__main__':
    init_db()