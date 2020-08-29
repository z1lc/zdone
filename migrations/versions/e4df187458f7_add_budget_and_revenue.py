"""add budget and revenue

Revision ID: e4df187458f7
Revises: a68c22349a06
Create Date: 2020-08-28 23:36:07.977188

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4df187458f7'
down_revision = 'a68c22349a06'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('videos', sa.Column('budget', sa.BigInteger(), nullable=True))
    op.add_column('videos', sa.Column('revenue', sa.BigInteger(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('videos', 'revenue')
    op.drop_column('videos', 'budget')
    # ### end Alembic commands ###
