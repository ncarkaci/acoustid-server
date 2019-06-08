import os
import datetime
import pickle
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask, request, session
from flask.sessions import SecureCookieSessionInterface
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import scoped_session
from acoustid.script import Script
from acoustid.db import get_session_args
from acoustid.web import db
from acoustid.web.views.general import general_page
from acoustid.web.views.user import user_page
from acoustid.web.views.apps import apps_page
from acoustid.web.views.metadata import metadata_page
from acoustid.web.views.stats import stats_page
from acoustid.web.views.admin import admin_page
from acoustid._release import GIT_RELEASE


def make_application(config_filename=None, tests=False):
    if config_filename is None:
        config_filename = os.environ.get('ACOUSTID_CONFIG')

    script = Script(config_filename, tests=tests)
    script.setup_logging()

    config = script.config

    app = Flask('acoustid.web')
    app.config.update(
        DEBUG=config.website.debug,
        SECRET_KEY=config.website.secret,
        MB_OAUTH_CLIENT_ID=config.website.mb_oauth_client_id,
        MB_OAUTH_CLIENT_SECRET=config.website.mb_oauth_client_secret,
        GOOGLE_OAUTH_CLIENT_ID=config.website.google_oauth_client_id,
        GOOGLE_OAUTH_CLIENT_SECRET=config.website.google_oauth_client_secret,
    )
    if tests:
        app.config['TESTING'] = True

    app.acoustid_script = script
    app.acoustid_config = config
    app.acoustid_config_filename = config_filename

    app.wsgi_app = ProxyFix(app.wsgi_app)

    sentry_sdk.init(
        config.sentry.web_dsn,
        release=GIT_RELEASE,
        integrations=[FlaskIntegration()]
    )

    # can't use json because of python-openid
    app.session_interface = SecureCookieSessionInterface()
    app.session_interface.serializer = pickle

    @app.context_processor
    def inject_common_values():
        show_donate_banner = False
        if datetime.date.today().month in (11, 12):
            show_donate_banner = True
        return dict(
            account_id=session.get('id'),
            show_maintenace_banner=config.website.maintenance,
            show_donate_banner=show_donate_banner,
            morris_js_version='0.5.1',
            raphael_js_version='2.1.4',
            bootstrap_version='3.3.6',
            jquery_version='1.12.0',
        )

    def get_flask_request_scope():
        try:
            return id(request._get_current_object())
        except RuntimeError:
            return 0

    @app.teardown_request
    def close_db_session(*args, **kwargs):
        db.session.remove()

    @app.route('/_health')
    def health():
        from acoustid.api import get_health_response
        return get_health_response(script, request, require_master=True)

    @app.route('/_health_docker')
    def health_docker():
        from acoustid.api import get_health_response
        return get_health_response(script, request)

    db.session_factory.configure(**get_session_args(script))
    db.session = scoped_session(db.session_factory, scopefunc=get_flask_request_scope)

    app.register_blueprint(general_page)
    app.register_blueprint(user_page)
    app.register_blueprint(apps_page)
    app.register_blueprint(metadata_page)
    app.register_blueprint(stats_page)
    app.register_blueprint(admin_page)

    return app


if __name__ == "__main__":
    import argparse
    from werkzeug.serving import run_simple
    from werkzeug.wsgi import DispatcherMiddleware
    from acoustid.server import make_application as make_api_application

    parser = argparse.ArgumentParser()
    parser.add_argument('--ssl', action='store_true')
    parser.add_argument('--ssl-crt')
    parser.add_argument('--ssl-key')
    parser.add_argument('--api', action='store_true')
    parser.add_argument('--host', '-H', default='127.0.0.1')
    parser.add_argument('--port', '-p', default=5000, type=int)
    args = parser.parse_args()

    app = make_application()
    app.debug = True

    app.acoustid_script.setup_console_logging()

    run_args = {
        'use_debugger': True,
        'use_reloader': True,
        'extra_files': [app.acoustid_config_filename],
    }

    if args.ssl:
        if args.ssl_crt and args.ssl_key:
            run_args['ssl_context'] = args.ssl_crt, args.ssl_key
        else:
            run_args['ssl_context'] = 'adhoc'

    if args.api:
        app = DispatcherMiddleware(app, {
            '/api': make_api_application(app.acoustid_config_filename)[1],
        })

    run_simple(args.host, args.port, app, **run_args)  # type: ignore
