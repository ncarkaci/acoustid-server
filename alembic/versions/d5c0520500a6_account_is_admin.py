"""account_is_admin

Revision ID: d5c0520500a6
Revises: 3b48d5f44110
Create Date: 2016-02-10 22:52:06.114214

"""

# revision identifiers, used by Alembic.
revision = 'd5c0520500a6'
down_revision = '3b48d5f44110'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()


def upgrade_default():
    op.add_column('account',
        sa.Column('is_admin', sa.Boolean(), server_default=sa.text('false'), nullable=False)
    )


def downgrade_default():
    op.drop_column('account', 'is_admin')


def upgrade_slow():
    pass


def downgrade_slow():
    pass
