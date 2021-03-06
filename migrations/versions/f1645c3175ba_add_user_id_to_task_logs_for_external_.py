"""add user id to task logs for external tasks

Revision ID: f1645c3175ba
Revises: 9689a542a9c5
Create Date: 2020-08-11 21:34:52.018807

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1645c3175ba'
down_revision = '9689a542a9c5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('task_logs', sa.Column('user_id', sa.Integer()))
    op.create_foreign_key(None, 'task_logs', 'users', ['user_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'task_logs', type_='foreignkey')
    op.drop_column('task_logs', 'user_id')
    # ### end Alembic commands ###
