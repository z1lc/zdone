"""add generic reviewlog model

Revision ID: 73bd7fe3e3f6
Revises: bbfb7b357fde
Create Date: 2020-11-14 13:38:00.705423

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73bd7fe3e3f6'
down_revision = 'bbfb7b357fde'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('anki_review_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('zdone_id', sa.Text(), nullable=False),
    sa.Column('template_name', sa.Text(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('anki_review_logs')
    # ### end Alembic commands ###
