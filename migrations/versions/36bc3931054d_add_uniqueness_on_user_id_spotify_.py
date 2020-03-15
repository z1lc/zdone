"""add uniqueness on user_id+spotify_artist_uri

Revision ID: 36bc3931054d
Revises: 2c22a1dd13af
Create Date: 2020-03-14 17:52:39.913009

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '36bc3931054d'
down_revision = '2c22a1dd13af'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('_user_id_and_spotify_artist_uri', 'managed_spotify_artists', ['user_id', 'spotify_artist_uri'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('_user_id_and_spotify_artist_uri', 'managed_spotify_artists', type_='unique')
    # ### end Alembic commands ###