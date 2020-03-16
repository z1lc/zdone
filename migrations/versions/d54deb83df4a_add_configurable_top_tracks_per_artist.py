"""add configurable top tracks per artist

Revision ID: d54deb83df4a
Revises: 36bc3931054d
Create Date: 2020-03-15 21:44:51.114714

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd54deb83df4a'
down_revision = '36bc3931054d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('managed_spotify_artists', sa.Column('num_top_tracks', sa.Integer(), server_default='3', nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('managed_spotify_artists', 'num_top_tracks')
    # ### end Alembic commands ###
