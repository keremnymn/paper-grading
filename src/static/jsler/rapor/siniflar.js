document.getElementById('siniflar-btn').className = 'nav-link active'
document.getElementById('yenisinif-btn').addEventListener('click', () => {
    let sinifModal = document.getElementById('sinifModal')
    $(sinifModal).modal('show')
})

document.getElementById('yenisinif-form').addEventListener('submit', function(e) {
    e.preventDefault();
    $.ajax({
        type: "POST",
        url: "/yeni_sinif",
        data: {'ad': document.getElementById('sinifinput').value},
        success: function () {
            window.location.reload();
        },
        error: (data) => {
            if (data.status == 401) {
                toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
                toastr.error('Bu adı daha önce kullanmışsınız.');
            }
            else {
                toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
                toastr.error('Bir hata oluştu.');
            }
        }
    })
})

let tablo =  document.getElementById('data');
if (typeof(tablo) != 'undefined' && tablo != null){
    let locales = {'tr': '//cdn.datatables.net/plug-ins/9dcbecd42ad/i18n/Turkish.json', 'en': ''}
    const table = $(tablo).DataTable({
        "fnInitComplete": function (oSettings, json) {
            let trs = Array.from(document.getElementsByTagName('tr')).slice(1)
            for (i=0; i < trs.length; i++) {
                trs[i].className = trs[i].className + ' gercekTr dp-body'
            }
        },
        "order": [[ 1, "desc" ]],
        "oLanguage": {
            "sUrl": locales[lang]
        },
        "ajax": {
            "url": "/get_siniflar",
            "type": "GET",
            "dataSrc":""
        },
        columns: [
            {data: 'name'},
            {data: 'ogrenci_sayisi'},
            {data: 'sinav_sayisi'},
            {data: 'sinif_ort'},
            {data: 'id', visible:false},
        ]
    });
    $('#data tbody').on('click', 'tr', function () {
        var data = table.row( this ).data();
        window.location.href = '/pg/panel/siniflar/' + data['id']
    })
}