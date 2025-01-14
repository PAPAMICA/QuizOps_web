"""Add preferred_language field to user table"""
from app import create_app, db

def upgrade():
    app = create_app()
    with app.app_context():
        # Add the preferred_language column
        db.engine.execute('ALTER TABLE user ADD COLUMN preferred_language VARCHAR(2) DEFAULT "fr"')
        print("Added preferred_language column to user table")

def downgrade():
    app = create_app()
    with app.app_context():
        # Remove the preferred_language column
        db.engine.execute('ALTER TABLE user DROP COLUMN preferred_language')
        print("Removed preferred_language column from user table")

if __name__ == '__main__':
    upgrade() 