let translations = {
  'ogrencileri': {'tr': 'Öğrencileri', 'en': 'Students'},
  'baslikSuccess': {'tr': 'Başlık değiştirildi.', 'en': 'The title has been changed.'},
  'yetersizKredi': {
    'tr': '<div><p>Bu işlem için yeterli krediniz bulunmamaktadır.</p><a class="btn btn-info" href="/pg/fiyatlar">Kredi Satın Al</a></div>',
    'en': "<div><p>You don't have enough credits for this request.</p><a class='btn btn-info' href='/pg/pricing'>Buy Credits</a></div>"
  },
  'repBildirim': {
    'tr': 'Rapor hazır olunca size bildirim göndereceğiz.',
    'en': "We'll notify you when the report is ready."
  },
  'yetersizOgr': {
    'tr': 'Yeterli sayıda öğrenci veya sınav bulunamadı.',
    'en': 'Not enough students or exams.'
  },
  'ilkRapor': {'tr': 'İlk raporunuzu oluşturun', 'en': 'Create your first report'},
  'repIstek': {'tr': 'Rapor İsteği Gönder', 'en': 'Request a report'},
  'repAciklama': {
    'tr': '<br>Şu ana kadar yapılan tüm sınavların detaylı kazanım raporlarını elde edin.',
    'en': "<br>Get learning objectives reports of all the exams you've graded."
  },
  'indir': {'tr': 'İndir', 'en': 'Download'},
  'olusturulanRep': {
    'tr': 'Bu Sınıf İçin Oluşturulan Raporlar',
    'en': 'Reports Generated For This Class'
  },
  'gecerliAd': {
    'tr': 'Lütfen geçerli bir ad giriniz.',
    'en': 'Please enter a valid name.'
  }
}

let sinifID = window.location.href.split("/").pop().replace('#', '');
document.getElementById('siniflar-btn').className = 'nav-link active'

$('a[href="#sinif"]').on('shown.bs.tab', function (e) {
  document.getElementById('rapor-col').style = 'display:none;'
})
$('a[href="#sinif"]').on('hidden.bs.tab', function (e) {
  document.getElementById('rapor-col').style = 'display:inline;'
})

$('#baslik').hover(() => {
  $('#editBtn').attr('style', 'margin-top:3px; margin-right:10px; display:inline')
},
() => {
  $('#editBtn').attr('style', 'display:none')
})

function spanSwitch(e) {
    let txt = e.innerHTML;
    let element = document.getElementById('baslik');
  
    element.innerHTML = `<div class="row"><input id="baslik-degistir" class="form-control mr-2" onceki='${e.innerHTML}' onblur='spanReset(this)' value='${txt}'> ${translations['ogrencileri'][lang]}</div>`;
    document.getElementById('baslik-degistir').focus();
  }
  
  function spanReset(e) {
    let txt = e.value;
    let onceki = e.getAttribute('onceki')
    let element = document.getElementById('baslik');
    let _svg = '<svg xmlns="http://www.w3.org/2000/svg" id="editBtn" width="24" height="24" fill="currentColor" style="display:none;" class="mb-2 bi bi-pencil-square" viewBox="0 0 16 16"><path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/><path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5v11z"/></svg>'
    if (txt != onceki && (txt.length < 5 || txt.length > 150) ) {
      toastr.options.timeOut = 1500;
      toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
      toastr.error(translations['gecerliAd'][lang]);
      element.innerHTML = _svg + `<span onclick='spanSwitch(this)'>${onceki}</span> ${translations['ogrencileri'][lang]}`;
    }
    else if (txt == onceki) {
      element.innerHTML = _svg + `<span onclick='spanSwitch(this)'>${onceki}</span> ${translations['ogrencileri'][lang]}`;
    }
    else {
        $.ajax({
          url: "/rapor/sinif_ad_degistir",
          data: {
              'id': sinifID,
              'ad': txt
          },
          dataType: "text",
          type: 'POST',
          success: () => {
              toastr.options.timeOut = 1500;
              toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
              toastr.success(translations['baslikSuccess'][lang]);
              let element = document.getElementById('baslik');
              element.innerHTML = _svg + `<span onclick='spanSwitch(this)'>${txt}</span> ${translations['ogrencileri'][lang]}`;
          },
          error: () => {
            hataToast()
          }
        })
    }
  }

document.getElementById('yeniogrenci-btn').addEventListener('click', () => {
  let ogrenciEkleModal = document.getElementById('ogrenciEkleModal')
  $(ogrenciEkleModal).modal('show')
  setTimeout(() => {document.getElementById('sinifListeInput').focus()}, 480)
})

