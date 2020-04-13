"""add testing boolean to separate followed vs tested artists

Revision ID: 0b2399fd0c4f
Revises: 68bfc3ad5986
Create Date: 2020-04-12 19:28:50.709294

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b2399fd0c4f'
down_revision = '68bfc3ad5986'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('managed_spotify_artists', sa.Column('testing', sa.Boolean(), server_default='false', nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('managed_spotify_artists', 'testing')
    # ### end Alembic commands ###
