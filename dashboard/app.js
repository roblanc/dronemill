// ==========================================================================
// DRONEMILL DASHBOARD — FRONTEND LOGIC (VANILLA JS)
// ==========================================================================

let scheduleData = [];
let statusData = {};

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupFilters();
  setupRefresh();
  loadAllData();
});

// Setup Tab Navigation
function setupTabs() {
  const navBtns = document.querySelectorAll('.nav-item');
  const panes = document.querySelectorAll('.tab-pane');

  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      navBtns.forEach(b => b.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetTab = btn.getAttribute('data-tab');
      const pane = document.getElementById(`pane-${targetTab}`);
      if (pane) pane.classList.add('active');
    });
  });
}

// Setup Filters
function setupFilters() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.getAttribute('data-filter');
      renderTimeline(filter);
    });
  });
}

// Setup Refresh
function setupRefresh() {
  const btn = document.getElementById('btn-refresh');
  if (btn) {
    btn.addEventListener('click', () => {
      btn.style.transform = 'rotate(180deg)';
      setTimeout(() => btn.style.transform = '', 300);
      loadAllData();
    });
  }
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

// Fetch Status
async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    statusData = data;

    document.getElementById('metric-buffer').textContent = `${data.future_scheduled_count} Days`;
    document.getElementById('badge-scheduled').textContent = data.future_scheduled_count;
    document.getElementById('metric-storage').textContent = `${data.free_disk_gb} GB Free`;
    document.getElementById('sidebar-next-release').textContent = data.next_release;

    // Telemetry pane
    document.getElementById('stat-used-disk').textContent = `${data.used_disk_gb} GB Used`;
    document.getElementById('stat-free-disk').textContent = `${data.free_disk_gb} GB Free`;
    document.getElementById('storage-progress-bar').style.width = `${data.disk_percent}%`;
    document.getElementById('stat-buffer-days').textContent = `${data.future_scheduled_count} Days Ahead`;
  } catch (err) {
    console.error('Error loading status:', err);
  }
}

// Fetch Schedule
async function fetchSchedule() {
  const container = document.getElementById('timeline-container');
  try {
    const res = await fetch('/api/schedule');
    scheduleData = await res.json();
    renderTimeline('all');
  } catch (err) {
    container.innerHTML = `<div class="loader">Error loading schedule: ${err.message}</div>`;
  }
}

// Render Timeline
function renderTimeline(filter) {
  const container = document.getElementById('timeline-container');
  if (!scheduleData.length) {
    container.innerHTML = `<div class="loader">No releases found.</div>`;
    return;
  }

  let filtered = scheduleData;
  if (filter === 'future') {
    filtered = scheduleData.filter(i => i.is_future);
  } else if (filter === 'published') {
    filtered = scheduleData.filter(i => !i.is_future);
  }

  container.innerHTML = filtered.map(item => {
    const thumbSrc = item.thumbnail ? `/media/image/${encodeURIComponent(item.thumbnail)}` : '';
    const badgeClass = item.is_future ? 'scheduled' : 'published';
    const badgeText = item.is_future ? 'SCHEDULED' : 'PUBLISHED';

    return `
      <article class="release-card">
        <div class="card-thumb-wrap">
          <img src="${thumbSrc}" alt="${item.title}" class="card-thumb-img" loading="lazy" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'100%\\' height=\\'100%\\' fill=\\'%23111\\'><text x=\\'50%\\' y=\\'50%\\' fill=\\'%23555\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\' font-family=\\'sans-serif\\' font-size=\\'14\\'>Preview Image</text></svg>'">
          <span class="release-badge-pill ${badgeClass}">${badgeText}</span>
        </div>
        <div class="card-body">
          <h3 class="card-title-text">${escapeHtml(item.title)}</h3>
          <p class="card-date-meta">🗓️ ${item.release_formatted}</p>
          <div class="card-tags-row">
            ${(item.tags || []).slice(0, 4).map(t => `<span class="tag-badge">#${escapeHtml(t)}</span>`).join('')}
          </div>
        </div>
      </article>
    `;
  }).join('');
}

// Fetch Playlists
async function fetchPlaylists() {
  const container = document.getElementById('playlists-container');
  try {
    const res = await fetch('/api/playlists');
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
    container.innerHTML = `<div class="loader">Error loading playlists: ${err.message}</div>`;
  }
}

// Fetch Community Posts
async function fetchCommunityPosts() {
  const container = document.getElementById('community-container');
  try {
    const res = await fetch('/api/community-posts');
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
        <button class="copy-btn" onclick="copyPostText(${idx})">Copy to Clipboard</button>
      </div>
    `).join('');
    window._communityPosts = posts;
  } catch (err) {
    container.innerHTML = `<div class="loader">Error loading posts: ${err.message}</div>`;
  }
}

// Copy Post Text
window.copyPostText = function(idx) {
  if (window._communityPosts && window._communityPosts[idx]) {
    const post = window._communityPosts[idx];
    const fullText = `${post.content}\n\nPoll Options:\n` + post.poll_options.map(o => `• ${o}`).join('\n');
    navigator.clipboard.writeText(fullText).then(() => {
      alert('Community Post copied to clipboard!');
    });
  }
};

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
