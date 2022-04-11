from flask import current_app
from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from src import db, login_manager
from sqlalchemy import event
from flask_login import UserMixin
from slugify import slugify
import json, string, random

def id_generator(size=5, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def generate_rand_id():
    rand_id = id_generator()
    while db.session.query(Sinav).filter(Sinav.uuid == rand_id).limit(1).first() is not None:
        rand_id = id_generator()
    return rand_id

def rapor_rand_id():
    rand_id = id_generator()
    while db.session.query(Rapor).filter(Rapor.uuid == rand_id).limit(1).first() is not None:
        rand_id = id_generator()
    return rand_id

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Yetenek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    lang = db.Column(db.String(4), default='tr')

    def __repr__(self):
        return f'<Yetenek id:{self.id}, ad:{self.name}'

user_yetenekler = db.Table('user_yetenekler', 
                            db.Column('user_id', db.Integer, 
                            db.ForeignKey('user.id')),
                            db.Column('yetenek_id', db.Integer, 
                            db.ForeignKey('yetenek.id'))
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    notifications = db.relationship('Notification', backref='kullanici',
                                lazy='dynamic')
    username = db.Column(db.String(40), nullable=False)
    image_file = db.Column(db.String(40), default='default.jpg')
    isadmin = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    bo_kullanimlar = db.relationship("PaperGradingKullanimi", backref="ogretmen", lazy=True, cascade="all, delete")
    yapilan_sinavlar = db.relationship("Okunansinav", backref="ogretmen", lazy=True, cascade="all, delete")
    fatura = db.relationship("BireyselFatura", backref="satin_alan", lazy=True)
    sinavlar = db.relationship("Sinav", backref="sinavi_hazirlayan", lazy=True)
    siniflar = db.relationship("Sinif", backref="olusturan", lazy=True)

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def __repr__(self):
        return f"User('{self.username}','{self.email}','{self.image_file}')"

class Basevote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)
    tip = db.Column(db.String(50))

    __mapper_args__ = {
        'polymorphic_identity':'basevote',
        'polymorphic_on':tip
    }
    def __repr__(self):
        return f"Tip('{self.tip}','{self.timestamp}','{self.id}')"

class Sinav_Vote(Basevote):
    id = db.Column(db.Integer, db.ForeignKey('basevote.id'), primary_key=True)
    sinav_id = db.Column(db.Integer, db.ForeignKey("sinav.id"))
    sinav = db.relationship('Sinav', backref='alkis', lazy=True)

    __mapper_args__ = {
        'polymorphic_identity':'sinav_vote',
    }

    def __repr__(self):
        return f"<ID: {self.id} User: {self.user_id}"

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    lang = db.Column(db.String(4), default='tr')
    kazanimlar = db.relationship("Kazanim", backref="seviye", lazy=True)

    def __repr__(self):
        return f'<Tag id:{self.id}, ad:{self.name}'
    
class Ilke(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    lang = db.Column(db.String(4), default='tr')

    def __repr__(self):
        return f'<İlke id:{self.id}, ad:{self.name}'

class Hangiders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    lang = db.Column(db.String(4), default='tr')
    paper_grading_kullanimi = db.relationship("PaperGradingKullanimi", backref="ders_adi", lazy=True)
    sinavlar = db.relationship("Sinav", backref="ders_adi", lazy=True)
    konular = db.relationship("Konu", backref="ders_adi", lazy=True)
    kazanimlar = db.relationship("Kazanim", backref="ders_adi", lazy=True)

    def __repr__(self):
        return f'{self.id} Ad: {self.name}'

## kredi sistemi
class Fatura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)
    tip = db.Column(db.String(50), default='bireysel_fatura')

    __mapper_args__ = {
        'polymorphic_identity':'fatura',
        'polymorphic_on':tip
    }

class BireyselFatura(Fatura):
    id = db.Column(db.Integer, db.ForeignKey('fatura.id'), primary_key=True)
    kalan_kredi = db.Column(db.Integer, default=20, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bitis_suresi = db.Column(db.Integer, default=12, nullable=False)
    etkin_mi = db.Column(db.Boolean, default=True)
    order_id = db.Column(db.String(120))
    promosyon_kredisi_mi = db.Column(db.Boolean, default=False)

    def kapat(self):
        self.etkin_mi=False

    __mapper_args__ = {
        'polymorphic_identity':'bireysel_fatura',
    }

    def __repr__(self):
        return f"Fatura Sahibi: {self.user_id}',Sure:'{self.bitis_suresi}')"

class PaperGradingKullanimi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kagit_sayisi = db.Column(db.Integer, nullable=False)
    hatali_kagit_sayisi = db.Column(db.Integer, default=0, nullable=False)
    coktan_secmeli_sayisi = db.Column(db.Integer)
    dogru_yanlis_sayisi = db.Column(db.Integer)
    eslestirme_sayisi = db.Column(db.Integer)
    bosluk_doldurma_sayisi = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)
    maliyet = db.Column(db.Integer)
    kredi_gideri = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hangi_ders = db.Column(db.Integer, db.ForeignKey('hangiders.id'), nullable=False)
    sinav_dili = db.Column(db.String(100), nullable=False)
    okunan_sinav_id = db.Column(db.Integer, db.ForeignKey('okunansinav.id'))
    okunan_sinav = db.relationship('Okunansinav', backref='kullanim')

    def __repr__(self):
        return f"Kullanım('{self.timestamp}','{self.kagit_sayisi}')"

sinav_tags = db.Table('sinav_tags', 
                            db.Column('sinav_id', db.Integer, 
                            db.ForeignKey('sinav.id')),
                            db.Column('tag_id', db.Integer, 
                            db.ForeignKey('tag.id'))
)

sinav_konular = db.Table('sinav_konular', 
                            db.Column('sinav_id', db.Integer, 
                            db.ForeignKey('sinav.id')),
                            db.Column('konu_id', db.Integer, 
                            db.ForeignKey('konu.id'))
)

class Sinav(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(5), default=generate_rand_id, unique=True)
    pdf_dosyasi = db.Column(db.String(30), nullable=False)
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)
    ozel_mi = db.Column(db.Boolean, default=False, nullable=False)
    baslik = db.Column(db.String(170), nullable=False)
    ust_yazi = db.Column(db.String(120))
    alt_yazi = db.Column(db.String(120))
    sayfa_duzeni = db.Column(db.String(20))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hangi_ders = db.Column(db.Integer, db.ForeignKey('hangiders.id'), nullable=False)
    logo_id = db.Column(db.Integer, db.ForeignKey('logo.id'))
    lang = db.Column(db.String(4), default='tr')
    sorular = db.relationship('Soru', backref='hangi_sinav', lazy=True, cascade="all, delete")
    tags = db.relationship('Tag', secondary=sinav_tags, backref='bu_tagi_kullanan_sinavlar', lazy='dynamic')
    konular = db.relationship('Konu', secondary=sinav_konular, backref='bu_konuyu_kullanan_sinavlar', lazy='dynamic')
    alkis_sayi = db.Column(db.Integer(), default=0)
    indirme_sayi = db.Column(db.Integer(), default=0)
    kopyalama_sayi = db.Column(db.Integer(), default=0)
    aciklama = db.Column(db.Text(120))

    def __repr__(self):
        return f"Sınav('{self.timestamp}','{self.baslik}')"

