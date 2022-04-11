from flask import Blueprint
from src import db
from src import admin
# from flask_admin import AdminIndexView
# from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin
from src.models import *
from src.yonetici.utils import *
import os

yonetici = Blueprint('yonetici', __name__)

path = os.path.join(os.path.dirname(__file__))
path = path[:-8]
path = os.path.join(path, 'static')

admin.add_view(MyModelView(Hangiders, db.session))
admin.add_view(MyModelView(Ilke, db.session))
admin.add_view(MyModelView(Tag, db.session))
admin.add_view(MyModelView(Sinav_Vote, db.session))
admin.add_view(MyModelView(User, db.session))
admin.add_view(MyModelView(Yetenek, db.session))
admin.add_view(MyModelView(BireyselFatura, db.session))
admin.add_view(MyModelView(PaperGradingKullanimi, db.session))
admin.add_view(MyModelView(Sinav, db.session))
admin.add_view(MyModelView(Sinav_Kopya, db.session))
admin.add_view(MyModelView(Soru, db.session))
admin.add_view(MyModelView(Konu, db.session))
admin.add_view(MyModelView(Notification, db.session))
admin.add_view(MyModelView(Kazanim, db.session))
admin.add_view(MyModelView(Okunansinav, db.session))
admin.add_view(MyModelView(Ogrenci, db.session))
admin.add_view(MyModelView(Okunansoru, db.session))
admin.add_view(MyModelView(Logo, db.session))
admin.add_view(MyModelView(Sinif, db.session))
admin.add_view(FileAdmin(path, '/static/', name='static'))
