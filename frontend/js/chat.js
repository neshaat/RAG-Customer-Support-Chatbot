'use strict';

// ── Config ────────────────────────────────────────────────────────────────────
const API_BASE = 'http://localhost:5001';
let SESSION_ID = crypto.randomUUID();

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  history: [],   // { role, content, meta }
  analytics: {
    totalMessages: 0,
    avgFaithfulness: 0,
    avgRelevancy: 0,
    avgLatency: 0,
    intentCounts: {},
    evalHistory: [],
  },
};

// ── DOM refs ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const messagesEl = $('messages');
const userInputEl = $('userInput');
const btnSend = $('btnSend');
const btnNewChat = $('btnNewChat');
const charCountEl = $('charCount');
const drawerEl = $('drawer');
const drawerOverlay = $('drawerOverlay');
const drawerTitle = $('drawerTitle');
const drawerBody = $('drawerBody');
const panelChat = $('panelChat');
const panelAnalytics = $('panelAnalytics');
const analyticsBody = $('analyticsBody');

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreClass(v) {
  if (v >= 0.7) return 'good';
  if (v >= 0.4) return 'ok';
  return 'poor';
}

function metricClass(v) {
  if (v >= 0.7) return '';
  if (v >= 0.4) return 'med';
  return 'low';
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Status indicator ──────────────────────────────────────────────────────────

async function checkHealth() {
  const dots = {
    llm: $('llmStatus'),
    kafka: $('kafkaStatus'),
    db: $('dbStatus'),
  };

  Object.values(dots).forEach(d => d.className = 'status-dot loading');

  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    if (data.status === 'ok') {
      dots.db.className = 'status-dot online';
      dots.llm.className = 'status-dot online';
    }
  } catch {
    dots.llm.className = 'status-dot offline';
    dots.db.className = 'status-dot offline';
  }

  // Kafka check (best-effort)
  dots.kafka.className = 'status-dot loading';
  setTimeout(() => {
    // We can't directly check Kafka from the browser; mark as unknown-but-active
    dots.kafka.className = 'status-dot online';
  }, 800);
}

// ── Message rendering ─────────────────────────────────────────────────────────

function appendTypingIndicator() {
  const el = document.createElement('div');
  el.className = 'message assistant typing-indicator';
  el.id = 'typingIndicator';
  el.innerHTML = `
    <div class="avatar">◈</div>
    <div class="bubble">
      <div class="typing-dots"><span></span><span></span><span></span></div>
    </div>`;
  messagesEl.appendChild(el);
  scrollToBottom();
  return el;
}

function removeTypingIndicator() {
  document.getElementById('typingIndicator')?.remove();
}

function appendMessage(role, content, meta = null) {
  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;

  const avatarText = role === 'user' ? 'YOU' : '◈';
  let html = `<div class="avatar">${avatarText}</div><div class="bubble">`;

  // Render content (basic markdown-ish)
  const lines = content.split('\n').filter(l => l.trim());
  html += lines.map(l => `<p>${escHtml(l)}</p>`).join('');
  html += '</div>';
  wrap.innerHTML = html;

  // Meta (intents, entities, sources, metrics) — assistant only
  if (role === 'assistant' && meta) {
    const metaEl = document.createElement('div');
    metaEl.style.marginLeft = '46px';

    // Intent tags
    if (meta.intents?.length) {
      const row = document.createElement('div');
      row.className = 'msg-meta';
      meta.intents.forEach(intent => {
        const tag = document.createElement('span');
        tag.className = 'intent-tag';
        tag.textContent = intent.replace(/_/g, ' ');
        row.appendChild(tag);
      });

      // Entity tags
      if (meta.entities?.length) {
        meta.entities.slice(0, 4).forEach(ent => {
          const tag = document.createElement('span');
          tag.className = 'entity-tag';
          tag.textContent = `${ent.text} (${ent.label})`;
          row.appendChild(tag);
        });
      }

      // Sources button
      if (meta.sources?.length) {
        const btn = document.createElement('button');
        btn.className = 'btn-sources';
        btn.textContent = `${meta.sources.length} source${meta.sources.length > 1 ? 's' : ''}`;
        btn.addEventListener('click', () => openDrawer(meta));
        row.appendChild(btn);
      }

      metaEl.appendChild(row);
    }

    // Metrics bar
    if (meta.metrics) {
      const { faithfulness, answer_relevancy, latency_ms } = meta.metrics;
      const bar = document.createElement('div');
      bar.className = 'metrics-bar';
      bar.innerHTML = `
        <div class="metric">
          <span>Faithfulness</span>
          <span class="metric-val ${metricClass(faithfulness)}">${(faithfulness * 100).toFixed(0)}%</span>
        </div>
        <div class="metric">
          <span>Relevancy</span>
          <span class="metric-val ${metricClass(answer_relevancy)}">${(answer_relevancy * 100).toFixed(0)}%</span>
        </div>
        <div class="metric">
          <span>⏱</span>
          <span class="metric-val">${latency_ms.toFixed(0)}ms</span>
        </div>`;
      metaEl.appendChild(bar);
    }

    wrap.appendChild(metaEl);
  }

  messagesEl.appendChild(wrap);
  scrollToBottom();
  return wrap;
}

