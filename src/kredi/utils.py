from flask import abort, current_app, session, json
from flask_login import current_user
from src import db
from src.models import User, BireyselFatura, \
                              PaperGradingKullanimi, Hangiders,\
                              Tag, Konu
from src.paper_grading.utils import kagit_temizle
import os, ast, boto3, hashlib
from datetime import datetime
import xml.etree.cElementTree as ET

s3_client = boto3.client('s3', aws_access_key_id=os.environ['S3_ACCESS_KEY'],\
                  aws_secret_access_key=os.environ['S3_SECRET_KEY'], \
                  region_name=os.environ['S3_REGION'])

def hesap(kagit_sayisi, kagit_yuzu, bosluk_doldurma, cs_sayisi, dy_sayisi, e_sayisi):
  bir_dolar = 8.40
  her_binde_maliyet = (1.5 * bir_dolar) / 1000
  bir_bosluk_doldurma_katsayisi = her_binde_maliyet * 2

  ad_soyad_sayisi = kagit_sayisi/kagit_yuzu
  ad_soyad_maliyeti = ad_soyad_sayisi * her_binde_maliyet

  bir_coktan_secmeli_katsayisi = 0.004
  bir_dogru_yanlis_katsayisi = 0.0007
  bir_eslestirme_katsayisi = 0.003

  cs_gider = (kagit_sayisi * cs_sayisi) * bir_coktan_secmeli_katsayisi

  dy_gider = (kagit_sayisi * dy_sayisi) * bir_dogru_yanlis_katsayisi

  e_gider = (kagit_sayisi * e_sayisi) * bir_eslestirme_katsayisi

  bd_sayisi = bosluk_doldurma
  bd_gider = (kagit_sayisi * bd_sayisi) * bir_bosluk_doldurma_katsayisi

  toplam_gider = cs_gider + dy_gider + e_gider + bd_gider + ad_soyad_maliyeti

  maliyet = toplam_gider
  if kagit_sayisi < 501:
    gelir = (maliyet * 1.12) + (kagit_sayisi * 0.06)
  elif kagit_sayisi >= 501 and kagit_sayisi < 1001:
    gelir = (maliyet * 1.12) + (kagit_sayisi * 0.08)
  elif kagit_sayisi > 1000:
    gelir = (maliyet * 1.12) + (kagit_sayisi * 0.12)

  #gelir *= 10
  gelir = max(maliyet, (gelir + 1))
  print('gelir: ', gelir)
  print('maliyet: ', bd_gider)
  return int(round(maliyet)), round(gelir)

def diff_days(d1, d2):
  return (d1 - d2).days

def bireysel_kredi_hesapla(user):
    faturalar = db.session.query(BireyselFatura)\
                .filter(BireyselFatura.user_id == user.id)\
                .filter(BireyselFatura.etkin_mi)\
                .order_by(BireyselFatura.timestamp.asc()).all()
    kredi = 0
    for fatura in faturalar:
      if diff_days(datetime.utcnow(), fatura.timestamp) > fatura.bitis_suresi * 30:
          fatura.kapat()
          db.session.commit()
      elif fatura.etkin_mi:
        kredi += fatura.kalan_kredi
      else:
        kredi = 0
    return kredi

def kredi_hesapla(user):
  kredi = bireysel_kredi_hesapla(user)
  return kredi

def promosyon_kredisi_ekle(user):
    faturalar = db.session.query(BireyselFatura)\
              .filter(BireyselFatura.user_id == user.id)\
              .order_by(BireyselFatura.timestamp.asc()).all()
    if faturalar:
      return abort(500)
    else:
      fatura = BireyselFatura(kalan_kredi=200,
                              user_id = user.id,
                              bitis_suresi=1,
                              etkin_mi=True,
                              promosyon_kredisi_mi=True)
      db.session.add(fatura)
      db.session.commit()
      return '', 200

def kullanim_dus(user, kredi):
  faturalar = db.session.query(BireyselFatura)\
        .filter(BireyselFatura.user_id == user.id)\
        .filter(BireyselFatura.etkin_mi)\
        .order_by(BireyselFatura.timestamp.asc()).all()

  for x in faturalar:
      if kredi >= x.kalan_kredi:
          kredi -= x.kalan_kredi
          x.kalan_kredi = 0
      elif kredi != 0 and kredi < x.kalan_kredi:
          x.kalan_kredi -= kredi
          kredi = 0
  return '', 200

