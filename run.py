from app import create_app, db
from app.models import User, QuizResult
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db)

@app.cli.command()
def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        print('Database initialized.')

@app.cli.command()
def compile_translations():
    """Compile all translations."""
    import os
    os.system('pybabel compile -d app/translations')
    print('Translations compiled.')

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
    app.run(debug=True, port=8080)