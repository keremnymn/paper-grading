import os, json, re, ast, boto3, pathlib, ast, requests
from flask import render_template, url_for, flash, redirect,\
                request, abort, Blueprint, current_app, jsonify,\
                session
from flask_login import current_user, login_required
from src import db, get_locale
from src.models import User, Logo, BireyselFatura,\
                                PaperGradingKullanimi,\
                                Hangiders, Soru, Sinav, Tag, Konu, \
                                Sinav_Vote, Sinav_Kopya, Kazanim
from src.kredi.forms import TahminFormu
from src.kredi.utils import hesap, konular_ve_kademeler
from src.kredi.pdf_olustur import pdf_yazdir, parse_questions,\
                                        sorulari_gonder, sorulari_guncelle,\
                                        buckettan_sil, bucket_gorsel_ad_degistir,\
                                        bucket_sinav_kopyala, konu_ekle
from werkzeug.utils import secure_filename
from sqlalchemy import func
from urllib.parse import unquote
from src.models import generate_rand_id
from datetime import datetime
from flask_babel import lazy_gettext as _l, get_locale

kredi = Blueprint('kredi', __name__)
s3_client = boto3.client('s3')
dosya_turleri = ['.jpg','.jpeg', '.png']

@kredi.post('/kredi_tahmini')
def tahmin():
    form = TahminFormu()
    if form.validate_on_submit():
        _, data = hesap(int(form.kagit_sayisi.data), 
                        int(form.kacsayfa.data), 
                        int(form.bosluk_doldurma.data),
                        int(form.coktan_secmeli.data),
                        int(form.dogru_yanlis.data),
                        int(form.eslestirme.data))
        return jsonify(data = data)
    return jsonify(data = form.errors)

### ÖNEMLİ ###
'''
    kullanıcıların yüklediği fakat kullanmadığı görseller için bir cron job
    ya da admin sayfasına bir function yazılmalı. bu function kullanıcıların 
    yazdığı tüm soruları ve kullanıcıların directorylerindeki tüm görselleri
    eşleştirmeli, eğer görsel databaseteki bir soruda kullanılmamışsa silmelidir.
'''
### ÖNEMLİ ###

@kredi.route('/pg/exams', methods=['GET', 'POST'], endpoint='sinavlar_en')
@kredi.route('/pg/sinavlar', methods=['GET', 'POST'])

def sinavlar():
    page = request.args.get('page', 1, type=int)
    sinavlar = db.session.query(Sinav).filter_by(lang=str(get_locale())).filter(Sinav.user_id == current_user.id).order_by(Sinav.timestamp.desc())
    acik_sinavlar = db.session.query(Sinav).filter_by(lang=str(get_locale())).filter(Sinav.ozel_mi == False).count()
    return render_template('kredi/sinavlar.html', 
                            sinavlar=sinavlar.paginate(page=page, per_page=8), 
                            baslik=_l('Hazırladığınız Sınavlar'),
                            acik_sinavlar=acik_sinavlar)

@kredi.route('/pg/exam/<int:id>', methods=['GET', 'POST'])
@kredi.route('/pg/sinav/<int:id>', methods=['GET', 'POST'])

