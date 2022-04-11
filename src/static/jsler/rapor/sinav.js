let locales = {'tr': '//cdn.datatables.net/plug-ins/9dcbecd42ad/i18n/Turkish.json', 'en': ''}
let thisTranslations = {
    'ogrenci': {'tr': 'Öğrenci', 'en': 'Student'},
    'puani': {'tr': 'Puanı', 'en': 'Score'},
    'eslestirmeUyari': {'tr': 'Dikkat! Bu öğrenci başka bir kâğıt ile eşleştirilmiş.', 'en': "Warning! You've already matched this student."},
    'okundu': {'tr': ' kağıt başarıyla okundu.', 'en': ' papers have been graded.'},
    'iliskilendir': {'tr': 'Bir sınıfla ilişkilendir ', 'en': 'Link a class '},
    'hata': {'tr': 'Hata: ', 'en': 'Error: '},
    'labelTip': {'tr': 'Soru Tipi', 'en': 'Question Type'},
    'uyariBaslik': {'tr': 'Başlık en az 4, en fazla 100 karakter olmalıdır.', 'en': 'Number of characters in the title should be between 4 and 100.'},
    'successBaslik': {'tr': 'Başlık değiştirildi.', 'en': 'The title has been changed.'},
    'bekle': {'tr': 'Lütfen bekleyin', 'en': 'Please wait'},
    'sifirSinif': {
        'tr': 'Henüz bir sınıf oluşturmamışsınız. Bu sınavı bir sınıfla ilişkilendirmek için panelden sınıflar sekmesini kullanarak bir sınıf oluşturun.',
        'en': "You haven't created a class yet. To link this exam with a class, you need to create a class first using classes tab on the panel."
    },
    'linkClass': {'tr': 'Bu sınavın ait olduğu sınıfı seçin.', 'en': 'Choose the class of this exam.'},
    'yetersizOgrenci': {
        'tr': 'Sınıfta yeterince öğrenci yok. Lütfen sınıfa öğrenci ekleyin.',
        'en': 'Not enough students in the class. Please add some students in the class first.'
    },
    'ogrUri': {'tr': '/pg/panel/ogrenci/', 'en': '/pg/panel/student/'}
}

const truncateString = (string = '', maxLength = 47) => 
  string.length > maxLength 
    ? `${string.substring(0, maxLength)}…`
    : string

function thEkle(iliskili) {
    let puanTh = document.createElement('th')
    puanTh.innerHTML = thisTranslations['puani'][lang]
    let eylemTh = document.createElement('th')
    eylemTh.innerHTML = ''
    if (iliskili == true) {
        let gercekOgrenciTh = document.createElement('th')
        gercekOgrenciTh.innerHTML = thisTranslations['ogrenci'][lang]
        document.getElementById('dynamic-th').append(gercekOgrenciTh, puanTh, eylemTh)
    }
    else {
        document.getElementById('dynamic-th').append(puanTh, eylemTh)
    }
}

function getThisId(onizleme) {
    let thisId;
    for (i=0; i < _bilgiler['ogrenciler'].length; i++) {
        if (_bilgiler['ogrenciler'][i]['adsoyad'].includes(decodeURIComponent(onizleme.src))) {
            thisId = _bilgiler['ogrenciler'][i]['id']
        }
    }
    return thisId
}

let ogrSonuc;

