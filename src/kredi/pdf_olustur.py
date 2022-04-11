from fpdf import FPDF
from string import ascii_uppercase
from fpdf import FPDF, HTMLMixin
from urllib.parse import parse_qs, unquote
import os, boto3, re, cv2
from src.models import Soru, Logo, Konu
from src import db
from flask import current_app
from cv2 import IMWRITE_JPEG_QUALITY, IMWRITE_JPEG_OPTIMIZE

s3_client = boto3.client('s3')
s3 = boto3.resource('s3')
s3_name=os.environ['S3_NAME']

class Base:
  sag = False
  sayi = 0
  ust_yazi = ''
  alt_yazi = ''
  logo_ad = ''
  s3_bucket_name = os.environ['S3_URL']
  lst = ascii_uppercase[:11]
  defaults = [s3_bucket_name + 'pdfs/a.png',\
            s3_bucket_name + 'pdfs/b.png',\
            s3_bucket_name + 'pdfs/c.png',\
            s3_bucket_name + 'pdfs/d.png',\
            s3_bucket_name + 'pdfs/e.png']
  sik_harfleri = ['<b>A) </b>', '<b>B) </b>', '<b>C) </b>', '<b>D) </b>', '<b>E) </b>']
  
  def subscript(self, soru):
    ayir = re.split("(<sub>[\\s\\S]+?</sub>)|(<sup>[\\s\\S]+?</sup>)", soru)
    ayir = [x for x in ayir if x != None]
    subp = re.findall("(<sub>[\\s\\S]+?</sub>)|(<sup>[\\s\\S]+?</sup>)", soru)
    subp = [x[0] + x[1] for x in subp]
    subp_class_kaldir = ['<br>', '&nbsp;', '<p>', '</p>',]
    for x in ayir:
      ilk_y = self.get_y()
      yaz = x[5:-6]
      for y in subp_class_kaldir:
        if y in yaz:
          yaz = yaz.replace(y, '')
      if x in subp and x.startswith('<sub>'):
        _x = self.get_x()
        self.set_y(ilk_y + 2)
        self.set_x(_x)
        self.set_font('ArialUnicode','', 5)
        self.write(txt=yaz.replace('&nbsp;', ''))
        self.set_y(ilk_y)
        self.set_x(self.get_string_width(x) + (_x - 10))
      elif x in subp and x.startswith('<sup>'):
        self.set_font('ArialUnicode','', 5)
        self.write(txt=yaz.replace('&nbsp;', ''))
      else:
        self.set_font('ArialUnicode','', 9)
        self.write_html(x)
        self.set_x(self.get_x())
  
  def class_kaldir(self, text):
    kaldir = ['<b>', '</b>', '<i>', '</i>', '<u>', '</u>', '<br>', '<p>', '</p>', '&nbsp;', '<script>', '</script>', '<sub>', '</sub>', '<sup>', '</sup>']
    for x in kaldir:
      if x in text:
          text = text.replace(x, '')
    return text

  def soru_temizle(self, text):
    text = text.replace('<p></p>', '')
    while text.endswith('<p>\r\n</p>'):
      text = text.replace('<p>\r\n</p>', '')
    if text.endswith('<b>\r\n</b>'):
      text = text[:-9]
    if text.endswith('<p>'):
      text = text[:-3]
    if text.startswith('<p>') and text.endswith('</p>'):
      text = text[3:-4]
    if text.endswith('<p>'):
      text = text[:-3]
    return text

  def p_kaldir(self, text):
    kaldir = ['<p>', '</p>', '<br>', '<p></p>']
    for x in kaldir:
      if x in text:
        text = text.replace(x, '')
    return text
  
  def mat_formulu_mu(self, yol):
    if not 'matematik' in yol:
      return False
    else:
      try:
        num = yol.split('matematik')[1].strip('.png')
        return True if len(num) == 13 else False
      except:
        return False

  def sik_yazdir(self, siklar, user_id, px_sinir):
    en_uzun_piksel = 0
    yeni_siklar = []
    yukseklikler = []

    for gorsel in siklar:
      if not gorsel in self.defaults:
        gercek_ad = unquote(os.path.basename(gorsel))
        ad, _ext = os.path.splitext(gercek_ad)
        kayit_yolu = os.path.join(current_app.root_path, f'static/fpdf/pdf_files/gorseller/{user_id}/' + gercek_ad)
        
        
        key = gorsel.split(current_app.config['S3_BUCKET_NAME'])
        s3_client.download_file(s3_name, unquote(key[1]), kayit_yolu)
        
        if self.mat_formulu_mu(gercek_ad):
          img = cv2.imread(kayit_yolu, cv2.IMREAD_UNCHANGED)
          height, width, _ = tuple([0.50*x for x in img.shape])
          yeni_ad = kayit_yolu.replace('.png', '_resized.png')
          cv2.imwrite(yeni_ad, img)
        else:
          img = cv2.imread(kayit_yolu, 0)
          width = int(img.shape[1])
          height = int(img.shape[0])

          scale_percent = 100
          if (px_sinir == (38, 38) or px_sinir == (48, 48)) and img.shape[1]/img.shape[0] < 1: #tek satırda ve görseller dikey
            px_sinir = (px_sinir[0], 64)

          if not width < px_sinir[0] or height > px_sinir[1]:
            width = int(img.shape[1] * scale_percent / 100)
            height = int(img.shape[0] * scale_percent / 100)
            
            while width > px_sinir[0] or height > px_sinir[1]:
              scale_percent = scale_percent - 0.1
              width = int(img.shape[1] * scale_percent / 100)
              height = int(img.shape[0] * scale_percent / 100)
      
          yeni_ad = kayit_yolu.replace('.jpg', '_resized.jpg')
          cv2.imwrite(yeni_ad, img, [int(cv2.IMWRITE_JPEG_QUALITY), 50,IMWRITE_JPEG_OPTIMIZE])
        
        if height > en_uzun_piksel:
          en_uzun_piksel = height
        
        _tuple = (yeni_ad, width, height)
        
        yeni_siklar.append(_tuple)
        yukseklikler.append(height)

        # os.remove(kayit_yolu)
    return yeni_siklar, en_uzun_piksel, yukseklikler

