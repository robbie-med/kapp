const TeacherPage = {
    currentPage: 1,
    currentSearch: '',
    currentLevel: '',
    currentType: '',
    showAddForm: false,

    _posLabels: { noun: '명사', verb: '동사', adjective: '형용사', adverb: '부사', particle: '조사', determiner: '관형사', interjection: '감탄사', suffix: '접미사' },
    _grammarCatLabels: { ending: '어미', particle: '조사', connector: '연결', expression: '표현', conjugation: '활용' },
    _formalityLabels: { formal: '격식체', polite: '존댓말', casual: '반말' },
    _sourceLabels: { seed: '기본', telegram: '텔레그램', signal: '시그널', teacher: '선생님', manual: '수동' },

    load() {
        const el = document.getElementById('page-teacher');
        el.innerHTML = `
            <div class="search-bar">
                <input type="text" id="teacher-search" placeholder="한국어 또는 영어로 검색...">
                <select id="teacher-level">
                    <option value="">전체 수준</option>
                    <option value="1">TOPIK 1</option>
                    <option value="2">TOPIK 2</option>
                    <option value="3">TOPIK 3</option>
                    <option value="4">TOPIK 4</option>
                    <option value="5">TOPIK 5</option>
                    <option value="6">TOPIK 6</option>
                </select>
            </div>
            <div style="display:flex;gap:0.5rem;margin-bottom:1rem">
                <select id="teacher-type" style="flex:1;padding:8px;border:2px solid var(--border);border-radius:8px;background:white">
                    <option value="">전체 유형</option>
                    <option value="vocab">단어</option>
                    <option value="grammar">문법</option>
                </select>
                <button class="btn btn-primary" id="teacher-add-btn">+ 항목 추가</button>
                <button class="btn btn-secondary" id="teacher-dup-btn">중복 확인</button>
            </div>
            <div id="teacher-add-area" class="hidden"></div>
            <div id="teacher-dup-area" class="hidden"></div>
            <div id="teacher-list"></div>
            <div id="teacher-pagination" style="text-align:center;margin-top:1rem"></div>
            <div id="teacher-sentences" style="margin-top:2rem"></div>
            <div id="teacher-students" style="margin-top:2rem"></div>`;

        this._loadSentences();
        this._loadStudents();

        document.getElementById('teacher-search').addEventListener('input', this._debounce(() => this._search(), 300));
        document.getElementById('teacher-level').addEventListener('change', () => this._search());
        document.getElementById('teacher-type').addEventListener('change', () => this._search());
        document.getElementById('teacher-add-btn').addEventListener('click', () => this._toggleAddForm());
        document.getElementById('teacher-dup-btn').addEventListener('click', () => this._findDuplicates());
        this._search();
    },

    _toggleAddForm() {
        const area = document.getElementById('teacher-add-area');
        this.showAddForm = !this.showAddForm;
        if (this.showAddForm) {
            area.classList.remove('hidden');
            area.innerHTML = `
                <div class="add-form card">
                    <input type="text" id="tadd-korean" placeholder="한국어 (예: 행복하다)">
                    <input type="text" id="tadd-english" placeholder="영어 (예: to be happy)">
                    <div class="form-row">
                        <select id="tadd-type">
                            <option value="vocab">단어</option>
                            <option value="grammar">문법</option>
                        </select>
                        <select id="tadd-level">
                            ${[1,2,3,4,5,6].map(l => `<option value="${l}">TOPIK ${l}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-row">
                        <select id="tadd-pos">
                            <option value="">품사</option>
                            <option value="noun">명사</option>
                            <option value="verb">동사</option>
                            <option value="adjective">형용사</option>
                            <option value="adverb">부사</option>
                            <option value="particle">조사</option>
                            <option value="determiner">관형사</option>
                            <option value="interjection">감탄사</option>
                            <option value="suffix">접미사</option>
                        </select>
                        <input type="text" id="tadd-dictionary-form" placeholder="사전형 (선택사항)" style="flex:1">
                    </div>
                    <input type="text" id="tadd-notes" placeholder="메모 (선택사항)">
                    <button class="btn btn-primary btn-block" id="tadd-submit" style="margin-top:0.5rem">추가</button>
                </div>`;
            document.getElementById('tadd-submit').addEventListener('click', () => this._addItem());
        } else {
            area.classList.add('hidden');
        }
    },

    async _addItem() {
        const korean = document.getElementById('tadd-korean').value.trim();
        const english = document.getElementById('tadd-english').value.trim();
        if (!korean || !english) return;

        try {
            const data = {
                korean, english,
                item_type: document.getElementById('tadd-type').value,
                topik_level: parseInt(document.getElementById('tadd-level').value),
                notes: document.getElementById('tadd-notes').value.trim(),
            };
            const pos = document.getElementById('tadd-pos').value;
            const dictForm = document.getElementById('tadd-dictionary-form').value.trim();
            if (pos) data.pos = pos;
            if (dictForm) data.dictionary_form = dictForm;
            await API.createItem(data);
            this.showAddForm = false;
            document.getElementById('teacher-add-area').classList.add('hidden');
            this._search();
        } catch (err) {
            alert('오류: ' + err.message);
        }
    },

    async _search() {
        this.currentSearch = document.getElementById('teacher-search')?.value || '';
        this.currentLevel = document.getElementById('teacher-level')?.value || '';
        this.currentType = document.getElementById('teacher-type')?.value || '';
        this.currentPage = 1;
        await this._fetchItems();
    },

    async _fetchItems() {
        const list = document.getElementById('teacher-list');
        list.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

        try {
            const params = { page: this.currentPage, per_page: 50 };
            if (this.currentSearch) params.search = this.currentSearch;
            if (this.currentLevel) params.topik_level = this.currentLevel;
            if (this.currentType) params.item_type = this.currentType;

            const data = await API.getItems(params);

            if (data.items.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-icon">📚</div><p>항목이 없습니다</p></div>';
                return;
            }

            let html = '';
            for (const item of data.items) {
                const exCount = item.example_count || 0;
                html += `
                    <div class="card item-card" style="cursor:pointer" data-item-id="${item.id}">
                        <div>
                            <div class="item-korean">${this._esc(item.korean)}</div>
                            <div class="item-english">${this._esc(item.english)}</div>
                            <div class="item-meta">
                                <span class="badge badge-level">TOPIK ${item.topik_level}</span>
                                <span class="badge badge-type">${item.item_type === 'vocab' ? '단어' : '문법'}</span>
                                ${item.pos ? `<span class="badge badge-pos">${this._posLabels[item.pos] || item.pos}</span>` : ''}
                                ${item.grammar_category ? `<span class="badge">${this._grammarCatLabels[item.grammar_category] || item.grammar_category}</span>` : ''}
                                ${exCount > 0 ? `<span class="badge">예문 ${exCount}</span>` : ''}
                                ${item.notes ? `<span class="badge">메모</span>` : ''}
                            </div>
                        </div>
                    </div>`;
            }
            list.innerHTML = html;

            // Click handlers
            list.querySelectorAll('[data-item-id]').forEach(card => {
                card.addEventListener('click', () => {
                    this._loadDetail(parseInt(card.dataset.itemId));
                });
            });

            // Pagination
            const totalPages = Math.ceil(data.total / data.per_page);
            const pag = document.getElementById('teacher-pagination');
            if (totalPages > 1) {
                pag.innerHTML = `
                    <span style="font-size:0.85rem;color:var(--text-secondary)">
                        ${data.page} / ${totalPages} 페이지 (총 ${data.total}개)
                    </span>
                    <div style="margin-top:0.5rem;display:flex;gap:0.5rem;justify-content:center">
                        ${data.page > 1 ? `<button class="btn btn-secondary" id="teacher-prev">이전</button>` : ''}
                        ${data.page < totalPages ? `<button class="btn btn-secondary" id="teacher-next">다음</button>` : ''}
                    </div>`;
                const prev = document.getElementById('teacher-prev');
                const next = document.getElementById('teacher-next');
                if (prev) prev.addEventListener('click', () => { this.currentPage--; this._fetchItems(); });
                if (next) next.addEventListener('click', () => { this.currentPage++; this._fetchItems(); });
            } else {
                pag.innerHTML = `<span style="font-size:0.85rem;color:var(--text-secondary)">총 ${data.total}개</span>`;
            }
        } catch (err) {
            list.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async _loadDetail(itemId) {
        const el = document.getElementById('page-teacher');
        el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

        try {
            const item = await API.getItem(itemId);

            const formalityLabels = this._formalityLabels;

            let html = `
                <button class="btn btn-secondary" id="teacher-back" style="margin-bottom:1rem">뒤로</button>

                <div class="card">
                    <h4 style="margin-bottom:0.75rem">항목 수정</h4>
                    <div style="margin-bottom:0.5rem">
                        <label style="font-size:0.8rem;color:var(--text-secondary)">한국어</label>
                        <input type="text" id="edit-korean" value="${this._escAttr(item.korean)}">
                    </div>
                    <div style="margin-bottom:0.5rem">
                        <label style="font-size:0.8rem;color:var(--text-secondary)">영어</label>
                        <input type="text" id="edit-english" value="${this._escAttr(item.english)}">
                    </div>
                    <div class="form-row" style="margin-bottom:0.5rem">
                        <div style="flex:1">
                            <label style="font-size:0.8rem;color:var(--text-secondary)">유형</label>
                            <select id="edit-type">
                                <option value="vocab" ${item.item_type === 'vocab' ? 'selected' : ''}>단어</option>
                                <option value="grammar" ${item.item_type === 'grammar' ? 'selected' : ''}>문법</option>
                            </select>
                        </div>
                        <div style="flex:1">
                            <label style="font-size:0.8rem;color:var(--text-secondary)">TOPIK 수준</label>
                            <select id="edit-level">
                                ${[1,2,3,4,5,6].map(l => `<option value="${l}" ${item.topik_level === l ? 'selected' : ''}>TOPIK ${l}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="form-row" style="margin-bottom:0.5rem">
                        <div style="flex:1">
                            <label style="font-size:0.8rem;color:var(--text-secondary)">품사 (POS)</label>
                            <select id="edit-pos">
                                <option value="">—</option>
                                ${['noun','verb','adjective','adverb','particle','determiner','interjection','suffix'].map(p =>
                                    `<option value="${p}" ${item.pos === p ? 'selected' : ''}>${this._posLabels[p]}</option>`
                                ).join('')}
                            </select>
                        </div>
                        <div style="flex:1">
                            <label style="font-size:0.8rem;color:var(--text-secondary)">사전형</label>
                            <input type="text" id="edit-dictionary-form" value="${this._escAttr(item.dictionary_form || '')}">
                        </div>
                    </div>
                    <div style="margin-bottom:0.5rem">
                        <label style="font-size:0.8rem;color:var(--text-secondary)">문법 카테고리</label>
                        <select id="edit-grammar-category">
                            <option value="">—</option>
                            ${['ending','particle','connector','expression','conjugation'].map(c =>
                                `<option value="${c}" ${item.grammar_category === c ? 'selected' : ''}>${this._grammarCatLabels[c]}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div style="margin-bottom:0.5rem">
                        <label style="font-size:0.8rem;color:var(--text-secondary)">메모</label>
                        <input type="text" id="edit-notes" value="${this._escAttr(item.notes || '')}">
                    </div>
                    <div style="display:flex;gap:0.5rem;margin-top:0.75rem">
                        <button class="btn btn-primary" id="edit-save" style="flex:1">저장</button>
                        <button class="btn btn-secondary" id="edit-delete" style="color:var(--error)">삭제</button>
                    </div>
                </div>`;

            // Examples section
            html += `
                <div class="card" style="margin-top:1rem">
                    <h4 style="margin-bottom:0.75rem">예문 (${item.examples.length})</h4>`;

            if (item.examples.length > 0) {
                for (const ex of item.examples) {
                    html += `
                        <div style="display:flex;justify-content:space-between;align-items:flex-start;padding:0.5rem 0;border-bottom:1px solid var(--border)">
                            <div>
                                <div style="font-size:0.95rem">${this._esc(ex.korean)}</div>
                                <div style="font-size:0.85rem;color:var(--text-secondary)">${this._esc(ex.english)}</div>
                                <span class="badge" style="margin-top:0.25rem">${formalityLabels[ex.formality] || ex.formality}</span>
                            </div>
                            <button class="btn btn-secondary example-delete-btn" data-example-id="${ex.id}" style="padding:0.25rem 0.5rem;font-size:0.8rem;color:var(--error)">X</button>
                        </div>`;
                }
            } else {
                html += `<p style="color:var(--text-secondary);font-size:0.85rem">예문이 없습니다</p>`;
            }

            html += `
                    <div style="margin-top:0.75rem;border-top:1px solid var(--border);padding-top:0.75rem">
                        <h5 style="font-size:0.85rem;margin-bottom:0.5rem">예문 추가</h5>
                        <input type="text" id="ex-korean" placeholder="한국어 문장">
                        <input type="text" id="ex-english" placeholder="영어 번역" style="margin-top:0.25rem">
                        <div class="form-row" style="margin-top:0.25rem">
                            <select id="ex-formality" style="flex:1">
                                <option value="polite">존댓말</option>
                                <option value="formal">격식체</option>
                                <option value="casual">반말</option>
                            </select>
                            <button class="btn btn-primary" id="ex-add-btn">추가</button>
                        </div>
                    </div>
                </div>`;

            // Mastery/SRS info
            if (item.mastery) {
                const m = item.mastery;
                const pct = Math.round((m.overall_score || 0) * 100);
                html += `
                    <div class="card" style="margin-top:1rem">
                        <h4 style="margin-bottom:0.5rem">학습 정보</h4>
                        <div style="font-size:0.85rem;line-height:1.8">
                            <div>숙달도: <strong>${pct}%</strong></div>
                            <div>연습 횟수: <strong>${m.practice_count}회</strong></div>
                            <div>문법: ${Math.round((m.grammar_score || 0) * 100)}% · 어휘: ${Math.round((m.vocab_score || 0) * 100)}% · 격식: ${Math.round((m.formality_score || 0) * 100)}%</div>
                        </div>
                    </div>`;
            }
            if (item.srs) {
                const s = item.srs;
                const nextReview = s.next_review ? new Date(s.next_review).toLocaleDateString('ko-KR') : '—';
                html += `
                    <div class="card" style="margin-top:0.5rem">
                        <div style="font-size:0.85rem;line-height:1.8">
                            <div>다음 복습: <strong>${nextReview}</strong></div>
                            <div>반복 횟수: ${s.repetitions} · 간격: ${Math.round(s.interval_days)}일</div>
                        </div>
                    </div>`;
            }

            el.innerHTML = html;

            // Event listeners
            document.getElementById('teacher-back').addEventListener('click', () => this.load());

            document.getElementById('edit-save').addEventListener('click', () => this._saveItem(itemId));
            document.getElementById('edit-delete').addEventListener('click', () => this._deleteItem(itemId));

            document.getElementById('ex-add-btn').addEventListener('click', () => this._addExample(itemId));

            el.querySelectorAll('.example-delete-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._deleteExample(itemId, parseInt(btn.dataset.exampleId));
                });
            });

        } catch (err) {
            el.innerHTML = `
                <button class="btn btn-secondary" id="teacher-back" style="margin-bottom:1rem">뒤로</button>
                <div class="card"><p class="error">${err.message}</p></div>`;
            document.getElementById('teacher-back').addEventListener('click', () => this.load());
        }
    },

    async _saveItem(itemId) {
        try {
            const data = {
                korean: document.getElementById('edit-korean').value.trim(),
                english: document.getElementById('edit-english').value.trim(),
                item_type: document.getElementById('edit-type').value,
                topik_level: parseInt(document.getElementById('edit-level').value),
                notes: document.getElementById('edit-notes').value.trim(),
            };
            const pos = document.getElementById('edit-pos').value;
            const dictForm = document.getElementById('edit-dictionary-form').value.trim();
            const gramCat = document.getElementById('edit-grammar-category').value;
            if (pos) data.pos = pos;
            if (dictForm) data.dictionary_form = dictForm;
            if (gramCat) data.grammar_category = gramCat;
            await API.updateItem(itemId, data);
            this._loadDetail(itemId);
        } catch (err) {
            alert('저장 오류: ' + err.message);
        }
    },

    async _deleteItem(itemId) {
        if (!confirm('이 항목을 삭제하시겠습니까?')) return;
        try {
            await API.deleteItem(itemId);
            this.load();
        } catch (err) {
            alert('삭제 오류: ' + err.message);
        }
    },

    async _addExample(itemId) {
        const korean = document.getElementById('ex-korean').value.trim();
        const english = document.getElementById('ex-english').value.trim();
        if (!korean || !english) return;

        try {
            await API.addExample(itemId, {
                korean, english,
                formality: document.getElementById('ex-formality').value,
            });
            this._loadDetail(itemId);
        } catch (err) {
            alert('예문 추가 오류: ' + err.message);
        }
    },

    async _deleteExample(itemId, exampleId) {
        try {
            await API.deleteExample(itemId, exampleId);
            this._loadDetail(itemId);
        } catch (err) {
            alert('예문 삭제 오류: ' + err.message);
        }
    },

    async _findDuplicates() {
        const area = document.getElementById('teacher-dup-area');
        if (!area.classList.contains('hidden')) {
            area.classList.add('hidden');
            return;
        }
        area.classList.remove('hidden');
        area.innerHTML = '<div class="loading"><div class="spinner"></div>중복 검색중...</div>';

        try {
            const data = await API.findDuplicates();
            if (data.groups.length === 0) {
                area.innerHTML = '<div class="card"><p style="color:var(--text-secondary)">중복 항목이 없습니다</p></div>';
                return;
            }

            let html = `<div class="card"><h4 style="margin-bottom:0.75rem">중복 항목 (${data.total_groups}개 그룹)</h4>`;
            for (let gi = 0; gi < data.groups.length; gi++) {
                const g = data.groups[gi];
                const matchLabel = g.match_type === 'exact' ? '동일' : '사전형 일치';
                html += `
                    <div style="padding:0.75rem 0;${gi > 0 ? 'border-top:2px solid var(--border);' : ''}">
                        <div style="font-size:0.8rem;color:var(--text-secondary);margin-bottom:0.5rem">
                            <span class="badge">${matchLabel}</span> "${this._esc(g.korean)}" — ${g.items.length}개 항목
                        </div>`;

                for (const item of g.items) {
                    const practices = item.total_practices || 0;
                    const examples = item.example_count || 0;
                    html += `
                        <div style="display:flex;justify-content:space-between;align-items:center;padding:0.25rem 0.5rem;margin-bottom:0.25rem;background:var(--bg-secondary);border-radius:6px">
                            <div style="flex:1">
                                <strong>${this._esc(item.korean)}</strong>
                                <span style="color:var(--text-secondary);margin-left:0.25rem">${this._esc(item.english)}</span>
                                <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.15rem">
                                    #${item.id} · T${item.topik_level} · ${this._sourceLabels[item.source] || item.source}
                                    ${practices > 0 ? ` · 연습 ${practices}회` : ''}
                                    ${examples > 0 ? ` · 예문 ${examples}개` : ''}
                                </div>
                            </div>
                            <div style="display:flex;gap:0.25rem">`;

                    // Show merge buttons for other items in the group (merge into this one)
                    const others = g.items.filter(i => i.id !== item.id);
                    for (const other of others) {
                        html += `<button class="btn btn-secondary merge-btn" data-keep="${item.id}" data-remove="${other.id}" style="padding:0.2rem 0.5rem;font-size:0.7rem">← #${other.id} 병합</button>`;
                    }
                    html += `</div></div>`;
                }
                html += `</div>`;
            }
            html += `</div>`;
            area.innerHTML = html;

            area.querySelectorAll('.merge-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const keepId = parseInt(btn.dataset.keep);
                    const removeId = parseInt(btn.dataset.remove);
                    if (!confirm(`#${removeId}을(를) #${keepId}에 병합하시겠습니까? #${removeId}은(는) 삭제됩니다.`)) return;
                    try {
                        await API.mergeItems(keepId, removeId);
                        this._findDuplicates();
                        // Re-open after merge to refresh
                        const area2 = document.getElementById('teacher-dup-area');
                        area2.classList.add('hidden');
                        this._findDuplicates();
                    } catch (err) {
                        alert('병합 오류: ' + err.message);
                    }
                });
            });
        } catch (err) {
            area.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async _loadSentences() {
        const container = document.getElementById('teacher-sentences');
        if (!container) return;
        try {
            const data = await API.getSentences({ per_page: 20 });
            const sentences = data.sentences || [];
            let html = `
                <div class="card">
                    <h4 style="margin-bottom:0.75rem">문장 관리 (${data.total || 0})</h4>`;

            if (sentences.length > 0) {
                for (const s of sentences) {
                    html += `
                        <div style="padding:0.5rem 0;border-bottom:1px solid var(--border)">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start">
                                <div style="flex:1;cursor:pointer" class="sentence-row" data-sentence-id="${s.id}">
                                    <div style="font-size:0.95rem">${this._esc(s.korean)}</div>
                                    <div style="font-size:0.85rem;color:var(--text-secondary)">${this._esc(s.english)}</div>
                                    <div class="item-meta" style="margin-top:0.25rem">
                                        <span class="badge badge-level">TOPIK ${s.topik_level}</span>
                                        <span class="badge">${this._formalityLabels[s.formality] || s.formality}</span>
                                        ${s.linked_item_count > 0 ? `<span class="badge">항목 ${s.linked_item_count}개</span>` : ''}
                                    </div>
                                </div>
                                <button class="btn btn-secondary sentence-delete-btn" data-sentence-id="${s.id}" style="padding:0.25rem 0.5rem;font-size:0.8rem;color:var(--error)">X</button>
                            </div>
                        </div>`;
                }
            } else {
                html += `<p style="color:var(--text-secondary);font-size:0.85rem">문장이 없습니다</p>`;
            }

            html += `
                    <div style="margin-top:0.75rem;border-top:1px solid var(--border);padding-top:0.75rem">
                        <h5 style="font-size:0.85rem;margin-bottom:0.5rem">문장 추가</h5>
                        <input type="text" id="sentence-korean" placeholder="한국어 문장">
                        <input type="text" id="sentence-english" placeholder="영어 번역 (비워두면 자동 번역)" style="margin-top:0.25rem">
                        <div class="form-row" style="margin-top:0.25rem">
                            <select id="sentence-formality" style="flex:1">
                                <option value="polite">존댓말</option>
                                <option value="formal">격식체</option>
                                <option value="casual">반말</option>
                            </select>
                            <button class="btn btn-primary" id="sentence-add-btn">추가</button>
                        </div>
                        <div id="sentence-add-result" class="hidden" style="margin-top:0.5rem;font-size:0.85rem"></div>
                    </div>
                </div>`;
            container.innerHTML = html;

            document.getElementById('sentence-add-btn')?.addEventListener('click', () => this._addSentence());
            container.querySelectorAll('.sentence-delete-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this._deleteSentence(parseInt(btn.dataset.sentenceId));
                });
            });
            container.querySelectorAll('.sentence-row').forEach(row => {
                row.addEventListener('click', () => this._loadSentenceDetail(parseInt(row.dataset.sentenceId)));
            });
        } catch (err) {
            container.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async _addSentence() {
        const korean = document.getElementById('sentence-korean').value.trim();
        if (!korean) return;
        const english = document.getElementById('sentence-english').value.trim();
        const formality = document.getElementById('sentence-formality').value;

        const btn = document.getElementById('sentence-add-btn');
        btn.disabled = true;
        btn.textContent = '처리중...';
        const resultDiv = document.getElementById('sentence-add-result');

        try {
            const result = await API.createSentence({ korean, english, formality });
            resultDiv.classList.remove('hidden');
            const linkedNames = (result.linked_items || []).map(i => i.korean).join(', ');
            resultDiv.innerHTML = `
                <div style="color:var(--success)">
                    추가됨! TOPIK ${result.topik_level}
                    ${result.english ? `<br>번역: ${this._esc(result.english)}` : ''}
                    ${linkedNames ? `<br>연결된 항목: ${this._esc(linkedNames)}` : ''}
                </div>`;
            document.getElementById('sentence-korean').value = '';
            document.getElementById('sentence-english').value = '';
            setTimeout(() => this._loadSentences(), 2000);
        } catch (err) {
            resultDiv.classList.remove('hidden');
            resultDiv.innerHTML = `<div style="color:var(--error)">오류: ${err.message}</div>`;
        } finally {
            btn.disabled = false;
            btn.textContent = '추가';
        }
    },

    async _deleteSentence(sentenceId) {
        if (!confirm('이 문장을 삭제하시겠습니까?')) return;
        try {
            await API.deleteSentence(sentenceId);
            this._loadSentences();
        } catch (err) {
            alert('삭제 오류: ' + err.message);
        }
    },

    async _loadSentenceDetail(sentenceId) {
        const container = document.getElementById('teacher-sentences');
        container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
        try {
            const [s, bd] = await Promise.all([
                API.getSentence(sentenceId),
                API.getSentenceBreakdown(sentenceId),
            ]);

            let html = `
                <div class="card">
                    <button class="btn btn-secondary" id="sentence-back" style="margin-bottom:0.75rem">뒤로</button>
                    <div style="font-size:1.1rem;margin-bottom:0.25rem">${this._esc(s.korean)}</div>
                    <div style="font-size:0.9rem;color:var(--text-secondary);margin-bottom:0.5rem">${this._esc(s.english)}</div>
                    <div class="item-meta">
                        <span class="badge badge-level">TOPIK ${s.topik_level}</span>
                        <span class="badge">${this._formalityLabels[s.formality] || s.formality}</span>
                        <span class="badge">${this._sourceLabels[s.source] || s.source}</span>
                    </div>
                    ${s.notes ? `<p style="font-size:0.85rem;margin-top:0.5rem;color:var(--text-secondary)">${this._esc(s.notes)}</p>` : ''}

                    <h5 style="margin-top:1rem;margin-bottom:0.5rem;font-size:0.85rem">문장 분석</h5>
                    <div style="display:flex;flex-wrap:wrap;gap:0.25rem;margin-bottom:0.75rem;line-height:2.2">`;

            // Render word-by-word breakdown
            for (const token of bd.breakdown) {
                if (token.type === 'separator') {
                    html += `<span>${this._esc(token.text)}</span>`;
                } else if (token.match) {
                    const m = token.match;
                    const bgColor = m.linked ? 'var(--primary)' : '#6c757d';
                    const levelColor = ['','#4CAF50','#8BC34A','#FFC107','#FF9800','#FF5722','#9C27B0'][m.topik_level] || '#999';
                    html += `
                        <span class="breakdown-word" data-item-id="${m.id}"
                              style="display:inline-block;position:relative;cursor:pointer;
                                     background:${bgColor}15;border-bottom:2px solid ${bgColor};
                                     padding:0.15rem 0.35rem;border-radius:4px;font-size:1rem;
                                     transition:background 0.15s"
                              onmouseenter="this.style.background='${bgColor}25'"
                              onmouseleave="this.style.background='${bgColor}15'">
                            ${this._esc(token.text)}
                            <span style="position:absolute;top:-0.4rem;right:-0.2rem;font-size:0.55rem;
                                         background:${levelColor};color:white;border-radius:50%;
                                         width:14px;height:14px;display:flex;align-items:center;
                                         justify-content:center;font-weight:700">${m.topik_level}</span>
                        </span>`;
                } else {
                    html += `<span style="display:inline-block;padding:0.15rem 0.35rem;font-size:1rem;
                                          color:var(--text-secondary);border-bottom:2px solid transparent">${this._esc(token.text)}</span>`;
                }
            }

            html += `</div>
                    <div id="word-detail" style="min-height:2rem;font-size:0.85rem;color:var(--text-secondary)">
                        단어를 클릭하면 상세 정보가 표시됩니다
                    </div>

                    <h5 style="margin-top:1rem;margin-bottom:0.5rem;font-size:0.85rem">연결된 항목 (${s.linked_items.length})</h5>`;
            if (s.linked_items.length > 0) {
                for (const li of s.linked_items) {
                    html += `
                        <div style="display:flex;justify-content:space-between;align-items:center;padding:0.25rem 0">
                            <span>${this._esc(li.korean)} — ${this._esc(li.english)}</span>
                            <button class="btn btn-secondary unlink-btn" data-item-id="${li.id}" style="padding:0.15rem 0.4rem;font-size:0.75rem;color:var(--error)">해제</button>
                        </div>`;
                }
            } else {
                html += `<p style="font-size:0.85rem;color:var(--text-secondary)">연결된 항목이 없습니다</p>`;
            }
            html += `</div>`;
            container.innerHTML = html;

            document.getElementById('sentence-back').addEventListener('click', () => this._loadSentences());
            container.querySelectorAll('.unlink-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    await API.unlinkSentenceItem(sentenceId, parseInt(btn.dataset.itemId));
                    this._loadSentenceDetail(sentenceId);
                });
            });

            // Word click handlers — show detail in #word-detail
            const breakdownData = {};
            for (const token of bd.breakdown) {
                if (token.match) breakdownData[token.match.id] = token;
            }
            container.querySelectorAll('.breakdown-word').forEach(el => {
                el.addEventListener('click', () => {
                    const itemId = parseInt(el.dataset.itemId);
                    const token = breakdownData[itemId];
                    if (!token || !token.match) return;
                    const m = token.match;
                    const posLabel = m.pos ? (this._posLabels[m.pos] || m.pos) : '—';
                    const detailEl = document.getElementById('word-detail');
                    detailEl.innerHTML = `
                        <div style="padding:0.5rem;background:var(--bg-secondary);border-radius:6px">
                            <div style="font-size:1rem"><strong>${this._esc(m.korean)}</strong> → ${this._esc(m.english)}</div>
                            <div style="margin-top:0.25rem">
                                <span class="badge badge-level">TOPIK ${m.topik_level}</span>
                                <span class="badge">${m.item_type === 'vocab' ? '단어' : '문법'}</span>
                                ${posLabel !== '—' ? `<span class="badge badge-pos">${posLabel}</span>` : ''}
                                ${m.dictionary_form ? `<span class="badge">사전형: ${this._esc(m.dictionary_form)}</span>` : ''}
                                ${m.linked ? '<span class="badge" style="background:var(--primary);color:white">연결됨</span>' : '<span class="badge">미연결</span>'}
                            </div>
                        </div>`;
                });
            });
        } catch (err) {
            container.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    async _loadStudents() {
        const container = document.getElementById('teacher-students');
        if (!container) return;
        try {
            const [studentsData, overview] = await Promise.all([
                API.getStudents(),
                API.getTeacherOverview(),
            ]);
            const students = studentsData.students || [];
            const overviewMap = {};
            for (const s of (overview.students || [])) {
                overviewMap[s.id] = s;
            }

            let html = `
                <div class="card">
                    <h4 style="margin-bottom:0.75rem">학생 관리 / 현황</h4>
                    <div style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0.75rem">
                        전체 항목: ${overview.total_items}개
                    </div>`;

            if (students.length > 0) {
                for (const s of students) {
                    const ov = overviewMap[s.id] || {};
                    const level = ov.estimated_level ? ov.estimated_level.toFixed(1) : '—';
                    const avgScore = ov.recent_avg_score != null ? Math.round(ov.recent_avg_score * 100) + '%' : '—';
                    const lastPractice = ov.last_practice ? this._relativeTime(ov.last_practice) : '없음';
                    const m = ov.mastery || {};
                    const masteredPct = (m.mastered && (m.mastered + m.learning + m.struggling + m.unseen) > 0)
                        ? Math.round(m.mastered / (m.mastered + m.learning + m.struggling + m.unseen) * 100)
                        : 0;
                    const scoreClass = ov.recent_avg_score >= 0.8 ? 'score-high' :
                                       ov.recent_avg_score >= 0.5 ? 'score-mid' : 'score-low';

                    html += `
                        <div style="padding:0.75rem 0;border-bottom:1px solid var(--border)">
                            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                                <div>
                                    <strong>${this._esc(s.display_name)}</strong>
                                    <span style="font-size:0.8rem;color:var(--text-secondary);margin-left:0.5rem">@${this._esc(s.username)}</span>
                                </div>
                                <button class="btn btn-secondary student-delete-btn" data-student-id="${s.id}" style="padding:0.2rem 0.5rem;font-size:0.75rem;color:var(--error)">삭제</button>
                            </div>
                            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;font-size:0.8rem">
                                <div style="text-align:center;padding:0.4rem;background:var(--bg-secondary);border-radius:6px">
                                    <div style="font-size:1.1rem;font-weight:700">T${level}</div>
                                    <div style="color:var(--text-secondary)">수준</div>
                                </div>
                                <div style="text-align:center;padding:0.4rem;background:var(--bg-secondary);border-radius:6px">
                                    <div style="font-size:1.1rem;font-weight:700" class="${ov.recent_avg_score != null ? scoreClass : ''}">${avgScore}</div>
                                    <div style="color:var(--text-secondary)">최근 점수</div>
                                </div>
                                <div style="text-align:center;padding:0.4rem;background:var(--bg-secondary);border-radius:6px">
                                    <div style="font-size:1.1rem;font-weight:700">${ov.due_for_review || 0}</div>
                                    <div style="color:var(--text-secondary)">복습 대기</div>
                                </div>
                            </div>
                            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;font-size:0.8rem;margin-top:0.5rem">
                                <div style="text-align:center;padding:0.4rem;background:var(--bg-secondary);border-radius:6px">
                                    <div style="font-size:1.1rem;font-weight:700">${ov.recent_practices || 0}<span style="font-size:0.7rem;font-weight:400">/${ov.total_practices || 0}</span></div>
                                    <div style="color:var(--text-secondary)">연습 (7일/전체)</div>
                                </div>
                                <div style="text-align:center;padding:0.4rem;background:var(--bg-secondary);border-radius:6px">
                                    <div style="font-size:1.1rem;font-weight:700">${ov.items_encountered || 0}</div>
                                    <div style="color:var(--text-secondary)">접한 항목</div>
                                </div>
                                <div style="text-align:center;padding:0.4rem;background:var(--bg-secondary);border-radius:6px">
                                    <div style="font-size:1.1rem;font-weight:700">${masteredPct}%</div>
                                    <div style="color:var(--text-secondary)">숙달</div>
                                </div>
                            </div>
                            ${ov.mastery ? `
                            <div style="display:flex;height:6px;border-radius:3px;overflow:hidden;margin-top:0.5rem;background:var(--border)">
                                <div style="width:${masteredPct}%;background:var(--success)"></div>
                                <div style="width:${m.mastered+m.learning+m.struggling+m.unseen > 0 ? Math.round(m.learning/(m.mastered+m.learning+m.struggling+m.unseen)*100) : 0}%;background:var(--primary)"></div>
                                <div style="width:${m.mastered+m.learning+m.struggling+m.unseen > 0 ? Math.round(m.struggling/(m.mastered+m.learning+m.struggling+m.unseen)*100) : 0}%;background:var(--error)"></div>
                            </div>
                            <div style="display:flex;gap:0.75rem;font-size:0.7rem;color:var(--text-secondary);margin-top:0.25rem">
                                <span style="color:var(--success)">${m.mastered} 숙달</span>
                                <span style="color:var(--primary)">${m.learning} 학습중</span>
                                <span style="color:var(--error)">${m.struggling} 어려움</span>
                                <span>${m.unseen} 미학습</span>
                            </div>` : ''}
                            <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.35rem">
                                마지막 연습: ${lastPractice}
                            </div>
                        </div>`;
                }
            } else {
                html += `<p style="color:var(--text-secondary);font-size:0.85rem">학생이 없습니다</p>`;
            }
            html += `
                    <div style="margin-top:0.75rem;border-top:1px solid var(--border);padding-top:0.75rem">
                        <h5 style="font-size:0.85rem;margin-bottom:0.5rem">학생 추가</h5>
                        <input type="text" id="student-username" placeholder="사용자 이름">
                        <input type="text" id="student-displayname" placeholder="표시 이름" style="margin-top:0.25rem">
                        <input type="password" id="student-password" placeholder="비밀번호" style="margin-top:0.25rem">
                        <button class="btn btn-primary btn-block" id="student-add-btn" style="margin-top:0.5rem">추가</button>
                    </div>
                </div>`;
            container.innerHTML = html;

            document.getElementById('student-add-btn')?.addEventListener('click', () => this._addStudent());
            container.querySelectorAll('.student-delete-btn').forEach(btn => {
                btn.addEventListener('click', () => this._deleteStudent(parseInt(btn.dataset.studentId)));
            });
        } catch (err) {
            container.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    _relativeTime(dateStr) {
        const now = new Date();
        const d = new Date(dateStr);
        const diffMs = now - d;
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return '방금 전';
        if (diffMin < 60) return `${diffMin}분 전`;
        const diffHrs = Math.floor(diffMin / 60);
        if (diffHrs < 24) return `${diffHrs}시간 전`;
        const diffDays = Math.floor(diffHrs / 24);
        if (diffDays < 7) return `${diffDays}일 전`;
        return d.toLocaleDateString('ko-KR');
    },

    async _addStudent() {
        const username = document.getElementById('student-username').value.trim();
        const displayName = document.getElementById('student-displayname').value.trim();
        const password = document.getElementById('student-password').value;
        if (!username || !displayName || !password) return;
        try {
            await API.createStudent({ username, display_name: displayName, password });
            this._loadStudents();
        } catch (err) {
            alert('학생 추가 오류: ' + err.message);
        }
    },

    async _deleteStudent(studentId) {
        if (!confirm('이 학생을 삭제하시겠습니까?')) return;
        try {
            await API.deleteStudent(studentId);
            this._loadStudents();
        } catch (err) {
            alert('학생 삭제 오류: ' + err.message);
        }
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },

    _escAttr(str) {
        return (str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },

    _debounce(fn, ms) {
        let t;
        return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
    },
};
