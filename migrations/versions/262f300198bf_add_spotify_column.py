"""add spotify column

Revision ID: 262f300198bf
Revises: a1654de7c7d1
Create Date: 2020-03-14 12:35:45.880953

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '262f300198bf'
down_revision = 'a1654de7c7d1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('spotify_token_json', sa.String(length=1024), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'spotify_token_json')
    # ### end Alembic commands ###
