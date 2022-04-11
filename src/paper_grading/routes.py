import os, json, ast, operator,\
        pathlib, concurrent.futures, pandas as pd
from src.paper_grading.forms import DenemeFormu, FormingFor, MyForm
from flask_login import current_user, login_required
from wtforms import FieldList, FormField
from src.paper_grading.utils import inferpic_temizle, tablo_hazirla, kazanimlari_tanimla, sonuclari_veritabanina_yaz,\
                                        kagit_temizle, tuple_olustur, \
                                        upload_papers, bilgileri_ver, klasor_olustur, cv2_resize, koordinat_goster, \
                                        adim_bir, adim_iki, kagit_goster, ardarda, detect_eyle2, bilgi_ekle, \
                                        detect_eyle, sorulariekle, puanlar, yanit_duzenle, sonuc_duzenle,\
                                        predictor
from src.models import User, Hangiders, Sinav
from flask import render_template, json, Blueprint, abort, url_for, flash, redirect, request, current_app, session
from src import db, celery
from werkzeug.utils import secure_filename
from src.kredi.utils import paper_grading_kullanim_bildir, kredi_hesapla, hesap
from src.main.utils import bildirim_gonder
from flask_babel import lazy_gettext as _l, get_locale

paper_grading = Blueprint('paper_grading', __name__)

dosya_turleri = ['.jpg','.jpeg', '.png','.pdf']

@paper_grading.route('/pg/kagit_sil', methods=['POST'])
def kagit_sil():
    kagit_temizle(str(current_user.id))
    return '', 200

@paper_grading.route('/pg/grade/', methods=['GET', 'POST'])
@paper_grading.route('/pg/giris/', methods=['GET', 'POST'])
def pg_main():
    form = DenemeFormu()
    dersler = db.session.query(Hangiders.name).filter_by(lang=str(get_locale()))
    dersler = [(ders[0], ders[0]) for ders in dersler.all()]
    form.ders.choices=dersler
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    if os.path.exists(path) and len(os.listdir(path)) > 1:
        sayi = 0
        for x in os.listdir(path):
            if x.startswith('Kağıt') and x.endswith('.png'):
                sayi += 1
        ihtar = sayi
    else:
        ihtar = 0
    if os.path.isfile(os.path.join(path, 'siraya_alindi.txt')):
        with open(os.path.join(path, 'siraya_alindi.txt'), 'w') as f:
            f.write('ilk')
        return redirect(url_for('main.pg_landing'))
    klasor_olustur(current_user.id)
    kredi = kredi_hesapla(current_user)

    return render_template('paper_grading/pg_upload.html', 
                            form=form, 
                            baslik=_l('Sınav Okut'), 
                            ihtar=ihtar, 
                            kredi=kredi if not kredi == None else 0)

@paper_grading.route('/pg/form_al', methods=['POST'])
def form_al():
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    pictures = request.files.getlist('pictures[]')
    form = request.form
    bilgiler = {'dil': form['dil'], 'magic_num': form['kacsayfa'],\
                'ders': form['ders'], 'email': current_user.email,\
                'sinav_id': form['kod']}
    if bilgiler['sinav_id'] != '':
        sinav = Sinav.query.filter_by(uuid=bilgiler['sinav_id']).first()
    else:
        sinav = None
    with open(os.path.join(path, 'bilgiler.json'), 'w') as f:
        json.dump(bilgiler, f)
    for picture in pictures:
        filename = secure_filename(picture.filename.lower())
        fn, uzanti = os.path.splitext(filename)
        if uzanti not in dosya_turleri:
            kagit_temizle(path)
            return abort(501)
        else:
            try:
                upload_papers(picture, form['kacsayfa'])
            except:
                flash(_l('Bir anda 500 kâğıttan fazlası yüklenemez.'), 'danger')
                return redirect(url_for("paper_grading.pg_main"))
    list1 = list()
    for goruntu in os.listdir(path):
        if goruntu.endswith(".png"):
            list1.append(goruntu)
    magic_num = int(form['kacsayfa'])
    tuple_olustur(path, list1, magic_num)
    detect_listesi1 = [os.path.join(path, x) for x in os.listdir(path) if x.endswith('.png') and int(x[:-4].replace('Kağıt ', '')) <= magic_num]
    sinav_duzeni = '' if sinav == None else sinav.sayfa_duzeni
    bilgi_ekle(path, ['sinav_duzeni'], [sinav_duzeni])
    detect_eyle(detect_listesi1, path, sinav_duzeni)
    return str(current_user.id), 200

