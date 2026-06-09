/* ── State ── */
const PROVIDERS = ['openai', 'gemini', 'grok', 'perplexity'];
const PROV_LABELS = { openai: 'OpenAI', gemini: 'Gemini', grok: 'Grok', perplexity: 'Perplexity' };
const PROV_COLORS = { openai: '#00d4aa', gemini: '#6c63ff', grok: '#ff6b6b', perplexity: '#ffa94d' };

let attachedFile = null;
let activeRole = '';
let activeProviders = [...PROVIDERS];

/* ── DOM refs ── */
const chat = document.getElementById('chat');
const welcome = document.getElementById('welcome');
const input = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const statusBar = document.getElementById('statusBar');
const fileBtn = document.getElementById('fileBtn');
const fileModal = document.getElementById('fileModal');
const fileContent = document.getElementById('fileContent');
const fileCancel = document.getElementById('fileCancel');
const fileApply = document.getElementById('fileApply');
const roleSelect = document.getElementById('roleSelect');
const providerToggles = document.getElementById('providerToggles');
let msgIdCounter = 0;

/* ── Init ── */
function init() {
  buildProviderToggles();
  fetchStatus();
  setInterval(fetchStatus, 30_000);
  input.addEventListener('input', onInput);
  input.addEventListener('keydown', onKey);
  sendBtn.addEventListener('click', send);
  fileBtn.addEventListener('click', () => fileModal.classList.remove('hidden'));
  fileCancel.addEventListener('click', () => { fileModal.classList.add('hidden'); fileContent.value = ''; });
  fileApply.addEventListener('click', () => {
    attachedFile = fileContent.value;
    fileBtn.classList.toggle('active', !!attachedFile);
    fileModal.classList.add('hidden');
  });
  roleSelect.addEventListener('change', () => { activeRole = roleSelect.value; });
  input.focus();
}

function buildProviderToggles() {
  providerToggles.innerHTML = '';
  PROVIDERS.forEach(p => {
    const btn = document.createElement('button');
    btn.className = 'provider-toggle on';
    btn.dataset.provider = p;
    btn.textContent = PROV_LABELS[p];
    btn.addEventListener('click', () => {
      btn.classList.toggle('on');
      activeProviders = [...providerToggles.querySelectorAll('.provider-toggle.on')].map(b => b.dataset.provider);
      updateSend();
    });
    providerToggles.appendChild(btn);
  });
}

/* ── Status ── */
async function fetchStatus() {
  try {
    const r = await fetch('/api/status');
    const data = await r.json();
    statusBar.innerHTML = data.map(s =>
      `<span class="status-dot${s.available ? '' : ' off'}">${s.provider}</span>`
    ).join('');
  } catch { statusBar.textContent = '?';
  }
}

/* ── Input handling ── */
function onInput() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  updateSend();
}
function onKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
}
function updateSend() {
  sendBtn.disabled = !input.value.trim() || activeProviders.length === 0;
}

/* ── Send ── */
async function send() {
  const text = input.value.trim();
  if (!text || activeProviders.length === 0) return;

  input.value = '';
  input.style.height = 'auto';
  updateSend();
  welcome.classList.add('hidden');

  const msgId = ++msgIdCounter;
  appendMessage(msgId, text);

  const body = {
    question: text,
    providers: activeProviders.join(','),
  };
  if (attachedFile) body.file_content = attachedFile;
  if (activeRole) body.roles = activeRole;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    await readSSE(res, msgId);
  } catch (err) {
    PROVIDERS.forEach(p => {
      const bodyEl = getPanelBody(msgId, p);
      if (bodyEl && bodyEl.querySelector('.placeholder')) {
        bodyEl.innerHTML = `<span class="error-text">Connection failed: ${err.message}</span>`;
      }
    });
  }
}

/* ── SSE reader ── */
async function readSSE(response, msgId) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n');
    buffer = parts.pop() || '';

    for (const line of parts) {
      if (line.startsWith('data: ')) {
        try {
          const evt = JSON.parse(line.slice(6));
          handleEvent(evt, msgId);
        } catch { /* skip malformed */ }
      }
    }
  }
}

function handleEvent(evt, msgId) {
  const { kind, provider, data } = evt;

  if (kind === 'token') {
    const bodyEl = getPanelBody(msgId, provider);
    if (!bodyEl) return;
    const ph = bodyEl.querySelector('.placeholder');
    if (ph) ph.remove();
    bodyEl.insertAdjacentText('beforeend', data);
    scrollBottom();
  }

  if (kind === 'done') {
    const panel = document.querySelector(`.panel[data-msg="${msgId}"][data-provider="${provider}"]`);
    if (!panel) return;
    panel.querySelector('.spinner').classList.remove('on');
    panel.querySelector('.check').classList.remove('hidden');
    const foot = panel.querySelector('.panel-foot');
    if (foot) foot.classList.add('show');
  }

  if (kind === 'error') {
    const panel = document.querySelector(`.panel[data-msg="${msgId}"][data-provider="${provider}"]`);
    if (panel) {
      panel.querySelector('.spinner').classList.remove('on');
      panel.querySelector('.err').classList.remove('hidden');
    }
    const bodyEl = getPanelBody(msgId, provider);
    if (bodyEl) {
      const ph = bodyEl.querySelector('.placeholder');
      if (ph) ph.remove();
      bodyEl.innerHTML = `<span class="error-text">${data}</span>`;
    }
  }

  if (kind === 'complete') {
    input.focus();
  }
}

/* ── DOM helpers ── */
function appendMessage(msgId, text) {
  const div = document.createElement('div');
  div.className = 'msg';
  div.id = `msg-${msgId}`;

  const qDiv = document.createElement('div');
  qDiv.className = 'msg-q';
  if (attachedFile) {
    const badge = document.createElement('span');
    badge.className = 'file-badge';
    badge.textContent = '📎 code attached';
    qDiv.appendChild(badge);
    qDiv.appendChild(document.createElement('br'));
  }
  qDiv.appendChild(document.createTextNode(text));
  div.appendChild(qDiv);

  const aDiv = document.createElement('div');
  aDiv.className = 'msg-a';

  PROVIDERS.forEach(p => {
    const panel = document.createElement('div');
    panel.className = 'panel';
    panel.dataset.msg = msgId;
    panel.dataset.provider = p;

    panel.innerHTML = `
      <div class="panel-head">
        ${PROV_LABELS[p]}
        <span class="spinner on"></span>
        <span class="check hidden">✓</span>
        <span class="err hidden">✗</span>
      </div>
      <div class="panel-body"><span class="placeholder">Waiting…</span></div>
      <div class="panel-foot"></div>
    `;

    aDiv.appendChild(panel);
  });

  div.appendChild(aDiv);
  chat.appendChild(div);
  scrollBottom();
}

function getPanelBody(msgId, provider) {
  const panel = document.querySelector(`.panel[data-msg="${msgId}"][data-provider="${provider}"]`);
  return panel ? panel.querySelector('.panel-body') : null;
}

function scrollBottom() {
  chat.scrollTop = chat.scrollHeight;
}

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', init);
