let lang = document.documentElement.lang
let dateTranslations = {
  'once': {'tr': 'önce', 'en': 'ago'},
  'saniye': {'tr': 'saniye', 'en': 'seconds'},
  'dakika': {'tr': 'dakika', 'en': 'minutes'},
  'saat': {'tr': 'saat', 'en':'hours'},
  'gun': {'tr': 'gün', 'en': 'days'},
  'ay': {'tr': 'ay', 'en': 'months'},
  'yil': {'tr': 'yıl', 'en': 'years'}
}
function dateToHowManyAgo(stringDate){
  var currDate = new Date();
  var diffMs=currDate.getTime() - new Date(stringDate).getTime();
  var sec=diffMs/1000;
  if(sec<60)
      return parseInt(sec)+' '+ dateTranslations['saniye'][lang] +(parseInt(sec)>1?'':'')+' ' + dateTranslations['once'][lang];
  var min=sec/60;
  if(min<60)
      return parseInt(min)+' '+ dateTranslations['dakika'][lang] +(parseInt(min)>1?'':'')+' ' + dateTranslations['once'][lang];
  var h=min/60;
  if(h<24)
      return parseInt(h)+' '+ dateTranslations['saat'][lang] +(parseInt(h)>1?'':'')+' ' + dateTranslations['once'][lang];
  var d=h/24;
  if(d<30)
      return parseInt(d)+' '+ dateTranslations['gun'][lang] +(parseInt(d)>1?'':'')+' ' + dateTranslations['once'][lang];
  var m=d/30;
  if(m<12)
      return parseInt(m)+' '+ dateTranslations['ay'][lang] +(parseInt(m)>1?'':'')+' ' + dateTranslations['once'][lang];
  var y=m/12;
  return parseInt(y)+' '+ dateTranslations['yil'][lang] +(parseInt(y)>1?'':'')+' ' + dateTranslations['once'][lang];
}

function set_message_count(sayi) {
    let message_count = document.getElementById('message_count')
    let bildirim_ikonu = document.getElementById('dropdownMenuButton2')
    if (! sayi == 0) {
        message_count.innerText = sayi
        message_count.style = 'display: inline;'
        bildirim_ikonu.setAttribute('data-toggle', 'dropdown')
    }
    else if (sayi == 0) {
      message_count.style = 'display:none'
    }
    else {
        message_count.style = 'display:none'
        bildirim_ikonu.removeAttribute('data-toggle', '')
    }
}
function okunduIsaretle(idler) {
  $.ajax({
    url: '/read_notifications',
    type: 'post',
    dataType: 'text',
    data: {'idler': idler},
    success: function () {
      for (i=0; i < idler.length; i++) {
        let degistir = document.getElementById(idler[i])
        degistir.id = idler[i].replace('yenibild_', 'bild_')
      }
    }
  })
}
function dividerEkle(dropdownid) {
  let dd = document.getElementById(dropdownid)
  let ddd = document.createElement('div')
  ddd.className = 'dropdown-divider'
  let _a = document.createElement('a')
  _a.className = 'dropdown-item text-center'
  _a.style = 'font-size: small'
  _a.innerText = 'Tümünü Gör'
  _a.href = '#'
  dd.appendChild(ddd)
  dd.appendChild(_a)
}

function yeniBildirimler () {
  $.ajax('/yeni_nots').done(
    function(yeni_nots) {
      let sayi = parseInt(yeni_nots)
      set_message_count(sayi)
    }
  )
}

function bildirimleri_al () {
  let bildirim_ekle = document.getElementById('bildirim_ekle')
  bildirim_ekle.innerHTML = '<div class="text-center"><div class="spinner-border text-info" role="status"><span class="sr-only"></span></div></div>'
    $.ajax('/notifications').done(
        function(notifications) {
          notifications.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            $('#bildirim_ekle').empty()
            const idler = []
              for (var i = 0; i < notifications.length; i++) {
                  const data = notifications[i].data
                  let tarih = notifications[i].timestamp
                  tarih = dateToHowManyAgo(tarih)
                  let wrapper = document.createElement('div')
                  wrapper.className = 'notifications-wrapper'
                  let not_a = document.createElement('a')
                  wrapper.appendChild(not_a)
                  not_a.className = 'bildirim notification-item'
                  not_a.href = data['hedef']
                  not_a.type = 'button'
                  if (notifications[i].yeni_mi) {
                    not_a.id = 'yenibild_' + notifications[i].id
                    not_a.className = 'yenibildirim bildirim notification-item'
                    let id = notifications[i].id
                    idler.push(notifications[i].id)
                  }
                  else {
                    not_a.id = 'bild_' + notifications[i].id
                  }
                  let baslik = document.createElement('h4')
                  not_a.appendChild(baslik)
                  baslik.className = 'bildirim-title'
                  baslik.innerHTML = data['baslik']
                  let mesaj = document.createElement('p')
                  mesaj.innerHTML = data['data']
                  mesaj.className = 'bildirim-info'
                  not_a.appendChild(mesaj)
                  let _tarih = document.createElement('span')
                  _tarih.className = 'bildtarih badge badge-info'
                  _tarih.innerText = tarih
                  not_a.appendChild(_tarih)
                  bildirim_ekle.appendChild(not_a)
              }
            dividerEkle(bildirim_ekle.id)
            if (idler.length > 0) {
              okunduIsaretle(Array.from(idler))
            }
        }
    );
  }
setTimeout(yeniBildirimler(), 1000)
var intervalID = null;

function intervalManager(flag, animate, time) {
  if(flag)
    intervalID =  setInterval(animate, time);
  else
    clearInterval(intervalID);
}
document.addEventListener("visibilitychange", event => {
    if (document.visibilityState == "visible") {
        intervalManager(true, yeniBildirimler, 20000)
    } else {
        intervalManager(false)
    }
  })
$('#bildirim-ikonu').on('hidden.bs.dropdown', function () {
  intervalManager(true, yeniBildirimler, 20000)
})

$('#bildirim-ikonu').on('shown.bs.dropdown', function () {
  bildirimleri_al()
  $('#message_count').css('display', 'none')
  intervalManager(false)
})

function hataToast() {
  let hataMsj = {'tr': 'Bir hata oluştu.', 'en': 'An error occurred.'}
  toastr.options.timeOut = 1500; // 1.5s
  toastr.options = {"positionClass": "toast-bottom-right","preventDuplicates": true}
  toastr.error(hataMsj[lang]);
}