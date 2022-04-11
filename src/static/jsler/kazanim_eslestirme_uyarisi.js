$(document).ready(function() {
    $('#kazanimUyarisi').modal('show')
  })
  $('.btn').on('click', (e) => {
    if (e.target.id == 'degistir') {
      $.ajax({
          url: "/pg/kazanim_degisiklikleri",
          data: {'istek': 'sinav_id'},
          dataType: "text",
          type: 'POST',
          success: function(data) {
            const id = data
            let baslik = document.getElementById('kazanimUyarisiLabel')
            let icerik = document.getElementById('modal-icerik')
            let modalFooter = document.getElementById('modal-alt')
            let devam = document.getElementById('devam')
            let eskiIcerik = {'baslik': baslik.innerHTML, 'icerik': icerik.innerHTML}
            if (document.getElementById('modal-geri') == null) {
              let geriButton = document.createElement('button')
              geriButton.className = 'btn btn-secondary'
              geriButton.style = 'margin-top: -1px;'
              geriButton.id = "modal-geri"
              geriButton.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-arrow-90deg-left" viewBox="0 0 16 16"><path fill-rule="evenodd" d="M1.146 4.854a.5.5 0 0 1 0-.708l4-4a.5.5 0 1 1 .708.708L2.707 4H12.5A2.5 2.5 0 0 1 15 6.5v8a.5.5 0 0 1-1 0v-8A1.5 1.5 0 0 0 12.5 5H2.707l3.147 3.146a.5.5 0 1 1-.708.708l-4-4z"/></svg> Geri Dön'
              modalFooter.appendChild(geriButton)
              geriButton.onclick = () => {
                baslik.innerHTML = eskiIcerik['baslik'];
                icerik.innerHTML = eskiIcerik['icerik'];
                devam.style = 'display: inline-block; margin-top: -1px'
                $(geriButton).remove();
              }
              devam.style = 'display:none;'
            }
            icerik.innerHTML = '<div class="row justify-content-center text-center"><div class="form-group col-4"><label for="mevcut-id">Şu anki sınav kodu: </label><input class="form-control" id="mevcut-id" type="text" placeholder="' + id + '" readonly></div><div class="form-group col-4"><label for="yeni-id">Yeni Sınav Kodu: </label><input class="form-control" id="yeni-id" type="text" maxlength="5"></input></div>'
            baslik.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" class="mb-2 bi bi-plus-circle-dotted" viewBox="0 0 16 16"><path d="M8 0c-.176 0-.35.006-.523.017l.064.998a7.117 7.117 0 0 1 .918 0l.064-.998A8.113 8.113 0 0 0 8 0zM6.44.152c-.346.069-.684.16-1.012.27l.321.948c.287-.098.582-.177.884-.237L6.44.153zm4.132.271a7.946 7.946 0 0 0-1.011-.27l-.194.98c.302.06.597.14.884.237l.321-.947zm1.873.925a8 8 0 0 0-.906-.524l-.443.896c.275.136.54.29.793.459l.556-.831zM4.46.824c-.314.155-.616.33-.905.524l.556.83a7.07 7.07 0 0 1 .793-.458L4.46.824zM2.725 1.985c-.262.23-.51.478-.74.74l.752.66c.202-.23.418-.446.648-.648l-.66-.752zm11.29.74a8.058 8.058 0 0 0-.74-.74l-.66.752c.23.202.447.418.648.648l.752-.66zm1.161 1.735a7.98 7.98 0 0 0-.524-.905l-.83.556c.169.253.322.518.458.793l.896-.443zM1.348 3.555c-.194.289-.37.591-.524.906l.896.443c.136-.275.29-.54.459-.793l-.831-.556zM.423 5.428a7.945 7.945 0 0 0-.27 1.011l.98.194c.06-.302.14-.597.237-.884l-.947-.321zM15.848 6.44a7.943 7.943 0 0 0-.27-1.012l-.948.321c.098.287.177.582.237.884l.98-.194zM.017 7.477a8.113 8.113 0 0 0 0 1.046l.998-.064a7.117 7.117 0 0 1 0-.918l-.998-.064zM16 8a8.1 8.1 0 0 0-.017-.523l-.998.064a7.11 7.11 0 0 1 0 .918l.998.064A8.1 8.1 0 0 0 16 8zM.152 9.56c.069.346.16.684.27 1.012l.948-.321a6.944 6.944 0 0 1-.237-.884l-.98.194zm15.425 1.012c.112-.328.202-.666.27-1.011l-.98-.194c-.06.302-.14.597-.237.884l.947.321zM.824 11.54a8 8 0 0 0 .524.905l.83-.556a6.999 6.999 0 0 1-.458-.793l-.896.443zm13.828.905c.194-.289.37-.591.524-.906l-.896-.443c-.136.275-.29.54-.459.793l.831.556zm-12.667.83c.23.262.478.51.74.74l.66-.752a7.047 7.047 0 0 1-.648-.648l-.752.66zm11.29.74c.262-.23.51-.478.74-.74l-.752-.66c-.201.23-.418.447-.648.648l.66.752zm-1.735 1.161c.314-.155.616-.33.905-.524l-.556-.83a7.07 7.07 0 0 1-.793.458l.443.896zm-7.985-.524c.289.194.591.37.906.524l.443-.896a6.998 6.998 0 0 1-.793-.459l-.556.831zm1.873.925c.328.112.666.202 1.011.27l.194-.98a6.953 6.953 0 0 1-.884-.237l-.321.947zm4.132.271a7.944 7.944 0 0 0 1.012-.27l-.321-.948a6.954 6.954 0 0 1-.884.237l.194.98zm-2.083.135a8.1 8.1 0 0 0 1.046 0l-.064-.998a7.11 7.11 0 0 1-.918 0l-.064.998zM8.5 4.5a.5.5 0 0 0-1 0v3h-3a.5.5 0 0 0 0 1h3v3a.5.5 0 0 0 1 0v-3h3a.5.5 0 0 0 0-1h-3v-3z"/></svg> Yeni Sınav Kodu'
            let yeniId = document.getElementById('yeni-id')
            yeniId.addEventListener('input', () => {
              yeniId.value = yeniId.value.toUpperCase();
            })
            e.target.onclick = () => {
              if (yeniId.value == '') {
                toastr.options.timeOut = 1500; // 1.5s
                    toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
                    toastr.error('Lütfen bir değer giriniz.');
                    yeniId.focus();
              }
              else {
                $.ajax({
                  url: "/pg/kazanim_degisiklikleri",
                  data: {'istek': yeniId.value},
                  dataType: "text",
                  type: 'POST',
                  success: function(_id) {
                    icerik.innerHTML = '<div class="text-center"><h3>Lütfen Bekleyin</h3><div class="spinner-border text-info" role="status"><span class="sr-only">Loading...</span></div></div>'
                    var refreshIntervalId = setInterval(function (){
                        $.ajax({
                            url:"/yukleme_guncelleme",
                            data: {'aydi': _id},
                            dataType:"text",
                            type: 'POST',
                            success:function(data){
                                clearInterval(refreshIntervalId)
                                window.location.reload();
                                },
                            error: function(){
                                //pass
                            }
                        });
                    }, 2500)
                  },
                  error: () => {
                    icerik.innerHTML = '<div class="row justify-content-center text-center"><div class="form-group col-4"><label for="mevcut-id">Şu anki sınav kodu: </label><input class="form-control" id="mevcut-id" type="text" placeholder="' + id + '" readonly></div><div class="form-group col-4"><label for="yeni-id">Yeni Sınav Kodu: </label><input class="form-control" id="yeni-id" type="text" maxlength="5"></input></div>'
                    toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
                    toastr.error('Böyle bir sınav bulunamadı.');
                    yeniId.focus();
                  }
                })
              }
            }
          }
      })
    }
    else {
      $.ajax({
          url: "/pg/kazanim_degisiklikleri",
          data: {'istek': e.target.id},
          dataType: "text",
          type: 'POST',
          success: function(data) {
            location.reload();
          }
      })
    }
  })