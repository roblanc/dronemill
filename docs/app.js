// ==========================================================================
// DRONEMILL DASHBOARD — MOBILE-FIRST LOGIC (VANILLA JS)
// ==========================================================================

let scheduleData = [];
let statusData = {};
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
  setupTheme();
  setupTabs();
  setupFilters();
  setupRefresh();
  setupModal();
  setupDrawer();
  loadAllData();
});

// Setup Dark / Light Theme Toggle
function setupTheme() {
  const savedTheme = localStorage.getItem('dronemill-theme') || 
    (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  applyTheme(savedTheme);

  const toggleBtns = [
    document.getElementById('btn-theme-toggle'),
    document.getElementById('btn-mobile-theme-toggle')
  ].filter(Boolean);

  toggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next = current === 'light' ? 'dark' : 'light';
      applyTheme(next);
      localStorage.setItem('dronemill-theme', next);
    });
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.body.classList.toggle('light-theme', theme === 'light');
  
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  if (metaTheme) {
    metaTheme.setAttribute('content', theme === 'light' ? '#f8fafc' : '#0a0c10');
  }

  const label = document.getElementById('theme-label-text');
  if (label) {
    label.textContent = theme === 'light' ? 'Light' : 'Dark';
  }
}

// Setup Mobile Sidebar Drawer
function setupDrawer() {
  const drawer = document.getElementById('sidebar-drawer');
  const backdrop = document.getElementById('drawer-backdrop');
  const openBtn = document.getElementById('btn-drawer-toggle');
  const closeBtn = document.getElementById('btn-drawer-close');

  function openDrawer() {
    if (drawer) drawer.classList.add('drawer-open');
    if (backdrop) backdrop.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    if (drawer) drawer.classList.remove('drawer-open');
    if (backdrop) backdrop.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (openBtn) openBtn.addEventListener('click', openDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);

  // Close drawer when clicking any nav item in the drawer
  const navItems = document.querySelectorAll('.sidebar .nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', closeDrawer);
  });
}

// Setup Tab Navigation (Supports both Desktop Sidebar & Mobile Bottom Nav)
function setupTabs() {
  const allNavBtns = document.querySelectorAll('.nav-item, .mobile-nav-item');
  const panes = document.querySelectorAll('.tab-pane');

  allNavBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');

      // Update active states on both desktop and mobile buttons
      allNavBtns.forEach(b => {
        if (b.getAttribute('data-tab') === targetTab) {
          b.classList.add('active');
        } else {
          b.classList.remove('active');
        }
      });

      // Switch tab pane
      panes.forEach(p => p.classList.remove('active'));
      const activePane = document.getElementById(`pane-${targetTab}`);
      if (activePane) {
        activePane.classList.add('active');
        // Scroll to top of pane on mobile
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  });
}

// Setup Filter Buttons
function setupFilters() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter') || 'all';
      renderFeed();
    });
  });
}

// Setup Refresh Buttons
function setupRefresh() {
  const btns = [document.getElementById('btn-refresh'), document.getElementById('btn-mobile-refresh')].filter(Boolean);
  btns.forEach(btn => {
    btn.addEventListener('click', async () => {
      btn.style.transform = 'rotate(360deg)';
      btn.style.transition = 'transform 0.4s ease';
      setTimeout(() => {
        btn.style.transform = '';
        btn.style.transition = '';
      }, 400);

      try {
        // Trigger live YouTube sync in backend if online
        await fetch('/api/sync-youtube').catch(() => {});
      } catch (e) {}

      await loadAllData();
      showToast('Live data & YouTube links refreshed', '🔄');
    });
  });
}

// Load All Endpoints
async function loadAllData() {
  await Promise.all([
    fetchStatus(),
    fetchSchedule(),
    fetchPlaylists(),
    fetchCommunityPosts()
  ]);
}

// Fetch Status Telemetry
async function fetchStatus() {
  try {
    const res = await fetch('data/status.json?v=20261007070018');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    statusData = data;

    const bufferText = `${data.future_scheduled_count || 0} Days`;
    const bufferElem = document.getElementById('metric-buffer');
    if (bufferElem) bufferElem.textContent = bufferText;

    const badgeScheduled = document.getElementById('badge-scheduled');
    if (badgeScheduled) badgeScheduled.textContent = data.future_scheduled_count || 0;

    const storageElem = document.getElementById('metric-storage');
    if (storageElem) storageElem.textContent = `${data.free_disk_gb || 0} GB Free`;

    const nextRelElem = document.getElementById('sidebar-next-release');
    if (nextRelElem) nextRelElem.textContent = data.next_release || 'None';

    // Telemetry Tab
    const usedDisk = document.getElementById('stat-used-disk');
    if (usedDisk) usedDisk.textContent = `${data.used_disk_gb || 0} GB Used`;

    const freeDisk = document.getElementById('stat-free-disk');
    if (freeDisk) freeDisk.textContent = `${data.free_disk_gb || 0} GB Available`;

    const progBar = document.getElementById('storage-progress-bar');
    if (progBar) progBar.style.width = `${data.disk_percent || 0}%`;

    const statBuffer = document.getElementById('stat-buffer-days');
    if (statBuffer) statBuffer.textContent = `${data.future_scheduled_count || 0} Days Ahead`;
  } catch (err) {
    console.error('Error loading status:', err);
  }
}

