from flask import current_app
from src import db, celery
from src.models import PaperGradingKullanimi, Ogrenci, Ogrencirapor, Okunansinav, Sinav, Sinifrapor, Sinif, User
from src.main.utils import bildirim_gonder
from src.kredi.utils import kullanim_dus, kredi_hesapla
import re, os, ast, numpy as np, matplotlib.pyplot as plt, locale, boto3, Levenshtein, xlsxwriter
from fpdf import FPDF, HTMLMixin
from urllib.parse import quote_plus
from textwrap import wrap
from datetime import datetime

s3_client = boto3.client('s3', aws_access_key_id=os.environ['S3_ACCESS_KEY'],\
                  aws_secret_access_key=os.environ['S3_SECRET_KEY'], \
                  region_name=os.environ['S3_REGION'])
s3 = boto3.resource('s3', aws_access_key_id=os.environ['S3_ACCESS_KEY'],\
                  aws_secret_access_key=os.environ['S3_SECRET_KEY'], \
                  region_name=os.environ['S3_REGION'])
s3_url = os.environ['S3_URL']

def ogrenci_okunan_sorular(ogrenci):
    return [
            {
                'sira': x.soru_sirasi,
                'tip': x.tip,
                'puan': x.puan,
                'beklenen_cevaplar':x.beklenen_cevaplar,
                'ogrenci_cevaplari':x.ogrenci_cevaplari,
                'sonuc': x.sonuc,
                'onizleme': '<img src="' + x.onizleme + '" loading=lazy>',
                'guven': x.guven,
                'id': x.id
            }
            for x in ogrenci.okunan_sorular
        ]

def _ogrenci_preview(ogrenci):
    return [
            {
                'puan': x.puan,
                'beklenen_cevaplar':x.beklenen_cevaplar,
                'ogrenci_cevaplari':x.ogrenci_cevaplari,
                'sonuc': x.sonuc,
                'onizleme': '<img src="' + x.onizleme + '" loading=lazy>',
                'guven': x.guven,
                'id': x.id
            }
            for x in ogrenci.okunan_sorular
        ]

def koordinattan_yukseklik_genislik(koordinat):
    bir, iki, uc, dort = ast.literal_eval(koordinat)
    uc = uc - bir
    dort = dort - iki
    liste = [int(bir), int(iki), int(uc), int(dort)]
    liste = [x * 0.30 for x in liste]
    return liste[2], liste[3]

class PDF(FPDF, HTMLMixin):
    def footer(self):
        self.set_y(-15)
        self.set_font('ArialUnicode', '', 8)
        self.set_text_color(100,100,100)
        self.cell(0, 10, 'Created automatically..', 0, 0, 'C', link='https://pg.com/')

def ogrenci_yeni_rapor(ogrenci):
    '''
        şu an için sadece bir rapora
        izin verdiğimiz için önceki
        raporu silelim
    '''
    if len(ogrenci.raporlar) > 0:
        rapor = ogrenci.raporlar[-1]
        key = 'rapor/' + str(ogrenci.id) + '/' + rapor.uuid + '.' + rapor.tur
        s3_client.delete_object(Bucket=os.environ['S3_NAME'], Key=key)
        db.session.delete(rapor)
        yeni_rapor = Ogrencirapor(ogrenci_id=ogrenci.id)
        db.session.add(yeni_rapor)
        db.session.commit()
        return yeni_rapor.id
    else:
        rapor = Ogrencirapor(ogrenci_id=ogrenci.id)
        db.session.add(rapor)
        db.session.commit()
        return rapor.id

