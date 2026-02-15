const CalendarPage = {
    currentStudent: null,
    currentWeekStart: null,
    students: [],
    assignments: [],

    async load() {
        const el = document.getElementById('page-calendar');

        // Initialize to current week
        const today = new Date();
        this.currentWeekStart = new Date(today);
        this.currentWeekStart.setDate(today.getDate() - today.getDay()); // Start of week (Sunday)

        el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';

        try {
            const studentsData = await API.getStudents();
            this.students = studentsData.students;

            if (this.students.length > 0 && !this.currentStudent) {
                this.currentStudent = this.students[0].id;
            }

            await this.renderCalendar();
        } catch (err) {
            el.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async renderCalendar() {
        const el = document.getElementById('page-calendar');

        // Get week range
        const weekEnd = new Date(this.currentWeekStart);
        weekEnd.setDate(weekEnd.getDate() + 6);

        const startDate = this.currentWeekStart.toISOString().split('T')[0];
        const endDate = weekEnd.toISOString().split('T')[0];

        // Load assignments for current student and week
        const data = await API.getAssignments(this.currentStudent, startDate, endDate);
        this.assignments = data.assignments;

        el.innerHTML = `
            <div style="margin-bottom:1rem">
                <h3>📅 Curriculum Calendar</h3>
                <p style="color:var(--text-secondary);font-size:0.9rem">Assign lessons, sentences, and vocab to students</p>
            </div>

            <div class="card" style="margin-bottom:1rem">
                <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">
                    <div style="flex:1;min-width:200px">
                        <label style="display:block;font-weight:600;margin-bottom:0.5rem">Student:</label>
                        <select id="student-select" class="input" style="width:100%">
                            ${this.students.map(s => `
                                <option value="${s.id}" ${s.id === this.currentStudent ? 'selected' : ''}>
                                    ${this._esc(s.display_name)} (${s.username})
                                </option>
                            `).join('')}
                        </select>
                    </div>
                    <div style="display:flex;gap:0.5rem;align-items:center">
                        <button class="btn btn-secondary" id="prev-week-btn">← Previous Week</button>
                        <button class="btn btn-secondary" id="today-btn">Today</button>
                        <button class="btn btn-secondary" id="next-week-btn">Next Week →</button>
                    </div>
                </div>
            </div>

            <div id="calendar-grid" style="display:grid;grid-template-columns:repeat(7,1fr);gap:0.5rem;margin-bottom:1rem">
                ${this.renderWeekDays()}
            </div>

            <div class="card">
                <h4 style="margin-bottom:0.75rem">📋 Assignments This Week</h4>
                <div id="assignments-list"></div>
            </div>
        `;

        // Event listeners
        document.getElementById('student-select').addEventListener('change', (e) => {
            this.currentStudent = parseInt(e.target.value);
            this.renderCalendar();
        });

        document.getElementById('prev-week-btn').addEventListener('click', () => {
            this.currentWeekStart.setDate(this.currentWeekStart.getDate() - 7);
            this.renderCalendar();
        });

        document.getElementById('next-week-btn').addEventListener('click', () => {
            this.currentWeekStart.setDate(this.currentWeekStart.getDate() + 7);
            this.renderCalendar();
        });

        document.getElementById('today-btn').addEventListener('click', () => {
            const today = new Date();
            this.currentWeekStart = new Date(today);
            this.currentWeekStart.setDate(today.getDate() - today.getDay());
            this.renderCalendar();
        });

        this.renderAssignmentsList();
    },

    renderWeekDays() {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const today = new Date().toDateString();

        let html = '';
        for (let i = 0; i < 7; i++) {
            const date = new Date(this.currentWeekStart);
            date.setDate(date.getDate() + i);
            const dateStr = date.toDateString();
            const isToday = dateStr === today;
            const isPast = date < new Date(today);

            // Count assignments for this day
            const dayAssignments = this.assignments.filter(a => {
                return a.due_date === date.toISOString().split('T')[0];
            });

            html += `
                <div class="card" style="padding:0.75rem;cursor:pointer;border:2px solid ${isToday ? 'var(--primary)' : 'var(--border)'};
                     ${isPast ? 'opacity:0.6;' : ''}"
                     onclick="CalendarPage.addAssignment('${date.toISOString().split('T')[0]}')">
                    <div style="font-weight:600;font-size:0.75rem;color:var(--text-secondary);margin-bottom:0.25rem">
                        ${days[i]}
                    </div>
                    <div style="font-size:1.25rem;font-weight:600;margin-bottom:0.5rem">
                        ${date.getDate()}
                    </div>
                    ${dayAssignments.length > 0 ? `
                        <div style="background:var(--primary);color:white;font-size:0.7rem;padding:0.25rem;border-radius:4px;text-align:center">
                            ${dayAssignments.length} assignment${dayAssignments.length > 1 ? 's' : ''}
                        </div>
                    ` : '<div style="font-size:0.7rem;color:var(--text-secondary)">No assignments</div>'}
                </div>
            `;
        }
        return html;
    },

    renderAssignmentsList() {
        const container = document.getElementById('assignments-list');

        if (this.assignments.length === 0) {
            container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">No assignments this week</p>';
            return;
        }

        const typeIcons = { lesson: '📚', sentence: '💬', vocab: '📗' };
        const typeLabels = { lesson: 'Lesson', sentence: 'Sentence', vocab: 'Vocabulary' };

        container.innerHTML = this.assignments.map(a => {
            const dueDate = new Date(a.due_date);
            const isOverdue = !a.completed_at && dueDate < new Date();
            const isCompleted = !!a.completed_at;

            let title = '';
            if (a.assignment_type === 'lesson') {
                title = `Lesson ${a.lesson_number}: ${a.lesson_title}`;
            } else if (a.assignment_type === 'sentence') {
                title = a.sentence_korean;
            } else if (a.assignment_type === 'vocab') {
                title = `${a.item_korean} (${a.item_english})`;
            }

            return `
                <div style="padding:0.75rem;border-left:3px solid ${isCompleted ? 'var(--success)' : (isOverdue ? 'var(--error)' : 'var(--primary)')};
                     background:#f9fafb;margin-bottom:0.5rem;border-radius:4px">
                    <div style="display:flex;justify-content:space-between;align-items:start">
                        <div style="flex:1">
                            <div style="font-weight:600;margin-bottom:0.25rem">
                                ${typeIcons[a.assignment_type]} ${this._esc(title)}
                                ${isCompleted ? '<span style="color:var(--success);font-size:0.9rem">✓ Complete</span>' : ''}
                            </div>
                            <div style="font-size:0.75rem;color:var(--text-secondary)">
                                ${typeLabels[a.assignment_type]} • Due: ${dueDate.toLocaleDateString()}
                                ${isOverdue ? '<span style="color:var(--error);font-weight:600"> (Overdue)</span>' : ''}
                            </div>
                            ${a.notes ? `<div style="font-size:0.8rem;margin-top:0.5rem;color:var(--text-secondary)">${this._esc(a.notes)}</div>` : ''}
                        </div>
                        <button class="btn btn-secondary" style="padding:4px 8px;font-size:0.8rem"
                                onclick="CalendarPage.deleteAssignment(${a.id})">Delete</button>
                    </div>
                </div>
            `;
        }).join('');
    },

    async addAssignment(dueDate) {
        const studentName = this.students.find(s => s.id === this.currentStudent)?.display_name || 'Student';

        const content = document.getElementById('page-calendar');
        const modal = document.createElement('div');
        modal.id = 'assignment-modal';
        modal.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:1000';

        modal.innerHTML = `
            <div class="card" style="width:90%;max-width:500px;max-height:80vh;overflow-y:auto">
                <h4 style="margin-bottom:1rem">Add Assignment for ${this._esc(studentName)}</h4>
                <p style="font-size:0.9rem;color:var(--text-secondary);margin-bottom:1rem">Due: ${new Date(dueDate).toLocaleDateString()}</p>

                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:600;margin-bottom:0.5rem">Assignment Type:</label>
                    <select id="assignment-type" class="input" style="width:100%">
                        <option value="lesson">📚 Lesson</option>
                        <option value="sentence">💬 Sentence</option>
                        <option value="vocab">📗 Vocabulary</option>
                    </select>
                </div>

                <div id="assignment-selector"></div>

                <div style="margin-bottom:1rem">
                    <label style="display:block;font-weight:600;margin-bottom:0.5rem">Notes (optional):</label>
                    <textarea id="assignment-notes" class="input" rows="3" style="width:100%"></textarea>
                </div>

                <div style="display:flex;gap:0.5rem">
                    <button class="btn btn-secondary btn-block" onclick="CalendarPage.closeModal()">Cancel</button>
                    <button class="btn btn-primary btn-block" id="save-assignment-btn">Save Assignment</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Load lesson selector by default
        await this.renderAssignmentSelector('lesson');

        document.getElementById('assignment-type').addEventListener('change', async (e) => {
            await this.renderAssignmentSelector(e.target.value);
        });

        document.getElementById('save-assignment-btn').addEventListener('click', async () => {
            const type = document.getElementById('assignment-type').value;
            const selector = document.getElementById('assignment-selector-value');
            const notes = document.getElementById('assignment-notes').value;

            if (!selector || !selector.value) {
                alert('Please select an item to assign');
                return;
            }

            const assignmentData = {
                student_id: this.currentStudent,
                assignment_type: type,
                due_date: dueDate,
                notes: notes,
            };

            if (type === 'lesson') {
                assignmentData.lesson_id = parseInt(selector.value);
            } else if (type === 'sentence') {
                assignmentData.sentence_id = parseInt(selector.value);
            } else if (type === 'vocab') {
                assignmentData.item_id = parseInt(selector.value);
            }

            try {
                await API.createAssignment(assignmentData);
                this.closeModal();
                await this.renderCalendar();
            } catch (err) {
                alert('Failed to create assignment: ' + err.message);
            }
        });
    },

    async renderAssignmentSelector(type) {
        const container = document.getElementById('assignment-selector');
        container.innerHTML = '<div class="loading">Loading options...</div>';

        try {
            let html = '<label style="display:block;font-weight:600;margin-bottom:0.5rem">Select Item:</label>';
            html += '<select id="assignment-selector-value" class="input" style="width:100%">';

            if (type === 'lesson') {
                const unitsData = await API.getUnits();
                for (const unit of unitsData.units) {
                    const lessonsData = await API.getLessons(unit.id);
                    html += `<optgroup label="Unit ${unit.unit_number}: ${unit.title}">`;
                    for (const lesson of lessonsData.lessons) {
                        html += `<option value="${lesson.id}">Lesson ${lesson.lesson_number}: ${lesson.title}</option>`;
                    }
                    html += '</optgroup>';
                }
            } else if (type === 'sentence') {
                const sentencesData = await API.getSentences({limit: 50});
                for (const sentence of sentencesData.sentences) {
                    html += `<option value="${sentence.id}">${sentence.korean} (${sentence.english})</option>`;
                }
            } else if (type === 'vocab') {
                const itemsData = await API.getItems({limit: 100});
                for (const item of itemsData.items) {
                    html += `<option value="${item.id}">${item.korean} (${item.english})</option>`;
                }
            }

            html += '</select>';
            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<p class="error">${err.message}</p>`;
        }
    },

    async deleteAssignment(assignmentId) {
        if (!confirm('Delete this assignment?')) return;

        try {
            await API.deleteAssignment(assignmentId);
            await this.renderCalendar();
        } catch (err) {
            alert('Failed to delete: ' + err.message);
        }
    },

    closeModal() {
        const modal = document.getElementById('assignment-modal');
        if (modal) modal.remove();
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },
};
