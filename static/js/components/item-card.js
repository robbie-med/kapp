const ItemCard = {
    render(item, showMastery = true) {
        const masteryPct = item.overall_score != null ? Math.round(item.overall_score * 100) : null;
        const masteryColor = masteryPct === null ? '#E0E6ED' :
                            masteryPct >= 80 ? '#4CAF50' :
                            masteryPct >= 50 ? '#FF9800' : '#F44336';

        const posLabel = item.pos ? `<span class="badge badge-pos">${item.pos}</span>` : '';
        const dictForm = item.dictionary_form ? `<span class="item-dict-form">${this._esc(item.dictionary_form)}</span>` : '';

        return `
            <div class="card item-card" data-item-id="${item.id}">
                <div>
                    <div class="item-korean">${this._esc(item.korean)}${dictForm ? ` <span style="font-size:0.75rem;color:var(--text-secondary)">(${dictForm})</span>` : ''}</div>
                    <div class="item-english">${this._esc(item.english)}</div>
                    <div class="item-meta">
                        <span class="badge badge-level">TOPIK ${item.topik_level}</span>
                        <span class="badge badge-type">${item.item_type}</span>
                        ${posLabel}
                        ${item.grammar_category ? `<span class="badge">${item.grammar_category}</span>` : ''}
                        ${item.source && item.source !== 'seed' ? `<span class="badge">${item.source}</span>` : ''}
                    </div>
                </div>
                ${showMastery && masteryPct !== null ? `
                    <div class="mastery-ring" style="background: ${masteryColor}20; color: ${masteryColor}">
                        ${masteryPct}%
                    </div>` : ''}
            </div>`;
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },
};
