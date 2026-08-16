// Generate a concept image inside the logged-in ChatGPT browser via CDP.
// Usage: node tools/chatgpt-gen.mjs "<prompt>" "<output.png>"
import WebSocket from '/usr/share/nodejs/ws/index.js'
import { writeFileSync } from 'node:fs'

const PROMPT = process.argv[2]
const OUT = process.argv[3]
if (!PROMPT || !OUT) {
  console.log('usage: node tools/chatgpt-gen.mjs "<prompt>" "<output.png>"')
  process.exit(1)
}

const tabs = await (await fetch('http://127.0.0.1:9222/json/list')).json()
const page = tabs.find((t) => t.type === 'page' && t.url.includes('chatgpt.com'))
if (!page) throw new Error('chatgpt page not found')
const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pend = new Map()
const send = (method, params = {}) =>
  new Promise((res, rej) => {
    const i = ++id
    pend.set(i, { res, rej })
    ws.send(JSON.stringify({ id: i, method, params }))
  })
ws.on('message', (b) => {
  const m = JSON.parse(b.toString())
  if (m.id && pend.has(m.id)) {
    const p = pend.get(m.id)
    pend.delete(m.id)
    m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result)
  }
})
await new Promise((r) => ws.on('open', r))

const ev = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })
  if (r.exceptionDetails) throw new Error('page eval exception')
  return r.result?.value
}
const clickLeaf = async (text) =>
  ev(
    `(()=>{const els=[...document.querySelectorAll('*')].filter(e=>e.children.length===0&&(e.innerText||'').trim()===${JSON.stringify(text)});const el=els[0];if(!el)return false;el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return true})()`,
  )
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

await ev(`(()=>{const el=[...document.querySelectorAll('a')].find(a=>(a.getAttribute('aria-label')||'')==='New chat');el&&el.click();return true})()`)
await sleep(1500)
await ev(`document.querySelector('[data-testid="composer-plus-btn"]')?.click()`)
await sleep(1300)
await clickLeaf('Create image')
await sleep(1200)
await ev(`document.querySelector('#prompt-textarea').focus()`)
await sleep(300)
await send('Input.insertText', { text: PROMPT })
await sleep(700)
const typed = await ev(`document.querySelector('#prompt-textarea')?.innerText || ''`)
if (!typed.trim()) {
  console.log('FAIL: prompt not in composer')
  process.exit(1)
}
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 })
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 })
console.log('sent prompt, waiting for image...')

let src = null
let stop = true
for (let i = 0; i < 40; i++) {
  await sleep(5000)
  const s = await ev(
    `(()=>{const img=[...document.querySelectorAll('img')].find(i=>/backend-api\\/estuary\\/content/.test(i.src||''));return {src:img?img.src:null, w:img?img.naturalWidth:0, h:img?img.naturalHeight:0, stop:!!document.querySelector('[data-testid="stop-button"]')}})()`,
  )
  stop = s.stop
  if (s.src && !stop) {
    src = s.src
    break
  }
}
if (!src) {
  console.log('FAIL: no image after wait (still generating: ' + stop + ')')
  process.exit(1)
}

const data = await ev(
  `(async()=>{const img=[...document.querySelectorAll('img')].find(i=>/backend-api\\/estuary\\/content/.test(i.src||''));const r=await fetch(img.src);const ct=r.headers.get('content-type');const b=await r.arrayBuffer();let bin='';const bytes=new Uint8Array(b);const chunk=0x8000;for(let i=0;i<bytes.length;i+=chunk){bin+=String.fromCharCode.apply(null,bytes.subarray(i,i+chunk))}return {ct, b64:btoa(bin), w:img.naturalWidth, h:img.naturalHeight}})()`,
)
const ext = (data.ct || '').includes('jpeg') || (data.ct || '').includes('jpg') ? 'jpg' : 'png'
const file = OUT.endsWith('.png') || OUT.endsWith('.jpg') ? OUT : `${OUT}.${ext}`
writeFileSync(file, Buffer.from(data.b64, 'base64'))
console.log('SAVED', file, data.w + 'x' + data.h, (data.b64.length * 0.75 / 1048576).toFixed(2) + 'MB')
process.exit(0)
