from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField
from wtforms.validators import InputRequired
from wtforms.fields.html5 import IntegerField
from flask_babel import lazy_gettext as _l

class TahminFormu(FlaskForm):
    coktan_secmeli = IntegerField(_l("Çoktan Seçmeli Sayısı"), validators=[InputRequired(message="Lütfen bir sayı giriniz.")])
    dogru_yanlis = IntegerField(_l("Doğru Yanlış Sayısı"), validators=[InputRequired(message="Lütfen bir sayı giriniz.")])
    eslestirme = IntegerField(_l("Eşleştirme Sayısı"), validators=[InputRequired(message="Lütfen bir sayı giriniz.")])
    bosluk_doldurma = IntegerField(_l("Boşluk Doldurma Sayısı"), validators=[InputRequired(message="Lütfen bir sayı giriniz.")])
    kagit_sayisi = IntegerField(_l("Sınav, Kaç Kişilik?"), validators=[InputRequired(message="Lütfen bir sayı giriniz.")])
    kacsayfa = SelectField(_l('Sınav, Kaçar Sayfa?'), choices=[('1', _l('Birer')), ('2', _l('İkişer')), ('3', _l('Üçer')), ('4', _l('Dörder')), ('5', _l('Beşer')), ('6', _l('Altışar'))])
    submit=SubmitField(_l("Tahmin:"))