@celery.task(queue='pdf')
def ogrenci_rapor_pdf(bilgiler):
    lang = bilgiler['lang']
    rapor_id = bilgiler['id']
    rapor = Ogrencirapor.query.filter_by(id=rapor_id).first()
    ogrenci = Ogrenci.query.filter_by(id=rapor.ogrenci_id).first()
    sinav = Okunansinav.query.filter_by(id=ogrenci.sinav_id).first()
    bo_kullanim = PaperGradingKullanimi.query.filter_by(okunan_sinav_id=sinav.id).first()
    translations = {
        'score': {'tr': 'Aldığı Puan: ', 'en': 'Score: '},
        'sutunlar': {
            'tr': ("Soru", "Soru Tipi", "Puan", "Beklenen Yanıtlar", "Öğrenci Yanıtları", "Sonuç", "Önizleme"),
            'en': ("Question", "Type", "Points", "Expected Answers", "Student Answers", "Result", "Preview")
        },
        'sonuc': {
            'yanlis': {'tr': 'Yanlış', 'en': 'False'},
            'dogru': {'tr': 'Doğru', 'en': 'Correct'}
        },
        'bilgiler': {
            'tr': 'Sınav Bilgiler',
            'en': 'Exam Informations'
        },
        'sinifaGore': {
            'tr': 'Sınıfa Göre Öğrenci Başarısı',
            'en': 'Average Success of the Class'
        },
        'kazanimList': {
            'tr': 'Kazanım Listesi',
            'en': 'Learning Objectives List'
        },
        'ogr': {'tr': 'Öğrenci: ', 'en': 'Student: '},
        'Çoktan Seçmeli': 'Multiple Choice',
        'Boşluk Doldurma': 'Gap Filling',
        'Doğru Yanlış': 'True False',
        'Eşleştirme': 'Matching',
        'dogru': 'true',
        'yanlis': 'false'
    }
    data = [
            {
                'sira': x.soru_sirasi if lang == 'tr' else x.soru_sirasi.replace('Soru', 'Q'),
                'tip': x.tip if lang == 'tr' else translations[x.tip],
                'puan': x.puan,
                'beklenen_cevaplar':x.beklenen_cevaplar,
                'ogrenci_cevaplari':x.ogrenci_cevaplari,
                'sonuc': translations['sonuc']['dogru'][lang] if x.sonuc == True else translations['sonuc']['yanlis'][lang],
                'onizleme': '<img src="' + x.onizleme + '" loading=lazy>',
                'koordinat': x.koordinat
            }
            for x in ogrenci.okunan_sorular
        ]
    path = os.path.join(current_app.root_path, 'static/fpdf')
    pdf = PDF(orientation="landscape")
    pdf.add_page()
    pdf.add_font('ArialUnicode',fname=os.path.join(path,'fonts/arial.ttf'),uni=True)
    pdf.add_font('ArialUnicode', style="B",fname=os.path.join(path,'fonts/arialbld.ttf'),uni=True)
        
    ogrenci_adi = ogrenci.ad_soyad.split('/')
    ogrenci_adi = f'{s3_url}onizlemeler/{str(ogrenci_adi[-2])}/{quote_plus(ogrenci_adi[-1])}'
    pdf.set_font('ArialUnicode', 'B', 10)
    pdf.cell(txt=translations['ogr'][lang])
    pdf.image(ogrenci_adi, w=80, y=pdf.get_y() - 2)
    pdf.set_x(250)
    pdf.cell(txt=translations['score'][lang] + str(ogrenci.toplam_puan))
    pdf.ln(10)

    sutunlar = translations['sutunlar'][lang]
    genislikler = [15, 30, 9, 70, 60, 18, 80]
    
    for idx, col_name in enumerate(sutunlar):
        pdf.cell(genislikler[idx], 6, col_name, border=1)
    pdf.ln(10)
    pdf.set_font('ArialUnicode', '', 10)  # disabling bold text

    for idx, row in enumerate(data):
        pdf.set_text_color(100,100,100) if row['sonuc'] == translations['sonuc']['yanlis'][lang] else pdf.set_text_color(0,0,0)
        genislik, yukseklik = koordinattan_yukseklik_genislik(row['koordinat'])
        gorsel = re.findall('<img src=([\\s\\S]+?)" loading=lazy', row['onizleme'])[0][1:].split('/')
        tam_gorsel = f'{s3_url}onizlemeler/{str(gorsel[-2])}/{quote_plus(gorsel[-1])}'
        
        pdf.multi_cell(w=genislikler[0], txt=row['sira'], ln=3, max_line_height=pdf.font_size)
        pdf.multi_cell(w=genislikler[1], txt=row['tip'], ln=3, max_line_height=pdf.font_size)
        pdf.multi_cell(w=genislikler[2], txt=str(row['puan']), ln=3, max_line_height=pdf.font_size)
        pdf.multi_cell(w=genislikler[3], txt=row['beklenen_cevaplar'][0:65], ln=3, max_line_height=pdf.font_size)
        pdf.multi_cell(w=genislikler[4], txt=row['ogrenci_cevaplari'][0:65], ln=3, max_line_height=pdf.font_size)
        pdf.multi_cell(w=genislikler[5], txt=row['sonuc'], ln=3, max_line_height=pdf.font_size)
        pdf.image(tam_gorsel, w=min(genislik * 0.2645833333, 80), h=min(yukseklik, yukseklik * 0.2645833333))
        pdf.ln(yukseklik * 0.10)
    
    pdf.set_text_color(0,0,0)
    pdf.set_font('ArialUnicode', 'B', 14)
    pdf.cell(125)
    pdf.cell(30, 10, translations['bilgiler'][lang], 0, 0, 'C')
    pdf.ln(10)
    pdf.set_font('ArialUnicode', '', 10)
    if lang == 'tr':
        locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')

    if sinav != None and sinav.kazanim_analizi:
        sistemdeki_karsiligi = Sinav.query.filter_by(id=sinav.sistemdeki_karsiligi).first()
        konular = [x.name for x in sistemdeki_karsiligi.konular.all()]
        bilgiler = ogrenci_rapor_bilgiler({'bo_kullanim': bo_kullanim, 'sinav': sinav, 'konular': konular, 'ogrenci': ogrenci, 'lang': lang})
        pdf.write_html(bilgiler)
        pdf.ln(10)
        img = kazanim_plot(sinav, ogrenci, lang)
        pdf.set_font('ArialUnicode', 'B', 14)
        pdf.cell(125)
        pdf.cell(30, 10, translations['sinifaGore'][lang], 0, 0, 'C')
        pdf.ln(10)
        pdf.image(img, x=5, w=280)
        os.remove(img)

        okunan_sorular = ogrenci.okunan_sorular
        kazanimlar = [(y.name, x.soru_sirasi) for x in okunan_sorular for y in x.kazanimlar.all()]
        result = {}
        for i in kazanimlar:
            x = i[0].replace('Soru', 'Question') if lang == 'en' else i[0]
            result.setdefault(i[0],[]).append(i[1])
        data = ((x, ' - '.join(y)) for x, y in result.items())
        
        pdf.cell(125)
        pdf.cell(30, 10, translations['kazanimList'][lang], 0, 0, 'C')
        pdf.ln(10)

        pdf.set_font('ArialUnicode', '', 10)
        line_height = pdf.font_size * 4
        col_width = pdf.epw / 2 # distribute content evenly
        for row in data:
            for datum in row:
                pdf.multi_cell(col_width, line_height, datum, border=1, ln=3, max_line_height=pdf.font_size)
            pdf.ln(line_height)
    else:
        bilgiler = ogrenci_rapor_bilgiler({'bo_kullanim': bo_kullanim, 'sinav': sinav, 'ogrenci': ogrenci, 'lang': lang})
        pdf.write(bilgiler)
        pdf.ln(10)
    
    s3_bucket = s3.Bucket(os.environ['S3_NAME'])
    liste = s3_bucket.objects.filter(Prefix=f'rapor/{str(ogrenci.id)}').all()
    for x in liste:
        s3.Object(os.environ['S3_NAME'], x.key).delete()
    
    kayit_yolu = gecici_kayit()
    pdf.output(kayit_yolu)
    upload_gecici_to_s3(rapor, kayit_yolu, 'ogrenci/' + str(ogrenci.id))
    rapor.durum = 'hazir'
    try:
        db.session.commit()
    except:
        db.session.rollback()
    return '', 200

