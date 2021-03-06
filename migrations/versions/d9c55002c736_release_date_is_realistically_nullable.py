"""release date is realistically nullable

Revision ID: d9c55002c736
Revises: 6487627f037a
Create Date: 2021-01-04 18:06:42.502872

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9c55002c736'
down_revision = '6487627f037a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('spotify_albums', 'released_at',
               existing_type=sa.DATE(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('spotify_albums', 'released_at',
               existing_type=sa.DATE(),
               nullable=False)
    # ### end Alembic commands ###