// is_future is set when the data is built, and the static copy can be a day old.
// Re-check it against the viewer's clock so passed releases count as published.
function refreshFuture(items) {
  const now = Date.now();
  items.forEach(i => {
    const t = Date.parse(i.publish_at || '');
    if (!isNaN(t)) i.is_future = t > now;
  });
  return items;
}

// The build sets on_youtube to false for queue entries it could not find on the channel.
const notOnYoutube = i => i.on_youtube === false;

// Fetch Schedule
async function fetchSchedule() {
  const container = document.getElementById('timeline-container');
  try {
    const res = await fetch('data/schedule.json?v=20261007070018');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw = await res.json();
    const wasFuture = raw.map(i => i.is_future);
    refreshFuture(raw);
    // Releases that went live since the build lead the published list, newest first.
    const justPublished = raw.filter((i, n) => wasFuture[n] && !i.is_future).reverse();
    scheduleData = [
      ...raw.filter(i => i.is_future),
      ...justPublished,
      ...raw.filter((i, n) => !wasFuture[n]),
    ];

    if (currentChannel === 'dronemill') renderFeed();
  } catch (err) {
    container.innerHTML = `<div class="loader">Error loading schedule: ${escapeHtml(err.message)}</div>`;
  }
}

// Render Timeline / Queue Cards
function renderTimeline(filter) {
  const container = document.getElementById('timeline-container');
  if (!scheduleData.length) {
    container.innerHTML = `<div class="loader">No releases found in queue.</div>`;
    return;
  }

  let filtered = scheduleData;
  if (filter === 'future') {
    filtered = scheduleData.filter(i => i.is_future && !notOnYoutube(i));
  } else if (filter === 'published') {
    filtered = scheduleData.filter(i => !i.is_future && !notOnYoutube(i));
  }

  if (!filtered.length) {
    container.innerHTML = `<div class="loader">No releases matching this filter.</div>`;
    return;
  }

  container.className = 'yt-feed';
  container.innerHTML = filtered.map(item => {
    const thumbSrc = item.thumbnail ? `images/${encodeURIComponent(item.thumbnail)}` : '';
    return ytCard({
      ch: 'dronemill', title: item.title, thumb: thumbSrc, duration: item.duration, views: item.views,
      ms: Date.parse(item.publish_at || ''), isFuture: item.is_future, missing: notOnYoutube(item),
      planned: (item.release_formatted || '').replace(/^\w+, /, '').replace(/ — .*/, ''),
      attrs: `href="#" onclick="event.preventDefault(); openVideoDetail(${item.id})"`,
    });
  }).join('');
}

