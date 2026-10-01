#!/usr/bin/env node

/**
 * Crawl ALL videos ever uploaded on YouTube Studio channel via Chrome DevTools Protocol (CDP)
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const OUTPUT_FILE = path.join(ROOT_DIR, 'output', 'all_channel_videos.json');
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

class StudioCrawler {
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

  async openContentTab() {
    const url = 'https://studio.youtube.com/channel/UCjQ4h6BGkjEY6hB0M9fDGIg/videos/upload?filter=%5B%5D&sort=%7B%22columnType%22%3A%22date%22%2C%22sortOrder%22%3A%22DESCENDING%22%7D';
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

  async setPageSizeTo50() {
    console.log('>> Setting rows per page to 50 (or max)...');
    await this.evaluate(`
      (() => {
        // Find rows per page dropdown or selector
        const pageSelector = document.querySelector('ytcp-table-footer ytcp-dropdown-trigger, ytcp-table-footer #page-size-select, #page-size-selector');
        if (pageSelector) {
          pageSelector.click();
          const inner = pageSelector.shadowRoot ? pageSelector.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
        }
      })()
    `);
    await sleep(2000);

    // Select 50
    await this.evaluate(`
      (() => {
        const items = Array.from(document.querySelectorAll('paper-item, tp-yt-paper-item, ytcp-text-menu-item, [role="option"]'));
        const opt50 = items.find(it => (it.textContent || '').trim() === '50' || (it.textContent || '').trim() === '30');
        if (opt50) opt50.click();
      })()
    `);
    await sleep(4000);
  }

  async extractCurrentPageVideos() {
    return await this.evaluate(`
      (() => {
        function deepQueryAll(selector, root = document.documentElement) {
          let results = Array.from(root.querySelectorAll(selector));
          const walkers = [root];
          while (walkers.length > 0) {
            const current = walkers.shift();
            if (current && current.shadowRoot) {
              results = results.concat(Array.from(current.shadowRoot.querySelectorAll(selector)));
              walkers.push(current.shadowRoot);
            }
            const children = current ? (current.children || []) : [];
            for (let i = 0; i < children.length; i++) walkers.push(children[i]);
          }
          return results;
        }

        const rows = deepQueryAll('ytcp-video-row');
        return rows.map(row => {
          const titleLink = row.querySelector('#video-title') || row.querySelector('a[href*="/video/"]');
          const href = titleLink ? (titleLink.getAttribute('href') || titleLink.href || '') : '';
          const match = href.match(/\\/video\\/([^\\/\\?]+)/);
          const videoId = match ? match[1] : null;
          const title = (titleLink ? (titleLink.innerText || titleLink.textContent || '') : '').trim();

          const visEl = row.querySelector('.visibility') || row.querySelector('[class*="visibility"]');
          const vis = visEl ? (visEl.innerText || visEl.textContent || '').trim() : '';

          const monEl = row.querySelector('.monetization') || row.querySelector('[class*="monetization"]');
          const mon = monEl ? (monEl.innerText || monEl.textContent || '').trim() : '';

          const dateEl = row.querySelector('.date') || row.querySelector('[class*="date"]');
          const date = dateEl ? (dateEl.innerText || dateEl.textContent || '').trim() : '';

          return {
            videoId,
            title,
            visibility: vis,
            monetization: mon,
            date
          };
        }).filter(v => v.videoId);
      })()
    `);
  }

  async goToNextPage() {
    return await this.evaluate(`
      (() => {
        function deepQueryAll(selector, root = document.documentElement) {
          let results = Array.from(root.querySelectorAll(selector));
          const walkers = [root];
          while (walkers.length > 0) {
            const current = walkers.shift();
            if (current && current.shadowRoot) {
              results = results.concat(Array.from(current.shadowRoot.querySelectorAll(selector)));
              walkers.push(current.shadowRoot);
            }
            const children = current ? (current.children || []) : [];
            for (let i = 0; i < children.length; i++) walkers.push(children[i]);
          }
          return results;
        }

        const nextBtns = deepQueryAll('#navigate-after, [aria-label="Next page" i], ytcp-icon-button[aria-label*="Next" i]');
        for (const btn of nextBtns) {
          const disabled = btn.disabled || btn.getAttribute('aria-disabled') === 'true' || btn.classList.contains('disabled');
          if (!disabled) {
            btn.click();
            const inner = btn.shadowRoot ? btn.shadowRoot.querySelector('button') : null;
            if (inner && !inner.disabled) inner.click();
            return true;
          }
        }
        return false;
      })()
    `);
  }
}

async function crawlAll() {
  console.log('==============================================');
  console.log('>> Starting Full Channel Crawler for ALL Videos');
  console.log('==============================================');

  const crawler = new StudioCrawler();
  await crawler.checkConnection();
  await crawler.openContentTab();

  const allVideos = new Map();
  let pageNumber = 1;

  try {
    console.log('>> Loading YouTube Studio Content page...');
    await sleep(8000);

    await crawler.setPageSizeTo50();
    await sleep(4000);

    while (true) {
      console.log(`\n>> Scraping Page ${pageNumber}...`);
      const pageVideos = await crawler.extractCurrentPageVideos();
      console.log(`>> Found ${pageVideos ? pageVideos.length : 0} videos on page ${pageNumber}.`);

      if (pageVideos && pageVideos.length > 0) {
        let newCount = 0;
        for (const v of pageVideos) {
          if (!allVideos.has(v.videoId)) {
            allVideos.set(v.videoId, v);
            newCount++;
          }
        }
        console.log(`>> Added ${newCount} new videos. (Total unique: ${allVideos.size})`);
      }

      console.log('>> Checking for next page...');
      const hasNext = await crawler.goToNextPage();
      if (!hasNext) {
        console.log('>> Reached last page! No more pages available.');
        break;
      }

      console.log('>> Loading next page...');
      await sleep(6000);
      pageNumber++;

      if (pageNumber > 50) {
        console.log('>> Reached safety page limit (50 pages). Stopping.');
        break;
      }
    }

    const videoList = Array.from(allVideos.values());
    console.log('\n==============================================');
    console.log(`>> CRAWL COMPLETE: Found ${videoList.length} total videos on the channel.`);
    console.log('==============================================');

    fs.mkdirSync(path.dirname(OUTPUT_FILE), { recursive: true });
    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(videoList, null, 2), 'utf8');
    console.log(`>> Saved full catalog to: ${OUTPUT_FILE}`);

    return videoList;
  } finally {
    await crawler.closeTab();
  }
}

if (require.main === module) {
  crawlAll().then(videos => {
    console.log(`\nSummary of Channel Videos (${videos.length}):`);
    videos.forEach((v, i) => {
      console.log(`[${i + 1}] ${v.videoId} | ${v.title.slice(0, 45)} | Vis: ${v.visibility.slice(0, 15)} | Mon: ${v.monetization} | Date: ${v.date}`);
    });
  }).catch(err => {
    console.error('Crawler failed:', err);
    process.exit(1);
  });
}

module.exports = { crawlAll };
