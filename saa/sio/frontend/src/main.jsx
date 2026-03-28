/**
 * Swan Interaction Overlay — Frontend Entry Point
 *
 * Vanilla JS + HTML implementation (no build step required).
 * Connects to the SIO FastAPI backend via REST + WebSocket.
 *
 * To use with React: replace this with a proper React app.
 * This scaffold works standalone for development and testing.
 */

const API_BASE = window.location.origin;
const WS_BASE = `ws://${window.location.host}`;

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  sessionId: null,
  viewMode: 'analyst', // human, analyst, engineer
  messages: [],
  stateSnapshot: null,
  stateDiffs: [],
  rationale: null,
  relationships: {},
  modulators: {},
  conflicts: [],
};

// ---------------------------------------------------------------------------
// API Client
// ---------------------------------------------------------------------------

async function apiCall(method, path, body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, opts);
  return res.json();
}

async function createSession() {
  const data = await apiCall('POST', '/api/sessions', { view_mode: state.viewMode });
  state.sessionId = data.session_id;
  connectWebSocket();
  return data;
}

async function sendMessage(text) {
  if (!state.sessionId) await createSession();
  const data = await apiCall('POST', '/api/chat', {
    text,
    session_id: state.sessionId,
  });
  return data;
}

async function getState() {
  if (!state.sessionId) return null;
  return apiCall('GET', `/api/state/${state.sessionId}`);
}

async function injectEvent(eventType, eventData) {
  if (!state.sessionId) return null;
  return apiCall('POST', `/api/inject/${state.sessionId}`, {
    event_type: eventType,
    data: eventData,
  });
}

async function getRationale() {
  if (!state.sessionId) return null;
  return apiCall('GET', `/api/rationale/${state.sessionId}`);
}

// ---------------------------------------------------------------------------
// WebSocket
// ---------------------------------------------------------------------------

let ws = null;

function connectWebSocket() {
  if (!state.sessionId) return;
  ws = new WebSocket(`${WS_BASE}/ws/${state.sessionId}`);
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'state_update') {
      state.stateSnapshot = data.snapshot;
      renderSidebar();
    }
  };
  ws.onclose = () => { setTimeout(connectWebSocket, 2000); };
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderApp() {
  const root = document.getElementById('root');
  root.innerHTML = `
    <div class="sio-layout">
      <header class="sio-header">
        <h1>Swan Interaction Overlay</h1>
        <span style="color: var(--text-secondary); font-size: 12px;">
          Session: ${state.sessionId || 'none'}
        </span>
        <div class="mode-selector">
          ${['human', 'analyst', 'engineer'].map(m => `
            <button class="mode-btn ${state.viewMode === m ? 'active' : ''}"
                    onclick="setViewMode('${m}')">${m}</button>
          `).join('')}
        </div>
      </header>
      <div class="sio-main">
        <div class="chat-container">
          <div class="chat-messages" id="chat-messages"></div>
          ${state.viewMode === 'engineer' ? '<div class="trace-panel" id="trace-panel"></div>' : ''}
          <div class="chat-input-area">
            <input class="chat-input" id="chat-input" placeholder="Type a message..."
                   onkeydown="if(event.key==='Enter')handleSend()">
            <button class="chat-send-btn" onclick="handleSend()">Send</button>
          </div>
        </div>
      </div>
      <div class="sio-sidebar" id="sidebar">
        ${renderSidebarContent()}
      </div>
    </div>
  `;
  renderMessages();
}

function renderSidebarContent() {
  const s = state.stateSnapshot;
  if (!s && state.viewMode === 'human') return '<div class="panel"><p style="color:var(--text-secondary);font-size:12px;">Chat panel only in Human mode.</p></div>';
  if (!s) return '<div class="panel"><p style="color:var(--text-secondary);font-size:12px;">No session active. Send a message to begin.</p></div>';

  let html = '';

  // Internal State Panel
  if (state.viewMode !== 'human') {
    html += `
      <div class="panel">
        <div class="panel-header">Internal State</div>
        ${stateRow('Energy', s.energy)}
        ${stateRow('Viability', s.viability)}
        ${stateRow('Continuity', s.continuity_score)}
        ${stateRow('Memory Integrity', s.memory_integrity)}
        ${stateRow('Damage', s.damage, true)}
        ${stateRow('Strain', s.strain, true)}
      </div>
    `;
  }

  // Modulators
  if (state.viewMode !== 'human' && s.modulators) {
    html += `
      <div class="panel">
        <div class="panel-header">Modulators</div>
        ${Object.entries(s.modulators).map(([k, v]) =>
          `<div class="panel-row"><span class="label">${k}</span><span class="value">${v.toFixed(3)}</span></div>`
        ).join('')}
      </div>
    `;
  }

  // Relationships
  if (state.viewMode !== 'human' && s.relationships && Object.keys(s.relationships).length > 0) {
    html += `
      <div class="panel">
        <div class="panel-header">Relationships</div>
        ${Object.entries(s.relationships).map(([agent, rel]) => `
          <div class="panel-row">
            <span class="label">${agent}</span>
            <span class="value">trust:${(rel.trust||0).toFixed(2)} bond:${(rel.bond_strength||0).toFixed(2)}</span>
          </div>
        `).join('')}
      </div>
    `;
  }

  // Values
  if (state.viewMode !== 'human' && s.values && Object.keys(s.values).length > 0) {
    html += `
      <div class="panel">
        <div class="panel-header">Values</div>
        ${Object.entries(s.values).map(([k, v]) =>
          `<div class="panel-row"><span class="label">${k}</span><span class="value">${v.toFixed(3)}</span></div>`
        ).join('')}
      </div>
    `;
  }

  // State Diffs
  if (state.viewMode !== 'human' && state.stateDiffs.length > 0) {
    html += `
      <div class="panel">
        <div class="panel-header">Last State Change</div>
        <div class="diff-list">
          ${state.stateDiffs.map(d => {
            const cls = d.delta > 0 ? 'diff-positive' : d.delta < 0 ? 'diff-negative' : 'diff-neutral';
            const sign = d.delta > 0 ? '+' : '';
            return `<div class="diff-item"><span class="${cls}">${d.field}: ${sign}${d.delta?.toFixed(4) || '?'}</span></div>`;
          }).join('')}
        </div>
      </div>
    `;
  }

  // Scenario Controls (engineer mode)
  if (state.viewMode === 'engineer') {
    html += `
      <div class="panel">
        <div class="panel-header">Scenario Controls</div>
        <div class="scenario-controls">
          <button class="scenario-btn" onclick="doInject('damage','{}')">Inject Damage</button>
          <button class="scenario-btn" onclick="doInject('betrayal','{\"agent_id\":\"user\"}')">Betrayal</button>
          <button class="scenario-btn" onclick="doInject('stabilizing_presence','{\"agent_id\":\"user\",\"stress_reduction\":0.1}')">Support</button>
          <button class="scenario-btn" onclick="doInject('resource_shock','{\"amount\":0.3}')">Resource Shock</button>
          <button class="scenario-btn" onclick="doInject('hazard_spike','{\"level\":0.7}')">Hazard Spike</button>
        </div>
      </div>
    `;
  }

  return html;
}

