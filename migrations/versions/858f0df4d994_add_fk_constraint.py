"""add FK constraint

Revision ID: 858f0df4d994
Revises: 9b2dd325878b
Create Date: 2020-03-23 20:25:04.884407

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '858f0df4d994'
down_revision = '9b2dd325878b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, 'managed_spotify_artists', 'spotify_artists', ['spotify_artist_uri'], ['uri'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'managed_spotify_artists', type_='foreignkey')
    # ### end Alembic commands ###
