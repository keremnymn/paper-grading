from src.kredi.utils import kredi_hesapla
from flask import abort, current_app, url_for, redirect, render_template, Blueprint, jsonify, request, session
from flask_login import current_user, login_required
from src import db
from sqlalchemy import func
from src.rapor.utils import kazanim_performans, alphanum_key, ogrenci_kagit_sil, ogrenci_kazanim_performansi, ogrenci_okunan_sorular,\
                                ogrenci_rapor_pdf, gercek_ogrenci_ortalama, sinav_onizleme_sil, sinif_sinav_eslestir, sinif_ortalama,\
                                deep_analysis_kazanimlar, ogrenci_yeni_rapor, sinif_raporu_kredisi, sinif_raporlari_sil, _ogrenci_preview
from src.models import PaperGradingKullanimi, Okunansinav, Okunansoru, Ogrenci, Sinav, Sinif, Gercekogrenci, Sinifrapor
import boto3, os, string, unicodedata
from textwrap import wrap
from flask_babel import lazy_gettext as _l

rapor = Blueprint('rapor', __name__)
s3_client = boto3.client('s3')

@rapor.route('/pg/panel', methods=['GET', 'POST'])

def dashboard():
    kagitlar = db.session.query(func.sum(PaperGradingKullanimi.kagit_sayisi)).filter(PaperGradingKullanimi.user_id == current_user.id).scalar()
    sorular = db.session.query(func.sum(\
                                PaperGradingKullanimi.coktan_secmeli_sayisi\
                                + PaperGradingKullanimi.dogru_yanlis_sayisi\
                                + PaperGradingKullanimi.eslestirme_sayisi\
                                + PaperGradingKullanimi.bosluk_doldurma_sayisi)).filter(PaperGradingKullanimi.user_id == current_user.id).scalar()
    kredi = kredi_hesapla(current_user)
    tasarruf = 0 if kagitlar == None else int(round((kagitlar * 3 ) / 60))
    son_kullanilan_sinavlar = [Sinav.query.filter_by(id=x.sistemdeki_karsiligi).first() for x in Okunansinav.query.filter_by(lang=session['lang_code']).filter_by(user_id=current_user.id).limit(6) if x.sistemdeki_karsiligi != None]
    
    return render_template('rapor/index.html',
                            isIndex=True, 
                            baslik="Paper Grading Panel",
                            kagitlar=0 if kagitlar == None else kagitlar,
                            sorular=0 if sorular == None else sorular,
                            kredi=0 if kredi == None else kredi,
                            tasarruf=tasarruf,
                            son_kullanilan_sinavlar=son_kullanilan_sinavlar[::-1])

@rapor.get('/pg/panel/exams')
@rapor.get('/pg/panel/sinavlar')

def sinavlar():
    return render_template('rapor/sinavlar.html', isIndex=True, baslik=_l("Yapılan Sınavlar"))

@rapor.get('/pg/panel/exams/<int:id>')
@rapor.get('/pg/panel/sinavlar/<int:id>')

def sinav_goster(id):
    sinav = Okunansinav.query.filter_by(id=id).first()
    if current_user.id != sinav.user_id:
        return redirect(url_for('main.pg_landing'))
    ortalama = int(sum([o.toplam_puan for o in sinav.ogrenciler])) / len(sinav.ogrenciler)
    return render_template('rapor/sinav.html', 
                            baslik=sinav.ad, 
                            isIndex=True, 
                            sinav=sinav, 
                            ortalama=int(round(ortalama)))

@rapor.get('/pg/panel/classes')
@rapor.get('/pg/panel/siniflar')

def siniflar():
    return render_template('rapor/siniflar.html', isIndex=True, baslik=_l("Sınıflar"))

@rapor.get('/pg/panel/classes/<int:id>')
@rapor.get('/pg/panel/siniflar/<int:id>')

def sinif_goster(id):
    sinif = Sinif.query.filter_by(id=id).first()
    if current_user.id != sinif.user_id:
        return redirect(url_for('main.pg_landing'))
    return render_template('rapor/sinif.html', 
                            baslik=sinif.name, 
                            isIndex=True, 
                            sinif=sinif)

@rapor.get('/pg/panel/student/<int:id>')
@rapor.get('/pg/panel/ogrenci/<int:id>')