// Open Video Detail Modal / Bottom Sheet
window.openVideoDetail = function(id) {
  const item = scheduleData.find(i => i.id === id);
  if (!item) return;

  const thumbSrc = item.thumbnail ? `images/${encodeURIComponent(item.thumbnail)}` : '';
  const badgeClass = notOnYoutube(item) ? 'missing' : item.is_future ? 'scheduled' : 'published';
  const badgeText = notOnYoutube(item) ? 'NOT ON YOUTUBE' : item.is_future ? 'SCHEDULED' : 'PUBLISHED';
  const hasYt = !!item.youtube_url;

  const modalBody = document.getElementById('modal-content-body');
  modalBody.innerHTML = `
    <img src="${thumbSrc}" alt="${escapeHtml(item.title)}" class="modal-hero-thumb">
    <div class="modal-meta-row">
      <span class="release-badge-pill ${badgeClass}">${badgeText}</span>
      <span class="card-date-meta">🗓️ ${escapeHtml(item.release_formatted)}</span>
      ${hasYt ? `<span class="yt-status-badge">▶ YouTube: ${escapeHtml(item.privacy || 'Uploaded')}</span>` : `<span class="pending-status-badge">Draft / Not Uploaded</span>`}
      <span class="tag-badge font-mono">#${item.id}</span>
    </div>
    <h3 class="modal-video-title">${escapeHtml(item.title)}</h3>

    ${hasYt ? `
      <div class="modal-yt-box">
        <div class="modal-yt-header">
          <div class="modal-yt-title-group">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#ff0033"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
            <strong>YouTube Video Link</strong>
          </div>
          <span class="font-mono text-muted" style="font-size: 0.72rem;">ID: ${escapeHtml(item.video_id)}</span>
        </div>
        <div class="modal-yt-url-row">
          <a href="${escapeHtml(item.youtube_url)}" target="_blank" rel="noopener noreferrer" class="modal-yt-url-link font-mono" title="Open link on YouTube">${escapeHtml(item.youtube_url)}</a>
          <button class="modal-mini-copy-btn" onclick="copyText('${escapeForJs(item.youtube_url)}', 'YouTube link copied!')" title="Copy YouTube Link">Copy Link</button>
        </div>
        <div class="modal-yt-btn-group">
          <a href="${escapeHtml(item.youtube_url)}" target="_blank" rel="noopener noreferrer" class="modal-act-btn yt-primary">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
            Watch on YouTube
          </a>
          <button class="modal-act-btn" onclick="copyText('${escapeForJs(item.youtube_url)}', 'YouTube link copied!')">📋 Copy YouTube Link</button>
        </div>
      </div>
    ` : ''}

    <div class="modal-actions">
      <button class="modal-act-btn primary" onclick="copyText('${escapeForJs(item.title)}', 'Title copied!')">Copy Title</button>
      <button class="modal-act-btn" onclick="copyText('${escapeForJs(item.description || '')}', 'Description copied!')">Copy Description</button>
    </div>

    ${item.tags && item.tags.length ? `
      <div>
        <h4 class="modal-section-title">YouTube Tags</h4>
        <div class="card-tags-row" style="margin-top: 6px;">
          ${item.tags.map(t => `<span class="tag-badge">#${escapeHtml(t)}</span>`).join('')}
        </div>
      </div>
    ` : ''}

    ${item.description ? `
      <div>
        <h4 class="modal-section-title">Full Description</h4>
        <div class="modal-desc-box">${escapeHtml(item.description)}</div>
      </div>
    ` : ''}
  `;

  const backdrop = document.getElementById('video-modal-backdrop');
  backdrop.classList.add('active');
  document.body.style.overflow = 'hidden';
};

// Setup Modal Listeners
function setupModal() {
  const backdrop = document.getElementById('video-modal-backdrop');
  const closeBtn = document.getElementById('modal-close-btn');

  function closeModal() {
    backdrop.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (backdrop) {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeModal();
    });
  }

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
}

// Fetch Playlists
async function fetchPlaylists() {
  const container = document.getElementById('playlists-container');
  try {
    const res = await fetch('data/playlists.json?v=20261007070018');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const playlists = await res.json();

    container.innerHTML = Object.entries(playlists).map(([name, data]) => `
      <div class="playlist-card">
        <h3 class="playlist-title">${escapeHtml(name)}</h3>
        <p class="playlist-desc">${escapeHtml(data.description)}</p>
        <div class="playlist-video-list">
          ${(data.videos || []).map(v => {
            if (v.youtube_url) {
              return `
                <a href="${escapeHtml(v.youtube_url)}" target="_blank" rel="noopener noreferrer" class="playlist-vid-item has-link" title="Open on YouTube: ${escapeHtml(v.title)}">
                  <span class="pl-icon">▶</span>
                  <span class="pl-text">${escapeHtml(v.title)}</span>
                  <span class="pl-yt-pill">YouTube ↗</span>
                </a>
              `;
            } else {
              return `
                <div class="playlist-vid-item" title="${escapeHtml(v.title)}">
                  <span class="pl-icon">▶</span>
                  <span class="pl-text">${escapeHtml(v.title)}</span>
                </div>
              `;
            }
          }).join('')}
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="loader">Error loading playlists: ${escapeHtml(err.message)}</div>`;
  }
}

// Fetch Community Posts
async function fetchCommunityPosts() {
  const container = document.getElementById('community-container');
  try {
    const res = await fetch('data/community.json?v=20261007070018');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const posts = await res.json();

    container.innerHTML = posts.map((post, idx) => `
      <div class="community-card">
        <span class="community-type-pill">${escapeHtml(post.type)}</span>
        <p class="community-post-text">${escapeHtml(post.content)}</p>
        <div class="poll-option-list">
          ${(post.poll_options || []).map(opt => `
            <div class="poll-option-item">🗳️ ${escapeHtml(opt)}</div>
          `).join('')}
        </div>
        <button class="copy-btn" onclick="copyCommunityPost(${idx})">📋 Copy Post to Clipboard</button>
      </div>
    `).join('');
    window._communityPosts = posts;
  } catch (err) {
    container.innerHTML = `<div class="loader">Error loading community posts: ${escapeHtml(err.message)}</div>`;
  }
}

// Copy Community Post
window.copyCommunityPost = function(idx) {
  if (window._communityPosts && window._communityPosts[idx]) {
    const post = window._communityPosts[idx];
    const fullText = `${post.content}\n\nPoll Options:\n` + (post.poll_options || []).map(o => `• ${o}`).join('\n');
    copyText(fullText, 'Community post copied!');
  }
};

// Generic Copy Text Helper
window.copyText = function(text, successMsg = 'Copied to clipboard!') {
  if (!navigator.clipboard) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    showToast(successMsg, '✅');
    return;
  }

  navigator.clipboard.writeText(text).then(() => {
    showToast(successMsg, '✅');
  }).catch(err => {
    console.error('Clipboard write error:', err);
  });
};

