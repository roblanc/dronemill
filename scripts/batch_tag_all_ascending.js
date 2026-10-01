#!/usr/bin/env node

/**
 * Batch Tag Products across ALL Channel Videos in Chronological Ascending Order (Earliest -> Latest)
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const VIDEOS_FILE = path.join(ROOT_DIR, 'output', 'all_channel_videos_ascending.json');
const PROGRESS_FILE = path.join(ROOT_DIR, 'output', 'tagging_all_channel_progress.json');
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

function saveProgress(progress) {
  fs.mkdirSync(path.dirname(PROGRESS_FILE), { recursive: true });
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify(progress, null, 2), 'utf8');
}

function getSmartSearchQuery(title = '') {
  const t = title.toLowerCase();
  if (t.includes('study') || t.includes('reading') || t.includes('valedictorian') || t.includes('academia') || t.includes('focus') || t.includes('library') || t.includes('physics') || t.includes('math') || t.includes('history') || t.includes('scholar') || t.includes('spinoza') || t.includes('socrates')) {
    return 'Noise Cancelling Headphones';
  }
  if (t.includes('space') || t.includes('star') || t.includes('mars') || t.includes('neptune') || t.includes('jupiter') || t.includes('saturn') || t.includes('uranus') || t.includes('pluto') || t.includes('titan') || t.includes('planet') || t.includes('galaxy') || t.includes('nebula') || t.includes('cosmic') || t.includes('moon') || t.includes('supermoon') || t.includes('asteroid') || t.includes('astronaut')) {
    return 'Galaxy Star Projector';
  }
  if (t.includes('sleep') || t.includes('noise') || t.includes('binaural') || t.includes('delta') || t.includes('theta') || t.includes('rest') || t.includes('dream') || t.includes('night') || t.includes('calm') || t.includes('insomnia') || t.includes('healing')) {
    return 'Bluetooth Sleep Headphones';
  }
  if (t.includes('retro') || t.includes('cassette') || t.includes('mallsoft') || t.includes('analog') || t.includes('video store') || t.includes('arcade')) {
    return 'Retro Bluetooth Speaker';
  }
  return 'Bluetooth Sleep Headphones';
}

class StudioClient {
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

  async openVideoEditTab(videoId) {
    const url = `https://studio.youtube.com/video/${videoId}/edit`;
    const res = await fetch(`http://127.0.0.1:${this.port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
    if (!res.ok) throw new Error(`Failed to create Chrome tab: ${res.statusText}`);
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

async function tagVideo(videoId, title = '', maxProducts = 2) {
  const client = new StudioClient(CDP_PORT);
  await client.checkConnection();

  try {
    await client.openVideoEditTab(videoId);
    await sleep(6500);

    // Check if products already tagged
    const existingStatus = await client.evaluate(function() {
      const btn = document.querySelector('#shopping-toolbar-edit') || document.querySelector('[aria-label*="tagged products" i]');
      if (btn) {
        const text = (btn.textContent || btn.innerText || btn.getAttribute('aria-label') || '').trim();
        if (text.match(/\d+\s+tagged product/i)) return text;
      }
      const container = document.querySelector('#shopping-toolbar-edit');
      if (container && container.parentElement) {
        const pText = container.parentElement.innerText || '';
        if (pText.match(/\d+\s+tagged product/i)) return pText.trim();
      }
      return null;
    });

    if (existingStatus) {
      console.log(`  [ALREADY TAGGED] "${existingStatus}" - Skipping.`);
      return { success: true, status: 'already_tagged', details: existingStatus };
    }

    const searchQuery = getSmartSearchQuery(title);
    console.log(`  >> Search Query: "${searchQuery}" (tagging up to ${maxProducts} items)`);

    // Step 1: Open Tag products dialog
    const opened = await client.evaluate(function() {
      const btn = document.querySelector('#shopping-toolbar-edit') ||
                  document.querySelector('[aria-label="Edit products"]') ||
                  document.querySelector('[aria-label="Tag products"]');
      if (btn) {
        btn.click();
        const inner = btn.shadowRoot ? btn.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
        return true;
      }
      return false;
    });

    if (!opened) {
      console.log(`  [!] Shopping / Tag button not found for video ${videoId}.`);
      return { success: false, reason: 'Shopping button not found' };
    }

    await sleep(3000);

    // Step 2: Fill search input
    const searchFound = await client.evaluate(`
      (() => {
        const input = document.querySelector('input[placeholder*="Search products"]');
        if (input) {
          input.focus();
          input.click();
          input.value = ${JSON.stringify(searchQuery)};
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        }
        return false;
      })()
    `);

    if (!searchFound) {
      console.log(`  [!] Search input not found in shopping dialog.`);
      return { success: false, reason: 'Search input not found' };
    }

    // Trigger Enter key
    await client.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    await client.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });

    await sleep(4000);

    // Step 3: Tag top items
    const tagResult = await client.evaluate(`
      (() => {
        const addBtns = Array.from(document.querySelectorAll('ytcp-icon-button[aria-label*="Tag product"], button[aria-label*="Tag product"], ytcp-icon-button.tag-product-button'));
        let taggedCount = 0;
        const target = ${maxProducts};
        for (const btn of addBtns.slice(0, target)) {
          btn.click();
          const inner = btn.shadowRoot ? btn.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
          taggedCount++;
        }
        return { found: addBtns.length, tagged: taggedCount };
      })()
    `);

    console.log(`  >> Tagged: ${tagResult.tagged} items (from ${tagResult.found} catalog results).`);
    await sleep(2000);

    // Step 4: Click Next
    await client.evaluate(function() {
      const nextBtn = Array.from(document.querySelectorAll('ytcp-button, button')).find(b => b.textContent && b.textContent.trim() === 'Next');
      if (nextBtn) {
        nextBtn.click();
        const inner = nextBtn.shadowRoot ? nextBtn.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
      }
    });

    await sleep(3000);

    // Step 5: Click Done
    await client.evaluate(function() {
      const btns = Array.from(document.querySelectorAll('ytcp-button, button'));
      const doneBtn = btns.find(b => b.textContent && b.textContent.trim() === 'Done');
      if (doneBtn) {
        doneBtn.click();
        const inner = doneBtn.shadowRoot ? doneBtn.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
      }
    });

    await sleep(3500);

    // Step 6: Save changes
    const saveStatus = await client.evaluate(function() {
      const saveBtn = document.querySelector('#save-button, ytcp-button#save-button, [aria-label="Save"]');
      if (saveBtn) {
        const disabled = saveBtn.disabled || saveBtn.getAttribute('aria-disabled') === 'true';
        if (!disabled) {
          saveBtn.click();
          const inner = saveBtn.shadowRoot ? saveBtn.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
          return 'Saved';
        }
        return 'Save disabled (already saved)';
      }
      return 'Save button not found';
    });

    console.log(`  >> Save status: ${saveStatus}`);
    await sleep(2500);

    return {
      success: true,
      status: 'tagged',
      query: searchQuery,
      taggedCount: tagResult.tagged
    };
  } catch (err) {
    console.error(`  [ERROR] Tagging error for ${videoId}:`, err.message);
    return { success: false, error: err.message };
  } finally {
    await client.closeTab();
  }
}

async function main() {
  if (!fs.existsSync(VIDEOS_FILE)) {
    console.error('Error: Videos file not found at', VIDEOS_FILE);
    process.exit(1);
  }

  const videos = JSON.parse(fs.readFileSync(VIDEOS_FILE, 'utf8'));
  const progress = loadProgress();

  console.log('================================================================');
  console.log(`>> Starting Batch Product Tagging Across ${videos.length} Videos (Ascending)`);
  console.log('================================================================');

  let processedCount = 0;
  let taggedCount = 0;
  let alreadyTaggedCount = 0;
  let errorCount = 0;

  for (let i = 0; i < videos.length; i++) {
    const v = videos[i];
    const vid = v.videoId;
    const title = v.title || '';
    const date = v.date ? v.date.replace('\n', ' - ') : '';

    console.log(`\n[${i + 1}/${videos.length}] Video: ${vid} | "${title.slice(0, 50)}" | ${date}`);

    // If already recorded in progress file as completed, skip
    if (progress[vid] && progress[vid].success && progress[vid].status === 'tagged') {
      console.log(`  [CACHED] Already processed in progress file. Skipping.`);
      alreadyTaggedCount++;
      continue;
    }

    const res = await tagVideo(vid, title, 2);
    progress[vid] = {
      title,
      date,
      timestamp: new Date().toISOString(),
      ...res
    };
    saveProgress(progress);

    processedCount++;
    if (res.success) {
      if (res.status === 'tagged') taggedCount++;
      else if (res.status === 'already_tagged') alreadyTaggedCount++;
    } else {
      errorCount++;
    }

    // Brief pause between videos
    await sleep(2500);
  }

  console.log('\n================================================================');
  console.log(`>> ALL DONE! Summary:`);
  console.log(`   - Total Videos Processed: ${processedCount}`);
  console.log(`   - Newly Tagged: ${taggedCount}`);
  console.log(`   - Already Tagged: ${alreadyTaggedCount}`);
  console.log(`   - Errors / Unmodified: ${errorCount}`);
  console.log('================================================================');
}

main().catch(err => {
  console.error('Fatal batch tagger error:', err);
  process.exit(1);
});
