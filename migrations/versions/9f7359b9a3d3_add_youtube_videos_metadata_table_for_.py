"""add youtube videos metadata table for duration

Revision ID: 9f7359b9a3d3
Revises: bd2d19af16eb
Create Date: 2020-07-22 09:40:13.867960

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f7359b9a3d3'
down_revision = 'bd2d19af16eb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('youtube_videos',
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('duration_seconds', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('youtube_videos')
    # ### end Alembic commands ###
