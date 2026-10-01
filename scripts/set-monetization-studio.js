#!/usr/bin/env node

/**
 * YouTube Studio - Automated Monetization Activator via Chrome DevTools Protocol (CDP)
 * 
 * Usage:
 *   node set-monetization-studio.js <video_id>
 *   node set-monetization-studio.js --scheduled
 *   node set-monetization-studio.js --latest [N]
 *   node set-monetization-studio.js --all
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const HISTORY_FILE = path.join(ROOT_DIR, 'output', 'upload_history.json');
const CDP_PORT = process.env.CHROME_CDP_PORT || 9222;

function sleep(ms) {
  return new Promise(res => setTimeout(res, ms));
}

class StudioMonetizationClient {
  constructor(port = CDP_PORT) {
    this.port = port;
    this.ws = null;
    this.tabId = null;
    this.msgId = 0;
  }

  async checkConnection() {
    try {
      const res = await fetch(`http://127.0.0.1:${this.port}/json/version`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      throw new Error(`Cannot connect to Chrome on port ${this.port}. Is Chrome running with --remote-debugging-port=${this.port}?`);
    }
  }

  async openMonetizationTab(videoId) {
    const url = `https://studio.youtube.com/video/${videoId}/monetization`;
    const res = await fetch(`http://127.0.0.1:${this.port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
    if (!res.ok) throw new Error(`Failed to create Chrome tab: ${res.statusText}`);
    const tab = await res.json();
    this.tabId = tab.id;

    this.ws = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, { once: true });
      this.ws.addEventListener('error', reject, { once: true });
    });

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
        try {
          const msg = JSON.parse(event.data);
          if (msg.id === id) {
            this.ws.removeEventListener('message', handler);
            if (msg.error) reject(msg.error);
            else resolve(msg.result);
          }
        } catch (e) {
          reject(e);
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

  async captureScreenshot(outputPath) {
    try {
      const shot = await this.send('Page.captureScreenshot', { format: 'png' });
      if (shot && shot.data) {
        fs.writeFileSync(outputPath, Buffer.from(shot.data, 'base64'));
        return outputPath;
      }
    } catch (err) {
      console.warn(`[WARN] Screenshot capture failed: ${err.message}`);
    }
    return null;
  }
}

async function enableMonetizationForVideo(videoId) {
  console.log(`\n========================================`);
  console.log(`>> Checking Monetization for Video: ${videoId}`);
  console.log(`========================================`);

  const client = new StudioMonetizationClient(CDP_PORT);
  await client.checkConnection();

  try {
    console.log(`>> Opening Monetization page for [${videoId}]...`);
    await client.openMonetizationTab(videoId);
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

    console.log(`>> Current Monetization Status: "${currentStatus || 'Unknown'}"`);

    if (currentStatus && currentStatus.toLowerCase().startsWith('on')) {
      console.log(`[OK] Monetization is ALREADY ON for video ${videoId}.`);
      return { success: true, videoId, status: 'already_on' };
    }

    // Step 1: Open Dropdown / Options
    console.log(`>> Opening monetization options...`);
    await client.evaluate(function() {
      const el = document.querySelector('.m10n-text') || document.querySelector('ytcp-video-monetization .edit-button');
      if (el) el.click();
    });
    await sleep(2000);

    // Step 2: Select 'On' radio option
    console.log(`>> Selecting 'On' radio option...`);
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

    // Step 3: Click 'Next' button inside the container
    console.log(`>> Clicking 'Next' in container...`);
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

    // Step 4: Handle self-certification modal
    console.log(`>> Handling Ad-Suitability self-certification...`);
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
    console.log(`>> Certification Status: ${certResult}`);
    await sleep(4000);

    // Step 5: Save changes on main page
    console.log(`>> Saving main video monetization settings...`);
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
        return 'Save disabled (already saved)';
      }
      return 'Save button not found';
    });
    console.log(`>> Save result: ${saveRes}`);
    await sleep(4000);

    // Verification screenshot
    const shotPath = `/tmp/monetization_${videoId}.png`;
    await client.captureScreenshot(shotPath);

    const saveConfirmed = saveRes === 'Saved successfully!' || saveRes === 'Save disabled (already saved)';
    if (saveConfirmed) {
      console.log(`[SUCCESS] Monetization successfully turned ON for video: ${videoId}`);
    } else {
      console.log(`[FAIL] Monetization NOT confirmed saved for video: ${videoId} (saveResult: "${saveRes}"). Check ${shotPath}.`);
    }

    return { success: saveConfirmed, videoId, status: saveConfirmed ? 'enabled' : 'unconfirmed', saveResult: saveRes, certification: certResult };
  } catch (err) {
    console.error(`[ERROR] Failed to enable monetization for ${videoId}:`, err.message);
    return { success: false, error: err.message };
  } finally {
    await client.closeTab();
  }
}

function loadHistoryVideos() {
  if (!fs.existsSync(HISTORY_FILE)) return [];
  try {
    return JSON.parse(fs.readFileSync(HISTORY_FILE, 'utf8')) || [];
  } catch (e) {
    return [];
  }
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
YouTube Studio Monetization Activator (CDP)
-------------------------------------------
Usage:
  node set-monetization-studio.js <video_id>
  node set-monetization-studio.js --scheduled
  node set-monetization-studio.js --latest [N]
  node set-monetization-studio.js --all
    `);
    process.exit(0);
  }

  const history = loadHistoryVideos();

  if (args[0] === '--scheduled') {
    const scheduled = history.filter(v => v.video_id && v.publish_at);
    console.log(`>> Found ${scheduled.length} scheduled/upcoming video(s) to process:`);
    for (const v of scheduled) {
      console.log(` - [${v.video_id}] ${v.title.slice(0, 50)} (Publish: ${v.publish_at})`);
    }

    const results = [];
    for (let i = 0; i < scheduled.length; i++) {
      const v = scheduled[i];
      console.log(`\n========================================`);
      console.log(`[${i + 1}/${scheduled.length}] Processing ${v.video_id}...`);
      const res = await enableMonetizationForVideo(v.video_id);
      results.push(res);
      await sleep(2000);
    }
    console.log(`\n>> All scheduled videos processed!`);
    console.log(JSON.stringify(results, null, 2));
    return;
  }

  if (args[0] === '--latest' || args[0] === '--all') {
    const isAll = args[0] === '--all';
    const limit = isAll ? 9999 : (parseInt(args[1], 10) || 5);
    const valid = history.filter(v => v.video_id);
    const targets = isAll ? valid : valid.slice(-limit);

    console.log(`>> Processing ${targets.length} video(s)...`);
    for (let i = 0; i < targets.length; i++) {
      const v = targets[i];
      console.log(`\n[${i + 1}/${targets.length}] Processing ${v.video_id}...`);
      await enableMonetizationForVideo(v.video_id);
      await sleep(2000);
    }
    console.log(`\n>> Batch monetization complete!`);
    return;
  }

  const videoId = args[0];
  const res = await enableMonetizationForVideo(videoId);
  if (!res.success) process.exit(1);
}

if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = { enableMonetizationForVideo };