class PDF(FPDF, HTMLMixin, Base):
  @property
  def accept_page_break(self):
      """Accept automatic page break or not"""
      if not self.sag:
        self.sag = True
        if self.page_no() == 1:
          self.set_y(25)
        else:
          self.set_y(20)
        self.set_x(110)
        self.set_right_margin(5)
        self.set_left_margin(110)
        return False
      else:
        self.sag = False
        if self.page_no() == 1:
          self.set_y(25)
        else:
          self.set_y(20)
        self.set_x(10)
        self.set_right_margin(110)
        self.set_left_margin(10)
        #self.add_page(same=True)
        #self.set_auto_page_break(auto=True)
        return True

  def adsoyad(self, dil):
    self.set_font('ArialUnicode', '', 11)
    if dil == 'tr':
      self.cell(100, 6, txt='AD SOYAD:', border=1)
      self.cell(15, 6, txt='')
      self.cell(100, 6, txt='Sınıf/Numara: ______________')
    else:
      self.cell(103, 6, txt='NAME SURNAME:', border=1)
      self.cell(15, 6, txt='')
      self.cell(100, 6, txt='Class/Number: ______________')
    self.set_y(20)
  
  def sinav_kodu(self, kod):
    self.set_font('ArialUnicode', '', 9)
    self.cell(120, 6, txt=kod, border=1, align="C")

  def footer(self):
    # Position at 1.5 cm from bottom
    self.set_y(-15)
    self.set_text_color(100,100,100)
    self.set_font('ArialUnicode', 'I', 8)
    # Page number
    self.cell(0, 9, self.alt_yazi, 0, 0, 'L')

  def header(self):
    self.set_y(5)
    self.set_font('ArialUnicode', '', 8)
    ust_yazi = self.ust_yazi
    w = self.get_string_width(ust_yazi) + 6
    if self.logo_ad != '':
      self.image(x=190, y=1, w=15, h=15, name=self.s3_bucket_name + self.logo_ad)
    self.set_x(10)
    self.set_text_color(143,143,143)
    self.cell(w, 9, ust_yazi, 0, 0, 'L')
    self.set_line_width(0.1)
    self.set_draw_color(243,243,243)
    self.line(105, 40, 105, 270)
    self.ln(10)

  def coktan_secmeli_yerlestir(self, siklar):
    ilk_y = self.get_y()
    sonuc = True
    for x, y in enumerate(siklar):
      y = self.class_kaldir(y)
      if self.sag:
        koordinatlar = [110, 130, 150, 170, 190]
        sinirlar = [130, 150, 170, 190, 210]
      else:
        koordinatlar = [10, 30, 50, 70, 90]
        sinirlar = [30, 50, 70, 90, 110]
      self.set_x(int(koordinatlar[x]))
      if self.get_x() + self.get_string_width(y) + 8 >= sinirlar[x]:
        sonuc = False
    if sonuc:
      for x, y in enumerate(siklar):
        self.set_y(ilk_y)
        if self.sag:
          self.set_x(110)
          self.set_right_margin(0)
          koordinatlar = [110, 130, 150, 170, 190]
        else:
          self.set_x(10)
          self.set_right_margin(100)
          koordinatlar = [10, 30, 50, 70, 90]
        self.set_x(int(koordinatlar[x]))
        self.write_html(self.sik_harfleri[x])
        y = self.p_kaldir(y)
        self.subscript(y)
      self.ln(3)
    else:
      if len(siklar) > 4:
        self.coktan_secmeli_yerlestir2(siklar)
      else:
        self.coktan_secmeli_yerlestir3(siklar)

  def coktan_secmeli_yerlestir2(self, siklar):
    ilk_y = self.get_y()
    if self.sag:
      koordinatlar = [110, 140, 170, 125, 155]
      sinirlar = [140, 170, 210, 155, 210]
    else:
      koordinatlar = [10, 40, 70, 25, 55]
      sinirlar = [40, 70, 100, 55, 100]
    sonuc = True
    for x, y in enumerate(siklar):
      y = self.class_kaldir(y)
      self.set_x(int(koordinatlar[x]))
      if self.get_x() + self.get_string_width(y) + 5 >= sinirlar[x]:
        sonuc = False
    son_koord = 0
    if sonuc:
      self.set_right_margin(0)
      for x, y in enumerate(siklar):
        self.set_y(ilk_y)
        if x == 3 or x == 4:
          self.set_y(self.get_y() + 5)
        if x != 0 and son_koord > 110:
          self.sag = True
        if self.sag:
          koordinatlar = [110, 140, 170, 125, 155, 190]
        else:
          koordinatlar = [10, 40, 70, 25, 55, 90]
        self.set_x(int(koordinatlar[x]))
        self.write_html(self.sik_harfleri[x])
        son_koord = self.get_x()
        y = self.p_kaldir(y)
        self.subscript(y)
      self.ln(1)
    else:
      self.coktan_secmeli_yerlestir3(siklar)

  def coktan_secmeli_yerlestir3(self, siklar):
    ilk_y = self.get_y()
    if self.sag:
      koordinatlar = [110, 155, 110, 155, 130]
      sinirlar = [155, 200, 155, 200, 210]
    else:
      koordinatlar = [10, 55, 10, 55, 30]
      sinirlar = [55, 100, 55, 100, 110]
    sonuc = True
    for x, y in enumerate(siklar):
      y = self.class_kaldir(y)
      self.set_x(int(koordinatlar[x]))
      if self.get_x() + self.get_string_width(y) + 8 >= sinirlar[x]:
        sonuc = False
    son_koord = 0
    if sonuc:
      for x, y in enumerate(siklar):
        if x == 2:
          self.set_y(self.get_y() + 5)
        if x == 3:
          self.set_y(self.get_y())
        elif x == 4:
          self.set_y(self.get_y() + 5)
          if self.sag:
            self.set_x(130)
          else:
            self.set_x(30)
        if x != 0 and son_koord > 110:
          self.sag = True
        if self.sag:
          koordinatlar = [110, 155, 110, 155, 130]
        else:
          koordinatlar = [10, 55, 10, 55, 30]
        self.set_x(int(koordinatlar[x]))
        self.write_html(self.sik_harfleri[x])
        son_koord = self.get_x()
        y = self.p_kaldir(y)
        self.subscript(y)
        if x == len(siklar) - 1:
          self.ln(2)
    else:
      self.coktan_secmeli_yerlestir4(siklar)

  def coktan_secmeli_yerlestir4(self, siklar):
    sonuc = True
    for x, y in enumerate(siklar):
      if self.sag:
        self.set_x(110)
      else:
        self.set_x(10)
      self.write_html(self.sik_harfleri[x])
      #self.set_x(self.get_x() + 5)
      if self.sag:
        self.set_left_margin(114)
        self.set_x(114)
      else:
        self.set_left_margin(14)
        self.set_x(14)
      y = self.p_kaldir(y)
      self.subscript(y)
      if x != len(siklar) -1:
        self.ln(5)

  def coktan_secmeli_gorselli1(self, siklar, user_id):
    px_sinir = (110, 100)
    yeni_siklar, en_uzun_piksel, _ = self.sik_yazdir(siklar, user_id, px_sinir)

    if self.sag:
      koordinatlar = [110, 157, 110, 157, 130]
    else:
      koordinatlar = [10, 57, 10, 57, 30]
    yukseklik = (en_uzun_piksel * 0.2645833333) + 3
    y_konum = self.get_y()
    
    for x, y in enumerate(yeni_siklar):
      if x == 2 or x == 4:
        y_konum += yukseklik
        self.set_y(y_konum)
      else:
        self.set_y(y_konum)

      if self.sag:
        koordinatlar = [110, 157, 110, 157, 130]
      else:
        koordinatlar = [10, 57, 10, 57, 30]
      self.set_x(int(koordinatlar[x]))
      self.write_html(self.sik_harfleri[x])
      # son_koord = self.get_x()
      self.image(name=y[0], # dosya adı
                w=min((y[1] * 0.2645833333), 38), # genişlik
                h=(min((y[2] * 0.2645833333), px_sinir[1])), # yükseklik
                x=(self.get_x() + 2)) # yatay eksen
      self.ln(3)
      os.remove(y[0])

  def coktan_secmeli_gorselli2(self, siklar, user_id):
    px_sinir = (100, 80)
    yeni_siklar, en_uzun_piksel, _ = self.sik_yazdir(siklar, user_id, px_sinir)

    if self.sag:
      koordinatlar = [110, 140, 170, 127, 157]
    else:
      koordinatlar = [10, 40, 70, 27, 57]
    yukseklik = (en_uzun_piksel * 0.2645833333) + 3
    y_konum = self.get_y()
    
    for x, y in enumerate(yeni_siklar):
      if x == 3:
        y_konum += yukseklik
        self.set_y(y_konum)
      else:
        self.set_y(y_konum)
      # if x != 0 and son_koord > 110:
      #   self.sag = True
      if self.sag:
        koordinatlar = [110, 140, 170, 127, 157]
      else:
        koordinatlar = [10, 40, 70, 27, 57]
      self.set_x(int(koordinatlar[x]))
      self.write_html(self.sik_harfleri[x])
      # son_koord = self.get_x()
      self.image(name=y[0], #dosya adı
                w=min((y[1] * 0.2645833333), 23), #genişlik
                h=(min((y[2] * 0.2645833333), px_sinir[1])), #yükseklik
                x=(self.get_x() + 2)) #yatay eksen
      self.ln(1)
      os.remove(y[0])
  
  def coktan_secmeli_gorselli3(self, siklar, user_id):
    px_sinir = (300, 60)
    yeni_siklar, en_uzun_piksel, yukseklikler = self.sik_yazdir(siklar, user_id, px_sinir)

    if self.sag:
      self.set_x(110)
    else:
      self.set_x(10)
    y_konum = self.get_y()
    
    for x, y in enumerate(yeni_siklar):
      if x == 0:
        self.set_y(y_konum)
      else:
        y_konum += (yukseklikler[x-1] * 0.2645833333) + 4
        self.set_y(y_konum)
      if self.sag:
        self.set_x(110)
      else:
        self.set_x(10)
      self.write_html(self.sik_harfleri[x])
      # son_koord = self.get_x()
      self.image(name=y[0], #dosya adı
                w=min((y[1] * 0.2645833333), 100), #genişlik
                h=(min((y[2] * 0.2645833333), px_sinir[1])), #yükseklik
                x=(self.get_x() + 2)) #yatay eksen
      os.remove(y[0])

  def coktan_secmeli_gorselli4(self, siklar, user_id):
    px_sinir = (38, 38)
    yeni_siklar, en_uzun_piksel, _ = self.sik_yazdir(siklar, user_id, px_sinir)

    if self.sag:
      koordinatlar = [110, 130, 150, 170, 190]
    else:
      koordinatlar = [10, 30, 50, 70, 90]
    sik_harfleri = ['A)', 'B)', 'C)', 'D)', 'E)']
    y_konum = self.get_y()
    
    kapladigi_uzunluk = 0
    for x, y in enumerate(yeni_siklar):
      self.set_y(y_konum)
      if self.sag:
        koordinatlar = [110, 130, 150, 170, 190]
      else:
        koordinatlar = [10, 30, 50, 70, 90]
      self.set_x(int(koordinatlar[x]))
      self.write_html(self.sik_harfleri[x])

      if y[2] * 0.2645833333 > kapladigi_uzunluk:
        kapladigi_uzunluk = y[2] * 0.2645833333
      self.image(name=y[0], # dosya adı
                w=min((y[1] * 0.2645833333), 10), # genişlik
                h=(min((y[2] * 0.2645833333), 14)), #biraz daha uzun olabilir, 8 idi, 14 olarak güncelledim.
                x=(self.get_x() + 1), #yatay eksen
                ) 
      os.remove(y[0])
    self.ln(round(kapladigi_uzunluk/4.5))
  
  def coktan_secmeli(self, soru, siklar, gorsel, secim, user_id, *args):
    self.sayi += 1
    self.ln(8)
    for x, y in enumerate(siklar):
      if self.class_kaldir(siklar[x]) == '' and x != 4:
        raise Exception('En az dört şık olmalı.')
    if len(siklar) == 5 and self.class_kaldir(siklar[4]) == '':
      siklar.pop(4)
    for arg in args:
      if self.sag and self.get_y() + arg > 280:
        self.add_page()
        self.sag = False
        self.set_x(10)
        if self.page_no() == 1:
          self.set_y(25)
        else:
          self.set_y(20)
        self.set_right_margin(110)
        self.set_left_margin(10)
      elif not self.sag and self.get_y() + arg > 280:
        self.sag = True
        self.set_x(110)
        if self.page_no() == 1:
          self.set_y(25)
        else:
          self.set_y(20)
        self.set_right_margin(10)
        self.set_left_margin(110)
        
    if self.sag:
      konum = 110
      self.set_right_margin(10)
      self.set_left_margin(110)
    else:
      konum = 10
      self.set_left_margin(10)
      self.set_right_margin(110)

    soru = self.soru_temizle(soru)
    soru = str(self.sayi) + '. ' + soru
    self.set_x(konum)
    self.set_font('ArialUnicode','B', 9)
    if current_app.config['S3_BUCKET_NAME'] in soru:
      self.gorsel_math(soru, user_id)
    else:
      self.subscript(soru)
    self.ln(6)
    self.set_x(konum)
    if gorsel == True:
      if int(secim) == 1:
        self.coktan_secmeli_gorselli1(siklar, user_id)
      elif int(secim) == 2:
        if siklar[-1] == current_app.config['S3_BUCKET_NAME'] + 'pdfs/e.png':
          self.coktan_secmeli_gorselli1(siklar, user_id)
        else:
          self.coktan_secmeli_gorselli2(siklar, user_id)
      elif int(secim) == 3:
        self.coktan_secmeli_gorselli3(siklar, user_id)
      elif int(secim) == 4:
        self.coktan_secmeli_gorselli4(siklar, user_id)
    else:
      self.coktan_secmeli_yerlestir(siklar)

  def dogru_yanlis(self, ana_soru, sorular):
    self.sayi += 1
    self.ln(8)
    if self.sag:
      self.set_x(110)
    else:
      self.set_x(10)
    self.set_font('ArialUnicode', 'B', 9)
    ana_soru = str(self.sayi) + '. ' + ana_soru
    self.multi_cell(90, 4, ana_soru)
    self.set_font('ArialUnicode', '', 9)
    self.cell(95, 4, ln=True)
    for soru in sorular:
      if self.sag:
        if self.get_y() >= 270:
          self.add_page()
          self.sag = False
          if self.page_no() == 1:
            self.set_y(25)
          else:
            self.set_y(20)
          upper_left = 10
          self.set_line_width(0.61)
          self.rect(upper_left, self.get_y(), 7, 6)
          self.set_x(17)
          self.multi_cell(85, 6, soru)
          if sorular[-1] != soru:
            self.ln(3)
        else:
          self.set_x(116)
          soru = '  ' + soru
          upper_left = 110
          self.set_line_width(0.61)
          self.rect(upper_left, self.get_y(), 7, 6)
          self.multi_cell(85, 6, soru)
          if sorular[-1] != soru:
            self.ln(3)
      else:
        if self.get_y() >= 270:
          self.sag = True
          if self.page_no() == 1:
            self.set_y(25)
          else:
            self.set_y(20)
          self.set_x(116)
          soru = '  ' + soru
          upper_left = 110
          self.set_line_width(0.61)
          self.rect(upper_left, self.get_y(), 7, 6)
          self.multi_cell(85, 6, soru)
          if sorular[-1] != soru:
            self.ln(3)
        else:
          self.set_x(16)
          soru = '  ' + soru
          upper_left = 10
          self.set_line_width(0.61)
          self.rect(upper_left, self.get_y(), 7, 6)
          self.multi_cell(85, 6, soru)
          if sorular[-1] != soru:
            self.ln(3)
    self.set_y(self.get_y() - 5)

  def bosluk_doldurma(self, soru, paragraf, sorular, aciklama, tablo):
    self.sayi += 1
    self.ln(8)
    konum = self.get_y()
    if self.sag:
      self.set_x(110)
    else:
      self.set_x(10)
    if aciklama != '':
      self.set_font('ArialUnicode', '', 9)
      self.multi_cell(90, 6, aciklama)
    soru = str(self.sayi) + '. ' + soru
    self.set_font('ArialUnicode', 'B', 9)
    self.multi_cell(90, 4, soru)
    if tablo != '':
      self.ln(1)
      self.set_font('ArialUnicode', '', 9)
      self.set_line_width(0.3)
      if self.sag:
        self.set_x(110)
      else:
        self.set_x(10)
      self.multi_cell(90, 4, tablo, align='C', border=1)
    self.cell(95, 4, ln=True)
    if paragraf and self.sag:
      self.set_x(110)
      self.set_font('ArialUnicode', '', 9)
      sorular = re.split("[\_]+[^a-zA-Z0-9?., !]+[\_]", paragraf)
      bosluklar = re.findall("[\_]+[^a-zA-Z0-9?., !]+[\_]", paragraf)
      liste = zip(sorular, bosluklar)
      for x in liste:
        if self.sag:
          self.set_left_margin(110)
          self.set_right_margin(10)
          sinir = 199
        else:
          self.set_left_margin(10)
          self.set_right_margin(110)
          sinir = 110
        self.write(11, x[0])
        y = x[1]
        if len(y) > 50:
          y = y[:43]
        elif len(y) < 10:
          y = '__________'
        if not y.startswith(' '):
          y = ' ' + y
        if not y.endswith(' '):
          y = y + ' '
        genislik = len(y) * 3
        self.set_font('ArialUnicode', '', 28)
        if self.get_x() + genislik > sinir:
          self.set_y(self.get_y() + 12)
          self.cell(5, 9, ' [')
          self.set_font('ArialUnicode', '', 9)
          self.set_text_color(242,242,242)
          self.cell((genislik * 0.6), 12, y)
          self.set_font('ArialUnicode', '', 28)
          self.set_text_color(0,0,0)
          if len(y) > 40:
            self.set_x(self.get_x() + 2)
          else:
            pass
          self.cell(3, 9, '] ')
          self.set_font('ArialUnicode', '', 9)
          #self.set_x(self.get_x() + 5)
        else:
          #self.set_y(self.get_y() + 5)
          self.cell(5, 9, ' [')
          self.set_font('ArialUnicode', '', 9)
          self.set_text_color(242,242,242)
          self.cell((genislik * 0.6), 12, y)
          self.set_font('ArialUnicode', '', 28)
          self.set_text_color(0,0,0)
          if len(y) > 40:
            self.set_x(self.get_x() + 2)
          else:
            pass
          self.cell(3, 9, '] ')
          self.set_font('ArialUnicode', '', 9)

    elif paragraf and not self.sag:
      self.set_left_margin(10)
      self.set_right_margin(110)
      self.set_x(10)
      self.set_font('ArialUnicode', '', 9)
      sorular = re.split("[\_]+[^a-zA-Z0-9?.,!]+[\_]", paragraf)
      bosluklar = re.findall("[\_]+[^a-zA-Z0-9?.,!]+[\_]", paragraf)
      liste = zip(sorular, bosluklar)
      for x in liste:
        self.write(11, x[0])
        if self.sag:
          self.set_left_margin(110)
          self.set_right_margin(10)
          sinir = 199
        else:
          self.set_left_margin(10)
          self.set_right_margin(110)
          sinir = 110
        y = x[1]
        if len(y) > 50:
          y = y[:43]
        elif len(y) < 10:
          y = '__________'
        if not y.startswith(' '):
          y = ' ' + y
        if not y.endswith(' '):
          y = y + ' '
        genislik = len(y) * 3
        self.set_font('ArialUnicode', '', 28)
        if self.get_x() + genislik > sinir:
          self.set_y(self.get_y() + 12)
          self.cell(5, 9, ' [')
          self.set_font('ArialUnicode', '', 9)
          konum = self.get_x()
          self.set_text_color(242,242,242)
          self.cell((genislik * 0.6), 12, y)
          self.set_font('ArialUnicode', '', 28)
          self.set_text_color(0,0,0)
          if len(y) > 40:
            self.set_x(self.get_x() + 2)
          else:
            pass
          self.cell(3, 9, '] ')
          self.set_font('ArialUnicode', '', 9)
          #self.set_x(self.get_x() + 5)
        else:
          #self.set_y(self.get_y() + 5)
          self.cell(5, 9, ' [')
          self.set_font('ArialUnicode', '', 9)
          self.set_text_color(242,242,242)
          self.cell((genislik * 0.6), 12, y)
          self.set_font('ArialUnicode', '', 28)
          self.set_text_color(0,0,0)
          if len(y) > 40:
            self.set_x(self.get_x() + 2)
          else:
            pass
          self.cell(3, 9, '] ')
          self.set_font('ArialUnicode', '', 9)
    self.write(11, sorular[-1])
    self.ln(6)

  def gorsel_math(self, soru, user_id):
    ayristirma = re.split("<img([\\s\\S]+?)>", soru)
    if '</p><p>' in ayristirma:
      ayristirma.remove('</p><p>')
    for idx, x in enumerate(ayristirma):
      if self.sag:
        konum = 110
        sinir = 210
        self.set_right_margin(10)
        self.set_left_margin(110)
      else:
        konum = 10
        sinir = 110
        self.set_left_margin(10)
        self.set_right_margin(110)
      self.set_x(konum)
      if not x.startswith(' src="'):
        if f'https://{s3_name}' in ayristirma[idx-1]:
          self.set_y(self.get_y() - 3)
          if idx == len(ayristirma) - 1:
            #eğer soru cümlesiyse biraz daha yakınlaştır
            self.set_y(self.get_y() - 3)
          if idx != len(ayristirma) - 1 and f'https://{s3_name}' in ayristirma[idx+1]:
            self.set_y(self.get_y() - 2)
        self.subscript(x)
        if idx != len(ayristirma) - 1 and idx != 0 and f'https://{s3_name}' in ayristirma[idx+1]:
          self.ln(2)
      else:
        soru = soru.replace('<img' + x + '>', '')
        src = re.findall("src=([\\s\\S]+?)style", x)
        width = re.findall("width: ([\\s\\S]+?);", x)

        kayit_yolu = os.path.join(current_app.root_path, f'static/fpdf/pdf_files/gorseller/{user_id}/' + os.path.basename(src[0][1:-2]))

        key = src[0][1:-2].split(current_app.config['S3_BUCKET_NAME'])
        s3_client.download_file(s3_name, key[1], os.path.join(kayit_yolu))

        genislik = min((int(float(width[0].replace('px', ''))) * 0.6 ) * 0.2645833333, 100)
        
        onceki = str(ayristirma[idx-1]).replace('.', '')

        if ''.join(onceki[:-1]).isdigit() and not len(onceki) > 2:
          pass
        elif f'https://{s3_name}' in onceki:
          self.ln(3)
        else:
          self.set_y(self.get_y() - 3)
        self.image(name=kayit_yolu, x=konum+5, w=genislik)
        
        os.remove(kayit_yolu)

  def gorsel_cv2(self, gorsel, rakam, user_id):
    gercek_ad = unquote(os.path.basename(gorsel))
    ad, _ext = os.path.splitext(gercek_ad)
    kayit_yolu = os.path.join(current_app.root_path, f'static/fpdf/pdf_files/gorseller/{user_id}/' + gercek_ad)
    key = gorsel.split(current_app.config['S3_BUCKET_NAME'])
    s3_client.download_file(s3_name, unquote(key[1]), kayit_yolu)
    
    if _ext == '.png':
      img = cv2.imread(kayit_yolu, cv2.IMREAD_UNCHANGED)
    else:
      img = cv2.imread(kayit_yolu, 0)
    landscape = 'yatay'
    scale_percent = 99 # percent of original size
    if rakam == 1:
      yatay_sinir = 85
      dikey_sinir = 128
    elif rakam == 2:
      yatay_sinir = 170
      dikey_sinir = 255
    else:
      yatay_sinir = 340
      dikey_sinir = 510
    if img.shape[1]/img.shape[0] > 1 or img.shape[1]/img.shape[0] == 1: #görsel yatay veya köşeler eşit
      width = int(img.shape[1] * scale_percent / 100)
      height = int(img.shape[0] * scale_percent / 100)
      if not width < yatay_sinir:
        while width > yatay_sinir:
          scale_percent = scale_percent - 0.1
          width = int(img.shape[1] * scale_percent / 100)
          height = int(img.shape[0] * scale_percent / 100)

    elif img.shape[1]/img.shape[0] < 1: #görsel dikey
      width = int(img.shape[1] * scale_percent / 100)
      height = int(img.shape[0] * scale_percent / 100)
      landscape = 'dikey'
      if not height < dikey_sinir:
        while height > dikey_sinir:
          scale_percent = scale_percent - 0.1
          width = int(img.shape[1] * scale_percent / 100)
          height = int(img.shape[0] * scale_percent / 100)

    dim = (width, height)

    # resize image
    # resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    yeni_ad = kayit_yolu.replace(_ext, '_gorselresized' + _ext)
    cv2.imwrite(f'{yeni_ad}', img, [int(cv2.IMWRITE_JPEG_QUALITY), 40,IMWRITE_JPEG_OPTIMIZE])
    os.remove(kayit_yolu)

    bilgiler = {'landscape': landscape, 'boyutlar': dim, 'dosya': yeni_ad}
    return bilgiler
  
  def gorselekle(self, gorsel, rakam, user_id):
    self.ln(8)
    if self.sag:
      self.set_x(110)
      konum = 110
    else:
      self.set_x(10)
      konum = 10

    bilgiler = self.gorsel_cv2(gorsel, rakam, user_id)
  
    gorsel = bilgiler['dosya']
    if bilgiler['landscape'] == 'dikey':
      self.image(name=gorsel, 
                w=min(int(bilgiler['boyutlar'][0] * 0.2645833333), 90), 
                h=int(bilgiler['boyutlar'][1] * 0.2645833333))
    else:
      self.image(name=gorsel, 
                w=int(bilgiler['boyutlar'][0] * 0.2645833333), 
                h=int(bilgiler['boyutlar'][1] * 0.2645833333))
    self.set_y(self.get_y() - 5)
    os.remove(gorsel)

  def eslestirme(self, soru, ilk_liste, ikinci_liste, yazdirma_turu):
    #ilk listenin öğelerinin uzunluğu = 24 olmalı
    self.sayi += 1
    self.ln(8)
    if self.sag:
      self.set_x(110)
    else:
      self.set_x(10)
    self.set_font('ArialUnicode', 'B', 9)
    soru = str(self.sayi) + '. ' + soru
    self.multi_cell(90, 4, soru)
    self.set_font('ArialUnicode', '', 9)
    self.cell(95, 4, ln=True)
    e_sayac = 0
    if yazdirma_turu == 'altalta':
      for idx, soru in enumerate(ilk_liste):
        if self.sag:
          if self.get_y() >= 270:
            self.add_page()
            self.sag = False
            if self.page_no() == 1:
              self.set_y(25)
            else:
              self.set_y(20)
            upper_left = 10
            self.set_line_width(0.61)
            self.rect(upper_left, self.get_y(), 7, 6)
            self.set_x(16)
            soru = ' ' + soru
            self.set_x(self.get_x() + 1)
            self.multi_cell(83, 6, soru)
            self.ln(3)
          else:
            upper_left = 110
            self.set_line_width(0.61)
            self.rect(upper_left, self.get_y(), 7, 6)
            self.set_x(118)
            soru = ' ' + soru
            self.set_x(self.get_x() + 1)
            self.multi_cell(83, 6, soru)
            self.ln(3)
        else:
          self.set_line_width(0.61)
          if self.get_y() >= 270:
            upper_left = 110
            if self.page_no() == 1:
              self.set_y(25)
            else:
              self.set_y(20)
            self.sag = True
            self.rect(upper_left, self.get_y(), 7, 6)
            self.set_x(118)
            soru = ' ' + soru
            self.set_x(self.get_x() + 1)
            self.multi_cell(83, 6, soru)
            self.ln(3)
          else:
            upper_left = 10
            self.rect(upper_left, self.get_y(), 7, 6)
            self.set_x(16)
            soru = ' ' + soru
            self.set_x(self.get_x() + 1)
            self.multi_cell(83, 6, soru)
            self.ln(3)
      for idx, soru in enumerate(ikinci_liste):
        eslesecek = self.lst[e_sayac]+ '. ' + ikinci_liste[e_sayac]
        e_sayac += 1
        if self.sag:
          self.set_x(110)
        else:
          self.set_x(10)
        self.multi_cell(90, 4, eslesecek, align='L')
        if idx != len(ikinci_liste) - 1:
          self.ln(1)
        else:
          self.ln(2)
    else:
      for idx, soru in enumerate(ilk_liste):
        if self.sag:
          #self.set_x(110)
          if self.get_y() >= 270:
            self.add_page()
            self.sag = False
            if self.page_no() == 1:
              self.set_y(25)
            else:
              self.set_y(20)
            upper_left = 10
            self.set_line_width(0.61)
            self.rect(upper_left, self.get_y(), 7, 6)
            self.set_x(18)
            soru = ' ' + soru
            self.cell(43, 7, soru, ln=False)
            harf_ekle = True
            try:
              eslesecek = ikinci_liste[idx]
            except:
              eslesecek = ''
              harf_ekle = False
            if harf_ekle:
              eslesecek = self.lst[idx]+ '. ' + ikinci_liste[idx]
              self.multi_cell(43, 7, eslesecek)
            else:
              self.multi_cell(43, 7, '')
            if idx != len(ilk_liste) -1:
              self.ln(2)
          else:
            upper_left = 110
            self.set_line_width(0.61)
            self.rect(upper_left, self.get_y(), 7, 6)
            self.set_x(118)
            soru = ' ' + soru
            self.cell(43, 7, soru, ln=False)
            harf_ekle = True
            try:
              eslesecek = ikinci_liste[idx]
            except:
              eslesecek = ''
              harf_ekle = False
            if harf_ekle:
              eslesecek = self.lst[idx]+ '. ' + ikinci_liste[idx]
              self.multi_cell(43, 7, eslesecek)
            else:
              self.multi_cell(43, 7, '')
            if idx != len(ilk_liste) -1:
              self.ln(2)
        else:
          self.set_line_width(0.61)
          if self.get_y() >= 270:
            upper_left = 110
            if self.page_no() == 1:
              self.set_y(25)
            else:
              self.set_y(20)
            self.sag = True
            self.rect(upper_left, self.get_y(), 7, 6)
            self.set_x(118)
            soru = ' ' + soru
            self.cell(43, 7, soru, ln=False)
            harf_ekle = True
            try:
              eslesecek = ikinci_liste[idx]
            except:
              eslesecek = ''
              harf_ekle = False
            if harf_ekle:
              eslesecek = self.lst[idx]+ '. ' + ikinci_liste[idx]
              self.multi_cell(43, 7, eslesecek)
            else:
              self.multi_cell(43, 7, '')
            if idx != len(ilk_liste) -1:
              self.ln(2)
          else:
            upper_left = 10
            self.rect(upper_left, self.get_y(), 7, 6)
            self.set_x(18)
            soru = ' ' + soru
            self.cell(43, 7, soru, ln=False)
            harf_ekle = True
            try:
              eslesecek = ikinci_liste[idx]
            except:
              eslesecek = ''
              harf_ekle = False
            if harf_ekle:
              eslesecek = self.lst[idx]+ '. ' + ikinci_liste[idx]
              self.multi_cell(43, 7, eslesecek)
            else:
              self.multi_cell(43, 7, '')
            if idx != len(ilk_liste) -1:
              self.ln(2)
    self.set_y(self.get_y() - 5)

