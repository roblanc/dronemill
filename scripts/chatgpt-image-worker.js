#!/usr/bin/env node
/*
 * ChatGPT UI image worker through Dia browser for Dronemill.
 *
 * UI-only: no OpenAI API calls. This worker controls Dia through a Chromium
 * DevTools port and saves approved image outputs to images/inbox/.
 */

const fs = require('fs');
const path = require('path');
const childProcess = require('child_process');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const DIA_APP = '/Applications/Dia.app';
const DIA_BIN = '/Applications/Dia.app/Contents/MacOS/Dia';
const CDP_PORT = process.env.DIA_CDP_PORT || '9333';
const CDP_ENDPOINT = `http://127.0.0.1:${CDP_PORT}`;

function usage() {
  console.error('Usage: node scripts/chatgpt-image-worker.js [--max N] [--prompts path]');
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

function parsePrompts(slug, promptsFile) {
  const promptsPath = promptsFile ? path.resolve(promptsFile) : path.join(ROOT, 'output', 'ui_image_prompts.txt');
  if (!fs.existsSync(promptsPath)) throw new Error(`prompts file missing: ${promptsPath}`);
  const text = fs.readFileSync(promptsPath, 'utf8');

  if (promptsFile) {
    return [...text.matchAll(/--- Image ([^\s]+) ---\n([\s\S]*?)(?=\n--- Image [^\s]+ ---|$)/g)]
      .map((m) => ({ filename: m[1].trim(), prompt: m[2].trim() }));
  }

  return [...text.matchAll(/--- Beat (\d+)\/(\d+) \(words [^)]+\) ---\n([\s\S]*?)(?=\n--- Beat \d+\/\d+|$)/g)]
    .map((m) => ({
      filename: `scene-${String(Number(m[1])).padStart(2, '0')}.png`,
      prompt: m[3].trim(),
    }));
}

function cdpAvailable() {
  try {
    childProcess.execFileSync('/usr/bin/curl', ['-fsS', `${CDP_ENDPOINT}/json/version`], {
      stdio: 'ignore',
      timeout: 2000,
    });
    return true;
  } catch {
    return false;
  }
}

function startDiaWithCdp() {
  if (cdpAvailable()) return;
  if (!fs.existsSync(DIA_APP) || !fs.existsSync(DIA_BIN)) {
    throw Object.assign(new Error('Dia is not installed at /Applications/Dia.app'), { unavailable: true });
  }

  // Existing Dia instances do not accept new DevTools flags; restart to attach automation.
  childProcess.spawnSync('/usr/bin/pkill', ['-TERM', '-x', 'Dia'], { stdio: 'ignore' });
  childProcess.spawnSync('/bin/sleep', ['3']);
  childProcess.spawnSync('/usr/bin/open', [
    '-na',
    DIA_APP,
    '--args',
    `--remote-debugging-port=${CDP_PORT}`,
    '--no-first-run',
    '--no-default-browser-check',
    'https://chatgpt.com/',
  ], { stdio: 'ignore' });

  for (let i = 0; i < 20; i++) {
    if (cdpAvailable()) return;
    childProcess.spawnSync('/bin/sleep', ['1']);
  }
  throw Object.assign(new Error(`Dia did not expose DevTools on ${CDP_ENDPOINT}`), { unavailable: true });
}

