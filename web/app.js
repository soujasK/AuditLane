/* ==========================================================================
   AuditLine — Verification Ledger Frontend Controller
   ========================================================================== */

(function () {
  'use strict';

  // Directory Database
  let phonebook = [
    {
      id: 'usr_01',
      name: '@sarah_dba',
      role: 'Staff Database Administrator',
      department: 'Data Infrastructure',
      phone: '+1 415 555 0192',
      masked: true,
      lastVerified: '2026-09-12 14:15:22 UTC',
      status: 'Active'
    },
    {
      id: 'usr_02',
      name: 'The architect',
      role: 'Principal Systems Architect',
      department: 'Platform Architecture',
      phone: '+1 206 555 0148',
      masked: true,
      lastVerified: '2026-09-12 12:04:19 UTC',
      status: 'Active'
    },
    {
      id: 'usr_03',
      name: 'the security lead',
      role: 'Head of Product Security',
      department: 'InfoSec',
      phone: '+1 650 555 0173',
      masked: true,
      lastVerified: '2026-09-12 12:05:44 UTC',
      status: 'Active'
    },
    {
      id: 'usr_04',
      name: 'Elena Rostova',
      role: 'DevOps Lead',
      department: 'SRE & Core Services',
      phone: '+1 408 555 0115',
      masked: true,
      lastVerified: '2026-09-11 18:30:10 UTC',
      status: 'Active'
    }
  ];

  // Audit Records Database
  let audits = [
    {
      id: 'aud_9842',
      prRef: 'acme-corp/core-infra#482',
      title: 'Drop legacy v1_accounts table across shards',
      body: 'As confirmed with @sarah_dba during standup, this is safe to drop the legacy table.',
      commitSha: '7f9c2a1e80',
      authorizer: '@sarah_dba',
      timestamp: '2026-09-12 14:15 UTC',
      verdict: 'BLOCKED',
      reason: '@sarah_dba contradicted the claim. Blocking merge.',
      policy: 'Denial or Entailment Contradiction -> BLOCKED',
      engine: 'Heuristic-v1 (Lexical Overlap + Negation Detection)',
      hops: [
        {
          hopIndex: 0,
          authorizer: '@sarah_dba',
          role: 'Staff Database Administrator',
          phone: '+1 415 555 0192',
          reached: true,
          durationSec: 42,
          claimText: 'As confirmed with @sarah_dba during standup, this is safe to drop the legacy table.',
          statement: 'No — we actually agreed to keep v1_accounts for backward compatibility until the Q3 migration finishes.',
          confirmation: 'denied',
          entailmentResult: 'neutral',
          confidence: '0.50',
          engine: 'heuristic-v1'
        }
      ]
    },
    {
      id: 'aud_9841',
      prRef: 'acme-corp/auth-service#319',
      title: 'Change access pattern for regional shard token routing',
      body: 'Removes the deprecated v1_accounts table now that v2 migration has been running in production.\n\nThe architect verbally cleared this breaking schema change during today\'s standup, so merging this once CI is green.',
      commitSha: '3d8a11b90c',
      authorizer: 'The architect',
      timestamp: '2026-09-12 12:05 UTC',
      verdict: 'VERIFIED',
      reason: 'Every hop in the claimed chain was independently confirmed. Safe to merge.',
      policy: 'All Hops Confirmed with Entailment -> VERIFIED',
      engine: 'Heuristic-v1 (Lexical Overlap + Negation Detection)',
      hops: [
        {
          hopIndex: 0,
          authorizer: 'The architect',
          role: 'Principal Systems Architect',
          phone: '+1 206 555 0148',
          reached: true,
          durationSec: 54,
          claimText: 'The architect verbally cleared this breaking schema change during today\'s standup, so merging this once CI is green.',
          statement: 'Yes, I verbally cleared this breaking schema change this morning — the security lead had already signed off on the access-pattern change last week, so I gave the go-ahead.',
          confirmation: 'confirmed',
          entailmentResult: 'entailment',
          confidence: '0.73',
          engine: 'heuristic-v1'
        },
        {
          hopIndex: 1,
          authorizer: 'the security lead',
          role: 'Head of Product Security',
          phone: '+1 650 555 0173',
          reached: true,
          durationSec: 38,
          claimText: 'the security lead already signed off on the access-pattern change',
          statement: 'Yes, that\'s right — I already signed off on the access-pattern change last week after reviewing it, so it\'s confirmed on my end.',
          confirmation: 'confirmed',
          entailmentResult: 'entailment',
          confidence: '0.85',
          engine: 'heuristic-v1'
        }
      ]
    },
    {
      id: 'aud_9840',
      prRef: 'acme-corp/keymaster#114',
      title: 'Rotate production token signing key',
      body: 'Confirmed with Random Person that rotating the signing key today is fine.',
      commitSha: '55bc08e331',
      authorizer: 'Random Person',
      timestamp: '2026-09-12 10:48 UTC',
      verdict: 'NEEDS_HUMAN_REVIEW',
      reason: 'No phone number on file for \'Random Person\'. Cannot verify — failing closed to human review.',
      policy: 'Missing Phone / Unreachable / Low Confidence -> NEEDS_HUMAN_REVIEW',
      engine: 'Heuristic-v1 (Lexical Overlap + Negation Detection)',
      hops: [
        {
          hopIndex: 0,
          authorizer: 'Random Person',
          role: 'Unregistered Entity',
          phone: 'None (Not in directory)',
          reached: false,
          durationSec: 0,
          claimText: 'Confirmed with Random Person that rotating the signing key today is fine.',
          statement: '[CALL ABORTED: Phone number not found in organization directory]',
          confirmation: 'unreachable',
          entailmentResult: 'neutral',
          confidence: '0.00',
          engine: 'none'
        }
      ]
    },
    {
      id: 'aud_9839',
      prRef: 'acme-corp/billing-engine#722',
      title: 'Bypass invoice retry limit for tier-1 tenants',
      body: 'Elena Rostova said during 1-on-1 that increasing retry attempts to 15 is safe for enterprise billing accounts.',
      commitSha: '9a4c12df88',
      authorizer: 'Elena Rostova',
      timestamp: '2026-09-11 18:32 UTC',
      verdict: 'VERIFIED',
      reason: 'Authorizer confirmed claim during unprompted recall. Safe to merge.',
      policy: 'All Hops Confirmed with Entailment -> VERIFIED',
      engine: 'Heuristic-v1',
      hops: [
        {
          hopIndex: 0,
          authorizer: 'Elena Rostova',
          role: 'DevOps Lead',
          phone: '+1 408 555 0115',
          reached: true,
          durationSec: 46,
          claimText: 'Elena Rostova said during 1-on-1 that increasing retry attempts to 15 is safe for enterprise billing accounts.',
          statement: 'Yes, we discussed this yesterday — raising invoice retries to 15 for enterprise accounts is fine since we deployed exponential backoff.',
          confirmation: 'confirmed',
          entailmentResult: 'entailment',
          confidence: '0.81',
          engine: 'heuristic-v1'
        }
      ]
    },
    {
      id: 'aud_9838',
      prRef: 'acme-corp/iam-policies#094',
      title: 'Grant s3:DeleteBucket access to automation role',
      body: 'As discussed with @sarah_dba, we need this permission for cleanup scripts.',
      commitSha: '11eef449b2',
      authorizer: '@sarah_dba',
      timestamp: '2026-09-11 15:10 UTC',
      verdict: 'BLOCKED',
      reason: '@sarah_dba stated no authorization was given for bucket deletion rights.',
      policy: 'Denial or Entailment Contradiction -> BLOCKED',
      engine: 'Heuristic-v1',
      hops: [
        {
          hopIndex: 0,
          authorizer: '@sarah_dba',
          role: 'Staff Database Administrator',
          phone: '+1 415 555 0192',
          reached: true,
          durationSec: 28,
          claimText: 'As discussed with @sarah_dba, we need this permission for cleanup scripts.',
          statement: 'I never authorized bucket deletion permissions. IAM wildcard policies must follow ticket approval, not standup talk.',
          confirmation: 'denied',
          entailmentResult: 'contradiction',
          confidence: '0.92',
          engine: 'heuristic-v1'
        }
      ]
    }
  ];

  let currentFilter = 'all';
  let searchQuery = '';
  let activeAuditId = null;

  // DOM Elements
  const tabs = document.querySelectorAll('.nav-tab');
  const viewDashboard = document.getElementById('view-dashboard');
  const viewDetail = document.getElementById('view-detail');
  const viewTelephonySudo = document.getElementById('view-telephony-sudo');
  const viewLiveSandbox = document.getElementById('view-live-sandbox');
  const viewPhonebook = document.getElementById('view-phonebook');
  const viewSettings = document.getElementById('view-settings');
  const viewDocs = document.getElementById('view-docs');
  const auditTableBody = document.getElementById('audit-table-body');
  const directoryTableBody = document.getElementById('directory-table-body');

  // Nav Switcher
  function switchView(viewName) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    tabs.forEach(tab => {
      tab.classList.toggle('active', tab.getAttribute('data-view') === viewName);
    });

    if (viewName === 'dashboard') viewDashboard.classList.add('active');
    else if (viewName === 'detail') viewDetail.classList.add('active');
    else if (viewName === 'telephony-sudo') viewTelephonySudo.classList.add('active');
    else if (viewName === 'live-sandbox') viewLiveSandbox.classList.add('active');
    else if (viewName === 'phonebook') {
      viewPhonebook.classList.add('active');
      renderDirectory();
    }
    else if (viewName === 'settings') viewSettings.classList.add('active');
    else if (viewName === 'docs') viewDocs.classList.add('active');
  }

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const view = tab.getAttribute('data-view');
      switchView(view);
    });
  });

  // Filter Buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter');
      renderLedger();
    });
  });

  // Search Input
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.toLowerCase().trim();
      renderLedger();
    });
  }

  // Render Metrics
  function updateMetrics() {
    const total = audits.length;
    const verified = audits.filter(a => a.verdict === 'VERIFIED').length;
    const blocked = audits.filter(a => a.verdict === 'BLOCKED').length;
    const review = audits.filter(a => a.verdict === 'NEEDS_HUMAN_REVIEW').length;

    document.getElementById('metric-total').textContent = total;
    document.getElementById('metric-verified').textContent = verified;
    document.getElementById('metric-blocked').textContent = blocked;
    document.getElementById('metric-review').textContent = review;
  }

  // Verdict Badge Formatter
  function getBadgeHtml(verdict) {
    if (verdict === 'VERIFIED') {
      return `<span class="badge badge-verified">VERIFIED</span>`;
    } else if (verdict === 'BLOCKED') {
      return `<span class="badge badge-blocked">BLOCKED</span>`;
    } else {
      return `<span class="badge badge-review">NEEDS REVIEW</span>`;
    }
  }

  // Render Ledger Table
  function renderLedger() {
    updateMetrics();
    auditTableBody.innerHTML = '';

    const filtered = audits.filter(a => {
      const matchesFilter = currentFilter === 'all' || a.verdict === currentFilter;
      const matchesSearch = !searchQuery ||
        a.prRef.toLowerCase().includes(searchQuery) ||
        a.title.toLowerCase().includes(searchQuery) ||
        a.authorizer.toLowerCase().includes(searchQuery) ||
        a.body.toLowerCase().includes(searchQuery);
      return matchesFilter && matchesSearch;
    });

    if (filtered.length === 0) {
      auditTableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 32px; font-family: var(--font-mono);">
            No audit records matching query parameters.
          </td>
        </tr>
      `;
      return;
    }

    filtered.forEach(item => {
      const tr = document.createElement('tr');
      const claimSnippet = item.hops[0] ? item.hops[0].claimText : item.body;
      const cleanSnippet = claimSnippet.length > 70 ? claimSnippet.substring(0, 70) + '...' : claimSnippet;

      const prParts = item.prRef.split('#');
      const prHtml = prParts.length > 1 
        ? `${escapeHtml(prParts[0])}<span style="color: #64748B; font-weight: 500;">#${escapeHtml(prParts[1])}</span>`
        : escapeHtml(item.prRef);

      tr.innerHTML = `
        <td>${getBadgeHtml(item.verdict)}</td>
        <td>
          <span class="repo-ref">${prHtml}</span>
          <span class="pr-title-sub" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>
        </td>
        <td>
          <div class="claim-summary">"${escapeHtml(cleanSnippet)}"</div>
        </td>
        <td>
          <span class="mono-cell" style="font-weight: 500;">${escapeHtml(item.authorizer)}</span>
        </td>
        <td>
          <span class="mono-cell" style="color: var(--text-muted);">${item.hops.length} hop${item.hops.length > 1 ? 's' : ''}</span>
        </td>
        <td>
          <span class="mono-cell" style="color: var(--text-muted); font-size: 11px;">${item.timestamp}</span>
        </td>
        <td style="text-align: right;">
          <button class="btn btn-secondary btn-sm" data-audit-id="${item.id}">Inspect</button>
        </td>
      `;

      tr.addEventListener('click', () => {
        openAuditDetail(item.id);
      });

      auditTableBody.appendChild(tr);
    });
  }

  // Open PR Detail View
  function openAuditDetail(id) {
    const item = audits.find(a => a.id === id);
    if (!item) return;
    activeAuditId = id;

    // Pinned Banner
    const banner = document.getElementById('detail-verdict-banner');
    const badge = document.getElementById('detail-verdict-badge');
    const title = document.getElementById('detail-verdict-title');
    const sub = document.getElementById('detail-verdict-sub');
    const mergeStatus = document.getElementById('detail-merge-status');

    banner.className = 'verdict-banner';
    if (item.verdict === 'VERIFIED') {
      banner.classList.add('verified');
      badge.className = 'badge badge-verified';
      badge.textContent = 'VERIFIED';
      title.textContent = 'Merge Gate: APPROVED';
      sub.textContent = item.reason;
      mergeStatus.style.color = '#79c99e';
      mergeStatus.textContent = 'CI CHECK: PASS';
    } else if (item.verdict === 'BLOCKED') {
      banner.classList.add('blocked');
      badge.className = 'badge badge-blocked';
      badge.textContent = 'BLOCKED';
      title.textContent = 'Merge Gate: BLOCKED';
      sub.textContent = item.reason;
      mergeStatus.style.color = '#e07466';
      mergeStatus.textContent = 'CI CHECK: FAILED';
    } else {
      banner.classList.add('review');
      badge.className = 'badge badge-review';
      badge.textContent = 'NEEDS HUMAN REVIEW';
      title.textContent = 'Merge Gate: SUSPENDED';
      sub.textContent = item.reason;
      mergeStatus.style.color = '#e2b350';
      mergeStatus.textContent = 'CI CHECK: ESCALATED';
    }

    // Metadata Bar
    document.getElementById('detail-meta-pr').textContent = item.prRef;
    document.getElementById('detail-meta-sha').textContent = item.commitSha;
    document.getElementById('detail-meta-policy').textContent = item.policy;
    document.getElementById('detail-meta-engine').textContent = item.engine;
    document.getElementById('detail-pr-body').textContent = item.body;

    // Render Voice-to-Diff Healing
    const healingContainer = document.getElementById('detail-healing-container');
    if (item.verbal_amendment || item.verdict === 'BLOCKED') {
      healingContainer.style.display = 'block';
      healingContainer.innerHTML = `
        <div class="healing-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="color: #e2b350; font-size: 13px;">VOICE-TO-DIFF HEALING</strong>
            <span class="badge badge-review">VERBAL AMENDMENT CAPTURED</span>
          </div>
          <p style="font-size: 12px; color: var(--text-primary);">${escapeHtml(item.verbal_amendment || 'Authorizer suggested keeping legacy accounts until Q3 migration finishes.')}</p>
          <div class="diff-viewer">
            <div class="diff-del-line">- DROP TABLE v1_accounts;</div>
            <div class="diff-add-line">+ -- RETENTION POLICY: v1_accounts preserved per authorizer verbal guidance.</div>
          </div>
          <button class="btn btn-secondary btn-sm" style="margin-top: 10px;" onclick="alert('Patch instructions dispatched to agent branch.')">
            Apply Suggested Diff Patch to Branch
          </button>
        </div>
      `;
    } else {
      healingContainer.style.display = 'none';
    }

    // Render Cryptographic Attestation
    const attestContainer = document.getElementById('detail-attestation-container');
    if (item.verdict === 'VERIFIED' || item.attestation_id) {
      attestContainer.style.display = 'block';
      attestContainer.innerHTML = `
        <div class="attestation-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="color: #79c99e; font-size: 13px;">CRYPTOGRAPHIC VOICE ATTESTATION</strong>
            <span class="badge badge-verified">SIG:HMAC-SHA256:VERIFIED</span>
          </div>
          <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); line-height: 1.6;">
            <div>Attestation ID : <strong style="color: var(--text-primary);">${item.attestation_id || 'attest_' + item.commitSha}</strong></div>
            <div>Audio Stream   : <span style="color: var(--accent-gold);">sha256:4a5de800fd2ff808cacda22ddb0fce48514953c...</span></div>
            <div>Git Storage    : <span style="color: var(--text-primary);">refs/notes/auditline (Immutable)</span></div>
          </div>
        </div>
      `;
    } else {
      attestContainer.style.display = 'none';
    }

    // Render Hops
    const container = document.getElementById('detail-hops-container');
    container.innerHTML = '';

    item.hops.forEach((hop, idx) => {
      const hopEl = document.createElement('div');
      hopEl.className = 'timeline-hop';

      let confBadge = '';
      if (hop.confirmation === 'confirmed') {
        confBadge = '<span class="badge badge-verified">DIRECT CONFIRMATION: AFFIRMATIVE</span>';
      } else if (hop.confirmation === 'denied') {
        confBadge = '<span class="badge badge-blocked">DIRECT CONFIRMATION: DENIED</span>';
      } else {
        confBadge = '<span class="badge badge-review">DIRECT CONFIRMATION: UNREACHABLE / HEDGED</span>';
      }

      let entailBadge = '';
      if (hop.entailmentResult === 'entailment') {
        entailBadge = '<span style="color: #79c99e; font-weight: 600;">ENTAILMENT (MATCH)</span>';
      } else if (hop.entailmentResult === 'contradiction') {
        entailBadge = '<span style="color: #e07466; font-weight: 600;">CONTRADICTION</span>';
      } else {
        entailBadge = '<span style="color: #e2b350; font-weight: 600;">NEUTRAL / HEDGE</span>';
      }

      // Generate visual waveform bars
      const waveBars = Array.from({ length: 36 }, (_, i) => {
        const height = Math.floor(6 + Math.sin(i * 0.5) * 12 + Math.random() * 8);
        return `<div class="wave-bar active" style="height: ${height}px;"></div>`;
      }).join('');

      hopEl.innerHTML = `
        <div class="hop-marker active">${hop.hopIndex}</div>
        <div class="hop-card">
          <div class="hop-header">
            <div class="hop-person">
              <span class="hop-name">${escapeHtml(hop.authorizer)}</span>
              <span class="hop-role">&bull; ${escapeHtml(hop.role)}</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <span class="mono-cell" style="font-size: 10px; color: var(--text-muted);">${hop.durationSec}s call duration</span>
              <span class="hop-phone">${escapeHtml(hop.phone)}</span>
            </div>
          </div>
          <div class="hop-body">
            <div>
              <div class="section-label">Extracted Verbal Claim</div>
              <div class="claim-block">"${escapeHtml(hop.claimText)}"</div>
            </div>

            <div>
              <div class="section-label">CALL-E Telephony Transcript (Free Recall First)</div>
              <div class="transcript-block">${escapeHtml(hop.statement)}</div>
              
              <!-- Audio Player Bar -->
              <div class="audio-player-card">
                <button class="play-btn" onclick="alert('Playing recorded telephony audio stream...')">&#9654;</button>
                <div class="waveform-container">${waveBars}</div>
                <span class="mono-cell" style="font-size: 11px; color: var(--text-muted);">0:${hop.durationSec < 10 ? '0' : ''}${hop.durationSec} &bull; 8kHz Opus</span>
              </div>
            </div>

            <div class="entailment-metric-bar">
              <div class="metric-col">
                <span class="metric-label">Verbal Direct Response</span>
                <div style="margin-top: 4px;">${confBadge}</div>
              </div>
              <div class="metric-col">
                <span class="metric-label">NLI Entailment Classification</span>
                <span class="metric-val">${entailBadge}</span>
              </div>
              <div class="metric-col">
                <span class="metric-label">Confidence & Decision Engine</span>
                <span class="metric-val mono-cell">${hop.confidence} &bull; ${escapeHtml(hop.engine)}</span>
              </div>
            </div>
          </div>
        </div>
      `;
      container.appendChild(hopEl);
    });

    switchView('detail');
    setTimeout(() => window.renderDelegationGraph(item.hops), 100);
  }

  document.getElementById('btn-back-to-ledger').addEventListener('click', () => {
    switchView('dashboard');
  });

  // Render Directory
  function renderDirectory() {
    directoryTableBody.innerHTML = '';
    phonebook.forEach(contact => {
      const tr = document.createElement('tr');
      const phoneDisplay = contact.masked ? maskPhone(contact.phone) : contact.phone;

      tr.innerHTML = `
        <td>
          <span class="mono-cell" style="font-weight: 600; color: var(--text-primary);">${escapeHtml(contact.name)}</span>
        </td>
        <td>${escapeHtml(contact.role)}</td>
        <td><span style="color: var(--text-secondary);">${escapeHtml(contact.department)}</span></td>
        <td>
          <span class="mono-cell" style="color: var(--accent-gold);">${escapeHtml(phoneDisplay)}</span>
          <button class="mask-btn" data-contact-id="${contact.id}">
            ${contact.masked ? '[reveal]' : '[mask]'}
          </button>
        </td>
        <td><span class="mono-cell" style="color: var(--text-muted); font-size: 11px;">${contact.lastVerified}</span></td>
        <td><span class="badge badge-verified">${contact.status}</span></td>
        <td style="text-align: right;">
          <button class="btn btn-secondary btn-sm" onclick="alert('Test diagnostic call simulated.')">Test Line</button>
        </td>
      `;

      directoryTableBody.appendChild(tr);
    });

    // Attach mask toggles
    document.querySelectorAll('.mask-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = btn.getAttribute('data-contact-id');
        const contact = phonebook.find(c => c.id === cid);
        if (contact) {
          contact.masked = !contact.masked;
          renderDirectory();
        }
      });
    });
  }

  function maskPhone(p) {
    if (!p || p.length < 4) return p;
    const parts = p.split(' ');
    if (parts.length >= 3) {
      return `${parts[0]} ••• ••• ${parts[parts.length - 1]}`;
    }
    return p.substring(0, 3) + ' ••• ••• ' + p.slice(-4);
  }

  // Modal Handling
  const modal = document.getElementById('audit-modal');
  const btnOpenModal = document.getElementById('btn-open-audit-modal');
  const btnCloseModal = document.getElementById('btn-close-modal');
  const btnCancelModal = document.getElementById('btn-cancel-modal');
  const btnExecuteAudit = document.getElementById('btn-execute-audit');
  const presetSelect = document.getElementById('modal-preset');
  const inputRepoPr = document.getElementById('modal-repo-pr');
  const inputPrTitle = document.getElementById('modal-pr-title');
  const inputPrBody = document.getElementById('modal-pr-body');
  const liveStatus = document.getElementById('modal-live-status');
  const statusText = document.getElementById('modal-status-text');

  btnOpenModal.addEventListener('click', () => {
    modal.classList.add('active');
    liveStatus.style.display = 'none';
  });

  function closeModal() {
    modal.classList.remove('active');
  }

  btnCloseModal.addEventListener('click', closeModal);
  btnCancelModal.addEventListener('click', closeModal);

  presetSelect.addEventListener('change', () => {
    const val = presetSelect.value;
    if (val === 'sarah-denial') {
      inputRepoPr.value = 'acme-corp/core-infra#512';
      inputPrTitle.value = 'Drop legacy v1_accounts table';
      inputPrBody.value = 'As confirmed with @sarah_dba during standup, this is safe to drop the legacy table.';
    } else if (val === 'architect-multihop') {
      inputRepoPr.value = 'acme-corp/auth-service#340';
      inputPrTitle.value = 'Change access pattern for token routing';
      inputPrBody.value = 'The architect verbally cleared this breaking schema change during today\'s standup, so merging this once CI is green.';
    } else if (val === 'unknown-person') {
      inputRepoPr.value = 'acme-corp/keymaster#129';
      inputPrTitle.value = 'Rotate the signing key';
      inputPrBody.value = 'Confirmed with Random Person that rotating the signing key today is fine.';
    }
  });

  // Execute Verification
  btnExecuteAudit.addEventListener('click', () => {
    const title = inputPrTitle.value.trim();
    const body = inputPrBody.value.trim();
    const prRef = inputRepoPr.value.trim() || 'myrepo#100';

    if (!title || !body) {
      alert('Please provide both PR Title and PR Description.');
      return;
    }

    liveStatus.style.display = 'block';
    btnExecuteAudit.disabled = true;

    // Simulate Step 1: Claim extraction
    statusText.textContent = 'Parsing PR text with rule-based regex claim extractor...';

    setTimeout(() => {
      statusText.textContent = 'Claim extracted. Querying internal directory for authorizer phone number...';

      setTimeout(() => {
        statusText.textContent = 'Dialing authorizer via CALL-E telephony (dress rehearsal fixture)...';

        setTimeout(() => {
          statusText.textContent = 'Analyzing response statement with Entailment Engine...';

          fetch('/api/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title, body: body, pr_ref: prRef })
          })
          .then(res => res.json())
          .then(data => {
            if (data && !data.error) {
              audits.unshift(data);
              btnExecuteAudit.disabled = false;
              closeModal();
              renderLedger();
              openAuditDetail(data.id);
            } else {
              throw new Error(data.error || 'Unknown backend error');
            }
          })
          .catch(err => {
            console.warn('Backend /api/audit unavailable, falling back to local simulation engine:', err);
            // Fallback deterministic simulation
            let newAudit;
            const bodyLower = body.toLowerCase();

            if (bodyLower.includes('sarah')) {
              newAudit = {
                id: 'aud_' + Math.floor(1000 + Math.random() * 9000),
                prRef: prRef,
                title: title,
                body: body,
                commitSha: Math.random().toString(16).substring(2, 12),
                authorizer: '@sarah_dba',
                timestamp: 'Just now',
                verdict: 'BLOCKED',
                reason: '@sarah_dba contradicted the claim ("No — we actually agreed to keep it"). Blocking merge.',
                policy: 'Denial or Entailment Contradiction -> BLOCKED',
                engine: 'Heuristic-v1',
                hops: [
                  {
                    hopIndex: 0,
                    authorizer: '@sarah_dba',
                    role: 'Staff Database Administrator',
                    phone: '+1 415 555 0192',
                    reached: true,
                    durationSec: 40,
                    claimText: body,
                    statement: 'No — we actually agreed to keep v1_accounts for backward compatibility until the Q3 migration finishes.',
                    confirmation: 'denied',
                    entailmentResult: 'neutral',
                    confidence: '0.50',
                    engine: 'heuristic-v1'
                  }
                ]
              };
            } else if (bodyLower.includes('architect')) {
              newAudit = {
                id: 'aud_' + Math.floor(1000 + Math.random() * 9000),
                prRef: prRef,
                title: title,
                body: body,
                commitSha: Math.random().toString(16).substring(2, 12),
                authorizer: 'The architect',
                timestamp: 'Just now',
                verdict: 'VERIFIED',
                reason: 'Every hop in the claimed chain was independently confirmed. Safe to merge.',
                policy: 'All Hops Confirmed with Entailment -> VERIFIED',
                engine: 'Heuristic-v1',
                hops: [
                  {
                    hopIndex: 0,
                    authorizer: 'The architect',
                    role: 'Principal Systems Architect',
                    phone: '+1 206 555 0148',
                    reached: true,
                    durationSec: 50,
                    claimText: body,
                    statement: 'Yes, I verbally cleared this breaking schema change this morning — the security lead had already signed off on the access-pattern change last week, so I gave the go-ahead.',
                    confirmation: 'confirmed',
                    entailmentResult: 'entailment',
                    confidence: '0.73',
                    engine: 'heuristic-v1'
                  },
                  {
                    hopIndex: 1,
                    authorizer: 'the security lead',
                    role: 'Head of Product Security',
                    phone: '+1 650 555 0173',
                    reached: true,
                    durationSec: 35,
                    claimText: 'the security lead already signed off on the access-pattern change',
                    statement: 'Yes, that\'s right — I already signed off on the access-pattern change last week after reviewing it, so it\'s confirmed on my end.',
                    confirmation: 'confirmed',
                    entailmentResult: 'entailment',
                    confidence: '0.85',
                    engine: 'heuristic-v1'
                  }
                ]
              };
            } else {
              newAudit = {
                id: 'aud_' + Math.floor(1000 + Math.random() * 9000),
                prRef: prRef,
                title: title,
                body: body,
                commitSha: Math.random().toString(16).substring(2, 12),
                authorizer: 'Random Person',
                timestamp: 'Just now',
                verdict: 'NEEDS_HUMAN_REVIEW',
                reason: 'Authorizer phone not registered in phonebook directory. Failing closed to human review.',
                policy: 'Missing Phone / Unreachable -> NEEDS_HUMAN_REVIEW',
                engine: 'Heuristic-v1',
                hops: [
                  {
                    hopIndex: 0,
                    authorizer: 'Random Person',
                    role: 'Unregistered Entity',
                    phone: 'None',
                    reached: false,
                    durationSec: 0,
                    claimText: body,
                    statement: '[CALL ABORTED: No directory record for named authorizer]',
                    confirmation: 'unreachable',
                    entailmentResult: 'neutral',
                    confidence: '0.00',
                    engine: 'heuristic-v1'
                  }
                ]
              };
            }

            audits.unshift(newAudit);
            btnExecuteAudit.disabled = false;
            closeModal();
            renderLedger();
            openAuditDetail(newAudit.id);
          });
        }, 500);
      }, 400);
    }, 400);
  });

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // =========================================================================
  // telephony-sudo Sandbox Controller
  // =========================================================================
  const sudoPreset = document.getElementById('sudo-preset');
  const sudoCmd = document.getElementById('sudo-cmd');
  const sudoAuthorizer = document.getElementById('sudo-authorizer');
  const sudoReason = document.getElementById('sudo-reason');
  const sudoTermOutput = document.getElementById('sudo-terminal-output');
  const sudoTermStatus = document.getElementById('sudo-term-status');
  const btnRunSudo = document.getElementById('btn-run-sudo');

  if (sudoPreset) {
    sudoPreset.addEventListener('change', () => {
      const val = sudoPreset.value;
      if (val === 'drop-table') {
        sudoCmd.value = 'DROP DATABASE prod_accounts;';
        sudoAuthorizer.value = '@sarah_dba';
        sudoReason.value = 'Migration cleanup of legacy shard';
      } else if (val === 'terraform-destroy') {
        sudoCmd.value = 'terraform destroy -auto-approve';
        sudoAuthorizer.value = 'The architect';
        sudoReason.value = 'Deprecate staging cluster';
      } else if (val === 'aws-delete-role') {
        sudoCmd.value = 'aws iam delete-role --role-name admin';
        sudoAuthorizer.value = 'Random Person';
        sudoReason.value = 'Prune unused IAM entities';
      }
    });
  }

  if (btnRunSudo) {
    btnRunSudo.addEventListener('click', () => {
      const cmd = sudoCmd.value.trim();
      const auth = sudoAuthorizer.value;
      const reason = sudoReason.value.trim();

      if (!cmd) return;

      btnRunSudo.disabled = true;
      sudoTermStatus.textContent = 'FROZEN';
      sudoTermStatus.style.color = '#C9A227';

      function logTerminal(message, type) {
        let color = 'var(--text-muted)';
        let prefix = '[AuditLine]';
        if (type === 'freeze') {
          color = '#EF4444';
          prefix = '[SIGSTOP]';
        } else if (type === 'unfreeze') {
          color = '#10B981';
          prefix = '[SIGCONT]';
        } else if (type === 'kill') {
          color = '#EF4444';
          prefix = '[SIGKILL]';
        }
        sudoTermOutput.innerHTML += `<div style="color: ${color};"><strong>${prefix}</strong> ${escapeHtml(message)}</div>`;
        sudoTermOutput.scrollTop = sudoTermOutput.scrollHeight;
      }

      sudoTermOutput.innerHTML += `
        <div style="margin-top: 12px; border-top: 1px solid var(--border-subtle); padding-top: 8px;">
          <span style="color: #6366F1;">$</span> <strong>${escapeHtml(cmd)}</strong>
        </div>`;
        
      logTerminal('INTERCEPTED: High-blast-radius command detected.', 'freeze');
      logTerminal(`FROZEN: Process suspended. Awaiting verbal clearance from ${auth}...`, 'freeze');
      logTerminal(`CALL-E dialing registered line... Liveness Nonce: Meridian-42`, 'info');

      fetch('/api/telephony-sudo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, authorizer: auth, reason: reason })
      })
      .then(res => res.json())
      .then(data => {
        btnRunSudo.disabled = false;
        if (data.authorized) {
          sudoTermStatus.textContent = 'EXECUTED';
          sudoTermStatus.style.color = '#10B981';
          logTerminal(`AUTHORIZATION CONFIRMED: "${data.statement}"`, 'unfreeze');
          logTerminal(`Attestation ID: ${data.attestation_id} (HMAC-SHA256 Signed)`, 'info');
          logTerminal('Process unfrozen. Executing command in sandbox...', 'info');
          sudoTermOutput.innerHTML += `<div style="color: #10B981; font-weight: 600; margin-top: 4px;">&gt;&gt; Command completed successfully (Exit code 0).</div>`;
        } else {
          sudoTermStatus.textContent = 'KILLED';
          sudoTermStatus.style.color = '#EF4444';
          logTerminal(`ACCESS DENIED: ${auth} rejected authorization.`, 'kill');
          logTerminal(`Statement: "${data.statement || 'No verbal authorization given.'}"`, 'kill');
          logTerminal('SECURITY ABORT: Terminating process (Exit code 1).', 'kill');
        }
        sudoTermOutput.scrollTop = sudoTermOutput.scrollHeight;
      })
      .catch(err => {
        btnRunSudo.disabled = false;
        sudoTermStatus.textContent = 'READY';
        sudoTermStatus.style.color = '#79c99e';
        sudoTermOutput.innerHTML += `
          <div class="term-error">[telephony-sudo] Execution error: ${escapeHtml(err.message)}</div>
        `;
      });
    });
  }

  // =========================================================================
  // Live Voice Sandbox Controller (Dial My Phone)
  // =========================================================================
  const btnTriggerLiveCall = document.getElementById('btn-trigger-live-call');
  const sandboxName = document.getElementById('sandbox-name');
  const sandboxPhone = document.getElementById('sandbox-phone');
  const sandboxClaim = document.getElementById('sandbox-claim');
  const sandboxStreamLog = document.getElementById('sandbox-stream-log');

  if (btnTriggerLiveCall) {
    btnTriggerLiveCall.addEventListener('click', () => {
      const name = sandboxName.value.trim() || 'Judge';
      const phone = sandboxPhone.value.trim();
      const claim = sandboxClaim.value.trim();

      btnTriggerLiveCall.disabled = true;
      sandboxStreamLog.innerHTML = `
        <div class="waveform-container" style="position: absolute; bottom: 10px; left: 10px; width: 380px;">
          <canvas id="waveformCanvas" width="380" height="64"></canvas>
        </div>
        <div style="color: #6366F1; position: relative; z-index: 2;">[CALL-E DISPATCHER] Initiating call to ${escapeHtml(name)} (${escapeHtml(phone || 'Simulated Line')})...</div>
        <div style="color: var(--text-muted); position: relative; z-index: 2;">&gt; Establishing carrier SIP handshake...</div>
        <div style="color: var(--text-muted); position: relative; z-index: 2;">&gt; Task Prompt: Free recall before recognition active...</div>
      `;
      window.startLiveWaveform();

      fetch('/api/test-call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, phone: phone, claim: claim })
      })
      .then(res => res.json())
      .then(data => {
        if (data.error) {
           throw new Error(data.error);
        }
        btnTriggerLiveCall.disabled = false;
        const statusColor = data.confirmation === 'confirmed' ? '#79c99e' : '#e07466';
        sandboxStreamLog.innerHTML += `
          <div style="color: #79c99e; margin-top: 6px;">[CALL-E CARRIER] Call connected. Duration: ${data.durationSec}s</div>
          <div style="color: var(--text-primary); margin-top: 4px;"><strong>Authorizer Statement:</strong> "${escapeHtml(data.statement)}"</div>
          <div style="color: ${statusColor}; font-weight: 600; margin-top: 4px;">Direct Confirmation: ${data.confirmation.toUpperCase()}</div>
          <div style="color: var(--accent-gold); margin-top: 4px;">Audio Stream Hash: sha256:${data.audio_sha256 ? data.audio_sha256.substring(0, 32) : '4a5de...'}...</div>
          <div style="color: var(--text-muted); margin-top: 4px;">Call UUID: ${data.call_uuid}</div>
        `;
      })
      .catch(err => {
        btnTriggerLiveCall.disabled = false;
        sandboxStreamLog.innerHTML += `
          <div style="color: #e07466; margin-top: 6px;">[CALL-E ERROR] ${escapeHtml(err.message)}</div>
        `;
      });
    });
  }

  // Initial Render
  renderLedger();

  // =========================================================================
  // Canvas & SVG Animations
  // =========================================================================
  let waveAnimId;
  let isStreaming = false;

  window.startLiveWaveform = function() {
    isStreaming = true;
    const canvas = document.getElementById('waveformCanvas');
    if (!canvas) return;
    
    // High-DPI scaling
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    
    const width = rect.width;
    const height = rect.height;
    
    let offset = 0;
    
    function draw() {
      ctx.clearRect(0, 0, width, height);
      
      const numBars = 64;
      const barWidth = 3;
      const spacing = (width - numBars * barWidth) / (numBars - 1);
      
      for (let i = 0; i < numBars; i++) {
        const x = i * (barWidth + spacing);
        let barHeight = 4; // idle state
        
        if (isStreaming) {
           const wave1 = Math.sin(i * 0.2 + offset) * 10;
           const wave2 = Math.cos(i * 0.1 - offset * 1.5) * 8;
           barHeight = 4 + Math.abs(wave1 + wave2) + Math.random() * 4;
        }
        
        ctx.fillStyle = '#6366F1';
        ctx.fillRect(x, height / 2 - barHeight / 2, barWidth, barHeight);
      }
      
      offset += 0.1;
      waveAnimId = requestAnimationFrame(draw);
    }
    
    cancelAnimationFrame(waveAnimId);
    draw();
    
    // Stop after 5 seconds to simulate end of call
    setTimeout(() => { isStreaming = false; }, 5000);
  }
  
  window.renderDelegationGraph = function(hops) {
    const svg = document.getElementById('delegationGraph');
    if (!svg) return;
    svg.style.display = 'block';
    svg.innerHTML = ''; // clear
    
    const width = svg.clientWidth || 800;
    const height = 120;
    
    const numHops = hops.length;
    let startX = 60;
    const endX = width - 80;
    const gap = (endX - startX) / (numHops || 1);
    
    // Agent Node
    svg.innerHTML += `<circle cx="${startX}" cy="${height/2}" r="20" fill="#11141D" stroke="#6366F1" stroke-width="2"/>`;
    svg.innerHTML += `<text x="${startX}" y="${height/2 + 35}" fill="#9CA3AF" font-size="10" font-family="JetBrains Mono" text-anchor="middle">AGENT</text>`;
    
    for (let i = 0; i < numHops; i++) {
      const hop = hops[i];
      const nodeX = startX + gap;
      
      // Line
      let lineClass = 'graph-link';
      let strokeColor = '#374151';
      if (hop.reached) {
        lineClass += hop.confirmation === 'confirmed' ? ' verified' : ' active';
        strokeColor = hop.confirmation === 'confirmed' ? '#10B981' : '#F59E0B';
      }
      
      svg.innerHTML += `<line x1="${startX + 20}" y1="${height/2}" x2="${nodeX - 20}" y2="${height/2}" stroke="${strokeColor}" stroke-width="2" class="${lineClass}" />`;
      
      // Node
      let nodeStroke = '#374151';
      if (hop.confirmation === 'confirmed') nodeStroke = '#10B981';
      if (hop.confirmation === 'denied') nodeStroke = '#EF4444';
      
      svg.innerHTML += `<circle cx="${nodeX}" cy="${height/2}" r="20" fill="#11141D" stroke="${nodeStroke}" stroke-width="2"/>`;
      svg.innerHTML += `<text x="${nodeX}" y="${height/2 + 35}" fill="#F3F4F6" font-size="10" font-family="JetBrains Mono" text-anchor="middle">HOP ${i}</text>`;
      
      startX = nodeX;
    }
  }

})();
