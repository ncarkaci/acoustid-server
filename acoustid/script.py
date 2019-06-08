# Copyright (C) 2011 Lukas Lalinsky
# Distributed under the MIT license, see the LICENSE file for details.

import sys
import logging
import sqlalchemy
import sqlalchemy.pool
import sentry_sdk
from redis import Redis
from optparse import OptionParser
from acoustid.config import Config
from acoustid.indexclient import IndexClientPool
from acoustid.utils import LocalSysLogHandler
from acoustid.db import DatabaseContext
from acoustid._release import GIT_RELEASE

logger = logging.getLogger(__name__)


class ScriptContext(object):

    def __init__(self, db, redis, index):
        self.db = db
        self.redis = redis
        self.index = index

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()


class Script(object):

    def __init__(self, config_path, tests=False):
        self.config = Config()
        if config_path:
            self.config.read(config_path)
        self.config.read_env(tests=tests)

        create_engine_kwargs = {'poolclass': sqlalchemy.pool.AssertionPool} if tests else {}
        self.db_engines = self.config.databases.create_engines(**create_engine_kwargs)

        if not self.config.index.host:
            self.index = None
        else:
            self.index = IndexClientPool(host=self.config.index.host,
                                         port=self.config.index.port,
                                         recycle=60)

        if not self.config.redis.host:
            self.redis = None
        else:
            self.redis = Redis(host=self.config.redis.host,
                               port=self.config.redis.port)

        self._console_logging_configured = False
        self.setup_logging()

    @property
    def engine(self):
        return self.db_engines['default']

    def setup_logging(self):
        for logger_name, level in sorted(self.config.logging.levels.items()):
            logging.getLogger(logger_name).setLevel(level)
        if self.config.logging.syslog:
            handler = LocalSysLogHandler(ident='acoustid',
                facility=self.config.logging.syslog_facility, log_pid=True)
            handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
            logging.getLogger().addHandler(handler)
        else:
            self.setup_console_logging()

    def setup_console_logging(self, quiet=False):
        if self._console_logging_configured:
            return
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s - %(message)s', '%H:%M:%S'))
        if quiet:
            handler.setLevel(logging.ERROR)
        logging.getLogger().addHandler(handler)
        self._console_logging_configured = True

    def setup_sentry(self):
        sentry_sdk.init(self.config.sentry.script_dsn, release=GIT_RELEASE)

    def context(self):
        db = DatabaseContext(self).session
        return ScriptContext(db=db, redis=self.redis, index=self.index)


def run_script(func, option_cb=None, master_only=False):
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="config",
        help="configuration file", metavar="FILE")
    parser.add_option("-q", "--quiet", dest="quiet", action="store_true",
        default=False, help="don't print info messages to stdout")
    if option_cb is not None:
        option_cb(parser)
    (options, args) = parser.parse_args()
    if not options.config:
        parser.error('no configuration file')
    script = Script(options.config)
    script.setup_console_logging(options.quiet)
    script.setup_sentry()
    if master_only and script.config.cluster.role != 'master':
        logger.debug("Not running script %s on a slave server", sys.argv[0])
    else:
        logger.debug("Running script %s", sys.argv[0])
        try:
            func(script, options, args)
        except Exception:
            logger.exception("Script finished %s with an exception", sys.argv[0])
            raise
        else:
            logger.debug("Script finished %s successfuly", sys.argv[0])
    script.engine.dispose()
    script.index.dispose()
