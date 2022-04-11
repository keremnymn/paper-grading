$(document).ready(async function(){
    let gosterim = document.getElementById('gosterim')
    await $.ajax({
      url: "/landing_veriler",
      type: 'GET',
      success: function(data) {
        var veriler = document.getElementsByClassName('veriler')
        for(var i = 0; i < data.length; i++) {
          veriler[i].innerHTML = data[i]
        }
      }
    })
  })
  $('.testi1').owlCarousel({
  loop: true,
  margin: 30,
  nav: false,
  dots: true,
  autoplay: true,
  responsiveClass: true,
  responsive: {
    0: {
      items: 1,
      nav: false
    },
    1024: {
      items: 2
    }
  }
});
AOS.init({once: true, disable:'mobile'});
// jQuery counterUp
$('[data-toggle="counter-up"]').counterUp({
  delay: 10,
  time: 1000
});