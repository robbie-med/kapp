const PracticePage = {
    session: null,
    recording: false,
    sessionStartTime: null,
    currentMode: 'speaking',

    load() {
        const el = document.getElementById('page-practice');
        if (this.session) return; // Don't reload if session active
        el.innerHTML = `
            <div class="mode-selector">
                <button class="mode-btn active" data-mode="speaking">Speaking</button>
                <button class="mode-btn" data-mode="reading">Reading</button>
            </div>
            <div class="formality-selector">
                <button class="formality-btn active" data-f="polite">해요체<br><small>Polite</small></button>
                <button class="formality-btn" data-f="formal">합쇼체<br><small>Formal</small></button>
                <button class="formality-btn" data-f="casual">해체<br><small>Casual</small></button>
            </div>
            <div style="text-align:center">
                <button class="btn btn-primary btn-block" id="start-practice-btn">Start Practice</button>
            </div>
            <div id="practice-content"></div>`;

        el.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                el.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentMode = btn.dataset.mode;
            });
        });

        el.querySelectorAll('.formality-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                el.querySelectorAll('.formality-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
        document.getElementById('start-practice-btn').addEventListener('click', () => this.startSession());
    },

    async startSession() {
        const formality = document.querySelector('.formality-btn.active')?.dataset.f || 'polite';
        const content = document.getElementById('practice-content');
        content.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';
        document.getElementById('start-practice-btn').classList.add('hidden');

        try {
            this.sessionStartTime = new Date().toISOString();
            if (this.currentMode === 'reading') {
                this.session = await API.startPractice({ formality, item_count: 5, mode: 'reading' });
                this.currentCardIndex = 0;
                this.renderReadingCard();
            } else {
                // Speaking mode
                this.session = await API.startPractice({ formality, item_count: 3, mode: 'speaking' });
                this.renderPrompt();
            }
        } catch (err) {
            content.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
            document.getElementById('start-practice-btn').classList.remove('hidden');
        }
    },

    renderPrompt() {
        const s = this.session;
        const content = document.getElementById('practice-content');
        content.innerHTML = `
            <div class="prompt-card">
                <div class="prompt-korean">${this._esc(s.prompt)}</div>
                <div class="prompt-english">${this._esc(s.prompt_english)}</div>
            </div>
            <div class="target-items">
                ${s.target_items.map(i => `<span class="target-chip">${this._esc(i.korean)} (${this._esc(i.english)})</span>`).join('')}
            </div>
            <div class="record-area">
                <button class="record-btn" id="record-btn">🎤</button>
                <div class="record-label" id="record-label">Tap to record</div>
            </div>
            <div id="feedback-area"></div>`;

        document.getElementById('record-btn').addEventListener('click', () => this.toggleRecord());
    },

    async toggleRecord() {
        const btn = document.getElementById('record-btn');
        const label = document.getElementById('record-label');

        if (!this.recording) {
            try {
                await AudioCapture.start();
                this.recording = true;
                btn.classList.add('recording');
                btn.innerHTML = '';
                label.textContent = 'Tap to stop';
            } catch (err) {
                label.textContent = 'Microphone access denied';
            }
        } else {
            this.recording = false;
            btn.classList.remove('recording');
            btn.innerHTML = '🎤';
            label.textContent = 'Processing...';
            btn.disabled = true;

            const blob = await AudioCapture.stop();
            await this.submitAudio(blob);
        }
    },

    async submitAudio(blob) {
        const feedback = document.getElementById('feedback-area');
        feedback.innerHTML = '<div class="loading"><div class="spinner"></div>Analyzing your speech...</div>';

        try {
            const formData = new FormData();
            formData.append('audio', blob, `recording.${AudioCapture.getExtension()}`);
            formData.append('session_data', JSON.stringify({
                item_ids: this.session.item_ids,
                formality: this.session.formality,
                prompt: this.session.prompt,
                started_at: this.sessionStartTime,
                mode: this.session.mode || 'speaking',
                sentence_id: this.session.sentence_id || null,
            }));

            const result = await API.submitPractice(formData);
            feedback.innerHTML = FeedbackComponent.render(result);

            // Show "Next" button
            feedback.innerHTML += `
                <div style="text-align:center;margin-top:1rem">
                    <button class="btn btn-primary btn-block" id="next-practice-btn">Next Practice</button>
                </div>`;
            document.getElementById('next-practice-btn').addEventListener('click', () => {
                this.session = null;
                this.load();
            });
        } catch (err) {
            feedback.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }

        document.getElementById('record-btn').disabled = false;
        document.getElementById('record-label').textContent = 'Tap to record again';
    },

    renderReadingCard() {
        const cards = this.session.cards;
        if (this.currentCardIndex >= cards.length) {
            this.completeReading();
            return;
        }
        const card = cards[this.currentCardIndex];
        const content = document.getElementById('practice-content');
        content.innerHTML = `
            <div class="card flashcard">
                <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:1rem">
                    ${this.currentCardIndex + 1} / ${cards.length}
                </div>
                <div style="font-size:1.5rem;margin-bottom:0.5rem">${this._esc(card.korean)}</div>
                ${card.sentence ? `<div style="font-size:0.95rem;color:var(--text-secondary);margin:0.75rem 0">${this._esc(card.sentence.korean)}</div>` : ''}
                <div id="reveal-area" class="hidden" style="margin-top:1.5rem;padding-top:1rem;border-top:2px solid var(--border)">
                    <div style="font-size:1.1rem;font-weight:600">${this._esc(card.english)}</div>
                    ${card.sentence ? `<div style="font-size:0.85rem;color:var(--text-secondary);margin-top:0.5rem">${this._esc(card.sentence.english)}</div>` : ''}
                </div>
            </div>
            <div style="text-align:center;margin-top:1rem">
                <button class="btn btn-primary btn-block" id="reveal-btn">Show Answer</button>
                <button class="btn btn-primary btn-block hidden" id="next-card-btn">Next</button>
            </div>`;

        document.getElementById('reveal-btn').addEventListener('click', () => {
            document.getElementById('reveal-area').classList.remove('hidden');
            document.getElementById('reveal-btn').classList.add('hidden');
            document.getElementById('next-card-btn').classList.remove('hidden');
        });
        document.getElementById('next-card-btn').addEventListener('click', () => {
            this.currentCardIndex++;
            this.renderReadingCard();
        });
    },

    async completeReading() {
        const content = document.getElementById('practice-content');
        const duration = Math.round((Date.now() - new Date(this.sessionStartTime).getTime()) / 1000);
        try {
            await API.completeReading({
                item_ids: this.session.cards.map(c => c.item_id),
                duration_seconds: duration,
                cards_reviewed: this.session.cards.length,
            });
            content.innerHTML = `
                <div class="card" style="text-align:center;padding:2rem">
                    <div style="font-size:1.5rem;margin-bottom:0.5rem">Complete!</div>
                    <div style="color:var(--text-secondary)">
                        ${this.session.cards.length} cards reviewed in ${Math.round(duration / 60)} min
                    </div>
                </div>
                <button class="btn btn-primary btn-block" id="next-practice-btn">New Session</button>`;
            document.getElementById('next-practice-btn').addEventListener('click', () => {
                this.session = null;
                this.load();
            });
        } catch (err) {
            content.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async startLessonPractice(lessonId) {
        // Navigate to practice page and start a lesson-based session
        Nav.show('practice');

        const el = document.getElementById('page-practice');
        el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading lesson...</div>';

        try {
            this.sessionStartTime = new Date().toISOString();
            this.session = await API.startPractice({ lesson_id: lessonId, formality: 'polite', item_count: 5, mode: 'speaking' });

            // Display lesson info if available
            if (this.session.lesson_info) {
                const content = document.getElementById('practice-content') || document.createElement('div');
                const lessonBanner = `
                    <div style="background:#f0f9ff;padding:0.75rem;border-radius:8px;margin-bottom:1rem;border-left:4px solid var(--primary)">
                        <div style="font-weight:600;margin-bottom:0.25rem">📚 ${this._esc(this.session.lesson_info)}</div>
                        <div style="font-size:0.85rem;color:var(--text-secondary)">Practicing ${this.session.target_items.length} items from this lesson</div>
                    </div>
                `;
                this.renderPrompt();
                // Insert lesson banner at the top
                const practiceContent = document.getElementById('practice-content');
                practiceContent.innerHTML = lessonBanner + practiceContent.innerHTML;
            } else {
                this.renderPrompt();
            }
        } catch (err) {
            el.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },
};