class Dummy(PDF):
  def kontrol(self, x, y, soru, siklar, gorsel_var_mi, secim, user_id):
    self.add_page()
    ilk_y = self.get_y()
    self.coktan_secmeli(soru, siklar, gorsel_var_mi, secim, user_id)
    fark = self.get_y() - ilk_y
    return fark
    
class PDFTEK(FPDF, HTMLMixin, Base):

  def adsoyad(self, dil):
    self.set_font('ArialUnicode', '', 11)
    if dil == 'tr':
      self.cell(100, 6, txt='AD SOYAD:', border=1)
      self.cell(15, 6, txt='')
      self.cell(100, 6, txt='Sınıf/Numara: ______________')
    else:
      self.cell(103, 6, txt='NAME SURNAME:', border=1)
      self.cell(15, 6, txt='')
      self.cell(100, 6, txt='Class/Number: ______________')
    self.set_y(20)
  
  def footer(self):
    # Position at 1.5 cm from bottom
    self.set_y(-15)
    self.set_text_color(100,100,100)
    self.set_font('ArialUnicode', 'I', 8)
    # Page number
    self.cell(0, 9, self.alt_yazi, 0, 0, 'L')

  def header(self):
    self.set_y(5)
    self.set_font('ArialUnicode', '', 8)
    ust_yazi = self.ust_yazi
    w = self.get_string_width(ust_yazi) + 6
    if self.logo_ad != '':
      self.image(x=190, y=1, w=15, h=15, name=self.s3_bucket_name + self.logo_ad)
    self.set_x(10)
    self.set_text_color(143,143,143)
    self.cell(w, 9, ust_yazi, 0, 0, 'C')
    self.ln(10)

  def coktan_secmeli_yerlestir(self, siklar):
    ilk_y = self.get_y()
    sonuc = True
    koordinatlar = [10, 35, 60, 85, 110]
    sinirlar = [35, 60, 85, 110, 190]
    for x, y in enumerate(siklar):
      y = self.class_kaldir(y)
      self.set_x(int(koordinatlar[x]))
      if self.get_x() + self.get_string_width(y) + 8 >= sinirlar[x]:
        sonuc = False
    if sonuc:
      for x, y in enumerate(siklar):
        self.set_y(ilk_y)
        self.set_x(int(koordinatlar[x]))
        self.write_html(self.sik_harfleri[x])
        y = self.p_kaldir(y)
        self.subscript(y)
      self.ln(3)
    else:
      if len(siklar) > 4:
        self.coktan_secmeli_yerlestir2(siklar)
      else:
        self.coktan_secmeli_yerlestir3(siklar)

  def coktan_secmeli_yerlestir2(self, siklar):
    ilk_y = self.get_y()
    koordinatlar = [10, 40, 70, 25, 55, 95]
    sinirlar = [40, 70, 95, 55, 135]
    
    sonuc = True
    for x, y in enumerate(siklar):
      self.set_x(int(koordinatlar[x]))
      y = self.class_kaldir(y)
      if self.get_x() + self.get_string_width(y) + 5 >= sinirlar[x]:
        sonuc = False
    son_koord = 0
    if sonuc:
      for x, y in enumerate(siklar):
        self.set_y(ilk_y)
        if x == 3 or x == 4:
          self.set_y(self.get_y() + 8)
        
        koordinatlar = [10, 40, 70, 25, 55, 95]
        self.set_x(int(koordinatlar[x]))
        self.write_html(self.sik_harfleri[x])
        son_koord = self.get_x()
        y = self.p_kaldir(y)
        self.subscript(y)
      self.ln(1)
    else:
      self.coktan_secmeli_yerlestir3(siklar)

  
  def coktan_secmeli_yerlestir3(self, siklar):
    ilk_y = self.get_y()
    koordinatlar = [10, 60, 10, 60, 30]
    sinirlar = [60, 110, 60, 110, 190]
    
    sonuc = True
    for x, y in enumerate(siklar):
      y = self.class_kaldir(y)
      self.set_x(int(koordinatlar[x]))
      if self.get_x() + self.get_string_width(y) + 5 >= sinirlar[x]:
        sonuc = False
    son_koord = 0
    if sonuc:
      for x, y in enumerate(siklar):
        if x == 2:
          self.set_y(self.get_y() + 8)
        if x == 3:
          self.set_y(self.get_y())
        elif x == 4:
          self.set_y(self.get_y() + 8)
          self.set_x(30)
        koordinatlar = [10, 60, 10, 60, 30]
        self.set_x(int(koordinatlar[x]))
        self.write_html(self.sik_harfleri[x])
        son_koord = self.get_x()
        y = self.p_kaldir(y)
        self.subscript(y)
        if x == len(siklar) - 1:
          self.ln(2)
    else:
      self.coktan_secmeli_yerlestir4(siklar)

  def coktan_secmeli_yerlestir4(self, siklar):
    sonuc = True
    for x, y in enumerate(siklar):
      self.set_x(10)
      self.write_html(self.sik_harfleri[x])
      self.set_x(14)
      self.set_left_margin(14)
      y = self.p_kaldir(y)
      self.subscript(y)
      if x != len(siklar) -1:
        self.ln(5)

  def coktan_secmeli_gorselli1(self, siklar, user_id):
    px_sinir = (110, 100)
    yeni_siklar, en_uzun_piksel, _ = self.sik_yazdir(siklar, user_id, px_sinir)

    koordinatlar = [10, 57, 10, 57, 30]
    sik_harfleri = ['A)', 'B)', 'C)', 'D)', 'E)']
    yukseklik = (en_uzun_piksel * 0.2645833333) + 4
    y_konum = self.get_y()
    
    for x, y in enumerate(yeni_siklar):
      if x == 2 or x == 4:
        y_konum += yukseklik
        self.set_y(y_konum)
      else:
        self.set_y(y_konum)
      
      koordinatlar = [10, 57, 10, 57, 30]
      
      self.set_x(int(koordinatlar[x]))
      self.set_font('ArialUnicode', 'B', 9)
      self.cell(5, 8, sik_harfleri[x])
      # son_koord = self.get_x()
      self.image(name=y[0], # dosya adı
                w=min((y[1] * 0.2645833333), 38), # genişlik
                h=(min((y[2] * 0.2645833333), px_sinir[1])), # yükseklik
                x=(self.get_x() + 2)) # yatay eksen
      self.ln(3)
      os.remove(y[0])


  def coktan_secmeli_gorselli2(self, siklar, user_id):
    px_sinir = (100, 80)
    yeni_siklar, en_uzun_piksel, _ = self.sik_yazdir(siklar, user_id, px_sinir)

    if self.sag:
      koordinatlar = [110, 140, 170, 127, 157]
    else:
      koordinatlar = [10, 40, 70, 27, 57]
    sik_harfleri = ['A)', 'B)', 'C)', 'D)', 'E)']
    yukseklik = (en_uzun_piksel * 0.2645833333) + 3
    y_konum = self.get_y()
    
    for x, y in enumerate(yeni_siklar):
      if x == 3:
        y_konum += yukseklik
        self.set_y(y_konum)
      else:
        self.set_y(y_konum)

      koordinatlar = [10, 40, 70, 27, 57]
      self.set_x(int(koordinatlar[x]))
      self.set_font('ArialUnicode', 'B', 9)
      self.cell(4, 8, sik_harfleri[x])
      # son_koord = self.get_x()
      self.image(name=y[0], #dosya adı
                w=min((y[1] * 0.2645833333), 23), #genişlik
                h=(min((y[2] * 0.2645833333), px_sinir[1])), #yükseklik
                x=(self.get_x() + 2)) #yatay eksen
      self.ln(1)
      os.remove(y[0])

  def coktan_secmeli_gorselli3(self, siklar, user_id):
    px_sinir = (400, 60)
    yeni_siklar, en_uzun_piksel, yukseklikler = self.sik_yazdir(siklar, user_id, px_sinir)

    if self.sag:
      self.set_x(110)
    else:
      self.set_x(10)
    sik_harfleri = ['A)', 'B)', 'C)', 'D)', 'E)']
    y_konum = self.get_y()
    
    for x, y in enumerate(yeni_siklar):
      if x == 0:
        self.set_y(y_konum)
      else:
        y_konum += (yukseklikler[x-1] * 0.2645833333) + 4
        self.set_y(y_konum)
      if self.sag:
        self.set_x(110)
      else:
        self.set_x(10)
      self.set_font('ArialUnicode', 'B', 9)
      self.cell(4, 8, sik_harfleri[x])
      # son_koord = self.get_x()
      self.image(name=y[0], #dosya adı
                w=min((y[1] * 0.2645833333), 100), #genişlik
                h=(min((y[2] * 0.2645833333), px_sinir[1])), #yükseklik
                x=(self.get_x() + 2)) #yatay eksen
      os.remove(y[0])

  def coktan_secmeli_gorselli4(self, siklar, user_id):
    px_sinir = (48, 48)
    yeni_siklar, en_uzun_piksel, _ = self.sik_yazdir(siklar, user_id, px_sinir)

    koordinatlar = [10, 35, 60, 85, 110]
    y_konum = self.get_y()
    
    kapladigi_uzunluk = 0
    for x, y in enumerate(yeni_siklar):
      self.set_y(y_konum)
      koordinatlar = [10, 30, 50, 70, 90]
      self.set_x(int(koordinatlar[x]))
      self.write_html(self.sik_harfleri[x])

      if y[2] * 0.2645833333 > kapladigi_uzunluk:
        kapladigi_uzunluk = y[2] * 0.2645833333
      self.image(name=y[0], # dosya adı
                w=min((y[1] * 0.2645833333), 12), # genişlik
                h=(min((y[2] * 0.2645833333), 18)),
                x=(self.get_x() + 1), #yatay eksen
                y=(self.get_y() - 1) #dikey eksen
                ) 
      os.remove(y[0])
    self.ln(round(kapladigi_uzunluk/1.8))

  def coktan_secmeli(self, soru, siklar, gorsel, secim, user_id, *args):
    self.sayi += 1
    self.ln(8)
    for x, y in enumerate(siklar):
      if self.class_kaldir(siklar[x]) == '' and x != 4:
        raise Exception('En az dört şık olmalı.')
    if len(siklar) == 5 and self.class_kaldir(siklar[4]) == '':
      siklar.pop(4)
    for arg in args:
      if self.get_y() + arg > 280:
        self.add_page()
        self.set_x(10)
        if self.page_no() == 1:
          self.set_y(25)
        else:
          self.set_y(20)
        
    konum = 10
    soru = self.soru_temizle(soru)
    soru = str(self.sayi) + '. ' + soru
    self.set_x(konum)
    self.set_font('ArialUnicode','B', 9)
    if current_app.config['S3_BUCKET_NAME'] in soru:
      self.gorsel_math(soru, user_id)
    else:
      self.subscript(soru)
    self.ln(6)
    self.set_x(konum)
    if gorsel == True:
      if int(secim) == 1:
        self.coktan_secmeli_gorselli1(siklar, user_id)
      elif int(secim) == 2:
        if siklar[-1] == current_app.config['S3_BUCKET_NAME'] + 'pdfs/e.png':
          self.coktan_secmeli_gorselli1(siklar, user_id)
        else:
          self.coktan_secmeli_gorselli2(siklar, user_id)
      elif int(secim) == 3:
        self.coktan_secmeli_gorselli3(siklar, user_id)
      elif int(secim) == 4:
        self.coktan_secmeli_gorselli4(siklar, user_id)
    else:
      self.coktan_secmeli_yerlestir(siklar)

  def dogru_yanlis(self, ana_soru, sorular):
    self.sayi += 1
    self.ln(12)
    self.set_x(10)
    self.set_font('ArialUnicode', 'B', 9)
    ana_soru = str(self.sayi) + '. ' + ana_soru
    self.multi_cell(190, 4, ana_soru)
    self.set_font('ArialUnicode', '', 9)
    self.ln(4)
    for soru in sorular:
      if self.get_y() > 270:
        self.add_page()
      self.set_x(16)
      soru = '  ' + soru
      upper_left = 10
      self.set_line_width(0.61)
      self.rect(upper_left, self.get_y(), 7, 6)
      self.multi_cell(174, 6, soru)
      self.ln(3)

  def bosluk_doldurma(self, soru, paragraf, sorular, aciklama, tablo):
    self.sayi += 1
    self.ln(12)
    konum = self.get_y()
    self.set_x(10)
    if aciklama != '':
      self.set_font('ArialUnicode', '', 9)
      self.multi_cell(190, 6, aciklama)
    soru = str(self.sayi) + '. ' + soru
    self.set_font('ArialUnicode', 'B', 9)
    self.multi_cell(0, 4, soru)
    if tablo != '':
      self.ln(1)
      self.set_font('ArialUnicode', '', 9)
      self.set_line_width(0.3)
      self.set_x(10)
      self.multi_cell(190, 4, tablo, align='C', border=1)
    self.ln(4)
    self.set_x(10)
    self.set_font('ArialUnicode', '', 9)
    sorular = re.split("[\_]+[^a-zA-Z]+[\_]", paragraf)
    bosluklar = re.findall("[\_]+[^a-zA-Z]+[\_]", paragraf)
    liste = zip(sorular, bosluklar)
    for x in liste:
      sinir = 200
      y = x[1]
      if len(y) > 60:
        y = y[:53]
      elif len(y) < 10:
        y = '__________'
      if not y.startswith(' '):
        y = ' ' + y
      if not y.endswith(' '):
        y = y + ' '
      genislik = len(y) * 2.7
      
      self.write(11, x[0])
      
      self.set_font('ArialUnicode', '', 28)
      if self.get_x() + genislik > sinir:
        self.set_y(self.get_y() + 11)
        self.cell(5, 9, ' [')
        self.set_font('ArialUnicode', '', 9)
        konum = self.get_x() #bakılsın
        self.set_text_color(242,242,242)
        self.cell((genislik * 0.6), 12, y)
        self.set_font('ArialUnicode', '', 28)
        self.set_text_color(0,0,0)
        if len(y) > 40: #hatırlayamadım
          self.set_x(self.get_x() + 2)
        else:
          pass
        self.cell(3, 9, '] ')
        self.set_font('ArialUnicode', '', 9)
        #self.set_x(self.get_x() + 5)
      else:
        #self.set_y(self.get_y() + 5)
        self.cell(5, 9, ' [')
        self.set_font('ArialUnicode', '', 9)
        self.set_text_color(242,242,242)
        self.cell((genislik * 0.6), 12, y)
        self.set_font('ArialUnicode', '', 28)
        self.set_text_color(0,0,0)
        if len(y) > 40: #hatırlayamadım
          self.set_x(self.get_x() + 2)
        else:
          pass
        self.cell(3, 9, '] ')
        self.set_font('ArialUnicode', '', 9)
    self.write(11, sorular[-1])
    self.ln(10)

  def gorsel_math(self, soru, user_id):
    ayristirma = re.split("<img([\\s\\S]+?)>", soru)
    if '</p><p>' in ayristirma:
      ayristirma.remove('</p><p>')
    for idx, x in enumerate(ayristirma):
      konum = 10
      self.set_x(konum)
      if not x.startswith(' src="'):
        if f'https://{s3_name}' in ayristirma[idx-1]:
          self.set_y(self.get_y() - 3)
          if idx == len(ayristirma) - 1:
            #eğer soru cümlesiyse biraz daha yakınlaştır
            self.set_y(self.get_y() - 3)
          if idx != len(ayristirma) - 1 and f'https://{s3_name}' in ayristirma[idx+1]:
            self.set_y(self.get_y() - 2)
        self.subscript(x)
        if idx != len(ayristirma) - 1 and idx != 0 and f'https://{s3_name}' in ayristirma[idx+1]:
          self.ln(2)
      else:
        soru = soru.replace('<img' + x + '>', '')
        src = re.findall("src=([\\s\\S]+?)style", x)
        width = re.findall("width: ([\\s\\S]+?);", x)

        kayit_yolu = os.path.join(current_app.root_path, f'static/fpdf/pdf_files/gorseller/{user_id}/' + os.path.basename(src[0][1:-2]))

        key = src[0][1:-2].split(current_app.config['S3_BUCKET_NAME'])
        s3_client.download_file(s3_name, key[1], os.path.join(kayit_yolu))

        genislik = min((int(float(width[0].replace('px', ''))) * 0.6 ) * 0.2645833333, 100)
        
        onceki = str(ayristirma[idx-1]).replace('.', '')

        if ''.join(onceki[:-1]).isdigit() and not len(onceki) > 2:
          pass
        elif f'https://{s3_name}' in onceki:
          self.ln(3)
        else:
          self.set_y(self.get_y() - 3)
        self.image(name=kayit_yolu, x=konum+5, w=genislik)
        os.remove(kayit_yolu)
  
  def gorsel_cv2(self, gorsel, rakam, user_id):
    gercek_ad = unquote(os.path.basename(gorsel))
    ad, _ext = os.path.splitext(gercek_ad)
    kayit_yolu = os.path.join(current_app.root_path, f'static/fpdf/pdf_files/gorseller/{user_id}/' + gercek_ad)
    key = gorsel.split(current_app.config['S3_BUCKET_NAME'])
    s3_client.download_file(s3_name, unquote(key[1]), kayit_yolu)
    
    if _ext == '.png':
      img = cv2.imread(kayit_yolu, cv2.IMREAD_UNCHANGED)
    else:
      img = cv2.imread(kayit_yolu, 0)
    landscape = 'yatay'
    scale_percent = 99 # percent of original size
    if rakam == 1:
      yatay_sinir = 200
      dikey_sinir = 128
    elif rakam == 2:
      yatay_sinir = 350
      dikey_sinir = 255
    else:
      yatay_sinir = 650
      dikey_sinir = 510
    if img.shape[1]/img.shape[0] > 1 or img.shape[1]/img.shape[0] == 1: #görsel yatay veya köşeler eşit
      width = int(img.shape[1] * scale_percent / 100)
      height = int(img.shape[0] * scale_percent / 100)
      if not width < yatay_sinir:
        while width > yatay_sinir:
          scale_percent = scale_percent - 0.1
          width = int(img.shape[1] * scale_percent / 100)
          height = int(img.shape[0] * scale_percent / 100)

    elif img.shape[1]/img.shape[0] < 1: #görsel dikey
      width = int(img.shape[1] * scale_percent / 100)
      height = int(img.shape[0] * scale_percent / 100)
      landscape = 'dikey'
      if not height < dikey_sinir:
        while height > dikey_sinir:
          scale_percent = scale_percent - 0.1
          width = int(img.shape[1] * scale_percent / 100)
          height = int(img.shape[0] * scale_percent / 100)

    dim = (width, height)

    # resize image
    # resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    yeni_ad = kayit_yolu.replace(_ext, '_gorselresized' + _ext)
    cv2.imwrite(f'{yeni_ad}', img, [int(cv2.IMWRITE_JPEG_QUALITY), 40,IMWRITE_JPEG_OPTIMIZE])
    os.remove(kayit_yolu)

    bilgiler = {'landscape': landscape, 'boyutlar': dim, 'dosya': yeni_ad}
    return bilgiler
  
  def gorselekle(self, gorsel, rakam, user_id):
    self.ln(12)
    self.set_x(20)
    konum = 20

    bilgiler = self.gorsel_cv2(gorsel, rakam, user_id)
  
    gorsel = bilgiler['dosya']
    if bilgiler['landscape'] == 'dikey':
      self.image(name=gorsel, 
                w=min(int(bilgiler['boyutlar'][0] * 0.2645833333), 90), 
                h=int(bilgiler['boyutlar'][1] * 0.2645833333))
    else:
      self.image(name=gorsel, 
                w=int(bilgiler['boyutlar'][0] * 0.2645833333), 
                h=int(bilgiler['boyutlar'][1] * 0.2645833333))
    self.set_y(self.get_y() - 5)

  def eslestirme(self, soru, ilk_liste, ikinci_liste, yazdirma_turu):
    self.sayi += 1
    self.ln(12)
    self.set_x(10)
    self.set_font('ArialUnicode', 'B', 9)
    soru = str(self.sayi) + '. ' + soru
    self.multi_cell(190, 4, soru)
    self.set_font('ArialUnicode', '', 9)
    self.ln(4)
    e_sayac = 0
    if yazdirma_turu == 'altalta':
      for idx, soru in enumerate(ilk_liste):
        self.set_line_width(0.61)
        if self.get_y() >= 270:
          self.add_page()
          upper_left = 10
          if self.page_no() == 1:
            self.set_y(25)
          else:
            self.set_y(20)
          self.rect(upper_left, self.get_y(), 7, 6)
          self.set_x(18)
          soru = ' ' + soru
          self.set_x(self.get_x() + 1)
          self.multi_cell(183, 6, soru)
          self.ln(3)
        else:
          upper_left = 10
          self.rect(upper_left, self.get_y(), 7, 6)
          self.set_x(16)
          soru = ' ' + soru
          self.set_x(self.get_x() + 1)
          self.multi_cell(183, 6, soru)
          self.ln(3)
      for idx, soru in enumerate(ikinci_liste):
        eslesecek = self.lst[e_sayac]+ '. ' + ikinci_liste[e_sayac]
        e_sayac += 1
        self.set_x(10)
        self.multi_cell(190, 4, eslesecek, align='L')
        if idx != len(ikinci_liste) - 1:
          self.ln(1)
        else:
          self.ln(2)
    else:
      for idx, soru in enumerate(ilk_liste):
        self.set_line_width(0.61)
        if self.get_y() >= 270:
          self.add_page()
          upper_left = 10
          if self.page_no() == 1:
            self.set_y(25)
          else:
            self.set_y(20)
          self.sag = True
          self.rect(upper_left, self.get_y(), 7, 6)
          self.set_x(18)
          soru = ' ' + soru
          self.cell(100, 7, soru, ln=False)
          harf_ekle = True
          try:
            eslesecek = ikinci_liste[idx]
          except:
            eslesecek = ''
            harf_ekle = False
          if harf_ekle:
            eslesecek = self.lst[idx]+ '. ' + ikinci_liste[idx]
            self.multi_cell(80, 7, eslesecek)
          else:
            self.multi_cell(90, 7, '')
          if idx != len(ilk_liste) -1:
            self.ln(2)
        else:
          upper_left = 10
          self.rect(upper_left, self.get_y(), 7, 6)
          self.set_x(18)
          soru = ' ' + soru
          self.cell(100, 7, soru, ln=False)
          harf_ekle = True
          try:
            eslesecek = ikinci_liste[idx]
          except:
            eslesecek = ''
            harf_ekle = False
          if harf_ekle:
            eslesecek = self.lst[idx]+ '. ' + ikinci_liste[idx]
            self.multi_cell(80, 7, eslesecek)
          else:
            self.multi_cell(90, 7, '')
          if idx != len(ilk_liste) -1:
            self.ln(2)
    self.set_y(self.get_y() - 5)