def ogrenci_goster(id):
    ogrenci = Ogrenci.query.filter_by(id=id).first()
    if ogrenci.sinav.user_id != current_user.id:
        return redirect(url_for('main.pg_landing'))
    if 'Hata: ' in ogrenci.ad_soyad and ogrenci.ad_soyad.endswith('.png'):
        return redirect(url_for('rapor.sinav_goster', id=ogrenci.sinav_id))
    else:
        sinav = Okunansinav.query.filter_by(id=ogrenci.sinav_id).first()
        ortalama = int(sum([o.toplam_puan for o in sinav.ogrenciler])) / len(sinav.ogrenciler)
        return render_template('rapor/ogrenci.html', 
                            baslik=_l("Paper Grading Panel"),
                            isIndex=True,
                            sinav=sinav,
                            ogrenci=ogrenci,
                            ortalama=int(round(ortalama)))

### ----> AJAX ROUTES <---- ###


@rapor.get('/rapor/panel_genel')
def panel_genel():
    sinavlar = Okunansinav.query.filter_by(user_id=current_user.id).order_by(Okunansinav.timestamp.asc()).limit(7)
    return jsonify([
        {
            'tarih': x.timestamp.strftime("%d %B %Y"),
            'ortalama':round(int(sum([o.toplam_puan for o in x.ogrenciler])) / len(x.ogrenciler), 2)
        }
        for x in sinavlar
    ])


@rapor.post('/rapor/ogrenci_preview')
def ogrenci_preview():
    id = request.form.get('id')
    ogrenci = Ogrenci.query.filter_by(id=id).first()
    if ogrenci.sinav.user_id != current_user.id:
        return abort(404)
    bilgiler = _ogrenci_preview(ogrenci)
    return {'bilgiler': sorted(bilgiler, key=lambda x: x['guven'], reverse=True)}


@rapor.post('/rapor/ogrenci_ajax')
def ogrenci_ajax():
    id = request.form.get('id')
    ogrenci = Ogrenci.query.filter_by(id=id).first()
    sinav = Okunansinav.query.filter_by(id=ogrenci.sinav_id).first()
    if sinav.user_id != current_user.id:
        return abort(404)
    sinif_kazanimlari, ogrenci_kazanimlari = ogrenci_kazanim_performansi(sinav, ogrenci)
    bilgiler = ogrenci_okunan_sorular(ogrenci)
    labels = [wrap(x, 40) for x in sinif_kazanimlari.keys()]
    bilgiler = {
        'bilgiler': sorted(bilgiler, key=lambda x: alphanum_key(x['sira'])),
        'sinif_kazanimlari':sinif_kazanimlari,
        'ogrenci_kazanimlari': ogrenci_kazanimlari,
        'labels': labels
    }
    return bilgiler


@rapor.post('/rapor/pdfolustur')
def pdfolustur():
    id = request.form.get('id')
    ogrenci = Ogrenci.query.filter_by(id=id).first()
    if ogrenci.sinav.user_id != current_user.id:
        return abort(404)
    # try:
    rapor_id = ogrenci_yeni_rapor(ogrenci)
    dispatch = {'id': rapor_id, 'lang': session['lang_code']}
    if os.environ['RUNNING_ON'] == 'localhost':
        ogrenci_rapor_pdf(dispatch)
    else:
        ogrenci_rapor_pdf.delay(dispatch)
    return '', 200
    # except:
    #     db.session.rollback()
    #     return abort(500)


@rapor.post('/rapor/rapor_kontrol')
def rapor_kontrol():
    id = request.form.get('id')
    ogrenci = Ogrenci.query.filter_by(id=id).first()
    liste = ['hata', 'bekliyor']
    if len(ogrenci.raporlar) > 0:
        rapor = ogrenci.raporlar[-1]
        if not rapor.durum in liste:
            data = current_app.config['S3_BUCKET_NAME'] + 'rapor/ogrenci/' + str(ogrenci.id) + '/' + rapor.uuid + '.' + rapor.tur
            return data
        else:
            return ogrenci.raporlar[-1].durum
    else:
        return ''


