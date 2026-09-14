// SignalPost Interactive Web Client

let currentProfile = null;
let currentFactsFilter = 'ALL';
let explorerOffset = 0;
const explorerLimit = 50;
let explorerTotal = 0;
let searchDebounceTimer = null;

// Modulo 11 weights for Norwegian org numbers
const WEIGHTS = [3, 2, 7, 6, 5, 4, 3, 2];

function validateMod11(orgnr) {
  const clean = orgnr.replace(/\D/g, '');
  if (clean.length !== 9) return false;
  const first8 = clean.slice(0, 8);
  let sum = 0;
  for (let i = 0; i < 8; i++) {
    sum += parseInt(first8[i], 10) * WEIGHTS[i];
  }
  const rem = sum % 11;
  if (rem === 1) return false; // Illegal control digit
  const expectedControl = rem === 0 ? 0 : 11 - rem;
  return parseInt(clean[8], 10) === expectedControl;
}

// Live Checksum Feedback
document.addEventListener('DOMContentLoaded', () => {
  const input = document.getElementById('orgnr-input');
  const badge = document.getElementById('checksum-badge');

  input.addEventListener('input', () => {
    const val = input.value.replace(/\D/g, '');
    if (val.length === 0) {
      badge.className = 'checksum-badge idle';
      badge.textContent = 'MOD 11 Ready';
    } else if (val.length < 9) {
      badge.className = 'checksum-badge idle';
      badge.textContent = `${val.length}/9 Digits`;
    } else if (val.length === 9) {
      if (validateMod11(val)) {
        badge.className = 'checksum-badge valid';
        badge.textContent = '✓ MOD 11 Valid';
      } else {
        badge.className = 'checksum-badge invalid';
        badge.textContent = '✗ Checksum Fail';
      }
    } else {
      badge.className = 'checksum-badge invalid';
      badge.textContent = 'Max 9 Digits';
    }
  });

  // Load initial preset (Equinor)
  loadCompany('923609016');
  loadExplorerData();
  loadStats();
});

function switchTab(tabId) {
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

  const targetPane = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);
  if (targetPane) targetPane.classList.add('active');
  if (targetBtn) targetBtn.classList.add('active');
}

function setPreset(orgnr) {
  const input = document.getElementById('orgnr-input');
  input.value = orgnr;
  input.dispatchEvent(new Event('input'));
  loadCompany(orgnr);
}

async function handleLookup(e) {
  e.preventDefault();
  const input = document.getElementById('orgnr-input');
  const orgnr = input.value.replace(/\D/g, '');
  if (!orgnr) return;
  loadCompany(orgnr);
}

