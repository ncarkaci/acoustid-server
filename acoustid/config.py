# Copyright (C) 2011 Lukas Lalinsky
# Distributed under the MIT license, see the LICENSE file for details.

import os.path
import logging
from six.moves import configparser as ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

logger = logging.getLogger(__name__)


def str_to_bool(x):
    return x.lower() in ('1', 'on', 'true')


def read_env_item(obj, key, name, convert=None):
    value = None
    if name in os.environ:
        value = os.environ[name]
        logger.info('Reading config value from environment variable %s', name)
    elif name + '_FILE' in os.environ:
        value = open(os.environ[name + '_FILE']).read().strip()
        logger.info('Reading config value from environment variable %s', name + '_FILE')
    if value is not None:
        if convert is not None:
            value = convert(value)
        setattr(obj, key, value)


class BaseConfig(object):

    def read(self, parser, section):
        if parser.has_section(section):
            self.read_section(parser, section)

    def read_section(self, parser, section):
        pass

    def read_env(self, prefix):
        pass


class DatabasesConfig(BaseConfig):

    def __init__(self):
        self.databases = {
            'default': DatabaseConfig(),
            'slow': DatabaseConfig(),
        }
        self.use_two_phase_commit = False

    def create_engines(self, **kwargs):
        engines = {}
        for name, db_config in self.databases.items():
            engines[name] = db_config.create_engine(**kwargs)
        return engines

    def read_section(self, parser, section):
        if parser.has_option(section, 'two_phase_commit'):
            self.use_two_phase_commit = parser.getboolean(section, 'two_phase_commit')
        for name, sub_config in self.databases.items():
            sub_section = '{}:{}'.format(section, name)
            sub_config.read_section(parser, sub_section)

    def read_env(self, prefix):
        read_env_item(self, 'use_two_phase_commit', prefix + 'TWO_PHASE_COMMIT', convert=str_to_bool)
        for name, sub_config in self.databases.items():
            sub_prefix = prefix + name.upper() + '_'
            sub_config.read_env(sub_prefix)


class DatabaseConfig(BaseConfig):

    def __init__(self):
        self.user = None
        self.superuser = 'postgres'
        self.name = None
        self.host = None
        self.port = None
        self.password = None
        self.pool_size = None
        self.pool_recycle = None
        self.pool_pre_ping = None

    def create_url(self, superuser=False):
        kwargs = {}
        if superuser:
            kwargs['username'] = self.superuser
        else:
            kwargs['username'] = self.user
        kwargs['database'] = self.name
        if self.host is not None:
            kwargs['host'] = self.host
        if self.port is not None:
            kwargs['port'] = self.port
        if self.password is not None:
            kwargs['password'] = self.password
        return URL('postgresql', **kwargs)

    def create_engine(self, superuser=False, **kwargs):
        if self.pool_size is not None and 'pool_size' not in kwargs:
            kwargs['pool_size'] = self.pool_size
        if self.pool_recycle is not None and 'pool_recycle' not in kwargs:
            kwargs['pool_recycle'] = self.pool_recycle
        if self.pool_pre_ping is not None and 'pool_pre_ping' not in kwargs:
            kwargs['pool_pre_ping'] = self.pool_pre_ping
        return create_engine(self.create_url(superuser=superuser), **kwargs)

    def create_psql_args(self, superuser=False):
        args = []
        if superuser:
            args.append('-U')
            args.append(self.superuser)
        else:
            args.append('-U')
            args.append(self.user)
        if self.host is not None:
            args.append('-h')
            args.append(self.host)
        if self.port is not None:
            args.append('-p')
            args.append(str(self.port))
        args.append(self.name)
        return args

    def read_section(self, parser, section):
        self.user = parser.get(section, 'user')
        self.name = parser.get(section, 'name')
        if parser.has_option(section, 'host'):
            self.host = parser.get(section, 'host')
        if parser.has_option(section, 'port'):
            self.port = parser.getint(section, 'port')
        if parser.has_option(section, 'password'):
            self.password = parser.get(section, 'password')
        if parser.has_option(section, 'pool_size'):
            self.pool_size = parser.getint(section, 'pool_size')
        if parser.has_option(section, 'pool_recycle'):
            self.pool_recycle = parser.getint(section, 'pool_recycle')
        if parser.has_option(section, 'pool_pre_ping'):
            self.pool_pre_ping = parser.getboolean(section, 'pool_pre_ping')

    def read_env(self, prefix):
        read_env_item(self, 'name', prefix + 'NAME')
        read_env_item(self, 'host', prefix + 'HOST')
        read_env_item(self, 'port', prefix + 'PORT', convert=int)
        read_env_item(self, 'user', prefix + 'USER')
        read_env_item(self, 'password', prefix + 'PASSWORD')
        read_env_item(self, 'pool_size', prefix + 'POOL_SIZE', convert=int)
        read_env_item(self, 'pool_recycle', prefix + 'POOL_RECYCLE', convert=int)
        read_env_item(self, 'pool_pre_ping', prefix + 'POOL_PRE_PING', convert=str_to_bool)


