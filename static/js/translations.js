const Translations = {
    currentLang: localStorage.getItem('lang') || 'en',

    strings: {
        en: {
            // Navigation
            practice: 'Practice',
            review: 'Review',
            lessons: 'Lessons',
            items: 'Items',
            stats: 'Stats',
            settings: 'Settings',
            teacher: '관리',
            calendar: '일정',

            // Common
            loading: 'Loading...',
            error: 'Error',
            save: 'Save',
            cancel: 'Cancel',
            delete: 'Delete',
            edit: 'Edit',
            add: 'Add',
            back: 'Back',
            next: 'Next',
            previous: 'Previous',
            close: 'Close',
            search: 'Search',
            filter: 'Filter',

            // Teacher Calendar
            calendar_title: 'Curriculum Calendar',
            calendar_desc: 'Assign lessons, sentences, and vocab to students',
            student: 'Student',
            prev_week: 'Previous Week',
            next_week: 'Next Week',
            today: 'Today',
            assignments_this_week: 'Assignments This Week',
            no_assignments: 'No assignments',
            add_assignment: 'Add Assignment',
            assignment_type: 'Assignment Type',
            lesson: 'Lesson',
            sentence: 'Sentence',
            vocabulary: 'Vocabulary',
            due_date: 'Due Date',
            notes: 'Notes',
            optional: 'optional',
            save_assignment: 'Save Assignment',
            delete_assignment: 'Delete this assignment?',
            overdue: 'Overdue',
            completed: 'Complete',
            no_assignments_week: 'No assignments this week',

            // Teacher Interface
            teacher_dashboard: 'Teacher Dashboard',
            manage_items: 'Manage Items',
            manage_sentences: 'Manage Sentences',
            student_progress: 'Student Progress',
            create_student: 'Create Student',
            username: 'Username',
            display_name: 'Display Name',
            password: 'Password',
            korean: 'Korean',
            english: 'English',
            item_type: 'Type',
            topik_level: 'TOPIK Level',
            tags: 'Tags',
            examples: 'Examples',
            add_item: 'Add Item',
            add_sentence: 'Add Sentence',
            add_example: 'Add Example',
            formality: 'Formality',
            polite: 'Polite (해요체)',
            formal: 'Formal (합쇼체)',
            casual: 'Casual (해체)',
            vocab: 'Vocabulary',
            grammar: 'Grammar',

            // Settings
            language: 'Language',
            language_toggle: 'Language',
            korean_lang: '한국어',
            english_lang: 'English',
        },
        ko: {
            // Navigation
            practice: '연습',
            review: '복습',
            lessons: '수업',
            items: '항목',
            stats: '통계',
            settings: '설정',
            teacher: '관리',
            calendar: '일정',

            // Common
            loading: '로딩 중...',
            error: '오류',
            save: '저장',
            cancel: '취소',
            delete: '삭제',
            edit: '편집',
            add: '추가',
            back: '뒤로',
            next: '다음',
            previous: '이전',
            close: '닫기',
            search: '검색',
            filter: '필터',

            // Teacher Calendar
            calendar_title: '커리큘럼 일정',
            calendar_desc: '학생에게 수업, 문장, 단어 배정',
            student: '학생',
            prev_week: '이전 주',
            next_week: '다음 주',
            today: '오늘',
            assignments_this_week: '이번 주 과제',
            no_assignments: '과제 없음',
            add_assignment: '과제 추가',
            assignment_type: '과제 유형',
            lesson: '수업',
            sentence: '문장',
            vocabulary: '어휘',
            due_date: '마감일',
            notes: '메모',
            optional: '선택사항',
            save_assignment: '과제 저장',
            delete_assignment: '이 과제를 삭제하시겠습니까?',
            overdue: '지연',
            completed: '완료',
            no_assignments_week: '이번 주 과제가 없습니다',

            // Teacher Interface
            teacher_dashboard: '선생님 대시보드',
            manage_items: '항목 관리',
            manage_sentences: '문장 관리',
            student_progress: '학생 진도',
            create_student: '학생 생성',
            username: '사용자명',
            display_name: '표시 이름',
            password: '비밀번호',
            korean: '한국어',
            english: '영어',
            item_type: '유형',
            topik_level: 'TOPIK 레벨',
            tags: '태그',
            examples: '예시',
            add_item: '항목 추가',
            add_sentence: '문장 추가',
            add_example: '예시 추가',
            formality: '형식',
            polite: '해요체',
            formal: '합쇼체',
            casual: '해체',
            vocab: '어휘',
            grammar: '문법',

            // Settings
            language: '언어',
            language_toggle: '언어',
            korean_lang: '한국어',
            english_lang: 'English',
        }
    },

    t(key) {
        return this.strings[this.currentLang][key] || this.strings['en'][key] || key;
    },

    setLanguage(lang) {
        if (lang !== 'en' && lang !== 'ko') return;
        this.currentLang = lang;
        localStorage.setItem('lang', lang);

        // Trigger a custom event so pages can re-render
        window.dispatchEvent(new CustomEvent('languageChanged', {detail: {lang}}));
    },

    getLanguage() {
        return this.currentLang;
    }
};

// Short alias
const t = (key) => Translations.t(key);
