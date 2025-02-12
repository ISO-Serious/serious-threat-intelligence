import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User

@click.command('create-admin')
@click.option('--username', prompt=True, help='Admin username')
@click.option('--email', prompt=True, help='Admin email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@with_appcontext
def create_admin_command(username, email, password):
    """Create an admin user."""
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            click.echo('Error: Username already exists')
            return
            
        user = User.query.filter_by(email=email).first()
        if user:
            click.echo('Error: Email already exists')
            return
            
        user = User(
            username=username,
            email=email,
            role='admin',
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f'Successfully created admin user: {username}')
    except Exception as e:
        click.echo(f'Error creating admin user: {str(e)}')