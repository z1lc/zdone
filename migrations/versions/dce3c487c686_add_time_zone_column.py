"""add time zone column

Revision ID: dce3c487c686
Revises: 8a2073751905
Create Date: 2020-06-12 10:28:37.417674

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dce3c487c686'
down_revision = '8a2073751905'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('current_time_zone', sa.String(length=128), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'current_time_zone')
    # ### end Alembic commands ###