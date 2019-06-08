"""move submissions

Revision ID: d52d50968cf7
Revises: ae7e1e5763ef
Create Date: 2019-06-08 11:04:53.563059

"""
import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence
from dateutil.relativedelta import relativedelta


# revision identifiers, used by Alembic.
revision = 'd52d50968cf7'
down_revision = 'ae7e1e5763ef'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()


def upgrade_default():
    op.rename_table('submission', 'submission_old')


def downgrade_default():
    op.rename_table('submission_old', 'submission')


def upgrade_slow():
    op.execute(CreateSequence(Sequence('submission_id_seq')))
    op.create_table('submission',
        sa.Column('id', sa.Integer(), server_default=sa.text("nextval('submission_id_seq')"), nullable=False),
        sa.Column('created', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('handled', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('application_version', sa.String(), nullable=True),
        sa.Column('fingerprint', postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=False),
        sa.Column('bitrate', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(), nullable=True),
        sa.Column('mbid', postgresql.UUID(), nullable=True),
        sa.Column('puid', postgresql.UUID(), nullable=True),
        sa.Column('foreignid', sa.String(), nullable=True),
        sa.Column('track', sa.String(), nullable=True),
        sa.Column('artist', sa.String(), nullable=True),
        sa.Column('album', sa.String(), nullable=True),
        sa.Column('album_artist', sa.String(), nullable=True),
        sa.Column('track_no', sa.Integer(), nullable=True),
        sa.Column('disc_no', sa.Integer(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        postgresql_partition_by='RANGE (created)',
    )

    one_month = relativedelta(months=1)
    partitions_from = datetime.date(2010, 1, 1)
    partitions_to = datetime.date.today().replace(month=1, day=1) + relativedelta(months=12)
    range_from = partitions_from
    while range_from < partitions_to:
        range_to = range_from + one_month
        op.execute("""

            CREATE TABLE IF NOT EXISTS submission_y{range_from.year:04d}m{range_to.month:02d}
                PARTITION OF submission
                FOR VALUES FROM ('{range_from}') TO ('{range_to}');

            ALTER TABLE submission_y{range_from.year:04d}m{range_to.month:02d}
                ADD PRIMARY KEY (id);

            CREATE INDEX submission_y{range_from.year:04d}m{range_to.month:02d}_idx_handled
                ON submission_y{range_from.year:04d}m{range_to.month:02d} (handled);

        """.format(range_from=range_from, range_to=range_to))
        range_from = range_to


def downgrade_slow():
    op.drop_table('submission')
    op.execute(DropSequence(Sequence('submission_id_seq')))
