// ── Data loading ───────────────────────────────────────────────
async function loadJSON(name) {
  const res = await fetch(`./data/${name}.json`);
  if (!res.ok) throw new Error(`Failed to load ${name}.json (${res.status})`);
  return res.json();
}

// ── Confidence badge ───────────────────────────────────────────
const CONF_CONFIG = {
  SOURCED: { glyph: '●', label: 'sourced', cls: 'conf-sourced' },
  'VISUALLY VERIFIED': { glyph: '◐', label: 'verified', cls: 'conf-verified' },
  'VISUALLY VERIFIED (LOW)': { glyph: '◑', label: 'verified·low', cls: 'conf-verified' },
  ESTIMATED: { glyph: '○', label: 'estimate', cls: 'conf-estimated' },
  HIGH: { glyph: '●', label: 'high conf.', cls: 'conf-sourced' },
  MEDIUM: { glyph: '◐', label: 'medium', cls: 'conf-verified' },
  LOW: { glyph: '◑', label: 'low', cls: 'conf-estimated' },
  INSUFFICIENT: { glyph: '○', label: 'insufficient', cls: 'conf-insufficient' },
};

function confBadge(tier, showLabel = true) {
  const cfg = CONF_CONFIG[tier] || CONF_CONFIG.ESTIMATED;
  return `<span class="conf-badge ${cfg.cls}" title="${tier}">
    <span class="glyph">${cfg.glyph}</span>${showLabel ? `<span>${cfg.label}</span>` : ''}
  </span>`;
}

// ── Shell: topbar + nav, shared across all pages ───────────────
const NAV_ITEMS = [
  { href: 'index.html', label: 'Map', icon: '◈' },
  { href: 'heatmap.html', label: 'Parking Heatmap', icon: '◆' },
  { href: 'hotspots.html', label: 'Hotspots', icon: '▲' },
  { href: 'deployment.html', label: 'Deployment', icon: '▶' },
  { href: 'validation.html', label: 'Validation', icon: '✓' },
  { href: 'coverage.html', label: 'Coverage', icon: '◎' },
];

function renderShell(activePage) {
  const path = window.location.pathname.split('/').pop() || 'index.html';

  document.getElementById('topbar').innerHTML = `
    <div class="brand">
      <span class="brand-mark">◆</span>
      <span class="brand-text">TRAFFICOS</span>
      <span class="brand-sub">BENGALURU TRAFFIC POLICE</span>
    </div>
    <div id="ticker-slot"></div>
    <div class="clock mono" id="clock"></div>
  `;

  document.getElementById('nav').innerHTML = `
    ${NAV_ITEMS.map(item => `
      <a href="${item.href}" class="nav-link ${path === item.href ? 'active' : ''}">
        <span class="nav-icon">${item.icon}</span>
        <span>${item.label}</span>
      </a>
    `).join('')}
    <div class="nav-footer">
      <span class="mono nav-footer-text">v6.0 PRODUCTION</span>
    </div>
  `;

  startClock();
  loadJSON('coverage').then(cov => {
    document.getElementById('ticker-slot').innerHTML = `
      <span class="mono ticker">
        <span style="color: var(--green-bright)">${cov.tier_counts.HIGH}</span>
        <span style="color: var(--paper-dim)"> / ${cov.total_junctions} JUNCTIONS — HIGH CONFIDENCE</span>
      </span>
    `;
  }).catch(() => {});
}

function startClock() {
  function tick() {
    const el = document.getElementById('clock');
    if (!el) return;
    const time = new Intl.DateTimeFormat('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
      timeZone: 'Asia/Kolkata',
    }).format(new Date());
    el.textContent = `${time} IST`;
  }
  tick();
  setInterval(tick, 1000);
}

// ── Loading / error state helpers ───────────────────────────────
function showLoading(containerEl, label = 'Loading') {
  containerEl.innerHTML = `
    <div class="state-wrap">
      <span class="mono loading-text">${label}<span class="loading-dots">···</span></span>
    </div>`;
}

function showError(containerEl, message, retryFn) {
  containerEl.innerHTML = `
    <div class="state-wrap">
      <div class="error-box">
        <div class="eyebrow" style="color: var(--orange)">Connection failed</div>
        <div class="error-msg mono">${message}</div>
        ${retryFn ? '<button id="retry-btn" style="margin-top:14px;background:transparent;border:1px solid var(--orange);color:var(--orange);padding:6px 14px;font-size:12px;cursor:pointer;border-radius:var(--radius);font-family:var(--font-mono)">Retry</button>' : ''}
      </div>
    </div>`;
  if (retryFn) {
    document.getElementById('retry-btn').addEventListener('click', retryFn);
  }
}

// ── Stat card helper ─────────────────────────────────────────────
function statCard(label, value, sub, accent = '') {
  return `
    <div class="stat-card">
      <div class="eyebrow">${label}</div>
      <div class="stat-value ${accent ? `accent-${accent}` : ''}">${value}</div>
      ${sub ? `<div class="stat-sub">${sub}</div>` : ''}
    </div>`;
}

function esc(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
