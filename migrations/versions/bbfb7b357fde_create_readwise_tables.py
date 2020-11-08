"""create readwise tables

Revision ID: bbfb7b357fde
Revises: 24dff3f748d6
Create Date: 2020-11-08 13:24:23.016306

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bbfb7b357fde'
down_revision = '24dff3f748d6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('readwise_books',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('author', sa.Text(), nullable=True),
    sa.Column('cover_image_url', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('managed_readwise_books',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('readwise_book_id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['readwise_book_id'], ['readwise_books.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'readwise_book_id', 'category', name='_user_id_readwise_book_id_and_category')
    )
    op.create_table('readwise_highlights',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('managed_readwise_book_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['managed_readwise_book_id'], ['managed_readwise_books.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('readwise_highlights')
    op.drop_table('managed_readwise_books')
    op.drop_table('readwise_books')
    # ### end Alembic commands ###