function previewOgr(e) {
    yanitDegisFunc = (soru_id, txt, e) => {
        let thisRow = $(e).parents()[4]
        let soruPuani = parseInt(thisRow.childNodes[0].innerHTML)
        let beklenenCevaplar = thisRow.childNodes[1].innerHTML.split(',')
        let result = thisRow.childNodes[3]
        $.ajax({
            url: "/rapor/soru_cevap_degistir",
            data: {
                'id': soru_id,
                'cevap': txt
            },
            dataType: "text",
            type: 'POST',
            success: () => {
                let yeniSonuc;
                let eskiSonuc = thisRow.childNodes[2]
                eskiSonuc.innerHTML = txt
                $(eskiSonuc).wrapInner("<span onclick='spanSwitch(this)'></span>");
                if (beklenenCevaplar.includes(txt)) {
                    if (result.innerHTML != translations['true'][lang]) {
                        yeniSonuc = parseInt(ogrSonuc.innerHTML) + parseInt(soruPuani)
                        result.innerHTML = translations['true'][lang]
                        puan.innerHTML = thisTranslations['puani'][lang] + ': ' + yeniSonuc
                    }
                }
                else {
                    if (result.innerHTML != translations['false'][lang]) {
                        yeniSonuc = parseInt(ogrSonuc.innerHTML) - parseInt(soruPuani)
                        result.innerHTML = translations['false'][lang]
                        puan.innerHTML = thisTranslations['puani'][lang] + ': ' + yeniSonuc
                    }
                }
                ogrSonuc.innerHTML = yeniSonuc === undefined ? ogrSonuc.innerHTML : yeniSonuc
            },
            error: () => {
                hataToast()
            }
        })
      }
    let thisTr = e.closest('tr')
    let sonucIndex = thisTr.childNodes.length == 3 ? 1 : 2
    ogrSonuc = thisTr.childNodes[sonucIndex]
    let headerDiv = document.createElement('div')
    headerDiv.className = 'd-flex justify-content-between'
    let thisOnizleme = thisTr.querySelector('img')
    let puan = document.createElement('p')
    puan.innerHTML = thisTranslations['puani'][lang] + ': ' + ogrSonuc.innerHTML
    headerDiv.append(thisOnizleme.cloneNode(), puan)
    const thisId = getThisId(thisOnizleme)
    let previewModal = document.getElementById('preivewModal')
    $(previewModal).modal('show')
    let header = previewModal.querySelector('.modal-title')
    header.innerHTML = ''
    header.appendChild(headerDiv)
    let body = previewModal.querySelector('.modal-body')
    body.innerHTML = ''
    let spinnerDiv = document.createElement('div')
    spinnerDiv.className = 'spinner-border text-info'
    spinnerDiv.setAttribute('role', 'status')
    let spinSpan = document.createElement('span')
    spinSpan.className = 'sr-only'
    spinnerDiv.appendChild(spinSpan)
    body.appendChild(spinnerDiv)
    $.ajax({
        url: "/rapor/ogrenci_preview",
        type: 'text',
        method: 'POST',
        data: {
            'id': thisId,
        },
        success: (data) => {
            body.innerHTML = ''
            let prevTable = document.createElement('table')
            prevTable.id = 'prevTable'
            prevTable.className = 'table'
            prevTable.style = "width: 100%;"
            let prevDiv = document.createElement('div')
            prevDiv.className ='cell-border compact'
            prevDiv.style = 'overflow-x: auto;'
            prevDiv.appendChild(prevTable)
            let prevThead = document.createElement('thead')
            let prevBody = document.createElement('tbody')
            let tr = document.createElement('tr')
            prevThead.appendChild(tr)
            prevTable.append(prevThead, prevBody)
            let ths;
            switch (lang) {
                case 'tr':
                    ths = ['Puan', 'Beklenen Cevaplar', 'Öğrenci Cevapları', 'Sonuç', 'Önizleme']
                    break;
                case 'en':
                    ths = ['Points', 'Expected Answers', 'Student Answers',  'Result', 'Preview']
                    break;
            }
            for (i=0; i < ths.length; i++) {
                let th = document.createElement('th')
                th.innerHTML = ths[i]
                tr.appendChild(th)
            }
            body.appendChild(prevDiv)
            for (i=0; i < data['bilgiler'].length; i++) {
                let s = data['bilgiler'][i]['sonuc']
                data['bilgiler'][i]['sonuc'] = translations[s][lang]
            }
            const previewTable = $('#prevTable').DataTable({
                "oLanguage": {
                    "sUrl": locales[lang]
                },
                "order": [[ 3, "desc" ]],
                "pageLength": 50,
                "createdRow": function( row, data, dataIndex){
                    let liste = data['beklenen_cevaplar'].split(',')
                    for (i=0; i < liste.length; i++) {
                        row.childNodes[0].setAttribute('id', data['id'])
                        $(row.childNodes[2]).wrapInner("<span onclick='spanSwitch(this)'></span>");
                        if (data['ogrenci_cevaplari'] != liste[i] && data['guven'] < 0.9) {
                            row.className = 'dikkat'
                        }
                    }
                },
                data: data['bilgiler'],
                columns: [
                    {data: 'puan'},
                    {data: 'beklenen_cevaplar'},
                    {data: 'ogrenci_cevaplari'},
                    {data: 'sonuc'},
                    {data: 'onizleme', searchable: false},
                    {data: 'guven', visible:false},
                    {data: 'id', visible:false},
                ]
            });
        },
        error: () => {
            hataToast()
        }
    })
}

