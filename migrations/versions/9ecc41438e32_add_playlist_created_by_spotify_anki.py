"""add playlist created by spotify+anki

Revision ID: 9ecc41438e32
Revises: e18db9a77e1b
Create Date: 2020-07-16 21:57:51.278999

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9ecc41438e32'
down_revision = 'e18db9a77e1b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('spotify_playlist_uri', sa.String(length=128), nullable=True))
    op.create_unique_constraint(None, 'users', ['spotify_playlist_uri'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'spotify_playlist_uri')
    # ### end Alembic commands ###