def sinav_goster(id):
    kilavuz_onay = True if not 'sinav_okuma_kilavuz_onay' in session else False
    sinav = db.session.query(Sinav).filter(Sinav.id == id).first_or_404()
    url = current_app.config['S3_BUCKET_NAME'] + f'pdfs/{str(sinav.user_id)}/' + sinav.pdf_dosyasi + '.pdf'
    
    if not current_user.is_authenticated or sinav.lang != session['lang_code']:
        session['lang_code'] = sinav.lang
        return redirect(url_for('main.pg_landing'))
    elif current_user.is_authenticated and current_user.id == sinav.user_id:
        konular, kademeler, dersler = konular_ve_kademeler()
        liste = db.session.query(Soru).filter(Soru.sinav_id == sinav.id).all()
        raw_data = sorulari_gonder(liste)
        
        bu_sinav_kademeler = [x.name for x in sinav.tags.all()]
        bu_sinav_konular = [x.name for x in sinav.konular.all()]
        
        return render_template('kredi/sinav_olustur.html', 
                                isIndex=True, 
                                baslik=sinav.baslik, 
                                data=raw_data,
                                dersler=dersler, 
                                url=url, 
                                sinav=sinav,
                                kademeler=kademeler, 
                                bu_sinav_kademeler=bu_sinav_kademeler,
                                bu_sinav_konular=bu_sinav_konular,
                                konular=konular,
                                kilavuz_onay=kilavuz_onay)
    elif sinav.ozel_mi:
        return redirect(url_for('main.pg_landing'))
    else:
        sinav_vote = db.session.query(Sinav_Vote)\
            .filter(Sinav_Vote.user_id == current_user.id)\
            .filter(Sinav_Vote.sinav_id == sinav.id).first()
        alkislanmis_mi = True if sinav_vote is not None else False
        return render_template('kredi/sinav_incele.html', 
                                isIndex=True, 
                                baslik=sinav.baslik, 
                                url=url,
                                sinav=sinav,
                                alkislanmis_mi=alkislanmis_mi)

@kredi.route('/pg/exam/create', methods=['GET', 'POST'])
@kredi.route('/pg/sinav/yeni', methods=['GET', 'POST'])

def sinav_olustur():
    kilavuz_onay = True if not 'sinav_okuma_kilavuz_onay' in session else False
    konular, kademeler, dersler = konular_ve_kademeler()
    gorsel_path = pathlib.Path(os.path.join(current_app.root_path, 'static/fpdf/pdf_files/gorseller', str(current_user.id)))
    if not gorsel_path.exists():
        os.makedirs(gorsel_path)

    ozel_sinavlar = db.session.query(func.count(Sinav.user_id == current_user.id)).filter(Sinav.ozel_mi == True).scalar()
    if ozel_sinavlar > 100:
        flash(_l('Çok fazla sınav hazırladınız, bazılarını silmeyi deneyin.'), 'danger')
        return redirect(url_for('kredi.sinavlar'))
        
    return render_template('kredi/sinav_olustur.html', 
                            isIndex=True, 
                            baslik=_l("Sınav Oluştur"), 
                            dersler=dersler, 
                            kademeler=kademeler,
                            konular=konular,
                            kilavuz_onay=kilavuz_onay)

