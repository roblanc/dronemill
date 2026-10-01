#!/usr/bin/env node

/**
 * YouTube Studio - Automated Product Tagging via Chrome DevTools Protocol (CDP)
 * 
 * Usage:
 *   node tag-products-studio.js <video_id> [search_query] [--count=2]
 *   node tag-products-studio.js --published
 *   node tag-products-studio.js --scheduled
 *   node tag-products-studio.js --latest [N] [search_query]
 *   node tag-products-studio.js --all [search_query]
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const HISTORY_FILE = path.join(ROOT_DIR, 'output', 'upload_history.json');
const CDP_PORT = process.env.CHROME_CDP_PORT || 9222;

async function getWebSocketClass() {
  try {
    const mod = await import('/usr/share/nodejs/ws/index.js');
    return mod.default || mod;
  } catch (e1) {
    try {
      const mod = await import('ws');
      return mod.default || mod;
    } catch (e2) {
      if (typeof WebSocket !== 'undefined') return WebSocket;
      throw new Error('WebSocket module not found.');
    }
  }
}

function sleep(ms) {
  return new Promise(res => setTimeout(res, ms));
}

class StudioCDPClient {
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

  async openVideoEditTab(videoId) {
    const url = `https://studio.youtube.com/video/${videoId}/edit`;
    const res = await fetch(`http://127.0.0.1:${this.port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
    if (!res.ok) throw new Error(`Failed to create Chrome tab: ${res.statusText}`);
    const tab = await res.json();
    this.tabId = tab.id;

    const WS = await getWebSocketClass();
    this.ws = new WS(tab.webSocketDebuggerUrl);

    await new Promise((resolve, reject) => {
      this.ws.on('open', resolve);
      this.ws.on('error', reject);
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
      const handler = (buf) => {
        try {
          const msg = JSON.parse(buf.toString());
          if (msg.id === id) {
            this.ws.off('message', handler);
            if (msg.error) reject(msg.error);
            else resolve(msg.result);
          }
        } catch (e) {
          reject(e);
        }
      };
      this.ws.on('message', handler);
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    });
    if (res && res.exceptionDetails) {
      throw new Error(res.exceptionDetails.text || 'CDP Evaluation Exception');
    }
    return res ? (res.result ? res.result.value : res) : null;
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

function getSmartSearchQuery(title = '') {
  const t = title.toLowerCase();
  if (t.includes('sleep') || t.includes('dream') || t.includes('night') || t.includes('insomnia') || t.includes('rest')) {
    return 'Bluetooth Sleep Headphones';
  }
  if (t.includes('study') || t.includes('focus') || t.includes('work') || t.includes('reading') || t.includes('library') || t.includes('academia') || t.includes('school') || t.includes('classroom')) {
    return 'Noise Cancelling Headphones';
  }
  if (t.includes('space') || t.includes('cosmic') || t.includes('stars') || t.includes('observatory') || t.includes('asteroid')) {
    return 'Galaxy Star Projector';
  }
  if (t.includes('rain') || t.includes('thunder') || t.includes('storm') || t.includes('ocean') || t.includes('water') || t.includes('pool')) {
    return 'Bluetooth Sleep Headphones';
  }
  return 'Bluetooth Sleep Headphones';
}

async function tagProductsForVideo(videoId, customQuery = null, maxProducts = 2) {
  console.log(`\n========================================`);
  console.log(`>> Starting Product Tagging for Video: ${videoId}`);
  console.log(`========================================`);

  const client = new StudioCDPClient(CDP_PORT);
  await client.checkConnection();

  try {
    console.log(`>> Opening YouTube Studio editor for [${videoId}]...`);
    await client.openVideoEditTab(videoId);

    // Wait for initial page load
    console.log(`>> Waiting for YouTube Studio interface to load...`);
    await sleep(6500);

    // Check if products are already tagged
    const existingStatus = await client.evaluate(`
      (() => {
        const btn = document.querySelector('#shopping-toolbar-edit') || document.querySelector('[aria-label*="tagged products" i]');
        if (btn) {
          const text = (btn.textContent || btn.innerText || btn.getAttribute('aria-label') || '').trim();
          if (text.match(/\\d+\\s+tagged product/i)) {
            return text;
          }
        }
        // Also check parent text
        const container = document.querySelector('#shopping-toolbar-edit');
        if (container && container.parentElement) {
          const pText = container.parentElement.innerText || '';
          if (pText.match(/\\d+\\s+tagged product/i)) {
            return pText.trim();
          }
        }
        return null;
      })()
    `);

    if (existingStatus) {
      console.log(`[OK] Video ${videoId} ALREADY has products tagged: "${existingStatus}". Skipping.`);
      return { success: true, videoId, status: 'already_tagged', details: existingStatus };
    }

    // Get Video Title for smart search query if not provided
    let videoTitle = '';
    try {
      videoTitle = await client.evaluate(`
        (() => {
          const titleInput = document.querySelector('#textbox[aria-label*="title" i], [aria-label="Title (required)"], ytcp-social-suggestions-textbox #textbox');
          return titleInput ? (titleInput.textContent || titleInput.value || '').trim() : document.title;
        })()
      `);
    } catch (_) {}

    const searchQuery = customQuery || getSmartSearchQuery(videoTitle);
    console.log(`>> Video Title: "${videoTitle || 'Unknown'}"`);
    console.log(`>> Search Query for Products: "${searchQuery}" (tagging up to ${maxProducts} products)`);

    // Step 1: Open Tag products / Shopping Edit button
    console.log(`>> Opening Shopping / Tag products dialog...`);
    const openedShopping = await client.evaluate(`
      (() => {
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
      })()
    `);

    if (!openedShopping) {
      console.log(`[!] Shopping / Tag products button not found for video ${videoId}.`);
      return { success: false, reason: 'Shopping button not found' };
    }

    await sleep(3000);

    // Step 2: Focus and type search query into product search input
    console.log(`>> Searching for "${searchQuery}" in products catalog...`);
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
      console.log(`[!] Product search input box not found in dialog.`);
      return { success: false, reason: 'Search input not found' };
    }

    // Trigger Enter key to perform search
    await client.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    await client.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });

    console.log(`>> Waiting for search results...`);
    await sleep(4000);

    // Step 3: Tag top N products
    console.log(`>> Tagging up to ${maxProducts} products...`);
    const tagResult = await client.evaluate(`
      (() => {
        const addBtns = Array.from(document.querySelectorAll('ytcp-icon-button[aria-label*="Tag product"], button[aria-label*="Tag product"], ytcp-icon-button.tag-product-button'));
        let taggedCount = 0;
        const targetCount = ${maxProducts};
        for (const btn of addBtns.slice(0, targetCount)) {
          btn.click();
          const inner = btn.shadowRoot ? btn.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
          taggedCount++;
        }
        return {
          found: addBtns.length,
          tagged: taggedCount
        };
      })()
    `);

    console.log(`>> Tag Result: Tagged ${tagResult.tagged} products (from ${tagResult.found} available options).`);
    await sleep(2000);

    // Step 4: Click "Next" button in the dialog
    console.log(`>> Clicking "Next" step...`);
    const nextResult = await client.evaluate(`
      (() => {
        const nextBtn = Array.from(document.querySelectorAll('ytcp-button, button')).find(b => b.textContent && b.textContent.trim() === 'Next');
        if (nextBtn) {
          nextBtn.click();
          const inner = nextBtn.shadowRoot ? nextBtn.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
          return 'Clicked Next';
        }
        return 'Next not found';
      })()
    `);
    console.log(`>> Next Step: ${nextResult}`);
    await sleep(3500);

    // Step 5: Click "Done" on timestamps step
    console.log(`>> Completing dialog ("Done")...`);
    const doneResult = await client.evaluate(`
      (() => {
        const btns = Array.from(document.querySelectorAll('ytcp-button, button'));
        const doneBtn = btns.find(b => b.textContent && b.textContent.trim() === 'Done');
        if (doneBtn) {
          doneBtn.click();
          const inner = doneBtn.shadowRoot ? doneBtn.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
          return 'Clicked Done';
        }
        return 'Done not found';
      })()
    `);
    console.log(`>> Dialog status: ${doneResult}`);
    await sleep(4000);

    // Step 6: Save changes on main YouTube Studio page
    console.log(`>> Saving main video details...`);
    const mainSaveResult = await client.evaluate(`
      (() => {
        const saveBtn = document.querySelector('#save-button, ytcp-button#save-button, [aria-label="Save"]');
        if (saveBtn) {
          const disabled = saveBtn.disabled || saveBtn.getAttribute('aria-disabled') === 'true';
          if (!disabled) {
            saveBtn.click();
            const inner = saveBtn.shadowRoot ? saveBtn.shadowRoot.querySelector('button') : null;
            if (inner) inner.click();
            return 'Main Save Clicked';
          }
          return 'Save button disabled / already saved';
        }
        return 'Save button not found';
      })()
    `);
    console.log(`>> Save status: ${mainSaveResult}`);
    await sleep(3000);

    // Verification screenshot
    const shotPath = `/tmp/yt_tagged_${videoId}.png`;
    await client.captureScreenshot(shotPath);
    console.log(`>> Verification screenshot saved to: ${shotPath}`);
    console.log(`[SUCCESS] Products successfully tagged for video: ${videoId}`);

    return {
      success: true,
      videoId,
      query: searchQuery,
      taggedCount: tagResult ? tagResult.tagged : 0,
      screenshot: shotPath
    };
  } catch (err) {
    console.error(`[ERROR] Failed tagging products for ${videoId}:`, err.message);
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
YouTube Studio Product Tagger (CDP)
-----------------------------------
Usage:
  node tag-products-studio.js <video_id> [search_query] [--count=2]
  node tag-products-studio.js --published
  node tag-products-studio.js --scheduled
  node tag-products-studio.js --latest [N] [search_query]
  node tag-products-studio.js --all [search_query]

Options:
  --count=N         Number of products to tag per video (default: 2)
  --port=PORT       CDP remote debugging port (default: 9222)
  --help, -h        Show this help message

Examples:
  node scripts/tag-products-studio.js PzkHP0arItU "Bluetooth Sleep Headphones"
  node scripts/tag-products-studio.js --published
  node scripts/tag-products-studio.js --scheduled
    `);
    process.exit(0);
  }

  let countArg = 2;
  const countMatch = args.find(a => a.startsWith('--count='));
  if (countMatch) {
    countArg = parseInt(countMatch.split('=')[1], 10) || 2;
  }

  const cleanArgs = args.filter(a => !a.startsWith('--count=') && !a.startsWith('--port='));
  const history = loadHistoryVideos();

  if (cleanArgs[0] === '--published') {
    const now = new Date();
    // Videos that are public or whose publish_at has passed
    const published = history.filter(v => {
      if (!v.video_id) return false;
      if (v.privacy === 'public') return true;
      if (v.publish_at && new Date(v.publish_at) <= now) return true;
      return false;
    });

    console.log(`>> Found ${published.length} published video(s) to process:`);
    for (const v of published) {
      console.log(` - [${v.video_id}] ${v.title.slice(0, 50)}`);
    }

    const results = [];
    for (let i = 0; i < published.length; i++) {
      const vid = published[i].video_id;
      console.log(`\n[${i + 1}/${published.length}] Processing ${vid}...`);
      const res = await tagProductsForVideo(vid, null, countArg);
      results.push(res);
      await sleep(2000);
    }
    console.log(`\n>> All published videos processed!`);
    console.log(JSON.stringify(results, null, 2));
    return;
  }

  if (cleanArgs[0] === '--scheduled') {
    const now = new Date();
    const scheduled = history.filter(v => {
      if (!v.video_id) return false;
      if (v.publish_at && new Date(v.publish_at) > now) return true;
      return false;
    });

    console.log(`>> Found ${scheduled.length} scheduled/upcoming video(s) to process:`);
    for (const v of scheduled) {
      console.log(` - [${v.video_id}] ${v.title.slice(0, 50)} (Publish: ${v.publish_at})`);
    }

    for (let i = 0; i < scheduled.length; i++) {
      const vid = scheduled[i].video_id;
      console.log(`\n[${i + 1}/${scheduled.length}] Processing ${vid}...`);
      await tagProductsForVideo(vid, null, countArg);
      await sleep(2000);
    }
    console.log(`\n>> All scheduled videos processed!`);
    return;
  }

  if (cleanArgs[0] === '--latest' || cleanArgs[0] === '--all') {
    const isAll = cleanArgs[0] === '--all';
    const limit = isAll ? 9999 : (parseInt(cleanArgs[1], 10) || 3);
    const query = (!isAll && isNaN(parseInt(cleanArgs[1], 10))) ? cleanArgs[1] : (cleanArgs[2] || null);

    const valid = history.filter(v => v.video_id);
    const targets = isAll ? valid : valid.slice(-limit);
    console.log(`>> Found ${targets.length} video(s) to process:`, targets.map(t => t.video_id));

    for (let i = 0; i < targets.length; i++) {
      const vid = targets[i].video_id;
      console.log(`\n[${i + 1}/${targets.length}] Processing ${vid}...`);
      await tagProductsForVideo(vid, query, countArg);
      await sleep(2000);
    }
    console.log(`\n>> Batch tagging complete!`);
    return;
  }

  const videoId = cleanArgs[0];
  const query = cleanArgs[1] || null;

  if (!videoId) {
    console.error('[!] Video ID is required.');
    process.exit(1);
  }

  const result = await tagProductsForVideo(videoId, query, countArg);
  if (!result.success) {
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = { tagProductsForVideo };
