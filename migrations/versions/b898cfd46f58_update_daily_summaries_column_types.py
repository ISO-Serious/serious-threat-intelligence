"""Update daily_summaries column types

Revision ID: b898cfd46f58
Revises: a87b4c37fc6d
Create Date: 2025-02-11 12:27:24.226474

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b898cfd46f58'
down_revision = 'a87b4c37fc6d'
branch_labels = None
depends_on = None


def upgrade():
    # Keep both columns as varchar/string type
    op.execute("""
        ALTER TABLE daily_summaries 
        ALTER COLUMN date TYPE varchar,
        ALTER COLUMN generated_at TYPE varchar
    """)

def downgrade():
    pass