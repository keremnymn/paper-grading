from flask import Blueprint, render_template
from flask_babel import lazy_gettext as _l

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(404)
def error_404(error):
    kod = '404'
    return render_template('errors/404.html', baslik=_l('Hata') + kod), 404

@errors.app_errorhandler(403)
def error_403(error):
    kod = '403'
    return render_template('errors/403.html', baslik=_l('Hata') + kod), 403

@errors.app_errorhandler(500)
def error_500(error):
    kod = '500'
    return render_template('errors/500.html', baslik=_l('Hata') + kod), 500

@errors.app_errorhandler(413)
def error_413(error):
    kod = '413'
    return render_template('errors/413.html', baslik=_l('Hata') + kod), 413