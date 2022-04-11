from src.models import Kazanim, Okunansinav, Ogrenci, Okunansoru, Sinav, Inferfiles
import os, io, json, ast, cv2, random, Levenshtein, \
        torch, time, re, pathlib,\
        boto3, tempfile, sys, re
from pdf2image import convert_from_path
from datetime import datetime
from cv2 import IMWRITE_JPEG_QUALITY, IMWRITE_JPEG_OPTIMIZE, IMWRITE_WEBP_QUALITY
from PIL import Image
from scipy.spatial import distance as dist
from imutils import paths
from math import sqrt
from urllib.parse import parse_qs

from flask import current_app
from flask_login import current_user
from src import celery, db

s3_client = boto3.client('s3', aws_access_key_id=os.environ['S3_ACCESS_KEY'],\
                  aws_secret_access_key=os.environ['S3_SECRET_KEY'], \
                  region_name=os.environ['S3_REGION'])
s3 = boto3.resource('s3', aws_access_key_id=os.environ['S3_ACCESS_KEY'],\
                    aws_secret_access_key=os.environ['S3_SECRET_KEY'], \
                    region_name=os.environ['S3_REGION'])

def object_detection_yukle():
    path1 = os.path.join(os.path.dirname(__file__))
    cfg = get_cfg()
    cfg.merge_from_file(path1 + "/modeller/config.yaml")
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.9
    cfg.MODEL.WEIGHTS = path1 + "/modeller/r50.pth"
    cfg.MODEL.DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    predictor = DefaultPredictor(cfg)
    return predictor

if sys.argv and (sys.argv[-1] == 'obj' or sys.argv[-1] == 'celery' or os.environ['RUNNING_ON'] == 'localhost'):
    # sadece celery worker'lara import edelim
    from detectron2.engine import DefaultPredictor
    from detectron2.config import get_cfg
    from fastai.vision.all import load_learner
    from google.cloud import vision
    import numpy as np, pandas as pd

    predictor = object_detection_yukle()
    # predictor = ''
else:
    predictor = ''

def parse_kazanim_idler(sorular):
    liste = []
    bul = {'dy': 'Doğru Yanlış İfadesi', 'e': 'İlk Eş'}
    for x in sorular:
        soru = parse_qs(x.raw_soru)
        if x.tip != 'gorsel':
            try:
                liste.append(soru['kazanim_idler'][0].split(',') if not x.tip == 'coktan_secmeli' else [soru['kazanim_idler'][0].split(',')])
            except:
                if x.tip == 'coktan_secmeli':
                    liste.append([['0']])
                elif x.tip == 'bosluk_doldurma':
                    bosluk_sayisi = len(re.findall("[\_]+[^a-zA-Z0-9?., !]+[\_]", soru['Paragraf'][0]))
                    liste.append('0' * bosluk_sayisi)
                else:
                    ifade = bul['dy'] if x.tip == 'dogru_yanlis' else bul['e']
                    ifade_sayisi = len(soru[ifade])
                    liste.append('0' * ifade_sayisi)
    return liste

def tablo_hazirla(path, magic_num, gereken_dosyalar, lang):
    images = [] #s3'teki inferpics
    translations = {
        0: {'tr': 'Ad Soyad', 'en': 'Name Surname'},
        1: {'tr': 'Boşluk Doldurma', 'en': 'Gap Filling'},
        2: {'tr': 'Çoktan Seçmeli', 'en': 'Multiple Choice'},
        'dy': {'tr': 'Doğru Yanlış', 'en': 'True False'},
        'e': {'tr': 'Eşleştirme', 'en': 'Matching'},
        'soru': {'tr': 'Soru', 'en': 'Q'},
        'kagit': {'tr': 'Kağıt ', 'en': 'Paper '}
    }
    for i in range(1, magic_num + 1):
        images.append(current_app.config['S3_BUCKET_NAME'] + f'inferpics/{str(current_user.id)}/Kağıt {i}_pred.webp')
        son_onay_kagitlari = {}
        bd_sayisi = 0
        cs_sayisi = 0
        dy_sayisi = 0
        e_sayisi = 0
        for kait in os.listdir(path):
            if kait in gereken_dosyalar:
                with open(os.path.join(path, kait), 'r') as f:
                    j = ast.literal_eval(f.read())
                for y in j['Sorular'].values():
                    del y['Soru Koordinatları']
                    del y['Öğrenci Cevapları']
                    del y['Önizleme']
                    del y['Güven']
                    if y['Soru Tipi'] == 0:
                        y['Soru Tipi'] = translations[y['Soru Tipi']][lang]
                        y['Beklenen Cevaplar'] = ''
                        y['Soru Puanı'] = ''
                    elif y['Soru Tipi'] == 1:
                        y['Soru Tipi'] = translations[y['Soru Tipi']][lang]
                        bd_sayisi += 1
                    elif y['Soru Tipi'] == 2:
                        y['Soru Tipi'] = translations[y['Soru Tipi']][lang]
                        cs_sayisi += 1
                    else:
                        if dogru_yanlis_mi(y['Beklenen Cevaplar']):
                            #eğer doğru yanlış ise soru tipine doğru yanlış yazalım
                            y['Soru Tipi'] = translations['dy'][lang]
                            dy_sayisi += 1
                        else:
                            #eğer değilse eşleştirme yazalım
                            y['Soru Tipi'] = translations['e'][lang]
                            e_sayisi += 1
                duzgun_rakamlar = {'' if name == 'Soru 1' else translations['soru'][lang] + ' ' + str(int(name.replace('Soru ', '')) - 1): entry for name, entry in j['Sorular'].items()}
                k_adi = j['Kağıt Adı'].strip('.png')
                son_onay_kagitlari = {k_adi.replace(k_adi[:-1], translations['kagit'][lang]): duzgun_rakamlar}
    soru_sayilari = {'bd_sayisi': bd_sayisi, 'cs_sayisi': cs_sayisi, 'dy_sayisi': dy_sayisi, 'e_sayisi': e_sayisi}
    return soru_sayilari, images, son_onay_kagitlari

def kazanimlari_tanimla(sinav, istek):
    if istek == 'okunansinav':
        sorular = [x.okunan_sorular for x in sinav.ogrenciler]
        kazanimlar = [x.kazanimlar.all() for x in sorular[0]]
    else:
        sorular = sinav.sorular
        kazanimlar = parse_kazanim_idler(sorular)
        kazanimlar = [item for sublist in kazanimlar for item in sublist]
    
    if istek == 'adlar':
        names = []
        for x in kazanimlar:
            if type(x) == list:
                _names = []
                for y in x:
                    _names.append('null' if int(y) == 0 else Kazanim.query.filter_by(id=int(y)).first().name)
                names.append(_names)
            else:
                names.append('null' if int(x) == 0 else Kazanim.query.filter_by(id=int(x)).first().name)
        return names
    else:
        return kazanimlar

