var raporGeldiMi = false;
function enableButton(button) {
    button.removeAttribute('disabled')
}

function raporRender(data) {
    let hedef = document.getElementById('rapor-div')
    hedef.innerHTML = ''
    intervalManager(false, raporDurumu)
    let yenile_button = document.createElement('button')
    yenile_button.setAttribute('disabled', '')
    yenile_button.onclick = raporIste
    setTimeout(enableButton(yenile_button), 500)
    yenile_button.className = 'btn btn-info btn-block'
    yenile_button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="mb-1 bi bi-arrow-repeat" viewBox="0 0 16 16"><path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"/><path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"/></svg>' + translations['renewReport'][lang]
    let _iframe = document.createElement('iframe')
    _iframe.src = data
    _iframe.type = 'application/pdf'
    _iframe.width = '100%'
    _iframe.height = '650px'
    hedef.append(yenile_button, _iframe)
    raporGeldiMi = data;
}

function raporDurumu() {
    if (raporGeldiMi == false) {
        $.ajax({
            type: "POST",
            url: '/rapor/rapor_kontrol',
            data:{'id': window.location.href.split("/").pop().replace('#', '')},
            success: (data) => {
                let hedef = document.getElementById('rapor-div')
                hedef.innerHTML = ''
                if (data == 'yok' || data == '') {
                    let baslik = document.createElement('h3')
                    baslik.innerHTML = translations['raporCikti'][lang]
                    let ilk_aciklama = document.createElement('p')
                    ilk_aciklama.innerHTML = translations['aciklama1'][lang]
                    let ikinci_aciklama = document.createElement('p')
                    ikinci_aciklama.innerHTML = translations['aciklama2'][lang]
                    hedef.append(baslik, ilk_aciklama, ikinci_aciklama)
                    let form = document.createElement('form')
                    form.addEventListener('submit', raporIste)
                    let form_div = document.createElement('div')
                    form_div.className = 'form-group form-check'
                    let input = document.createElement('input')
                    input.type = 'checkbox'
                    input.className = 'bgcheck form-check-input'
                    input.setAttribute('required', '')
                    input.id = 'exampleCheck1'
                    let label = document.createElement('label')
                    label.className = 'form-check-label'
                    label.htmlFor = 'exampleCheck1'
                    label.innerHTML = translations['imSure'][lang]
                    form_div.append(input, label)
                    form.appendChild(form_div)
                    let submit_button = document.createElement('button')
                    submit_button.type = 'submit'
                    submit_button.className = 'btn btn-primary'
                    submit_button.innerHTML = translations['reqRep'][lang]
                    form.appendChild(submit_button)
                    hedef.appendChild(form)
                }
                else if (data == 'bekliyor') {
                    let bekle = bekleniyor()
                    hedef.appendChild(bekle)
                }
                else {
                    raporRender(data)
                }
            },
            error: () => {
                hataToast()
            }
        })
    }
    else {
        raporRender(raporGeldiMi)
    }
}

function bekleniyor() {
    let div = document.createElement('div')
    let baslik = document.createElement('h3')
    baslik.innerHTML = translations['repHazirlaniyor'][lang]
    let aciklama = document.createElement('p')
    aciklama.innerHTML = translations['repBildir'][lang]
    let spinnerDiv = document.createElement('div')
    spinnerDiv.className = 'spinner-border text-info'
    spinnerDiv.setAttribute('role', 'status')
    let spinSpan = document.createElement('span')
    spinSpan.className = 'sr-only'
    spinSpan.innerHTML = 'Loading...'
    spinnerDiv.appendChild(spinSpan)
    div.append(baslik, aciklama, spinnerDiv)
    return div
}

function raporIste(event) {
    event.preventDefault();
    $.ajax({
        type: "POST",
        url: '/rapor/pdfolustur',
        data:{'id': window.location.href.split("/").pop().replace('#', '')},
        success: () => {
            raporGeldiMi = false;
            let hedef = document.getElementById('rapor-div')
            let bekle = bekleniyor()
            hedef.innerHTML = ''
            hedef.appendChild(bekle)
            intervalManager(true, raporDurumu, 3000)
        },
        error: () => {
            hataToast()
        }
    })
}

  $(document).ready(function () {
      yanitDegisFunc = (soru_id, txt, e) => {
        $.ajax({
            url: "/rapor/soru_cevap_degistir",
            data: {
                'id': soru_id,
                'cevap': txt
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
      }
    document.getElementById('canvas-div').style = 'height:0; display:none'
    $('a[href="#rapor"]').on('shown.bs.tab', function (e) {
        raporDurumu()
      })
    $('a[href="#kazanim"]').on('shown.bs.tab', function (e) {
        document.getElementById('canvas-div').style = 'height:auto; display:block;'
    })
    $('a[href="#kazanim"]').on('hidden.bs.tab', function (e) {
        document.getElementById('canvas-div').style = 'height:0; display:none;'
    })
    document.getElementById('sinavlar-btn').className = 'nav-link active'
    let locales = {'tr': '//cdn.datatables.net/plug-ins/9dcbecd42ad/i18n/Turkish.json', 'en': ''}
    const table = $('#data').DataTable({
        "fnInitComplete": function (oSettings, json) {
            var ctx = document.getElementById('chart1').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: json['labels'],
                    datasets: [{
                        label: translations['sinifOrtalama'][lang],
                        data: Object.values(json['sinif_kazanimlari']),
                        backgroundColor: [
                            'rgba(70, 130, 180, 0.4)',
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                        ],
                        borderWidth: 0.2,
                    }, {
                        label: translations['ogrenciBasari'][lang],
                        data: Object.values(json['ogrenci_kazanimlari']),
                        backgroundColor: [
                            'rgba(0,0,255,0.4)',
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                        ],
                        borderWidth: 0.2,
                    }]
                },
            });
        },
        "createdRow": function( row, data, dataIndex){
            let liste = data['beklenen_cevaplar'].split(',')
            for (i=0; i < liste.length; i++) {
                row.childNodes[0].setAttribute('id', data['id'])
                $(row.childNodes[4]).wrapInner("<span onclick='spanSwitch(this)'></span>");
                if (data['ogrenci_cevaplari'] != liste[i] && data['guven'] < 0.9) {
                    row.className = 'dikkat'
                }
            }
        },
        "order": [[ 7, "asc" ]],
        "oLanguage": {
            "sUrl": locales[lang]
        },
        "pageLength": 50,
        "ajax": {
            "url": "/rapor/ogrenci_ajax",
            "type": "POST",
            "data": {'id': window.location.href.split("/").pop().replace('#', '')},
            "dataSrc":function(jsonObj) {
                for (i=0; i < jsonObj['bilgiler'].length; i++){
                    let s = jsonObj['bilgiler'][i]['sonuc']
                    let ss = jsonObj['bilgiler'][i]['sira']
                    let qt = jsonObj['bilgiler'][i]['tip']
                    jsonObj['bilgiler'][i]['sonuc'] = translations[s][lang]
                    jsonObj['bilgiler'][i]['sira'] = ss.replace('Soru ', translations['soru'][lang])
                    jsonObj['bilgiler'][i]['tip'] = translations['qTypes'][lang][qt]
                }
                return jsonObj['bilgiler'];      
            }
        },
        columns: [
            {data: 'sira'},
            {data: 'tip'},
            {data: 'puan'},
            {data: 'beklenen_cevaplar'},
            {data: 'ogrenci_cevaplari'},
            {data: 'sonuc'},
            {data: 'onizleme'},
            {data: 'id', visible:false}
        ]
    });

})