import click
from flask.cli import with_appcontext
from app.models.user import User
from app import db

def register_commands(app):
    @app.cli.command('make-admin')
    @click.argument('username')
    @with_appcontext
    def make_admin(username):
        """Promote a user to admin status."""
        user = User.query.filter_by(username=username).first()
        if user is None:
            click.echo(f'Error: User {username} not found')
            return
        
        user.is_admin = True
        db.session.commit()
        click.echo(f'User {username} is now an admin') 