def sonuclari_veritabanina_yaz(magic_num, path, user, duzenli_txt_liste, lang):
    gereken_dosya = '.txt' if magic_num == 0 else '_updated.txt'
    bilgiler = bilgileri_ver(path)
    if bilgiler['sinav_id'] != '':
        sinav = Sinav.query.filter_by(uuid=str(bilgiler['sinav_id'])).first()
        _kazanimlar = kazanimlari_tanimla(sinav, 'idler')
        with open(os.path.join(path, f'kgt{magic_num+1}_uzunluk.json'), 'r') as f:
            ksayi = json.load(f)
        if not len(_kazanimlar) == ksayi - 1:
            bilgi_ekle(path, ['analiz_yapilsin'], ['false'])
            bilgiler['analiz_yapilsin'] = 'false'
    okunan_sinav = Okunansinav(
        user_id=user.id,
        lang=lang,
        sistemdeki_karsiligi=sinav.id if bilgiler['analiz_yapilsin'] == 'true' else None,
        kazanim_analizi=True if bilgiler['analiz_yapilsin'] == "true" else False,
        ad="Sınav" if lang == 'tr' else "Exam" + datetime.utcnow().strftime("%d-%m-%Y, %H:%M:%S")
    )
    db.session.add(okunan_sinav)
    db.session.flush()
    
    sonuc = 0
    for son in duzenli_txt_liste:
        if son.startswith('Kağıt') and son.endswith(gereken_dosya):
            with open(os.path.join(path, son), 'r') as f:
                j = ast.literal_eval(f.read())
            if 'Hata' in j['Sorular']:
                ogrenci = Ogrenci(
                    sinav_id=okunan_sinav.id,
                    ad_soyad = 'Hata: ' + j['Sorular']['Hata'],
                    toplam_puan = 0
                )
                db.session.add(ogrenci)
            else:
                sorular = {'Soru ' + str(int(name.replace('Soru ', '')) - 1): entry for name, entry in j['Sorular'].items()}
                for y in sorular.values():
                    if not 'Ad Soyad' in y and y['Sonuç'] == 'Doğru':
                        sonuc += y['Soru Puanı']
                sorular['Soru 0']['Sonuç'] = sonuc
                sayac = 0
                for x, y in sorular.items():
                    if 'Ad Soyad' in y:
                        ogrenci = Ogrenci(
                            sinav_id=okunan_sinav.id,
                            ad_soyad = y['Önizleme'],
                            ad_soyad_gercek = y['Ad Soyad'],
                            koordinat = str(y['Soru Koordinatları']),
                            toplam_puan = sonuc
                        )
                        db.session.add(ogrenci)
                        db.session.flush()
                    else:
                        soru = Okunansoru(
                            soru_sirasi = x,
                            ogrenci_id = ogrenci.id,
                            tip = y['Soru Tipi'],
                            koordinat = str(y['Soru Koordinatları']),
                            puan = y['Soru Puanı'],
                            beklenen_cevaplar = y['Beklenen Cevaplar'],
                            ogrenci_cevaplari = y['Öğrenci Cevapları'],
                            onizleme = y['Önizleme'],
                            guven = y['Güven'],
                            sonuc = True if y['Sonuç'] == 'Doğru' else False
                        )
                        if bilgiler['analiz_yapilsin'] == 'true':
                            if not type(_kazanimlar[sayac]) == list and not (_kazanimlar[sayac]) == '0':
                                soru.kazanimlar.append(Kazanim.query.filter_by(id=int(_kazanimlar[sayac])).first())
                            else:
                                for x in _kazanimlar[sayac]:
                                    if not x == '0':
                                        soru.kazanimlar.append(Kazanim.query.filter_by(id=int(x)).first())
                        ogrenci.okunan_sorular.append(soru)
                        db.session.add(soru)
                        sayac += 1
                sonuc = 0
    s3_bucket = s3.Bucket(os.environ['S3_NAME'])
    inf_liste = s3_bucket.objects.filter(Prefix=f"inferpics/{str(user.id)}").limit(magic_num+1)
    s3_name=os.environ['S3_NAME']
    for x in inf_liste:
        yeni_ad = os.path.basename(x.key).strip(".webp") + "_" + str(time.time()).replace(".", "-") + ".webp"
        s3.Object(os.environ['S3_NAME'], f"inferpics/{str(user.id)}/{str(okunan_sinav.id)}/{yeni_ad}").copy_from(CopySource=f'{s3_name}/{x.key}', ACL='public-read')
        db.session.add(
            Inferfiles(
                name = yeni_ad,
                sinav_id = okunan_sinav.id
            )
        )
    try:
        db.session.commit()
        return okunan_sinav
    except:
        db.session.rollback()
        raise Exception

def inferpic_temizle(user_id):
    inferpic_path = os.path.join(current_app.root_path, 'static/inferpics', str(user_id))
    for z in os.listdir(inferpic_path):
        z = os.path.join(inferpic_path, z)
        if os.path.isfile(z):
            os.remove(z)

def kagit_temizle(user_id):
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(user_id))
    if os.path.isfile(os.path.join(path, 'siraya_alindi_islemde.txt')):
        raise Exception
    else:
        for x in os.listdir(path):
            x = os.path.join(path, x)
            if os.path.isfile(x):
                os.remove(x)
        for y in os.listdir(os.path.join(path, 'onizleme')):
            y = os.path.join(os.path.join(path, 'onizleme'), y)
            if os.path.isfile(y):
                os.remove(y)
        inferpic_temizle(user_id)
        return '', 200

def tuple_olustur(path, liste_sorted, magic_num):
    magic_num=int(magic_num)
    sorted_list = sorted(liste_sorted, key=lambda x: int(''.join(filter(str.isdigit, x))))
    goruntuler = [tuple(sorted_list[i:i+magic_num]) for i in range(0, len(sorted_list), magic_num)]
    gorlist = list()
    for gor in goruntuler:
        gor = list(gor)
        gorlist.append(gor)
    yenilist = list()
    for ns in gorlist:
        for hs in enumerate(ns):
            yenilist.append(hs)
    with open(os.path.join(path, 'tuples.json'), 'w') as f:
        json.dump(yenilist,f)

@celery.task(queue='pdf')
def parse_pdf(path, dosya, magic_num):
    with tempfile.TemporaryDirectory() as temp:
        images_from_path = convert_from_path(dosya, output_folder=temp)
        for picture in images_from_path[int(magic_num):]:
            tum_kagitlar = list(paths.list_images(path))
            kagit_sayisi = int(len(tum_kagitlar)) + 1
            picture_ad = f"Kağıt {kagit_sayisi}"
            picture_path = os.path.join(path, picture_ad)
            picture_full = picture_path + '.png'
            #picture = picture.convert(mode='P', palette=Image.ADAPTIVE)
            picture.save(picture_full)
        os.remove(dosya)
        list1 = [goruntu for goruntu in os.listdir(path) if goruntu.endswith('.png')]
        tuple_olustur(path, list1, magic_num)
        os.remove(os.path.join(path, 'siraya_alindi_islemde.txt'))
        return '', 200

def upload_papers(picture, magic_num):
    ##productiona geçerken popplerı yüklemeyi unutma.
    ##apt-get install -y poppler-utils
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    tum_kagitlar = list(paths.list_images(path))
    kagit_sayisi = int(len(tum_kagitlar)) + 1
    picture_ad, _ext = os.path.splitext(picture.filename)
    if _ext == '.pdf':
        pdfadi = datetime.now()
        pdfdosyasi = os.path.join(current_app.root_path, 'gecici', f'{current_user.id}-{pdfadi}.pdf')
        picture.save(pdfdosyasi)
        with tempfile.TemporaryDirectory() as temp:
            images_from_path = convert_from_path(pdfdosyasi, thread_count=2, output_folder=path)
            if len(images_from_path) + len(tum_kagitlar) > 500:
                raise Exception
            else:
                for picture in images_from_path[:int(magic_num)]:
                    tum_kagitlar = list(paths.list_images(path))
                    kagit_sayisi = int(len(tum_kagitlar)) + 1
                    picture_ad = f"Kağıt {kagit_sayisi}"
                    picture_path = os.path.join(path, picture_ad)
                    picture_full = picture_path + '.png'
                    picture.save(picture_full)
                with open(os.path.join(path, 'siraya_alindi_islemde.txt'), 'w') as f:
                    f.write('siraya_alindi_islemde')
                parse_pdf.delay(path, pdfdosyasi, magic_num)
    else:
        picture_ad = f"Kağıt {kagit_sayisi}"
        picture_path = os.path.join(path, picture_ad)
        picture_full = picture_path + '.png'
        picture.save(picture_full)

def bilgileri_ver(path):
    with open(os.path.join(path, 'bilgiler.json'), 'r') as f:
        f = f.read()
        sozluk = json.loads(f)
    return sozluk