class DummyTek(PDFTEK):
  def kontrol(self, x, y, soru, siklar, gorsel_var_mi, secim, user_id):
    self.add_page()
    ilk_y = self.get_y()
    self.coktan_secmeli(soru, siklar, gorsel_var_mi, secim, user_id)
    fark = self.get_y() - ilk_y
    return fark

def pdf_yazdir(path, sorular, user_id, pdf_fn, sinav, lang):
  liste = []

  sayac = 0

  for x, y in sorular.items():
    if x.startswith(f'blocks[{sayac}][data]'):
      liste.append(x)
      sayac += 1

  if sorular['duzen'] == 'cift-sutun':
    dummy = Dummy()
    pdf = PDF()
  else:
    dummy = DummyTek()
    pdf = PDFTEK()
    
  if 'ust_yazi' in sorular:
    pdf.ust_yazi = sorular['ust_yazi']
    dummy.ust_yazi = sorular['ust_yazi']

  if 'alt_yazi' in sorular:
    pdf.alt_yazi = sorular['alt_yazi']
    dummy.alt_yazi = sorular['alt_yazi']
  
  if sorular['logo_secimi'] != 'None' and sorular['logo_secimi'] != '':
    logo_ad = Logo.query.filter_by(id=int(sorular['logo_secimi'])).first().uri
    pdf.logo_ad = logo_ad
    dummy.logo_ad = logo_ad
  
  pdf.set_title('GraidApp')
  dummy.set_title('GraidApp')

  pdf.add_font('ArialUnicode',fname=os.path.join(path,'fonts/arial.ttf'),uni=True)
  pdf.add_font('ArialUnicode',style="I",fname=os.path.join(path,'fonts/ariali.ttf'),uni=True)
  pdf.add_font('ArialUnicode', style="B",fname=os.path.join(path,'fonts/arialbld.ttf'),uni=True)
  pdf.add_font('ArialUnicode', style="BI",fname=os.path.join(path,'fonts/arialbi.ttf'),uni=True)
  
  dummy.add_font('ArialUnicode',fname=os.path.join(path,'fonts/arial.ttf'),uni=True)
  dummy.add_font('ArialUnicode',style="I",fname=os.path.join(path,'fonts/ariali.ttf'),uni=True)
  dummy.add_font('ArialUnicode', style="B",fname=os.path.join(path,'fonts/arialbld.ttf'),uni=True)
  dummy.add_font('ArialUnicode', style="BI",fname=os.path.join(path,'fonts/arialbi.ttf'),uni=True)
  
  pdf.set_font('ArialUnicode', '', 10)
  dummy.set_font('ArialUnicode', '', 10)

  pdf.add_page()
  
  if sinav != '':
    kod_ifadesi = 'Sınav Kodu: ' if lang == 'tr' else 'Exam Code: '
    with pdf.rotation(angle=90, x=50, y=10):
      pdf.set_font('ArialUnicode', '', 9)
      pdf.text(x=-80, y=-32, txt=kod_ifadesi + str(sinav.uuid))
      pdf.set_font('ArialUnicode', '', 10)
  
  pdf.set_author('GraidApp')
  pdf.adsoyad('en' if sorular['ders'] == 'İngilizce' or lang == 'en' else 'tr')

  for soru in liste:
    if pdf.page_no() > 6:
      raise Exception("Sayfa 6'yı geçemez.", "sayfa")
    if soru.endswith('[coktan_secmeli]'):
      soru = parse_qs(sorular[soru])
      siklar = []
      #GorselliMi=true
      for sik, ifade in soru.items():
        if sik.endswith('Şıkkı'):
          siklar.append(ifade[0])
      if 'GorselliMi' in soru.keys() and soru['GorselliMi'][0] == 'true':
        gorsel_var_mi = True
        secim = soru['duzen-secim'][0]
      else:
        secim = ''
        gorsel_var_mi = False
      durum = dummy.kontrol(pdf.get_x(),pdf.get_y(), soru['Soru'][0], siklar, gorsel_var_mi, secim, user_id)
      pdf.coktan_secmeli(soru['Soru'][0], siklar, gorsel_var_mi, secim, user_id, durum)
    elif soru.endswith('[eslestirme]'):
      soru = parse_qs(sorular[soru])
      ilk_liste = soru['İlk Eş']
      ikinci_liste = soru['İkinci Eş']
      _soru = soru['Soru'][0]
      try:
        #sorular alt alta mı olacak
        altalta = soru['Altalta'] #silme
        pdf.eslestirme(_soru, ilk_liste, ikinci_liste, 'altalta')
      except:
        pdf.eslestirme(_soru, ilk_liste, ikinci_liste, '')
    elif soru.endswith('[dogru_yanlis]'):
      soru = parse_qs(sorular[soru])
      ifadeler = []
      for _, ifade in soru.items():
        for ifade in soru['Doğru Yanlış İfadesi']:
          if not ifade in ifadeler:
            ifadeler.append(ifade)
      pdf.dogru_yanlis(soru['Soru Tümcesi'][0], ifadeler)
    elif soru.endswith('[gorsel]'):
      soru = parse_qs(sorular[soru])
      gorsel = soru['Görsel'][0]
      if '-_yeni_-' in gorsel and sinav != '':
        gorsel = gorsel.replace('-_yeni_-', f'-{str(sinav.id)}-')
      boyut = soru['boyut'][0]
      if boyut == 'tam':
        boyut = 3
      elif boyut == 'orta':
        boyut = 2
      else:
        boyut = 1
      pdf.gorselekle(gorsel, boyut, user_id)
    else:
      aciklama = ''
      _sorular = ''
      soru = parse_qs(sorular[soru])
      pdf.bosluk_doldurma(soru['Soru Tümcesi'][0], soru['Paragraf'][0], _sorular, aciklama, soru['Tablo'][0] if 'Tablo' in soru else '')
    
  kayit_path = os.path.join(path,f'pdf_files/{pdf_fn}.pdf')
  pdf.output(kayit_path)
  s3_yol = f'pdfs/{str(user_id)}/' + pdf_fn + '.pdf'
  
  if sinav != '':
    key = f'pdfs/{user_id}/{sinav.pdf_dosyasi}.pdf'
    s3_client.delete_object(Bucket=s3_name, Key=key)

  s3_client.upload_file(kayit_path, s3_name, s3_yol, ExtraArgs={
    "ACL": "public-read",
    "CacheControl": "max-age=2000000,public",
    "Expires": "2030-09-01T00:00:00Z",
    "ContentType": 'application/pdf'})
  os.remove(kayit_path)

  return s3_yol