def ogrenci_rapor_bilgiler(sozluk):
    bo_kullanim = sozluk['bo_kullanim']
    sinav = sozluk['sinav']
    konular = sozluk['konular'] if 'konular' in sozluk else None
    ogrenci = sozluk['ogrenci']
    lang = sozluk['lang']
    toplam_puan = 0
    for x in sinav.ogrenciler:
        toplam_puan+= x.toplam_puan
    ortalama = round(toplam_puan / len(sinav.ogrenciler), 2)
    ogrenci_basarisi = round(ortalama - ogrenci.toplam_puan, 2)
    if lang == 'tr':
        durum = 'az' if ogrenci_basarisi > 0 else 'fazla'
        ogrenci_basarisi = 'Bu öğrenci sınıf ortalamasından <b>' + str(ogrenci_basarisi).replace('-', '') + f'</b> puan daha {durum} aldı.'
        bilgiler = f'''<b>{bo_kullanim.timestamp.strftime("%d %B %Y")}</b> tarihinde yapılan bu <b>{bo_kullanim.ders_adi.name}</b> sınavına <b>{len(sinav.ogrenciler)}</b> öğrenci katıldı ve sınavın ortalama puanı <b>{ortalama}</b> olarak hesaplandı.''' + ogrenci_basarisi
        if konular != None:
            bilgiler += f' Sınav ağırlıklı olarak <b>{", ".join(konular)}</b> konuları hakkındaydı.'
    else:
        durum = 'lower' if ogrenci_basarisi > 0 else 'higher'
        ogrenci_basarisi = 'Compared to class average, this student got <b>' + str(ogrenci_basarisi).replace('-', '') + f'</b> points {durum}.'
        bilgiler = f'''<b>{len(sinav.ogrenciler)}</b> students attended this <b>{bo_kullanim.ders_adi.name}</b> exam which was conducted on <b>{bo_kullanim.timestamp.strftime("%d %B %Y")}</b> and the average of these students' scores is <b>{ortalama}</b>.'''
        if konular != None:
            bilgiler += f' This exam was mostly about <b>{", ".join(konular)}</b>'

    return bilgiler

