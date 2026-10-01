const fs = require('fs');
const CDP_PORT = 9222;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function testMonetizeDetailed(videoId) {
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

  console.log('Loading page...');
  await sleep(9000);

  // Step 1: Open Dropdown
  console.log('Step 1: Clicking monetization trigger...');
  const clickedTrigger = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.querySelector('ytcp-video-metadata-monetization');
      if (el) {
        const trigger = el.querySelector('#trigger') || el.querySelector('ytcp-dropdown-trigger') || el;
        trigger.click();
        const inner = trigger.shadowRoot ? trigger.shadowRoot.querySelector('button') || trigger.shadowRoot.querySelector('*') : null;
        if (inner) inner.click();
        return true;
      }
      return false;
    })()`,
    returnByValue: true
  });
  console.log('Trigger clicked:', clickedTrigger.result.value);
  await sleep(2500);

  // Step 2: Select 'On' radio and Click 'Done' in the dropdown dialog
  console.log('Step 2: Selecting ON radio and clicking Done...');
  const selectRes = await send('Runtime.evaluate', {
    expression: `(() => {
      const radios = Array.from(document.querySelectorAll('paper-radio-button, tp-yt-paper-radio-button, [role="radio"]'));
      const onRadio = radios.find(r => (r.textContent || '').trim().toLowerCase().startsWith('on') || r.getAttribute('name') === 'ON');
      if (onRadio) {
        onRadio.click();
        const inner = onRadio.shadowRoot ? onRadio.shadowRoot.querySelector('#radio') || onRadio.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
      }

      // Find Done button inside the dropdown or dialog
      const btns = Array.from(document.querySelectorAll('ytcp-button, button'));
      const doneBtn = btns.find(b => (b.textContent || '').trim() === 'Done' || (b.textContent || '').trim() === 'Apply' || (b.id === 'save-button' && b.closest('ytcp-dropdown-trigger, ytcp-text-menu, tp-yt-paper-dialog, ytcp-dialog')));
      if (doneBtn) {
        doneBtn.click();
        const inner = doneBtn.shadowRoot ? doneBtn.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();
        return { onFound: !!onRadio, doneClicked: true, doneText: doneBtn.textContent.trim() };
      }
      return { onFound: !!onRadio, doneClicked: false, allBtns: btns.map(b => b.textContent.trim()).filter(Boolean) };
    })()`,
    returnByValue: true
  });
  console.log('Select & Done result:', JSON.stringify(selectRes.result.value, null, 2));
  await sleep(3500);

  // Step 3: Self-certification dialog
  console.log('Step 3: Checking self-certification dialog...');
  const certRes = await send('Runtime.evaluate', {
    expression: `(() => {
      const checkboxes = Array.from(document.querySelectorAll('tp-yt-paper-checkbox, paper-checkbox, ytcp-checkbox-lit, [role="checkbox"]'));
      const noneBox = checkboxes.find(c => (c.textContent || '').trim().toLowerCase().includes('none of the above'));
      if (noneBox) {
        noneBox.click();
        const inner = noneBox.shadowRoot ? noneBox.shadowRoot.querySelector('#checkbox') || noneBox.shadowRoot.querySelector('button') : null;
        if (inner) inner.click();

        const btns = Array.from(document.querySelectorAll('ytcp-button, button'));
        const submitBtn = btns.find(b => (b.textContent || '').trim().toLowerCase() === 'submit');
        if (submitBtn) {
          submitBtn.click();
          const sInner = submitBtn.shadowRoot ? submitBtn.shadowRoot.querySelector('button') : null;
          if (sInner) sInner.click();
          return 'None checked & Submit clicked';
        }
        return 'None checked, submit not found';
      }
      return 'No certification dialog';
    })()`,
    returnByValue: true
  });
  console.log('Cert result:', certRes.result.value);
  await sleep(4000);

  // Step 4: Click Save on main page
  console.log('Step 4: Clicking main Save button...');
  const saveRes = await send('Runtime.evaluate', {
    expression: `(() => {
      const saveBtn = document.querySelector('#save-button, ytcp-button#save-button, [aria-label="Save"]');
      if (saveBtn) {
        const disabled = saveBtn.disabled || saveBtn.getAttribute('aria-disabled') === 'true';
        if (!disabled) {
          saveBtn.click();
          const inner = saveBtn.shadowRoot ? saveBtn.shadowRoot.querySelector('button') : null;
          if (inner) inner.click();
          return 'Saved successfully';
        }
        return 'Save button disabled';
      }
      return 'Save button not found';
    })()`,
    returnByValue: true
  });
  console.log('Save result:', saveRes.result.value);
  await sleep(5000);

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  if (shot && shot.data) {
    fs.writeFileSync('/tmp/monetization_test_done.png', Buffer.from(shot.data, 'base64'));
    console.log('Saved /tmp/monetization_test_done.png');
  }

  await fetch(`http://127.0.0.1:${CDP_PORT}/json/close/${tab.id}`, { method: 'PUT' });
  ws.close();
}

testMonetizeDetailed('qQ7Kxn9PDEg').catch(console.error);
