"""add in production to differentiate ended shows vs. completed ones

Revision ID: 7be2878b34fb
Revises: 447c9f9d585b
Create Date: 2020-07-25 12:02:46.869898

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7be2878b34fb'
down_revision = '447c9f9d585b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('videos', sa.Column('in_production', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('videos', 'in_production')
    # ### end Alembic commands ###