def parse_questions(data):
  liste = []
  sayac = 0

  for x, y in data.items():
    if x.startswith(f'blocks[{sayac}][data]'):
        liste.append(x)
        sayac += 1

  sorular = []

  for soru in liste:
    if soru.endswith('[coktan_secmeli]'):
      soru = data[soru]
      tip_ve_soru = ('coktan_secmeli', str(soru))
      sorular.append(tip_ve_soru)
    elif soru.endswith('[eslestirme]'):
      soru = data[soru]
      tip_ve_soru = ('eslestirme', str(soru))
      sorular.append(tip_ve_soru)
    elif soru.endswith('[dogru_yanlis]'):
      soru = data[soru]
      tip_ve_soru = ('dogru_yanlis', str(soru))
      sorular.append(tip_ve_soru)
    elif soru.endswith('[gorsel]'):
      soru = data[soru]
      tip_ve_soru = ('gorsel', str(soru))
      sorular.append(tip_ve_soru)
    else:
      soru = data[soru]
      tip_ve_soru = ('bosluk_doldurma', str(soru))
      sorular.append(tip_ve_soru)
  
  return sorular

def sorulari_gonder(liste):
  raw_data = ''
  for x, y in enumerate(liste):
      if x == len(liste) -1:
          ekle = f'#_%?39?%_#type:"{y.tip}", data:#_%?39?%_#input:"{y.raw_soru}"#_%?38?%_##_%?38?%_#'
      else:
          ekle = f'#_%?39?%_#type:"{y.tip}", data:#_%?39?%_#input:"{y.raw_soru}"#_%?38?%_##_%?38?%_#,'
      ekle = ekle.replace('#_%?39?%_#', '{')
      ekle = ekle.replace('#_%?38?%_#', '}')
      raw_data += ekle
  return raw_data

