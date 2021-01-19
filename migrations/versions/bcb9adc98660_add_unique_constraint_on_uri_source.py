"""add unique constraint on uri+source

Revision ID: bcb9adc98660
Revises: 2e6c8a0c4ea5
Create Date: 2021-01-18 20:21:29.229598

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bcb9adc98660'
down_revision = '2e6c8a0c4ea5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'best_selling_artists', ['artist_uri', 'source'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'best_selling_artists', type_='unique')
    # ### end Alembic commands ###
