"""add name

Revision ID: 1f2c8a628b05
Revises: 46cc49df2efd
Create Date: 2020-07-19 18:00:40.264096

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f2c8a628b05'
down_revision = '46cc49df2efd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('video_persons', sa.Column('name', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('video_persons', 'name')
    # ### end Alembic commands ###
