from __future__ import with_statement
import os
import logging
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

import acoustid.tables
target_metadata = acoustid.tables.metadata

import acoustid.config
acoustid_config_filename = os.environ.get('ACOUSTID_CONFIG',
    os.path.join(os.path.dirname(__file__), '..', 'acoustid.conf'))
acoustid_config = acoustid.config.Config()
acoustid_config.read(acoustid_config_filename)
acoustid_config.read_env()

use_two_phase_commit = acoustid_config.databases.use_two_phase_commit


def include_object(db_name):
    def inner(obj, name, obj_type, reflected, compare_to):
        if obj_type == "table":
            if obj.schema == "musicbrainz":
                return False
            bind_key = obj.info.get('bind_key', 'default')
            if bind_key != db_name:
                return False
        if obj_type == "column":
            if obj.table.schema == "musicbrainz":
                return False
            bind_key = obj.table.info.get('bind_key', 'default')
            if bind_key != db_name:
                return False
        return True
    return inner


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    for name, db_config in acoustid_config.databases.databases.items():
        logger.info("Migrating database %s" % name)

        context.configure(
            url=db_config.create_url(),
            target_metadata=target_metadata,
            literal_binds=True,
            include_object=include_object(name),
        )

        with context.begin_transaction():
            context.run_migrations(engine_name=name)


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engines = {}
    for name, db_config in acoustid_config.databases.databases.items():
        engines[name] = rec = {}
        rec["engine"] = db_config.create_engine(poolclass=pool.NullPool)

    for name, rec in engines.items():
        engine = rec["engine"]
        rec["connection"] = conn = engine.connect()

        if use_two_phase_commit:
            rec["transaction"] = conn.begin_twophase()
        else:
            rec["transaction"] = conn.begin()

    try:
        for name, rec in engines.items():
            logger.info("Migrating database %s" % name)
            context.configure(
                connection=rec["connection"],
                upgrade_token="%s_upgrades" % name,
                downgrade_token="%s_downgrades" % name,
                target_metadata=target_metadata,
                include_object=include_object(name),
            )
            context.run_migrations(engine_name=name)

        if use_two_phase_commit:
            for rec in engines.values():
                rec["transaction"].prepare()

        for rec in engines.values():
            rec["transaction"].commit()
    except:
        for rec in engines.values():
            rec["transaction"].rollback()
        raise
    finally:
        for rec in engines.values():
            rec["connection"].close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