soru_kazanimlari = db.Table('soru_kazanimlari', 
                            db.Column('kazanim_id', db.Integer, 
                            db.ForeignKey('kazanim.id')),
                            db.Column('soru_id', db.Integer, 
                            db.ForeignKey('soru.id'))
)

class Soru(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tip = db.Column(db.String(100), nullable=False)
    sinav_id = db.Column(db.Integer, db.ForeignKey('sinav.id'))
    kazanimlar = db.relationship('Kazanim', secondary=soru_kazanimlari, backref='sorular', lazy='dynamic')

    raw_soru = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"Sınav('{self.tip}','{self.sinav_id}')"

class Kazanim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(270), nullable=False)
    lang = db.Column(db.String(4), default='tr')
    hangi_ders = db.Column(db.Integer, db.ForeignKey('hangiders.id'), nullable=False)
    tag = db.Column(db.Integer, db.ForeignKey('tag.id'), nullable=False)
    
    def __repr__(self):
        return f"Kazanım('{self.name}')"

class Konu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    lang = db.Column(db.String(4), default='tr')
    hangi_ders = db.Column(db.Integer, db.ForeignKey('hangiders.id'), nullable=False)
    sinav_id = db.Column(db.Integer, db.ForeignKey('sinav.id'))
    
    def __repr__(self):
        return f"Ad('{self.name}','{self.hangi_ders}')"