class IndexConfig(BaseConfig):

    def __init__(self):
        self.host = '127.0.0.1'
        self.port = 6080

    def read_section(self, parser, section):
        if parser.has_option(section, 'host'):
            self.host = parser.get(section, 'host')
        if parser.has_option(section, 'port'):
            self.port = parser.getint(section, 'port')

    def read_env(self, prefix):
        read_env_item(self, 'host', prefix + 'INDEX_HOST')
        read_env_item(self, 'port', prefix + 'INDEX_PORT', convert=int)


class RedisConfig(BaseConfig):

    def __init__(self):
        self.host = '127.0.0.1'
        self.port = 6379

    def read_section(self, parser, section):
        if parser.has_option(section, 'host'):
            self.host = parser.get(section, 'host')
        if parser.has_option(section, 'port'):
            self.port = parser.getint(section, 'port')

    def read_env(self, prefix):
        read_env_item(self, 'host', prefix + 'REDIS_HOST')
        read_env_item(self, 'port', prefix + 'REDIS_PORT', convert=int)


def get_logging_level_names():
    try:
        return logging._levelNames
    except AttributeError:
        level_names = {}
        for value, name in logging._levelToName.items():
            level_names[name] = value
        return level_names


class LoggingConfig(BaseConfig):

    def __init__(self):
        self.levels = {}
        self.syslog = False
        self.syslog_facility = None

    def read_section(self, parser, section):
        level_names = get_logging_level_names()
        for name in parser.options(section):
            if name == 'level':
                self.levels[''] = level_names[parser.get(section, name)]
            elif name.startswith('level.'):
                self.levels[name.split('.', 1)[1]] = level_names[parser.get(section, name)]
        if parser.has_option(section, 'syslog'):
            self.syslog = parser.getboolean(section, 'syslog')
        if parser.has_option(section, 'syslog_facility'):
            self.syslog_facility = parser.get(section, 'syslog_facility')

    def read_env(self, prefix):
        pass  # XXX