@kredi.post('/pdf_yenile')
def pdfyenile():
    data = request.form.to_dict()
    path = os.path.join(current_app.root_path, 'static/fpdf')
    sinav = db.session.query(Sinav).filter(Sinav.user_id == current_user.id).filter(Sinav.baslik == data['baslik']).first()
    ozel_mi = True if data['gizli_mi'] == 'false' else False
    ders = db.session.query(Hangiders).filter(Hangiders.name  == data['ders']).first_or_404()
    gorsel_path = pathlib.Path(os.path.join(current_app.root_path, 'static/fpdf/pdf_files/gorseller', str(current_user.id)))
    istenmeyen_karakterler = ['^', '!', '?', '"', 'é', '}', '{', '-', '[', ']', '%', '#', '$', '£', '*', '<', '>', '=']
    
    if 'yeni_mi' in data.keys():
        var_mi = db.session.query(Sinav).filter(Sinav.user_id == current_user.id).filter(Sinav.baslik == data['baslik']).first()
        if var_mi:
            return abort(413)
    
    _baslik = ''
    for x in data['baslik']:
        if x in istenmeyen_karakterler:
            x = ''
        _baslik += x
    
    if sinav:
        if current_user.id != sinav.user_id and not current_user.isadmin:
            return abort(404)
        else:
            pdf_fn = str(current_user.id) + '-' + data['time']
            try:
                fn = pdf_yazdir(path, data, current_user.id, pdf_fn, sinav, session['lang_code'])
            except Exception as err:
                if err.args[1] == 'sayfa':
                    return abort(406)
                else:
                    return abort(500)
            sinav.pdf_dosyasi = pdf_fn
            sinav.ozel_mi = ozel_mi
            sinav.hangi_ders = ders.id
            sinav.ust_yazi = data['ust_yazi']
            sinav.alt_yazi = data['alt_yazi']
            sinav.aciklama = data['aciklama']
            if data['logo_secimi'] != '' and data['logo_secimi'] != 'None':
                sinav.logo_id = int(data['logo_secimi'])
            if sinav.uuid == None:
                sinav.uuid = generate_rand_id()
            
            if sinav.sayfa_duzeni != data['duzen']:
                sinav.sayfa_duzeni = data['duzen']

            tags = data['kademeler'].split(',')
            sinav.tags = []
            try:
                for x in tags:
                    tag_ekle = Tag.query.filter_by(lang=session['lang_code']).filter_by(name=f'{x}').first()
                    sinav.tags.append(tag_ekle)
            except:
                db.session.rollback()
                return abort(403)

            if 'konular' in data and data['konular'] != '':
                try:
                    konu_ekle(sinav, data['konular'], ders)
                except IndexError:
                    sinav.konular = []
            try:
                db.session.commit()
            except:
                db.session.rollback()
                return abort(500)

            #işlevin neden kullanılmaması gerektiğini işlevin içinde belirttim
            #eski_gorselleri_sil(gorsel_path, data, sinav)

            fn = current_app.config['S3_BUCKET_NAME'] + fn

            # celery'ye gönderilecek.
            # sorulari_guncelle.delay(sinav,data)
            sorulari_guncelle(sinav, data)

            return jsonify(fn)
    else:
        pdf_fn = str(current_user.id) + '-' + data['time']

        try:
            fn = pdf_yazdir(path, data, current_user.id, pdf_fn, '', session['lang_code'])
        except Exception as err:
            if err.args[1] == 'sayfa':
                return abort(406)
            else:
                return abort(500)

        sinav = Sinav(pdf_dosyasi=pdf_fn, ozel_mi=ozel_mi, baslik=_baslik,\
                        ust_yazi=data['ust_yazi'] if 'ust_yazi' in data else '',\
                        user_id=current_user.id, hangi_ders=ders.id,
                        sayfa_duzeni=data['duzen'], alt_yazi=data['alt_yazi'],
                        aciklama=data['aciklama'], lang=session['lang_code'])
        try:
            db.session.add(sinav)
            db.session.flush()
            db.session.refresh(sinav)
        except:
            db.session.rollback()
            return abort(500)
        
        try:
            tags = data['kademeler'].split(',')
            for x in tags:
                tag_ekle = Tag.query.filter_by(name=f'{x}').first()
                sinav.tags.append(tag_ekle)
        except:
            return abort(403)

        if 'konular' in data and data['konular'] != '':
            konu_ekle(sinav, data['konular'], ders)
        
        if data['logo_secimi'] != '' and data['logo_secimi'] != 'None':
            sinav.logo_id = int(data['logo_secimi'])
        
        sorular = parse_questions(data)

        for soru in sorular:
            raw_soru = soru[1].replace('-_yeni_-', f'-{str(sinav.id)}-')
            soru = Soru(tip=soru[0], raw_soru=raw_soru, sinav_id=sinav.id)
            db.session.add(soru)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            return abort(500)
        
        for gorsel in os.listdir(gorsel_path):
            if '-_yeni_-' in gorsel:
                yeni_ad = gorsel.replace('-_yeni_-', f'-{str(sinav.id)}-')
                os.rename(os.path.join(gorsel_path, gorsel), os.path.join(gorsel_path, yeni_ad))
        bucket_gorsel_ad_degistir(str(current_user.id), str(sinav.id))
        fn = current_app.config['S3_BUCKET_NAME'] + fn

        return {'data':fn, 'id':sinav.id}

