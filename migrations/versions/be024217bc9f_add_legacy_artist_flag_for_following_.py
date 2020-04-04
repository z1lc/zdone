"""add legacy artist flag for following migration

Revision ID: be024217bc9f
Revises: 858f0df4d994
Create Date: 2020-04-04 14:41:39.426528

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'be024217bc9f'
down_revision = '858f0df4d994'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('managed_spotify_artists', sa.Column('legacy', sa.Boolean(), server_default='true', nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('managed_spotify_artists', 'legacy')
    # ### end Alembic commands ###