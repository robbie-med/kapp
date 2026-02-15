const Pages = {
    practice: PracticePage,
    review: ReviewPage,
    lessons: LessonsPage,
    items: ItemsPage,
    stats: StatsPage,
    settings: SettingsPage,
    teacher: TeacherPage,
    calendar: CalendarPage,
};

const App = {
    role: 'student',
    studentId: null,
    displayName: '',
    isTeacherLogin: false,

    async init() {
        Nav.init();
        this.initLanguageToggle();

        try {
            const auth = await API.checkAuth();
            this.role = auth.role || 'student';
            this.studentId = auth.student_id || null;
            this.displayName = auth.display_name || '';
            this.showApp();
        } catch {
            this.showLogin();
        }

        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const pw = document.getElementById('login-password').value;
            const err = document.getElementById('login-error');
            err.classList.add('hidden');
            try {
                let result;
                if (this.isTeacherLogin) {
                    result = await API.teacherLogin(pw);
                } else {
                    const username = document.getElementById('login-username').value.trim();
                    if (!username) {
                        err.textContent = 'Please enter a username';
                        err.classList.remove('hidden');
                        return;
                    }
                    result = await API.login(username, pw);
                }
                this.role = result.role || 'student';
                this.studentId = result.student_id || null;
                this.displayName = result.display_name || '';
                this.showApp();
            } catch (ex) {
                err.textContent = this.isTeacherLogin ? '비밀번호가 틀렸습니다' : 'Invalid username or password';
                err.classList.remove('hidden');
            }
        });

        // Teacher login toggle
        const toggleLink = document.getElementById('teacher-login-toggle');
        if (toggleLink) {
            toggleLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.isTeacherLogin = !this.isTeacherLogin;
                const btn = document.querySelector('#login-form button[type="submit"]');
                const usernameField = document.getElementById('login-username');
                const passwordField = document.getElementById('login-password');
                if (this.isTeacherLogin) {
                    btn.textContent = '선생님 로그인';
                    passwordField.placeholder = '선생님 비밀번호';
                    usernameField.style.display = 'none';
                    usernameField.value = '';
                    toggleLink.textContent = 'Student login';
                } else {
                    btn.textContent = 'Login';
                    passwordField.placeholder = 'Password';
                    usernameField.style.display = '';
                    toggleLink.textContent = '선생님 로그인';
                }
            });
        }
    },

    showLogin() {
        this.role = 'student';
        this.studentId = null;
        this.displayName = '';
        this.isTeacherLogin = false;
        document.getElementById('login-screen').classList.add('active');
        document.getElementById('login-screen').classList.remove('hidden');
        document.getElementById('main-app').classList.add('hidden');
        // Reset login form state
        const btn = document.querySelector('#login-form button[type="submit"]');
        const usernameField = document.getElementById('login-username');
        const passwordField = document.getElementById('login-password');
        if (btn) btn.textContent = 'Login';
        if (usernameField) { usernameField.style.display = ''; usernameField.value = ''; }
        if (passwordField) passwordField.placeholder = 'Password';
        const toggleLink = document.getElementById('teacher-login-toggle');
        if (toggleLink) toggleLink.textContent = '선생님 로그인';
    },

    showApp() {
        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('main-app').classList.remove('hidden');

        // Show/hide teacher nav
        const teacherNav = document.getElementById('nav-teacher');
        const calendarNav = document.getElementById('nav-calendar');
        if (teacherNav) {
            if (this.role === 'teacher') {
                teacherNav.classList.remove('hidden');
                if (calendarNav) calendarNav.classList.remove('hidden');
            } else {
                teacherNav.classList.add('hidden');
                if (calendarNav) calendarNav.classList.add('hidden');
            }
        }

        PracticePage.load();
    },

    initLanguageToggle() {
        const toggle = document.getElementById('lang-toggle');
        if (!toggle) return;

        // Set initial text
        toggle.textContent = Translations.getLanguage() === 'ko' ? '한' : 'EN';

        // Toggle on click
        toggle.addEventListener('click', () => {
            const newLang = Translations.getLanguage() === 'en' ? 'ko' : 'en';
            Translations.setLanguage(newLang);
            toggle.textContent = newLang === 'ko' ? '한' : 'EN';

            // Reload current page to apply translations
            if (Nav.currentPage && Pages[Nav.currentPage] && Pages[Nav.currentPage].load) {
                Pages[Nav.currentPage].load();
            }
        });
    },
};

document.addEventListener('DOMContentLoaded', () => App.init());

// Register service worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}
