const sidebarCollapseButton = document.createElement('button')
sidebarCollapseButton.id = 'sidebarCollapse'
sidebarCollapseButton.type = "button"
sidebarCollapseButton.className = "btn"

const sidebarSpan = document.createElement('span')
sidebarSpan.className = "navbar-toggler-icon"

sidebarCollapseButton.appendChild(sidebarSpan)
let ekle = document.getElementById("sidebar-button-ekle")
let logo = document.getElementById("logo-a")
ekle.insertBefore(sidebarCollapseButton, logo)

$('#sidebarCollapse').on('click', function () {
    $('.idocs-navigation').toggleClass('active');
  });