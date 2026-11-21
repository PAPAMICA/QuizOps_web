import os

from app import create_app, db
from app.models import User, QuizResult
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db)


def _debug_enabled():
    """Debug stays off unless FLASK_DEBUG is explicitly turned on."""
    return os.environ.get('FLASK_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}

@app.cli.command()
def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        print('Database initialized.')


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'QuizResult': QuizResult}

if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print('Database initialized successfully.')
        except Exception as e:
            print(f'Error initializing database: {e}')
    app.run(debug=_debug_enabled(), port=8080, host='0.0.0.0')