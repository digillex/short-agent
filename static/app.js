'use strict';

// ── Health check ─────────────────────────────────────────────────────────────

async function checkHealth() {
  const btn = document.getElementById('checkHealthBtn');
  btn.disabled = true;
  btn.textContent = 'Checking…';

  setDot('dotApi', 'idle');
  setDot('dotKey', 'idle');
  setDot('dotOutput', 'idle');
  setText('statusApi', '—');
  setText('statusKey', '—');
  setText('statusOutput', '—');
  hide('statusMessage');

  try {
    const res = await fetch('/');
    const data = await res.json();

    setDot('dotApi', 'ok');
    setText('statusApi', data.status === 'ok' ? 'Online' : 'Warning');

    if (data.openai_key_set) {
      setDot('dotKey', 'ok');
      setText('statusKey', 'Configured');
    } else {
      setDot('dotKey', 'warn');
      setText('statusKey', 'Missing');
      show('statusMessage');
      document.getElementById('statusMessage').textContent =
        data.message || 'OPENAI_API_KEY is not set. Add it to your .env file.';
    }

    setDot('dotOutput', 'ok');
    setText('statusOutput', data.output_dir || './outputs');
  } catch (err) {
    setDot('dotApi', 'error');
    setText('statusApi', 'Offline');
    show('statusMessage');
    document.getElementById('statusMessage').textContent =
      'Could not reach the API. Is the server running?';
  }

  btn.disabled = false;
  btn.textContent = 'Check Health';
}

// ── Generate ─────────────────────────────────────────────────────────────────

async function generatePackages(event) {
  event.preventDefault();

  hide('errorBox');
  hide('resultsSection');
  show('loader');

  const btn = document.getElementById('generateBtn');
  btn.disabled = true;

  const payload = {
    channel_name: 'DIGI-TV',
    content_theme: val('contentTheme'),
    content_pillars: [
      'AI tools and automation',
      'future mobility and self-driving technology',
      'engineering and infrastructure',
      'digital business and creator economy',
      'social impact of technology',
    ],
    number_of_packages: parseInt(val('numPackages'), 10),
    duration_seconds: parseInt(val('durationSec'), 10),
    language: val('language'),
    platforms: ['YouTube Shorts', 'Facebook Reels', 'Instagram Reels', 'TikTok'],
    extra_instruction: val('extraInstruction'),
    save_output: true,
  };

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok || data.status === 'error') {
      showError(data.error || JSON.stringify(data));
    } else {
      renderResults(data);
    }
  } catch (err) {
    showError('Network error: ' + err.message);
  }

  hide('loader');
  btn.disabled = false;
}

// ── Render results ────────────────────────────────────────────────────────────

