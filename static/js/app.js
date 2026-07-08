// ---------- Shared: live zone status ----------
async function fetchZones() {
  const res = await fetch('/api/crowd-status');
  const data = await res.json();
  return data.zones;
}

function statusClass(status) {
  return { normal: 'normal', busy: 'busy', critical: 'critical' }[status] || 'normal';
}

function renderZoneList(zones) {
  const el = document.getElementById('zoneList');
  if (!el) return;
  el.innerHTML = zones.map(z => `
    <div class="zone-row">
      <span class="zone-row__name">${z.name}</span>
      <span class="zone-row__bar"><span class="zone-row__fill fill--${statusClass(z.status)}" style="width:${z.occupancy_pct}%"></span></span>
      <span class="zone-row__pct status--${statusClass(z.status)}">${z.occupancy_pct}%</span>
    </div>
  `).join('');
}

function renderZoneTable(zones) {
  const body = document.getElementById('zoneTableBody');
  if (!body) return;
  body.innerHTML = zones.map(z => `
    <tr>
      <td>${z.name}</td>
      <td class="status--${statusClass(z.status)}">${z.occupancy_pct}%</td>
      <td>${z.count.toLocaleString()}</td>
      <td>${z.wait_min} min</td>
      <td class="status--${statusClass(z.status)}">${z.status.toUpperCase()}</td>
    </tr>
  `).join('');
}

async function pollZones() {
  const zones = await fetchZones();
  renderZoneList(zones);
  renderZoneTable(zones);
  const zoneSelect = document.getElementById('incZone');
  if (zoneSelect && !zoneSelect.dataset.filled) {
    zoneSelect.innerHTML = zones.map(z => `<option value="${z.id}">${z.name}</option>`).join('');
    zoneSelect.dataset.filled = '1';
  }
}

if (document.getElementById('zoneList') || document.getElementById('zoneTableBody')) {
  pollZones();
  setInterval(pollZones, 6000);
}

// ---------- Fan portal: chat ----------
const chatForm = document.getElementById('chatForm');
if (chatForm) {
  const log = document.getElementById('chatLog');
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById('chatInput');
    const lang = document.getElementById('chatLang').value;
    const message = input.value.trim();
    if (!message) return;
    log.insertAdjacentHTML('beforeend', `<div class="msg msg--user">${escapeHtml(message)}</div>`);
    input.value = '';
    log.scrollTop = log.scrollHeight;
    const thinking = document.createElement('div');
    thinking.className = 'msg msg--bot';
    thinking.textContent = '…';
    log.appendChild(thinking);
    log.scrollTop = log.scrollHeight;
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, language: lang }),
      });
      const data = await res.json();
      thinking.textContent = data.reply;
    } catch {
      thinking.textContent = 'Connection issue — please try again.';
    }
    log.scrollTop = log.scrollHeight;
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ---------- Fan portal: wayfinder ----------
const navForm = document.getElementById('navForm');
if (navForm) {
  navForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const origin = document.getElementById('navOrigin').value;
    const destination = document.getElementById('navDest').value;
    const accessible = document.getElementById('navAccessible').checked;
    const result = document.getElementById('navResult');
    result.innerHTML = '<li>Finding route…</li>';
    const res = await fetch('/api/navigate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ origin, destination, accessible }),
    });
    const data = await res.json();
    const steps = data.directions.split('\n').filter(Boolean);
    result.innerHTML = steps.map(s => `<li>${escapeHtml(s.replace(/^\d+\.\s*/, ''))}</li>`).join('');
  });
}

// ---------- Fan portal: sustainability tip ----------
const tipEl = document.getElementById('sustainTip');
if (tipEl) {
  fetch('/api/sustainability-tip').then(r => r.json()).then(d => { tipEl.textContent = d.tip; });
}

// ---------- Ops: AI briefing ----------
async function loadBrief() {
  const el = document.getElementById('briefText');
  if (!el) return;
  el.textContent = 'Generating briefing…';
  const res = await fetch('/api/ops-brief', { method: 'POST' });
  const data = await res.json();
  el.textContent = data.brief;
}
const refreshBtn = document.getElementById('refreshBrief');
if (refreshBtn) {
  refreshBtn.addEventListener('click', loadBrief);
  loadBrief();
}

// ---------- Ops: incident log ----------
async function loadIncidents() {
  const list = document.getElementById('incidentLog');
  if (!list) return;
  const res = await fetch('/api/incidents');
  const data = await res.json();
  list.innerHTML = data.map(i => `
    <li>
      <div>${i.type}${i.note ? ' — ' + escapeHtml(i.note) : ''}</div>
      <div class="inc-meta">${i.zone} · ${new Date(i.ts).toLocaleTimeString()}</div>
    </li>
  `).join('') || '<li>No incidents logged.</li>';
}
const incidentForm = document.getElementById('incidentForm');
if (incidentForm) {
  incidentForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const zone = document.getElementById('incZone').value;
    const type = document.getElementById('incType').value;
    const note = document.getElementById('incNote').value;
    await fetch('/api/incidents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zone, type, note }),
    });
    document.getElementById('incNote').value = '';
    loadIncidents();
  });
  loadIncidents();
  setInterval(loadIncidents, 10000);
}
