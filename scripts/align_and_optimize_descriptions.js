#!/usr/bin/env node

/**
 * YouTube Studio - Automated Description Audit & SEO/AEO/GEO Alignment
 * 
 * Inspects all channel videos, purges legacy/outdated channel relics (e.g. 'aperitif', buy me a coffee, etc.),
 * and updates descriptions with modern YouTube SEO, AEO (Answer Engine Optimization),
 * and GEO (Generative Engine Optimization) formatting.
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const VIDEOS_FILE = path.join(ROOT_DIR, 'output', 'all_channel_videos_ascending.json');
const PROGRESS_FILE = path.join(ROOT_DIR, 'output', 'descriptions_update_progress.json');
const CDP_PORT = process.env.CHROME_CDP_PORT || 9222;

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function loadJSON(filePath, defaultVal = {}) {
  if (!fs.existsSync(filePath)) return defaultVal;
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8')) || defaultVal;
  } catch (e) {
    return defaultVal;
  }
}

function saveJSON(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
}

/**
 * Generate rich, atmospheric narrative hook tailored to the video's specific title & theme
 */
function generateNarrativeHook(title = '', rawExisting = '') {
  const t = title.toLowerCase();

  // Aggressively clean existing description
  let cleaned = (rawExisting || '')
    .replace(/https?:\/\/\S+/gi, '')
    .replace(/www\.\S+/gi, '')
    .replace(/buymeacoffee\S*/gi, '')
    .replace(/patreon\S*/gi, '')
    .replace(/#\w+/g, '')
    .replace(/[♥❤️✨🔥🜲•🎧⏳🔊📜]\s*[^\n]*/g, '')
    .replace(/\d+:\d+\s*[–—\-].*/g, '')
    .replace(/aperitif/gi, '')
    .replace(/dragonballz|dbz|healingpod|asmr/gi, '')
    .replace(/super thanks/gi, '')
    .replace(/support the channel/gi, '')
    .replace(/buy me a coffee/gi, '')
    .trim();

  const lines = cleaned.split('\n')
    .map(l => l.trim())
    .filter(l => (
      l.length > 25 &&
      !l.toLowerCase().includes('support') &&
      !l.toLowerCase().includes('thank you') &&
      !l.toLowerCase().includes('past trauma') &&
      !l.toLowerCase().includes('all original audio') &&
      !l.toLowerCase().includes('calming ambient music')
    ));

  cleaned = lines.join('\n\n');

  // If existing description had genuine custom lore (and no legacy garbage), keep it
  if (cleaned.length >= 75) {
    return cleaned;
  }

  // Otherwise generate custom narrative based on specific title themes
  if (t.includes('valedictorian') || t.includes('harry potter') || t.includes('slytherin') || t.includes('ravenclaw')) {
    return `An unyielding pursuit of forbidden knowledge beneath the flicker of dying candles. Ink-stained fingers turning pages of ancient leather-bound grimoires in the restricted section while rain lashes against gothic stone arches. Let the rhythmic scratching of quills, old parchment, and the heavy silence of the night hours fuel your focus.`;
  }
  if (t.includes('elon musk') || t.includes('humanity to mars')) {
    return `Deep nocturnal engineering and radical ambition. High-frequency focus soundscapes calibrated for solving complex systems, orbital mechanics, and pushing through late-night problem-solving sessions without cognitive fatigue.`;
  }
  if (t.includes('hannibal lecter') || t.includes('mind palace')) {
    return `Absolute precision, cold analytical clarity, and total cognitive isolation. A calculated, immersive dark academia soundscape designed for navigating complex labyrinths of thought and relentless mental focus.`;
  }
  if (t.includes('communist dystopia')) {
    return `Cold concrete monoliths, endless bureaucratic corridors, and the muffled drone of a frozen city. An atmospheric, melancholic ambient journey through industrial twilight, heavy silence, and Soviet brutalist architecture.`;
  }
  if (t.includes('divorced mom')) {
    return `A quiet, reflective evening in an empty room bathed in golden twilight. Gentle melancholic ambient textures and distant nostalgic warmth designed for unhurried thought, decompressing after a long week, and deep rest.`;
  }
  if (t.includes('ocd brain') || t.includes('calm your')) {
    return `A soothing, symmetrical ambient blanket designed to slow racing thoughts, quiet internal noise, and restore cognitive equilibrium. Minimalist frequencies and gentle resonant beds for effortless focus or sleep.`;
  }
  if (t.includes('lex fridman')) {
    return `Relentless curiosity and deep nocturnal concentration. Minimalist atmospheric drones designed for long-form research, code development, philosophical inquiries, and uninterrupted flow states.`;
  }
  if (t.includes('math') || t.includes('madman')) {
    return `Chalk dust floating in shafts of moonlight, infinite equations covering blackboards across empty lecture halls, and the frantic clarity of late-night mathematical breakthroughs.`;
  }
  if (t.includes('ancient scholar') || t.includes('futuristic tavern')) {
    return `Where ancient manuscripts meet neon rain. A scholar lost in thought at the edge of a cybernetic metropolis, deciphering forgotten star charts in an empty tavern while the world sleeps.`;
  }
  if (t.includes('past trauma') || t.includes('healing')) {
    return `A gentle, restorative soundscape crafted for profound decompression, nervous system reset, and emotional quiet. Slow-evolving ambient pads and warm acoustic frequencies designed to help you breathe deeply and let go.`;
  }
  if (t.includes('psychiatry') || t.includes('asylum')) {
    return `Gaslight shadows dancing along damp stone corridors, leather-bound case files, and the profound, unsettling silence of an isolated 19th-century Victorian asylum. Designed for deep study and atmospheric reading.`;
  }
  if (t.includes('downtime in the old world') || t.includes('old world')) {
    return `Echoes of a forgotten era before screens and constant notifications. Hearth fires crackling in timbered libraries, rain upon cobblestone streets, and the unhurried passage of quiet afternoons.`;
  }
  if (t.includes('national geographic') || t.includes('magazine')) {
    return `Flipping through dog-eared glossy pages of 1980s expeditions, deep-sea trenches, and lost rainforests under a warm desk lamp on a quiet rainy Sunday afternoon.`;
  }
  if (t.includes('video store') || t.includes('vhs') || t.includes('rewind season') || t.includes('analog')) {
    return `Warm magnetic tape hiss, glowing CRT monitors, and the comforting melancholy of late-night video aisles after closing. A liminal analog soundscape for rewinding memories or deep nighttime rest.`;
  }
  if (t.includes('erebus') || t.includes('arctic') || t.includes('ice') || t.includes('glacier') || t.includes('polar')) {
    return `Sub-zero silence and the ancient pressure of shifting pack ice. Inspired by the lost expeditions of deep time, frozen in eternal stillness under the polar aurora.`;
  }
  if (t.includes('lighthouse') || t.includes('fog') || t.includes('shoreline') || t.includes('ocean') || t.includes('salt archive') || t.includes('tide')) {
    return `A solitary beacon cutting through heavy midnight sea fog. Distant crashing swells, ancient iron groan, and the crushing beauty of the nocturnal ocean.`;
  }
  if (t.includes('lovecraft') || t.includes('cthulhu') || t.includes('r\'lyeh') || t.includes('carcosa') || t.includes('eldritch') || t.includes('abyss') || t.includes('leviathan') || t.includes('tower') || t.includes('fresnel')) {
    return `Deep abyssal resonance, non-Euclidean shadows, and the haunting beauty of cosmic solitude. Atmospheric drones tuned to slow your breathing and transport you into the eerie vastness of the unknown.`;
  }
  if (t.includes('liminal') || t.includes('backrooms') || t.includes('empty') || t.includes('poolroom') || t.includes('arcade') || t.includes('motel') || t.includes('depot') || t.includes('corridor') || t.includes('mall') || t.includes('atrium') || t.includes('subway') || t.includes('laundromat') || t.includes('fitting room') || t.includes('bus')) {
    return `Suspended in the quiet hours between destinations. Soft fluorescent hums, echoing tiles, and the comforting stillness of empty transitional architecture outside of time.`;
  }
  if (t.includes('space') || t.includes('asteroid') || t.includes('orbital') || t.includes('galaxy') || t.includes('mars') || t.includes('station') || t.includes('planet') || t.includes('nebula') || t.includes('dyson')) {
    return `An endless drift across silent cosmic expanses and cold orbital horizons. Sub-bass atmospheric resonance and stellar drones designed to quiet the mind and induce deep focus.`;
  }
  if (t.includes('prehistoric') || t.includes('dinosaur') || t.includes('mammoth') || t.includes('swamp') || t.includes('rain') || t.includes('mangrove') || t.includes('thunder')) {
    return `Ancient primordial soundscapes from deep time. Distant thunder over prehistoric forests, warm rain upon Cretaceous rivers, and the undisturbed breath of ancient earth.`;
  }
  if (t.includes('christmas') || t.includes('snow') || t.includes('winter') || t.includes('cozy')) {
    return `Warm hearth embers, falling snow outside frost-lined windowpanes, and the gentle stillness of a winter sanctuary. Peaceful ambient textures designed for deep comfort and rest.`;
  }

  return `An evocative atmospheric soundscape crafted by @timelessambience55. Deep textured drones, immersive spatial beds, and quiet resonance designed for deep focus, sleep, and mental clarity.`;
}

/**
 * Generate genre tags and timestamps based on title & duration
 */
function buildFullDescription(title, rawExisting) {
  const t = title.toLowerCase();

  // Detect duration
  let timestamps = `0:00 — Drift Begins\n20:00 — Deepening Atmosphere\n40:00 — Submerged Resonance\n1:00:00 — Fade into Stillness`;
  if (t.includes('8 hour') || t.includes('8h') || t.includes('8 hours')) {
    timestamps = `0:00 — Drift Begins\n2:00:00 — Deepening Atmosphere\n4:00:00 — Submerged Resonance\n6:00:00 — Midnight Reverie\n8:00:00 — Fade into Stillness`;
  } else if (t.includes('3 hour') || t.includes('3h') || t.includes('3 hours')) {
    timestamps = `0:00 — Drift Begins\n45:00 — Deepening Atmosphere\n1:30:00 — Submerged Resonance\n2:15:00 — Midnight Reverie\n3:00:00 — Fade into Stillness`;
  } else if (t.includes('2 hour') || t.includes('2h') || t.includes('2 hours')) {
    timestamps = `0:00 — Drift Begins\n30:00 — Deepening Atmosphere\n1:00:00 — Submerged Resonance\n1:30:00 — Midnight Reverie\n2:00:00 — Fade into Stillness`;
  }

  // Hashtags
  let hashtags = ['#ambient', '#darkambient', '#cosmichorror', '#sleepmusic', '#studymusic', '#timelessambience'];
  if (t.includes('study') || t.includes('reading') || t.includes('academia') || t.includes('library') || t.includes('scholar') || t.includes('physics') || t.includes('math') || t.includes('valedictorian') || t.includes('asylum') || t.includes('psychiatry')) {
    hashtags = ['#darkacademia', '#studymusic', '#ambientstudy', '#deepfocus', '#readingmusic', '#darkambient', '#timelessambience'];
  } else if (t.includes('liminal') || t.includes('backrooms') || t.includes('dead mall') || t.includes('poolroom') || t.includes('laundromat') || t.includes('subway') || t.includes('motel') || t.includes('bus depot') || t.includes('arcade') || t.includes('level 0')) {
    hashtags = ['#liminalspace', '#backrooms', '#dreamcore', '#weirdcore', '#darkambient', '#sleepmusic', '#liminal', '#timelessambience'];
  } else if (t.includes('video store') || t.includes('vhs') || t.includes('cassette') || t.includes('analog') || t.includes('rewind season')) {
    hashtags = ['#analognostalgia', '#vhsambient', '#retroambient', '#mallsoft', '#liminalspace', '#darkambient', '#timelessambience'];
  } else if (t.includes('space') || t.includes('asteroid') || t.includes('galaxy') || t.includes('nebula') || t.includes('orbital') || t.includes('mars') || t.includes('dyson') || t.includes('cosmonaut')) {
    hashtags = ['#scifiambient', '#deepspace', '#spaceambient', '#cosmicambient', '#darkambient', '#sleepmusic', '#timelessambience'];
  } else if (t.includes('dinosaur') || t.includes('mammoth') || t.includes('prehistoric') || t.includes('swamp') || t.includes('mangrove')) {
    hashtags = ['#prehistoricambient', '#ancientearth', '#natureambient', '#rainambient', '#darkambient', '#sleepmusic', '#timelessambience'];
  } else if (t.includes('lovecraft') || t.includes('cthulhu') || t.includes('r\'lyeh') || t.includes('carcosa') || t.includes('lighthouse') || t.includes('abyss') || t.includes('fog')) {
    hashtags = ['#lovecraftian', '#cosmichorror', '#darkambient', '#eldritchhorror', '#sleepmusic', '#studymusic', '#timelessambience'];
  }

  const hook = generateNarrativeHook(title, rawExisting);

  return `${hook}

🎧 Recommended Use Cases:
• Deep Sleep, Lucid Dreaming & Nighttime Wind-Down
• High-Focus Deep Work, Software Engineering & Writing
• Atmospheric Dark Academia, Sci-Fi & Cosmic Horror Reading
• Anxiety Relief, Calming Overactive Thoughts & Insomnia Relief

⏳ Chapters & Timestamps:
${timestamps}

🔊 Audio Engineering & Sound Design:
• Multi-layered spatial soundscapes crafted by @timelessambience55.
• Mastered to broadcast loudness standards (EBU R128) with dynamic spatial depth.
• Headphone listening recommended for full binaural immersion.

📜 Connect & Explore:
• Subscribe for weekly atmospheric releases: https://www.youtube.com/@timelessambience55?sub_confirmation=1
• Channel: @timelessambience55

${hashtags.join(' ')}`;
}

class StudioCDPClient {
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

async function auditAndUpdateVideo(videoId, expectedTitle = '') {
  const client = new StudioCDPClient(CDP_PORT);
  await client.checkConnection();

  try {
    await client.openVideoEditTab(videoId);

    // Poll until description box & title appear (up to 25s)
    const startTime = Date.now();
    let currentData = null;
    while (Date.now() - startTime < 25000) {
      await sleep(1000);
      currentData = await client.evaluate(function() {
        const titleBox = document.querySelector('#textbox[aria-label*="title" i], [aria-label="Title (required)"], ytcp-social-suggestions-textbox #textbox');
        const descBox = document.querySelector('#description-textarea #textbox, ytcp-video-description #textbox, [aria-label*="description" i]');
        if (titleBox && descBox) {
          return {
            title: (titleBox.innerText || titleBox.textContent || '').trim(),
            description: (descBox.innerText || descBox.textContent || '').trim()
          };
        }
        return null;
      });
      if (currentData) break;
    }

    if (!currentData) {
      console.log(`  [!] Elements not found in Studio for ${videoId}`);
      return { success: false, reason: 'Description box not found in DOM' };
    }

    const title = currentData.title || expectedTitle || '';
    const oldDesc = currentData.description || '';
    const newDesc = buildFullDescription(title, oldDesc);

    // Check if already aligned AND free of legacy junk
    const hasLegacyJunk = /aperitif|buymeacoffee|patreon|super thanks|healingpod|dragonballz/i.test(oldDesc);
    const isModern = oldDesc.includes('🎧 Recommended Use Cases:') && oldDesc.includes('⏳ Chapters & Timestamps:') && oldDesc.includes('@timelessambience55');

    if (isModern && !hasLegacyJunk) {
      console.log(`  [OK] Already aligned and clean.`);
      return {
        success: true,
        status: 'already_aligned',
        title,
        oldDescLength: oldDesc.length
      };
    }

    // Set new description via DOM & synthetic events
    const updateResult = await client.evaluate(`
      (() => {
        const descBox = document.querySelector('#description-textarea #textbox, ytcp-video-description #textbox, [aria-label*="description" i]');
        if (!descBox) return { success: false, reason: 'No descBox' };

        descBox.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, ${JSON.stringify(newDesc)});
        
        descBox.dispatchEvent(new Event('input', { bubbles: true, composed: true }));
        descBox.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
        
        return { success: true, newLength: (descBox.innerText || descBox.textContent || '').length };
      })()
    `);

    if (!updateResult || !updateResult.success) {
      console.log(`  [!] Failed to set description text for ${videoId}`);
      return { success: false, reason: 'Failed to insert text in descBox' };
    }

    await sleep(2000);

    // Click Save Button
    const saveResult = await client.evaluate(function() {
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

    console.log(`  >> Save status: ${saveResult}`);
    await sleep(3000);

    return {
      success: true,
      status: 'updated',
      title,
      hadLegacyJunk: hasLegacyJunk,
      newDescLength: newDesc.length
    };
  } catch (err) {
    console.error(`  [ERROR] Error processing ${videoId}:`, err.message);
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
  const progress = loadJSON(PROGRESS_FILE, {});

  console.log('================================================================');
  console.log(`>> Starting YouTube Description Audit & Legacy Cleanup`);
  console.log(`>> Total Videos in Catalog: ${videos.length}`);
  console.log('================================================================');

  let updatedCount = 0;
  let alreadyAlignedCount = 0;
  let errorCount = 0;

  for (let i = 0; i < videos.length; i++) {
    const v = videos[i];
    const vid = v.videoId;
    const title = v.title || '';
    const date = v.date ? v.date.replace('\n', ' - ') : '';

    console.log(`\n[${i + 1}/${videos.length}] Video: ${vid} | "${title.slice(0, 45)}" | ${date}`);

    // If recorded in progress and marked as already_aligned or updated, skip
    if (progress[vid] && progress[vid].success && (progress[vid].status === 'already_aligned' || progress[vid].status === 'updated')) {
      console.log(`  [CACHED] Already verified/updated. Skipping.`);
      if (progress[vid].status === 'updated') updatedCount++;
      else alreadyAlignedCount++;
      continue;
    }

    const res = await auditAndUpdateVideo(vid, title);
    progress[vid] = {
      title,
      date,
      timestamp: new Date().toISOString(),
      ...res
    };
    saveJSON(PROGRESS_FILE, progress);

    if (res.success) {
      if (res.status === 'updated') updatedCount++;
      else if (res.status === 'already_aligned') alreadyAlignedCount++;
    } else {
      errorCount++;
    }

    await sleep(2500);
  }

  console.log('\n================================================================');
  console.log(`>> ALL DONE! Description Review Summary:`);
  console.log(`   - Total Videos Processed: ${videos.length}`);
  console.log(`   - Newly Updated / Cleaned: ${updatedCount}`);
  console.log(`   - Already Aligned: ${alreadyAlignedCount}`);
  console.log(`   - Errors: ${errorCount}`);
  console.log('================================================================');
}

main().catch(err => {
  console.error('Fatal description updater error:', err);
  process.exit(1);
});
