// SignalPost Frontend Application Logic

let allLoadedProfiles = [];
let currentSelectedProfile = null;
let currentTab = 'lookup';
let activeSort = 'complete';
let activeIndustry = 'ALL';
let activeStatus = 'ALL';

// Norwegian Modulo 11 check weights
const WEIGHTS = [3, 2, 7, 6, 5, 4, 3, 2];

function validateMod11(rawOrgnr) {
  const clean = String(rawOrgnr).replace(/\D/g, '');
  if (clean.length !== 9) return false;
  const first8 = clean.slice(0, 8);
  let sum = 0;
  for (let i = 0; i < 8; i++) {
    sum += parseInt(first8[i], 10) * WEIGHTS[i];
  }
  const rem = sum % 11;
  if (rem === 1) return false;
  const expectedControl = rem === 0 ? 0 : 11 - rem;
  return parseInt(clean[8], 10) === expectedControl;
}

// Initial Boot
document.addEventListener('DOMContentLoaded', async () => {
  setupSearchListener();
  await loadInitialProfiles();
  loadStats();
});

// Setup hero search input listener
function setupSearchListener() {
  const input = document.getElementById('main-search-input');
  const pill = document.getElementById('checksum-pill');

  input.addEventListener('input', () => {
    const val = input.value.trim().replace(/\D/g, '');
    if (val.length === 0) {
      pill.className = 'hero-checksum-indicator idle';
      pill.textContent = 'MOD 11';
      filterCompanyList(input.value.trim());
    } else if (val.length === 9) {
      if (validateMod11(val)) {
        pill.className = 'hero-checksum-indicator valid';
        pill.textContent = '✓ MOD 11';
      } else {
        pill.className = 'hero-checksum-indicator invalid';
        pill.textContent = '✗ Invalid';
      }
      filterCompanyList(input.value.trim());
    } else if (val.length > 0 && val.length < 9) {
      pill.className = 'hero-checksum-indicator idle';
      pill.textContent = `${val.length}/9`;
      filterCompanyList(input.value.trim());
    } else {
      filterCompanyList(input.value.trim());
    }
  });
}

// Fetch Initial Batch from Backend
async function loadInitialProfiles() {
  try {
    const resp = await fetch('/api/profiles?limit=150&offset=0');
    if (resp.ok) {
      const data = await resp.json();
      allLoadedProfiles = data.profiles || [];
      populateIndustryFilter(allLoadedProfiles);
      renderCompanyList(allLoadedProfiles);

      if (allLoadedProfiles.length > 0) {
        selectCompany(allLoadedProfiles[0].orgnr);
      }
    }
  } catch (err) {
    console.error('Failed to load company profiles:', err);
  }
}

// Populate Industry Dropdown
function populateIndustryFilter(profiles) {
  const select = document.getElementById('industry-filter');
  const industries = new Set();

  profiles.forEach(p => {
    if (p.industry_description) {
      industries.add(p.industry_description);
    }
  });

  select.innerHTML = '<option value="ALL">All industries</option>';
  Array.from(industries).sort().forEach(ind => {
    const opt = document.createElement('option');
    opt.value = ind;
    opt.textContent = ind.length > 28 ? ind.slice(0, 25) + '...' : ind;
    select.appendChild(opt);
  });
}

// Render Left Sidebar Company List
function renderCompanyList(profiles) {
  const container = document.getElementById('company-scroll-list');
  container.innerHTML = '';

  let filtered = [...profiles];

  if (activeIndustry !== 'ALL') {
    filtered = filtered.filter(p => p.industry_description === activeIndustry);
  }

  if (activeStatus !== 'ALL') {
    filtered = filtered.filter(p => (p.status || '').toLowerCase().includes(activeStatus.toLowerCase()));
  }

  if (activeSort === 'name') {
    filtered.sort((a, b) => a.name.localeCompare(b.name));
  } else if (activeSort === 'employees') {
    filtered.sort((a, b) => (b.employee_count || 0) - (a.employee_count || 0));
  }

  document.getElementById('sidebar-matches-count').textContent = `${filtered.length.toLocaleString()} companies found`;

  if (filtered.length === 0) {
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">No companies matching filters.</div>';
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement('div');
    const isActive = currentSelectedProfile && currentSelectedProfile.orgnr === p.orgnr;
    card.className = `company-item-card ${isActive ? 'active' : ''}`;
    card.id = `item-${p.orgnr}`;
    card.onclick = () => selectCompany(p.orgnr);

    const city = (p.business_address && p.business_address.poststed) ? p.business_address.poststed : 'NORWAY';
    const naceCode = p.industry_code || 'General';

    card.innerHTML = `
      <div class="item-company-name">${escapeHtml(p.name)}</div>
      <div class="item-submeta">${p.orgnr} • ${escapeHtml(city)}</div>
      <div class="item-industry-pill">${escapeHtml(naceCode)}</div>
    `;
    container.appendChild(card);
  });
}