def sorulari_guncelle(sinav, data):
  liste = []
  sayac = 0

  for x, y in data.items():
    if x.startswith(f'blocks[{sayac}][data]'):
        liste.append(x)
        sayac += 1

  sorular = []
  sinavin_tum_sorulari = db.session.query(Soru).filter(Soru.sinav_id == sinav.id).all()
  
  for soru in liste:
    if soru.endswith('[coktan_secmeli]'):
      soru = data[soru]
      tip_ve_soru = ('coktan_secmeli', str(soru))
      sorular.append(tip_ve_soru)
    elif soru.endswith('[eslestirme]'):
      soru = data[soru]
      tip_ve_soru = ('eslestirme', str(soru))
      sorular.append(tip_ve_soru)
    elif soru.endswith('[dogru_yanlis]'):
      soru = data[soru]
      soru = soru.replace('-_yeni_-', str(sinav.id))
      tip_ve_soru = ('dogru_yanlis', str(soru))
      sorular.append(tip_ve_soru)
    elif soru.endswith('[gorsel]'):
      soru = data[soru]
      tip_ve_soru = ('gorsel', str(soru))
      sorular.append(tip_ve_soru)
    else:
      soru = data[soru]
      tip_ve_soru = ('bosluk_doldurma', str(soru))
      sorular.append(tip_ve_soru)
  
  for x in sinavin_tum_sorulari:
    if x.raw_soru not in sorular:
      db.session.delete(x)
  
  for y in sorular:
    ekle = Soru(sinav_id=sinav.id, raw_soru=y[1], tip=y[0])
    db.session.add(ekle)
  
  db.session.commit()

  return '', 200

