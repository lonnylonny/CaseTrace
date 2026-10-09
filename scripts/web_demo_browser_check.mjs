// Regression checks for download visibility and incomplete answer records.
// Usage: node scripts/web_demo_browser_check.mjs http://127.0.0.1:8010/
// Requires Node 22+ and Chrome; requests are replaced with offline fixtures.
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';

const pageUrl = process.argv[2] || 'http://127.0.0.1:8010/';
const chromePath = process.env.CASETRACE_CHROME_BINARY
  || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const saved = JSON.parse(readFileSync(
  new URL('../results/m4/dev-v3-answer-v10/q005.json', import.meta.url), 'utf8'));
const profile = mkdtempSync(join(tmpdir(), 'casetrace-web-regression-'));
const chrome = spawn(chromePath, [
  '--headless=new', '--no-first-run', '--no-default-browser-check',
  '--disable-background-networking', '--remote-debugging-port=0',
  `--user-data-dir=${profile}`, 'about:blank',
], { stdio: 'ignore' });
let launchError;
chrome.on('error', (error) => { launchError = error; });
let socket;
let nextId = 0;
const pending = new Map();

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`CDP timeout: ${method}`));
    }, 10000);
    pending.set(id, (message) => {
      clearTimeout(timer);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const result = await send('Runtime.evaluate', {
    expression, awaitPromise: true, returnByValue: true,
  });
  if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result.value;
}

try {
  let port;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (launchError) throw launchError;
    try { port = readFileSync(join(profile, 'DevToolsActivePort'), 'utf8').split('\n')[0]; }
    catch { await sleep(100); }
    if (port) break;
  }
  if (!port) throw new Error('Chrome did not start');
  const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {
    method: 'PUT', signal: AbortSignal.timeout(5000),
  })).json();
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true });
    socket.addEventListener('error', reject, { once: true });
  });
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (pending.has(message.id)) {
      pending.get(message.id)(message);
      pending.delete(message.id);
    }
  });
  await send('Page.enable');
  await send('Page.navigate', { url: pageUrl });
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    ready = await evaluate('document.readyState === "complete" && typeof present === "function"');
    if (ready) break;
    await sleep(100);
  }
  if (!ready) throw new Error('Web page did not load');
  const failures = [];
  let checks = 0;
  const check = (name, passed) => {
    checks += 1;
    console.log(`${passed ? 'PASS' : 'FAIL'} ${name}`);
    if (!passed) failures.push(name);
  };
  check('initial download is invisible', await evaluate('downloadButton.getClientRects().length === 0'));
  await evaluate(`window.__realFetch = window.fetch;
    window.__runResponse = async function (httpStatus, body) {
      window.fetch = async function () {
        return {status: httpStatus, text: async function () {return JSON.stringify(body);}};
      };
      queryInput.value = '浏览器离线回归';
      await submitAnswer({preventDefault: function () {}});
      return {kind: statusLine.dataset.kind, visible: downloadButton.getClientRects().length > 0,
        href: downloadButton.getAttribute('href'), busy: submitButton.disabled,
        text: resultBody.textContent};
    };`);
  for (const [name, status, body, kind, visible] of [
    ['success', 200, { status: 'ok', record: saved }, 'ok', true],
    ['422 after success', 422, { detail: [] }, 'error', false],
    ['503 without record', 503, { status: 'service_unavailable', record: null }, 'error', false],
  ]) {
    const view = await evaluate(`window.__runResponse(${status}, ${JSON.stringify(body)})`);
    check(name, view.kind === kind && view.visible === visible && !view.busy);
  }
  for (const [name, change] of [
    ['empty record', () => ({})],
    ['missing answer', (record) => { delete record.answer; }],
    ['missing case_answers', (record) => { delete record.answer.case_answers; }],
    ['invalid ranking', (record) => { record.ranking = null; }],
    ['missing context', (record) => { delete record.context; }],
    ['mismatched status', (record) => { record.status = 'model_failed'; }],
  ]) {
    const record = structuredClone(saved);
    const changed = change(record) || record;
    const view = await evaluate(`window.__runResponse(200, ${JSON.stringify({status: 'ok', record: changed})})`);
    check(name, view.kind === 'error' && !view.visible && !view.href && !view.busy
      && !view.text.includes('本次未采用历史案例'));
  }
  const zero = structuredClone(saved);
  zero.answer.case_answers = [];
  const zeroView = await evaluate(`window.__runResponse(200, ${JSON.stringify({status: 'ok', record: zero})})`);
  check('valid zero adoption', zeroView.kind === 'ok' && zeroView.visible
    && zeroView.text.includes('本次未采用历史案例'));
  const noHits = structuredClone(zero);
  noHits.status = 'no_hits';
  noHits.ranking = [];
  noHits.context.cases = [];
  const noHitsView = await evaluate(`window.__runResponse(200, ${JSON.stringify({status: 'no_hits', record: noHits})})`);
  check('valid no_hits', noHitsView.kind === 'warning' && noHitsView.visible);
  const badNoHits = await evaluate('window.__runResponse(200, {status: "no_hits", record: {}})');
  check('incomplete no_hits', badNoHits.kind === 'error' && !badNoHits.visible);
  console.log(`${checks - failures.length}/${checks} passed; ${failures.length} failed`);
  process.exitCode = failures.length ? 1 : 0;
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  if (socket) socket.close();
  chrome.kill('SIGKILL');
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
}
