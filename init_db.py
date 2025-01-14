from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
import os

# Create a minimal application
app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db = SQLAlchemy(app)

# Import models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.String(64), nullable=False)
    category = db.Column(db.String(32), nullable=False)
    level = db.Column(db.String(16), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    answers = db.Column(db.JSON)
    time_spent = db.Column(db.Integer)

def init_db():
    # Remove existing database
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'quiz.db')
    if os.path.exists(db_path):
        print(f'Suppression de la base de données existante: {db_path}')
        os.remove(db_path)
    
    print('Création des tables...')
    db.create_all()
    print('Base de données initialisée avec succès!')

if __name__ == '__main__':
    init_db() 