@paper_grading.route('/pg/form/<int:sayi>', methods=['GET', 'POST'])
def cevap_anahtarlari(sayi):
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    if os.path.exists(os.path.join(path, 'siraya_alindi.txt')):
        return redirect(url_for('paper_grading.pg_main'))

    img_path = current_app.config['S3_BUCKET_NAME'] + f'inferpics/{str(current_user.id)}/Kağıt {sayi}_pred.webp'
    try:
        bilgiler = bilgileri_ver(path)
        magic_num = int(bilgiler['magic_num'])
    except:
        flash(_l('Sınav kâğıtları bulunamadı. Lütfen ilk önce sınav kâğıtlarını yükleyiniz.'), 'danger')
        return redirect(url_for('paper_grading.pg_main'))
    if sayi == 1:
        for i in range(1, magic_num + 1):
            try:
                kagit = os.path.join(path, f'Kağıt {i}.png')
                ardarda(os.path.join(path, f"Kağıt {i}.txt"), rakam=i)
                #lütfen burayı .webp olarak değiştirme.
                if not os.path.isfile(os.path.join(current_app.root_path, 'static/inferpics', str(current_user.id), f'Kağıt {i}_pred.png')):
                    kagit_goster(kagit, os.path.join(path, f'Kağıt {i}.txt'), i, session['lang_code'])
            except:
                flash(_l('Sınav kâğıtlarını Paper Grading kurallarına göre hazırladığınızdan emin olunuz.'), 'danger')
                return redirect(url_for('paper_grading.pg_main'))
    kagit = f'Kâğıt {sayi}' if session['lang_code'] == 'tr' else f'Paper {sayi}'
    with open(os.path.join(path, f'Kağıt {sayi}.txt'), 'r') as kgt:
        j = ast.literal_eval(kgt.read())

    sayac = 1
    uzunluk = len(j['Sorular'].keys())

    if sayi > 1:
        with open(os.path.join(path, f'kgt{sayi-1}_uzunluk.json'), 'r') as f:
            ksayi = json.load(f)
        sayac = ksayi + 1
    else:
        ksayi = 0

    soru_tipleri=[]
    for _, y in j['Sorular'].items():
        if y['Soru Tipi'] == 0:
            sayac = 2
            uzunluk -= 1
        elif y['Soru Tipi'] == 1:
            soru_tipleri.append(_l('Boşluk Doldurma'))
        elif y['Soru Tipi'] == 2:
            soru_tipleri.append(_l('Çoktan Seçmeli'))
        else:
            soru_tipleri.append(_l('Eşleştirme/Doğru Yanlış'))
    ##### ---- #####
    ## toplam soru sayısını bul, 100'e böl. her bir soru değerini çıkar. ##
    with open(os.path.join(path, f'kgt{magic_num}_uzunluk.json'), 'r') as toplam_soru:
        t_s = int(json.load(toplam_soru))
    t_s -= 1 #ad soyadı toplam sorudan çıkaralım.
    her_soru_puani = 100 / t_s
    her_soru_puani = int(round(her_soru_puani))
    ##### formdaki soru sayısını burada belirleyelim #####
    #FormingFor.soru = TextAreaField() beklenen cevabı değiştirebiliyorum, bi ara bakalım
    class NewForm(MyForm):pass
    NewForm.sorular = FieldList(FormField(FormingFor), min_entries=uzunluk)
    form = NewForm()
    gond = json.dumps(koordinat_goster(j,sayac, path, f'ca_{sayi-1}.json'))
    loaded_r = json.loads(gond)
    
    ca = pathlib.Path(os.path.join(path, f'ca_{sayi-1}.json'))
    if ca.exists():
        with open(os.path.join(path, f'ca_{sayi-1}.json'), 'r') as c:
            c = ast.literal_eval(c.read())
        for indeks, soru in enumerate(form.sorular):
            soru.label = f'Soru_{sayac}'
            soru.deger.render_kw = {"class": "form-control puan", "value": f"{c[indeks]['deger']}", "onfocus": "silinemez_sayi(this.id)"}
            soru.soru.render_kw = {"class": "form-control yanit","onfocus":f"karaktersay(this.id)", "value": f"{c[indeks]['soru']}"}
            sayac += 1
    else:
        for indeks, soru in enumerate(form.sorular):
            soru.label = f'Soru_{sayac}'
            soru.deger.render_kw = {"class": "form-control puan", "value": f"{her_soru_puani}", "onfocus": "silinemez_sayi(this.id)"}
            soru.soru.render_kw = {"class": "form-control yanit","onfocus":f"karaktersay(this.id)"}
            sayac += 1
    
    sinav = Sinav.query.filter_by(uuid=bilgiler['sinav_id']).first()
    
    eslestirme_uyarisi = False
    kazanimlar = []
    if bilgiler['sinav_id'] == '':
        eslestirme_uyarisi = '' # eğer kod girilmemişse yoksa bir uyarı çıkmasın.
    elif bilgiler['sinav_id'] != '' and sinav == None:
        eslestirme_uyarisi = True # kod girilmiş ama sinav bulunamamış
    else:
        kazanimlar = kazanimlari_tanimla(sinav, 'adlar')
        if not len(kazanimlar) == t_s:
            kazanimlar.clear()
            eslestirme_uyarisi = True
    bilgi_ekle(path, ['analiz_yapilsin'], ['true' if eslestirme_uyarisi == False else ''])

    ##### ---- #####
    ##### form gönderildiğinde beklenen cevapları json olarak kaydedelim #####
    if form.validate_on_submit():
        cevaplar = form.sorular.data
        cevaplar = json.dumps(cevaplar)
        with open(os.path.join(path, f"ca_{sayi-1}.json"), "w") as cvp1:
            cvp1.write(cevaplar)
        adim_bir(os.path.join(path, f"ca_{sayi-1}.json"), os.path.join(path, f"Kağıt {sayi}.txt"), int(sayi-1))
    ##### ---- #####
        if sayi < magic_num: 
            return redirect(url_for("paper_grading.cevap_anahtarlari", sayi=sayi+1))
        else:
            return redirect(url_for("paper_grading.b_onay"))
    return render_template('paper_grading/pg_show_img.html', form=form, 
                            img_path=img_path, 
                            kagit=kagit,
                            magic_num=magic_num,
                            baslik=kagit,
                            isIndex=True,
                            gond=loaded_r,
                            st=soru_tipleri,
                            ksayi=ksayi,
                            kazanimlar=kazanimlar,
                            eslestirme_uyarisi=eslestirme_uyarisi)

