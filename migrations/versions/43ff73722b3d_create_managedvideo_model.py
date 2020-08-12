"""create managedvideo model

Revision ID: 43ff73722b3d
Revises: dcb34c72b5f0
Create Date: 2020-08-08 22:35:47.172316

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '43ff73722b3d'
down_revision = 'dcb34c72b5f0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('managed_videos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('video_id', sa.Text(), nullable=False),
    sa.Column('date_added', sa.Date(), server_default=sa.text('CURRENT_DATE'), nullable=False),
    sa.Column('watched', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'video_id', name='_user_id_and_video_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('managed_videos')
    # ### end Alembic commands ###