async function loadCompany(orgnr, forceRefresh = false) {
  const loading = document.getElementById('lookup-loading');
  const errorBanner = document.getElementById('lookup-error');
  const profileResult = document.getElementById('profile-result');

  loading.classList.remove('hidden');
  errorBanner.classList.add('hidden');
  profileResult.classList.add('hidden');

  try {
    const url = `/api/company/${orgnr}${forceRefresh ? '?force_refresh=true' : ''}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Could not retrieve company profile.');
    }

    const profile = await resp.json();
    currentProfile = profile;
    renderProfile(profile);
    loading.classList.add('hidden');
    profileResult.classList.remove('hidden');
  } catch (err) {
    loading.classList.add('hidden');
    errorBanner.classList.remove('hidden');
    document.getElementById('error-desc').textContent = err.message;
  }
}

function renderProfile(p) {
  document.getElementById('disp-company-name').textContent = p.name;
  document.getElementById('disp-orgnr').textContent = p.orgnr;
  document.getElementById('disp-org-form').textContent = p.org_form;
  document.getElementById('disp-status').textContent = p.status;
  document.getElementById('disp-freshness').textContent = p.freshness_status;
  
  const freshEl = document.getElementById('disp-freshness');
  freshEl.className = `tag tag-freshness ${p.freshness_status.toLowerCase()}`;

  document.getElementById('disp-nace').textContent = `${p.industry_code || 'N/A'} - ${p.industry_description || 'N/A'}`;
  document.getElementById('disp-employees').textContent = p.employee_count ? p.employee_count.toLocaleString() : 'N/A';

  document.getElementById('disp-executive-summary').textContent = p.executive_summary || 'Executive summary not generated.';
  document.getElementById('disp-ceo').textContent = p.ceo_name || 'Not Registered';
  document.getElementById('disp-chair').textContent = p.board_chair ? `Chair: ${p.board_chair}` : 'Board Chair: N/A';

  // Financials
  if (p.latest_financials && p.latest_financials.revenue) {
    const f = p.latest_financials;
    document.getElementById('disp-revenue').textContent = `${f.revenue.toLocaleString()} ${f.currency}`;
    document.getElementById('disp-fin-period').textContent = `Audited Fiscal Year ${f.year}`;
    document.getElementById('disp-ebit').textContent = f.operating_profit ? `${f.operating_profit.toLocaleString()} ${f.currency}` : 'N/A';
    document.getElementById('disp-net-profit').textContent = f.net_profit ? `Net Result: ${f.net_profit.toLocaleString()} ${f.currency}` : '';
    document.getElementById('disp-equity').textContent = f.total_assets ? `Total Assets: ${f.total_assets.toLocaleString()} ${f.currency}` : '';
  } else {
    document.getElementById('disp-revenue').textContent = 'N/A';
    document.getElementById('disp-fin-period').textContent = 'Accounts Pending / Micro-entity';
    document.getElementById('disp-ebit').textContent = 'N/A';
    document.getElementById('disp-net-profit').textContent = '';
  }

  // Capital
  if (p.share_capital) {
    document.getElementById('disp-capital').textContent = `${p.share_capital.toLocaleString()} ${p.share_capital_currency || 'NOK'}`;
  } else {
    document.getElementById('disp-capital').textContent = 'N/A';
  }

  // Render facts
  document.getElementById('count-all-facts').textContent = (p.facts || []).length;
  renderFactsTable(p.facts || []);
}

function filterFacts(category) {
  currentFactsFilter = category;
  document.querySelectorAll('.f-chip').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');

  if (!currentProfile || !currentProfile.facts) return;

  if (category === 'ALL') {
    renderFactsTable(currentProfile.facts);
  } else {
    const filtered = currentProfile.facts.filter(f => f.category.toLowerCase().includes(category.toLowerCase()));
    renderFactsTable(filtered);
  }
}

function renderFactsTable(facts) {
  const tbody = document.getElementById('facts-table-body');
  tbody.innerHTML = '';

  if (facts.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: var(--text-muted); padding: 32px;">No facts in this category.</td></tr>`;
    return;
  }

  facts.forEach(f => {
    const tr = document.createElement('tr');

    const catBadge = `<span class="tag tag-form">${f.category.split('&')[0].trim()}</span>`;
    const factCell = `
      <div class="fact-title-cell">
        <strong>${f.label}</strong>
        <span class="fact-val-text">${escapeHtml(String(f.value))}</span>
      </div>
    `;

    const sourceCell = `
      <div class="source-link-cell">
        <span class="source-auth-name">${f.source_name}</span>
        <a href="${f.source_url}" target="_blank" rel="noopener noreferrer">
          ${f.source_url}
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
        </a>
      </div>
    `;

    const dateCell = `<span class="date-badge">${f.source_date ? f.source_date.slice(0, 10) : 'N/A'}</span>`;
    const verifiedCell = `<span class="verified-pill">✓ 100% Provenance</span>`;

    tr.innerHTML = `
      <td>${catBadge}</td>
      <td>${factCell}</td>
      <td>${sourceCell}</td>
      <td>${dateCell}</td>
      <td>${verifiedCell}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function triggerProfileSync() {
  if (!currentProfile) return;
  const syncBtn = document.getElementById('sync-btn');
  syncBtn.disabled = true;
  syncBtn.innerHTML = `Checking Delta Stream...`;

  try {
    const resp = await fetch(`/api/company/${currentProfile.orgnr}/sync`, { method: 'POST' });
    const data = await resp.json();
    if (data.profile) {
      currentProfile = data.profile;
      renderProfile(data.profile);
    }
    alert(`Freshness Check Result: ${data.reason}\nStatus: ${data.freshness_status || 'CURRENT'}`);
  } catch (err) {
    alert(`Sync error: ${err.message}`);
  } finally {
    syncBtn.disabled = false;
    syncBtn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path></svg>
      Keep Current (Delta Sync)
    `;
  }
}

function copyProfileJson() {
  if (!currentProfile) return;
  navigator.clipboard.writeText(JSON.stringify(currentProfile, null, 2));
  alert('Profile JSON copied to clipboard!');
}

// 1,000 Profiles Explorer Logic
async function loadExplorerData() {
  const searchInput = document.getElementById('explorer-search');
  const query = searchInput ? searchInput.value.trim() : '';

  try {
    let url = `/api/profiles?limit=${explorerLimit}&offset=${explorerOffset}`;
    if (query) url += `&search=${encodeURIComponent(query)}`;

    const resp = await fetch(url);
    if (!resp.ok) return;
    const data = await resp.json();

    explorerTotal = data.total;
    renderExplorerTable(data.profiles || []);

    const start = explorerTotal === 0 ? 0 : explorerOffset + 1;
    const end = Math.min(explorerOffset + (data.profiles || []).length, explorerTotal);
    document.getElementById('page-info').textContent = `Showing ${start}-${end} of ${explorerTotal.toLocaleString()} Profiles`;

    document.getElementById('prev-page-btn').disabled = explorerOffset === 0;
    document.getElementById('next-page-btn').disabled = end >= explorerTotal;
  } catch (e) {
    console.error('Explorer error:', e);
  }
}

function renderExplorerTable(profiles) {
  const tbody = document.getElementById('explorer-table-body');
  tbody.innerHTML = '';

  if (profiles.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-muted); padding: 32px;">No profiles found matching search criteria.</td></tr>`;
    return;
  }

  profiles.forEach(p => {
    const tr = document.createElement('tr');
    const revStr = p.latest_financials && p.latest_financials.revenue ? `${p.latest_financials.revenue.toLocaleString()} ${p.latest_financials.currency}` : 'N/A';
    const empStr = p.employee_count ? p.employee_count.toLocaleString() : '0';

    tr.innerHTML = `
      <td><strong style="font-family: var(--font-mono); color: var(--accent-cyan);">${p.orgnr}</strong></td>
      <td><strong>${escapeHtml(p.name)}</strong></td>
      <td><span class="tag tag-form">${p.org_form}</span></td>
      <td>${escapeHtml((p.industry_description || 'N/A').slice(0, 30))}</td>
      <td>${empStr}</td>
      <td>${revStr}</td>
      <td><span class="tag tag-freshness">${p.freshness_status}</span></td>
      <td>
        <button class="btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="viewInAgent('${p.orgnr}')">View</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function viewInAgent(orgnr) {
  switchTab('lookup');
  setPreset(orgnr);
}

function handleExplorerSearch() {
  clearTimeout(searchDebounceTimer);
  searchDebounceTimer = setTimeout(() => {
    explorerOffset = 0;
    loadExplorerData();
  }, 300);
}

function changePage(dir) {
  explorerOffset += dir * explorerLimit;
  if (explorerOffset < 0) explorerOffset = 0;
  loadExplorerData();
}

async function loadStats() {
  try {
    const resp = await fetch('/api/stats');
    if (resp.ok) {
      const stats = await resp.json();
      document.getElementById('stat-total-profiles').textContent = `${stats.total_profiles.toLocaleString()}+`;
      document.getElementById('stat-total-facts').textContent = `${stats.total_facts_verified.toLocaleString()}+`;
    }
  } catch (e) {
    console.error('Stats error:', e);
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
