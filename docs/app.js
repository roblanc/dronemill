// ==========================================================================
// DRONEMILL DASHBOARD — MOBILE-FIRST LOGIC (VANILLA JS)
// ==========================================================================

let scheduleData = [];
let statusData = {};
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupFilters();
  setupRefresh();
  setupModal();
  setupDrawer();
  loadAllData();
});

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
      renderTimeline(currentFilter);
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

      await loadAllData();
      showToast('Live data refreshed', '🔄');
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
    const res = await fetch('data/status.json');
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

// Fetch Schedule
async function fetchSchedule() {
  const container = document.getElementById('timeline-container');
  try {
    const res = await fetch('data/schedule.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    scheduleData = await res.json();

    // Update Filter Counts
    const allCount = scheduleData.length;
    const futureCount = scheduleData.filter(i => i.is_future).length;
    const pubCount = allCount - futureCount;

    const cntAll = document.getElementById('count-all');
    const cntFuture = document.getElementById('count-future');
    const cntPub = document.getElementById('count-published');
    if (cntAll) cntAll.textContent = `(${allCount})`;
    if (cntFuture) cntFuture.textContent = `(${futureCount})`;
    if (cntPub) cntPub.textContent = `(${pubCount})`;

    renderTimeline(currentFilter);
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
    filtered = scheduleData.filter(i => i.is_future);
  } else if (filter === 'published') {
    filtered = scheduleData.filter(i => !i.is_future);
  }

  if (!filtered.length) {
    container.innerHTML = `<div class="loader">No releases matching this filter.</div>`;
    return;
  }

  container.innerHTML = filtered.map(item => {
    const thumbSrc = item.thumbnail ? `images/${encodeURIComponent(item.thumbnail)}` : '';
    const badgeClass = item.is_future ? 'scheduled' : 'published';
    const badgeText = item.is_future ? 'SCHEDULED' : 'PUBLISHED';

    return `
      <article class="release-card" onclick="openVideoDetail(${item.id})">
        <div class="card-thumb-wrap">
          <img src="${thumbSrc}" alt="${escapeHtml(item.title)}" class="card-thumb-img" loading="lazy" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'100%\\' height=\\'100%\\' fill=\\'%23111\\'><text x=\\'50%\\' y=\\'50%\\' fill=\\'%23555\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\' font-family=\\'sans-serif\\' font-size=\\'14\\'>Preview</text></svg>'">
          <span class="release-badge-pill ${badgeClass}">${badgeText}</span>
          <span class="card-order-tag">#${item.id}</span>
        </div>
        <div class="card-body">
          <h3 class="card-title-text">${escapeHtml(item.title)}</h3>
          <p class="card-date-meta">🗓️ ${escapeHtml(item.release_formatted)}</p>
          <div class="card-tags-row">
            ${(item.tags || []).slice(0, 3).map(t => `<span class="tag-badge">#${escapeHtml(t)}</span>`).join('')}
          </div>
          <span class="card-tap-hint">Tap for details & copy &rarr;</span>
        </div>
      </article>
    `;
  }).join('');
}

// Open Video Detail Modal / Bottom Sheet
window.openVideoDetail = function(id) {
  const item = scheduleData.find(i => i.id === id);
  if (!item) return;

  const thumbSrc = item.thumbnail ? `images/${encodeURIComponent(item.thumbnail)}` : '';
  const badgeClass = item.is_future ? 'scheduled' : 'published';
  const badgeText = item.is_future ? 'SCHEDULED' : 'PUBLISHED';

  const modalBody = document.getElementById('modal-content-body');
  modalBody.innerHTML = `
    <img src="${thumbSrc}" alt="${escapeHtml(item.title)}" class="modal-hero-thumb">
    <div class="modal-meta-row">
      <span class="release-badge-pill ${badgeClass}">${badgeText}</span>
      <span class="card-date-meta">🗓️ ${escapeHtml(item.release_formatted)}</span>
      <span class="tag-badge font-mono">#${item.id}</span>
    </div>
    <h3 class="modal-video-title">${escapeHtml(item.title)}</h3>
    
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
    const res = await fetch('data/playlists.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const playlists = await res.json();

    container.innerHTML = Object.entries(playlists).map(([name, data]) => `
      <div class="playlist-card">
        <h3 class="playlist-title">${escapeHtml(name)}</h3>
        <p class="playlist-desc">${escapeHtml(data.description)}</p>
        <div class="playlist-video-list">
          ${(data.videos || []).map(v => `
            <div class="playlist-vid-item" title="${escapeHtml(v.title)}">▶ ${escapeHtml(v.title)}</div>
          `).join('')}
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
    const res = await fetch('data/community.json');
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