function kagitSil(e) {
    let thisTr = e.closest('tr')
    let thisOnizleme = thisTr.querySelector('img')
    const thisId = getThisId(thisOnizleme)
    $('#kagitSilModal').modal('show')
    document.getElementById('kagitSilBtn').addEventListener('click', () => {
        $.ajax({
            url: "/rapor/kagit_sil",
            type: 'text',
            method: 'POST',
            data: {
                'id': thisId,
            },
            success: () => {
                window.location.reload();
            },
            error: () => {
                hataToast()
            }
        })
    })
}

function editOgrenci(e) {
    let kaydetBtn = document.getElementById('ogrenciDegistirBtn')
    kaydetBtn.setAttribute('disabled', '')
    let thisTr = e.closest('tr')
    let thisOnizleme = thisTr.querySelector('img').cloneNode()
    let thisName = thisTr.childNodes[1].innerHTML
    let secilenOgrenci;
    let body = document.getElementById('ogrenci-ad-degistir-body')
    let formGroup = document.createElement('div')
    let selectInput = document.createElement('select')
    selectInput.style = 'width: 100%'
    formGroup.className = 'form-row'
    let ilkCol = document.createElement('div')
    ilkCol.className = 'col'
    ilkCol.appendChild(thisOnizleme)
    let ikiCol = document.createElement('div')
    ikiCol.className = 'col'
    ikiCol.appendChild(selectInput)
    let uyari = document.createElement('small')
    uyari.className = 'mt-3 text-muted'
    formGroup.append(ilkCol, ikiCol, uyari)
    for(i = 0; i < _bilgiler['sinif_ogrenciler'].length; i++) {
        selectInput.innerHTML += "<option value=\"" + _bilgiler['sinif_ogrenciler'][i][1] + "\">" + _bilgiler['sinif_ogrenciler'][i][0] + "</option>";
        if (_bilgiler['sinif_ogrenciler'][i][0] == thisName) {
            secilenOgrenci = _bilgiler['sinif_ogrenciler'][i][1]
        }
    }
    $(selectInput).select2({language: "tr"});
    $(selectInput).val(secilenOgrenci);
    $(selectInput).trigger('change');
    body.innerHTML = ''
    body.appendChild(formGroup)
    $('#ogrenciAdDegistir').modal('show')
    const thisId = getThisId(thisOnizleme)
    let ids = new Array();
    for (i=0; i < _bilgiler['ogrenciler'].length; i++) {
        ids.push(_bilgiler['ogrenciler'][i]['gercek_ogrenci_id'])
    }
    let durum;
    let secilenId;
    $(selectInput).on('change', () => {
        secilenId = parseInt($(selectInput).val())
        if (secilenId == secilenOgrenci) {
            uyari.innerHTML = ''
            kaydetBtn.setAttribute('disabled', '')
            durum = 'ayni'
        }
        else if (ids.includes(secilenId) && secilenId != secilenOgrenci ) {
            uyari.innerHTML = thisTranslations['eslestirmeUyari'][lang]
            kaydetBtn.removeAttribute('disabled')
            durum = 'var'
        }
        else {
            uyari.innerHTML = '';
            kaydetBtn.removeAttribute('disabled')
            durum = 'yeni'
        }
    })
    kaydetBtn.addEventListener('click', () => {
        $.ajax({
            url: "/rapor/ogrenci_eslestirme_degis",
            data: {
                'id': thisId,
                'secilen': secilenId,
                'durum': durum,
            },
            dataType: "text",
            type: 'POST',
            success: () => {
                window.location.reload();
            },
            error: () => {
                hataToast()
            }
        })
    })
}

