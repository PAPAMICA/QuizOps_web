from flask import Blueprint

# Importer les blueprints
from app.routes.main import bp as main_bp
from app.routes.auth import bp as auth_bp
from app.routes.quiz import bp as quiz_bp

# Créer le blueprint principal
bp = Blueprint('main', __name__)

# Enregistrer les autres blueprints
def init_app(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(quiz_bp, url_prefix='/quiz') 