document.getElementById('sinifisil-btn').addEventListener('click', () => {
  $(document.getElementById('sinifiSilModal')).modal('show')
  let silBtn = document.getElementById('sinifSilGonderBtn')
  silBtn.addEventListener('click', () => {
    $.ajax({
      url: "/rapor/sinifi_sil",
      type: 'text',
      method: 'POST',
      data: {
        'id': sinifID
      },
      success: function (data) {
          window.location.href = '/pg/panel/siniflar'
      },
      error: () => {
        hataToast()
      }
  })
  })
})

document.getElementById('sinifListeGonder').addEventListener('click', (e) => {
  e.preventDefault();
  let sinifListeInput = document.getElementById('sinifListeInput')
  $.ajax({
    url: "/rapor/sinifa_ogrenci_ekle",
    type: 'text',
    method: 'POST',
    data: {
      'id': sinifID,
      'liste': sinifListeInput.value
    },
    success: function () {
        window.location.reload();
    },
    error: () => {
      hataToast()
    }
})
})


function editOgrenci(e) {
  let thisID = e.getAttribute('ogrid')
  let thisTr = e.closest('tr')
  let ogrenciAdi = thisTr.childNodes[0].innerHTML
  let ogrenciNum = thisTr.childNodes[1].innerHTML
  let modal = document.getElementById('editOgrenciModal')
  let isimInput = document.getElementById('isiminput')
  let numInput = document.getElementById('numarainput')
  isimInput.setAttribute('value', ogrenciAdi)
  numInput.setAttribute('value', ogrenciNum)
  $(modal).modal('show')
  console.log(isimInput.value)
  document.getElementById('ogrenciBilgileriDegisBtn').addEventListener('click', () => {
    $.ajax({
      url: "/rapor/sinif_ogrenci_bilgi_degis",
      type: 'text',
      method: 'POST',
      data: {
        'sinif_id': sinifID,
        'ogrenci_id': thisID,
        'isim': isimInput.value,
        'num': numInput.value
      },
      success: function () {
        window.location.reload();
      },
      error: () => {
        hataToast();
      }
    })
  })
}

function ogrenciSil(e) {
  let modal = document.getElementById('delOgrenciModal')
  $(modal).modal('show')
  let thisID = e.previousSibling.getAttribute('ogrid')
  document.getElementById('ogrenciSilBtn').addEventListener('click', () => {
    $.ajax({
      url: "/rapor/siniftan_ogr_sil",
      type: 'text',
      method: 'POST',
      data: {
        'id': thisID
      },
      success: function () {
        window.location.reload();
      },
      error: () => {
        hataToast();
      }
    })
  })
}

let duzenleBtn = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="var(--prussian)" class="mb-1 mx-2 bi bi-pencil-square" viewBox="0 0 16 16"><path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/><path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5v11z"/></svg>'
let silBtn = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="var(--prussian)" class="mb-1 mx-2 bi bi-trash" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/></svg>'
let _bilgiler;
let tutar;

$.ajax({
  url: "/get_sinif_ogrenciler",
  type: 'text',
  method: 'POST',
  data: {
    'id': sinifID
  },
  success: function (data) {
      _bilgiler = data['ogrenci_bilgi']
      tutar = data['rapor_tutar']
      for(i=0; i < _bilgiler.length; i++) {
        _bilgiler[i]['eylem'] = '<div class="d-flex justify-content-start"><span class="eylem-btn" onclick="editOgrenci(this)" ogrid="'+ _bilgiler[i]['id'] + '">'  + duzenleBtn + '</span><span class="eylem-btn" onclick="ogrenciSil(this)">' + silBtn + '</span></div>'
      }
      let tablo =  document.getElementById('data');
      if (typeof(tablo) != 'undefined' && tablo != null){
          let locales = {'tr': '//cdn.datatables.net/plug-ins/9dcbecd42ad/i18n/Turkish.json', 'en': ''}
          const table = $(tablo).DataTable({
              "order": [[ 2, "desc" ]],
              "oLanguage": {
                "sUrl": locales[lang]
            },
              data: _bilgiler,
              columns: [
                {data: 'name'},
                {data: 'numara'},
                {data: 'sinavlar'},
                {data: 'ortalama'},
                {data: 'eylem',"orderable": false, "searchable": false},
                {data: 'id', visible:false},
              ],
          });
          // $('#data tbody').on('click', 'tr', function () {
          //     var data = table.row( this ).data();
          //     window.location.href = '/pg/panel/siniflar/' + data['id']
          // })
      }
  }
})