@rapor.post('/rapor/soru_bilgileri')
def soru_bilgileri():
    id = request.form.get('id')
    bilgiler = PaperGradingKullanimi.query.filter_by(okunan_sinav_id=id).first()
    sinav = Okunansinav.query.filter_by(id=id).first()
    ogrenciler = [
        {
            'id': x.id,
            'adsoyad': x.ad_soyad,
            'gercek_ogrenci': None if x.gercek_ogrenci == None else x.gercek_ogrenci.name,
            'gercek_ogrenci_id': None if x.gercek_ogrenci == None else x.gercek_ogrenci.id,
            'puan': x.toplam_puan
        }
        for x in sinav.ogrenciler
    ]
    toplam_soru = [
                    bilgiler.coktan_secmeli_sayisi / bilgiler.kagit_sayisi, 
                    bilgiler.dogru_yanlis_sayisi / bilgiler.kagit_sayisi, 
                    bilgiler.eslestirme_sayisi / bilgiler.kagit_sayisi, 
                    bilgiler.bosluk_doldurma_sayisi / bilgiler.kagit_sayisi
                ]
    _kazanimlar = kazanim_performans(sinav)
    return {
            'toplam_soru': int(sum(toplam_soru)), 
            'ad': bilgiler.ders_adi.name,
            'kagit_sayisi': bilgiler.kagit_sayisi,
            'kazanimlar': _kazanimlar,
            'sinif': sinav.sinif.name if sinav.sinif != None else None,
            'ogrenciler': ogrenciler,
            'user_siniflar': [{'ad': x.name, 'id': x.id} for x in current_user.siniflar],
            'sinif': None if sinav.sinif_id == None else sinav.sinif.name,
            'sinif_ogrenciler': None if sinav.sinif_id == None else [(x.name, x.id) for x in sinav.sinif.ogrenciler]
        }


@rapor.post('/rapor/sinavlar_ajax')
def sinavlar_ajax():
    sinavlar = Okunansinav.query.filter_by(user_id=current_user.id).filter_by(silindi_mi=False).all()
    sinavlar = [
        {
            'ad': x.ad, 
            'tarih': x.timestamp, 
            'ogrenciler':len(x.ogrenciler),
            'puan':round(int(sum([o.toplam_puan for o in x.ogrenciler])) / len(x.ogrenciler),2),
            'ders_adi': x.kullanim[0].ders_adi.name,
            'sinif': x.sinif.name if x.sinif != None else None,
            'id': x.id
        }
        for x in sinavlar
    ]
    return jsonify(sinavlar)


@rapor.post('/rapor/sinav_ad_degistir')
def sinav_ad_degistir():
    id = request.form.get('id')
    ad = request.form.get('ad')
    sinav = Okunansinav.query.filter_by(id=id).first_or_404()
    if len(ad) < 100 and len(ad) > 3:
        sinav.ad = ad
        try:
            db.session.commit()
        except:
            db.session.rollback()
            return '', 500
    else:
        abort(500)
    return '', 200


@rapor.post('/rapor/soru_cevap_degistir')
def soru_cevap_degistir():
    id = request.form.get('id')
    cevap = request.form.get('cevap')
    if cevap == '' or cevap == None:
        return abort(404)
    else:
        cevap = cevap.lower().strip().replace('ı', 'i')
    cevap = unicodedata.normalize('NFD', cevap).encode('ascii', 'ignore').decode('utf-8').strip()
    soru = Okunansoru.query.filter_by(id=id).first_or_404()
    ogrenci = Ogrenci.query.filter_by(id=soru.ogrenci_id).first()
    if Okunansinav.query.filter_by(id=ogrenci.sinav_id).first().user_id != current_user.id:
        return abort(404)
    if len(cevap) > 0 and len(cevap) < 200:
        soru.ogrenci_cevaplari = cevap
        soru.guven = 1
        for x in soru.beklenen_cevaplar.split(','):
            x = x.strip()
            if cevap == x:
                if soru.sonuc != True:
                    ogrenci.toplam_puan += soru.puan
                soru.sonuc = True
                break
            else:
                if soru.sonuc != False:
                    ogrenci.toplam_puan -= soru.puan
                soru.sonuc = False
        try:
            db.session.commit()
            return '', 200
        except:
            db.session.rollback()
            return '', 500
    else:
        return abort(500)


@rapor.route('/panel_bilgiler', methods=['GET', 'POST'])
def panel_bilgiler():
    sorular = [sum(x) for x in Okunansinav.query.filter_by(user_id = current_user.id).ogrenciler]
    return {'sorular': sorular}


