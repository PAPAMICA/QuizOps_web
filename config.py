import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///quiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    QUIZ_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'quiz_data')
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)

    # Configuration email
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 100,
        'max_overflow': 50,
        'pool_timeout': 30,
        'pool_recycle': 300,
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