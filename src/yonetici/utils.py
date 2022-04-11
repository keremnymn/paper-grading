from flask import url_for, redirect
from flask_admin import AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        if current_user.is_authenticated and current_user.isadmin:
            return True
        else:
            return False
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('users.giris'))

class MyModelView(ModelView):
    def is_accessible(self):
        if current_user.is_authenticated and current_user.isadmin:
            return True
        else:
            return False
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('users.giris'))