async function getChatPage(browser) {
  const context = browser.contexts()[0];
  let page = context.pages().find((p) => /chatgpt\.com|chat\.openai\.com/.test(p.url()));
  if (!page) {
    page = await context.newPage();
    await page.goto('https://chatgpt.com/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  }
  await page.bringToFront().catch(() => {});
  await page.waitForTimeout(3000);
  return page;
}

async function assertLoggedIn(page) {
  const body = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
  if (/Log in to get answers|Log in|Sign up for free|Log in or sign up/i.test(body)) {
    throw Object.assign(new Error('ChatGPT in Dia is not logged in'), { unavailable: true });
  }
}

async function findComposer(page) {
  const candidates = [
    '[data-testid="prompt-textarea"]',
    '#prompt-textarea',
    '[contenteditable="true"][role="textbox"]',
    '[aria-label="Chat with ChatGPT"][role="textbox"]',
    '[data-testid="composer"] textarea',
    'textarea',
    '[contenteditable="true"]',
  ];
  for (const selector of candidates) {
    const loc = page.locator(selector).last();
    if (!(await loc.count().catch(() => 0))) continue;
    if (await loc.isVisible().catch(() => false)) return loc;
  }
  throw new Error('ChatGPT composer not found');
}

async function sendPrompt(page, prompt) {
  const composer = await findComposer(page);
  await composer.scrollIntoViewIfNeeded().catch(() => {});
  await composer.focus().catch(() => {});
  await composer.click({ force: true }).catch(() => {});
  await page.keyboard.insertText(prompt);
  await page.keyboard.press('Enter');
}

async function waitUntilIdle(page) {
  for (let i = 0; i < 360; i++) {
    const text = await page.locator('body').innerText().catch(() => '');
    if (/message limit|You've reached|try again later|temporarily unable|rate limit/i.test(text.slice(-3000))) {
      throw Object.assign(new Error(`CHATGPT_QUOTA ${text.slice(-1200)}`), { quota: true });
    }
    if (!/(Stop generating|Generating|Creating image|Thinking|Working)/i.test(text.slice(-3000))) {
      return;
    }
    await page.waitForTimeout(1000);
  }
}

async function generatedImages(page) {
  return page.locator('img').evaluateAll((nodes) => nodes.map((img) => ({
    src: img.currentSrc || img.src,
    width: img.naturalWidth,
    height: img.naturalHeight,
    alt: img.alt || '',
  })).filter((img) => {
    const src = img.currentSrc || img.src || '';
    return img.width >= 256
      && img.height >= 256
      && !/cdn\.auth0\.com|avatar|profile/i.test(`${src} ${img.alt || ''}`);
  })).catch(() => []);
}

async function waitForNewImage(page, previousSrcs) {
  for (let i = 0; i < 420; i++) {
    const text = await page.locator('body').innerText().catch(() => '');
    if (/message limit|You've reached|try again later|temporarily unable|rate limit/i.test(text.slice(-3000))) {
      throw Object.assign(new Error(`CHATGPT_QUOTA ${text.slice(-1200)}`), { quota: true });
    }
    if (/experienced an error when generating images|error when generating images|couldn.?t generate/i.test(text.slice(-2000))) {
      throw new Error(`CHATGPT_IMAGE_ERROR ${text.slice(-1200)}`);
    }
    const images = await generatedImages(page);
    const fresh = images.find((img) => !previousSrcs.has(img.src));
    if (fresh) return fresh;
    await page.waitForTimeout(1000);
  }
  throw new Error('Timed out waiting for generated ChatGPT image');
}

async function saveImageFromSrc(page, dest, imageInfo) {
  const dataUrl = await page.evaluate(async (src) => {
    const res = await fetch(src);
    const blob = await res.blob();
    return await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(reader.error);
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(blob);
    });
  }, imageInfo.src);

  const match = String(dataUrl).match(/^data:[^;]+;base64,(.+)$/);
  if (!match) throw new Error('Could not read generated image bytes');
  fs.writeFileSync(dest, Buffer.from(match[1], 'base64'));
  return { bytes: fs.statSync(dest).size, width: imageInfo.width, height: imageInfo.height };
}

function buildPrompt(item) {
  return [
    `Generate exactly one image for ${item.filename}.`,
    'Return the image directly in chat.',
    'Use cinematic 16:9 landscape composition for a dark ambient YouTube cover.',
    'No real people, no documentary collage, no text, no watermark, no subtitles, no speech bubbles, no UI frame.',
    item.prompt,
  ].join(' ');
}

async function main() {
  const { slug, max, promptsFile } = parseArgs();
  const outDir = path.join(ROOT, 'images', 'inbox');
  fs.mkdirSync(outDir, { recursive: true });
  const prompts = parsePrompts(slug, promptsFile);
  startDiaWithCdp();

  const browser = await chromium.connectOverCDP(CDP_ENDPOINT);
  const page = await getChatPage(browser);
  await assertLoggedIn(page);

  let generated = 0;
  for (const item of prompts) {
    const dest = path.join(outDir, item.filename);
    if (fs.existsSync(dest) && fs.statSync(dest).size > 10000) continue;
    if (generated >= max) break;

    console.log(`${item.filename} sending via ChatGPT/Dia`);
    const beforeImages = await generatedImages(page);
    const beforeSrcs = new Set(beforeImages.map((img) => img.src));
    await sendPrompt(page, buildPrompt(item));
    const freshImage = await waitForNewImage(page, beforeSrcs);
    await waitUntilIdle(page);
    const saved = await saveImageFromSrc(page, dest, freshImage);
    if (saved.bytes < 10000) throw new Error(`${item.filename} saved too small`);
    console.log(`${item.filename} saved ${saved.bytes} (${saved.width}x${saved.height})`);
    generated += 1;
  }

  console.log(`generated=${generated}`);
  process.exit(0);
}

main().catch((err) => {
  if (err && err.quota) {
    console.log(`QUOTA_EXHAUSTED ${JSON.stringify({ message: err.message.slice(-1200) })}`);
    process.exit(2);
  }
  if (err && err.unavailable) {
    console.error(`CHATGPT_UI_UNAVAILABLE ${err.message}`);
    process.exit(3);
  }
  console.error(err.stack || err);
  process.exit(1);
});