class WebSiteConfig(BaseConfig):

    def __init__(self):
        self.debug = False
        self.secret = None
        self.mb_oauth_client_id = None
        self.mb_oauth_client_secret = None
        self.google_oauth_client_id = None
        self.google_oauth_client_secret = None
        self.maintenance = False
        self.shutdown_delay = 0
        self.shutdown_file_path = '/tmp/acoustid-server-shutdown.txt'

    def read_section(self, parser, section):
        if parser.has_option(section, 'debug'):
            self.debug = parser.getboolean(section, 'debug')
        self.secret = parser.get(section, 'secret')
        if parser.has_option(section, 'mb_oauth_client_id'):
            self.mb_oauth_client_id = parser.get(section, 'mb_oauth_client_id')
        if parser.has_option(section, 'mb_oauth_client_secret'):
            self.mb_oauth_client_secret = parser.get(section, 'mb_oauth_client_secret')
        if parser.has_option(section, 'google_oauth_client_id'):
            self.google_oauth_client_id = parser.get(section, 'google_oauth_client_id')
        if parser.has_option(section, 'google_oauth_client_secret'):
            self.google_oauth_client_secret = parser.get(section, 'google_oauth_client_secret')
        if parser.has_option(section, 'maintenance'):
            self.maintenance = parser.getboolean(section, 'maintenance')
        if parser.has_option(section, 'shutdown_delay'):
            self.shutdown_delay = parser.getint(section, 'shutdown_delay')

    def read_env(self, prefix):
        read_env_item(self, 'debug', prefix + 'DEBUG', convert=str_to_bool)
        read_env_item(self, 'maintenance', prefix + 'MAINTENANCE', convert=str_to_bool)
        read_env_item(self, 'mb_oauth_client_id', prefix + 'MB_OAUTH_CLIENT_ID')
        read_env_item(self, 'mb_oauth_client_secret', prefix + 'MB_OAUTH_CLIENT_SECRET')
        read_env_item(self, 'google_oauth_client_id', prefix + 'GOOGLE_OAUTH_CLIENT_ID')
        read_env_item(self, 'google_oauth_client_secret', prefix + 'GOOGLE_OAUTH_CLIENT_SECRET')
        read_env_item(self, 'shutdown_delay', prefix + 'SHUTDOWN_DELAY', convert=int)


class uWSGIConfig(BaseConfig):

    def __init__(self):
        self.harakiri = 120
        self.http_timeout = 90
        self.http_connect_timeout = 10
        self.workers = 2
        self.post_buffering = 0
        self.buffer_size = 10240
        self.offload_threads = 1

    def read_section(self, parser, section):
        if parser.has_option(section, 'harakiri'):
            self.harakiri = parser.getint(section, 'harakiri')
        if parser.has_option(section, 'http_timeout'):
            self.http_timeout = parser.getint(section, 'http_timeout')
        if parser.has_option(section, 'http_connect_timeout'):
            self.http_connect_timeout = parser.getint(section, 'http_connect_timeout')
        if parser.has_option(section, 'workers'):
            self.workers = parser.getint(section, 'workers')
        if parser.has_option(section, 'post_buffering'):
            self.post_buffering = parser.getint(section, 'post_buffering')
        if parser.has_option(section, 'buffer_size'):
            self.buffer_size = parser.getint(section, 'buffer_size')
        if parser.has_option(section, 'offload_threads'):
            self.offload_threads = parser.getint(section, 'offload_threads')

    def read_env(self, prefix):
        read_env_item(self, 'harakiri', prefix + 'UWSGI_HARAKIRI', convert=int)
        read_env_item(self, 'http_timeout', prefix + 'UWSGI_HTTP_TIMEOUT', convert=int)
        read_env_item(self, 'http_connect_timeout', prefix + 'UWSGI_CONNECT_TIMEOUT', convert=int)
        read_env_item(self, 'workers', prefix + 'UWSGI_WORKERS', convert=int)
        read_env_item(self, 'post_buffering', prefix + 'UWSGI_POST_BUFFERING', convert=int)
        read_env_item(self, 'buffer_size', prefix + 'UWSGI_BUFFER_SIZE', convert=int)
        read_env_item(self, 'offload_threads', prefix + 'UWSGI_OFFLOAD_THREADS', convert=int)


