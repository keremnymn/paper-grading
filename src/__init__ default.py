from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from src.config import Config
from flask_migrate import Migrate
from flask_admin import Admin
from authlib.integrations.flask_client import OAuth
from src.yonetici.utils import MyAdminIndexView
from celery import Celery
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import MetaData
from flask_babel import Babel, lazy_gettext as _l

celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

migrate = Migrate(compare_type=True)
# db = SQLAlchemy(metadata=metadata)
db = SQLAlchemy()
oauth = OAuth()
admin = Admin(index_view=MyAdminIndexView())
bcrypt = Bcrypt()
csrf = CSRFProtect()
babel = Babel()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)
    admin.init_app(app)
    celery.conf.update(app.config)
    csrf.init_app(app)
    babel.init_app(app)
    
    from src.paper_grading.routes import paper_grading
    from src.main.routes import main
    from src.errors.handlers import errors
    from src.kredi.routes import kredi
    from src.rapor.routes import rapor
    from src.yonetici.routes import yonetici

    app.register_blueprint(yonetici)
    app.register_blueprint(main)
    app.register_blueprint(paper_grading)
    app.register_blueprint(errors)
    app.register_blueprint(kredi)
    app.register_blueprint(rapor)

    @app.context_processor
    def inject_template_scope():
        injections = dict()

        def cookies_check():
            value = request.cookies.get('cookie_consent')
            return value == 'true'
        injections.update(cookies_check=cookies_check)

        return injections
    return app

@babel.localeselector
def get_locale():
    return 'en'