function stateRow(label, value, inverted = false) {
  if (value == null) return '';
  const pct = Math.round(value * 100);
  let cls = 'good';
  if (inverted) {
    cls = value > 0.6 ? 'danger' : value > 0.3 ? 'warn' : 'good';
  } else {
    cls = value < 0.3 ? 'danger' : value < 0.6 ? 'warn' : 'good';
  }
  return `
    <div class="panel-row">
      <span class="label">${label}</span>
      <span class="value">${value.toFixed(3)}</span>
    </div>
    <div class="state-bar"><div class="state-bar-fill ${cls}" style="width:${pct}%"></div></div>
  `;
}

function renderSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.innerHTML = renderSidebarContent();
}

function renderMessages() {
  const container = document.getElementById('chat-messages');
  if (!container) return;
  container.innerHTML = state.messages.map(m => `
    <div class="chat-msg ${m.role}">
      <div>${m.text}</div>
      ${m.classification && state.viewMode !== 'human' ? `<div class="msg-classification">[${m.classification}] action: ${m.action || '?'}</div>` : ''}
      ${m.meta && state.viewMode !== 'human' ? `<div class="msg-meta">${m.meta}</div>` : ''}
    </div>
  `).join('');
  container.scrollTop = container.scrollHeight;
}

// ---------------------------------------------------------------------------
// Event Handlers
// ---------------------------------------------------------------------------

async function handleSend() {
  const input = document.getElementById('chat-input');
  if (!input || !input.value.trim()) return;
  const text = input.value.trim();
  input.value = '';

  state.messages.push({ role: 'user', text });
  renderMessages();

  try {
    const res = await sendMessage(text);
    state.stateSnapshot = res.state_snapshot;
    state.stateDiffs = res.state_diffs || [];
    state.messages.push({
      role: 'agent',
      text: res.response_text,
      classification: res.action_intent?.action_type,
      action: res.action_intent?.action_type,
      meta: `tick:${res.tick} score:${res.action_intent?.score?.toFixed(2)} conflict:${res.action_intent?.conflict}`,
    });
    renderMessages();
    renderSidebar();

    if (state.viewMode === 'engineer') {
      const trace = document.getElementById('trace-panel');
      if (trace) {
        trace.innerHTML = `<div class="trace-entry"><span class="trace-key">action:</span> ${res.action_intent?.action_type} (${res.action_intent?.score?.toFixed(3)})</div>`
          + (res.action_intent?.competing_actions || []).map(c =>
            `<div class="trace-entry"><span class="trace-key">  alt:</span> ${c.action} (${c.score?.toFixed(3)})</div>`
          ).join('')
          + (res.action_intent?.rationale || []).map(r =>
            `<div class="trace-entry"><span class="trace-key">reason:</span> ${r}</div>`
          ).join('');
      }
    }
  } catch (err) {
    state.messages.push({ role: 'agent', text: `[Error: ${err.message}]` });
    renderMessages();
  }
}

async function doInject(eventType, dataStr) {
  try {
    const data = JSON.parse(dataStr);
    const res = await injectEvent(eventType, data);
    state.stateSnapshot = res;
    renderSidebar();
    state.messages.push({ role: 'agent', text: `[Event injected: ${eventType}]`, meta: 'system' });
    renderMessages();
  } catch (err) {
    console.error('Inject error:', err);
  }
}

// Expose to window for onclick handlers
window.handleSend = handleSend;
window.setViewMode = (mode) => { state.viewMode = mode; renderApp(); };
window.doInject = doInject;

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

renderApp();
