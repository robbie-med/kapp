const SettingsPage = {
    async load() {
        const el = document.getElementById('page-settings');
        el.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

        try {
            const settings = await API.getSettings();
            const keySet = settings.openai_api_key_set;
            const maskedKey = settings.openai_api_key || '';
            const tgTokenSet = settings.telegram_bot_token_set;
            const maskedTgToken = settings.telegram_bot_token || '';

            el.innerHTML = `
                <div class="card">
                    <h4 style="margin-bottom:0.75rem">API Configuration</h4>
                    <div class="api-key-section">
                        <label class="setting-label" style="display:block;margin-bottom:0.35rem">OpenAI API Key</label>
                        <div class="api-key-status ${keySet ? 'key-active' : 'key-missing'}">
                            ${keySet ? '&#10003; Key configured' : '&#10007; No key set — practice features won\'t work'}
                        </div>
                        <div class="api-key-input-row">
                            <input type="password" id="api-key-input"
                                   placeholder="${keySet ? maskedKey : 'sk-...'}"
                                   autocomplete="off" spellcheck="false">
                            <button class="btn btn-secondary" id="api-key-toggle" title="Show/hide">&#128065;</button>
                        </div>
                        <div style="display:flex;gap:0.5rem;margin-top:0.5rem">
                            <button class="btn btn-primary" id="api-key-save" style="flex:1">Save Key</button>
                            <button class="btn btn-secondary" id="api-key-test">Test</button>
                        </div>
                        <div id="api-key-msg" class="api-key-msg hidden"></div>
                    </div>
                </div>

                <div class="card" style="margin-top:1rem">
                    <h4 style="margin-bottom:0.75rem">Practice Settings</h4>
                    <div class="setting-row">
                        <span class="setting-label">Default Formality</span>
                        <select id="setting-formality" data-key="default_formality">
                            <option value="formal" ${settings.default_formality === 'formal' ? 'selected' : ''}>Formal</option>
                            <option value="polite" ${settings.default_formality === 'polite' ? 'selected' : ''}>Polite</option>
                            <option value="casual" ${settings.default_formality === 'casual' ? 'selected' : ''}>Casual</option>
                        </select>
                    </div>
                    <div class="setting-row">
                        <span class="setting-label">Default TOPIK Level</span>
                        <select id="setting-level" data-key="default_topik_level">
                            ${[1,2,3,4,5,6].map(l => `<option value="${l}" ${settings.default_topik_level == l ? 'selected' : ''}>Level ${l}</option>`).join('')}
                        </select>
                    </div>
                    <div class="setting-row">
                        <span class="setting-label">Items per Session</span>
                        <select id="setting-count" data-key="items_per_session">
                            ${[1,2,3,4,5].map(n => `<option value="${n}" ${settings.items_per_session == n ? 'selected' : ''}>${n}</option>`).join('')}
                        </select>
                    </div>
                    <div class="setting-row">
                        <span class="setting-label">New Items per Session</span>
                        <select id="setting-new-items" data-key="new_items_per_session">
                            ${[1,2,3,4,5,7,10].map(n => `<option value="${n}" ${settings.new_items_per_session == n ? 'selected' : ''}>${n}</option>`).join('')}
                        </select>
                    </div>
                    <div class="setting-row">
                        <span class="setting-label">Curriculum Order</span>
                        <select id="setting-curriculum" data-key="curriculum_enabled">
                            <option value="true" ${settings.curriculum_enabled !== 'false' ? 'selected' : ''}>Enabled (TOPIK order)</option>
                            <option value="false" ${settings.curriculum_enabled === 'false' ? 'selected' : ''}>Disabled (random)</option>
                        </select>
                    </div>
                </div>

                <div class="card" style="margin-top:1rem">
                    <h4 style="margin-bottom:0.75rem">Telegram Bot</h4>
                    <div id="telegram-status" class="api-key-status key-missing">Checking...</div>

                    <label class="setting-label" style="display:block;margin-top:0.75rem;margin-bottom:0.35rem">Bot Token</label>
                    <div class="api-key-input-row">
                        <input type="password" id="telegram-token-input"
                               placeholder="${tgTokenSet ? maskedTgToken : 'Paste token from @BotFather'}"
                               autocomplete="off" spellcheck="false">
                        <button class="btn btn-secondary" id="telegram-token-toggle" title="Show/hide">&#128065;</button>
                    </div>

                    <label class="setting-label" style="display:block;margin-top:0.75rem;margin-bottom:0.35rem">Teacher Chat ID</label>
                    <input type="text" id="telegram-teacher-input" class="setting-input"
                           placeholder="Numeric Telegram user ID"
                           value="${settings.telegram_teacher_id || ''}"
                           autocomplete="off" style="width:100%;padding:0.5rem;border:1px solid var(--border);border-radius:6px;font-size:0.95rem">

                    <div style="display:flex;gap:0.5rem;margin-top:0.75rem">
                        <button class="btn btn-primary" id="telegram-save" style="flex:1">Save &amp; Connect</button>
                    </div>
                    <div id="telegram-msg" class="api-key-msg hidden"></div>

                    <details style="margin-top:1rem">
                        <summary style="cursor:pointer;font-weight:600;font-size:0.9rem">Setup Instructions</summary>
                        <div style="font-size:0.85rem;margin-top:0.5rem;color:var(--text-secondary);line-height:1.6">
                            <ol style="padding-left:1.2rem;margin:0">
                                <li>Open Telegram and message <strong>@BotFather</strong></li>
                                <li>Send <code>/newbot</code> and follow the prompts to create a bot</li>
                                <li>Copy the bot token and paste it above</li>
                                <li>To find your Teacher Chat ID, message <strong>@userinfobot</strong> on Telegram — it replies with your numeric ID</li>
                                <li>Click <strong>Save &amp; Connect</strong></li>
                                <li>Share the bot link with your teacher so they can message it</li>
                            </ol>
                            <p style="margin:0.75rem 0 0.25rem;font-weight:600">Teacher message formats:</p>
                            <ul style="padding-left:1.2rem;margin:0">
                                <li><code>새 단어: 행복하다 - to be happy</code></li>
                                <li><code>문법: -고 싶다 - want to</code></li>
                                <li><code>vocab: 사랑 - love</code></li>
                                <li><code>행복하다 - to be happy</code></li>
                                <li>Or just describe items naturally — AI will parse them</li>
                            </ul>
                        </div>
                    </details>
                </div>

                <div class="card" style="margin-top:1rem">
                    <h4 style="margin-bottom:0.75rem">Signal Bot</h4>
                    <div id="signal-status" class="api-key-status key-missing">Not configured</div>

                    <label class="setting-label" style="display:block;margin-top:0.75rem;margin-bottom:0.35rem">Teacher Phone Number</label>
                    <input type="text" id="signal-teacher-input" class="setting-input"
                           placeholder="+1234567890"
                           value="${settings.signal_teacher_number || ''}"
                           autocomplete="off" style="width:100%;padding:0.5rem;border:1px solid var(--border);border-radius:6px;font-size:0.95rem">

                    <label class="setting-label" style="display:block;margin-top:0.75rem;margin-bottom:0.35rem">Signal Phone Number (bot's number)</label>
                    <input type="text" id="signal-phone-input" class="setting-input"
                           placeholder="+1234567890"
                           value="${settings.signal_phone_number || ''}"
                           autocomplete="off" style="width:100%;padding:0.5rem;border:1px solid var(--border);border-radius:6px;font-size:0.95rem">

                    <label class="setting-label" style="display:block;margin-top:0.75rem;margin-bottom:0.35rem">Signal API URL</label>
                    <input type="text" id="signal-api-input" class="setting-input"
                           placeholder="http://localhost:8101"
                           value="${settings.signal_api_url || ''}"
                           autocomplete="off" style="width:100%;padding:0.5rem;border:1px solid var(--border);border-radius:6px;font-size:0.95rem">

                    <div style="display:flex;gap:0.5rem;margin-top:0.75rem">
                        <button class="btn btn-primary" id="signal-save" style="flex:1">Save</button>
                        <button class="btn btn-secondary" id="signal-test">Test Connection</button>
                    </div>
                    <div id="signal-msg" class="api-key-msg hidden"></div>

                    <details style="margin-top:1rem">
                        <summary style="cursor:pointer;font-weight:600;font-size:0.9rem">Setup Instructions</summary>
                        <div style="font-size:0.85rem;margin-top:0.5rem;color:var(--text-secondary);line-height:1.6">
                            <ol style="padding-left:1.2rem;margin:0">
                                <li>Run <code>docker-compose up -d</code> to start signal-cli-rest-api</li>
                                <li>Register or link a phone number with the Signal API</li>
                                <li>Enter the registered number as "Signal Phone Number" above</li>
                                <li>Enter your teacher's Signal number as "Teacher Phone Number"</li>
                                <li>The API URL defaults to <code>http://localhost:8101</code></li>
                                <li>Click <strong>Test Connection</strong> to verify</li>
                            </ol>
                            <p style="margin:0.75rem 0 0.25rem;font-weight:600">Same message formats as Telegram apply.</p>
                        </div>
                    </details>
                </div>

                <div class="card" style="margin-top:1rem">
                    <button class="btn btn-secondary btn-block" id="logout-btn">Logout</button>
                </div>`;

            this._bindEvents(el);
            this._loadBotStatus(settings);
        } catch (err) {
            el.innerHTML = `<div class="card"><p class="error">${err.message}</p></div>`;
        }
    },

    _loadBotStatus(settings) {
        // Fetch Telegram bot status
        API.get('/api/settings/bots/status').then(status => {
            const tgEl = document.getElementById('telegram-status');
            if (tgEl) {
                if (status.telegram?.running) {
                    tgEl.className = 'api-key-status key-active';
                    tgEl.innerHTML = '&#10003; Bot is running';
                } else {
                    tgEl.className = 'api-key-status key-missing';
                    tgEl.innerHTML = '&#10007; Bot is not running';
                }
            }
        }).catch(() => {});

        // Signal status based on config
        const sigEl = document.getElementById('signal-status');
        if (sigEl) {
            if (settings.signal_teacher_number && settings.signal_phone_number) {
                sigEl.className = 'api-key-status key-active';
                sigEl.innerHTML = '&#10003; Configured (webhook-based)';
            } else {
                sigEl.className = 'api-key-status key-missing';
                sigEl.innerHTML = '&#10007; Not configured';
            }
        }
    },

    _bindEvents(el) {
        // API key show/hide toggle
        const keyInput = document.getElementById('api-key-input');
        document.getElementById('api-key-toggle').addEventListener('click', () => {
            keyInput.type = keyInput.type === 'password' ? 'text' : 'password';
        });

        // Save key
        document.getElementById('api-key-save').addEventListener('click', async () => {
            const val = keyInput.value.trim();
            if (!val) return this._showMsg('api-key-msg', 'Enter an API key first', 'error');
            if (!val.startsWith('sk-')) return this._showMsg('api-key-msg', 'Key should start with sk-', 'error');

            try {
                await API.updateSetting('openai_api_key', val);
                keyInput.value = '';
                this._showMsg('api-key-msg', 'Key saved successfully', 'success');
                setTimeout(() => this.load(), 1500);
            } catch (err) {
                this._showMsg('api-key-msg', 'Failed to save: ' + err.message, 'error');
            }
        });

        // Test key
        document.getElementById('api-key-test').addEventListener('click', async () => {
            this._showMsg('api-key-msg', 'Testing...', 'info');
            try {
                const val = keyInput.value.trim();
                if (val) {
                    if (!val.startsWith('sk-')) return this._showMsg('api-key-msg', 'Key should start with sk-', 'error');
                    await API.updateSetting('openai_api_key', val);
                }
                const result = await API.post('/api/settings/openai-key/test');
                if (result.ok) {
                    this._showMsg('api-key-msg', 'Key is valid!', 'success');
                    if (val) setTimeout(() => this.load(), 1500);
                } else {
                    this._showMsg('api-key-msg', 'Invalid: ' + result.message, 'error');
                }
            } catch (err) {
                this._showMsg('api-key-msg', 'Test failed: ' + err.message, 'error');
            }
        });

        // Practice settings
        el.querySelectorAll('select[data-key]').forEach(sel => {
            sel.addEventListener('change', async () => {
                try {
                    await API.updateSetting(sel.dataset.key, sel.value);
                } catch (err) {
                    alert('Failed to save setting: ' + err.message);
                }
            });
        });

        // --- Telegram ---
        const tgTokenInput = document.getElementById('telegram-token-input');
        document.getElementById('telegram-token-toggle').addEventListener('click', () => {
            tgTokenInput.type = tgTokenInput.type === 'password' ? 'text' : 'password';
        });

        document.getElementById('telegram-save').addEventListener('click', async () => {
            const token = tgTokenInput.value.trim();
            const teacherId = document.getElementById('telegram-teacher-input').value.trim();

            if (!token && !teacherId) {
                return this._showMsg('telegram-msg', 'Enter a bot token or teacher ID', 'error');
            }

            try {
                if (token) await API.updateSetting('telegram_bot_token', token);
                if (teacherId) await API.updateSetting('telegram_teacher_id', teacherId);
                this._showMsg('telegram-msg', 'Saving and restarting bot...', 'info');
                const result = await API.post('/api/settings/telegram/restart');
                if (result.running) {
                    this._showMsg('telegram-msg', 'Bot connected!', 'success');
                    setTimeout(() => this.load(), 1500);
                } else {
                    this._showMsg('telegram-msg', 'Settings saved but bot did not start — check your token', 'error');
                    setTimeout(() => this.load(), 2000);
                }
            } catch (err) {
                this._showMsg('telegram-msg', 'Failed: ' + err.message, 'error');
            }
        });

        // --- Signal ---
        document.getElementById('signal-save').addEventListener('click', async () => {
            const teacher = document.getElementById('signal-teacher-input').value.trim();
            const phone = document.getElementById('signal-phone-input').value.trim();
            const apiUrl = document.getElementById('signal-api-input').value.trim();
            try {
                if (teacher) await API.updateSetting('signal_teacher_number', teacher);
                if (phone) await API.updateSetting('signal_phone_number', phone);
                if (apiUrl) await API.updateSetting('signal_api_url', apiUrl);
                this._showMsg('signal-msg', 'Signal settings saved', 'success');
                setTimeout(() => this.load(), 1500);
            } catch (err) {
                this._showMsg('signal-msg', 'Failed: ' + err.message, 'error');
            }
        });

        document.getElementById('signal-test').addEventListener('click', async () => {
            this._showMsg('signal-msg', 'Testing...', 'info');
            const apiUrl = document.getElementById('signal-api-input').value.trim();
            try {
                if (apiUrl) await API.updateSetting('signal_api_url', apiUrl);
                const result = await API.post('/api/settings/signal/test');
                if (result.ok) {
                    this._showMsg('signal-msg', result.message, 'success');
                } else {
                    this._showMsg('signal-msg', result.message, 'error');
                }
            } catch (err) {
                this._showMsg('signal-msg', 'Test failed: ' + err.message, 'error');
            }
        });

        // Logout
        document.getElementById('logout-btn').addEventListener('click', async () => {
            await API.logout();
            App.showLogin();
        });
    },

    _showMsg(elementId, text, type) {
        const msg = document.getElementById(elementId);
        msg.textContent = text;
        msg.className = `api-key-msg msg-${type}`;
        msg.classList.remove('hidden');
    },
};