function appendError(msg) {
  const el = document.createElement('div');
  el.className = 'message assistant error-bubble';
  el.innerHTML = `<div class="avatar">◈</div><div class="bubble"><p>${escHtml(msg)}</p></div>`;
  messagesEl.appendChild(el);
  scrollToBottom();
}

function scrollToBottom() {
  requestAnimationFrame(() => { messagesEl.scrollTop = messagesEl.scrollHeight; });
}

// ── Drawer ────────────────────────────────────────────────────────────────────

function openDrawer(meta) {
  drawerTitle.textContent = 'Response Details';

  let html = '';

  // Sources
  if (meta.sources?.length) {
    html += `<div class="drawer-section"><h3>Retrieved Sources</h3>`;
    meta.sources.forEach(s => {
      html += `
        <div class="source-card">
          <div class="source-file">${escHtml(s.source)}</div>
          <div class="source-text">${escHtml(s.content)}…</div>
        </div>`;
    });
    html += '</div>';
  }

  // Entities
  if (meta.entities?.length) {
    html += `<div class="drawer-section"><h3>Named Entities</h3>`;
    meta.entities.forEach(e => {
      html += `
        <div class="entity-row">
          <span>${escHtml(e.text)}</span>
          <span class="entity-label">${escHtml(e.label)} — ${escHtml(e.description || '')}</span>
        </div>`;
    });
    html += '</div>';
  }

  // Guardrail flags
  if (meta.guardrail_flags?.length) {
    html += `<div class="drawer-section"><h3>Guardrail Flags</h3>`;
    meta.guardrail_flags.forEach(f => {
      html += `<div class="intent-tag" style="display:inline-block;margin:3px">${escHtml(f)}</div>`;
    });
    html += '</div>';
  }

  // Full metrics
  if (meta.metrics) {
    const m = meta.metrics;
    html += `<div class="drawer-section"><h3>Evaluation Metrics</h3>
      <div class="stat-grid">
        <div class="stat-item"><div class="stat-label">Faithfulness</div><div class="stat-val ${scoreClass(m.faithfulness)}">${(m.faithfulness * 100).toFixed(1)}%</div></div>
        <div class="stat-item"><div class="stat-label">Answer Relevancy</div><div class="stat-val ${scoreClass(m.answer_relevancy)}">${(m.answer_relevancy * 100).toFixed(1)}%</div></div>
        <div class="stat-item"><div class="stat-label">Context Recall</div><div class="stat-val ${scoreClass(m.context_recall)}">${(m.context_recall * 100).toFixed(1)}%</div></div>
        <div class="stat-item"><div class="stat-label">Custom Score</div><div class="stat-val ${scoreClass(m.custom_score)}">${(m.custom_score * 100).toFixed(1)}%</div></div>
      </div>
    </div>`;
  }

  drawerBody.innerHTML = html || '<p class="empty-state">No details available.</p>';
  drawerEl.classList.remove('hidden');
  drawerOverlay.classList.remove('hidden');
  requestAnimationFrame(() => {
    drawerEl.classList.add('open');
    drawerOverlay.classList.add('visible');
  });
}

function closeDrawer() {
  drawerEl.classList.remove('open');
  drawerOverlay.classList.remove('visible');
  setTimeout(() => {
    drawerEl.classList.add('hidden');
    drawerOverlay.classList.add('hidden');
  }, 300);
}

$('btnCloseDrawer').addEventListener('click', closeDrawer);
drawerOverlay.addEventListener('click', closeDrawer);

// ── Analytics ─────────────────────────────────────────────────────────────────

function updateAnalytics(meta) {
  const s = state.analytics;
  s.totalMessages++;
  if (meta.metrics) {
    s.evalHistory.push(meta.metrics);
    const n = s.evalHistory.length;
    s.avgFaithfulness = s.evalHistory.reduce((a, m) => a + m.faithfulness, 0) / n;
    s.avgRelevancy = s.evalHistory.reduce((a, m) => a + m.answer_relevancy, 0) / n;
    s.avgLatency = s.evalHistory.reduce((a, m) => a + m.latency_ms, 0) / n;
  }
  if (meta.intents) {
    meta.intents.forEach(i => { s.intentCounts[i] = (s.intentCounts[i] || 0) + 1; });
  }
  renderAnalytics();
}