def kazanim_plot(sinav, ogrenci, lang):
    plotTranslations = {
        'sinifOrt': {
            'tr': 'Sınıf Ortalaması',
            'en': 'Class Average'
        },
        'ogrBas': {
            'tr': 'Öğrenci Başarısı',
            'en': 'Student Success'
        },
        'trueAns': {
            'tr': 'Doğru Yanıt Sayısı',
            'en': '# of True Answers'
        }
    }
    sinif_kazanimlari, ogrenci_kazanimlari = ogrenci_kazanim_performansi(sinav, ogrenci)
    plt.figure(figsize=(18,7))

    x = ['\n'.join(wrap(x, 40)) for x in sinif_kazanimlari.keys()]
    x_axis = np.arange(len(x))

    y = list(sinif_kazanimlari.values())
    z = list(ogrenci_kazanimlari.values())

    ax = plt.subplot(111)
    ax.bar(x_axis - 0.2, y, width=0.2, color=[(0.8, 0.6, 0.7, 0.4)], align='center', label=plotTranslations['sinifOrt'][lang])
    ax.bar(x_axis, z, width=0.2, color=[(0, 0, 1, 0.4)], align='center', label=plotTranslations['ogrBas'][lang])
    plt.ylabel(plotTranslations['trueAns'][lang])
    plt.xticks(x_axis, x)
    ax.legend()
    timestamp = str(datetime.now().timestamp()).replace('.', '')
    kayit_yolu = os.path.join(current_app.root_path, f'gecici/{timestamp}.png')
    
    plt.tight_layout()
    plt.savefig(kayit_yolu)
    return kayit_yolu