function raporIstekGonder(raporIsteBtn) {
  let raporOnayBtn = document.getElementById('raporIstekOnay')
  let btnIcerik = raporIsteBtn.innerHTML
  let modal = document.getElementById('raporIstekModal')
  let body = modal.querySelector('#raporOnayBody')
  if (tutar == 'yetersiz') {
    body.innerHTML = translations['yetersizKredi'][lang]
  }
  else {
    switch (lang){
      case 'tr':
        body.innerHTML = '<p>Bu işlem için <b>' + tutar + ' kredi</b> gerekmektedir. Onaylıyor musunuz?</p>'
        break;
      case 'en':
        body.innerHTML = '<p>For this request <b>' + tutar + ' credits</b> will be taken. Do you confirm?</p>'
        break;
    }
  }
  raporIsteBtn.setAttribute('disabled', '')
  raporIsteBtn.innerHTML = '<div class="spinner-border text-info" role="status"><span class="sr-only"></span></div>'
  $(modal).modal('show')
  raporOnayBtn.onclick = () => {
    $.ajax({
      url: "/deep_analysis",
      type: 'text',
      method: 'POST',
      data: {
        'id': sinifID
      },
      success: () => {
        toastr.options.timeOut = 1500;
        toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
        toastr.success(translations['repBildirim'][lang]);
        $(document.getElementById('sinif-tab')).tab('show')
        $('#raporIstekModal').modal('hide')
      },
      error: (data) => {
        if (data.status == 404) {
          toastr.options.timeOut = 1500;
          toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
          toastr.error(translations['yetersizOgr'][lang]);
        }
        else {
          hataToast()
        }
      }
    })
  }
  $(modal).on('hide.bs.modal', () => {
    raporIsteBtn.innerHTML = btnIcerik
    raporIsteBtn.removeAttribute('disabled')
  })
}

function ilkRapor() {
  let ilkDiv = document.createElement('div')
  let br = document.createElement('br')
  let ilkRaporBaslik = document.createElement('h2')
  ilkRaporBaslik.innerHTML = translations['ilkRapor'][lang]
  let raporIsteBtn = document.createElement('button')
  raporIsteBtn.className = 'btn btn-info'
  raporIsteBtn.innerHTML = translations['repIstek'][lang]
  raporIsteBtn.setAttribute('onclick', 'raporIstekGonder(this)')
  let aciklama = document.createElement('small')
  aciklama.className = 'text-muted'
  aciklama.innerHTML = translations['repAciklama'][lang]
  let img = document.createElement('img')
  img.src = '/static/icons/undraw_Save_to_bookmarks_re_8ajf.svg'
  img.loading = 'lazy'
  img.className = 'my-4 illustration'
  ilkDiv.append(ilkRaporBaslik, raporIsteBtn, br, aciklama, br, img)
  return ilkDiv
}

function raporlariListele(data) {
  let ilkDiv = document.createElement('div')
  for (i=0; i < data.length; i++) {
    let listUl = document.createElement('ul')
    listUl.className = 'list-group list-group-horizontal'
    Object.keys(data[i]).forEach(function(key, value) {
      let listItem = document.createElement('li')
      listItem.className = 'list-group-item flex-fill yatayliste'
      let icerik = data[i][key]
      if (key == 'href') {
        let href = data[i]['href']
        icerik = '<a class="btn btn-info btn-block" download href="' + href + '">' + translations['indir'][lang] +'</a>'
      }
      listItem.innerHTML = icerik
      listUl.appendChild(listItem)
    })
    ilkDiv.appendChild(listUl)
  }
  return ilkDiv
}

let sinifRaporlar;
let raporTab = document.getElementById('rapor-tab')
let raporCol = document.getElementById('rapor-col')
$(raporTab).on('show.bs.tab', () => {
  if (sinifRaporlar === undefined) {
    raporCol.innerHTML = ''
    let baslik = document.createElement('h2')
    baslik.innerHTML = translations['olusturulanRep'][lang]
    raporCol.appendChild(baslik)
    $.ajax({
      url: "/get_sinif_raporlar",
      type: 'text',
      method: 'POST',
      data: {
        'id': sinifID
      },
      success: (data) => {
        if (data.length == 0) {
          let icerik = ilkRapor()
          raporCol.appendChild(icerik)
          sinifRaporlar = icerik
        }
        else {
          let icerik = raporlariListele(data)
          raporCol.appendChild(icerik)
          sinifRaporlar = data
        }
      },
      error: () => {
        hataToast()
      }
    })
  }
})