let _bilgiler;

$.ajax({
        url: "/rapor/soru_bilgileri",
        data: {
            'id': window.location.href.split("/").pop().replace('#', ''),
        },
        dataType: "text",
        type: 'POST',
        success: (bilgiler) => {
            _bilgiler = JSON.parse(bilgiler)
            for (i=0; i < _bilgiler['ogrenciler'].length; i++) {
                let icerik = _bilgiler['ogrenciler'][i]['adsoyad']
                _bilgiler['ogrenciler'][i]['adsoyad'] = icerik.includes(thisTranslations['hata'][lang]) ? icerik.replace('.png', '') : '<img src="' + icerik + '" loading=lazy style="width: 24rem">'
            }
            switch (lang) {
                case 'tr':
                    document.getElementById('ders-adi').innerText = 'Bu ' + _bilgiler['ad'] + ' sınavında'
                case 'en':
                    document.getElementById('ders-adi').innerText = 'In this ' + _bilgiler['ad'] + ' exam'
            }
            document.getElementById('kagit-sayisi').innerText = _bilgiler['kagit_sayisi'] + thisTranslations['okundu'][lang]
            document.getElementById('sinif-adi').innerHTML = _bilgiler['sinif'] != null ? truncateString(_bilgiler['sinif']) : thisTranslations['iliskilendir'][lang] + '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-box-arrow-in-up-right" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M6.364 13.5a.5.5 0 0 0 .5.5H13.5a1.5 1.5 0 0 0 1.5-1.5v-10A1.5 1.5 0 0 0 13.5 1h-10A1.5 1.5 0 0 0 2 2.5v6.636a.5.5 0 1 0 1 0V2.5a.5.5 0 0 1 .5-.5h10a.5.5 0 0 1 .5.5v10a.5.5 0 0 1-.5.5H6.864a.5.5 0 0 0-.5.5z"/><path fill-rule="evenodd" d="M11 5.5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793l-8.147 8.146a.5.5 0 0 0 .708.708L10 6.707V10.5a.5.5 0 0 0 1 0v-5z"/></svg>'
            $('#baslik').hover(() => {
                $('#editBtn').attr('style', 'margin-top:3px; margin-right:10px; display:inline')
            },
            () => {
                $('#editBtn').attr('style', 'display:none')
            })
            document.getElementById('sinavlar-btn').className = 'nav-link active'
            document.getElementById('canvas-div').style = 'height:0; display:none;'
            $('a[href="#kazanim"]').on('shown.bs.tab', function (e) {
                document.getElementById('canvas-div').style = 'height:auto; display:block;'
            })
            $('a[href="#kazanim"]').on('hidden.bs.tab', function (e) {
                document.getElementById('canvas-div').style = 'height:0; display:none;'
            })
            let columns = [
                {data: 'adsoyad'},
            ]
            let duzenleBtn = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="var(--prussian)" class="mb-1 mx-2 bi bi-pencil-square" viewBox="0 0 16 16"><path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"/><path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5v11z"/></svg>'
            let silBtn = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="var(--prussian)" class="mb-1 mx-2 bi bi-trash" viewBox="0 0 16 16"><path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/></svg>'
            let previewBtn = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="var(--prussian)" class="mb-1 mx-2 bi bi-eye" viewBox="0 0 16 16"><path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z"/><path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z"/></svg>'
            if (_bilgiler['sinif'] != null) {
                thEkle(true)
                columns.push({data: 'gercek_ogrenci'})
                columns.push({data: 'puan'})
                columns.push({data: 'eylem',"orderable": false, "searchable": false})
                columns.push({data: 'gercek_ogrenci_id', visible:false})
                columns.push({data: 'id', visible:false})
                for (i=0; i<_bilgiler['ogrenciler'].length; i++) {
                    _bilgiler['ogrenciler'][i]['eylem'] = '<div class="d-flex justify-content-start"><span class="eylem-btn" onclick="editOgrenci(this)">'  + duzenleBtn + '</span><span class="eylem-btn" onclick="kagitSil(this)">' + silBtn + '</span><span class="eylem-btn" onclick="previewOgr(this)">' + previewBtn + '</span></div>'
                }
            }
            else {
                thEkle(false)
                columns.push({data: 'puan'})
                columns.push({data: 'eylem',"orderable": false, "searchable": false})
                columns.push({data: 'id', visible:false})
                for (i=0; i<_bilgiler['ogrenciler'].length; i++) {
                    _bilgiler['ogrenciler'][i]['eylem'] = '<div class="d-flex justify-content-start"><span class="eylem-btn" onclick="kagitSil(this)">' + silBtn + '</span><span class="eylem-btn" onclick="previewOgr(this)">' + previewBtn + '</span></div>'
                }
            }
            const table = $('#data').DataTable({
                "order": [[ 2, "desc" ]],
                "oLanguage": {
                    "sUrl": locales[lang]
                },
                "pageLength": 50,
                data: _bilgiler['ogrenciler'],
                columns: columns,
            });
            $('#data tbody').on('click', 'tr', function (e) {
                const data = table.row( this ).data();
                let targets = ['svg', 'path', 'SPAN']
                if (! targets.includes(e.target.nodeName)) {
                    window.location.href = data['adsoyad'].includes(thisTranslations['hata'][lang]) ? '' : thisTranslations['ogrUri'][lang] + data['id']
                }
            })
            var ctx = document.getElementById('chart2').getContext('2d');
            new Chart(ctx, {
                type: 'polarArea',
                data: {
                    labels: Object.keys(_bilgiler['kazanimlar']).map(s => s.substring(0, 120)),
                    datasets: [{
                        label: thisTranslations['labelTip'][lang],
                        data: Object.values(_bilgiler['kazanimlar']),
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.2)',
                            'rgba(54, 162, 235, 0.2)',
                            'rgba(255, 206, 86, 0.2)',
                            'rgba(75, 192, 192, 0.2)',
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
})

function baslikSwitch(e) {
  let txt = e.innerHTML;
  let element = document.getElementById('baslik');

  element.innerHTML = `<input id="baslik-degistir" class="form-control" onceki='${e.innerHTML}' onblur='baslikReset(this)' value='${txt}'/>`;
  document.getElementById('baslik-degistir').focus();
}

function baslikReset(e) {
  let txt = e.value;
  let onceki = e.getAttribute('onceki')
  if (txt != onceki && (txt.length < 4 || txt.length > 80) ) {
    toastr.options.timeOut = 1500; // 1.5s
    toastr.options = {
    "positionClass": "toast-bottom-right",
    "preventDuplicates": true
    }
    toastr.error(thisTranslations['uyariBaslik'][lang]);
    let element = document.getElementById('baslik');

    element.innerHTML = `<span onclick='baslikSwitch(this)'>${onceki}</span>`;
  }
  else if (txt == onceki) {
    let element = document.getElementById('baslik');

    element.innerHTML = `<span onclick='baslikSwitch(this)'>${onceki}</span>`;
  }
  else {
      $.ajax({
        url: "/rapor/sinav_ad_degistir",
        data: {
            'id': window.location.href.split("/").pop().replace('#', ''),
            'ad': txt
        },
        dataType: "text",
        type: 'POST',
        success: () => {
            toastr.options.timeOut = 1500; // 1.5s
            toastr.options = {
            "positionClass": "toast-bottom-right",
            "preventDuplicates": true
            }
            toastr.success(thisTranslations['successBaslik'][lang]);
            let element = document.getElementById('baslik');

            element.innerHTML = `<span onclick='baslikSwitch(this)'>${txt}</span>`;
        },
        error: () => {
            hataToast();
        }
      })
  }
}

function silModalFunc() {
    $('#sinavSilModal').modal('show')
}

function sinaviSil() {
    $.ajax({
        url: "/rapor/sinav_sil",
        data: {
            'id': window.location.href.split("/").pop().replace('#', ''),
        },
        dataType: "text",
        type: 'POST',
        success: () => {
            window.location.href = '/pg/panel/sinavlar'
        },
        error: () => {
            hataToast()
        }
    })
}

function returnBekleniyor() {
    let div = document.createElement('div')
    div.className = 'text-center'
    let baslik = document.createElement('h3')
    baslik.innerHTML = thisTranslations['bekle'][lang]
    let spinnerDiv = document.createElement('div')
    spinnerDiv.className = 'spinner-border text-info'
    spinnerDiv.setAttribute('role', 'status')
    let spinSpan = document.createElement('span')
    spinSpan.className = 'sr-only'
    spinSpan.innerHTML = 'Loading...'
    spinnerDiv.appendChild(spinSpan)
    div.append(baslik, spinnerDiv)
    return div
}

function siniflaIliskilendir() {
    let modalBody = document.getElementById('iliskilendir-body')
    let gonderBtn = document.getElementById('iliskiGonder')
    if (_bilgiler['user_siniflar'].length == 0 ) {
        let sinifAciklama = document.createElement('p')
        sinifAciklama.innerHTML = thisTranslations['sifirSinif'][lang]
        modalBody.innerHTML = ''
        modalBody.appendChild(sinifAciklama)
    }
    else {
        let formGroup = document.createElement('div')
        formGroup.className = 'form-group'
        let label = document.createElement('label')
        label.innerHTML = thisTranslations['linkClass'][lang]
        let selectInput = document.createElement('select')
        selectInput.className = 'form-control'
        selectInput.setAttribute('style', 'width: 100%;')
        formGroup.append(label, selectInput)
        for(var i = 0; i < _bilgiler['user_siniflar'].length; i++) {
            selectInput.innerHTML += "<option value=\"" + _bilgiler['user_siniflar'][i]['id'] + "\">" + _bilgiler['user_siniflar'][i]['ad'] + "</option>";
        }
        $(selectInput).select2({
            language: "tr"
        });
        $(selectInput).val(null);
        $(selectInput).trigger('change');
        modalBody.innerHTML = ''
        modalBody.appendChild(formGroup)
        gonderBtn.addEventListener('click', () => {
            let bekleniyor = returnBekleniyor();
            modalBody.innerHTML = ''
            modalBody.appendChild(bekleniyor)
            gonderBtn.setAttribute('disabled', '')
            $.ajax({
                url: "/rapor/sinif_eslestir",
                data: {
                    'sinav_id': window.location.href.split("/").pop().replace('#', ''),
                    'sinif_id': $(selectInput).val()
                },
                dataType: "text",
                type: 'POST',
                success: () => {
                    window.location.reload();
                },
                error: (err) => {
                    modalBody.innerHTML = ''
                    modalBody.appendChild(formGroup)
                    gonderBtn.removeAttribute('disabled')
                    if (err.status == 404) {
                        toastr.options.timeOut = 1500; // 1.5s
                        toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
                        toastr.error('');
                    }
                    else {
                        hataToast()
                    }
                }
            })
        })
    }

    $('#iliskilendirModal').modal('show')
    }