// CDP helper for the logged-in ChatGPT browser (chromium on :10, CDP :9222).
// Usage:
//   node tools/cdp.mjs --eval "<expr>" [--tab "<url-substring>"] [--url "<full url to navigate>"]
//   node tools/cdp.mjs --screenshot /tmp/shot.png [--tab "chatgpt"]
//   node tools/cdp.mjs --list
import WebSocket from '/usr/share/nodejs/ws/index.js'

const CDP = 'http://127.0.0.1:9222'

async function tabs() {
  const r = await fetch(`${CDP}/json/list`)
  return r.json()
}

async function pick(sub) {
  const list = await tabs()
  const pages = list.filter((t) => t.type === 'page')
  const target = sub
    ? pages.find((t) => t.url.includes(sub)) || pages[0]
    : pages[0]
  if (!target) throw new Error('no page tab found')
  return target
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl)
    let id = 0
    const pending = new Map()
    const listeners = []
    ws.on('open', () =>
      resolve({
        ws,
        send(method, params = {}) {
          const msgId = ++id
          return new Promise((res, rej) => {
            pending.set(msgId, { res, rej })
            ws.send(JSON.stringify({ id: msgId, method, params }))
          })
        },
        onEvent(fn) {
          listeners.push(fn)
        },
      }),
    )
    ws.on('message', (buf) => {
      const msg = JSON.parse(buf.toString())
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id)
        pending.delete(msg.id)
        msg.error ? p.rej(new Error(JSON.stringify(msg.error))) : p.res(msg.result)
      } else if (msg.method) {
        listeners.forEach((fn) => fn(msg))
      }
    })
    ws.on('error', reject)
  })
}

async function evalOn(c, expr, awaitPromise = true) {
  const r = await c.send('Runtime.evaluate', {
    expression: expr,
    returnByValue: true,
    awaitPromise,
  })
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails.exception))
  return r.result?.value
}

async function screenshot(c, file) {
  const r = await c.send('Page.captureScreenshot', { format: 'png' })
  const { writeFileSync } = await import('node:fs')
  writeFileSync(file, Buffer.from(r.data, 'base64'))
  console.log('saved', file)
}

const [, , arg, val, val2] = process.argv
if (arg === '--list') {
  for (const t of await tabs()) console.log(t.type.padEnd(9), t.url)
} else if (arg === '--screenshot') {
  const target = await pick(val && val !== 'chatgpt' ? val : 'chatgpt.com')
  const c = await connect(target.webSocketDebuggerUrl)
  await screenshot(c, val2 || '/tmp/cdp.png')
} else if (arg === '--eval') {
  const target = await pick('chatgpt.com')
  const c = await connect(target.webSocketDebuggerUrl)
  const out = await evalOn(c, val)
  console.log(typeof out === 'string' ? out : JSON.stringify(out, null, 2))
} else {
  console.log('unknown mode')
}