def kazanim_performans(sinav):
    sorular = [x.okunan_sorular for x in sinav.ogrenciler]
    kazanim_adlar = {item.name : 0 for sublist in sorular[0] for item in sublist.kazanimlar.all()}
    kazanimlar = []
    for x in sorular:
        kazanimlar.append([(y.sonuc, y.kazanimlar.all()) for y in x])
    
    kazanimlar = [item for sublist in kazanimlar for item in sublist]

    for x in kazanimlar:
        if x[0] == True:
            for y in x[1]:
                kazanim_adlar[y.name] += 1
    return dict(sorted(kazanim_adlar.items(), key=lambda item: item[1], reverse=True)[:5])

def ogrenci_kazanim_performansi(sinav, ogrenci, deep_analysis=False):
    sinif_kazanimlari = kazanim_performans(sinav)
    sinif_kazanimlari = {name: int(entry / len(sinav.ogrenciler)) for name, entry in sinif_kazanimlari.items()}
    
    sorular = [x for x in ogrenci.okunan_sorular]
    kazanim_adlar = {item.name : 0 for sublist in sorular for item in sublist.kazanimlar.all() if item.name in sinif_kazanimlari}
    kazanimlar = []
    for x in sorular:
        _tuple = (x.sonuc, x.kazanimlar.all())
        kazanimlar.append(_tuple)
    
    kazanimlar = [item for sublist in kazanimlar for item in sublist]
    for idx, x in enumerate(kazanimlar):
        if x == True:
            for y in kazanimlar[idx+1]:
                if y.name in sinif_kazanimlari.keys():
                    kazanim_adlar[y.name] += 1
    if deep_analysis == True:
        ogrenci_performansi = dict(sorted(kazanim_adlar.items(), key=lambda item: item[1], reverse=True))
    else:
        ogrenci_performansi = dict(sorted(kazanim_adlar.items(), key=lambda item: item[1], reverse=True)[:5])

    return sinif_kazanimlari, ogrenci_performansi

def sinif_raporlari_sil(sinif):
    for x in sinif.raporlar:
        key = f'rapor/sinif/{sinif.id}/{x.uuid}.xlsx'
        s3_client.delete_object(Bucket=os.environ['S3_NAME'], Key=key)

def upload_gecici_to_s3(rapor, kayit_yolu, id):
    rapor_tur = 'vnd.openxmlformats-officedocument.spreadsheetml.sheet' if rapor.tur == 'xlsx' else rapor.tur
    s3_yol = f'rapor/{id}/{rapor.uuid}.{rapor.tur}'
    s3_client.upload_file(kayit_yolu, os.environ['S3_NAME'], s3_yol, ExtraArgs={
        "ACL": "public-read",
        "CacheControl": "max-age=2000000,public",
        "Expires": "2030-09-01T00:00:00Z",
        "ContentType": f'application/{rapor_tur}'})
    os.remove(kayit_yolu)

def kazanim_sayisi(sinav):
    kazanim_listesi = {}
    for soru in sinav.ogrenciler[0].okunan_sorular:
        for x in soru.kazanimlar.all():
            if x.name not in kazanim_listesi.keys():
                kazanim_listesi[x.name] = 1
            else:
                kazanim_listesi[x.name] += 1
    return kazanim_listesi

def ogrenci_excel_ad(ogrenci):
    if ogrenci.gercek_ogrenci_id != None:
        ekle = ogrenci.gercek_ogrenci.numara + '-' + ogrenci.gercek_ogrenci.name
    else:
        ekle = ogrenci.gercek_ogrenci.numara + '-' + ogrenci.ad_soyad_gercek
    return ekle

