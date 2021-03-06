"""task completion

Revision ID: fcbfd34e49b5
Revises: 83a3d27de55e
Create Date: 2019-11-23 19:56:24.429296

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fcbfd34e49b5'
down_revision = '83a3d27de55e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('external_service_task_completions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('service', sa.String(length=128), nullable=False),
    sa.Column('task_id', sa.String(length=128), nullable=False),
    sa.Column('subtask_id', sa.String(length=128), nullable=True),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('external_service_task_completions')
    # ### end Alembic commands ###
