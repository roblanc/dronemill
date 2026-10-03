#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const CACHE_DIR = path.join(process.env.HOME, 'Library/Application Support/Antigravity/Cache/Cache_Data');
const DEVTOOLS_FILE = path.join(process.env.HOME, 'Library/Application Support/Antigravity/DevToolsActivePort');

function usage() {
  console.error('Usage: node scripts/antigravity-image-worker.js [--max N] [--prompts path]');
}

function parseArgs() {
  const args = process.argv.slice(2);
  let slug = 'dronemill';
  let max = Infinity;
  let promptsFile = path.join(ROOT, 'output', 'ui_image_prompts.txt');
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--max') {
      max = Number(args[++i] || '0');
    } else if (args[i] === '--prompts') {
      promptsFile = args[++i] || null;
    } else if (!args[i].startsWith('--')) {
      slug = args[i];
    }
  }
  return { slug, max, promptsFile };
}

function cdpEndpoint() {
  const port = fs.readFileSync(DEVTOOLS_FILE, 'utf8').split(/\s+/)[0];
  if (!port) throw new Error(`No DevTools port in ${DEVTOOLS_FILE}`);
  return `http://127.0.0.1:${port}`;
}

function cacheKeyForFilename(filename) {
  return path.basename(filename, path.extname(filename)).replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '').toLowerCase();
}

function parsePrompts(slug, promptsFile) {
  const promptsPath = promptsFile ? path.resolve(promptsFile) : path.join(ROOT, 'output', 'ui_image_prompts.txt');
  const text = fs.readFileSync(promptsPath, 'utf8');
  if (promptsFile) {
    return [...text.matchAll(/--- Image ([^\s]+) ---\n([\s\S]*?)(?=\n--- Image [^\s]+ ---|$)/g)]
      .map((m) => ({
        filename: m[1].trim(),
        cacheKey: cacheKeyForFilename(m[1].trim()),
        prompt: m[2].trim(),
      }));
  }
  return [...text.matchAll(/--- Beat (\d+)\/(\d+) \(words [^)]+\) ---\n([\s\S]*?)(?=\n--- Beat \d+\/\d+|$)/g)]
    .map((m) => ({
      num: Number(m[1]),
      total: Number(m[2]),
      filename: `scene-${String(Number(m[1])).padStart(2, '0')}.png`,
      cacheKey: `scene_${String(Number(m[1])).padStart(2, '0')}`,
      prompt: m[3].trim(),
    }));
}

function findCacheFileForScene(cacheKey, sinceMs = 0) {
  const hits = [];
  for (const name of fs.readdirSync(CACHE_DIR)) {
    if (!name.endsWith('_0')) continue;
    const p = path.join(CACHE_DIR, name);
    const stat = fs.statSync(p);
    if (stat.mtimeMs < sinceMs) continue;
    let s;
    try {
      s = fs.readFileSync(p, 'latin1');
    } catch {
      continue;
    }
    if (s.toLowerCase().includes(`${cacheKey}_`)) hits.push({ path: p, mtime: stat.mtimeMs });
  }
  hits.sort((a, b) => a.mtime - b.mtime);
  return hits.at(-1)?.path || null;
}

function carveScene(cacheKey, dest, sinceMs = 0) {
  const p = findCacheFileForScene(cacheKey, sinceMs);
  if (!p) return null;
  const buf = fs.readFileSync(p);
  const soi = buf.indexOf(Buffer.from([0xff, 0xd8]));
  const eoi = buf.lastIndexOf(Buffer.from([0xff, 0xd9]));
  if (soi < 0 || eoi < soi) return null;
  const jpg = buf.subarray(soi, eoi + 2);
  fs.writeFileSync(dest, jpg);
  return { cache: path.basename(p), bytes: jpg.length };
}

function simplifiedPrompt(item) {
  const base = item.prompt.replace(
    /visualizing this narration beat:[\s\S]*?Keep the frame cinematic and specific:/,
    'Scene mood:'
  );
  return [
    `Generate exactly one image for ${item.filename}.`,
    'Return the image directly in chat.',
    'Requirements: cinematic cosmic horror ambience cover art, 16:9 widescreen landscape composition, no text, no watermark, no subtitles, no UI frame.',
    'If the generator uses a square canvas, keep all important subjects inside the center-safe crop.',
    `Prompt: ${base}`,
  ].join(' ');
}

async function tail(page) {
  return page.evaluate(() => document.body.innerText.slice(-3000)).catch(() => '');
}

