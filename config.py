import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///quiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BABEL_DEFAULT_LOCALE = 'fr'
    LANGUAGES = ['fr', 'en']
    QUIZ_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'quiz_data')
    PERMANENT_SESSION_LIFETIME = timedelta(days=31) 