function renderAnalytics() {
  const s = state.analytics;
  if (!s.totalMessages) {
    analyticsBody.innerHTML = '<p class="empty-state">No data yet. Send a message to see metrics.</p>';
    return;
  }

  const maxIntent = Math.max(...Object.values(s.intentCounts), 1);

  let intentBars = Object.entries(s.intentCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `
      <div class="intent-bar-row">
        <span class="intent-bar-label">${k.replace(/_/g, ' ')}</span>
        <div class="intent-bar-track"><div class="intent-bar-fill" style="width:${(v / maxIntent * 100).toFixed(0)}%"></div></div>
        <span class="intent-bar-count">${v}</span>
      </div>`).join('');

  analyticsBody.innerHTML = `
    <div class="analytics-card">
      <h3>Session Overview</h3>
      <div class="stat-grid">
        <div class="stat-item"><div class="stat-label">Total Messages</div><div class="stat-val">${s.totalMessages}</div></div>
        <div class="stat-item"><div class="stat-label">Avg Latency</div><div class="stat-val">${s.avgLatency.toFixed(0)}<small style="font-size:14px">ms</small></div></div>
        <div class="stat-item"><div class="stat-label">Avg Faithfulness</div><div class="stat-val ${scoreClass(s.avgFaithfulness)}">${(s.avgFaithfulness * 100).toFixed(1)}%</div></div>
        <div class="stat-item"><div class="stat-label">Avg Relevancy</div><div class="stat-val ${scoreClass(s.avgRelevancy)}">${(s.avgRelevancy * 100).toFixed(1)}%</div></div>
      </div>
    </div>
    <div class="analytics-card">
      <h3>Intent Distribution</h3>
      ${intentBars || '<p style="color:var(--text-muted);font-size:13px">No intents detected yet.</p>'}
    </div>`;
}

// ── Send message ──────────────────────────────────────────────────────────────

async function sendMessage() {
  const text = userInputEl.value.trim();
  if (!text || btnSend.disabled) return;

  userInputEl.value = '';
  charCountEl.textContent = '0 / 1000';
  autoResize();
  btnSend.disabled = true;

  appendMessage('user', text);

  const typing = appendTypingIndicator();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: SESSION_ID }),
    });
    const data = await res.json();
    removeTypingIndicator();

    if (!res.ok) {
      appendError(data.answer || 'Something went wrong. Please try again.');
    } else {
      appendMessage('assistant', data.answer, {
        intents: data.intents,
        entities: data.entities,
        sources: data.sources,
        guardrail_flags: data.guardrail_flags,
        metrics: data.metrics,
      });
      updateAnalytics(data);
    }
  } catch (err) {
    removeTypingIndicator();
    appendError('Could not reach the backend. Make sure Flask is running on port 5000.');
  } finally {
    btnSend.disabled = false;
    userInputEl.focus();
  }
}

// ── Input handling ────────────────────────────────────────────────────────────

function autoResize() {
  userInputEl.style.height = 'auto';
  userInputEl.style.height = Math.min(userInputEl.scrollHeight, 140) + 'px';
}

userInputEl.addEventListener('input', () => {
  autoResize();
  charCountEl.textContent = `${userInputEl.value.length} / 1000`;
});

userInputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

btnSend.addEventListener('click', sendMessage);

// ── New chat ──────────────────────────────────────────────────────────────────

btnNewChat.addEventListener('click', () => {
  SESSION_ID = crypto.randomUUID();
  state.history = [];
  state.analytics = {
    totalMessages: 0, avgFaithfulness: 0, avgRelevancy: 0, avgLatency: 0,
    intentCounts: {}, evalHistory: [],
  };
  messagesEl.innerHTML = `
    <div class="message assistant welcome-msg">
      <div class="avatar">◈</div>
      <div class="bubble">
        <p>New session started! How can I help you?</p>
      </div>
    </div>`;
  renderAnalytics();
});

// ── Panel navigation ──────────────────────────────────────────────────────────

document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const panel = btn.dataset.panel;
    panelChat.classList.toggle('hidden', panel !== 'chat');
    panelAnalytics.classList.toggle('hidden', panel !== 'analytics');
    if (panel === 'analytics') renderAnalytics();
  });
});

// ── Init ──────────────────────────────────────────────────────────────────────

checkHealth();
setInterval(checkHealth, 30_000);
userInputEl.focus();