@kredi.post('/sinav_sil')
def sinav_sil():
    aydi = request.form.get('id')
    sinav_id = request.form.get('sinav')
    sinav = db.session.query(Sinav).filter(Sinav.user_id == aydi).filter(Sinav.id == sinav_id).first_or_404()
    if current_user.id != sinav.user_id:
        return abort(404)
    try:
        buckettan_sil(sinav, current_user.id)
        sinav_kopya = db.session.query(Sinav_Kopya)\
            .filter(Sinav_Kopya.yeni_sinav_id == sinav.id)\
            .filter(Sinav_Kopya.user_id == current_user.id).first()
        if sinav_kopya is not None:
            db.session.delete(sinav_kopya)
        db.session.delete(sinav)
        db.session.commit()
        return '', 200
    except:
        db.session.rollback()
        return abort(500)

@kredi.post('/sinav_gorsel_yukle')
def sinava_gorsel_yukle():
    file = request.files.get('file')
    if 'matematik' in file.filename:
        file.filename += '.png'

    dinamik = '-_yeni_-'

    try:
        sinav = request.form.get('sinav')
        sinav = db.session.query(Sinav).filter(Sinav.id == sinav).first_or_404()
        dinamik = f'-{str(sinav.id)}-'
        baslik = sinav.baslik
    except:
        baslik = request.form.get('baslik')
        if baslik == '' or '-_yeni_-' in baslik or '-_yeni_-_cs_-' in baslik:
            return abort(500)
    
    ad, _ext = os.path.splitext(file.filename.lower())
    ad = ad.replace('-', '')
    ad = baslik + dinamik + ad + _ext

    if _ext not in dosya_turleri:
        return abort(403)

    picture_path = os.path.join(current_app.root_path, 'static/fpdf/pdf_files/gorseller/', str(current_user.id) , ad)
    file.save(picture_path)

    s3_ext = _ext.strip('.')
    s3_yol = f'pdfs/{current_user.id}/gorseller/{ad}'
    s3_client.upload_file(picture_path, os.environ['S3_NAME'], s3_yol, ExtraArgs={
        "ACL": "public-read",
        "CacheControl": "max-age=2000000,public",
        "Expires": "2030-09-01T00:00:00Z",
        "ContentType": f'image/{s3_ext}'})

    return current_app.config['S3_BUCKET_NAME'] + f'pdfs/{str(current_user.id)}/gorseller/{ad}'

@kredi.post('/cs_gorsel_yukle')
def cs_gorsel_yukle():
    dosya_turleri = ['.jpg','.jpeg', '.png']
    files = request.files.getlist('files')

    dinamik = '-_yeni_-_cs_-'

    try:
        sinav = request.form.get('sinav')
        sinav = db.session.query(Sinav).filter(Sinav.id == sinav).first_or_404()
        dinamik = f'-{str(sinav.id)}-_cs_-'
        baslik = sinav.baslik
    except:
        baslik = request.form.get('baslik')
        if baslik == '' or baslik == '-_yeni_-_cs_-' or baslik == '-_yeni_-':
            return abort(413)

    gorsel_listesi = []
    for file in files:
        ad, _ext = os.path.splitext(file.filename.lower())
        ad = ad.replace('-', '')
        ad = baslik + dinamik + secure_filename(ad) + '.jpg'
        
        if _ext not in dosya_turleri:
            return abort(403)

        picture_path = os.path.join(current_app.root_path, 'static/fpdf/pdf_files/gorseller/', str(current_user.id) , ad)
        file.save(picture_path)

        s3_yol = f'pdfs/{current_user.id}/gorseller/{ad}'
        s3_client.upload_file(picture_path, os.environ['S3_NAME'], s3_yol, ExtraArgs={
            "ACL": "public-read",
            "CacheControl": "max-age=2000000,public",
            "Expires": "2030-09-01T00:00:00Z",
            "ContentType": 'image/jpg'})
        
        gorsel_listesi.append(current_app.config['S3_BUCKET_NAME'] + f'pdfs/{str(current_user.id)}/gorseller/{ad}')
    
    return jsonify(gorsel_listesi)

