#!/usr/bin/env node

/**
 * Automate Monetization Activation + Self-Certification + Save on all Scheduled YouTube Videos
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const VIDEOS_FILE = path.join(ROOT_DIR, 'output', 'all_channel_videos_ascending.json');
const PROGRESS_FILE = path.join(ROOT_DIR, 'output', 'monetization_scheduled_progress.json');
const CDP_PORT = process.env.CHROME_CDP_PORT || 9222;

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function loadProgress() {
  if (!fs.existsSync(PROGRESS_FILE)) return {};
  try {
    return JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf8')) || {};
  } catch (e) {
    return {};
  }
}

function saveProgress(prog) {
  fs.mkdirSync(path.dirname(PROGRESS_FILE), { recursive: true });
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify(prog, null, 2), 'utf8');
}

class StudioCDP {
  constructor(port = CDP_PORT) {
    this.port = port;
    this.ws = null;
    this.tabId = null;
    this.msgId = 0;
  }

  async checkConnection() {
    const res = await fetch(`http://127.0.0.1:${this.port}/json/version`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async openTab(url) {
    const res = await fetch(`http://127.0.0.1:${this.port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
    if (!res.ok) throw new Error(`Failed to open tab: ${res.statusText}`);
    const tab = await res.json();
    this.tabId = tab.id;

    this.ws = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise(r => this.ws.addEventListener('open', r, { once: true }));
    return tab;
  }

  async closeTab() {
    if (this.ws) {
      try { this.ws.close(); } catch (_) {}
      this.ws = null;
    }
    if (this.tabId) {
      try {
        await fetch(`http://127.0.0.1:${this.port}/json/close/${this.tabId}`, { method: 'PUT' });
      } catch (_) {}
      this.tabId = null;
    }
  }

  send(method, params = {}) {
    const id = ++this.msgId;
    return new Promise((resolve, reject) => {
      const handler = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id === id) {
          this.ws.removeEventListener('message', handler);
          if (msg.error) reject(msg.error);
          else resolve(msg.result);
        }
      };
      this.ws.addEventListener('message', handler);
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(funcOrStr) {
    const expression = typeof funcOrStr === 'function' ? `(${funcOrStr.toString()})()` : funcOrStr;
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    });
    if (res && res.exceptionDetails) {
      throw new Error(res.exceptionDetails.text || 'CDP Evaluation Exception');
    }
    return res && res.result ? res.result.value : null;
  }
}

async function enableMonetizationForVideo(videoId, title = '') {
  console.log(`\n------------------------------------------------------------`);
  console.log(`>> Processing Video: [${videoId}] "${title.slice(0, 45)}"`);
  console.log(`------------------------------------------------------------`);

  const client = new StudioCDP(CDP_PORT);
  await client.checkConnection();

  try {
    const url = `https://studio.youtube.com/video/${videoId}/monetization`;
    await client.openTab(url);
    await sleep(8000);

    // Close feature callout if present
    await client.evaluate(function() {
      const closeBtn = document.querySelector('#monetization-callout #close-button, #monetization-callout button');
      if (closeBtn) closeBtn.click();
    });
    await sleep(1000);

    // Check current status
    const currentStatus = await client.evaluate(function() {
      const el = document.querySelector('ytcp-video-metadata-monetization');
      if (el) {
        const text = (el.innerText || el.textContent || '').trim();
        return text;
      }
      return null;
    });

    console.log(`   Current setting: "${currentStatus || 'Unknown'}"`);

    if (currentStatus && currentStatus.toLowerCase().startsWith('on')) {
      console.log(`   [ALREADY ON] Monetization is already ON. Skipping.`);
      return { success: true, status: 'already_on' };
    }

    // Step 1: Open Dropdown
    console.log(`   >> Opening options...`);
    await client.evaluate(function() {
      const el = document.querySelector('.m10n-text') || document.querySelector('ytcp-video-monetization .edit-button');
      if (el) el.click();
    });
    await sleep(2000);

    // Step 2: Click 'On'
    console.log(`   >> Selecting 'On' option...`);
    await client.evaluate(function() {
      const radios = Array.from(document.querySelectorAll('paper-radio-button, tp-yt-paper-radio-button, [role="radio"]'));
      const onR = radios.find(r => (r.textContent || '').trim().toLowerCase().startsWith('on') || r.name === 'ON' || r.getAttribute('name') === 'ON');
      if (onR) {
        onR.click();
        const inner = onR.shadowRoot ? onR.shadowRoot.querySelector('#radio') || onR.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
      }
    });
    await sleep(2000);

    // Step 3: Click 'Next'
    console.log(`   >> Clicking Next button in container...`);
    await client.evaluate(function() {
      const btns = Array.from(document.querySelectorAll('ytcp-button, button'));
      const nextBtn = btns.find(b => (b.textContent || '').trim() === 'Next');
      if (nextBtn) {
        nextBtn.click();
        const inner = nextBtn.shadowRoot ? nextBtn.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
      }
    });
    await sleep(4000);

    // Step 4: Self-certification dialog
    console.log(`   >> Handling self-certification modal...`);
    const certResult = await client.evaluate(function() {
      const checkboxes = Array.from(document.querySelectorAll('tp-yt-paper-checkbox, paper-checkbox, ytcp-checkbox-lit, [role="checkbox"]'));
      const noneBox = checkboxes.find(c => (c.textContent || '').trim().toLowerCase().includes('none of the above'));
      if (noneBox) {
        noneBox.click();
        const inner = noneBox.shadowRoot ? noneBox.shadowRoot.querySelector('#checkbox') || noneBox.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();

        const submitBtn = Array.from(document.querySelectorAll('ytcp-button, button')).find(b => (b.textContent || '').trim().toLowerCase() === 'submit');
        if (submitBtn) {
          submitBtn.click();
          const sInner = submitBtn.shadowRoot ? submitBtn.shadowRoot.querySelector('button') : null;
          if (sInner) sInner.click();
          return 'None checked & Submit clicked';
        }
        return 'None checked, submit not found';
      }
      return 'No cert dialog found';
    });
    console.log(`   >> Certification status: ${certResult}`);
    await sleep(4000);

    // Step 5: Click Save on main page
    console.log(`   >> Saving changes...`);
    const saveRes = await client.evaluate(function() {
      const saveBtn = document.querySelector('#save-button, ytcp-button#save-button, [aria-label="Save"]');
      if (saveBtn) {
        const disabled = saveBtn.disabled || saveBtn.getAttribute('aria-disabled') === 'true';
        if (!disabled) {
          saveBtn.click();
          const inner = saveBtn.shadowRoot ? saveBtn.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
          return 'Saved successfully!';
        }
        return 'Save button disabled';
      }
      return 'Save button not found';
    });
    console.log(`   >> Save Result: ${saveRes}`);
    await sleep(4000);

    return {
      success: true,
      status: 'enabled',
      saveResult: saveRes,
      certification: certResult
    };
  } catch (err) {
    console.error(`   [ERROR] ${err.message}`);
    return { success: false, error: err.message };
  } finally {
    await client.closeTab();
  }
}

async function main() {
  const allVideos = JSON.parse(fs.readFileSync(VIDEOS_FILE, 'utf8'));
  const scheduled = allVideos.filter(v => 'scheduled' in v || (v.date && v.date.toLowerCase().includes('scheduled')));
  const progress = loadProgress();

  console.log('============================================================');
  console.log(`>> Enabling Monetization on ${scheduled.length} Scheduled Videos`);
  console.log('============================================================');

  for (let i = 0; i < scheduled.length; i++) {
    const v = scheduled[i];
    const vid = v.videoId;
    console.log(`\n[${i + 1}/${scheduled.length}] Processing ${vid}...`);

    if (progress[vid] && progress[vid].success && progress[vid].status === 'enabled') {
      console.log(`   [CACHED] Already enabled in progress record. Skipping.`);
      continue;
    }

    const res = await enableMonetizationForVideo(vid, v.title);
    progress[vid] = {
      title: v.title,
      date: v.date,
      timestamp: new Date().toISOString(),
      ...res
    };
    saveProgress(progress);

    await sleep(2000);
  }

  console.log('\n============================================================');
  console.log('>> ALL SCHEDULED VIDEOS MONETIZATION COMPLETED!');
  console.log('============================================================');
}

main().catch(err => {
  console.error('Fatal runner error:', err);
  process.exit(1);
});
