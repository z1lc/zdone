"""create tasks and task logs tables

Revision ID: 4cb4adbe81dc
Revises: dce3c487c686
Create Date: 2020-06-13 10:26:28.417888

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4cb4adbe81dc'
down_revision = 'dce3c487c686'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tasks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('ideal_interval', sa.Integer(), nullable=False),
    sa.Column('last_completion', sa.Date(), nullable=False),
    sa.Column('defer_until', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('task_id', sa.Integer(), nullable=False),
    sa.Column('at', sa.DateTime(), nullable=False),
    sa.Column('at_time_zone', sa.String(length=128), nullable=False),
    sa.Column('action', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('task_logs')
    op.drop_table('tasks')
    # ### end Alembic commands ###
