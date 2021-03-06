"""create unique constraint on readwise_highlights

Revision ID: 147022092eef
Revises: 73bd7fe3e3f6
Create Date: 2020-11-14 18:23:18.467679

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '147022092eef'
down_revision = '73bd7fe3e3f6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('_managed_readwise_book_id_and_text', 'readwise_highlights', ['managed_readwise_book_id', 'text'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('_managed_readwise_book_id_and_text', 'readwise_highlights', type_='unique')
    # ### end Alembic commands ###