@kredi.post('/mt_sil')
def mt_sil():
    #öğretmenin eklediği matematik formülünü s3'ten siler.
    file = request.form.get('src')
    id = request.form.get('id')
    if current_user.id != int(id):
        return abort(404)
    else:
        key = f'pdfs/{id}/gorseller/{os.path.basename(file)}'
        s3_client.delete_object(Bucket=os.environ['S3_NAME'], Key=key)
        return '', 200


@kredi.post('/konu_getir')
def konu_getir():
    secilen = request.form.get('secilen')
    ders = Hangiders.query.filter_by(lang=session['lang_code']).filter_by(name=secilen).first()
    konular = [x.name for x in db.session.query(Konu).filter(Konu.hangi_ders == ders.id).all()]
    konular = json.dumps(konular,ensure_ascii = False)
    return konular, 200

### HAZIR SINAVLAR ###
@kredi.route('/pg/exams/archive', methods=['GET', 'POST'])
@kredi.route('/pg/sinavlar/arsiv', methods=['GET', 'POST'])

def sinavlar_arsiv():
    page = request.args.get('page', 1, type=int)
    
    sinavlar = db.session.query(Sinav).filter_by(lang=str(get_locale())).filter(Sinav.ozel_mi == False)
    kademeler = db.session.query(Tag).filter_by(lang=str(get_locale()))
    dersler = db.session.query(Hangiders).filter_by(lang=str(get_locale()))
    
    konu_olmayan_dersler = Hangiders.konular.any()
    konu_olmayan_dersler = db.session.query(Hangiders, konu_olmayan_dersler)
    _konu_olmayan_dersler = [x[0].name for x in konu_olmayan_dersler if x[1] == False]

    kademeler = [x.name for x in kademeler.all()]
    dersler = [x.name for x in dersler.all()]
    
    kademeler = json.dumps(kademeler,ensure_ascii = False)
    dersler = json.dumps(dersler,ensure_ascii = False)
    konu_olmayan_dersler = json.dumps(_konu_olmayan_dersler,ensure_ascii = False)

    if request.method == 'POST':
        sozluk = request.form.to_dict(flat=False)
        if not 'ders' in sozluk: sozluk['ders'] = '';
        if 'konular' in sozluk:
            konular = '['
            for x in sozluk['konular']:
                konular = konular + "'" + x + "'" + ','
            konular = konular[:-1] + ']'
        else:
            konular = '[]'
        return redirect(url_for('kredi.sinavlar_arsiv',dersadi='' if sozluk['ders'][0] == '' else sozluk['ders'],
                                                    konular=konular, 
                                                    sinif= sozluk['sınıf'],
                                                    olcu='tarih' if not 'olcut' in sozluk else sozluk['olcut'],
                                                    page=1))
    elif request.method == 'GET':
        filtreler = {}
        sozluk = request.args.to_dict(flat=False)
        if sozluk != {}:
            gelen_liste = [] if 'konular' not in sozluk or sozluk['konular'][0] == '[]' or sozluk['konular'][0] == '' else ast.literal_eval(sozluk['konular'][0])
            if 'dersadi' in sozluk and sozluk['dersadi'][0] != '':
                ad = sozluk['dersadi'][0]
                ders = Hangiders.query.filter_by(name=ad).first_or_404()
                filtreler['dersler'] = sozluk['dersadi']
                sinavlar = sinavlar.filter(Sinav.hangi_ders == ders.id)
            if len(gelen_liste) != 0:
                tag_listesi = []
                for x in gelen_liste:
                    tag_ekle = Konu.query.filter_by(name=f'{x}').first_or_404()
                    tag_listesi.append(tag_ekle)
                sinavlar = sinavlar.filter(Sinav.konular.any(Konu.id.in_([x.id for x in tag_listesi])))
                filtreler['konular'] = [x.name for x in tag_listesi]
                tag_listesi.clear()
            if 'sinif' in sozluk and sozluk['sinif'][0] != '':
                sinif = db.session.query(Tag).filter(Tag.name == sozluk['sinif'][0]).first_or_404()
                filtreler['kademeler'] = sinif.name
                sinavlar = sinavlar.filter(Sinav.tags.any(Tag.id.in_([x.id for x in [sinif]])))
            if 'olcu' in sozluk:
                if sozluk['olcu'][0] == 'tarih':
                    sinavlar = sinavlar.order_by(Sinav.timestamp.desc())
                elif sozluk['olcu'][0] == 'puan':
                    sinavlar = sinavlar.order_by(Sinav.alkis_sayi.desc())
                filtreler['olcu'] = sozluk['olcu'][0]
        else:
            sinavlar = sinavlar.order_by(Sinav.alkis_sayi.desc())
    return render_template('kredi/sinavlar_arsiv.html', \
                            baslik=_l("Sınav Arşivi"),  \
                            sinavlar=sinavlar.paginate(page=page, per_page=9), \
                            kademeler=kademeler,
                            dersler=dersler,
                            filtreler=filtreler,
                            konu_olmayan_dersler=konu_olmayan_dersler)