# girilen kazanımlar eşleşmediği zaman çağrılır
@paper_grading.post('/pg/kazanim_degisiklikleri')
def kazanim_degisiklikleri():
    istek = request.form.get('istek')
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    bilgiler = bilgileri_ver(path)
    if istek == 'devam':
        bilgi_ekle(path, ['sinav_id'], [''])
        return '', 200
    elif istek == 'sinav_id':
        id = bilgiler['sinav_id']
        return id, 200
    else:
        try:
            sinav = Sinav.query.filter_by(uuid=str(istek).upper()).first_or_404()
        except:
            return abort(404)
        inferpic_temizle(current_user.id)
        bilgi_ekle(path, ['sinav_id'], [str(istek).upper()])
        bilgi_ekle(path, ['sinav_duzeni'], [sinav.sayfa_duzeni])
        magic_num = int(bilgiler['magic_num'])
        detect_listesi1 = [os.path.join(path, x) for x in os.listdir(path) if x.endswith('.png') and int(x[:-4].replace('Kağıt ', '')) <= magic_num]
        silme = ['bilgiler.json', 'tuples.json']
        for x in os.listdir(path):
            if not x.endswith('.png') and not x in silme and os.path.isfile(os.path.join(path, x)):
                os.remove(os.path.join(path, x))
        detect_eyle(detect_listesi1, path, sinav.sayfa_duzeni)
        return str(current_user.id), 200

