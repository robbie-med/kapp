const API = {
    async request(method, path, body, isFormData = false) {
        const opts = {
            method,
            credentials: 'same-origin',
        };
        if (body && !isFormData) {
            opts.headers = { 'Content-Type': 'application/json' };
            opts.body = JSON.stringify(body);
        } else if (body && isFormData) {
            opts.body = body;
        }
        const res = await fetch(path, opts);
        if (res.status === 401) {
            App.showLogin();
            throw new Error('Unauthorized');
        }
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.detail || 'Request failed');
        return data;
    },

    get(path) { return this.request('GET', path); },
    post(path, body) { return this.request('POST', path, body); },
    put(path, body) { return this.request('PUT', path, body); },
    del(path) { return this.request('DELETE', path); },
    postForm(path, formData) { return this.request('POST', path, formData, true); },

    login(username, password) { return this.post('/api/login', { username, password }); },
    teacherLogin(password) { return this.post('/api/login/teacher', { password }); },
    logout() { return this.post('/api/logout'); },
    checkAuth() { return this.get('/api/auth/check'); },

    getStudents() { return this.get('/api/students'); },
    createStudent(data) { return this.post('/api/students', data); },
    deleteStudent(id) { return this.del(`/api/students/${id}`); },

    startPractice(opts) { return this.post('/api/practice/start', opts); },
    submitPractice(formData) { return this.postForm('/api/practice/submit', formData); },

    getItems(params) {
        const qs = new URLSearchParams(params).toString();
        return this.get(`/api/items?${qs}`);
    },
    getItem(id) { return this.get(`/api/items/${id}`); },
    createItem(item) { return this.post('/api/items', item); },
    updateItem(id, data) { return this.put(`/api/items/${id}`, data); },
    deleteItem(id) { return this.del(`/api/items/${id}`); },
    addExample(itemId, example) { return this.post(`/api/items/${itemId}/examples`, example); },
    deleteExample(itemId, exampleId) { return this.del(`/api/items/${itemId}/examples/${exampleId}`); },
    findDuplicates() { return this.get('/api/items/duplicates/find'); },
    mergeItems(keepId, removeId) { return this.post(`/api/items/${keepId}/merge/${removeId}`); },

    getSentences(params) {
        const qs = new URLSearchParams(params).toString();
        return this.get(`/api/sentences?${qs}`);
    },
    getSentence(id) { return this.get(`/api/sentences/${id}`); },
    createSentence(data) { return this.post('/api/sentences', data); },
    deleteSentence(id) { return this.del(`/api/sentences/${id}`); },
    getSentenceBreakdown(id) { return this.get(`/api/sentences/${id}/breakdown`); },
    linkSentenceItem(sentenceId, itemId) { return this.post(`/api/sentences/${sentenceId}/link/${itemId}`); },
    unlinkSentenceItem(sentenceId, itemId) { return this.del(`/api/sentences/${sentenceId}/link/${itemId}`); },

    getLevelHistory() { return this.get('/api/stats/level-history'); },
    getEncounters() { return this.get('/api/stats/encounters'); },
    getActivity(days) { return this.get(`/api/stats/activity?days=${days || 30}`); },
    getMasteryByLevel() { return this.get('/api/stats/mastery-by-level'); },
    getVocabGrowth(days) { return this.get(`/api/stats/vocab-growth?days=${days || 90}`); },
    getTeacherOverview() { return this.get('/api/stats/teacher/overview'); },

    getReviewQueue() { return this.get('/api/review/queue'); },
    getHistory(limit) { return this.get(`/api/review/history?limit=${limit || 20}`); },
    getSessionDetail(id) { return this.get(`/api/review/history/${id}`); },

    getStats() { return this.get('/api/stats'); },

    getSettings() { return this.get('/api/settings'); },
    updateSetting(key, value) { return this.put(`/api/settings/${key}`, { value }); },

    // Goals
    getGoals(activeOnly = true) { return this.get(`/api/goals?active_only=${activeOnly}`); },
    createGoal(data) { return this.post('/api/goals', data); },
    deleteGoal(id) { return this.del(`/api/goals/${id}`); },

    // Reading practice
    completeReading(data) { return this.post('/api/practice/reading/complete', data); },

    // Weakness tracking
    getWeaknesses(limit = 20) { return this.get(`/api/stats/weaknesses?limit=${limit}`); },
    getItemTimeline(itemId, days = 30) { return this.get(`/api/stats/item-timeline/${itemId}?days=${days}`); },
    getErrorPatterns(limit = 20) { return this.get(`/api/stats/error-patterns?limit=${limit}`); },

    // Curriculum
    getUnits() { return this.get('/api/curriculum/units'); },
    getLessons(unitId) { return this.get(`/api/curriculum/units/${unitId}/lessons`); },
    getLesson(lessonId) { return this.get(`/api/curriculum/lessons/${lessonId}`); },

    // Calendar/Assignments
    getAssignments(studentId = null, startDate = null, endDate = null) {
        const params = new URLSearchParams();
        if (studentId) params.append('student_id', studentId);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        return this.get(`/api/calendar/assignments?${params}`);
    },
    createAssignment(data) { return this.post('/api/calendar/assignments', data); },
    updateAssignment(id, data) { return this.put(`/api/calendar/assignments/${id}`, data); },
    deleteAssignment(id) { return this.del(`/api/calendar/assignments/${id}`); },
    getStudentUpcoming(studentId) { return this.get(`/api/calendar/student/${studentId}/upcoming`); },
    completeAssignment(id) { return this.post(`/api/calendar/assignments/${id}/complete`); },
};