def klasor_olustur(id):
    path = pathlib.Path(os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id)))
    if not path.exists():
        os.makedirs(path)
        os.makedirs(os.path.join(path, 'onizleme'))
    static_path = pathlib.Path(os.path.join(current_app.root_path, "static/inferpics", str(current_user.id)))
    if not static_path.exists():
        os.makedirs(static_path)

def cv2_resize(picture):
    picture_ad, _ = os.path.splitext(picture)
    picture = cv2.imread(picture, 0)
    (w, h) = picture.shape
    if not (w, h) == (2000, 3000):
        resized = cv2.resize(picture, (2000,3000), interpolation=cv2.INTER_LANCZOS4)
        cv2.imwrite(f'{picture_ad}.png', resized)

def jpglestir(path):
    for x in os.listdir(path):
        dosya = os.path.join(path, x)
        scale_percent = 40
        src = cv2.imread(dosya, cv2.IMREAD_UNCHANGED)

        #calculate the scale percent of original dimensions
        width = int(src.shape[1] * scale_percent / 100)
        height = int(src.shape[0] * scale_percent / 100)

        # dsize
        dsize = (width, height)

        #pngden jpgye
        yalin_ad = os.path.basename(dosya)
        jpg_ad = yalin_ad.replace('.png', '.jpg')
        jpg_yolu = os.path.join(path, jpg_ad)

        # resize image
        output = cv2.resize(src, dsize)
        cv2.imwrite(f'{jpg_yolu}', output, [int(cv2.IMWRITE_JPEG_QUALITY), 70,IMWRITE_JPEG_OPTIMIZE])
        os.remove(dosya)

def crop_image(filename, pixel_value=255):
    gray = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
    crop_rows = gray[~np.all(gray == pixel_value, axis=1), :]
    cropped_image = crop_rows[:, ~np.all(crop_rows == pixel_value, axis=0)]
    cv2.imwrite(f'{filename}', cropped_image)

def onizleme_kucult(filename):
    scale_percent = 30
    src = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
    #calculate the 50 percent of original dimensions
    width = int(src.shape[1] * scale_percent / 100)
    height = int(src.shape[0] * scale_percent / 100)

    # dsize
    dsize = (width, height)

    # resize image
    output = cv2.resize(src, dsize)
    webp_ad = filename.replace(".jpg", ".webp")
    cv2.imwrite(webp_ad, output, [int(IMWRITE_WEBP_QUALITY), 85])
    return webp_ad

def onizleme_yukle(path, kagit_adi, _ad, roi):
    kagit_adi, _ = kagit_adi.split('.png')
    onizleme_adi = str(kagit_adi) + '-' + _ad + '-' + str(time.time()).replace('.', '-')
    cv2.imwrite(os.path.join(path, 'onizleme',f'{onizleme_adi}.jpg'), roi)
    onizleme_yol = os.path.join(path, 'onizleme', f'{onizleme_adi}.jpg')
    crop_image(onizleme_yol)
    dosya_yolu = onizleme_kucult(onizleme_yol)
    s3_yol = "onizlemeler/" + str(path.split("/")[-1]) + "/" + onizleme_adi + ".webp"
    s3_client.upload_file(dosya_yolu, os.environ['S3_NAME'], s3_yol, ExtraArgs={
        "ACL": "public-read",
        "CacheControl": "max-age=2000000,public",
        "Expires": "2030-09-01T00:00:00Z",
        "ContentType": 'image/webp'})
    os.remove(dosya_yolu)
    onizleme_yol = current_app.config['S3_BUCKET_NAME'] + s3_yol
    return onizleme_adi, onizleme_yol

def koordinat_goster(j, baslangic_sayisi, path, ca):
    js = ''
    path = pathlib.Path(os.path.join(path, ca))

    for x in j['Sorular'].items():
        if j['Kağıt Adı'] == 'Kağıt 1.png' and x[0] == 'Soru 1':
            pass
        else:
            bir, iki, uc, dort = x[1]['Soru Koordinatları']
            uc = uc - bir
            dort = dort - iki
            soru_num = f'Soru{baslangic_sayisi}'
            soru_id = "'" + soru_num + "'"
            sozluk = f'%id: {soru_id}, element: {soru_num}, x: {bir}, y: {iki}, width: {uc}, height: {dort}_'
            if path.exists():
                renk = '40, 200, 100, 0.0'
            else:
                renk = '40, 200, 100, 0.3'
            gond = f'var {soru_num} = document.createElement(?div?);\
            {soru_num}.style.backgroundColor = ?rgba({renk})?;\
            {soru_num}.style.cursor = ?pointer?;\
            {soru_num}.setAttribute(?id?,?#Gomulu{soru_num}?);\
            {soru_num}.setAttribute(?type?,?button?);\
            {soru_num}.setAttribute(?data-toggle?,?modal?);\
            {soru_num}.setAttribute(?data-target?, ?#Soru*{baslangic_sayisi}?);\
            hEl.addElement({sozluk});'
            gond = gond.replace('"','')
            js += str(gond)
            baslangic_sayisi+=1
    js = js.replace('%','{')
    js = js.replace('_','}')
    js = js.replace('*','_')
    js = js.replace('?','"')
    return js

def adim_bir(ca_dosyasi, txtdosyasi, aidiyet):
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    with open(ca_dosyasi, 'r') as f:
        krek = json.loads(f.read())
    
    for x in krek:
        del x['csrf_token']
        x['Beklenen Cevaplar'] = x['soru']
        del x['soru']
        x['Soru Puanı'] = x['deger']
        del x['deger']
    
    if os.path.isfile(os.path.join(path, txtdosyasi)) and aidiyet != 0:
        with open(os.path.join(path, txtdosyasi), 'r') as f:
            sonur = ast.literal_eval(f.read())
        rakam = [int(s) for s in list(sonur['Sorular'].keys())[0].split() if s.isdigit()]
        rakam = [''.join([str(i) for i in rakam])]
        sayar = int(rakam[0])
    else:
        sayar = 1
        with open(os.path.join(path, txtdosyasi), 'r') as n:
            sonur = ast.literal_eval(n.read())
        for u, b in sonur['Sorular'].items():
            if b['Soru Tipi'] == 0:
                sayar = 2

    liz = list()
    for s, d in enumerate(krek):
        liz.append(f'Soru {sayar}')
        sayar += 1
    asil = dict()
    for x,y in enumerate(krek):
        asil[x] = {liz[x]: y}
    asil_list = list()
    for x, y in asil.items():
        asil_list.append(y)
    sumbul = dict()
    for y in asil_list:
        sumbul.update(y)

    if sonur['Aidiyet'] == aidiyet:
        for x, y in sonur['Sorular'].items():
            if y['Soru Tipi'] == 0:
                pass
            else:
                y['Beklenen Cevaplar'] = sumbul[x]['Beklenen Cevaplar'].lower()
                y['Soru Puanı'] = sumbul[x]['Soru Puanı']
    with open(os.path.join(path, txtdosyasi), 'w') as m:
        m.write(str(sonur))

def adim_iki(txtdosyasi, path):
    with open(os.path.join(path, txtdosyasi), 'r') as n:
        sonur = ast.literal_eval(n.read())
    if 'Hata' in sonur['Sorular']:
        pass
    else:
        aidiyet = sonur['Aidiyet']
        with open(os.path.join(path, f'ca_{aidiyet}.json'), 'r') as f:
            krek = json.loads(f.read())

        sayi = list(sonur['Sorular'].keys())[0]

        rakam = [int(s) for s in sayi.split() if s.isdigit()]
        rakam = [''.join([str(i) for i in rakam])]
        rakam = int(rakam[0])

        sayar = rakam
        for u, b in sonur['Sorular'].items():
            if b['Soru Tipi'] == 0:
                sayar += 1

        for x in krek:
            del x['csrf_token']
            x['Beklenen Cevaplar'] = x['soru']
            del x['soru']
            x['Soru Puanı'] = x['deger']
            del x['deger']

        liz = list()
        for s, d in enumerate(krek):
            liz.append(f'Soru {sayar}')
            sayar += 1
        asil = dict()
        for x,y in enumerate(krek):
            asil[x] = {liz[x]: y}
        asil_list = list()
        for x, y in asil.items():
            asil_list.append(y)
        sumbul = dict()
        for y in asil_list:
            sumbul.update(y)

        for x, y in sonur['Sorular'].items():
            if y['Soru Tipi'] == 0:
                pass
            else:
                y['Beklenen Cevaplar'] = sumbul[x]['Beklenen Cevaplar'].lower()
                y['Soru Puanı'] = sumbul[x]['Soru Puanı']
        with open(os.path.join(path, txtdosyasi), 'w') as m:
            m.write(str(sonur))