// Toast Notification Manager
function showToast(message, icon = '✨') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentNode) toast.parentNode.removeChild(toast);
  }, 2500);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeForJs(str) {
  if (!str) return '';
  return String(str)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '');
}

// ---------------------------------------------------------------- NofaceChan (anime channel)
let animeData = null;

function setupChannelSwitch() {
  const btns = document.querySelectorAll('.channel-btn');
  btns.forEach(btn => btn.addEventListener('click', () => {
    btns.forEach(b => b.classList.toggle('active', b === btn));
    const anime = btn.getAttribute('data-channel') === 'anime';
    currentChannel = anime ? 'anime' : 'dronemill';
    document.getElementById('timeline-container').hidden = anime;
    document.getElementById('anime-container').hidden = !anime;
    if (anime && animeData === null) fetchAnime();
    else renderFeed();
  }));
}

async function fetchAnime() {
  const container = document.getElementById('anime-container');
  try {
    const res = await fetch('data/anime.json?v=20261007070018');
    animeData = refreshFuture(await res.json());
    // Scheduled first (soonest on top), then published (newest on top).
    const when = i => Date.parse(i.publish_at || '') || 0;
    animeData.sort((a, b) => (b.is_future - a.is_future) || (a.is_future ? when(a) - when(b) : when(b) - when(a)));
    if (currentChannel === 'anime') renderFeed();
  } catch (err) {
    container.innerHTML = `<div class="loader">Error loading NofaceChan: ${escapeHtml(err.message)}</div>`;
  }
}

function renderAnime() {
  const container = document.getElementById('anime-container');
  if (!animeData || !animeData.length) {
    container.innerHTML = `<div class="loader">Nothing scheduled or published yet.</div>`;
    return;
  }
  const items = animeData.filter(i => currentFilter === 'future' ? i.is_future : currentFilter === 'published' ? !i.is_future : true);
  if (!items.length) {
    container.innerHTML = `<div class="loader">No videos matching this filter.</div>`;
    return;
  }
  const card = item => ytCard({
    ch: 'anime', title: item.title, thumb: item.thumb, duration: item.duration, views: item.views,
    ms: Date.parse(item.publish_at || ''), isFuture: item.is_future,
    attrs: `href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer"`,
  });
  const videos = items.filter(i => i.kind !== 'short');
  const shorts = items.filter(i => i.kind === 'short');
  container.className = 'yt-feed';
  // A full first row of videos before the Shorts shelf, as YouTube does (one card on phones).
  const cols = getComputedStyle(container).gridTemplateColumns.split(' ').filter(Boolean).length || 1;
  container.innerHTML = videos.slice(0, cols).map(card).join('') + ytShortsShelf(shorts) + videos.slice(cols).map(card).join('');
}

// ---------------------------------------------------------------- YouTube-style feed
let currentChannel = 'dronemill';
const CHANNEL_INFO = {
  dronemill: { name: 'Timeless Ambience', avatar: 'images/avatar-timeless.jpg', color: '#3f51b5' },
  anime: { name: 'NofaceChan', avatar: 'images/anime/avatar.jpg', color: '#c2185b' },
};

function feedItems() {
  return currentChannel === 'anime' ? (animeData || []) : scheduleData;
}

function updateCounts() {
  const items = feedItems();
  const set = (id, n) => { const el = document.getElementById(id); if (el) el.textContent = n; };
  set('count-all', items.length);
  set('count-future', items.filter(i => i.is_future && !notOnYoutube(i)).length);
  set('count-published', items.filter(i => !i.is_future && !notOnYoutube(i)).length);
}

