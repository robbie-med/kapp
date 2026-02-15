const Nav = {
    init() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = btn.dataset.page;
                this.navigate(page);
            });
        });
    },

    navigate(page) {
        // Update nav buttons
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        const activeBtn = document.querySelector(`.nav-btn[data-page="${page}"]`);
        if (activeBtn) activeBtn.classList.add('active');

        // Update pages
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const activePage = document.getElementById(`page-${page}`);
        if (activePage) activePage.classList.add('active');

        // Update header
        const titles = { practice: 'Practice', review: 'Review Queue', items: 'Items', stats: 'Stats', settings: 'Settings', teacher: '항목 관리' };
        document.getElementById('page-title').textContent = titles[page] || page;

        // Trigger page load
        if (typeof Pages !== 'undefined' && Pages[page] && Pages[page].load) {
            Pages[page].load();
        }
    },
};