def kagit_goster(imgdosya, tahmintxt, rakam, lang):
    path = os.path.split(tahmintxt)[0]
    with open(os.path.join(path, tahmintxt), 'r') as n:
        cnt = ast.literal_eval(n.read())
    coords = list()
    for x in cnt['Sorular'].values():
        coords.append([int(u) for u in x['Soru Koordinatları']])

    labels = list()
    for x in cnt['Sorular'].keys():
        labels.append(x)

    sayac = 1
    if rakam == 1:
        for x, y in enumerate(labels):
            labels[x] = str(sayac)
            sayac += 1
    else:
        with open(os.path.join(path, f'kgt{rakam-1}_uzunluk.json'), 'r') as f:
            sayac = json.load(f)
        sayac += 1
        for x, y in enumerate(labels):
            labels[x] = str(sayac)
            sayac += 1

    soru_tip = list()
    for x in cnt['Sorular'].values():
        j = x['Soru Tipi']
        soru_tip.append(j)

    tip_sozluk = {'tr': {0: 'AS', 1: 'BD', 2: 'CS', 3: 'DY'}, 'en': {0: 'NS', 1: 'GF', 2: 'MC', 3: 'TF'}} 
    ad_soyad = {'tr': 'AD SOYAD', 'en': 'NAME SURNAME'}
    yeni_soru_tip = list()
    for idx, tip in enumerate(soru_tip):
        ekle = ad_soyad[lang] if (int(labels[idx]) - 1 == 0) else str(int(labels[idx]) - 1) + "-" + tip_sozluk[lang][tip]
        yeni_soru_tip.append(ekle)

    im = cv2.imread(imgdosya, 0)
    for idx, item in enumerate(coords):
        x, y, w, h = item
        # image = cv2.rectangle(im, (x, y), (w, h), (226,254,224), 2)
        text = yeni_soru_tip[idx]
        (text_width, text_height) = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.5, thickness=2)[0]
        text_offset_x = x
        text_offset_y = y
        box_coords = ((text_offset_x, text_offset_y), (text_offset_x + text_width + 2, text_offset_y - text_height - 1))
        cv2.rectangle(im, box_coords[0], box_coords[1], (226,254,224), cv2.FILLED)
        imag = cv2.putText(im, text, (text_offset_x, text_offset_y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, color=(0,0,0), thickness=2)
    impath = os.path.join(current_app.root_path, "static/inferpics", str(current_user.id))
    isim = os.path.basename(imgdosya)
    isim = isim.replace('.png', '_pred.png')
    yol = os.path.join(impath, isim)
    cv2.imwrite(yol, imag)

    s3_isim = os.path.basename(imgdosya).replace('.png', '_pred.webp')
    s3_kaydetme_yolu = os.path.join(impath, s3_isim)
    cv2.imwrite(s3_kaydetme_yolu, imag, [int(IMWRITE_WEBP_QUALITY), 60])
    # yeni_isim = "Kağıt -" +  str(time.time().replace(".", "-")) + ".webp"
    s3_yol = f'inferpics/{str(current_user.id)}/{s3_isim}'
    s3_client.upload_file(s3_kaydetme_yolu, os.environ['S3_NAME'], s3_yol, ExtraArgs={
        "ACL": "public-read",
        "CacheControl": "max-age=2000000,public",
        "Expires": "2030-09-01T00:00:00Z",
        "ContentType": 'image/webp'})
    os.remove(s3_kaydetme_yolu)

def ardarda(sorus, rakam):
    path = os.path.join(current_app.config['INFERFILES_PATH'], str(current_user.id))
    with open(sorus, 'r') as f:
        j = ast.literal_eval(f.read())
    sorusayisi = len(j['Sorular'].keys())
    if rakam != 1:
        with open(os.path.join(path, f'kgt{rakam-1}_uzunluk.json'),'r') as onceki:
            onceki = int(json.loads(onceki.read()))
        sorusayisi += onceki
    with open(os.path.join(path, f'kgt{rakam}_uzunluk.json'),'w') as jek:
        json.dump(int(sorusayisi), jek)
        
## bu fonksiyonda (detect_eyle2) ilk önce detectron2 ile prediction
## daha sonra predictionların çevresini büyütme
## daha sonra öğretmenlerin girdiği cevap anahtarını
## referans alıp, yeni tahmin edilen kâğıtlardaki
## soru sırasını referanslara göre düzenleme yer almaktadır
## belki de bunlar daha verimli bir şekilde yazılabilir
## ama ben şu an böyle yazabildim

# calculate the minkowski distance between two vectors
def minkowski_distance(row1, row2):
	distance = 0.0
	for i in range(len(row1)-1):
		distance += dist.minkowski(row1[i], row2[i])
	return sqrt(distance)

def get_neighbors(train, test_row, num_neighbors):
	distances = list()
	for train_row in train:
		dist = minkowski_distance(test_row, train_row)
		distances.append((train_row, dist))
	distances.sort(key=lambda tup: tup[1])
	neighbors = list()
	for i in range(num_neighbors):
		neighbors.append(distances[i][0])
    
	return neighbors

def get_neighbors2(train, test_row, num_neighbors, yenilist):
    distances = list()
    for train_row in train:
        dist = minkowski_distance(test_row, train_row)
        distances.append((train_row, dist))
    distances.sort(key=lambda tup: tup[1])
    neighbors = list()
    #iğrenç gözüküyor ama yapacak bir şey yok
    for i in range(num_neighbors):
        neighbors.append(distances[i][0])
    if neighbors in yenilist:
        neighbors.clear()
        neighbors.append(distances[i+1][0])
    if neighbors in yenilist:
        neighbors.clear()
        neighbors.append(distances[i+2][0])
    if neighbors in yenilist:
        neighbors.clear()
        neighbors.append(distances[i+3][0])
    if neighbors in yenilist:
        neighbors.clear()
        neighbors.append(distances[i+4][0])
    if neighbors in yenilist:
        neighbors.clear()
        neighbors.append(distances[i+5][0])
    if neighbors in yenilist:
        neighbors.clear()
        neighbors.append(distances[i+6][0])
    if neighbors in yenilist:
        neighbors.clear()
        neighbors.append(distances[i+7][0])
    return neighbors

def koordinat_duzelt(referans, pred_classes, sinif_ve_koordinat):
    yenilist=list()
    sayach = 0
    for x in referans:
        bir = get_neighbors([x[1] for x in sinif_ve_koordinat], referans[sayach], 1)
        yenilist.append(bir)
        sayach += 1

    if any(yenilist.count(x) > 1 for x in yenilist):
        #eğer yenilist içinde kendini tekrar eden koordinat varsa
        yenilist=list()
        sayach = 0
        for y in referans:
            bir = get_neighbors2([x[1] for x in sinif_ve_koordinat], referans[sayach], num_neighbors=1, yenilist=yenilist)
            yenilist.append(bir)
            sayach += 1
    else:
        #yoksa dewamke
        pass

    gecici_liste = [item for sublist in yenilist for item in sublist]

    geciciliste=[]
    d2_sorted = [None] * len(gecici_liste)

    for x in gecici_liste:
        gercek = x[0]
        ilk_aralik = gercek - 20
        son_aralik = gercek + 20
        for y in gecici_liste:
            if gecici_liste.index(y) != 0:
                if y[0]>ilk_aralik and y[0]<son_aralik:
                    if y in geciciliste:
                        pass
                    else:
                        geciciliste.append([gecici_liste.index(y),y])

        sira = []
        sayi = []

        for x, y in geciciliste:
            sira.append(x)
            sayi.append(y)

        sayi.sort(key=lambda x:(x[1],x[0]))
        sira.sort()

        merged_list = [(sira[i], sayi[i]) for i in range(0, len(sira))] 

        for x in merged_list:
            if x[1] in gecici_liste:
                d2_sorted.pop(x[0])
                d2_sorted.insert(x[0],x[1])
        geciciliste.clear()
    
    d2_sorted.pop(0)
    d2_sorted.insert(0, gecici_liste[0])
    return d2_sorted

def sinif_duzelt(d2_sorted, sinif_ve_koordinat):
    yenisinif=list()
    for x in d2_sorted:
        for y in sinif_ve_koordinat:
            if y[1] == x:
                yenisinif.append(y[0])
    return yenisinif

def detect_eyle2(inferpic_listesi, magic_num, path, predictor, sayfa_duzeni):
    referans_listesi = []
    for i in range(1, magic_num + 1):
        with open(os.path.join(path, f'Kağıt {i}.txt'), 'r') as o:
            j = ast.literal_eval(o.read())
        
        referans = list()
        for x in j['Sorular'].values():
            referans.append(x['Soru Koordinatları'])

        referans_listesi.append(referans)

    for inferpic in inferpic_listesi:
        picad = os.path.basename(inferpic)
        inferpic = cv2.imread(inferpic)
        outputs = predictor(inferpic)
        
        sozluk = _aidiyet(path, picad)
        aidiyet = sozluk['aidiyet']
        list6 = output_duzenle(outputs, aidiyet, sayfa_duzeni)

        sayac1 = 1
        soru_adlari = []
        for ds in range(len(list6)):
            soru_adlari.append("Soru " + str(sayac1))
            sayac1 += 1

        pred_boxes=[]
        pred_classes=[]
        for x in list6:
            pred_boxes.append(x[0])
            pred_classes.append(x[1])

        for x in range(1, aidiyet + 2):
            sinif_ve_koordinat = [(i, j) for i, j in zip(pred_classes, pred_boxes)]

            if len(referans_listesi[aidiyet]) != len(pred_boxes):
                sorular = {'Hata': f'{picad}'}
            else:
                d2_sorted = koordinat_duzelt(referans=referans_listesi[aidiyet], pred_classes=pred_classes, 
                                sinif_ve_koordinat=sinif_ve_koordinat)
                yenisinif = sinif_duzelt(d2_sorted=d2_sorted, sinif_ve_koordinat=sinif_ve_koordinat)
                
                birlestir = list(zip(d2_sorted, yenisinif))
                birlestir = yakin_duzelt(birlestir)
                
                sorular=dict()
                for ns in range(len(soru_adlari)):
                    sorular[soru_adlari[ns]] = {'Soru Koordinatları': birlestir[ns][0],
                                                'Soru Tipi': birlestir[ns][1], 
                                                'Soru Puanı' : list(), 
                                                'Beklenen Cevaplar' : list(), 
                                                'Öğrenci Cevapları' : list(),
                                                'Önizleme' : list(),
                                                'Güven': str()}
        
        jsoneyle(sorular, picad, inferpic_dir=path)

def yakin_duzelt(liste):
    duzeltildi = []
    for idx, x in enumerate(liste):
        if not x in duzeltildi:
            gercek = x[0][3]
            ilk_aralik = gercek - 15
            son_aralik = gercek + 15
            duzelt = []
            gercek_idler = []
            duzelt.append(x)
            gercek_idler.append(idx)
            for idx2, y in enumerate(liste):
                if y[0][3] > ilk_aralik and y[0][3] < son_aralik and idx != idx2 and not y in duzeltildi:
                    duzelt.append(y)
                    gercek_idler.append(idx2)
                    duzeltildi.append(x)
                    duzeltildi.append(y)
            duzelt.sort(key = lambda o: o[0][0], reverse=False)
            for idx3, o in enumerate(duzelt):
                liste.insert(gercek_idler[idx3], o)
                liste.pop(gercek_idler[idx3] + 1)
    return liste

def percentage(part, whole):
  return 100 * float(part)/float(whole)

def ikiye_ayir_duzenle(liste):
    sol = []
    sag = []
    
    yuzdeler = [percentage((x[0][0] + x[0][2] / 2), 3000) for x in liste]
    
    for idx, x in enumerate(yuzdeler):
        avg = (liste[idx][0][0] + liste[idx][0][2]) / 2
        if x < 49:
            sol.append(liste[idx])
        else:
            sag.append(liste[idx])
    
    sol.sort(key = lambda x: x[0][1], reverse=False)
    sol = yakin_duzelt(sol)
    sag.sort(key = lambda x: x[0][1], reverse=False)
    sag = yakin_duzelt(sag)

    son = sol + sag
    return son

def output_duzenle(outputs, aidiyet, sayfa_duzeni):
    array3 = outputs["instances"].pred_boxes.tensor.cpu().numpy()
    array6 = outputs["instances"].pred_classes.cpu().numpy()
    int_list = np.round(array3)

    #koordinatların çevresini büyütme 
    new_list7 = []
    for p in np.array(int_list)[:,3]:
        p = min(3000, p+5)
        new_list7.append(p)

    new_list6 = []
    for u in np.array(int_list)[:,2]:
        u = min(2000, u+5)
        new_list6.append(u)

    new_list5 = []
    for y in np.array(int_list)[:,1]:
        y = max(0, y-5)
        new_list5.append(y)

    new_list4 = []
    for x in np.array(int_list)[:,0]:
        x = max(0, x-5)
        new_list4.append(x)

    int_list[:,0] = new_list4
    int_list[:,1] = new_list5
    int_list[:,2] = new_list6
    int_list[:,3] = new_list7
    #koordinatların çevresini büyütme 

    for index in int_list[0:len(int_list)]:
        index = tuple(index)
    list6 = list(zip(int_list.tolist(), array6))

    if aidiyet == 0:
        list6 = sorted(list6, key = lambda x: x[0][1], reverse=False)
        ad_soyad = list6[0]
        list6.pop(0)

    for idx, x in enumerate(list6):
        if (x[1] == 0 and aidiyet != 0) or (aidiyet == 0 and idx != 0 and x[1] == 0):
            list6.pop(idx)
    
    if sayfa_duzeni == 'cift-sutun':
        list6 = ikiye_ayir_duzenle(list6)
    else:
        list6 = yakin_duzelt(sorted(list6, key = lambda x: x[0][1], reverse=False))
    
    if aidiyet == 0:
        list6.insert(0, ad_soyad)
        return list6
    else:
        return list6

def _aidiyet(path, picad):
    with open(os.path.join(path, 'tuples.json'), 'r') as f:
        tuples = [tuple(x) for x in json.loads(f.read())]
    durali = [x for x, y in enumerate(tuples) if y[1] == str(f'{picad}')]
    dural = int(durali[0])
    kagit_adi = tuples[dural][1]
    aidiyet = tuples[dural][0]
    return {'kagit_adi': kagit_adi, 'aidiyet': aidiyet}

@celery.task(queue='obj', autoretry_for=(RuntimeError,), retry_kwargs={'max_retries': 5})
def _detect(gerekli_bilgiler):
    for inferpic in gerekli_bilgiler['inferpic_listesi']:
        inferpic_dir, picad = os.path.split(inferpic)
        sozluk = _aidiyet(inferpic_dir, picad)
        
        cv2_resize(os.path.join(inferpic_dir,inferpic))
        inferpic = cv2.imread(inferpic)
        outputs = predictor(inferpic)

        try:
            list6 = output_duzenle(outputs, sozluk['aidiyet'], gerekli_bilgiler['sayfa_duzeni'])
        except:
            bilgi_ekle(inferpic_dir, ['cevap_anahtari_detection'], ['hata'])
            raise Exception('soru tespit edilemedi')
        
        sayac1 = 1
        soru_adlari = []
        for _ in range(len(list6)):
            soru_adlari.append("Soru " + str(sayac1))
            sayac1 += 1

        pred_boxes=[]
        pred_classes=[]
        for x in list6:
            pred_boxes.append(x[0])
            pred_classes.append(x[1])

        sorular=dict()
        for ns in range(len(soru_adlari)):
            sorular[soru_adlari[ns]] = {'Soru Koordinatları': list(pred_boxes[ns]),
                                        'Soru Tipi': pred_classes[ns], 
                                        'Soru Puanı' : list(), 
                                        'Beklenen Cevaplar' : list(), 
                                        'Öğrenci Cevapları' : list(),
                                        'Önizleme' : list(),
                                        'Güven': str()}
                                        
        jsoneyle(sorular, picad, inferpic_dir)
    bilgi_ekle(inferpic_dir, ['cevap_anahtari_detection'], ['tamamlandi'])
    return '', 200

def bilgi_ekle(path, key, value):
    bilgiler = bilgileri_ver(path)
    for idx, x in enumerate(key):
        bilgiler[x] = value[idx]
    with open(os.path.join(path, 'bilgiler.json'), 'w') as f:
        json.dump(bilgiler, f)

def detect_eyle(inferpic_listesi, path, sayfa_duzeni):
    bilgi_ekle(path, ['cevap_anahtari_detection'], ['isleme_alindi'])
    gerekli_bilgiler = {'inferpic_listesi': inferpic_listesi, 'sayfa_duzeni': sayfa_duzeni}
    if os.environ['RUNNING_ON'] == 'localhost':
        _detect(gerekli_bilgiler)
    else:
        _detect.apply_async((gerekli_bilgiler,))

def jsoneyle(sonuclar, picad, inferpic_dir):
    sozluk = _aidiyet(inferpic_dir, picad)
    kagit_json = {'Kağıt Adı': sozluk['kagit_adi'], 'Aidiyet': sozluk['aidiyet'], 'Sorular': sonuclar}
    txt = os.path.join(inferpic_dir, f'{picad.strip(".png")}.txt')
    with open(txt, "w") as asil_dict:
        asil_dict.write(str(kagit_json))
    os.chmod(txt, 0o777)

def sorulariekle(path, magic_num):
    #soru sayılarını aidiyetlerine göre yeniden düzenler.
    duzenli_txt_liste = []
    for duzenli_txt in os.listdir(path):
        if duzenli_txt.endswith('.txt') and not 'siraya_alindi' in duzenli_txt:
            duzenli_txt_liste.append(duzenli_txt)
    duzenli_txt_liste = sorted(duzenli_txt_liste, key=lambda x: int(''.join(filter(str.isdigit, x))))

    for i in range(1, magic_num + 1):
        for x in duzenli_txt_liste:
            if x.endswith('.txt') and not 'siraya_alindi' in x:
                with open(os.path.join(path, x), 'r') as f:
                    j = ast.literal_eval(f.read())
                if j['Aidiyet'] > 0:
                    isimler = list(j['Sorular'].keys())
                    bul = int(j['Aidiyet'])
                    with open (os.path.join(path, f'kgt{bul}_uzunluk.json'), 'r') as p:
                        l = int(json.load(p))
                    for ind, val in enumerate(isimler):
                        val = f'Soru {l+1}'
                        isimler[ind] = val
                        l += 1
                    if not 'Hata' in j['Sorular']:
                        j['Sorular'] = {name: entry for name, entry in zip(isimler, j['Sorular'].values())}
                    with open(os.path.join(path, x), 'w') as r:
                        r.write(str(j))

#boşluk doldurmada büyük şekilde okuturken ortaya çıkan
#yeniden ölçekleme hatasını gidermek için yazdım.
def oranla(w):
    oran = 2.0
    while w * oran > 1024:
        oran -= 0.1
    return oran

def visionapi_post_image(client, path, filename, hint):
    with io.open(os.path.join(path, f'{filename}'), 'rb') as ad_oku:
        content = ad_oku.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image, image_context={"language_hints": [f"{str(hint)}"]})
    texts = response.text_annotations
    df = pd.DataFrame(columns=['locale', 'description'])
    for text in texts:
        df = df.append(dict(locale=text.locale, description=text.description), ignore_index=True)
    return df, response

