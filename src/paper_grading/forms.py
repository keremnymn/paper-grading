from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, \
BooleanField, FieldList, FormField, StringField, SelectField, \
MultipleFileField, RadioField, TextAreaField
from wtforms.validators import DataRequired, Optional, Length, Email, NumberRange, InputRequired
from wtforms.fields.html5 import IntegerField
from flask_babel import lazy_gettext as _l

class DenemeFormu(FlaskForm):
    pictures=MultipleFileField(_l('Sınav kâğıtlarını düzenli bir şekilde seçip yükleyiniz.'), validators=[DataRequired(message='Lütfen Sınav Kâğıtlarını Seçiniz')])
    kacsayfa=SelectField(_l('Sınav, Kaçar Sayfadan Oluşuyor?'), choices=[('1', _l('Birer')), ('2', _l('İkişer')), ('3', _l('Üçer')), ('4', _l('Dörder')), ('5', _l('Beşer')), ('6', _l('Altışar'))])
    dil=RadioField(_l('Sınav Dili'), choices=[('tr',_l('Türkçe')),('en',_l('İngilizce')), ('de', _l('Almanca'))])
    ders=SelectField(_l('Sınav, Hangi Derse Ait?'))
    kod=StringField(_l('Sınav Kodu'), validators=[Optional()])
    kosullar=BooleanField(_l('Paper Grading Kullanım Koşullarını Kabul Ediyorum'), validators=[InputRequired()])
    sablon=BooleanField(_l('Sınavı Paper Grading Şablonuna Göre Hazırladım'), validators=[InputRequired()])
    submit=SubmitField(_l("Yükle ve devam et"))

class FormingFor(FlaskForm):
    soru = StringField(_l("Beklenen Yanıt"), validators=[DataRequired()])
    deger = IntegerField(_l("Soru Değeri"), validators=[DataRequired(message="Lütfen bir sayı giriniz."),NumberRange(min=0, max=50)])

class MyForm(FlaskForm):
    sorular = FieldList(FormField(FormingFor))