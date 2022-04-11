$(document).ready(function () {
    document.getElementById('sinavlar-btn').className = 'nav-link active'
    let locales = {'tr': '//cdn.datatables.net/plug-ins/9dcbecd42ad/i18n/Turkish.json', 'en': ''}
    const table = $('#data').DataTable({
        responsive: true,
        "fnInitComplete": function (oSettings, json) {
            let trs = Array.from(document.getElementsByTagName('tr')).slice(1)
            for (i=0; i < trs.length; i++) {
                trs[i].className = trs[i].className + ' gercekTr dp-body'
                let tarih = trs[i].childNodes[1].innerText
                trs[i].childNodes[1].innerText = dateToHowManyAgo(tarih)
            }
        },
        "order": [[ 6, "desc" ]],
        "oLanguage": {
            "sUrl": locales[lang]
        },
        ajax: {
            "url": "/rapor/sinavlar_ajax",
            "type": "POST",
            "dataSrc":"",
        },
        columns: [
        {data: 'ad'},
        {data: 'tarih'},
        {data: 'ogrenciler', searchable: false},
        {data: 'puan', searchable: false},
        {data: 'ders_adi'},
        {data: 'sinif'},
        {data: 'id', visible:false}
        ],
    });
    $('#data tbody').on('click', 'tr', function () {
            var data = table.row( this ).data();
            let link;
            switch(lang) {
                case 'tr':
                    link = '/pg/panel/sinavlar/'
                    break;
                case 'en':
                    link = '/pg/panel/exams/'
                    break;
            }
            window.location.href = link + data['id']
        } );
    });