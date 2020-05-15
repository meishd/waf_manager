import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from . import local_config
from .LogUtils import LogUtils

db = SQLAlchemy(session_options={'autocommit': True})
login_manager = LoginManager()

config_map = {
    'prod':'waf.local_config.Prod',
    'dev':'waf.local_config.Dev'
}

def create_app():
    app=Flask(__name__,instance_relative_config=True)
    config_map_name = os.getenv('FLASK_CONFIG')
    config_object_name = config_map[config_map_name]
    app.config.from_object(config_object_name)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db.init_app(app)
    LogUtils.init_app(app)

    from . import ipblacklist
    app.register_blueprint(ipblacklist.bp)
    app.add_url_rule('/',endpoint='ipblacklist.index')

    from . import rule
    app.register_blueprint(rule.bp)

    from . import ipwhite
    app.register_blueprint(ipwhite.bp)

    from . import auth
    app.register_blueprint(auth.bp)

    login_manager.init_app(app)

    return app