def puanlar(textdosyasi, path, lang):
    ## fastai dosyaları
    path2 = os.path.join(os.path.dirname(__file__))
    gecerli_gecersiz = load_learner(os.path.join(path2, "modeller/gecerli_gecersiz.pkl"), cpu=False if torch.cuda.is_available() else True)
    dogru_yanlis = load_learner(os.path.join(path2, "modeller/dogru_yanlis.pkl"), cpu=False if torch.cuda.is_available() else True)
    eslestirme = load_learner(os.path.join(path2, "modeller/eslestirme.pkl"), cpu=False if torch.cuda.is_available() else True)
    abcde = load_learner(os.path.join(path2, "modeller/abcde.pkl"), cpu=False if torch.cuda.is_available() else True)
    client = vision.ImageAnnotatorClient()

    path1 = os.path.join(current_app.root_path, 'paper_grading/')
    resim_ad = os.path.basename(textdosyasi).replace(".txt", ".png")
    resim_yol = os.path.join(path, resim_ad)
    with open(textdosyasi, 'r') as f:
        j = ast.literal_eval(f.read())
    bilgiler = bilgileri_ver(path)
    dil = 'en-t-i0-handwrit' if bilgiler['dil'] == 'en' else bilgiler['dil']
    ## GOOGLE VISION DENEMESİ ##
    if 'Hata' in j['Sorular']:
        pass
    else:
        dy_translations = {
            'dogru': {'tr': 'dogru', 'en': 'true'},
            'yanlis': {'tr': 'yanlis', 'en': 'false'},
            'bos': {'tr': 'gecersiz/bos', 'en': 'invalid/empty'}
        }
        for soru, bilgi in j['Sorular'].items():
            xmin, ymin, xmax, ymax = bilgi['Soru Koordinatları']
            tip = j['Sorular'][soru]['Soru Tipi']
            beklenen_cevap = j['Sorular'][soru]['Beklenen Cevaplar']

            # ad soyad
            if tip == 0:
                #opencv ile kes kaydet
                resim = cv2.imread(resim_yol)
                roi = resim[int(ymin):int(ymax), int(xmin):int(xmax)]
                cv2.imwrite(os.path.join(path, 'gecici.png'), roi)
            
                df, _ = visionapi_post_image(client, path, 'gecici.png', dil)
                try:
                    cikan_sonuc = df['description'][0]
                except:
                    cikan_sonuc = 'okunamadi'
                
                del j['Sorular'][soru]['Soru Puanı']
                del j['Sorular'][soru]['Beklenen Cevaplar']
                del j['Sorular'][soru]['Öğrenci Cevapları']
                del j['Sorular'][soru]['Güven']

                onizleme_adi, onizleme_yol = onizleme_yukle(path, j['Kağıt Adı'], 'adsoyad', roi)
                j['Sorular'][soru]['Önizleme'] = onizleme_yol

                gercek_ad_soyad = ad_soyad_replacement(cikan_sonuc.replace('\n', ' '))
                j['Sorular'][soru]['Ad Soyad'] = gercek_ad_soyad

                with open(textdosyasi, 'w') as o:
                    o.write(str(j))
            # boşluk doldurma
            elif tip == 1:
                resim = cv2.imread(resim_yol,cv2.IMREAD_GRAYSCALE)
                roi = resim[int(ymin - 5):int(ymax + 20), int(xmin):int(xmax)]

                onizleme_adi, onizleme_yol = onizleme_yukle(path, j['Kağıt Adı'], str(soru), roi)
                j['Sorular'][soru]['Önizleme'] = onizleme_yol

                cv2.imwrite(os.path.join(path, 'gecici-bd.png'), roi)
                
                kesilmis = os.path.join(path, 'gecici-bd.png')

                #debug gerekiyorsa ->
                # sayi = random.randint(1,500)
                # kesilmis1 = cv2.imread(kesilmis)
                # cv2.imwrite(os.path.join(path, 'debug', f'raw-{sayi}.png'), kesilmis1)
                
                
                image = cv2.imread(kesilmis, 0)
                # th = cv2.adaptiveThreshold(image, 
                #     255,  # maximum value assigned to pixel values exceeding the threshold
                #     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # gaussian weighted sum of neighborhood
                #     cv2.THRESH_BINARY,  # thresholding type
                #     201,  # block size (5x5 window)
                #     21)  # constant

                h, w = image.shape
                oran = oranla(w)

                path1 = os.path.join(current_app.root_path, 'paper_grading/')
                bosluk_doldurma_arkaplan = cv2.imread(os.path.join(path1, 'bosluk_doldurma_arkaplan.png'), cv2.IMREAD_GRAYSCALE)
                
                imResize = cv2.resize(image,None,fx=oran, fy=oran, interpolation = cv2.INTER_LANCZOS4)

                h, w = imResize.shape
                back = bosluk_doldurma_arkaplan
                hh, ww = back.shape

                yoff = round((hh-h)/2)
                xoff = round((ww-w)/2)

                result = back.copy()
                result[yoff:yoff+h, xoff:xoff+w] = imResize

                kernel = np.ones((2,2),np.uint8)
                dilation = cv2.dilate(result,kernel,iterations = 1)

                cv2.imwrite(os.path.join(path, 'buyuk_bd.png'), dilation)
                #debug gerekiyorsa ->
                # sayi = random.randint(1,500)
                # cizgili1 = cv2.imread(os.path.join(path, 'buyuk_bd.png'))
                # cv2.imwrite(os.path.join(path, 'debug', f'processed-{sayi}.png'), cizgili1)

                df, response = visionapi_post_image(client, path, 'buyuk_bd.png', dil)
                cikan_sonuc, guven = bd_sonuc_cikar(df, response)

                son_sonuc = bd_sonuc(cikan_sonuc).lower()
                son_sonuc = bd_bosluk_kaldir(son_sonuc)
                f = j['Sorular'][soru]['Beklenen Cevaplar'].split(',')
                son_sonuc = bd_i_duzelt(f, son_sonuc)
                son_sonuc = bd_tekrar_duzelt(f, son_sonuc)
                if not hasNumbers(f):
                    son_sonuc = bd_sayi_kaldir(son_sonuc)

                # işlenmemiş hali ile engellemeyi deneyelim
                df, response = visionapi_post_image(client, path, 'gecici-bd.png', dil)
                cikan_sonuc1, guven1 = bd_sonuc_cikar(df, response)
                
                son_sonuc1 = bd_sonuc(cikan_sonuc1).lower()
                son_sonuc1 = bd_bosluk_kaldir(son_sonuc1)
                son_sonuc1 = bd_i_duzelt(f, son_sonuc1)
                son_sonuc1 = bd_tekrar_duzelt(f, son_sonuc1)
                if not hasNumbers(f):
                    son_sonuc1 = bd_sayi_kaldir(son_sonuc1)

                yazdirilacak_cevap = str()
                karar = 0.0

                sonuc_sozluk = [
                        {'sonuc': son_sonuc, 'guven': guven}, 
                        {'sonuc': son_sonuc1, 'guven': guven1}
                    ]
                
                print(sonuc_sozluk)

                f = [bd_sonuc(x).lower() for x in f]
                for p in sonuc_sozluk:
                    if float(p['guven']) > karar:
                        karar = float(p['guven'])
                        yazdirilacak_cevap = p['sonuc']

                if not yazdirilacak_cevap == 'okunamadi':
                    for x in f:
                        for idx, y in enumerate(sonuc_sozluk):
                            digeri = 1 if idx == 0 else 0
                            bunun_benzerligi = Levenshtein.distance(y['sonuc'], x)
                            digerinin_benzerligi = Levenshtein.distance(sonuc_sozluk[digeri]['sonuc'], x)
                            if y['sonuc'] == x:
                                yazdirilacak_cevap = y['sonuc']
                                break
                            elif (len(y['sonuc']) > 2 and len(x) > 2) and y['sonuc'] in x:
                                yazdirilacak_cevap = y['sonuc']
                            elif y['sonuc'] != x and (bunun_benzerligi < digerinin_benzerligi):
                                yazdirilacak_cevap = y['sonuc']

                _confidence = [x['guven'] for x in sonuc_sozluk if x['sonuc'] == yazdirilacak_cevap]
                try:
                    j['Sorular'][soru]['Güven'] = max(_confidence)
                except:
                    j['Sorular'][soru]['Güven'] = 0
                if onlyNumbers([x for x in f]) and len(yazdirilacak_cevap) == 1 and not yazdirilacak_cevap.isdigit():
                    yazdirilacak_cevap = bd_sayiya_donustur(yazdirilacak_cevap)
                j['Sorular'][soru]['Öğrenci Cevapları'] = yazdirilacak_cevap
                with open(textdosyasi, 'w') as o:
                    o.write(str(j))
            # çoktan seçmeli
            elif tip == 2:
                #opencv ile kes kaydet
                resim = cv2.imread(resim_yol)
                roi = resim[int(ymin):int(ymax), int(xmin):int(xmax)]
                cv2.imwrite(os.path.join(path, 'gecici.png'), roi)
                kesilmis = os.path.join(path, 'gecici.png')
                
                onizleme_adi, onizleme_yol = onizleme_yukle(path, j['Kağıt Adı'], str(soru), roi)
                j['Sorular'][soru]['Önizleme'] = onizleme_yol


                #binary yap
                #scikit_th(kesilmis)

                #fastai
                img = np.asarray(Image.open(kesilmis).convert(mode="L"))
                prediction = gecerli_gecersiz.predict(img)

                if not (str(prediction[0]) == 'gecersiz' and np.amax(prediction[2].numpy()) > 0.95):
                    prediction = abcde.predict(img)

                guven = prediction[2].numpy()
                j['Sorular'][soru]['Güven'] = np.amax(guven)
                j['Sorular'][soru]['Öğrenci Cevapları'] = 'gecersiz/bos' if str(prediction[0]) == 'gecersiz' else str(prediction[0])
                with open(textdosyasi, 'w') as o:
                    o.write(str(j))
            # doğru yanlış / eşleştirme
            else:
                if dogru_yanlis_mi(beklenen_cevap):
                    tip = 'dogru_yanlis'
                    learn = dogru_yanlis
                else:
                    tip = 'eslestirme'
                    learn = eslestirme
                #opencv ile kes kaydet
                resim = cv2.imread(resim_yol)
                roi = resim[int(ymin):int(ymax), int(xmin):int(xmax)]
                cv2.imwrite(os.path.join(path, 'gecici.png'), roi)
                kesilmis = os.path.join(path, 'gecici.png')
                
                onizleme_adi, onizleme_yol = onizleme_yukle(path, j['Kağıt Adı'], str(soru), roi)
                j['Sorular'][soru]['Önizleme'] = onizleme_yol


                #training için çıkar

                img = np.asarray(Image.open(kesilmis).convert(mode="L"))
                prediction = learn.predict(img)
                yanit = str(prediction[0])
                guven = prediction[2].numpy()
                j['Sorular'][soru]['Güven'] = np.amax(guven)

                j['Sorular'][soru]['Öğrenci Cevapları'] = dy_translations[yanit][lang] if len(yanit) > 1 else yanit.lower()
                with open(textdosyasi, 'w') as o:
                    o.write(str(j))

