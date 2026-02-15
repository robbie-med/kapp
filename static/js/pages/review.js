const ReviewPage = {
    async load() {
        const el = document.getElementById('page-review');
        el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading review queue...</div>';

        try {
            const [queue, history] = await Promise.all([
                API.getReviewQueue(),
                API.getHistory(10),
            ]);

            let html = '';
            if (queue.total_due > 0) {
                html += `<h3 style="margin-bottom:0.75rem">Due for Review (${queue.total_due})</h3>`;
                for (const item of queue.queue.slice(0, 20)) {
                    const overdue = new Date(item.next_review) < new Date();
                    html += `
                        <div class="card review-item">
                            <div>
                                <div class="item-korean">${this._esc(item.korean)}</div>
                                <div class="item-english">${this._esc(item.english)}</div>
                                <div class="item-meta">
                                    <span class="badge badge-level">TOPIK ${item.topik_level}</span>
                                    <span class="badge">${item.repetitions} reps</span>
                                    ${item.overall_score != null ? `<span class="badge">${Math.round(item.overall_score * 100)}%</span>` : ''}
                                </div>
                            </div>
                            ${overdue ? '<span class="overdue-tag">Overdue</span>' : ''}
                        </div>`;
                }
            } else {
                html += `<div class="empty-state">
                    <div class="empty-icon">✅</div>
                    <p>All caught up! No items due for review.</p>
                </div>`;
            }

            if (history.sessions.length > 0) {
                html += `<h3 style="margin:1.5rem 0 0.75rem">Recent Practice</h3>`;
                for (const s of history.sessions) {
                    const scorePct = s.overall_score != null ? Math.round(s.overall_score * 100) + '%' : '—';
                    const scoreClass = s.overall_score >= 0.8 ? 'score-high' :
                                      s.overall_score >= 0.5 ? 'score-mid' : 'score-low';
                    html += `
                        <div class="card" style="cursor:pointer" data-session-id="${s.id}">
                            <div style="display:flex;justify-content:space-between;align-items:center">
                                <div>
                                    <div style="font-size:0.9rem">${this._esc(s.prompt?.substring(0, 60))}...</div>
                                    <div style="font-size:0.8rem;color:var(--text-secondary);margin-top:0.25rem">
                                        ${this._esc(s.transcript?.substring(0, 50) || '—')}
                                    </div>
                                    <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.25rem">
                                        ${new Date(s.created_at).toLocaleDateString()} · ${s.formality}
                                    </div>
                                </div>
                                <span class="score-badge ${scoreClass}" style="font-size:0.85rem">${scorePct}</span>
                            </div>
                        </div>`;
                }
            }

            el.innerHTML = html;

            // Attach click handlers to session cards
            el.querySelectorAll('[data-session-id]').forEach(card => {
                card.addEventListener('click', () => {
                    this._loadSessionDetail(parseInt(card.dataset.sessionId));
                });
            });
        } catch (err) {
            el.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async _loadSessionDetail(sessionId) {
        const el = document.getElementById('page-review');
        el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading session...</div>';

        try {
            const session = await API.getSessionDetail(sessionId);

            let html = `
                <button class="btn btn-secondary" id="back-to-history" style="margin-bottom:1rem">
                    Back to Review
                </button>

                <div class="prompt-card card">
                    <h4 style="margin-bottom:0.5rem">Prompt</h4>
                    <p style="font-size:1rem;line-height:1.5">${this._esc(session.prompt)}</p>
                    <div style="margin-top:0.5rem;font-size:0.8rem;color:var(--text-secondary)">
                        ${new Date(session.created_at).toLocaleDateString()} · ${this._esc(session.formality)}
                    </div>
                </div>`;

            if (session.items && session.items.length > 0) {
                html += `<div class="card"><h4 style="margin-bottom:0.5rem">Items Practiced</h4>`;
                for (const item of session.items) {
                    html += `
                        <div style="display:flex;gap:0.5rem;align-items:baseline;margin-bottom:0.25rem">
                            <span class="badge">${this._esc(item.item_type)}</span>
                            <strong>${this._esc(item.korean)}</strong>
                            <span style="color:var(--text-secondary)">${this._esc(item.english)}</span>
                        </div>`;
                }
                html += `</div>`;
            }

            if (session.feedback) {
                html += FeedbackComponent.render(session.feedback);
            } else {
                html += `<div class="card"><p style="color:var(--text-secondary)">No detailed feedback available for this session.</p></div>`;
            }

            el.innerHTML = html;

            document.getElementById('back-to-history').addEventListener('click', () => {
                this.load();
            });
        } catch (err) {
            el.innerHTML = `
                <button class="btn btn-secondary" id="back-to-history" style="margin-bottom:1rem">
                    Back to Review
                </button>
                <div class="card"><p class="error">${err.message}</p></div>`;
            document.getElementById('back-to-history').addEventListener('click', () => {
                this.load();
            });
        }
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },
};