def header_olustur(sinif):
    headers = ['Sınav', 'Ders', 'Kazanım', 'Soru Sayısı']
    for sinav in sinif.sinavlar:
        for ogrenci in sinav.ogrenciler:
            if ogrenci.gercek_ogrenci_id != None:
                ekle = ogrenci.gercek_ogrenci.numara + '-' + ogrenci.gercek_ogrenci.name
            else:
                ekle = ogrenci_excel_ad(ogrenci)
            if not ekle in headers:
                headers.append(ekle)
    return headers

def sinif_raporu_kredisi(sinif):
    ogrenci = 0
    sinavlar = [x for x in sinif.sinavlar if x.kazanim_analizi]
    for x in sinavlar:
        ogrenci += len(x.ogrenciler)
    tutar = round(int(ogrenci * 0.20))
    return tutar

@celery.task(queue="celery")
def deep_analysis_kazanimlar(idler):
    sinif = Sinif.query.filter_by(id=idler[0]).first()
    rapor = Sinifrapor.query.filter_by(id=idler[1]).first_or_404()
    user = User.query.filter_by(id=sinif.user_id).first()
    tutar = sinif_raporu_kredisi(sinif)
    kredi = kredi_hesapla(user)
    if tutar >= kredi:
        return 'yetersizkredi', 200
    headers = header_olustur(sinif)
    sinavlar = sinif.sinavlar
    listeler = []
    for sinav in sinavlar:
        kazanim_listesi = kazanim_sayisi(sinav)
        for kazanim, x in kazanim_listesi.items():
            bu_kazanim = [None] * len(headers)
            bu_kazanim[:4] = [sinav.ad, sinav.kullanim[0].ders_adi.name, kazanim, x]
            for ogrenci in sinav.ogrenciler:
                excel_ad = ogrenci_excel_ad(ogrenci)
                _, kazanimlar = ogrenci_kazanim_performansi(sinav, ogrenci, True)
                for ad, deger in kazanimlar.items():
                    if ad == kazanim:
                        basari = round(deger/x * 100, 1)
                        basari = int(basari) if basari.is_integer() else basari
                        idx = headers.index(excel_ad)
                        bu_kazanim[idx] = basari
                if bu_kazanim not in listeler:
                    listeler.append(bu_kazanim)
    listeler.insert(0, headers)
    kayit_yolu = gecici_kayit()
    wb = xlsxwriter.Workbook(kayit_yolu)
    ws = wb.add_worksheet(sinif.name)
    row = 0
    col = 0
    kz_genislik = 0
    for idx, line in enumerate(listeler):
        for idx2, item in enumerate(line):
            genislik = 0
            if idx == 0 and idx2 <= 2:
                format = wb.add_format()
                format.set_align('center')
                format.set_align('vcenter')
                ws.write(row, col, item, format)
            elif idx == 0 and idx2 > 2:
                format = wb.add_format()
                format.set_rotation(90)
                ws.write(row, col, item, format)
            elif idx2 > 3:
                ws.set_column(col, col, 5)
                ws.write(row, col, item)
            elif idx2 == 2:
                if len(str(item)) > kz_genislik:
                    kz_genislik = len(str(item))
                ws.set_column(col, col, min(130, kz_genislik))
                ws.write(row, col, item)
            else:
                if len(str(item)) > genislik:
                    genislik = len(str(item))
                ws.set_column(col, col, genislik + 1)
                ws.write(row, col, item)
            col += 1
        row += 1
        col = 0

    wb.close()
    upload_gecici_to_s3(rapor, kayit_yolu, 'sinif/' + str(sinif.id))
    rapor.durum = 'hazir'
    
    kullanim_dus(user, tutar)
    try:
        db.session.commit()
    except:
        db.session.rollback()
    bildirim = {'baslik': 'Sınıf Raporu Hazırlandı', 'data': f'{sinif.name} sınıfı raporu hazırlandı.', 'hedef': f'/pg/panel/siniflar/{sinif.id}'}
    bildirim_gonder({'alici': sinif.user_id,'name': 'sinif_rapor_olustu', 'data': bildirim})
    return '', 200