def yanit_duzenle(textdosyasi, path):
    with open(os.path.join(path, textdosyasi), 'r') as f:
        j = ast.literal_eval(f.read())
    if not 'Hata' in j['Sorular']:
        for x, y in j['Sorular'].items():
            if y['Soru Tipi'] == 0:
                pass
            elif y['Soru Tipi'] == 1:
                y['Beklenen Cevaplar'] = bd_sonuc(y['Beklenen Cevaplar']).lower()
                y['Öğrenci Cevapları'] = bd_sonuc(y['Öğrenci Cevapları']).lower()
            elif y['Soru Tipi'] == 2:
                y['Beklenen Cevaplar'] = y['Beklenen Cevaplar'].lower()
            elif y['Soru Tipi'] == 3:
                y['Beklenen Cevaplar'] = dogru_yanlis_duzelt(y['Beklenen Cevaplar']).lower()
        with open(os.path.join(path, textdosyasi), 'w') as q:
            q.write(str(j))

def sonuc_duzenle(textdosyasi, path, lang):
    with open(os.path.join(path, textdosyasi), 'r') as f:
        j = ast.literal_eval(f.read())
    if not 'Hata' in j['Sorular']:
        for x, y in j['Sorular'].items():
            if y['Soru Tipi'] == 0:
                del y['Soru Tipi']
            elif y['Soru Tipi'] == 1:
                y['Soru Tipi'] = 'Boşluk Doldurma'
                f = y['Beklenen Cevaplar'].split(',')
                f = [b.replace(" ", "") for b in f]
                h = [y['Öğrenci Cevapları']]
                h = [u.replace(" ", "") for u in h]
                for n, m in enumerate(f):
                    if len(m) <= 3: #tolerans olayı çok güvenilir gelmedi, tekrar bakılabilir
                        tolerans = 1
                    elif len(m) >= 4 and len(m) <= 5:
                        tolerans = 2
                    elif len(m) >= 6 and len(m) <= 8:
                        tolerans = 3
                    elif len(m) > 8 and len(m) <= 13:
                        tolerans = 4
                    elif len(m) >= 14 and len(m) <= 15:
                        tolerans = 5
                    elif len(m) >= 16:
                        tolerans = 7
                    sadece_sayi = onlyNumbers([x for x in f])
                    if sadece_sayi == True:
                        tolerans = 0
                    fark = Levenshtein.distance(h[0], m)
                    if fark <= tolerans:
                        y['Sonuç'] = 'Doğru'
                        break
                    else:
                        y['Sonuç'] = 'Yanlış'
            elif y['Soru Tipi'] == 2:
                y['Soru Tipi'] = 'Çoktan Seçmeli'
                cs_bc = y['Beklenen Cevaplar']
                cs_bc = bd_bosluk_kaldir(cs_bc)
                cs_oc = y['Öğrenci Cevapları']
                y['Sonuç'] = 'Doğru' if cs_bc == cs_oc else 'Yanlış'
            elif y['Soru Tipi'] == 3:
                dy_bc = y['Beklenen Cevaplar']
                dy_bc = bd_bosluk_kaldir(dy_bc)
                dy_oc = y['Öğrenci Cevapları']
                if dogru_yanlis_mi(y['Beklenen Cevaplar']):
                    y['Soru Tipi'] = 'Doğru Yanlış'
                    sonuc = dy_check(dy_bc, dy_oc, lang)
                    y['Sonuç'] = sonuc[1]
                else:
                    y['Soru Tipi'] = 'Eşleştirme'
                    y['Sonuç'] = 'Doğru' if dy_bc == dy_oc else 'Yanlış'
        with open(os.path.join(path, textdosyasi), 'w') as q:
            q.write(str(j))

