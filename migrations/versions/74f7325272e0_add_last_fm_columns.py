"""add last.fm columns

Revision ID: 74f7325272e0
Revises: 78d9f13b58b2
Create Date: 2020-04-09 00:38:49.708256

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '74f7325272e0'
down_revision = '78d9f13b58b2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('managed_spotify_artists', sa.Column('last_fm_scrobbles', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('last_fm_last_refresh_time', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_fm_username', sa.String(length=128), nullable=True))
    op.create_unique_constraint(None, 'users', ['last_fm_username'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'last_fm_username')
    op.drop_column('users', 'last_fm_last_refresh_time')
    op.drop_column('managed_spotify_artists', 'last_fm_scrobbles')
    # ### end Alembic commands ###
