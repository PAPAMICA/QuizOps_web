from app import create_app, db
from flask_migrate import Migrate, upgrade
import os

app = create_app()
migrate = Migrate(app, db)

with app.app_context():
    # Supprime la base de données si elle existe
    if os.path.exists('quiz.db'):
        os.remove('quiz.db')

    # Supprime le dossier migrations s'il existe
    if os.path.exists('migrations'):
        import shutil
        shutil.rmtree('migrations')

    # Initialise les migrations
    from flask_migrate import init, migrate, upgrade
    init()
    migrate()
    upgrade()

    print("Base de données réinitialisée avec succès!")