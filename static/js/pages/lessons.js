const LessonsPage = {
    currentUnit: null,
    currentLesson: null,

    async load() {
        const el = document.getElementById('page-lessons');
        el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading lessons...</div>';

        try {
            const data = await API.getUnits();
            this.renderUnits(data.units);
        } catch (err) {
            el.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    renderUnits(units) {
        const el = document.getElementById('page-lessons');
        el.innerHTML = `
            <div style="margin-bottom:1rem">
                <h3>📚 Curriculum</h3>
                <p style="color:var(--text-secondary);font-size:0.9rem">Browse lessons from <a href="https://www.howtostudykorean.com" target="_blank" style="color:var(--primary)">HowToStudyKorean.com</a></p>
            </div>
            <div id="units-container"></div>`;

        const container = document.getElementById('units-container');
        container.innerHTML = units.map(u => `
            <div class="card" style="margin-bottom:0.75rem;cursor:pointer;transition:all 0.2s"
                 onmouseenter="this.style.borderColor='var(--primary)'"
                 onmouseleave="this.style.borderColor='var(--border)'"
                 onclick="LessonsPage.loadUnit(${u.id})">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <div style="flex:1">
                        <div style="font-weight:600;font-size:1.1rem;margin-bottom:0.25rem">
                            Unit ${u.unit_number}: ${this._esc(u.title)}
                        </div>
                        <div style="font-size:0.85rem;color:var(--text-secondary)">
                            ${this._esc(u.description)}
                        </div>
                        <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.5rem">
                            📖 ${u.lesson_count} lessons • 🎯 TOPIK ${u.topik_level}
                        </div>
                    </div>
                    <div style="font-size:1.5rem;color:var(--primary)">→</div>
                </div>
            </div>
        `).join('');
    },

    async loadUnit(unitId) {
        this.currentUnit = unitId;
        const el = document.getElementById('page-lessons');
        el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading unit...</div>';

        try {
            const data = await API.getLessons(unitId);
            this.renderLessons(data.unit, data.lessons);
        } catch (err) {
            el.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    renderLessons(unit, lessons) {
        const el = document.getElementById('page-lessons');
        el.innerHTML = `
            <div style="margin-bottom:1rem">
                <button class="btn btn-secondary" onclick="LessonsPage.load()" style="margin-bottom:0.5rem">
                    ← Back to Units
                </button>
                <h3>Unit ${unit.unit_number}: ${this._esc(unit.title)}</h3>
            </div>
            <div id="lessons-container"></div>`;

        const container = document.getElementById('lessons-container');
        container.innerHTML = lessons.map(l => {
            const statusColors = {
                available: '#3b82f6',
                in_progress: '#f59e0b',
                completed: '#10b981'
            };
            const statusIcons = {
                available: '📘',
                in_progress: '📖',
                completed: '✅'
            };
            const statusLabels = {
                available: 'Available',
                in_progress: 'In Progress',
                completed: 'Completed'
            };

            return `
                <div class="card" style="margin-bottom:0.75rem;cursor:pointer;transition:all 0.2s"
                     onmouseenter="this.style.borderColor='var(--primary)'"
                     onmouseleave="this.style.borderColor='var(--border)'"
                     onclick="LessonsPage.loadLesson(${l.id})">
                    <div style="display:flex;justify-content:space-between;align-items:start">
                        <div style="flex:1">
                            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem">
                                <span style="font-size:1.2rem">${statusIcons[l.status]}</span>
                                <div>
                                    <div style="font-weight:600">Lesson ${l.lesson_number}: ${this._esc(l.title)}</div>
                                    <div style="font-size:0.75rem;color:var(--text-secondary)">
                                        ${l.item_count} items •
                                        ${l.practice_count > 0 ? `Practiced ${l.practice_count}x` : 'Not practiced yet'}
                                    </div>
                                </div>
                            </div>
                            ${l.mastery_score > 0 ? `
                                <div style="margin-top:0.5rem">
                                    <div style="display:flex;justify-content:space-between;font-size:0.75rem;margin-bottom:0.25rem">
                                        <span>Mastery</span>
                                        <span style="font-weight:600">${Math.round(l.mastery_score * 100)}%</span>
                                    </div>
                                    <div style="height:6px;background:#E0E6ED;border-radius:3px;overflow:hidden">
                                        <div style="height:100%;background:${statusColors[l.status]};width:${l.mastery_score * 100}%"></div>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        <div style="font-size:1.5rem;color:var(--primary);margin-left:1rem">→</div>
                    </div>
                </div>
            `;
        }).join('');
    },

    async loadLesson(lessonId) {
        this.currentLesson = lessonId;
        const el = document.getElementById('page-lessons');
        el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading lesson...</div>';

        try {
            const data = await API.getLesson(lessonId);
            this.renderLessonDetail(data.lesson);
        } catch (err) {
            el.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    renderLessonDetail(lesson) {
        const el = document.getElementById('page-lessons');
        const masteryPct = Math.round((lesson.mastery_score || 0) * 100);

        el.innerHTML = `
            <div style="margin-bottom:1rem">
                <button class="btn btn-secondary" onclick="LessonsPage.loadUnit(${this.currentUnit})" style="margin-bottom:0.5rem">
                    ← Back to Unit ${lesson.unit_number}
                </button>
                <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:1rem">
                    <div>
                        <h3>Lesson ${lesson.lesson_number}: ${this._esc(lesson.title)}</h3>
                        <p style="color:var(--text-secondary);font-size:0.9rem">
                            Unit ${lesson.unit_number}: ${this._esc(lesson.unit_title)}
                        </p>
                    </div>
                    ${lesson.url ? `
                        <a href="${lesson.url}" target="_blank" class="btn btn-secondary" style="padding:8px 16px">
                            📖 View on Website
                        </a>
                    ` : ''}
                </div>

                ${lesson.practice_count > 0 ? `
                    <div class="card" style="margin-bottom:1rem;background:#f0f9ff">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <div style="font-weight:600;margin-bottom:0.25rem">Your Progress</div>
                                <div style="font-size:0.85rem;color:var(--text-secondary)">
                                    Practiced ${lesson.practice_count} time${lesson.practice_count > 1 ? 's' : ''} •
                                    ${masteryPct}% mastery
                                </div>
                            </div>
                            <div style="font-size:2rem">${masteryPct >= 70 ? '⭐' : masteryPct >= 50 ? '📈' : '📚'}</div>
                        </div>
                        <div style="height:8px;background:#E0E6ED;border-radius:4px;overflow:hidden;margin-top:0.75rem">
                            <div style="height:100%;background:var(--success);width:${masteryPct}%"></div>
                        </div>
                    </div>
                ` : ''}

                <button class="btn btn-primary btn-block" onclick="PracticePage.startLessonPractice(${lesson.id})" style="margin-bottom:1rem">
                    🎯 Practice This Lesson
                </button>
            </div>

            <div class="card">
                <h4 style="margin-bottom:0.75rem">📝 Items in This Lesson (${lesson.items.length})</h4>
                <div id="lesson-items-container"></div>
            </div>`;

        const itemsContainer = document.getElementById('lesson-items-container');
        if (lesson.items.length === 0) {
            itemsContainer.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">No items linked yet.</p>';
        } else {
            const typeIcons = { vocab: '📗', grammar: '📘' };
            itemsContainer.innerHTML = lesson.items.map(item => {
                const practiced = item.practice_count > 0;
                const mastery = Math.round((item.mastery_score || 0) * 100);

                return `
                    <div style="padding:0.5rem;border-left:3px solid ${practiced ? 'var(--success)' : '#E0E6ED'};background:#f9fafb;margin-bottom:0.5rem;border-radius:4px">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div style="flex:1">
                                <div style="font-weight:600;margin-bottom:0.25rem">
                                    ${typeIcons[item.item_type]} ${this._esc(item.korean)}
                                    <span style="color:var(--text-secondary);font-weight:normal;font-size:0.9rem">
                                        (${this._esc(item.english)})
                                    </span>
                                </div>
                                <div style="font-size:0.75rem;color:var(--text-secondary)">
                                    ${item.item_type === 'vocab' ? 'Vocabulary' : 'Grammar'} •
                                    TOPIK ${item.topik_level}
                                    ${practiced ? `• Practiced ${item.practice_count}x` : '• Not practiced yet'}
                                </div>
                            </div>
                            ${practiced ? `
                                <div style="text-align:right;margin-left:1rem">
                                    <div style="font-weight:600;color:${mastery >= 70 ? 'var(--success)' : (mastery >= 50 ? 'var(--warning)' : 'var(--error)')}">${mastery}%</div>
                                    <div style="font-size:0.7rem;color:var(--text-secondary)">mastery</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }).join('');
        }
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },
};