def buckettan_sil(sinav, user_id):
    gorsel_path = os.path.join(current_app.root_path, 'static/fpdf/pdf_files/gorseller', str(user_id))
    #gerek var mı bilmiyorum. ama kalsın.
    for x in os.listdir(gorsel_path):
        if sinav.baslik in x:
            os.remove(os.path.join(gorsel_path, x))
    
    #pdf sil
    key = f'pdfs/{user_id}/{sinav.pdf_dosyasi}.pdf'
    s3_client.delete_object(Bucket=s3_name, Key=key)
    
    #sinava ait gorselleri sil
    s3_bucket = s3.Bucket(s3_name)
    liste = s3_bucket.objects.filter(Prefix=f'pdfs/{str(user_id)}/gorseller').all()
    for x in liste:
        if sinav.baslik in x.key:
            s3.Object(s3_name, x.key).delete()
    return '', 200

def bucket_gorsel_ad_degistir(user_id, sinav_id):
    s3_bucket = s3.Bucket(s3_name)
    liste = s3_bucket.objects.filter(Prefix=f'pdfs/{str(user_id)}/gorseller').all()
    for x in liste:
        if '-_yeni_-' in x.key:
          degistir = x.key
          s3.Object(s3_name, degistir.replace('-_yeni_-', f'-{str(sinav_id)}-')).copy_from(CopySource=f'{s3_name}/{degistir}', ACL='public-read')
          s3.Object(s3_name, degistir).delete()
    return '', 200