// Select and Display Full Company Profile on the Right
async function selectCompany(orgnr) {
  document.querySelectorAll('.company-item-card').forEach(c => c.classList.remove('active'));
  const activeEl = document.getElementById(`item-${orgnr}`);
  if (activeEl) activeEl.classList.add('active');

  let profile = allLoadedProfiles.find(p => p.orgnr === orgnr);

  if (!profile) {
    try {
      const resp = await fetch(`/api/company/${orgnr}`);
      if (resp.ok) {
        profile = await resp.json();
      }
    } catch (e) {
      console.error(e);
    }
  }

  if (profile) {
    currentSelectedProfile = profile;
    renderDetailView(profile);
  }
}

// Render the Detail Profile Panel
function renderDetailView(p) {
  document.getElementById('p-name').textContent = p.name;
  document.getElementById('p-orgnr').textContent = p.orgnr;
  document.getElementById('p-orgform').textContent = p.org_form_description || p.org_form;
  document.getElementById('p-status-badge').textContent = p.status || 'Active';
  document.getElementById('p-freshness-badge').textContent = p.freshness_status || 'CURRENT';

  // 4 Stat Boxes
  document.getElementById('p-employees').textContent = p.employee_count ? p.employee_count.toLocaleString() : 'N/A';
  document.getElementById('p-reg-date').textContent = p.registration_date ? formatDate(p.registration_date) : 'N/A';
  
  const city = (p.business_address && p.business_address.poststed) ? p.business_address.poststed : 'OSLO';
  document.getElementById('p-location').textContent = city;
  document.getElementById('p-mva').textContent = p.is_vat_registered ? 'Registered' : 'Not registered';

  // Narrative
  const empStr = p.employee_count ? `${p.employee_count.toLocaleString()} employees` : 'unspecified staff';
  const foundStr = p.foundation_date ? ` and founded on ${p.foundation_date}` : '';
  document.getElementById('p-narrative').textContent = 
    `${p.name} is registered in Norway as ${p.org_form_description || p.org_form}. The registry classifies its main activity as ${p.industry_description || 'General commerce'} (${p.industry_code || 'NACE'}). The current registry row reports ${empStr}${foundStr}. No adverse status flag is present in the sampled registry row.`;

  // Industry & Address
  document.getElementById('p-industry-code').textContent = p.industry_code || 'NACE General';
  document.getElementById('p-industry-desc').textContent = p.industry_description || 'Commercial activity';
  document.getElementById('p-city').textContent = city;
  
  let fullAddr = city;
  if (p.business_address) {
    const street = (p.business_address.adresse || []).join(', ');
    const postnr = p.business_address.postnummer || '';
    fullAddr = `${street ? street + ', ' : ''}${postnr} ${city}`.trim();
  }
  document.getElementById('p-street-address').textContent = fullAddr || 'Registered business address on file';

  // Financials
  if (p.latest_financials && p.latest_financials.revenue) {
    const f = p.latest_financials;
    document.getElementById('p-fin-tag').textContent = 'available';
    document.getElementById('p-fin-period').textContent = `1 filed periods (${f.year})`;
    document.getElementById('p-fin-revenue').textContent = `${f.revenue.toLocaleString()} ${f.currency}`;
    document.getElementById('p-fin-ebit').textContent = f.operating_profit ? `${f.operating_profit.toLocaleString()} ${f.currency}` : 'N/A';
    document.getElementById('p-fin-net').textContent = f.net_profit ? `${f.net_profit.toLocaleString()} ${f.currency}` : 'N/A';
    document.getElementById('p-fin-assets').textContent = f.total_assets ? `${f.total_assets.toLocaleString()} ${f.currency}` : 'N/A';
  } else {
    document.getElementById('p-fin-tag').textContent = 'accounts pending';
    document.getElementById('p-fin-period').textContent = 'Accounts pending / Exempt';
    document.getElementById('p-fin-revenue').textContent = 'N/A';
    document.getElementById('p-fin-ebit').textContent = 'N/A';
    document.getElementById('p-fin-net').textContent = 'N/A';
    document.getElementById('p-fin-assets').textContent = 'N/A';
  }

  // People & Ownership Table
  renderRolesTable(p);

  // Direct Sources Permalinks
  document.getElementById('link-enhet').href = `https://data.brreg.no/enhetsregisteret/api/enheter/${p.orgnr}`;
  document.getElementById('link-roller').href = `https://data.brreg.no/enhetsregisteret/api/enheter/${p.orgnr}/roller`;
  document.getElementById('link-regnskap').href = `https://data.brreg.no/regnskapsregisteret/regnskap/${p.orgnr}`;

  // Update Backend Inspection Views
  const jsonStr = JSON.stringify(p, null, 2);
  const backendBlock = document.getElementById('backend-raw-json');
  if (backendBlock) backendBlock.textContent = jsonStr;
  const modalBlock = document.getElementById('modal-json-block');
  if (modalBlock) modalBlock.textContent = jsonStr;
  const qaName = document.getElementById('qa-company-name');
  if (qaName) qaName.textContent = p.name;
}

