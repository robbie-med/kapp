const FeedbackComponent = {
    render(result) {
        const scoreClass = result.overall_score >= 0.8 ? 'score-high' :
                          result.overall_score >= 0.5 ? 'score-mid' : 'score-low';
        const scorePct = Math.round(result.overall_score * 100);

        let html = `
            <div class="feedback-section">
                <div style="text-align:center">
                    <span class="score-badge ${scoreClass}">${scorePct}%</span>
                </div>

                <div class="transcript-box card">
                    <h4 style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0.25rem">You said:</h4>
                    <p style="font-size:1rem">${this._esc(result.transcript)}</p>
                </div>

                <div class="card">
                    <h4 style="margin-bottom:0.5rem">Grammar</h4>
                    ${result.grammar.map(g => this._feedbackItem(g.point, g.status, g.explanation)).join('')}
                </div>

                <div class="card">
                    <h4 style="margin-bottom:0.5rem">Vocabulary</h4>
                    ${result.vocabulary.map(v => this._feedbackItem(v.word, v.status, v.explanation)).join('')}
                </div>

                <div class="card">
                    <h4 style="margin-bottom:0.5rem">Formality</h4>
                    <p style="font-size:0.85rem">Expected: <strong>${result.formality.expected}</strong> | Detected: <strong>${result.formality.detected}</strong></p>
                    ${result.formality.issues.length > 0 ?
                        result.formality.issues.map(i => `<p style="font-size:0.85rem;color:var(--warning);margin-top:0.25rem">${this._esc(i)}</p>`).join('') :
                        '<p style="font-size:0.85rem;color:var(--success);margin-top:0.25rem">Formality level correct!</p>'}
                </div>

                <div class="correction-box">
                    <h4>Corrected</h4>
                    <p>${this._esc(result.corrected_sentence)}</p>
                </div>
                <div class="correction-box" style="background:#E8EAF6;margin-top:0.5rem">
                    <h4>Natural alternative</h4>
                    <p>${this._esc(result.natural_alternative)}</p>
                </div>

                <div class="card" style="margin-top:0.75rem">
                    <p style="font-size:0.9rem;line-height:1.5">${this._esc(result.explanation)}</p>
                </div>
            </div>`;
        return html;
    },

    _feedbackItem(point, status, explanation) {
        return `
            <div class="feedback-item">
                <div class="feedback-status status-${status}"></div>
                <div class="feedback-text">
                    <div class="feedback-point">${this._esc(point)}</div>
                    <div class="feedback-explanation">${this._esc(explanation)}</div>
                </div>
            </div>`;
    },

    _esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    },
};
