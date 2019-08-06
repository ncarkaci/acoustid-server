"""submission result

Revision ID: 4581a68fa644
Revises: d52d50968cf7
Create Date: 2019-06-08 12:17:40.208947

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4581a68fa644'
down_revision = 'd52d50968cf7'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()


def upgrade_default():
    pass


def downgrade_default():
    pass


def upgrade_slow():
    op.create_table('submission_result',
        sa.Column('submission_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('application_version', sa.String(), nullable=True),
        sa.Column('fingerprint_id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('meta_id', sa.Integer(), nullable=True),
        sa.Column('mbid', postgresql.UUID(), nullable=True),
        sa.Column('puid', postgresql.UUID(), nullable=True),
        sa.Column('foreignid', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('submission_id', name=op.f('submission_result_pkey'))
    )


def downgrade_slow():
    op.drop_table('submission_result')
