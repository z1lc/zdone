"""add TMDB session id

Revision ID: dcb34c72b5f0
Revises: 4c12a602c9f4
Create Date: 2020-08-08 14:47:16.063308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dcb34c72b5f0'
down_revision = '4c12a602c9f4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('tmdb_session_id', sa.Text(), nullable=True))
    op.create_unique_constraint(None, 'users', ['tmdb_session_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('users', 'tmdb_session_id')
    # ### end Alembic commands ###