@kredi.route('/sinav_puan', methods=['GET', 'POST'])
def sinav_puan():
    sinav_id = request.form.get('id')
    tip = request.form.get('tip')
    user_id = request.form.get('user_id')
    if int(user_id) != int(current_user.id):
        return abort(404)
    sinav = db.session.query(Sinav).filter(Sinav.id == sinav_id).first_or_404()
    user = User.query.filter_by(id=user_id).first_or_404()
    sinav_sahibi = User.query.filter_by(id=sinav.user_id).first()
    if tip == 'alkis':
        sinav_vote = db.session.query(Sinav_Vote)\
                    .filter(Sinav_Vote.user_id == current_user.id)\
                    .filter(Sinav_Vote.sinav_id == sinav.id).first()
        if sinav_vote is not None:
            sinav_sahibi.alkis -= 2
            sinav.alkis_sayi -= 1
            db.session.delete(sinav_vote)
            db.session.commit()
            return '-1', 200
        else:
            _sinav_vote = Sinav_Vote(user_id=current_user.id, sinav_id=sinav.id)
            db.session.add(_sinav_vote)
            sinav_sahibi.alkis += 2
            sinav.alkis_sayi += 1
            db.session.commit()
            return '+1', 200
    elif tip == 'indir':
        url = current_app.config['S3_BUCKET_NAME'] + f'pdfs/{str(sinav.user_id)}/' + sinav.pdf_dosyasi + '.pdf'
        sinav.indirme_sayi += 1
        db.session.commit()
        return url, 200
    else:
        sinav_kopya = db.session.query(Sinav_Kopya)\
            .filter(Sinav_Kopya.sinav_id == sinav.id)\
            .filter(Sinav_Kopya.user_id == current_user.id).first()                    
        if sinav_kopya is not None:
            return url_for('kredi.sinav_goster', id=sinav_kopya.yeni_sinav_id)
        else:
            sorular = sinav.sorular
            yeni_pdf_dosyasi = sinav.pdf_dosyasi.replace(f'{sinav.user_id}-', f'{user_id}-')
            yeni_baslik = sinav.baslik + ' ' + str(sinav.user_id)
            yeni_sinav = Sinav(pdf_dosyasi=yeni_pdf_dosyasi,
                                ozel_mi=True,
                                baslik=yeni_baslik,
                                ust_yazi=sinav.ust_yazi,
                                alt_yazi=sinav.alt_yazi,
                                sayfa_duzeni=sinav.sayfa_duzeni,
                                user_id=user_id,
                                hangi_ders=sinav.hangi_ders,
                                tags=sinav.tags,
                                konular=sinav.konular)
            try:
                db.session.add(yeni_sinav)
                db.session.flush()
                db.session.refresh(yeni_sinav)
            except:
                db.session.rollback()
                return abort(500)
            
            bucket_sinav_kopyala(str(user_id), str(sinav.user_id), str(sinav.id), str(yeni_sinav.id), str(sinav.pdf_dosyasi),
                                        str(sinav.baslik), str(yeni_baslik))
            for x in sorular:
                rs = unquote(x.raw_soru)
                if current_app.config['S3_BUCKET_NAME'] in rs:
                    _rs = x.raw_soru
                    _rs = re.sub(r'.amazonaws.com%2Fpdfs%2F(.*?)%2Fgorseller%2F', f'.amazonaws.com%2Fpdfs%2F{str(user_id)}%2Fgorseller%2F', _rs)
                    gorseller = re.findall(f'.amazonaws.com%2Fpdfs%2F{str(user_id)}%2Fgorseller%2F(.*?)(.png|.jpg)', _rs)
                    for a in gorseller:
                        ad, uzanti = a
                        yeni = ad.replace(f'-{str(sinav.id)}-', f' {sinav.user_id}-{str(yeni_sinav.id)}-')
                        _rs = _rs.replace(ad + uzanti, yeni + uzanti)
                    soru = Soru(tip=x.tip,
                                sinav_id=yeni_sinav.id,
                                raw_soru=_rs)
                else:
                    soru = Soru(tip=x.tip,
                                sinav_id=yeni_sinav.id,
                                raw_soru=x.raw_soru)
                db.session.add(soru)
            sk = Sinav_Kopya(sinav_id=sinav.id,
                            user_id=user_id,
                            yeni_sinav_id=yeni_sinav.id)
            db.session.add(sk)
            sinav.kopyalama_sayi += 1
            sinav_sahibi.alkis += 3
            try:
                db.session.commit()
            except:
                db.session.rollback()
                return abort(500)
            return url_for('kredi.sinav_goster', id=yeni_sinav.id)


