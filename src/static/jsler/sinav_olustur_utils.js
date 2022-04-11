$('#logoModal').on('show.bs.modal', function () {
    $('#logo-sec').select2({
        language: "tr"
    });
    $.ajax({
    url:'/logolari_al',
    type:'get',
    success: (data) => {
        let logo_sec = document.getElementById('logo-sec')
        let logo_file =document.getElementById('logo-file')
        if (data.length == 0) {
            $("#logo-sec").select2('destroy');
            let body = this.querySelector('.modal-body')
            let goster_button = logo_file.previousElementSibling
            goster_button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" class="bi bi-upload" viewBox="0 0 16 16"><path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/><path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/></svg> Logo Yükleyin'
            goster_button.style = 'min-width: 100%;'
            body.innerHTML = ''
            let bu_col = document.createElement('div')
            bu_col.className = 'col'
            bu_col.id = 'logo-file-col'
            bu_col.appendChild(goster_button)
            bu_col.appendChild(logo_file)
            body.appendChild(bu_col)
        }
        else {
            logo_sec.innerHTML = ''
            for(var i = 0; i < data.length; i++) {
                logo_sec.innerHTML += "<option value=\"" + data[i]['id'] + "\">" + data[i]['name'] + "</option>";
            }
            $('#logo-sec').val(null);
            $('#logo-sec').trigger('change');
            $('#logo-sec').on('change', () => {
                document.getElementById('logo-secimi').value = $("#logo-sec").val()
                document.getElementById('logo-secilen-ph').placeholder = 'Seçilen Logo: ' + $("#logo-sec option:selected").text()
                $('#logoModal').modal('hide')
            })
        }
        logo_file.onchange = () => {
            let logo_file_types = ['jpg','jpeg', 'png']
            let file_ad = logo_file.files[0].name.toLowerCase();
            let logoLabel = document.getElementById('logo-file-label')
            if (logo_file.files[0].size > 500000 ) {
                toastr.options.timeOut = 1500;
                toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
                toastr.error('En fazla 500KB büyüklüğünde bir dosya yükleyebilirsiniz.');
                logo_file.value = ''
                document.getElementById('logo-ad-input').style = 'display:none;'
                logoLabel.style = 'min-height: 100%'
            }
            else if(! logo_file_types.includes(file_ad.split('.').pop())) {
                toastr.options.timeOut = 1500;
                toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
                toastr.error('Lütfen geçerli bir görsel seçiniz.');
                logo_file.value = ''
                document.getElementById('logo-ad-input').style = 'display:none;'
                logoLabel.style = 'min-height: 100%'
            }
            else {
                // logoLabel.style = 'min-height:0;'
                let col = document.getElementById('logo-file-col')
                let ad_input = document.createElement('input')
                let footer = document.getElementById('logo-modal-footer')
                col.appendChild(ad_input)
                ad_input.className = 'form-control mt-2'
                ad_input.placeholder = 'Logo için bir ad giriniz'
                ad_input.id = 'logo-ad-input'
                ad_input.addEventListener('input', () => {
                    if ((ad_input.value.length > 0 && ad_input.value.length < 99) && footer.childElementCount == 1) {
                        let logo_kaydet = document.createElement('button')
                        logo_kaydet.className = 'btn btn-primary'
                        logo_kaydet.innerHTML = 'Kaydet'
                        logo_kaydet.id = 'logo-yukle'
                        logo_kaydet.addEventListener('click', () => {
                            let logoForm = new FormData()
                            logoForm.append('file', logo_file.files[0], logo_file.files[0].name)
                            logoForm.append('name', ad_input.value)
                            $.ajax({
                                type: 'post',
                                url: '/logo_kaydet',
                                processData: false, 
                                contentType: false,
                                data: logoForm,
                                success: (data) => {
                                    $('#logoModal').modal('hide');
                                    document.getElementById('logo-secimi').value = data['id']
                                    document.getElementById('logo-secilen-ph').placeholder = 'Seçilen Logo: ' + data['name']
                                    toastr.options.timeOut = 1500;
                                    toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
                                    toastr.success('Logo yüklendi.');
                                },
                                error: () => {
                                    hataToast()
                                }
                            })
                        }) 
                        footer.appendChild(logo_kaydet)
                    }
                    else if ((ad_input.value.length == 0 || ad_input.value.length > 99) && footer.childElementCount > 1) {
                        let logo_kaydet = footer.childNodes[3]
                        $(logo_kaydet).remove()
                    }
                }) 
            }
        }
    }
})
})


let _kazanimlar = false;

function sayfaDuzeni(e){
    var sd = document.getElementById('sayfa-duzeni-hidden')
    sd.value = e.id
}
var mq = window.matchMedia( "(max-width: 768px)" );
if (mq.matches) {
    var degistir = document.getElementById('degistir')
    degistir.removeAttribute('class')
}
const textarea = document.querySelector("#ust_yazi");

textarea.addEventListener("input", event => {
    const target = event.currentTarget;
    const maxLength = 120;
    const currentLength = target.value.length;
    var gonder_dugme = document.getElementById('save-button');

    if (currentLength >= maxLength) {
    $('#ust_yazi').attr('class', 'form-control is-invalid')
        gonder_dugme.setAttribute('disabled', '');
        return $('#characterLeft').html('Daha fazla yazamazsınız');
    }
    else if (currentLength <= maxLength){
        gonder_dugme.removeAttribute('disabled');
        $('#ust_yazi').attr('class', 'form-control is-valid')
    }
    $('#characterLeft').attr('style', 'display:block;')
    $('#characterLeft').html(`${maxLength - currentLength} karakter kaldı`);
});

textarea.addEventListener("focusout", event => {
    $('#characterLeft').attr('style', 'display:none;')
})

const textarea2 = document.querySelector("#alt_yazi");

textarea2.addEventListener("input", event => {
    const target = event.currentTarget;
    const maxLength = 120;
    const currentLength = target.value.length;
    var gonder_dugme = document.getElementById('save-button');

    if (currentLength >= maxLength) {
    $('#alt_yazi').attr('class', 'form-control is-invalid')
        gonder_dugme.setAttribute('disabled', '');
        return $('#characterLeft2').html('Daha fazla yazamazsınız');
    }
    else if (currentLength <= maxLength){
        gonder_dugme.removeAttribute('disabled');
        $('#alt_yazi').attr('class', 'form-control is-valid')
    }
    $('#characterLeft2').attr('style', 'display:block;')
    $('#characterLeft2').html(`${maxLength - currentLength} karakter kaldı`);
});

textarea2.addEventListener("focusout", event => {
    $('#characterLeft2').attr('style', 'display:none;')
})