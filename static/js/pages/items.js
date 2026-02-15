const ItemsPage = {
    currentPage: 1,
    currentSearch: '',
    currentLevel: '',
    currentType: '',
    currentPos: '',
    showAddForm: false,

    load() {
        const el = document.getElementById('page-items');
        el.innerHTML = `
            <div class="search-bar">
                <input type="text" id="items-search" placeholder="Search Korean or English...">
                <select id="items-level">
                    <option value="">All Levels</option>
                    <option value="1">TOPIK 1</option>
                    <option value="2">TOPIK 2</option>
                    <option value="3">TOPIK 3</option>
                    <option value="4">TOPIK 4</option>
                    <option value="5">TOPIK 5</option>
                    <option value="6">TOPIK 6</option>
                </select>
            </div>
            <div style="display:flex;gap:0.5rem;margin-bottom:1rem">
                <select id="items-type" style="flex:1;padding:8px;border:2px solid var(--border);border-radius:8px;background:white">
                    <option value="">All Types</option>
                    <option value="vocab">Vocab</option>
                    <option value="grammar">Grammar</option>
                </select>
                <select id="items-pos" style="flex:1;padding:8px;border:2px solid var(--border);border-radius:8px;background:white">
                    <option value="">All POS</option>
                    <option value="noun">Noun</option>
                    <option value="verb">Verb</option>
                    <option value="adjective">Adjective</option>
                    <option value="adverb">Adverb</option>
                    <option value="particle">Particle</option>
                    <option value="determiner">Determiner</option>
                    <option value="interjection">Interjection</option>
                    <option value="suffix">Suffix</option>
                </select>
                <button class="btn btn-secondary" id="toggle-add-btn">+ Add</button>
            </div>
            <div id="add-form-area" class="hidden"></div>
            <div id="items-list"></div>
            <div id="items-pagination" style="text-align:center;margin-top:1rem"></div>`;

        document.getElementById('items-search').addEventListener('input', this._debounce(() => this.search(), 300));
        document.getElementById('items-level').addEventListener('change', () => this.search());
        document.getElementById('items-type').addEventListener('change', () => this.search());
        document.getElementById('items-pos').addEventListener('change', () => this.search());
        document.getElementById('toggle-add-btn').addEventListener('click', () => this.toggleAddForm());
        this.search();
    },

    toggleAddForm() {
        const area = document.getElementById('add-form-area');
        this.showAddForm = !this.showAddForm;
        if (this.showAddForm) {
            area.classList.remove('hidden');
            area.innerHTML = `
                <div class="add-form card">
                    <input type="text" id="add-korean" placeholder="Korean (e.g. 행복하다)">
                    <input type="text" id="add-english" placeholder="English (e.g. to be happy)">
                    <div class="form-row">
                        <select id="add-type">
                            <option value="vocab">Vocab</option>
                            <option value="grammar">Grammar</option>
                        </select>
                        <select id="add-level">
                            ${[1,2,3,4,5,6].map(l => `<option value="${l}">TOPIK ${l}</option>`).join('')}
                        </select>
                    </div>
                    <button class="btn btn-primary btn-block" id="add-submit-btn" style="margin-top:0.5rem">Add Item</button>
                </div>`;
            document.getElementById('add-submit-btn').addEventListener('click', () => this.addItem());
        } else {
            area.classList.add('hidden');
        }
    },

    async addItem() {
        const korean = document.getElementById('add-korean').value.trim();
        const english = document.getElementById('add-english').value.trim();
        if (!korean || !english) return;

        try {
            await API.createItem({
                korean, english,
                item_type: document.getElementById('add-type').value,
                topik_level: parseInt(document.getElementById('add-level').value),
            });
            this.showAddForm = false;
            document.getElementById('add-form-area').classList.add('hidden');
            this.search();
        } catch (err) {
            alert(err.message);
        }
    },

    async search() {
        this.currentSearch = document.getElementById('items-search')?.value || '';
        this.currentLevel = document.getElementById('items-level')?.value || '';
        this.currentType = document.getElementById('items-type')?.value || '';
        this.currentPos = document.getElementById('items-pos')?.value || '';
        this.currentPage = 1;
        await this.fetchItems();
    },

    async fetchItems() {
        const list = document.getElementById('items-list');
        list.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

        try {
            const params = { page: this.currentPage, per_page: 50 };
            if (this.currentSearch) params.search = this.currentSearch;
            if (this.currentLevel) params.topik_level = this.currentLevel;
            if (this.currentType) params.item_type = this.currentType;
            if (this.currentPos) params.pos = this.currentPos;

            const data = await API.getItems(params);

            if (data.items.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-icon">📚</div><p>No items found</p></div>';
                return;
            }

            list.innerHTML = data.items.map(i => ItemCard.render(i)).join('');

            // Click to detail
            list.querySelectorAll('[data-item-id]').forEach(card => {
                card.style.cursor = 'pointer';
                card.addEventListener('click', () => {
                    this._loadDetail(parseInt(card.dataset.itemId));
                });
            });

            const totalPages = Math.ceil(data.total / data.per_page);
            const pag = document.getElementById('items-pagination');
            if (totalPages > 1) {
                pag.innerHTML = `
                    <span style="font-size:0.85rem;color:var(--text-secondary)">
                        Page ${data.page} of ${totalPages} (${data.total} items)
                    </span>
                    <div style="margin-top:0.5rem;display:flex;gap:0.5rem;justify-content:center">
                        ${data.page > 1 ? `<button class="btn btn-secondary" onclick="ItemsPage.goPage(${data.page - 1})">Prev</button>` : ''}
                        ${data.page < totalPages ? `<button class="btn btn-secondary" onclick="ItemsPage.goPage(${data.page + 1})">Next</button>` : ''}
                    </div>`;
            } else {
                pag.innerHTML = `<span style="font-size:0.85rem;color:var(--text-secondary)">${data.total} items</span>`;
            }
        } catch (err) {
            list.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async _loadDetail(itemId) {
        const el = document.getElementById('page-items');
        el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

        try {
            const item = await API.getItem(itemId);
            const formalityLabels = { formal: 'Formal', polite: 'Polite', casual: 'Casual' };

            let html = `
                <button class="btn btn-secondary" id="items-back" style="margin-bottom:1rem">Back</button>

                <div class="card">
                    <div class="item-korean" style="font-size:1.3rem;margin-bottom:0.25rem">${this._esc(item.korean)}</div>
                    ${item.dictionary_form ? `<div style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0.25rem">Dictionary: ${this._esc(item.dictionary_form)}</div>` : ''}
                    <div class="item-english" style="font-size:1rem;margin-bottom:0.5rem">${this._esc(item.english)}</div>
                    <div class="item-meta">
                        <span class="badge badge-level">TOPIK ${item.topik_level}</span>
                        <span class="badge badge-type">${item.item_type}</span>
                        ${item.pos ? `<span class="badge badge-pos">${item.pos}</span>` : ''}
                        ${item.grammar_category ? `<span class="badge">${item.grammar_category}</span>` : ''}
                        ${item.source !== 'seed' ? `<span class="badge">${item.source}</span>` : ''}
                    </div>
                    ${item.notes ? `<p style="margin-top:0.5rem;font-size:0.85rem;color:var(--text-secondary)">${this._esc(item.notes)}</p>` : ''}
                </div>`;

            // Mastery
            if (item.mastery) {
                const m = item.mastery;
                const pct = Math.round((m.overall_score || 0) * 100);
                const color = pct >= 80 ? 'var(--success)' : pct >= 50 ? 'var(--warning)' : 'var(--error)';
                html += `
                    <div class="card" style="margin-top:0.75rem">
                        <h4 style="margin-bottom:0.5rem">Your Mastery</h4>
                        <div style="display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem">
                            <div style="font-size:2rem;font-weight:700;color:${color}">${pct}%</div>
                            <div style="font-size:0.85rem;color:var(--text-secondary)">
                                ${m.practice_count} practice${m.practice_count !== 1 ? 's' : ''}
                            </div>
                        </div>
                        <div style="display:flex;gap:1rem;font-size:0.85rem">
                            <div>Grammar: <strong>${Math.round((m.grammar_score || 0) * 100)}%</strong></div>
                            <div>Vocab: <strong>${Math.round((m.vocab_score || 0) * 100)}%</strong></div>
                            <div>Formality: <strong>${Math.round((m.formality_score || 0) * 100)}%</strong></div>
                        </div>
                    </div>`;
            } else {
                html += `
                    <div class="card" style="margin-top:0.75rem">
                        <h4 style="margin-bottom:0.25rem">Your Mastery</h4>
                        <p style="font-size:0.85rem;color:var(--text-secondary)">Not practiced yet</p>
                    </div>`;
            }

            // SRS
            if (item.srs) {
                const s = item.srs;
                const nextReview = s.next_review ? new Date(s.next_review).toLocaleDateString() : '—';
                const isOverdue = s.next_review && new Date(s.next_review) <= new Date();
                html += `
                    <div class="card" style="margin-top:0.5rem">
                        <h4 style="margin-bottom:0.5rem">Review Schedule</h4>
                        <div style="font-size:0.85rem;line-height:1.8">
                            <div>Next review: <strong style="${isOverdue ? 'color:var(--error)' : ''}">${nextReview}${isOverdue ? ' (overdue)' : ''}</strong></div>
                            <div>Interval: ${Math.round(s.interval_days)} days</div>
                            <div>Repetitions: ${s.repetitions}</div>
                        </div>
                    </div>`;
            }

            // Examples
            if (item.examples && item.examples.length > 0) {
                html += `
                    <div class="card" style="margin-top:0.75rem">
                        <h4 style="margin-bottom:0.5rem">Examples (${item.examples.length})</h4>`;
                for (const ex of item.examples) {
                    html += `
                        <div style="padding:0.4rem 0;border-bottom:1px solid var(--border)">
                            <div style="font-size:0.95rem">${this._esc(ex.korean)}</div>
                            <div style="font-size:0.85rem;color:var(--text-secondary)">${this._esc(ex.english)}</div>
                            <span class="badge" style="margin-top:0.15rem;font-size:0.75rem">${formalityLabels[ex.formality] || ex.formality}</span>
                        </div>`;
                }
                html += `</div>`;
            }

            // Tags
            if (item.tags && item.tags.length > 0) {
                html += `
                    <div class="card" style="margin-top:0.5rem">
                        <div class="item-meta">
                            ${item.tags.map(t => `<span class="badge">${this._esc(t)}</span>`).join('')}
                        </div>
                    </div>`;
            }

            el.innerHTML = html;
            document.getElementById('items-back').addEventListener('click', () => this.load());
        } catch (err) {
            el.innerHTML = `
                <button class="btn btn-secondary" id="items-back" style="margin-bottom:1rem">Back</button>
                <div class="card"><p class="error">${err.message}</p></div>`;
            document.getElementById('items-back').addEventListener('click', () => this.load());
        }
    },

    goPage(page) {
        this.currentPage = page;
        this.fetchItems();
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },

    _debounce(fn, ms) {
        let t;
        return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
    },
};
