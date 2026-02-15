const StatsPage = {
    async load() {
        const el = document.getElementById('page-stats');
        el.innerHTML = '<div class="loading"><div class="spinner"></div>Loading stats...</div>';

        try {
            const stats = await API.getStats();
            const m = stats.mastery;
            const total = (m.mastered + m.learning + m.struggling + m.unseen) || 1;
            const levelDisplay = stats.estimated_level != null ? stats.estimated_level.toFixed(1) : '—';

            el.innerHTML = `
                <div class="stat-grid">
                    <div class="card stat-card">
                        <div class="stat-value">${levelDisplay}</div>
                        <div class="stat-label">TOPIK Level</div>
                    </div>
                    <div class="card stat-card">
                        <div class="stat-value">${stats.due_for_review}</div>
                        <div class="stat-label">Due for Review</div>
                    </div>
                    <div class="card stat-card">
                        <div class="stat-value">${stats.recent_practice_count}</div>
                        <div class="stat-label">Sessions (7d)</div>
                    </div>
                    <div class="card stat-card">
                        <div class="stat-value">${stats.recent_avg_score != null ? Math.round(stats.recent_avg_score * 100) + '%' : '—'}</div>
                        <div class="stat-label">Avg Score (7d)</div>
                    </div>
                    <div class="card stat-card">
                        <div class="stat-value">${this._formatTime(stats.total_study_seconds || 0)}</div>
                        <div class="stat-label">Study Time</div>
                    </div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                        <h4>Goals</h4>
                        <button class="btn btn-secondary" id="add-goal-btn" style="padding:4px 12px;font-size:0.8rem">+ Goal</button>
                    </div>
                    <div id="goals-container"></div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <h4 style="margin-bottom:0.5rem">⚠️ Items Needing Attention</h4>
                    <div id="weaknesses-container"></div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <h4 style="margin-bottom:0.5rem">Error Patterns</h4>
                    <div id="error-patterns-container"></div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <h4 style="margin-bottom:0.5rem">Mastery Distribution</h4>
                    <div class="mastery-bar">
                        <div class="bar-mastered" style="width:${(m.mastered/total*100)}%"></div>
                        <div class="bar-learning" style="width:${(m.learning/total*100)}%"></div>
                        <div class="bar-struggling" style="width:${(m.struggling/total*100)}%"></div>
                        <div class="bar-unseen" style="width:${(m.unseen/total*100)}%"></div>
                    </div>
                    <div class="mastery-legend">
                        <div class="legend-item"><span class="legend-dot" style="background:var(--success)"></span> Mastered (${m.mastered})</div>
                        <div class="legend-item"><span class="legend-dot" style="background:var(--warning)"></span> Learning (${m.learning})</div>
                        <div class="legend-item"><span class="legend-dot" style="background:var(--error)"></span> Struggling (${m.struggling})</div>
                        <div class="legend-item"><span class="legend-dot" style="background:#E0E6ED"></span> Unseen (${m.unseen})</div>
                    </div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                        <h4>Practice Activity</h4>
                        <div class="interval-toggle" data-chart="activity">
                            <button class="interval-btn" data-days="7">7d</button>
                            <button class="interval-btn active" data-days="30">30d</button>
                            <button class="interval-btn" data-days="90">90d</button>
                        </div>
                    </div>
                    <div id="activity-chart" style="min-height:70px"></div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <h4 style="margin-bottom:0.5rem">Level Progression</h4>
                    <div id="level-chart" style="min-height:60px"></div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <h4 style="margin-bottom:0.5rem">Mastery by TOPIK Level</h4>
                    <div id="mastery-level-chart" style="min-height:60px"></div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                        <h4>Vocabulary Growth</h4>
                        <div class="interval-toggle" data-chart="vocab">
                            <button class="interval-btn" data-days="30">30d</button>
                            <button class="interval-btn active" data-days="90">90d</button>
                            <button class="interval-btn" data-days="0">All</button>
                        </div>
                    </div>
                    <div id="vocab-growth-chart" style="min-height:60px"></div>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <h4 style="margin-bottom:0.5rem">Summary</h4>
                    <div style="display:flex;justify-content:space-between;padding:0.35rem 0;border-bottom:1px solid var(--border)">
                        <span>Total Items</span><span style="font-weight:600">${stats.total_items}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:0.35rem 0;border-bottom:1px solid var(--border)">
                        <span>Items Encountered</span><span style="font-weight:600">${stats.items_encountered || 0}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:0.35rem 0;border-bottom:1px solid var(--border)">
                        <span>Vocabulary</span><span style="font-weight:600">${stats.vocab_count}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:0.35rem 0">
                        <span>Grammar</span><span style="font-weight:600">${stats.grammar_count}</span>
                    </div>
                </div>`;

            // Load charts, goals, and weakness analysis in parallel
            this._loadActivityChart();
            this._loadLevelChart();
            this._loadMasteryByLevel();
            this._loadVocabGrowth();
            this._loadGoals();
            this._loadWeaknesses();
            this._loadErrorPatterns();

            // Bind interval toggle buttons
            el.querySelectorAll('.interval-toggle').forEach(toggle => {
                toggle.querySelectorAll('.interval-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        toggle.querySelectorAll('.interval-btn').forEach(b => b.classList.remove('active'));
                        btn.classList.add('active');
                        const days = parseInt(btn.dataset.days) || 9999;
                        const chart = toggle.dataset.chart;
                        if (chart === 'activity') this._loadActivityChart(days);
                        else if (chart === 'vocab') this._loadVocabGrowth(days);
                    });
                });
            });
        } catch (err) {
            el.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async _loadActivityChart(days = 30) {
        const container = document.getElementById('activity-chart');
        if (!container) return;
        try {
            const data = await API.getActivity(days);
            const activity = data.activity || [];
            if (activity.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">No practice activity yet.</p>';
                return;
            }

            // Build a 30-day heatmap grid
            const today = new Date();
            const dayMap = {};
            for (const a of activity) {
                dayMap[a.date] = a;
            }

            let html = '<div style="display:flex;flex-wrap:wrap;gap:2px">';
            for (let i = days - 1; i >= 0; i--) {
                const d = new Date(today);
                d.setDate(d.getDate() - i);
                const key = d.toISOString().split('T')[0];
                const entry = dayMap[key];
                const sessions = entry ? entry.sessions : 0;
                const score = entry && entry.avg_score != null ? Math.round(entry.avg_score * 100) : null;

                // Color intensity based on sessions
                let bg = '#E0E6ED';
                if (sessions >= 5) bg = '#2E7D32';
                else if (sessions >= 3) bg = '#4CAF50';
                else if (sessions >= 1) bg = '#81C784';

                const label = d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
                const title = sessions > 0 ? `${label}: ${sessions} session${sessions > 1 ? 's' : ''}${score != null ? `, avg ${score}%` : ''}` : `${label}: no practice`;

                html += `<div style="width:calc(100%/15 - 2px);aspect-ratio:1;background:${bg};border-radius:3px;min-width:8px" title="${title}"></div>`;
            }
            html += '</div>';

            // Summary line
            const totalSessions = activity.reduce((s, a) => s + a.sessions, 0);
            const activeDays = activity.length;
            html += `<div style="font-size:0.8rem;color:var(--text-secondary);margin-top:0.5rem">${totalSessions} sessions across ${activeDays} active days</div>`;

            container.innerHTML = html;
        } catch {
            container.innerHTML = '';
        }
    },

    async _loadLevelChart() {
        const container = document.getElementById('level-chart');
        if (!container) return;
        try {
            const data = await API.getLevelHistory();
            const history = data.history || [];
            if (history.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">Complete practice sessions to track your level.</p>';
                return;
            }

            const latest = history[history.length - 1];
            const first = history[0];
            const change = (latest.level - first.level).toFixed(1);
            const arrow = change > 0 ? '+' : '';

            let html = `<div style="font-size:0.85rem;line-height:1.8">`;
            html += `<div>Current: <strong>TOPIK ${latest.level.toFixed(1)}</strong></div>`;
            if (history.length > 1) {
                html += `<div>Change: <strong style="color:${change >= 0 ? 'var(--success)' : 'var(--error)'}">${arrow}${change}</strong> since ${new Date(first.date).toLocaleDateString()}</div>`;
            }

            // Sparkline
            const recent = history.slice(-15);
            const maxLevel = Math.max(...recent.map(h => h.level), 1);
            const minLevel = Math.min(...recent.map(h => h.level), 1);
            const range = Math.max(maxLevel - minLevel, 0.5);

            html += `<div style="display:flex;align-items:end;gap:2px;height:40px;margin-top:0.5rem">`;
            for (const h of recent) {
                const pct = ((h.level - minLevel) / range) * 100;
                const height = Math.max(pct, 10);
                html += `<div style="flex:1;background:var(--primary);border-radius:2px 2px 0 0;height:${height}%" title="TOPIK ${h.level.toFixed(1)}"></div>`;
            }
            html += `</div></div>`;
            container.innerHTML = html;
        } catch {
            container.innerHTML = '';
        }
    },

    async _loadMasteryByLevel() {
        const container = document.getElementById('mastery-level-chart');
        if (!container) return;
        try {
            const data = await API.getMasteryByLevel();
            const levels = data.levels || [];
            if (levels.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">No mastery data yet.</p>';
                return;
            }

            let html = '';
            for (const lv of levels) {
                const total = lv.total || 1;
                const masteredPct = (lv.mastered / total * 100).toFixed(0);
                const learningPct = (lv.learning / total * 100).toFixed(0);
                const strugglingPct = (lv.struggling / total * 100).toFixed(0);
                const unseenPct = (lv.unseen / total * 100).toFixed(0);

                html += `
                    <div style="margin-bottom:0.5rem">
                        <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:0.15rem">
                            <span>TOPIK ${lv.level}</span>
                            <span style="color:var(--text-secondary)">${lv.total} items${lv.avg_score != null ? ` (avg ${Math.round(lv.avg_score * 100)}%)` : ''}</span>
                        </div>
                        <div style="display:flex;height:12px;border-radius:6px;overflow:hidden;background:#E0E6ED">
                            <div style="width:${masteredPct}%;background:var(--success)"></div>
                            <div style="width:${learningPct}%;background:var(--warning)"></div>
                            <div style="width:${strugglingPct}%;background:var(--error)"></div>
                        </div>
                    </div>`;
            }
            container.innerHTML = html;
        } catch {
            container.innerHTML = '';
        }
    },

    async _loadVocabGrowth(days = 90) {
        const container = document.getElementById('vocab-growth-chart');
        if (!container) return;
        try {
            const data = await API.getVocabGrowth(days);
            const growth = data.growth || [];
            if (growth.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">No encounter data yet.</p>';
                return;
            }

            const maxCum = Math.max(...growth.map(g => g.cumulative), 1);

            let html = `<div style="display:flex;align-items:end;gap:2px;height:50px">`;
            for (const g of growth.slice(-30)) {
                const height = (g.cumulative / maxCum * 100);
                html += `<div style="flex:1;background:var(--primary);border-radius:2px 2px 0 0;height:${Math.max(height, 5)}%;opacity:0.8" title="${g.date}: ${g.cumulative} total (+${g.new})"></div>`;
            }
            html += `</div>`;
            html += `<div style="font-size:0.8rem;color:var(--text-secondary);margin-top:0.5rem">Total items encountered: ${growth[growth.length - 1].cumulative}</div>`;
            container.innerHTML = html;
        } catch {
            container.innerHTML = '';
        }
    },

    _formatTime(seconds) {
        if (!seconds) return '0m';
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    },

    async _loadGoals() {
        const container = document.getElementById('goals-container');
        if (!container) return;
        try {
            const data = await API.getGoals();
            if (!data.goals || data.goals.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">No active goals. Tap + to set one.</p>';
                return;
            }
            const typeLabels = { practice_sessions: 'Sessions', new_items: 'New Items', study_time: 'Study (min)' };
            container.innerHTML = data.goals.map(g => `
                <div style="margin-bottom:0.75rem">
                    <div style="display:flex;justify-content:space-between;font-size:0.85rem;margin-bottom:0.25rem">
                        <span>${typeLabels[g.goal_type] || g.goal_type}: ${g.current_value}/${g.target_value}</span>
                        <span style="color:var(--text-secondary)">${g.period}${g.deadline ? ' - ' + g.deadline : ''}</span>
                    </div>
                    <div class="goal-progress-bar">
                        <div class="goal-progress-fill" style="width:${Math.min(g.progress_pct, 100)}%;background:${g.progress_pct >= 100 ? 'var(--success)' : 'var(--primary)'}"></div>
                    </div>
                </div>
            `).join('');
        } catch { container.innerHTML = ''; }
    },

    async _loadWeaknesses() {
        const container = document.getElementById('weaknesses-container');
        if (!container) return;
        try {
            const data = await API.getWeaknesses(10);
            if (!data.weaknesses || data.weaknesses.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">No problem items identified. Great work!</p>';
                return;
            }

            const typeIcons = { vocab: '📗', grammar: '📘' };
            const weaknessLabels = {
                not_absorbing: '❌ Not absorbing',
                high_errors: '⚠️ High error rate',
                stagnant: '⏸️ Stagnant',
                needs_practice: '📝 Needs practice'
            };
            const weaknessColors = {
                not_absorbing: '#ef4444',
                high_errors: '#f59e0b',
                stagnant: '#6b7280',
                needs_practice: '#3b82f6'
            };

            container.innerHTML = data.weaknesses.map(w => `
                <div style="padding:0.5rem;border-left:3px solid ${weaknessColors[w.weakness_type]};background:#f9fafb;margin-bottom:0.5rem;border-radius:4px">
                    <div style="display:flex;justify-content:space-between;align-items:start">
                        <div style="flex:1">
                            <div style="font-weight:600;margin-bottom:0.25rem">
                                ${typeIcons[w.item_type]} ${this._esc(w.korean)} <span style="color:var(--text-secondary);font-weight:normal">(${this._esc(w.english)})</span>
                            </div>
                            <div style="font-size:0.75rem;color:var(--text-secondary)">
                                ${weaknessLabels[w.weakness_type]} •
                                Exposed ${w.exposure_count}x, Used ${w.usage_count}x, Errors ${w.error_count}x •
                                Absorption ${Math.round(w.absorption_rate * 100)}%, Error rate ${Math.round(w.error_rate * 100)}%
                            </div>
                        </div>
                        <div style="text-align:right;font-size:0.75rem;white-space:nowrap;margin-left:1rem">
                            <div style="font-weight:600;color:${w.overall_score >= 0.7 ? 'var(--success)' : (w.overall_score >= 0.5 ? 'var(--warning)' : 'var(--error)')}">${Math.round(w.overall_score * 100)}%</div>
                            <div style="color:var(--text-secondary)">mastery</div>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch { container.innerHTML = ''; }
    },

    async _loadErrorPatterns() {
        const container = document.getElementById('error-patterns-container');
        if (!container) return;
        try {
            const data = await API.getErrorPatterns(10);
            if (!data.by_type || data.by_type.length === 0) {
                container.innerHTML = '<p style="color:var(--text-secondary);font-size:0.85rem">No error patterns yet.</p>';
                return;
            }

            let html = '<div style="font-size:0.85rem">';

            // By type summary
            html += '<div style="margin-bottom:1rem">';
            html += '<div style="font-weight:600;margin-bottom:0.5rem">By Type:</div>';
            data.by_type.forEach(t => {
                const rate = Math.round((t.avg_error_rate || 0) * 100);
                const color = rate > 50 ? 'var(--error)' : (rate > 30 ? 'var(--warning)' : 'var(--success)');
                html += `<div style="display:flex;justify-content:space-between;padding:0.25rem 0">
                    <span>${t.item_type === 'vocab' ? '📗 Vocabulary' : '📘 Grammar'} (${t.item_count} items)</span>
                    <span style="color:${color};font-weight:600">${rate}% error rate</span>
                </div>`;
            });
            html += '</div>';

            // Top problem items
            if (data.top_errors && data.top_errors.length > 0) {
                html += '<div style="margin-bottom:1rem">';
                html += '<div style="font-weight:600;margin-bottom:0.5rem">Most Common Mistakes:</div>';
                data.top_errors.slice(0, 5).forEach(e => {
                    const rate = Math.round((e.error_rate || 0) * 100);
                    html += `<div style="display:flex;justify-content:space-between;padding:0.25rem 0;border-bottom:1px solid var(--border)">
                        <span>${this._esc(e.korean)} <span style="color:var(--text-secondary)">(${this._esc(e.english)})</span></span>
                        <span style="color:var(--error);font-weight:600">${rate}%</span>
                    </div>`;
                });
                html += '</div>';
            }

            // Grammar categories (if available)
            if (data.by_grammar_category && data.by_grammar_category.length > 0) {
                html += '<div>';
                html += '<div style="font-weight:600;margin-bottom:0.5rem">Problem Grammar Categories:</div>';
                data.by_grammar_category.slice(0, 5).forEach(g => {
                    const rate = Math.round((g.avg_error_rate || 0) * 100);
                    html += `<div style="display:flex;justify-content:space-between;padding:0.25rem 0">
                        <span>${this._esc(g.category || 'Uncategorized')} (${g.item_count} items)</span>
                        <span style="color:var(--error);font-weight:600">${rate}%</span>
                    </div>`;
                });
                html += '</div>';
            }

            html += '</div>';
            container.innerHTML = html;
        } catch { container.innerHTML = ''; }
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },
};
