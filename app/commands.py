import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User, APIToken

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

@click.group('api-token')
def api_token_cli():
    """Manage API tokens."""
    pass

@api_token_cli.command('create')
@click.argument('name')
@with_appcontext
def create_api_token(name):
    """Create a new API token."""
    token = APIToken(
        name=name,
        token=APIToken.generate_token()
    )
    db.session.add(token)
    db.session.commit()
    click.echo(f"Created API token: {token.token}")

@api_token_cli.command('list')
@with_appcontext
def list_api_tokens():
    """List all API tokens."""
    tokens = APIToken.query.all()
    for token in tokens:
        status = "Active" if token.is_active else "Inactive"
        last_used = token.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if token.last_used_at else "Never"
        click.echo(f"{token.name}: {status} (Last used: {last_used})")

@api_token_cli.command('revoke')
@click.argument('name')
@with_appcontext
def revoke_api_token(name):
    """Revoke an API token."""
    token = APIToken.query.filter_by(name=name).first()
    if token:
        token.is_active = False
        db.session.commit()
        click.echo(f"Revoked token: {name}")
    else:
        click.echo(f"Token not found: {name}")

def init_app(app):
    """Register CLI commands with the app."""
    app.cli.add_command(create_admin_command)
    app.cli.add_command(api_token_cli)