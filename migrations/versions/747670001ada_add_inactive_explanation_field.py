"""add inactive explanation field

Revision ID: 747670001ada
Revises: 4cb4adbe81dc
Create Date: 2020-06-13 14:33:37.199973

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '747670001ada'
down_revision = '4cb4adbe81dc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('reminders', sa.Column('inactive_explanation', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('reminders', 'inactive_explanation')
    # ### end Alembic commands ###