@paper_grading.get('/pg/verify')
@paper_grading.get('/pg/onay')
def b_onay():
    image_file = current_app.config['S3_BUCKET_NAME'] + current_user.image_file
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    if os.path.exists(os.path.join(path, 'siraya_alindi.txt')):
        return redirect(url_for('paper_grading.pg_main'))
    bilgiler = bilgileri_ver(path)
    magic_num = int(bilgiler['magic_num']) 
    sorulariekle(path, magic_num)
    gereken_dosyalar = [f'Kağıt {x}.txt' for x in [*range(1, magic_num + 1)]]
    
    soru_sayilari, images, son_onay_kagitlari = tablo_hazirla(path, magic_num, gereken_dosyalar, session['lang_code'])

    sorted_d = {r: son_onay_kagitlari[r] for r in sorted(son_onay_kagitlari.keys(), key=operator.itemgetter(6), reverse=False)}
    pandalar = pd.concat({k: pd.DataFrame.from_dict(v, 'index') for k, v in sorted_d.items()}, axis=0)

    html_str = pandalar.to_html(classes='table table-hover')

    bekle = False
    kredi_yetiyor_mu = False
    if os.path.exists(os.path.join(path, 'siraya_alindi_islemde.txt')):
        bekle = True
    if not bekle:
        kullanici_kredisi = kredi_hesapla(current_user)
        kagit_list = [x.startswith('Kağıt') and x.endswith('.png') for x in os.listdir(path)]
        kagit_sayisi = kagit_list.count(True)
        _, gereken_kredi = hesap(kagit_sayisi, magic_num, soru_sayilari['bd_sayisi'], soru_sayilari['cs_sayisi'], soru_sayilari['dy_sayisi'],soru_sayilari['e_sayisi'])
        bilgi_ekle(path, ['gereken_kredi', 'kagit_sayisi'], [gereken_kredi, kagit_sayisi])
        if gereken_kredi <= kullanici_kredisi:
            kredi_yetiyor_mu = True
    return render_template("paper_grading/pg_onay.html", 
                            tablo=html_str, 
                            baslik=_l('Onayla'), 
                            img_path=images, 
                            image_file=image_file,
                            bekle=bekle,
                            kredi_yetiyor_mu=kredi_yetiyor_mu)

@paper_grading.post('/durum_guncelleme')
def durum_guncelle():
    aydi = request.form.get('aydi')
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(aydi))
    if os.path.isfile(os.path.join(path, 'siraya_alindi_islemde.txt')):
        data = 'islemde'
    else:
        data = 'tamamlandi'
    return data

@paper_grading.post('/yukleme_guncelleme')
def yukleme_guncelle():
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    bilgiler = bilgileri_ver(path)
    if 'cevap_anahtari_detection' not in bilgiler or bilgiler['cevap_anahtari_detection'] == 'hata':
        return str(current_user.id), 500
    elif bilgiler['cevap_anahtari_detection'] == 'tamamlandi':
        return '', 200
    else:
        return abort(404)