class Sinav_Kopya(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sinav_id = db.Column(db.Integer, db.ForeignKey("sinav.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    yeni_sinav_id = db.Column(db.Integer, nullable=False)

    sinav = db.relationship('Sinav', backref='kopyalayan', lazy=True)
    user = db.relationship('User', backref='kopyalanan_sinav', lazy=True)

    def __repr__(self):
        return f"<ID: {self.id} User: {self.user_id} Sınav: {self.sinav.id} >"

class Okunansinav(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(), index=True, default=datetime.utcnow)
    ad = db.Column(db.String(120))
    lang = db.Column(db.String(4), default='tr')
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    sinif_id = db.Column(db.Integer, db.ForeignKey("sinif.id"))
    kazanim_analizi = db.Column(db.Boolean())
    sistemdeki_karsiligi = db.Column(db.Integer, db.ForeignKey("sinav.id"))
    ogrenciler = db.relationship("Ogrenci", backref="sinav", lazy=True, cascade="all, delete")
    inferfiles = db.relationship("Inferfiles", backref="sinav", lazy=True, cascade="all, delete")
    raporlar = db.relationship("Sinavrapor", backref="sinav", lazy=True, cascade="all, delete")
    silindi_mi = db.Column(db.Boolean(), default=False)

    def __repr__(self):
        return f"<ID: {self.id} User: {self.user_id} Sınav: {self.sistemdeki_karsiligi} >"

class Ogrenci(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sinav_id = db.Column(db.Integer, db.ForeignKey("okunansinav.id"))
    gercek_ogrenci_id = db.Column(db.Integer, db.ForeignKey("gercekogrenci.id"))
    ad_soyad = db.Column(db.String(140), nullable=False)
    ad_soyad_gercek = db.Column(db.String(140))
    koordinat = db.Column(db.String(100))
    toplam_puan = db.Column(db.Integer, nullable=False)
    okunan_sorular = db.relationship("Okunansoru", backref="ogrenci", lazy=True, cascade="all, delete")
    raporlar = db.relationship("Ogrencirapor", backref="ogrenci", lazy=True, cascade="all, delete")
    
    def __repr__(self):
        return f"<ID: {self.id}>"

okunan_soru_kazanimlari = db.Table('okunan_soru_kazanimlari', 
                            db.Column('kazanim_id', db.Integer, 
                            db.ForeignKey('kazanim.id')),
                            db.Column('okunansoru_id', db.Integer, 
                            db.ForeignKey('okunansoru.id'))
)

class Okunansoru(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    soru_sirasi = db.Column(db.String(10), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey("ogrenci.id"), nullable=False)
    kazanimlar = db.relationship('Kazanim', secondary=okunan_soru_kazanimlari, backref='okunan_sinavlar', lazy='dynamic')
    tip = db.Column(db.String(100), nullable=False)
    koordinat = db.Column(db.String(100))
    puan = db.Column(db.Integer, nullable=False)
    beklenen_cevaplar = db.Column(db.String(270), nullable=False)
    ogrenci_cevaplari = db.Column(db.String(270), nullable=False)
    sonuc = db.Column(db.Boolean(), nullable=False)
    onizleme = db.Column(db.String(170), nullable=False)
    guven = db.Column(db.Float, nullable=False)
    
    def __repr__(self):
        return f"<ID: {self.id}, Tip: {self.tip}>"

class Inferfiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    sinav_id = db.Column(db.Integer, db.ForeignKey("okunansinav.id"))

    def __repr__(self):
        return f"<ID: {self.id}>"

class Sinif(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ogrenciler = db.relationship("Gercekogrenci", backref="sinif", lazy=True, cascade="all, delete")
    sinavlar = db.relationship("Okunansinav", backref="sinif", lazy=True)
    raporlar = db.relationship("Sinifrapor", backref="sinif", lazy=True, cascade="all, delete")
    
    def __repr__(self):
        return f"<Ad: {self.name}>"

class Gercekogrenci(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    numara = db.Column(db.String(20))
    sinif_id = db.Column(db.Integer, db.ForeignKey('sinif.id'), nullable=False)
    sinavlar = db.relationship("Ogrenci", backref="gercek_ogrenci", lazy=True)

    def __repr__(self):
        return f"<Ad: {self.name}>"

class Rapor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime(), default=datetime.utcnow)
    uuid = db.Column(db.String(5), default=rapor_rand_id, unique=True)
    # 'bekliyor', 'hazir' ya da 'hata' içerebilir.
    durum = db.Column(db.String(10), default='bekliyor')
    tur = db.Column(db.String(10), default='pdf')
    lang = db.Column(db.String(4), default='tr')
    tip = db.Column(db.String(50))

    __mapper_args__ = {
        'polymorphic_identity':'rapor',
        'polymorphic_on':tip
    }
    def __repr__(self):
        return f"Tip('{self.tip}','{self.timestamp}','{self.id}')"

class Ogrencirapor(Rapor):
    id = db.Column(db.Integer, db.ForeignKey('rapor.id'), primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenci.id'), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity':'ogrencirapor',
    }
    
    def __repr__(self):
        return f"<ID: {self.id} User: {self.ogrenci_id}"

class Sinifrapor(Rapor):
    id = db.Column(db.Integer, db.ForeignKey('rapor.id'), primary_key=True)
    sinif_id = db.Column(db.Integer, db.ForeignKey('sinif.id'), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity':'sinifrapor',
    }
    
    def __repr__(self):
        return f"<ID: {self.id} Sinif: {self.sinif_id}"

class Sinavrapor(Rapor):
    id = db.Column(db.Integer, db.ForeignKey('rapor.id'), primary_key=True)
    sinav_id = db.Column(db.Integer, db.ForeignKey('okunansinav.id'), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity':'sinavrapor',
    }
    
    def __repr__(self):
        return f"<ID: {self.id} Sinav: {self.sinav_id}"

class Logo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    okul_ad = db.Column(db.String(120), nullable=False)
    uri = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    sinavlar = db.relationship("Sinav", backref="logo", lazy=True)

    def __repr__(self):
        return f"<ID: {self.id}>"

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime(), index=True, default=datetime.utcnow)
    yeni_mi = db.Column(db.Boolean(), default=True)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))