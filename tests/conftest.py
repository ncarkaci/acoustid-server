import os
import pytest
from acoustid.config import str_to_bool
from acoustid.tables import metadata
from acoustid.data.fingerprint import update_fingerprint_index
from tests.data import create_sample_data


RECREATE_DB = True


def get_tables_for_bind(metadata, bind_key):
    tables = []
    for table in metadata.sorted_tables:
        if table.info.get('bind_key', 'default') == bind_key:
            tables.append(table)
    return tables


def create_all(metadata, engines):
    for bind_key, engine in engines.items():
        tables = get_tables_for_bind(metadata, bind_key)
        with engine.connect() as conn:
            with conn.begin():
                metadata.create_all(bind=conn, tables=tables)


def drop_all(metadata, engines):
    for bind_key, engine in engines.items():
        tables = get_tables_for_bind(metadata, bind_key)
        with engine.connect() as conn:
            with conn.begin():
                metadata.drop_all(bind=conn, tables=tables)


def delete_from_all_tables(metadata, engines):
    for bind_key, engine in engines.items():
        tables = get_tables_for_bind(metadata, bind_key)
        with engine.connect() as conn:
            with conn.begin():
                for table in reversed(tables):
                    conn.execute(table.delete())


def delete_shutdown_file(config):
    if os.path.exists(config.website.shutdown_file_path):
        os.remove(config.website.shutdown_file_path)


def prepare_database(script):
    delete_from_all_tables(metadata, script.db_engines)
    with script.context() as ctx:
        create_sample_data(ctx)
        ctx.db.flush()
        update_fingerprint_index(ctx.db.connection(), ctx.index)
        ctx.db.commit()


@pytest.fixture(scope='session')
def config_path():
    return os.path.dirname(os.path.abspath(__file__)) + '/../acoustid-test.conf'


@pytest.fixture(scope='session')
def script_global(config_path):
    from acoustid.script import Script

    script = Script(config_path, tests=True)

    recreate_db = str_to_bool(os.environ.get('ACOUSTID_TEST_RECREATE', ''))
    if recreate_db:
        drop_all(metadata, script.db_engines)

    create_all(metadata, script.db_engines)
    prepare_database(script)

    yield script


@pytest.fixture(scope='session')
def server_global(script_global, config_path):
    from acoustid.server import make_application

    server = make_application(config_path, tests=True)

    delete_shutdown_file(server.config)

    yield server


@pytest.fixture(scope='session')
def web_app_global(script_global, config_path):
    from acoustid.web.app import make_application

    server = make_application(config_path, tests=True)

    delete_shutdown_file(server.acoustid_config)

    yield server


@pytest.fixture()
def server(server_global):
    yield server_global


@pytest.fixture()
def web_app(web_app_global):
    yield web_app_global


@pytest.fixture()
def cleanup(script_global):
    yield
    prepare_database(script_global)