@rapor.post('/yeni_sinif')
def yeni_sinif():
    ad = request.form.get('ad')
    if ad == None:
        return abort(404)
    if Sinif.query.filter_by(user_id=current_user.id).filter_by(name=str(ad)).first() != None:
        return abort(401)
    else:
        sinif = Sinif(name=str(ad), user_id=current_user.id)
        db.session.add(sinif)
        try:
            db.session.commit()
            return '', 200
        except:
            db.session.rollback()
            return abort(500)


@rapor.get('/get_siniflar')
def get_siniflar():
    siniflar = Sinif.query.filter_by(user_id=current_user.id).all()
    return jsonify(
        [
            {
                'name': x.name,
                'ogrenci_sayisi': len(x.ogrenciler),
                'sinav_sayisi': len(x.sinavlar),
                'sinif_ort':sinif_ortalama(x),
                'id': x.id
            }
            for x in siniflar
        ]
    )


@rapor.post('/rapor/sinif_ad_degistir')
def sinif_ad_degistir():
    id = request.form.get('id')
    ad = request.form.get('ad')
    if ad == None:
        return abort(404)
    sinif = Sinif.query.filter_by(id=id).first_or_404()
    if len(ad) < 100 and len(ad) > 5:
        sinif.name = ad
        try:
            db.session.commit()
            return '', 200
        except:
            db.session.rollback()
            return '', 500
    else:
        abort(500)


@rapor.post('/rapor/sinifi_sil')
def sinifi_sil():
    id = request.form.get('id')
    sinif = Sinif.query.filter_by(id=id).first_or_404()
    sinif_raporlari_sil(sinif)
    db.session.delete(sinif)
    try:
        db.session.commit()
        return '', 200
    except:
        db.session.rollback()
        return abort(500)


@rapor.post('/rapor/sinifa_ogrenci_ekle')
def sinifa_ogrenci_ekle():
    id = request.form.get('id')
    liste = request.form.get('liste').split('\n')
    sinif = Sinif.query.filter_by(id=id).first_or_404()
    sinif_ogrenciler = [(x.numara, x.name) for x in sinif.ogrenciler]
    for x in liste:
        if len(x) > 0:
            if '-' in x:
                x = x.split('-', 1)
                numara = x[0].strip()[:20]
                ad = string.capwords(x[1].strip()[:70])
                if not (numara, ad) in sinif_ogrenciler:
                    ogrenci = Gercekogrenci(name=ad, numara=numara, sinif_id=sinif.id)
                    db.session.add(ogrenci)
            else:
                ad = string.capwords(x.strip()[:70])
                if not (None, ad) in sinif_ogrenciler:
                    ogrenci = Gercekogrenci(name=ad, sinif_id=sinif.id)
                    db.session.add(ogrenci)
    try:
        db.session.commit()
        return '', 200
    except:
        db.session.rollback()
        return '', 500


@rapor.post('/rapor/sinif_ogrenci_bilgi_degis')
def sinif_ogrenci_bilgi_degis():
    id = request.form.get('sinif_id')
    ogrenci_id = request.form.get('ogrenci_id')
    isim = request.form.get('isim')
    num = request.form.get('num')
    sinif = Sinif.query.filter_by(user_id=current_user.id).filter_by(id=id).first()
    sinif_ogrenciler = [(x.numara, x.name) for x in sinif.ogrenciler]
    if not (num, isim) in sinif_ogrenciler:
        ogrenci = Gercekogrenci.query.filter_by(id=ogrenci_id).first_or_404()
        ogrenci.numara = string.capwords(num.strip()[:20])
        ogrenci.name = string.capwords(isim.strip()[:70])
        try:
            db.session.commit()
        except:
            db.session.rollback()
            return abort(500)
    return '', 200


@rapor.post('/get_sinif_ogrenciler')
def get_sinif_ogrenciler():
    bilgiler = {}
    id = request.form.get('id')
    sinif = Sinif.query.filter_by(id=id).first_or_404()
    tutar = sinif_raporu_kredisi(sinif)
    kredi = kredi_hesapla(current_user)
    tutar = 'yetersiz' if tutar >= kredi else tutar
    ogrenci_bilgi = [
            {
                'name': x.name,
                'numara': x.numara,
                'sinavlar': len(x.sinavlar),
                'ortalama': gercek_ogrenci_ortalama(x),
                'id': x.id
            }
            for x in sinif.ogrenciler
        ]
    bilgiler['ogrenci_bilgi'] = ogrenci_bilgi
    bilgiler['rapor_tutar'] = tutar
    return bilgiler


