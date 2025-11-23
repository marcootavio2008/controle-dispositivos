document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.querySelector('.menu-toggle');
    const closeBtn = document.querySelector('.close-btn');
    const sidebarMenu = document.querySelector('.sidebar-menu');

    if (menuToggle && closeBtn && sidebarMenu) {
        menuToggle.addEventListener('click', () => {
            sidebarMenu.classList.add('open');
        });

        closeBtn.addEventListener('click', () => {
            sidebarMenu.classList.remove('open');
        });

        document.addEventListener('click', (event) => {
            if (!sidebarMenu.contains(event.target) && !menuToggle.contains(event.target)) {
                sidebarMenu.classList.remove('open');
            }
        });
    }
});

