"""add last air date for TV

Revision ID: 447c9f9d585b
Revises: 3f59e50fd925
Create Date: 2020-07-25 11:47:30.133873

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '447c9f9d585b'
down_revision = '3f59e50fd925'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('videos', sa.Column('last_air_date', sa.Date(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('videos', 'last_air_date')
    # ### end Alembic commands ###
