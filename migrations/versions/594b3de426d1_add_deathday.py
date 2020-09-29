"""add deathday

Revision ID: 594b3de426d1
Revises: e4df187458f7
Create Date: 2020-09-29 09:40:30.404482

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '594b3de426d1'
down_revision = 'e4df187458f7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('video_persons', sa.Column('deathday', sa.Date(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('video_persons', 'deathday')
    # ### end Alembic commands ###
