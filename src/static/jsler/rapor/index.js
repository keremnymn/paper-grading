$(document).ready(function () {
    document.getElementById('panel-btn').className = 'nav-link active'
    let ort = {'tr': 'Sınav Ortalaması', 'en': 'Exam Average'}
    $.ajax({
        url: "/rapor/panel_genel",
        dataType: "text",
        type: 'GET',
        success: (bilgiler) => {
            let _bilgiler = JSON.parse(bilgiler)
            let tarih = []
            let ortalamalar = []
            for(i=0; i < _bilgiler.length; i++) {
                tarih.push(_bilgiler[i]['tarih'])
                ortalamalar.push(_bilgiler[i]['ortalama'])
            }
            var ctx = document.getElementById('myAreaChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels:tarih,
                    datasets: [{
                        label: ort[lang],
                        data: ortalamalar,
                        fill: true,
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
})