async function assertAntigravityReady(page) {
  const text = await tail(page);
  if (/Authentication Required|Sign In|Open Settings|oauth2\.googleapis\.com|loadCodeAssist/i.test(text)) {
    const err = new Error(`Antigravity is not ready for image generation: ${text.trim().slice(0, 500)}`);
    err.unavailable = true;
    throw err;
  }
}

function latestResponseText(text) {
  return text.split(/Generate exactly one image for [\w.-]+\.png/).at(-1) || text;
}

function quotaInfo(text) {
  const latest = latestResponseText(text);
  if (!/RESOURCE_EXHAUSTED|quota.*exhausted|quota limit|capacity limit|message limit|try again later/i.test(latest)) {
    return null;
  }

  const atMatch = latest.match(/around\s+(\d{1,2}):(\d{2})\s+local/i);
  const relMatch = latest.match(/approximately\s+(\d+)\s+hours?(?:\s+and\s+(\d+)\s+minutes?)?/i)
    || latest.match(/approximately\s+(\d+)\s+minutes?/i);
  return {
    message: latest.trim().slice(-1200),
    localTime: atMatch ? `${atMatch[1].padStart(2, '0')}:${atMatch[2]}` : null,
    relative: relMatch ? relMatch[0] : null,
  };
}

async function waitCurrentReady(page) {
  for (let i = 0; i < 240; i++) {
    const text = await tail(page);
    const quota = quotaInfo(text);
    if (quota) return { status: 'quota', quota };
    if (!/(Working\.\.\.|Working\.|Generating with Gemini|Cancel \(⌃C\))/.test(latestResponseText(text))) {
      return { status: 'ready' };
    }
    await page.waitForTimeout(1000);
  }
  return { status: 'timeout' };
}

async function send(page, text) {
  await assertAntigravityReady(page);
  const selectors = [
    '[aria-label="Message input"]',
    '[data-testid="prompt-textarea"]',
    '[contenteditable="true"][role="textbox"]',
    '[role="textbox"]',
    'textarea',
    '[contenteditable="true"]',
  ];
  let input = null;
  for (const selector of selectors) {
    const candidate = page.locator(selector).last();
    if (!(await candidate.count().catch(() => 0))) continue;
    if (await candidate.isVisible().catch(() => false)) {
      input = candidate;
      break;
    }
  }
  if (!input) {
    const err = new Error(`Antigravity composer not found. Current page text: ${(await tail(page)).trim().slice(0, 500)}`);
    err.unavailable = true;
    throw err;
  }
  await input.click();
  await page.keyboard.insertText(text);
  await page.keyboard.press('Enter');
}

async function main() {
  const { slug, max, promptsFile } = parseArgs();
  const outDir = path.join(ROOT, 'images', 'inbox');
  fs.mkdirSync(outDir, { recursive: true });
  const prompts = parsePrompts(slug, promptsFile);
  const browser = await chromium.connectOverCDP(cdpEndpoint());
  const page = browser.contexts()[0].pages()[0];
  await page.keyboard.press('Escape').catch(() => {});
  await assertAntigravityReady(page);
  await waitCurrentReady(page);

  let generated = 0;
  for (const item of prompts) {
    const dest = path.join(outDir, item.filename);
    if (fs.existsSync(dest) && fs.statSync(dest).size > 10000) continue;
    if (generated >= max) break;

    console.log(`${item.filename} sending`);
    const sentAt = Date.now() - 1000;
    await send(page, simplifiedPrompt(item));

    let carved = null;
    let quota = null;
    const start = Date.now();
    while (Date.now() - start < 420000) {
      carved = carveScene(item.cacheKey, dest, sentAt);
      if (carved && carved.bytes > 10000) break;
      const info = quotaInfo(await tail(page));
      if (info) {
        quota = info;
        break;
      }
      await page.waitForTimeout(2000);
    }

    const ready = await waitCurrentReady(page);
    if (ready.status === 'quota') quota = ready.quota;
    carved = carveScene(item.cacheKey, dest, sentAt) || carved;
    if (carved && carved.bytes > 10000) {
      generated += 1;
      console.log(`${item.filename} saved ${carved.bytes}`);
      continue;
    }

    if (quota) {
      console.log(`QUOTA_EXHAUSTED ${JSON.stringify(quota)}`);
      process.exit(2);
    }

    console.error(`${item.filename} failed`);
    process.exit(1);
  }

  console.log(`generated=${generated}`);
  await browser.close();
}

main().catch((err) => {
  if (err && err.unavailable) {
    console.error(`ANTIGRAVITY_UI_UNAVAILABLE ${err.message}`);
    process.exit(3);
  }
  console.error(err.stack || err);
  process.exit(1);
});
