/* ==========================================================================
   AuditLane — Verification Ledger Frontend Controller
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

  // Ledger persistence. Real source of truth is now the server's
  // .auditlane_ledger.json (see scripts/serve_ui.py and auditlane/ledger.py
  // — every real call result, from telephony-gate (the Claude Code hook) or
  // Voice Sandbox, gets appended there, durably, independent of any
  // browser). This array/localStorage pair is kept as a fast-render cache
  // and offline fallback only, not the authoritative store anymore.
  // audit_pr doesn't write here at all — it runs via the GitHub Actions
  // workflow and posts straight to the PR itself.
  const LEDGER_STORAGE_KEY = 'auditlane_ledger_v1';

  function persistAudits() {
    try {
      localStorage.setItem(LEDGER_STORAGE_KEY, JSON.stringify(audits));
    } catch (e) {
      console.warn('Could not cache ledger to localStorage:', e);
    }
  }

  (function loadCachedAudits() {
    try {
      const saved = localStorage.getItem(LEDGER_STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          audits = parsed;
        }
      }
    } catch (e) {
      console.warn('Could not load cached ledger, using seed data:', e);
    }
  })();

  // Load the REAL, durable ledger from the server. This overwrites
  // whatever cache/seed data rendered first — real results take priority
  // over any local guess the moment they're available.
  function loadRealLedger() {
    fetch('/api/ledger')
      .then(res => res.json())
      .then(serverAudits => {
        // A successful response — even an empty array, e.g. right after
        // a fresh install or a reset — is real, authoritative state and
        // must win over stale seed/cached data. Only an actual fetch
        // failure (below) should leave the seed/cache fallback in place.
        if (Array.isArray(serverAudits)) {
          audits = serverAudits;
          persistAudits();
          renderLedger();
        }
      })
      .catch(err => console.warn('Could not load real ledger from server:', err));
  }

  let currentFilter = 'all';
  let searchQuery = '';
  let activeAuditId = null;

  // DOM Elements
  const tabs = document.querySelectorAll('.nav-tab');
  const viewDashboard = document.getElementById('view-dashboard');
  const viewDetail = document.getElementById('view-detail');
  const viewLiveSandbox = document.getElementById('view-live-sandbox');
  const viewPhonebook = document.getElementById('view-phonebook');
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
    else if (viewName === 'live-sandbox') viewLiveSandbox.classList.add('active');
    else if (viewName === 'phonebook') {
      viewPhonebook.classList.add('active');
      renderDirectory();
    }
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

    // Voice-to-Diff Healing card removed — it always rendered a
    // hardcoded "DROP TABLE v1_accounts" patch for ANY BLOCKED verdict,
    // regardless of what the actual claim was about. No real diff/patch
    // generation exists in the backend to back this; showing it was
    // actively misleading rather than a demo nicety.
    const healingContainer = document.getElementById('detail-healing-container');
    if (healingContainer) healingContainer.style.display = 'none';

    // Render Cryptographic Attestation — only when one was genuinely
    // created (see auditlane/attestation.py); previously showed for
    // EVERY 'VERIFIED' verdict with a hardcoded fake hash identical
    // across every result, and claimed storage in "refs/notes/auditlane"
    // which isn't where it's actually saved.
    const attestContainer = document.getElementById('detail-attestation-container');
    const attestedHop = (item.hops || []).find(h => h.audioSha256) || {};
    if (item.attestation_id) {
      attestContainer.style.display = 'block';
      attestContainer.innerHTML = `
        <div class="attestation-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="color: #79c99e; font-size: 13px;">CRYPTOGRAPHIC VOICE ATTESTATION</strong>
            <span class="badge badge-verified">SIG:HMAC-SHA256:VERIFIED</span>
          </div>
          <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); line-height: 1.6;">
            <div>Attestation ID : <strong style="color: var(--text-primary);">${escapeHtml(item.attestation_id)}</strong></div>
            <div>Call UUID      : <span style="color: var(--accent-gold);">${escapeHtml(attestedHop.callUuid || 'n/a (dress rehearsal)')}</span></div>
            <div>Transcript Hash: <span style="color: var(--accent-gold);">${attestedHop.audioSha256 ? 'sha256:' + escapeHtml(attestedHop.audioSha256.substring(0, 40)) + '...' : 'n/a (dress rehearsal)'}</span></div>
            <div>Storage        : <span style="color: var(--text-primary);">.git/auditlane/attestations/ (local, HMAC-signed JSON)</span></div>
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
              
              <!-- No audio player, no waveform — CALL-E's API exposes call
                   transcripts, not recorded audio, so there's nothing
                   real to visualize or play back. Just the fact, in text. -->
              <div class="mono-cell" style="font-size: 11px; color: var(--text-muted); margin-top: 8px;">${hop.durationSec}s call duration &bull; transcript above is the full real record (CALL-E provides no audio recording)</div>
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

  // Render Directory — fetches the REAL phonebook.json via the backend
  // every time this view is opened, instead of the hardcoded stub data
  // `phonebook` was seeded with above (which never reflected reality).
  function renderDirectory() {
    fetch('/api/phonebook')
      .then(res => res.json())
      .then(data => {
        phonebook = Object.entries(data).map(([name, phone], i) => ({
          id: 'usr_' + i,
          name: name,
          role: 'Verified Contact',
          department: '—',
          phone: phone,
          masked: true,
          lastVerified: '—',
          status: 'Active'
        }));
        renderDirectoryTable();
      })
      .catch(err => {
        console.warn('Could not load phonebook:', err);
        phonebook = [];
        directoryTableBody.innerHTML = '<tr><td colspan="7" style="color: #e07466; padding: 16px;">Could not load the directory from the backend. Try reloading the page.</td></tr>';
      });
  }

  function renderDirectoryTable() {
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
          <button class="btn btn-secondary btn-sm test-line-btn" data-contact-id="${contact.id}">Test Line</button>
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
          renderDirectoryTable();
        }
      });
    });

    // Attach "Test Line" buttons — data-attribute + real listener, not
    // inline onclick with string-interpolated name/phone. A name
    // containing a single quote (e.g. "O'Brien") would have broken the
    // inline-onclick JS even with HTML-entity-escaping, since the
    // browser HTML-decodes the attribute BEFORE executing it as JS.
    document.querySelectorAll('.test-line-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = btn.getAttribute('data-contact-id');
        const contact = phonebook.find(c => c.id === cid);
        if (contact) window.testContactLine(contact.name, contact.phone);
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

  // Note: the "Run Pull Request Verification" modal (POST /api/audit) was
  // removed from the dashboard UI — it competed visually with
  // telephony-gate as if they were equal-weight capabilities, when
  // telephony-gate is the one with real, unconditional teeth. audit_pr
  // itself is untouched: the backend endpoint, entailment engine, claim
  // extractor, and GitHub Action integration all still work exactly as
  // before for anyone driving them directly (see scripts/run_verification.py,
  // the MCP server, or action.yml) — any past audit_pr result already in
  // the ledger still renders in full via openAuditDetail() below, this
  // just removed the one-off browser form for creating new ones.

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
  // Live Voice Sandbox Controller (Dial My Phone)
  // =========================================================================
  const btnTriggerLiveCall = document.getElementById('btn-trigger-live-call');
  const sandboxName = document.getElementById('sandbox-name');
  const sandboxPhone = document.getElementById('sandbox-phone');
  const sandboxClaim = document.getElementById('sandbox-claim');
  const sandboxStreamLog = document.getElementById('sandbox-stream-log');

  // "Test Line" button on the Phonebook view used to just show a fake
  // alert claiming a call was simulated — nothing actually happened.
  // This makes it real: jump to Voice Sandbox with that contact's actual
  // name/phone pre-filled, so the button genuinely does what it says.
  window.testContactLine = function (name, phone) {
    sandboxName.value = name;
    sandboxPhone.value = phone;
    switchView('live-sandbox');
  };

  function appendSandboxLog(html) {
    sandboxStreamLog.innerHTML += html;
  }

  // Renders one real CALL-E event line ("Bot is speaking: ...",
  // "Callee said: ...", "Call is ringing.", etc.) as it actually
  // happens — this is the real interrogation stream, not a canned
  // status sequence.
  function renderLiveCallEvent(evt) {
    const msg = evt.message || '';
    let color = 'var(--text-muted)';
    if (msg.startsWith('Bot is speaking:')) color = '#6366F1';
    else if (msg.startsWith('Callee said:')) color = '#79c99e';
    else if (/ringing|connected/i.test(msg)) color = 'var(--accent-gold)';
    appendSandboxLog(`<div style="color: ${color}; position: relative; z-index: 2;">&gt; ${escapeHtml(msg)}</div>`);
  }

  function renderSandboxFinalResult(data) {
    const statusColor = data.confirmation === 'confirmed' ? '#79c99e' : '#e07466';
    appendSandboxLog(`
      <div style="color: #79c99e; margin-top: 6px;">[CALL-E CARRIER] Call finished. Duration: ${data.durationSec}s</div>
      <div style="color: var(--text-primary); margin-top: 4px;"><strong>Authorizer Statement:</strong> "${escapeHtml(data.statement)}"</div>
      <div style="color: ${statusColor}; font-weight: 600; margin-top: 4px;">Direct Confirmation: ${data.confirmation.toUpperCase()}</div>
      <div style="color: var(--accent-gold); margin-top: 4px;">Transcript Hash: ${data.audio_sha256 ? 'sha256:' + data.audio_sha256.substring(0, 32) + '...' : 'n/a (dress rehearsal — no real call placed)'}</div>
      <div style="color: var(--text-muted); margin-top: 4px;">Call UUID: ${data.call_uuid || 'n/a (dress rehearsal — no real call placed)'}</div>
    `);
  }

  function runMockSandboxCall(name, phone, claim) {
    fetch('/api/test-call', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, phone: phone, claim: claim })
    })
    .then(res => res.json())
    .then(data => {
      if (data.error) throw new Error(data.error);
      btnTriggerLiveCall.disabled = false;
      renderSandboxFinalResult(data);
      // The server already appended the real, authoritative ledger
      // entry for this call before responding — just re-fetch it
      // instead of separately constructing a client-side copy that
      // could diverge from what's actually stored.
      loadRealLedger();
    })
    .catch(err => {
      btnTriggerLiveCall.disabled = false;
      appendSandboxLog(`<div style="color: #e07466; margin-top: 6px;">[CALL-E ERROR] ${escapeHtml(err.message)}</div>`);
    });
  }

  // Polls the real call's event log and status every 2s, rendering each
  // new transcript line as it happens, until CALL-E reports a terminal
  // status. 8-minute safety cap so a stuck/very long call can't poll
  // forever if something goes wrong on CALL-E's side.
  function pollLiveCall(callId, cursor, startedAt) {
    const POLL_MS = 2000;
    const MAX_MS = 8 * 60 * 1000;

    if (Date.now() - startedAt > MAX_MS) {
      btnTriggerLiveCall.disabled = false;
      appendSandboxLog(`<div style="color: #e07466; margin-top: 6px;">[CALL-E] Still not finished after 8 minutes — stopped polling here. Check the Audits ledger shortly; the call may still complete on CALL-E's side.</div>`);
      return;
    }

    const eventsUrl = '/api/live-call/events?call_id=' + encodeURIComponent(callId)
      + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');

    fetch(eventsUrl)
      .then(res => res.json())
      .then(eventsData => {
        (eventsData.data || []).forEach(renderLiveCallEvent);
        const nextCursor = eventsData.next_cursor || cursor;

        fetch('/api/live-call/status?call_id=' + encodeURIComponent(callId))
          .then(res => res.json())
          .then(statusData => {
            if (statusData.error) throw new Error(statusData.error);
            if (statusData.terminal) {
              btnTriggerLiveCall.disabled = false;
              renderSandboxFinalResult(statusData.result);
              loadRealLedger();
            } else {
              setTimeout(() => pollLiveCall(callId, nextCursor, startedAt), POLL_MS);
            }
          })
          .catch(err => {
            btnTriggerLiveCall.disabled = false;
            appendSandboxLog(`<div style="color: #e07466; margin-top: 6px;">[CALL-E ERROR] ${escapeHtml(err.message)}</div>`);
          });
      })
      .catch(() => {
        // A transient events-poll failure shouldn't kill the whole
        // stream — just retry on the next tick.
        setTimeout(() => pollLiveCall(callId, cursor, startedAt), POLL_MS);
      });
  }

  if (btnTriggerLiveCall) {
    btnTriggerLiveCall.addEventListener('click', () => {
      const name = sandboxName.value.trim() || 'Judge';
      const phone = sandboxPhone.value.trim();
      const claim = sandboxClaim.value.trim();

      btnTriggerLiveCall.disabled = true;
      sandboxStreamLog.innerHTML = `
        <div style="color: #6366F1;">[CALL-E DISPATCHER] Initiating call to ${escapeHtml(name)} (${escapeHtml(phone || 'Simulated Line')})...</div>
      `;

      fetch('/api/live-call/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, phone: phone, claim: claim })
      })
      .then(res => res.json())
      .then(data => {
        if (data.error) throw new Error(data.error);
        if (data.mock) {
          appendSandboxLog(`<div style="color: var(--text-muted); position: relative; z-index: 2;">&gt; Dress rehearsal / demo number — resolving instantly, no live call placed.</div>`);
          runMockSandboxCall(name, phone, claim);
          return;
        }
        appendSandboxLog(`<div style="color: var(--text-muted); position: relative; z-index: 2;">&gt; Real call created (${escapeHtml(data.call_id)}) — streaming the actual conversation below as it happens...</div>`);
        pollLiveCall(data.call_id, null, Date.now());
      })
      .catch(err => {
        btnTriggerLiveCall.disabled = false;
        appendSandboxLog(`<div style="color: #e07466; margin-top: 6px;">[CALL-E ERROR] ${escapeHtml(err.message)}</div>`);
      });
    });
  }

  // Initial Render — instant paint from cache/seed data, then replaced
  // by the real server ledger the moment it loads.
  renderLedger();
  loadRealLedger();

  // Background poll so entries written by a completely separate process
  // — the telephony-gate hook firing from another Claude Code session
  // entirely, e.g. one rooted at a different project — show up here
  // without anyone needing to manually refresh the tab. The browser has
  // no way to know that file changed on disk otherwise.
  setInterval(loadRealLedger, 5000);

  // =========================================================================
  // SVG Animations
  // =========================================================================
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
