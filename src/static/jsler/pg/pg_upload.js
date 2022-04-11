document.getElementById('sinav_kodu').addEventListener('input', () => {
    document.getElementById('sinav_kodu').value = document.getElementById('sinav_kodu').value.toUpperCase();
})
var $fileInput = $('.file-input');
var $droparea = $('.file-drop-area');

// highlight drag area
$fileInput.on('dragenter', function() {
    $droparea.css('border', '1px solid var(--steel)')
    $droparea.css('background-color', 'var(--sky)')
});

// back to normal state
$fileInput.on('dragleave blur drop', function() {
    $droparea.css('border', '1px dashed var(--sky)')
    $droparea.css('background-color', 'aliceblue')
});

let translations = {
    'dragNDrop': {
        'tr': 'ya da sürükleyip bu alana bırakın.',
        'en': 'or drang and drop them here.'
    },
    '#ofFiles': {
        'tr': ' dosya seçildi.',
        'en': ' files chosen.'
    },
    'detecting': {
        'tr': 'Sorular tespit ediliyor...',
        'en': 'Detecting the questions...'
    },
    'errExt': {
        'tr': '"Desteklenen dosya türleri: JPG, PNG, PDF."',
        'en': "Valid file extensions: JPG, PNG, PDF."
    },
    'unknownErr': {
        'tr': "Bilinmeyen bir hata oluştu.",
        'en': "An unknown error occurred."
    }
}

// change inner text
$fileInput.on('change', function() {
    $droparea.css('border', '1px dashed var(--sky)')
    $droparea.css('background-color', 'aliceblue')
    var filesCount = $(this)[0].files.length;
    var $textContainer = $(this).prev();

    if (filesCount === 1) {
        // if single file is selected, show file name
        var fileName = $(this).val().split('\\').pop();
        $textContainer.text(fileName);
    } 
    else if (filesCount == 0) {
        $textContainer.text(translations['dragNDrop'][lang]);
    }
    else {
        // otherwise show number of files
        $textContainer.text(filesCount + translations['#ofFiles'][lang]);
    }
});
$("#betikform").submit(function(e){
    e.preventDefault();
    $('#yukleniyor').modal('show');
    var form = document.getElementById('betikform')
    var files = document.getElementById('sinavlar').files
    duzenliListe = Array.from(files);
    duzenliListe.sort(function(a,b){
        return a.name.localeCompare(b.name, undefined, {
            numeric: true,
            sensitivity: 'base'
        });
    });

    var fd = new FormData(form)
    
    for (var x = 0; x < duzenliListe.length; x++) {
        fd.append("pictures[]", duzenliListe[x]);
    }
    $.ajax({
        type : 'POST',
        url : '/pg/form_al',
        data: fd,
        processData: false,
        contentType: false,
        success: (data) => {
            var guncelleme_gonder = document.getElementById('guncelle')
            guncelleme_gonder.innerHTML = translations['detecting'][document.documentElement.lang]
            var refreshIntervalId = setInterval(function (){
                                    $.ajax({
                                        url:"/yukleme_guncelleme",
                                        data: '',
                                        dataType:"text",
                                        type: 'POST',
                                        success:function(){
                                            clearInterval(refreshIntervalId)
                                            window.location.href = '/pg/form/1'
                                            },
                                        error: function(err){
                                            if (err.status == 500) {
                                                setTimeout(() => {$('#yukleniyor').modal('hide');}, 500)
                                                clearInterval(refreshIntervalId)
                                                hataToast()
                                                $.ajax({
                                                    url: "/pg/kagit_sil",
                                                    data: '',
                                                    dataType: "text",
                                                    type: 'POST'
                                                })
                                            }
                                        }
                                    });
                                }, 2500)
        },
        error: (data) => {
            function modalHide () {
                $('#yukleniyor').modal('hide')
            }
            setTimeout(modalHide, 500)
            if (data.status == 501) {
                toastr.options.timeOut=1500;
                toastr.options={"positionClass":"toast-bottom-right","preventDuplicates":true};
                toastr.error(translations['errExt'][document.documentElement.lang])
            }
            else {
                toastr.options.timeOut=1500;
                toastr.options={"positionClass":"toast-bottom-right","preventDuplicates":true};
                toastr.error(translations['unknownErr'][document.documentElement.lang])
            }
        }
    })
});