def gercek_ogrenci_ortalama(gercekogrenci):
    sinavlar = gercekogrenci.sinavlar
    if len(sinavlar) == 0:
        return 0
    else:
        toplam_puan = 0
        for x in sinavlar:
            toplam_puan += x.toplam_puan
        return round(toplam_puan / len(sinavlar), 2)

def sinif_ortalama(sinif):
    sinavlar = sinif.sinavlar
    toplam = 0
    ogrenci_sayisi = 0
    for x in sinavlar:
        for y in x.ogrenciler:
            toplam += y.toplam_puan
            ogrenci_sayisi += 1
    try:
        ortalama = toplam / ogrenci_sayisi
        return round(ortalama, 2)
    except:
        return ''

@celery.task(queue="pdf")
def sinav_onizleme_sil(sinav_id):
    sinav = Okunansinav.query.filter_by(id=sinav_id).first()
    ogrenciler = sinav.ogrenciler
    ad_soyad_onizlemeleri = [x.ad_soyad for x in ogrenciler]
    inferfiles = [current_app.config['S3_BUCKET_NAME'] + 'inferfiles/' + str(sinav.user_id) + '/' + str(sinav.id) + '/' + x.name for x in sinav.inferfiles]
    soru_onizlemeleri = []
    rapor_gec = ['yok', 'bekleniyor', '']
    for x in ogrenciler:
        for y in x.okunan_sorular:
            soru_onizlemeleri.append(y.onizleme)
        for rapor in x.raporlar:
            soru_onizlemeleri.append(current_app.config['S3_BUCKET_NAME'] + f'rapor/ogrenci/{x.id}/{rapor.uuid}.pdf')
    for x in ad_soyad_onizlemeleri + soru_onizlemeleri + inferfiles:
        if not x.startswith('Hata: '):
            _, key = x.split(current_app.config['S3_BUCKET_NAME'])
            s3_client.delete_object(Bucket=os.environ['S3_NAME'], Key=key)
    
    db.session.delete(sinav)
    db.session.commit()
    return '', 200

def ogrenci_kagit_sil(ogrenci_id):
    ogrenci = Ogrenci.query.filter_by(id=ogrenci_id).first_or_404()
    if not ogrenci.ad_soyad.startswith('Hata :'):
        rapor_gec = ['yok', 'bekleniyor', '']
        onizlemeler = []
        onizlemeler.append(ogrenci.ad_soyad)
        for rapor in ogrenci.raporlar:
            onizlemeler.append(current_app.config['S3_BUCKET_NAME'] + f'rapor/ogrenci/{ogrenci.id}/{rapor.uuid}.pdf')
        for x in ogrenci.okunan_sorular:
            onizlemeler.append(x.onizleme)
        for x in onizlemeler:
            _, key = x.split(current_app.config['S3_BUCKET_NAME'])
            s3_client.delete_object(Bucket=os.environ['S3_NAME'], Key=key)
    db.session.delete(ogrenci)
    try:
        db.session.commit()
        return '', 200
    except:
        db.session.rollback()
        return '', 500

def sinif_sinav_eslestir(sinif, sinav):
    eslesmeler = []
    for x in sinav:
        en_az = ()
        uzaklik = 9999
        for y in sinif:
            x_y_uzaklik = abs(Levenshtein.distance(x[0], y[0]))
            if x_y_uzaklik < uzaklik:
                uzaklik = x_y_uzaklik
                en_az = (y[0], y[1])
        sinif.remove(en_az)
        eslesmeler.append((x[1], en_az[1]))
    return eslesmeler

def gecici_kayit():
    timestamp = str(datetime.now().timestamp()).replace('.', '')
    kayit_yolu = os.path.join(current_app.root_path, f'gecici/{timestamp}.pdf')
    return kayit_yolu

def tryint(s):
    try:
        return int(s)
    except:
        return s

def alphanum_key(s):
    return [ tryint(c) for c in re.split('([0-9]+)', s) ]