from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
mail = Mail()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)

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

    from app.routes import main
    app.register_blueprint(main.bp)

    from app.routes import auth
    app.register_blueprint(auth.bp)

    from app.routes import admin
    app.register_blueprint(admin.bp)

    from app.cli import register_commands
    register_commands(app)

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    return app

from app import models