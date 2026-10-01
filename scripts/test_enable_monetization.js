const fs = require('fs');
const CDP_PORT = 9222;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function enableMonetization(videoId) {
  const url = `https://studio.youtube.com/video/${videoId}/monetization`;
  const res = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
  const tab = await res.json();
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r, { once: true }));

  let msgId = 0;
  function send(method, params = {}) {
    const id = ++msgId;
    return new Promise((resolve, reject) => {
      const handler = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id === id) {
          ws.removeEventListener('message', handler);
          if (msg.error) reject(msg.error);
          else resolve(msg.result);
        }
      };
      ws.addEventListener('message', handler);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  console.log('Loading monetization tab for', videoId);
  await sleep(10000);

  // Check current text
  const initialText = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector('ytcp-video-metadata-monetization');
      return el ? el.innerText.trim() : 'not found';
    })()`,
    returnByValue: true
  });
  console.log('Current element text:', initialText.result.value);

  // Click the dropdown inside ytcp-video-metadata-monetization
  console.log('Clicking monetization dropdown...');
  await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector('ytcp-video-metadata-monetization');
      if (el) {
        const trigger = el.querySelector('ytcp-dropdown-trigger') || el.querySelector('#trigger') || el;
        trigger.click();
        const inner = trigger.shadowRoot ? trigger.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
      }
    })()`,
    returnByValue: true
  });

  await sleep(2500);

  // Take screenshot of open dropdown
  const shot1 = await send('Page.captureScreenshot', { format: 'png' });
  if (shot1 && shot1.data) {
    fs.writeFileSync('/tmp/monetization_dropdown_open.png', Buffer.from(shot1.data, 'base64'));
    console.log('Saved /tmp/monetization_dropdown_open.png');
  }

  // Click the 'On' radio button inside the dropdown dialog / menu
  console.log('Clicking ON option...');
  const clickedOn = await send('Runtime.evaluate', {
    expression: `(() => {
      const radios = Array.from(document.querySelectorAll('paper-radio-button, tp-yt-paper-radio-button, [role="radio"], paper-item, tp-yt-paper-item'));
      const onRadio = radios.find(r => (r.textContent || '').trim().toLowerCase().startsWith('on') || r.getAttribute('name') === 'ON' || r.id === 'radio-on');
      if (onRadio) {
        onRadio.click();
        const inner = onRadio.shadowRoot ? onRadio.shadowRoot.querySelector('#radio') || onRadio.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
        return { success: true, text: onRadio.textContent.trim(), tag: onRadio.tagName };
      }
      return { success: false, available: radios.map(r => r.textContent.trim()) };
    })()`,
    returnByValue: true
  });
  console.log('Clicked ON result:', JSON.stringify(clickedOn.result.value, null, 2));

  await sleep(2000);

  // Also click 'Done' if a dialog appeared
  await send('Runtime.evaluate', {
    expression: `(() => {
      const btns = Array.from(document.querySelectorAll('ytcp-button, button'));
      const doneBtn = btns.find(b => (b.textContent || '').trim() === 'Done' || (b.textContent || '').trim() === 'Save');
      if (doneBtn) {
        doneBtn.click();
        const inner = doneBtn.shadowRoot ? doneBtn.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
      }
    })()`,
    returnByValue: true
  });

  await sleep(2500);

  // Click Save button on main page
  console.log('Clicking main Save button...');
  const saveRes = await send('Runtime.evaluate', {
    expression: `(() => {
      const saveBtn = document.querySelector('#save-button, ytcp-button#save-button, [aria-label="Save"]');
      if (saveBtn) {
        const disabled = saveBtn.disabled || saveBtn.getAttribute('aria-disabled') === 'true';
        if (!disabled) {
          saveBtn.click();
          const inner = saveBtn.shadowRoot ? saveBtn.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
          return 'Saved successfully!';
        }
        return 'Save button disabled';
      }
      return 'Save button not found';
    })()`,
    returnByValue: true
  });
  console.log('Save result:', saveRes.result.value);

  await sleep(4000);

  // Take final confirmation screenshot
  const shot2 = await send('Page.captureScreenshot', { format: 'png' });
  if (shot2 && shot2.data) {
    fs.writeFileSync('/tmp/monetization_saved_final.png', Buffer.from(shot2.data, 'base64'));
    console.log('Saved /tmp/monetization_saved_final.png');
  }

  await fetch(`http://127.0.0.1:${CDP_PORT}/json/close/${tab.id}`, { method: 'PUT' });
  ws.close();
}

enableMonetization('qQ7Kxn9PDEg').catch(console.error);