function renderResults(data) {
  const metaEl = document.getElementById('resultsMeta');
  const containerEl = document.getElementById('packagesContainer');
  containerEl.innerHTML = '';

  metaEl.innerHTML = `
    <div class="meta-item">Generated: <strong>${data.generated_at}</strong></div>
    <div class="meta-item">Channel: <strong>${data.channel_name}</strong></div>
    <div class="meta-item">Packages: <strong>${data.number_of_packages}</strong></div>
    ${data.output_json_file ? `<div class="file-link">📄 ${data.output_json_file}</div>` : ''}
    ${data.output_markdown_file ? `<div class="file-link">📝 ${data.output_markdown_file}</div>` : ''}
  `;

  data.packages.forEach((pkg, i) => {
    const card = buildPackageCard(pkg, i + 1);
    containerEl.appendChild(card);
  });

  show('resultsSection');
  document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildPackageCard(pkg, num) {
  const card = document.createElement('div');
  card.className = 'pkg-card';

  // Header
  card.innerHTML = `
    <div class="pkg-header">
      <div>
        <div class="pkg-num">Package ${num}</div>
        <div class="pkg-title">${esc(pkg.title || pkg.topic)}</div>
        <div class="pkg-topic">${esc(pkg.topic)}</div>
      </div>
      <div style="font-size:0.78rem;color:var(--text-muted);text-align:right;flex-shrink:0;">
        ${esc(pkg.angle || '')}
      </div>
    </div>
    <div class="pkg-body">

      <div class="pkg-section">
        <div class="pkg-section-title">Hook (first 3 seconds)</div>
        <div class="pkg-hook">${esc(pkg.hook)}</div>
      </div>

      <div class="pkg-divider"></div>

      <div class="pkg-section">
        <div class="pkg-section-title">
          Script
          ${copyBtn('script_' + num, pkg.script)}
        </div>
        <div class="pkg-section-content code-style" id="script_${num}">${esc(pkg.script)}</div>
      </div>

      <div class="pkg-section">
        <div class="pkg-section-title">
          Voiceover
          ${copyBtn('vo_' + num, pkg.voiceover)}
        </div>
        <div class="pkg-section-content code-style" id="vo_${num}">${esc(pkg.voiceover)}</div>
      </div>

      <div class="pkg-divider"></div>

      <div class="pkg-section">
        <div class="pkg-section-title">
          Scene Prompts
          ${copyBtn('scenes_' + num, Array.isArray(pkg.scene_prompts) ? pkg.scene_prompts.join('\n') : pkg.scene_prompts)}
        </div>
        <div class="scene-list">
          ${(pkg.scene_prompts || []).map((s, si) =>
            `<div class="scene-item"><strong>Scene ${si + 1}:</strong> ${esc(s)}</div>`
          ).join('')}
        </div>
      </div>

      <div class="pkg-divider"></div>

      <div class="pkg-section">
        <div class="pkg-section-title">
          Title &amp; Description
          ${copyBtn('titledesc_' + num, `${pkg.title}\n\n${pkg.description}\n\n${(pkg.hashtags || []).join(' ')}`)}
        </div>
        <div class="pkg-section-content" style="margin-bottom:8px;"><strong>${esc(pkg.title)}</strong></div>
        <div class="pkg-section-content">${esc(pkg.description)}</div>
      </div>

      <div class="pkg-section">
        <div class="pkg-section-title">Hashtags</div>
        <div class="hashtag-list">
          ${(pkg.hashtags || []).map(h => `<span class="hashtag">${esc(h)}</span>`).join('')}
        </div>
      </div>

      <div class="pkg-section">
        <div class="pkg-section-title">Music Mood</div>
        <div class="pkg-section-content">${esc(pkg.music_mood)}</div>
      </div>

      <div class="pkg-divider"></div>

      <div class="pkg-section">
        <div class="pkg-section-title">Platform Notes</div>
        <div class="platform-grid">
          ${Object.entries(pkg.platform_notes || {}).map(([k, v]) => `
            <div class="platform-item">
              <div class="platform-name">${esc(k)}</div>
              <div>${esc(v)}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="pkg-section">
        <div class="pkg-section-title">Upload Checklist</div>
        <div class="checklist-list">
          ${(pkg.upload_checklist || []).map(item =>
            `<div class="checklist-item">${esc(item)}</div>`
          ).join('')}
        </div>
      </div>

      <div class="pkg-section">
        <div class="pkg-section-title">Risk Check</div>
        <div class="risk-box">${esc(pkg.risk_check)}</div>
      </div>

    </div>
  `;

  return card;
}

// ── Copy to clipboard ─────────────────────────────────────────────────────────

function copyBtn(id, text) {
  const encodedText = encodeURIComponent(text || '');
  return `<button class="copy-btn" onclick="copyText('${id}', decodeURIComponent('${encodedText}'))">Copy</button>`;
}

function copyText(id, text) {
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector(`[onclick*="'${id}'"]`);
    if (btn) {
      btn.textContent = 'Copied!';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.textContent = 'Copy';
        btn.classList.remove('copied');
      }, 2000);
    }
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function val(id) {
  return document.getElementById(id).value.trim();
}
function setText(id, text) {
  document.getElementById(id).textContent = text;
}
function setDot(id, state) {
  const el = document.getElementById(id);
  el.className = 'status-dot dot-' + state;
}
function show(id) { document.getElementById(id).classList.remove('hidden'); }
function hide(id) { document.getElementById(id).classList.add('hidden'); }
function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
function showError(msg) {
  const el = document.getElementById('errorBox');
  el.textContent = msg;
  show('errorBox');
}

// ── Auto-check on load ────────────────────────────────────────────────────────

window.addEventListener('DOMContentLoaded', () => {
  checkHealth();
});
