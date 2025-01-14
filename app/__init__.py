from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
babel = Babel()

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(['fr', 'en'])

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configuration de Babel
    app.config['BABEL_DEFAULT_LOCALE'] = 'fr'
    app.config['BABEL_SUPPORTED_LOCALES'] = ['fr', 'en']

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    babel.init_app(app)

    # Initialisation du gestionnaire de quiz
    from app.quiz_manager import QuizManager
    quiz_repo_path = os.path.join(os.path.dirname(app.root_path), '..', 'QuizOps_quiz')
    app.quiz_manager = QuizManager(quiz_repo_path)

    # Register the user loader
    from app.models.user import User
    @login.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Initialisation des routes
    from app.routes import init_app as init_routes
    init_routes(app)

    return app

from app import models