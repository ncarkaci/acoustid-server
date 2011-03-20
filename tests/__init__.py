# Copyright (C) 2011 Lukas Lalinsky
# Distributed under the MIT license, see the LICENSE file for details. 

import os
import sqlalchemy
import sqlalchemy.pool
from nose.tools import make_decorator
from acoustid.config import Config

config = None
engine = None

def setup():
    global config, engine
    config_path = os.path.dirname(os.path.abspath(__file__)) + '/../acoustid.conf'
    config = Config(config_path)
    engine = sqlalchemy.create_engine(config.database.create_url(),
        poolclass=sqlalchemy.pool.AssertionPool)


TABLES = [
    'track',
    'track_mbid',
    'musicbrainz.artist',
    'musicbrainz.gid_redirect',
    'musicbrainz.track'
]

SEQUENCES = [
    ('track', 'id'),
]

def prepare_database(conn, sql):
    with conn.begin():
        for table in TABLES:
            conn.execute("TRUNCATE %s CASCADE" % (table,))
        conn.execute(sql)
        for table, column in SEQUENCES:
            conn.execute("""
                SELECT setval('%(table)s_%(column)s_seq',
                    (SELECT max(%(column)s) FROM %(table)s))
            """ % {'table': table, 'column': column})


def with_database(func):
    def wrapper(*args, **kwargs):
        conn = engine.connect()
        try:
            func(conn, *args, **kwargs)
        finally:
            conn.close()
    wrapper = make_decorator(func)(wrapper)
    return wrapper