def bucket_sinav_kopyala(user_id, orj_user_id, sinav_id, yeni_sinav_id, pdf_adi, eski_baslik, yeni_baslik):
    s3_bucket = s3.Bucket(s3_name)
    
    yeni_pdf_adi = pdf_adi.replace(f'{orj_user_id}-', f'{user_id}-', 1)
    s3.Object(s3_name, f'pdfs/{user_id}/{yeni_pdf_adi}.pdf').copy_from(CopySource=f'{s3_name}/pdfs/{orj_user_id}/{pdf_adi}.pdf', ACL='public-read')
    
    liste = s3_bucket.objects.filter(Prefix=f'pdfs/{str(orj_user_id)}/gorseller').all()
    for x in liste:
        ad = x.key
        dosya_sinav_id = ad.split('-')[1]
        if int(dosya_sinav_id) == int(sinav_id):
          yeni_ad = ad.replace(f'-{sinav_id}-', f' {orj_user_id}-{yeni_sinav_id}-', 1)
          s3.Object(s3_name, f'pdfs/{user_id}/gorseller/{os.path.basename(yeni_ad)}').copy_from(CopySource=f'{s3_name}/pdfs/{orj_user_id}/gorseller/{os.path.basename(ad)}', ACL='public-read')
    return '', 200

def konu_ekle(sinav, konu_listesi, ders):
  sinav.konular = []
  konular = konu_listesi.split(',')
  for x in konular:
    hata = Konu.query.filter_by(hangi_ders=ders.id).filter_by(name=f'{x}').all()
    if len(hata) > 1:
      #birbirini tekrar eden girdiler olmadığından emin olduğumuzda bunu kaldırabiliriz.
      _hata = hata[1:]
      for x in _hata:
          db.session.delete(x)
    tag_ekle = hata[0]
    sinav.konular.append(tag_ekle)
  return '', 200

'''
  bunu cron job'a dönüştürelim. senkronize işlevde beklemesi gereksiz,
  asenkron işlemde ise istenmeyen sonuçlara neden olabilir.
'''
# def eski_gorselleri_sil(path, data, sinav):
#   liste = []
#   sayac = 0

#   for x, y in data.items():
#     if x.startswith(f'blocks[{sayac}][data]'):
#         liste.append(x)
#         sayac += 1

#   sorular = []

#   for soru in liste:
#     if soru.endswith('[gorsel]'):
#       soru = parse_qs(data[soru])
#       gorsel = soru['Görsel'][0]
#       sorular.append(unquote(os.path.basename(gorsel)))

#   for x in os.listdir(path):

#     kontrol = x.split('-')
#     if kontrol[0] == sinav.baslik and x not in sorular:
#       os.remove(os.path.join(path, x))
  
#   return '', 200