def ad_soyad_replacement(text):
    kaldir = ['AD SOYAD', 'NAME SURNAME', 'MAME SLIRNAME', 'MAME SURNAME']
    for x in kaldir:
        text = text.replace(x, '')
    replacements = {"1": "ı", "2":"z", "8":"B", "4":"A", ":":"", ";":"",
                    "?":"z", "$": "ş"}
    text = "".join([replacements.get(c, c) for c in text])
    return text

def bd_sonuc_cikar(df, response):
    try:
        cikan_sonuc = df['description'][0]
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    guven = paragraph.confidence
                break
            break
    except:
        cikan_sonuc = 'okunamadi'
        guven = 0
    return cikan_sonuc, guven

def bd_sonuc(text):
    replacements = {"ğ": "g","ü": "u","ö": "o","_": "",".": "","ı": "i","ç": "c","ş": "s","(": "",")": "","[": "","]": "", "!":"", "'":"", 
                    "-":"", "—":"", "/":"", "\ ":"", ":":"", ";":"", "^":"", "*":"", "|":"l", "Ğ": "g","Ü": "u","Ö": "o","I": "i","Ç": "c","Ş": "s"}
    text = "".join([replacements.get(c, c) for c in text])
    return text.replace('\n', ' ')

def hasNumbers(liste):
    sayi_var_mi = False
    for x in liste:
        if any(char.isdigit() for char in x):
            sayi_var_mi = True
    return sayi_var_mi