class SentryConfig(BaseConfig):

    def __init__(self):
        self.web_dsn = ''
        self.api_dsn = ''
        self.script_dsn = ''

    def read_section(self, parser, section):
        if parser.has_option(section, 'web_dsn'):
            self.web_dsn = parser.get(section, 'web_dsn')
        if parser.has_option(section, 'api_dsn'):
            self.api_dsn = parser.get(section, 'api_dsn')
        if parser.has_option(section, 'script_dsn'):
            self.script_dsn = parser.get(section, 'script_dsn')

    def read_env(self, prefix):
        read_env_item(self, 'web_dsn', prefix + 'SENTRY_WEB_DSN')
        read_env_item(self, 'api_dsn', prefix + 'SENTRY_API_DSN')
        read_env_item(self, 'script_dsn', prefix + 'SENTRY_SCRIPT_DSN')


class ReplicationConfig(BaseConfig):

    def __init__(self):
        self.import_acoustid = None
        self.import_acoustid_musicbrainz = None

    def read_section(self, parser, section):
        if parser.has_option(section, 'import_acoustid'):
            self.import_acoustid = parser.get(section, 'import_acoustid')
        if parser.has_option(section, 'import_acoustid_musicbrainz'):
            self.import_acoustid_musicbrainz = parser.get(section, 'import_acoustid_musicbrainz')

    def read_env(self, prefix):
        pass  # XXX


class ClusterConfig(BaseConfig):

    def __init__(self):
        self.role = 'master'
        self.base_master_url = None
        self.secret = None

    def read_section(self, parser, section):
        if parser.has_option(section, 'role'):
            self.role = parser.get(section, 'role')
        if parser.has_option(section, 'base_master_url'):
            self.base_master_url = parser.get(section, 'base_master_url')
        if parser.has_option(section, 'secret'):
            self.secret = parser.get(section, 'secret')

    def read_env(self, prefix):
        read_env_item(self, 'role', prefix + 'CLUSTER_ROLE')
        read_env_item(self, 'base_master_url', prefix + 'CLUSTER_BASE_MASTER_URL')
        read_env_item(self, 'secret', prefix + 'CLUSTER_SECRET')


class RateLimiterConfig(BaseConfig):

    def __init__(self):
        self.ips = {}
        self.applications = {}

    def read_section(self, parser, section):
        for name in parser.options(section):
            if name.startswith('ip.'):
                self.ips[name.split('.', 1)[1]] = parser.getfloat(section, name)
            elif name.startswith('application.'):
                self.applications[int(name.split('.', 1)[1])] = parser.getfloat(section, name)

    def read_env(self, prefix):
        pass  # XXX


class Config(object):

    def __init__(self):
        self.databases = DatabasesConfig()
        self.logging = LoggingConfig()
        self.website = WebSiteConfig()
        self.index = IndexConfig()
        self.redis = RedisConfig()
        self.replication = ReplicationConfig()
        self.cluster = ClusterConfig()
        self.rate_limiter = RateLimiterConfig()
        self.sentry = SentryConfig()
        self.uwsgi = uWSGIConfig()

    def read(self, path):
        logger.info("Loading configuration file %s", path)
        parser = ConfigParser.RawConfigParser()
        parser.read(path)
        self.databases.read(parser, 'database')
        self.logging.read(parser, 'logging')
        self.website.read(parser, 'website')
        self.index.read(parser, 'index')
        self.redis.read(parser, 'redis')
        self.replication.read(parser, 'replication')
        self.cluster.read(parser, 'cluster')
        self.rate_limiter.read(parser, 'rate_limiter')
        self.sentry.read(parser, 'sentry')
        self.uwsgi.read(parser, 'uwsgi')

    def read_env(self, tests=False):
        if tests:
            prefix = 'ACOUSTID_TEST_'
        else:
            prefix = 'ACOUSTID_'
        self.databases.read_env(prefix + 'DB_')
        self.logging.read_env(prefix)
        self.website.read_env(prefix)
        self.index.read_env(prefix)
        self.redis.read_env(prefix)
        self.replication.read_env(prefix)
        self.cluster.read_env(prefix)
        self.rate_limiter.read_env(prefix)
        self.sentry.read_env(prefix)
        self.uwsgi.read_env(prefix)