@celery.task(queue='celery', retry_kwargs={'max_retries': 5})
def async_sonuc(sozluk):
    _id = sozluk['id']
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(_id))

    bilgiler = bilgileri_ver(path)
    magic_num = int(bilgiler['magic_num']) 
    kullanici_emaili = str(bilgiler['email'])

    user = User.query.filter_by(email=kullanici_emaili).first()

    duzenli_liste = [x for x in os.listdir(path) if x.endswith('.png') and 'Kağıt' in x]
    duzenli_liste = sorted(duzenli_liste, key=lambda x: int(''.join(filter(str.isdigit, x))))

    #multiprocessing. dikkat    
    yeniden_boyutlandir = [os.path.join(path, x) for x in duzenli_liste if int(os.path.basename(x)[:-4].replace('Kağıt ', '')) > magic_num]
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        executor.map(cv2_resize, yeniden_boyutlandir)

    detect_listesi = []
    for inferpic in duzenli_liste:
        numara = [int(s) for s in str(inferpic.split()) if s.isdigit()]
        numara = ''.join([str(i) for i in numara])
        if int(numara) > magic_num:
            detect_listesi.append(os.path.join(path, inferpic))

    detect_eyle2(detect_listesi,
                magic_num,
                path, 
                predictor,
                bilgiler['sinav_duzeni'])
    
    duzenli_txt_liste = [x for x in os.listdir(path) if x.endswith('.txt') and not 'siraya_alindi' in x]
    duzenli_txt_liste = sorted(duzenli_txt_liste, key=lambda x: int(''.join(filter(str.isdigit, x))))

    sorulariekle(path, magic_num)
    for dosya1 in duzenli_txt_liste:
        numara = [int(s) for s in str(dosya1.split()) if s.isdigit()]
        numara = ''.join([str(i) for i in numara])
        if int(numara) <= magic_num:
            pass
        else:
            adim_iki(dosya1, path=path)
    for dosya in duzenli_txt_liste:
        dosya_yol = os.path.join(path, dosya)
        puanlar(dosya_yol, path, sozluk['lang'])
    for dosya2 in duzenli_txt_liste:
        yanit_duzenle(dosya2, path)
    for dosya3 in duzenli_txt_liste:
        sonuc_duzenle(dosya3, path, sozluk['lang'])

    liste = list()
    for dosya in duzenli_txt_liste:
        liste.append(os.path.join(path,dosya))
    
    magic_num -= 1
    updated_dict = dict()
    if magic_num == 0:
        pass
    elif magic_num == 1:
        for y, x in enumerate(liste):
            with open(x, 'r') as f:
                j = ast.literal_eval(f.read())
            if j['Aidiyet'] == 0:
                updated_dict = dict()
                updated_dict.update(j)
            elif j['Aidiyet'] == magic_num:
                kagit = j['Kağıt Adı']
                kagit = kagit.replace('.png', '_updated.txt')
                updated_dict['Sorular'].update(j['Sorular'])
                with open(os.path.join(path, kagit), 'w') as f:
                    f.write(str(updated_dict))
    elif magic_num >= 2:
            for y, x in enumerate(liste):
                with open(x, 'r') as f:
                    j = ast.literal_eval(f.read())
                if j['Aidiyet'] == 0:
                    updated_dict = dict()
                    updated_dict.update(j)
                elif j['Aidiyet'] != 0 and j['Aidiyet'] < magic_num:
                    updated_dict['Sorular'].update(j['Sorular'])
                elif j['Aidiyet'] == magic_num:
                    kagit = j['Kağıt Adı']
                    kagit = kagit.replace('.png', '_updated.txt')
                    updated_dict['Sorular'].update(j['Sorular'])
                    with open(os.path.join(path, kagit), 'w') as f:
                        f.write(str(updated_dict))

    duzenli_txt_liste = [x for x in os.listdir(path) if x.endswith('.txt') and not 'siraya_alindi' in x]
    duzenli_txt_liste = sorted(duzenli_txt_liste, key=lambda x: int(''.join(filter(str.isdigit, x))))
    
    okunan_sinav = sonuclari_veritabanina_yaz(magic_num, path, user, duzenli_txt_liste, sozluk['lang'])
    
    bildirim_sozluk = {
        'baslik': {'tr': 'Sınavlarınız okundu!', 'en': 'Your exam has been graded!'},
        'data': {'tr': 'Sonuçları panelden görebilirsiniz.', 'en': 'You can view the results on the panel.'},
        'hedef': {'tr': '/pg/panel/sinavlar', 'en': '/pg/panel/exams'}
    }
    bildirim = {
        'baslik': bildirim_sozluk['baslik'][sozluk['lang']], 
        'data': bildirim_sozluk['data'][sozluk['lang']], 
        'hedef': bildirim_sozluk['hedef'][sozluk['lang']]
    }
    bildirim_gonder({'alici': user.id,'name': 'sinav_okutma_bitti', 'data': bildirim})
    
    dil = bilgiler['dil']
    ders = bilgiler['ders']

    brans = db.session.query(Hangiders).filter(Hangiders.name == ders).first()
    paper_grading_kullanim_bildir(path, okunan_sinav, user.id, magic_num, dil, brans.id)
    return '', 200

@paper_grading.route('/siraya_al', methods=['POST'])
def siraya_al():
    aydi = request.form.get('aydi')
    path = os.path.join(current_app.config['INFERFILES_PATH'], aydi)
    
    bilgiler = bilgileri_ver(path)

    kullanici_kredisi = kredi_hesapla(User.query.filter_by(id=int(aydi)).first_or_404())
    if bilgiler['gereken_kredi'] > kullanici_kredisi:
        return abort(413)
    else:
        with open(os.path.join(path,'siraya_alindi.txt'), 'w') as f:
            f.write('ilk')
        sozluk = {'id':current_user.id, 'lang': session['lang_code']}
        if os.environ['RUNNING_ON'] == 'localhost':
            async_sonuc(sozluk)
        else:
            async_sonuc.delay(sozluk)
        return '', 200