def onlyNumbers(inputString):
  return (char.isdigit() for char in inputString)

def bd_tekrar_duzelt(f, sonuc):
    tekrar_var_mi = False
    for x in f:
        x = x.split()
        if len(x) != len(set(x)):
            tekrar_var_mi = True
    if not tekrar_var_mi:
        sonuc = sonuc.split()
        sonuc = ' '.join(sorted(set(sonuc), key=sonuc.index))
    return sonuc

def bd_i_duzelt(f, sonuc):
    # iki farklı loop yapmak zorunda kaldım
    i_var_mi = False
    for x in f:
        if x.lower().startswith('i '):
            i_var_mi = True
    if sonuc.lower().startswith('i ') and not i_var_mi:
        sonuc = sonuc[2:]
    liste = [' l', ' la', ' le']
    anlamsiz_var_mi = False
    for x in f:
        if x.lower().endswith(tuple(liste)):
            anlamsiz_var_mi = True
    if sonuc.lower().endswith(tuple(liste)) and not anlamsiz_var_mi:
        sonuc = sonuc[:-3]
    return sonuc.lower().strip()

def bd_sayi_kaldir(text):
    replacements = {"1": "", "2":"", "3":"", "4":"", "5":"", "6":"", "7":"", "8":"", "9":"", "0":""}
    text = "".join([replacements.get(c, c) for c in text])
    return text

def bd_sayiya_donustur(text):
    replacements = {"l":"1", "b":"6", "!":"1","a":"9", "g":"9", "t":"7", "+":"7", "z":"2", "b":"8"}
    text = "".join([replacements.get(c, c) for c in text])
    return text

def bd_bosluk_kaldir(x):
    if not bool(x.strip()):
        x = 'okunamadi'
    else:
        x = x.strip()
    return x

def dogru_yanlis_duzelt(text):
    replacements = {"ğ":"g", "ı":"i", "ş":"s"}
    text = "".join([replacements.get(c, c) for c in text])
    return text.strip()

def dogru_yanlis_mi(text):
    dy_ifadeleri = ['dogru', 'yanlis', 'yanlış', 'doğru', 'true', 'false']
    text = bd_bosluk_kaldir(text)
    return True if text.lower() in dy_ifadeleri else False

def dy_check(text, ogr_cevap, lang):
    dogru = ['dogru', 'doğru', 'true', 'ture', 'tru']
    res = 'd' if ogr_cevap in dogru and text.strip() in dogru else 'y'
    t = {
        'd': {'en': ['true', 'Doğru'], 'tr': ['dogru', 'Doğru']},
        'y': {'en': ['false', 'Yanlış'], 'tr': ['yanlis', 'Yanlış']}
    }
    return t[res][lang]
