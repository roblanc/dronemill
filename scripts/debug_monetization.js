const fs = require('fs');

const CDP_PORT = 9222;

async function debugMonetization(videoId) {
  const url = `https://studio.youtube.com/video/${videoId}/monetization/ads`;
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
          resolve(msg.result);
        }
      };
      ws.addEventListener('message', handler);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  await new Promise(r => setTimeout(r, 7000));

  // Take screenshot
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  if (shot && shot.data) {
    fs.writeFileSync('/tmp/monetization_debug.png', Buffer.from(shot.data, 'base64'));
    console.log('Saved screenshot to /tmp/monetization_debug.png');
  }

  const result = await send('Runtime.evaluate', {
    expression: `(() => {
      // Find elements containing 'Off'
      const nodes = [];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if ((node.nodeValue || '').trim() === 'Off') {
          nodes.push({
            text: node.nodeValue,
            parentTag: node.parentElement.tagName,
            parentClass: node.parentElement.className,
            parentId: node.parentElement.id,
            outerHTML: node.parentElement.outerHTML.slice(0, 300)
          });
        }
      }
      return nodes;
    })()`,
    returnByValue: true
  });

  console.log('Off nodes:', JSON.stringify(result.result.value, null, 2));

  await fetch(`http://127.0.0.1:${CDP_PORT}/json/close/${tab.id}`, { method: 'PUT' });
  ws.close();
}

debugMonetization('qQ7Kxn9PDEg').catch(console.error);