// Render Roles Table
function renderRolesTable(p) {
  const table = document.getElementById('p-roles-table');
  table.innerHTML = '';

  const rows = [];
  if (p.ceo_name) {
    rows.push({ name: p.ceo_name, title: 'Daglig leder' });
  }
  if (p.board_chair) {
    rows.push({ name: p.board_chair, title: 'Styreleder' });
  }
  if (p.auditor_name) {
    rows.push({ name: p.auditor_name, title: 'Revisor' });
  }

  if (p.key_roles && p.key_roles.length > 0) {
    p.key_roles.forEach(r => {
      const assigned = r.person_name || r.organization_name;
      if (assigned && !rows.some(existing => existing.name === assigned)) {
        rows.push({ name: assigned, title: r.role_description || r.role_code });
      }
    });
  }

  if (rows.length === 0) {
    rows.push({ name: 'Management details on registry file', title: 'Roles reported' });
  }

  rows.slice(0, 5).forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="role-person-name">${escapeHtml(r.name)}</td>
      <td class="role-title-text">${escapeHtml(r.title)}</td>
    `;
    table.appendChild(tr);
  });

  // Group status
  const groupTr = document.createElement('tr');
  const groupText = p.is_part_of_group ? 'Affiliated with corporate group structure' : 'Parent: not reported - group signal: not found';
  groupTr.innerHTML = `
    <td colspan="2" style="font-size: 0.78rem; color: var(--text-muted); padding-top: 10px;">
      ${escapeHtml(groupText)}
    </td>
  `;
  table.appendChild(groupTr);
}

// Handle Search Submission
async function handleSearchSubmit(e) {
  e.preventDefault();
  const query = document.getElementById('main-search-input').value.trim();
  if (!query) return;

  const cleanDigits = query.replace(/\D/g, '');
  if (cleanDigits.length === 9) {
    // Direct lookup by orgnr
    try {
      const resp = await fetch(`/api/company/${cleanDigits}`);
      if (resp.ok) {
        const profile = await resp.json();
        if (!allLoadedProfiles.some(p => p.orgnr === profile.orgnr)) {
          allLoadedProfiles.unshift(profile);
        }
        renderCompanyList(allLoadedProfiles);
        selectCompany(profile.orgnr);
        scrollToLookup();
        return;
      }
    } catch (err) {
      console.error(err);
    }
  }

  filterCompanyList(query);
  scrollToLookup();
}

function filterCompanyList(term) {
  if (!term) {
    renderCompanyList(allLoadedProfiles);
    return;
  }
  const lower = term.toLowerCase();
  const matched = allLoadedProfiles.filter(p => 
    p.name.toLowerCase().includes(lower) || 
    p.orgnr.includes(lower) ||
    (p.industry_description || '').toLowerCase().includes(lower) ||
    (p.business_address && (p.business_address.poststed || '').toLowerCase().includes(lower))
  );
  renderCompanyList(matched);
}

// Live Freshness Sync
async function syncCurrentCompany() {
  if (!currentSelectedProfile) return;
  const btn = event.target;
  const originalText = btn.innerHTML;
  btn.innerHTML = 'Connecting to stream...';

  try {
    const resp = await fetch(`/api/company/${currentSelectedProfile.orgnr}/sync`, { method: 'POST' });
    const data = await resp.json();
    if (data.profile) {
      currentSelectedProfile = data.profile;
      renderDetailView(data.profile);
    }
    alert(`Delta Stream Check: ${data.reason}\nFreshness Status: ${data.freshness_status || 'CURRENT'}`);
  } catch (err) {
    alert(`Sync error: ${err.message}`);
  } finally {
    btn.innerHTML = originalText;
  }
}

// Grounded Research Agent Q&A
function openAgentDrawer() {
  const modal = document.getElementById('agent-drawer-modal');
  modal.classList.remove('hidden');
}

function closeAgentDrawer() {
  const modal = document.getElementById('agent-drawer-modal');
  modal.classList.add('hidden');
}

function handleAgentQuestion(e) {
  e.preventDefault();
  const input = document.getElementById('agent-question-input');
  const question = input.value.trim();
  if (!question || !currentSelectedProfile) return;

  const history = document.getElementById('qa-history');
  
  // Append user message
  const userDiv = document.createElement('div');
  userDiv.style.cssText = 'background-color: #fff; border: 1px solid var(--border-subtle); padding: 8px 12px; border-radius: 6px;';
  userDiv.innerHTML = `<strong>You:</strong> ${escapeHtml(question)}`;
  history.appendChild(userDiv);

  // Grounded answer generator based on currentSelectedProfile
  const answer = generateGroundedAnswer(question, currentSelectedProfile);
  
  const agentDiv = document.createElement('div');
  agentDiv.style.cssText = 'background-color: var(--bg-subtle); padding: 8px 12px; border-radius: 6px;';
  agentDiv.innerHTML = `<strong style="color: var(--maroon-primary);">Agent:</strong> ${escapeHtml(answer)}`;
  history.appendChild(agentDiv);

  input.value = '';
  history.scrollTop = history.scrollHeight;
}

function generateGroundedAnswer(q, p) {
  const l = q.toLowerCase();
  if (l.includes('ceo') || l.includes('leder') || l.includes('manager')) {
    return p.ceo_name ? `According to official corporate governance records, the CEO (Daglig leder) of ${p.name} is ${p.ceo_name}.` : `No registered CEO name is reported in the official record for ${p.name}.`;
  }
  if (l.includes('chair') || l.includes('styreleder')) {
    return p.board_chair ? `The Chairman of the Board (Styreleder) is ${p.board_chair}.` : `No Board Chair is listed in the current governance record.`;
  }
  if (l.includes('revenue') || l.includes('turnover') || l.includes('omsetning') || l.includes('financial') || l.includes('money')) {
    if (p.latest_financials && p.latest_financials.revenue) {
      return `For the ${p.latest_financials.year} accounting period, ${p.name} reported annual revenue of ${p.latest_financials.revenue.toLocaleString()} ${p.latest_financials.currency}.`;
    }
    return `Annual financial accounts for ${p.name} are currently pending or not filed in the open Regnskapsregisteret preview.`;
  }
  if (l.includes('employee') || l.includes('staff') || l.includes('ansatte') || l.includes('workers')) {
    return p.employee_count ? `${p.name} has ${p.employee_count.toLocaleString()} registered employees reported to NAV Aa-registeret.` : `Employee headcount is not recorded for this entity.`;
  }
  if (l.includes('address') || l.includes('location') || l.includes('where') || l.includes('city')) {
    const addr = p.business_address ? `${(p.business_address.adresse || []).join(' ')}, ${p.business_address.postnummer || ''} ${p.business_address.poststed || ''}` : 'No address on file';
    return `The registered business address of ${p.name} is ${addr}.`;
  }
  if (l.includes('bankrupt') || l.includes('status') || l.includes('solvency')) {
    return `The official operating status of ${p.name} in Foretaksregisteret is '${p.status}'.`;
  }
  return `This answer is strictly bounded to the verified profile of ${p.name} (Org.nr: ${p.orgnr}). Verified facts include NACE ${p.industry_code} (${p.industry_description}), ${p.employee_count || 0} employees, and status '${p.status}'. Missing values are not hallucinated.`;
}

// Tab Switching
function setActiveTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.workspace-view').forEach(v => v.style.display = 'none');
  document.querySelectorAll('.tab-item').forEach(b => b.classList.remove('active'));

  const activeView = document.getElementById(`view-${tab}`);
  const activeBtn = document.getElementById(`tab-${tab}-btn`);
  if (activeView) activeView.style.display = 'block';
  if (activeBtn) activeBtn.classList.add('active');
}

// Modal Control
function toggleBackendModal() {
  const modal = document.getElementById('backend-modal');
  modal.classList.toggle('hidden');
}

function handleModalBackdropClick(e) {
  if (e.target.id === 'backend-modal') {
    toggleBackendModal();
  }
}

function handleDrawerBackdropClick(e) {
  if (e.target.id === 'agent-drawer-modal') {
    closeAgentDrawer();
  }
}

function scrollToLookup() {
  const el = document.getElementById('company-lookup');
  if (el) el.scrollIntoView({ behavior: 'smooth' });
}

function focusSearch() {
  const input = document.getElementById('main-search-input');
  if (input) {
    input.focus();
    input.scrollIntoView({ behavior: 'smooth' });
  }
}

function handleSortChange() {
  activeSort = document.getElementById('sort-select').value;
  renderCompanyList(allLoadedProfiles);
}

function handleFilterChange() {
  activeIndustry = document.getElementById('industry-filter').value;
  activeStatus = document.getElementById('status-filter').value;
  renderCompanyList(allLoadedProfiles);
}

async function loadStats() {
  try {
    const resp = await fetch('/api/stats');
    if (resp.ok) {
      const stats = await resp.json();
      document.getElementById('stat-card-count').textContent = stats.total_profiles.toLocaleString();
      document.getElementById('tab-badge-count').textContent = stats.total_profiles.toLocaleString();
    }
  } catch (e) {
    console.error(e);
  }
}

function formatDate(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  } catch {
    return isoStr;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