function renderFeed() {
  updateCounts();
  if (currentChannel === 'anime') renderAnime();
  else renderTimeline(currentFilter);
}

// ISO 8601 length (PT2H0M3S) as YouTube's badge (2:00:03).
function ytDuration(iso) {
  const m = /^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$/.exec(iso || '');
  if (!m) return '';
  const h = (+m[1] || 0) * 24 + (+m[2] || 0), min = +m[3] || 0, sec = +m[4] || 0;
  if (!h && !min && !sec) return '';
  const pad = n => String(n).padStart(2, '0');
  return h ? `${h}:${pad(min)}:${pad(sec)}` : `${min}:${pad(sec)}`;
}

function ytViews(n) {
  if (n === null || n === undefined) return '';
  if (n < 1000) return `${n} view${n === 1 ? '' : 's'}`;
  const short = (v, unit) => `${v >= 10 ? Math.floor(v) : Math.floor(v * 10) / 10}${unit} views`;
  return n < 1e6 ? short(n / 1e3, 'K') : short(n / 1e6, 'M');
}

function ytAgo(ms) {
  const s = (Date.now() - ms) / 1000;
  for (const [unit, len] of [['year', 31536000], ['month', 2592000], ['week', 604800], ['day', 86400], ['hour', 3600], ['minute', 60]]) {
    const v = Math.floor(s / len);
    if (v >= 1) return `${v} ${unit}${v > 1 ? 's' : ''} ago`;
  }
  return 'just now';
}

// Release time in the viewer's own time zone, as YouTube shows it.
function ytWhen(ms) {
  return new Date(ms).toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function ytAvatar(ch) {
  const info = CHANNEL_INFO[ch];
  return `<span class="yt-avatar" style="background:${info.color}"><b>${info.name[0]}</b><img src="${info.avatar}" alt="" loading="lazy" onerror="this.remove()"></span>`;
}

function ytCard({ ch, title, thumb, duration, views, ms, isFuture, missing, planned, attrs }) {
  const len = ytDuration(duration);
  const badge = missing ? '<span class="yt-badge yt-badge-missing">NOT UPLOADED</span>'
    : isFuture ? '<span class="yt-badge yt-badge-upcoming">UPCOMING</span>'
    : len ? `<span class="yt-badge">${len}</span>` : '';
  const sub = missing ? `<span class="yt-missing">Not on YouTube</span>${planned ? ` · planned ${escapeHtml(planned)}` : ''}`
    : isFuture && !isNaN(ms) ? `Scheduled for ${escapeHtml(ytWhen(ms))}`
    : [ytViews(views), isNaN(ms) ? '' : ytAgo(ms)].filter(Boolean).join(' · ');
  return `
    <a class="yt-card" ${attrs}>
      <div class="yt-thumb">${thumb ? `<img src="${escapeHtml(thumb)}" alt="" loading="lazy" onerror="this.remove()">` : ''}${badge}</div>
      <div class="yt-meta">
        ${ytAvatar(ch)}
        <div class="yt-text">
          <h3 class="yt-title">${escapeHtml(title)}</h3>
          <p class="yt-sub">${escapeHtml(CHANNEL_INFO[ch].name)}${sub ? ' · ' + sub : ''}</p>
        </div>
        <svg class="yt-kebab" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="5" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="12" cy="19" r="1.8"/></svg>
      </div>
    </a>`;
}

function ytShortsShelf(shorts) {
  if (!shorts.length) return '';
  return `
    <section class="yt-shelf">
      <h3 class="yt-shelf-title"><svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><rect x="5" y="2" width="14" height="20" rx="4" fill="#ff0033"/><path d="M10 8.5v7l6-3.5z" fill="#fff"/></svg>Shorts</h3>
      <div class="yt-shelf-row">
        ${shorts.map(i => {
          const ms = Date.parse(i.publish_at || '');
          const sub = i.is_future && !isNaN(ms) ? `Scheduled for ${ytWhen(ms)}` : ytViews(i.views);
          return `
            <a class="yt-short" href="${escapeHtml(i.url)}" target="_blank" rel="noopener noreferrer">
              <div class="yt-short-thumb"><img src="${escapeHtml(i.short_thumb || i.thumb)}" alt="" loading="lazy">${i.is_future ? '<span class="yt-badge yt-badge-upcoming">UPCOMING</span>' : ''}</div>
              <p class="yt-short-title">${escapeHtml(i.title)}</p>
              <p class="yt-short-sub">${escapeHtml(sub)}</p>
            </a>`;
        }).join('')}
      </div>
    </section>`;
}

document.addEventListener('DOMContentLoaded', setupChannelSwitch);
