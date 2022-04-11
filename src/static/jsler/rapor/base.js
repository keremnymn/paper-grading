let translations = {
    'renewReport': {'tr': ' Raporu yenile', 'en': ' Renew The Report'},
    'raporCikti': {'tr': 'Rapor Çıktısı', 'en': 'Export The Report'},
    'aciklama1': {
        'tr': 'Aşağıdaki düğmeye tıklayarak bu öğrenci için özel oluşturulmuş PDF raporunu elde edebilirsiniz.',
        'en': "You can get the PDF report generated for this student clicking the button below."
    },
    'aciklama2': {
        'tr': 'Rapor çıktısı almadan önce <span class="vurgu">tüm soruları kontrol etmeniz</span> önerilmektedir.',
        'en': "Before exporting the report, make sure that you've checked every question."
    },
    'imSure': {
        'tr': 'Tüm soruların doğruluğundan eminim.',
        'en': "I've checked every question."
    },
    'reqRep': {'tr': 'Rapor İste', 'en': 'Request A Report'},
    'repHazirlaniyor': {'tr': 'Rapor Hazırlanıyor', 'en': 'In Process'},
    'repBildir': {'tr': 'Rapor hazır olduğunda size bildireceğiz.', 'en': "We'll notify you when the report is ready."},
    'yanitUyari': {'tr': "Lütfen geçerli bir yanıt giriniz.", 'en': 'Please enter a valid answer.'},
    'dy': {'tr': 'Doğru Yanlış', 'en': 'True False'},
    'sinifOrtalama': {'tr': 'Sıfının Ortalama Başarısı', 'en': 'Average Success of the Class'},
    'ogrenciBasari': {'tr': 'Öğrenci Başarısı', 'en': 'Student Success'},
    'true': {'en': 'Correct ✓', 'tr': 'Doğru ✓'},
    'false': {'en': 'False X', 'tr': 'Yanlış X'},
    'soru': {'en': 'Q', 'tr': 'Soru '},
    'qTypes': {
        'tr': {
            'Çoktan Seçmeli': 'Çoktan Seçmeli',
            'Boşluk Doldurma': 'Boşluk Doldurma',
            'Doğru Yanlış': 'Doğru Yanlış',
            'Eşleştirme': 'Eşleştirme'
        },
        'en': {
            'Çoktan Seçmeli': 'Multiple Choice',
            'Boşluk Doldurma': 'Gap Filling',
            'Doğru Yanlış': 'True False',
            'Eşleştirme': 'Matching'
        }
    }
}

function spanSwitch(e) {
    let txt = e.innerText;
    if (e.childNodes[0].tagName == 'DIV' || txt == '✓') {
        //pass
    }
    else if (e.parentElement.tagName == 'SPAN') {
        $(e).parents()[1] = `<div class="input-group mb-3"><input autofocus class="form-control form-control-inline" onfocusout="vazgec(this)" onceki='${e.innerText}' value='${txt}'/> <div class="input-group-append"><span class="input-group-text" onmousedown='spanReset(this)'>✓</span></div></div>`; 
    }
    else {
        e.innerHTML = `<div class="input-group mb-3"><input autofocus class="form-control form-control-inline" onfocusout="vazgec(this)" onceki='${e.innerText}' value='${txt}'/> <div class="input-group-append"><span class="input-group-text" onmousedown='spanReset(this)'>✓</span></div></div>`; 
        e.childNodes[0].childNodes[0].focus();
    }
  }

  function vazgec(e) {
      setTimeout(() => {
        let onceki = e.getAttribute('onceki')
        let _td = $(e).parents()[2]
        _td.innerHTML = '<span onclick="spanSwitch(this)">' + onceki + '</span>'
      }, 100)
  }

  let yanitDegisFunc = () => void 0;

  function spanReset(e) {
    let div_grp = $(e).parents()[1]
    let onceki = div_grp.childNodes[0].getAttribute('onceki')
    let txt = div_grp.childNodes[0].value
    let soru_id = $(e).parents()[4].childNodes[0].getAttribute('id')
    let tip = $(e).parents()[4].childNodes[1].innerText
    if (txt != onceki && ! (txt.length > 0 && txt.length < 200) ) {
        toastr.options.timeOut = 1500; // 1.5s
        toastr.options = {
        "positionClass": "toast-bottom-right",
        "preventDuplicates": true
        }
        toastr.error(translations['yanitUyari'][lang]);
        let _td = $(e).parents()[3]
        _td.innerHTML = '<span onclick="spanSwitch(this)">' + onceki + '</span>'
    }
    else if (txt == onceki) {
        let _td = $(e).parents()[3]
        _td.innerHTML = '<span onclick="spanSwitch(this)">' + onceki + '</span>'
    }
    else {
        txt = txt.trim().toLowerCase();
        if (tip == translations['dy'][lang]) {
            txt = txt.replace('ş', 's')
            txt = txt.replace('ı', 'i')
            txt = txt.replace('ğ', 'g')
        }
        yanitDegisFunc(soru_id, txt, e)
    }
}