@rapor.post('/rapor/sinav_sil')
def sinav_sil():
    id = request.form.get('id')
    sinav = Okunansinav.query.filter_by(id=id).first_or_404()
    try:
        sinav.silindi_mi = True
        db.session.commit()
    except:
        db.session.rollback()
        return abort(500)
    if os.environ['RUNNING_ON'] == 'localhost':
        sinav_onizleme_sil(sinav.id)
    else:
        sinav_onizleme_sil.delay(sinav.id)
    return '', 200


@rapor.post('/rapor/sinif_eslestir')
def sinif_eslestir():
    sinif_id = request.form.get('sinif_id')
    sinav_id = request.form.get('sinav_id')
    sinif = Sinif.query.filter_by(id=sinif_id).first()
    sinav = Okunansinav.query.filter_by(id=sinav_id).first()
    if sinif == None:
        sinav.sinif_id = None
    else:
        sinif_ogrenciler = sinif.ogrenciler
        sinav_ogrenciler = sinav.ogrenciler
        if len(sinav_ogrenciler) > len(sinif_ogrenciler):
            return abort(404)
        eslestirmeler = sinif_sinav_eslestir([(x.name, x.id) for x in sinif_ogrenciler], [(x.ad_soyad_gercek, x.id) for x in sinav_ogrenciler])
        for x in eslestirmeler:
            Ogrenci.query.filter_by(id=x[0]).first().gercek_ogrenci_id = x[1]
        sinav.sinif_id = sinif.id
    try:
        db.session.commit()
        return '', 200
    except:
        db.session.rollback()
        return abort(500)


@rapor.post('/rapor/ogrenci_eslestirme_degis')
def ogrenci_eslestirme_degis():
    durum = request.form.get('durum')
    if durum == 'ayni':
        return abort(404)
    id = request.form.get('id')
    ogrenci_id = request.form.get('secilen')
    ogrenci = Ogrenci.query.filter_by(id=id).first_or_404()
    if durum == 'var':
        var_olan_ogrenci = Gercekogrenci.query.filter_by(id=ogrenci_id).first_or_404()
        for x in var_olan_ogrenci.sinavlar:
            if x.sinav_id == ogrenci.sinav_id:
                x.gercek_ogrenci_id = ''
    ogrenci.gercek_ogrenci_id = ogrenci_id
    try:
        db.session.commit()
        return '', 200
    except:
        db.session.rollback()
        return '', 500


@rapor.post('/rapor/kagit_sil')
def kagit_sil():
    id = request.form.get('id')
    try:
        ogrenci_kagit_sil(id)
        return '', 200
    except:
        return abort(500)


@rapor.post('/rapor/siniftan_ogr_sil')
def siniftan_ogr_sil():
    id = request.form.get('id')
    ogrenci = Gercekogrenci.query.filter_by(id=id).first_or_404()
    try:
        db.session.delete(ogrenci)
        db.session.commit()
        return '', 200
    except:
        db.session.rollback()
        return abort(500)

@rapor.post('/deep_analysis')

def deep_analysis():
    id = request.form.get('id')
    sinif = Sinif.query.filter_by(id=id).first_or_404()
    if len(sinif.sinavlar) == 0 or len(sinif.ogrenciler) == 0:
        return abort(404)
    rapor = Sinifrapor(sinif_id=sinif.id, durum='bekliyor', tur='xlsx')
    try:
        db.session.add(rapor)
        db.session.commit()
        if os.environ['RUNNING_ON'] == 'localhost':
            deep_analysis_kazanimlar([sinif.id, rapor.id])
        else:
            deep_analysis_kazanimlar.delay([sinif.id, rapor.id])
    except:
        db.session.rollback()
        return abort(500)
    return '', 200

@rapor.post('/get_sinif_raporlar')

def get_sinif_raporlar():
    id = request.form.get('id')
    sinif = Sinif.query.filter_by(id=id).first_or_404()
    raporlar = [
        {   
            'timestamp': x.timestamp.strftime("%d %B %Y"),
            'href': current_app.config['S3_BUCKET_NAME'] + f'rapor/sinif/{str(x.sinif_id)}/{x.uuid}.xlsx' if x.durum == 'hazir' else ''
        }
        for x in sinif.raporlar if x.durum == 'hazir'
    ]
    return jsonify(sorted(raporlar, key=lambda p: p['timestamp'], reverse=True))