@kredi.post('/kilavuz_okuma_onayla')
def kilavuz_okuma_onayla():
    data = request.form
    if data['kilavuz_tipi'] == 'sinav_okuma':
        session['sinav_okuma_kilavuz_onay'] = True
        session.permanent = True
    return '', 200

@kredi.post('/kazanimlari_al')
def kazanimlari_al():
    sinif = request.form.getlist('sinif[]')
    sinif_ids = [Tag.query.filter_by(name=x).first_or_404().id for x in sinif]
    ders = request.form.get('ders')
    ders_query = Hangiders.query.filter_by(lang=session['lang_code']).filter_by(name=ders).first_or_404().id
    kazanimlar_base = db.session.query(Kazanim).filter(Kazanim.hangi_ders==ders_query)
    kazanimlar = []
    for x in sinif_ids:
        kz = kazanimlar_base.filter(Kazanim.tag == x).all()
        for y in kz:
            kazanimlar.append({'id': y.id, 'name': y.name})
    return jsonify(kazanimlar), 200 if len(kazanimlar) > 0 else abort(500)

@kredi.get('/logolari_al')
def logolari_al():
    logolar = Logo.query.filter_by(user_id=current_user.id).all()
    if len(logolar) > 0:
        logolar = [
            {
                'id': x.id,
                'name': x.okul_ad
            }
            for x in logolar
        ]
    return jsonify(logolar)

@kredi.post('/logo_kaydet')
def logo_kaydet():
    file = request.files.get('file')
    name = request.form.get('name')
    ad, _ext = os.path.splitext(file.filename.lower())
    if _ext not in dosya_turleri:
        return abort(500)
    picture_path = os.path.join(current_app.root_path, 'gecici', ad)
    file.save(picture_path)
    s3_yol = 'logo/' + str(current_user.id) + '-' + str(datetime.now().timestamp()) + _ext
    ext = _ext.strip('.')
    s3_client.upload_file(picture_path, os.environ['S3_NAME'], s3_yol, ExtraArgs={
        "ACL": "public-read",
        "CacheControl": "max-age=2000000,public",
        "Expires": "2030-09-01T00:00:00Z",
        "ContentType": f'image/{ext}'})
    os.remove(picture_path)
    _logo = Logo(okul_ad = name,user_id = current_user.id, uri=s3_yol)
    db.session.add(_logo)
    try:
        db.session.commit()
        return {'id': _logo.id, 'name': name}, 200
    except:
        s3_client.delete_object(Bucket=os.environ['S3_NAME'], Key=s3_yol)
        db.session.rollback()
        return abort(500)