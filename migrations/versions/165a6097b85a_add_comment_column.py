"""add comment column

Revision ID: 165a6097b85a
Revises: 772afc03fa3d
Create Date: 2020-03-14 14:17:57.984124

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '165a6097b85a'
down_revision = '772afc03fa3d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('managed_spotify_artists', sa.Column('comment', sa.String(length=128), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('managed_spotify_artists', 'comment')
    # ### end Alembic commands ###
