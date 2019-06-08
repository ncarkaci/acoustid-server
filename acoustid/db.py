from sqlalchemy.orm import sessionmaker
from acoustid.tables import metadata


Session = sessionmaker()


def get_bind_args(engines):
    binds = {}
    for table in metadata.sorted_tables:
        bind_key = table.info.get('bind_key', 'default')
        if bind_key != 'default':
            binds[table] = engines[bind_key]
    return {'bind': engines['default'], 'binds': binds}


def get_session_args(script):
    kwargs = {'twophase': script.config.databases.use_two_phase_commit}
    kwargs.update(get_bind_args(script.db_engines))
    return kwargs


class DatabaseContext(object):

    def __init__(self, script):
        self.session = Session(**get_session_args(script))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
