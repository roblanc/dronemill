const fs = require('fs');
const path = require('path');

const CDP_PORT = process.env.CHROME_CDP_PORT || 9222;
const OUTPUT_FILE = path.join(__dirname, '..', 'output', 'all_channel_videos_ascending.json');

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
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
    // Sort by date ascending to get from earliest video to latest
    const url = 'https://studio.youtube.com/channel/UCjQ4h6BGkjEY6hB0M9fDGIg/videos/upload?filter=%5B%5D&sort=%7B%22columnType%22%3A%22date%22%2C%22sortOrder%22%3A%22ASCENDING%22%7D';
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

async function run() {
  console.log('====================================================');
  console.log('>> Starting Full Channel Crawler (Earliest -> Latest)');
  console.log('====================================================');

  const crawler = new StudioCrawler();
  await crawler.checkConnection();
  console.log('>> Connected to Chrome CDP on port', CDP_PORT);

  await crawler.openContentTab();
  console.log('>> YouTube Studio Content tab opened (Sorting ASCENDING by Date)...');
  await sleep(8000);

  // Set rows per page to 50
  console.log('>> Selecting 50 items per page...');
  await crawler.evaluate(function() {
    const trigger = document.querySelector('ytcp-table-footer ytcp-dropdown-trigger') || document.querySelector('#page-size-select');
    if (trigger) {
      trigger.click();
      const b = trigger.shadowRoot ? trigger.shadowRoot.querySelector('button') : null;
      if (b) b.click();
    }
  });
  await sleep(1500);

  await crawler.evaluate(function() {
    const items = Array.from(document.querySelectorAll('paper-item, tp-yt-paper-item, ytcp-text-menu-item, [role="option"]'));
    const opt50 = items.find(it => (it.textContent || '').trim() === '50');
    if (opt50) opt50.click();
  });
  await sleep(4000);

  const allVideos = [];
  const seenIds = new Set();
  let page = 1;

  while (true) {
    console.log(`\n>> Scraping Page ${page}...`);
    const pageData = await crawler.evaluate(function() {
      const rows = Array.from(document.querySelectorAll('ytcp-video-row'));
      const items = rows.map(r => {
        const a = r.querySelector('#video-title') || r.querySelector('a[href*="/video/"]');
        const href = a ? (a.getAttribute('href') || '') : '';
        const match = href.match(/\/video\/([^\/\?]+)/);
        const videoId = match ? match[1] : null;
        const title = a ? a.innerText.trim() : '';

        const visEl = r.querySelector('.visibility') || r.querySelector('[class*="visibility"]');
        const visibility = visEl ? (visEl.innerText || visEl.textContent || '').trim() : '';

        const dateEl = r.querySelector('.date') || r.querySelector('[class*="date"]');
        const date = dateEl ? (dateEl.innerText || dateEl.textContent || '').trim() : '';

        return { videoId, title, visibility, date };
      }).filter(v => v.videoId);

      const footer = document.querySelector('ytcp-table-footer');
      const footerText = footer ? footer.innerText.replace(/\s+/g, ' ').trim() : '';
      
      const nextBtn = document.querySelector('#navigate-after, [aria-label="Next page" i], ytcp-icon-button[aria-label*="Next" i]');
      let canNext = false;
      if (nextBtn) {
        const disabled = nextBtn.disabled || nextBtn.getAttribute('aria-disabled') === 'true' || nextBtn.classList.contains('disabled');
        canNext = !disabled;
      }

      return { items, footerText, canNext };
    });

    if (!pageData || !pageData.items || pageData.items.length === 0) {
      console.log('>> No videos found on this page. Re-checking or ending.');
      break;
    }

    let addedCount = 0;
    for (const item of pageData.items) {
      if (!seenIds.has(item.videoId)) {
        seenIds.add(item.videoId);
        allVideos.push(item);
        addedCount++;
        console.log(` [${allVideos.length}] ${item.videoId} | ${item.title.slice(0, 50)} | ${item.date || item.visibility}`);
      }
    }

    console.log(`>> Page ${page} summary: +${addedCount} videos (Total unique indexed: ${allVideos.length}). Footer: "${pageData.footerText}"`);

    if (!pageData.canNext) {
      console.log('>> Reached final page!');
      break;
    }

    console.log('>> Clicking Next Page...');
    await crawler.evaluate(function() {
      const nextBtn = document.querySelector('#navigate-after, [aria-label="Next page" i], ytcp-icon-button[aria-label*="Next" i]');
      if (nextBtn) {
        nextBtn.click();
        const inner = nextBtn.shadowRoot ? nextBtn.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
      }
    });

    await sleep(4000);
    page++;
    if (page > 30) {
      console.warn('>> Exceeded max safety page limit (30). Stopping pagination.');
      break;
    }
  }

  console.log(`\n====================================================`);
  console.log(`>> CRAWL COMPLETE: Found ${allVideos.length} videos in total!`);
  console.log(`====================================================`);

  fs.mkdirSync(path.dirname(OUTPUT_FILE), { recursive: true });
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(allVideos, null, 2), 'utf8');
  console.log(`>> Saved full ordered catalog to: ${OUTPUT_FILE}`);

  await crawler.closeTab();
}

run().catch(err => {
  console.error('Fatal crawler error:', err);
  process.exit(1);
});