def paper_grading_kullanim_bildir(path, okunan_sinav, user_id, magic_num, dil, brans_id):
  if dil == 'tr':
      dil = 'Türkçe'
  else:
      dil = 'İngilizce'
  
  coktan_secmeli_sayisi = 0
  dogru_yanlis_sayisi = 0
  eslestirme_sayisi = 0
  bosluk_doldurma_sayisi = 0

  hatali_kagitlar = []

  if magic_num == 0:
    for dosya in os.listdir(path):
      if dosya.endswith('.txt') and not 'siraya_alindi' in dosya:
        with open(os.path.join(path, dosya), 'r') as f:
          f = f.read()
          j = ast.literal_eval(f)
        if 'Hata' in j['Sorular']:
          hatali_kagitlar.append(j['Kağıt Adı'])
        else:
          for x, y in j['Sorular'].items():
            if 'Ad Soyad' in y:
                pass
            elif y['Soru Tipi'] == 'Çoktan Seçmeli':
              coktan_secmeli_sayisi += 1
            elif y['Soru Tipi'] == 'Doğru Yanlış':
              dogru_yanlis_sayisi += 1
            elif y['Soru Tipi'] == 'Eşleştirme':
              eslestirme_sayisi += 1
            else:
              bosluk_doldurma_sayisi += 1
  else:
    for dosya in os.listdir(path):
      if dosya.startswith('Kağıt') and dosya.endswith('_updated.txt') and not 'siraya_alindi' in dosya:
        with open(os.path.join(path, dosya), 'r') as f:
          f = f.read()
          j = ast.literal_eval(f)
        if 'Hata' in j['Sorular']:
          hatali_kagitlar.append(j['Kağıt Adı'])
        else:
          for x, y in j['Sorular'].items():
            if 'Ad Soyad' in y:
                pass
            elif y['Soru Tipi'] == 'Çoktan Seçmeli':
              coktan_secmeli_sayisi += 1
            elif y['Soru Tipi'] == 'Doğru Yanlış':
              dogru_yanlis_sayisi += 1
            elif y['Soru Tipi'] == 'Eşleştirme':
              eslestirme_sayisi += 1
            else:
              bosluk_doldurma_sayisi += 1
  
  toplam_kagit = 0
  for kagit in os.listdir(path):
    if kagit.startswith('Kağıt') and kagit.endswith('.png'):
      toplam_kagit += 1
  
  toplam_kagit -= len(hatali_kagitlar)

  kullanan = User.query.filter_by(id=user_id).first_or_404()
  
  kagit_yuzu = magic_num + 1

  bir_kagittaki_bd_sayisi = bosluk_doldurma_sayisi / toplam_kagit
  bir_kagittaki_cs_sayisi = coktan_secmeli_sayisi / toplam_kagit
  bir_kagittaki_dy_sayisi = dogru_yanlis_sayisi / toplam_kagit
  bir_kagittaki_e_sayisi = eslestirme_sayisi / toplam_kagit

  maliyet, gelir = hesap(toplam_kagit, kagit_yuzu, bir_kagittaki_bd_sayisi,\
                        bir_kagittaki_cs_sayisi, bir_kagittaki_dy_sayisi,\
                        bir_kagittaki_e_sayisi)

  ders = Hangiders.query.filter_by(id=brans_id).first()

  istatistik = PaperGradingKullanimi(kagit_sayisi=toplam_kagit,
                                  coktan_secmeli_sayisi=coktan_secmeli_sayisi,
                                  dogru_yanlis_sayisi=dogru_yanlis_sayisi,
                                  eslestirme_sayisi=eslestirme_sayisi,
                                  bosluk_doldurma_sayisi=bosluk_doldurma_sayisi,
                                  maliyet=maliyet,
                                  kredi_gideri=gelir,
                                  user_id=kullanan.id,
                                  okunan_sinav=okunan_sinav,
                                  hatali_kagit_sayisi=len(hatali_kagitlar),
                                  hangi_ders=ders.id,
                                  sinav_dili=dil)
  db.session.add(istatistik)

  if len(hatali_kagitlar) != 0:
    for hatali_kagit in os.listdir(path):
      if hatali_kagit in hatali_kagitlar:
        hatali_kagit = os.path.join(path, hatali_kagit)
        hatali_kagit_adi = 'hatali_kagitlar/' + \
                          str(kullanan.id) +\
                          f'-{kullanan.username}-'+\
                          os.path.basename(hatali_kagit)
        s3_client.upload_file(hatali_kagit, os.environ['S3_NAME'],
                              hatali_kagit_adi, 
                              ExtraArgs={
                                        "ContentType": 'image/png'
                                        }
                                      )

  kagit_temizle(user_id)

  kullanim_dus(kullanan, istatistik.kredi_gideri)
  try:
    db.session.commit()
    return '', 200
  except:
    db.session.rollback()
    return abort(500)

def konular_ve_kademeler():
  dersler = db.session.query(Hangiders).filter_by(lang=session['lang_code'])
  kademeler = db.session.query(Tag).filter_by(lang=session['lang_code'])
  kademeler = [x.name for x in kademeler.all()]
  konular = db.session.query(Konu).filter_by(lang=session['lang_code'])
  konular_sozluk = {}
  for x in dersler:
      konular_sozluk[str(x.name)] = [y.name for y in konular.all() if y.hangi_ders == x.id]
  
  dersler = [x.name for x in dersler.all()]

  konular = json.dumps(konular_sozluk,ensure_ascii = False)
  kademeler = json.dumps(kademeler,ensure_ascii = False)
  dersler = json.dumps(dersler,ensure_ascii = False)
  return konular, kademeler, dersler