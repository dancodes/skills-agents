#!/usr/bin/env node
// Drive one Chrome tab by its DevTools target id, so agents that share a browser never touch each other's tab.

import { appendFileSync, readFileSync, writeFileSync } from "node:fs";

const port = process.env.CDP_PORT ?? 9222;
const http = `http://127.0.0.1:${port}`;
const [, , command, ...args] = process.argv;

const usage = `Usage:
  tab.mjs list [filter]                         id, url and title of every tab
  tab.mjs open <url>                            new background tab, prints its id
  tab.mjs close <id>
  tab.mjs fit <id> <width> <height>             move the tab's window to 0,0 and size it to fill the screen
  tab.mjs goto <id> <url> [target] [seconds]    navigate, wait for target (default 15 s), print the load time
  tab.mjs wait <id> <target> [seconds]          wait for target (default 15 s), print the time waited
  tab.mjs waitjs <id> <expression> [seconds]    wait until the JS expression is truthy (default 15 s), print it
  tab.mjs pause <seconds>                       do nothing for that long
  tab.mjs popup <id> <count> <target> ...       click the targets in order, count times, each once nothing
                                                covers it; print each URL the page opens in a new tab,
                                                without opening it
  tab.mjs point <id> <target> [target ...]      screen x,y of each target's center, for xdotool
  tab.mjs click <id> <target>                   scroll target into view and click it (no real mouse)
  tab.mjs eval <id> <expression | @file>        evaluate JS, print the value
  tab.mjs call <id> <Method> [json] ...         send raw DevTools commands in order
  tab.mjs shot <id> <out.png>                   screenshot of the page
  tab.mjs crop <id> <out.png> <targets> [scale] sharp crop of the box around targets joined by |, default 2x
  tab.mjs listen <id> <out.jsonl> <seconds> [url-regex]   log requests, failures and console errors

A target is a CSS selector, or text=<exact visible text or aria-label>. Buttons and links win over plain text.
goto, wait and waitjs stop at once when the tab is on a login page (an auth.* host).`;

const fail = (message) => {
  console.error(message);
  process.exit(1);
};

async function connect(url) {
  const ws = new WebSocket(url);
  await new Promise((resolve, reject) => {
    ws.onopen = resolve;
    ws.onerror = () => reject(new Error(`Cannot connect to ${url}`));
  });
  const pending = new Map();
  const listeners = [];
  let id = 0;
  ws.onmessage = (ev) => {
    const message = JSON.parse(ev.data);
    if (!message.id) return listeners.forEach((listener) => listener(message));
    const call = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) call.reject(new Error(`${call.method}: ${message.error.message}`));
    else call.resolve(message.result);
  };
  return {
    send: (method, params = {}) =>
      new Promise((resolve, reject) => {
        pending.set(++id, { resolve, reject, method });
        ws.send(JSON.stringify({ id, method, params }));
      }),
    on: (listener) => listeners.push(listener),
    closed: new Promise((resolve) => ws.addEventListener("close", resolve)),
  };
}

const tab = (targetId) => connect(`ws://127.0.0.1:${port}/devtools/page/${targetId}`);

async function browser() {
  const version = await (await fetch(`${http}/json/version`)).json();
  return connect(version.webSocketDebuggerUrl);
}

async function evaluate(page, expression) {
  const result = await page.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });
  if (result.exceptionDetails) {
    const details = result.exceptionDetails;
    throw new Error(details.exception?.description ?? details.text);
  }
  return result.result.value;
}

const locate = `(target, scroll) => {
  let matches;
  if (target.startsWith("text=")) {
    const text = target.slice(5);
    const named = Array.from(document.querySelectorAll("body *")).filter((el) => {
      const box = el.getBoundingClientRect();
      if (box.width === 0 || box.height === 0) return false;
      return el.getAttribute("aria-label") === text || el.textContent.trim() === text;
    });
    const controls = "button, a, input, select, [role=button], [role=menuitem], [role=tab], [role=option]";
    const leaves = named.filter((el) => !named.some((other) => other !== el && el.contains(other)));
    matches = [...leaves.filter((el) => el.closest(controls)), ...leaves.filter((el) => !el.closest(controls))];
  } else {
    matches = Array.from(document.querySelectorAll(target));
  }
  const el = matches[0];
  if (!el) return null;
  if (scroll) el.scrollIntoView({ block: "center", inline: "center" });
  const box = el.getBoundingClientRect();
  const cx = box.left + box.width / 2;
  const cy = box.top + box.height / 2;
  const top = window.screenY + (window.outerHeight - window.innerHeight);
  const hit = document.elementFromPoint(cx, cy);
  const dpr = window.devicePixelRatio;
  return {
    x: Math.round((window.screenX + cx) * dpr),
    y: Math.round((top + cy) * dpr),
    css: { x: Math.round(cx), y: Math.round(cy), width: Math.round(box.width), height: Math.round(box.height) },
    matches: matches.length,
    inViewport: cx >= 0 && cy >= 0 && cx <= window.innerWidth && cy <= window.innerHeight,
    covered: !(hit && (el.contains(hit) || hit.contains(el))),
    neverInFront: window.outerHeight === window.innerHeight,
  };
}`;

const find = (page, target, scroll = false) =>
  evaluate(page, `(${locate})(${JSON.stringify(target)}, ${scroll})`);

const pause = (seconds) => new Promise((resolve) => setTimeout(resolve, seconds * 1000));

const loginPage = (page) =>
  evaluate(page, `/^auth[.]/.test(location.hostname) ? location.href : ""`).catch(() => "");

async function poll(page, check, seconds, what) {
  const started = Date.now();
  while (Date.now() - started < seconds * 1000) {
    const value = await check().catch(() => null);
    if (value) return { value, waited: ((Date.now() - started) / 1000).toFixed(1) };
    const login = await loginPage(page);
    if (login) fail(`The tab is on the login page ${login}. Log in as verify.md says, then run this again.`);
    await pause(0.25);
  }
  fail(`${what} did not show in ${seconds} s.`);
}

async function capture(page, params) {
  const result = await Promise.race([page.send("Page.captureScreenshot", params), pause(5)]);
  if (!result) fail("No screenshot in 5 s: a background tab often does not paint. Take a real frame with video.sh try.");
  return result;
}

const waitFor = async (page, target, seconds) =>
  (await poll(page, () => find(page, target), seconds, `"${target}"`)).waited;

const commands = {
  async list(filter = "") {
    const tabs = await (await fetch(`${http}/json/list`)).json();
    for (const t of tabs) {
      if (t.type === "page" && `${t.url} ${t.title}`.includes(filter)) console.log(`${t.id}  ${t.url}  ${t.title}`);
    }
  },

  async open(url) {
    const { targetId } = await (await browser()).send("Target.createTarget", { url, background: true });
    console.log(targetId);
  },

  async close(id) {
    console.log(await (await fetch(`${http}/json/close/${id}`)).text());
  },

  async fit(id, width, height) {
    const chrome = await browser();
    const { windowId } = await chrome.send("Browser.getWindowForTarget", { targetId: id });
    await chrome.send("Browser.setWindowBounds", { windowId, bounds: { windowState: "normal" } });
    const bounds = { left: 0, top: 0, width: Number(width), height: Number(height) };
    await chrome.send("Browser.setWindowBounds", { windowId, bounds });
    console.log(`${width}x${height}`);
  },

  async goto(id, url, target = "", seconds = 15) {
    const page = await tab(id);
    const started = Date.now();
    await page.send("Page.navigate", { url });
    if (!target) return console.log("navigated");
    await pause(0.5);
    await waitFor(page, target, Number(seconds));
    console.log(`"${target}" showed after ${((Date.now() - started) / 1000).toFixed(1)} s`);
  },

  async wait(id, target, seconds = 15) {
    console.log(`"${target}" showed after ${await waitFor(await tab(id), target, Number(seconds))} s`);
  },

  async waitjs(id, expression, seconds = 15) {
    const page = await tab(id);
    const { value, waited } = await poll(page, () => evaluate(page, expression), Number(seconds), `"${expression}"`);
    console.log(`true after ${waited} s: ${typeof value === "string" ? value : JSON.stringify(value)}`);
  },

  async pause(seconds) {
    await pause(Number(seconds));
    console.log(`paused ${seconds} s`);
  },

  async popup(id, count, ...targets) {
    if (!targets.length) fail(usage);
    const page = await tab(id);
    await evaluate(page, "window.__opened = []; window.open = (url) => { window.__opened.push(String(url)); return null; }; 0");
    for (let i = 1; i <= Number(count); i++) {
      for (const target of targets) {
        await poll(page, async () => (await find(page, target))?.covered === false, 30, `"${target}" uncovered`);
        await commands.click(id, target);
      }
      const { value, waited } = await poll(page, () => evaluate(page, `window.__opened[${i - 1}]`), 60, `New tab ${i}`);
      console.log(`${value}  (opened ${waited} s after the last click)`);
    }
  },

  async point(id, ...targets) {
    if (!targets.length) fail(usage);
    const page = await tab(id);
    for (const target of targets) {
      const found = await find(page, target);
      if (!found) fail(`"${target}" is not on the page.`);
      if (found.neverInFront) fail("This tab was never in front, so its screen offset reads 0. Run video.sh front on it, then measure again.");
      const { neverInFront, ...measured } = found;
      console.log(`${target}  ${JSON.stringify(measured)}`);
    }
  },

  async click(id, target) {
    const page = await tab(id);
    const found = await find(page, target, true);
    if (!found) fail(`"${target}" is not on the page.`);
    const at = { x: found.css.x, y: found.css.y, button: "left", clickCount: 1 };
    await page.send("Input.dispatchMouseEvent", { ...at, type: "mouseMoved", button: "none" });
    await page.send("Input.dispatchMouseEvent", { ...at, type: "mousePressed" });
    await page.send("Input.dispatchMouseEvent", { ...at, type: "mouseReleased" });
    console.log(`clicked "${target}" (${found.matches} match${found.matches === 1 ? "" : "es"})`);
  },

  async eval(id, expression) {
    const source = expression.startsWith("@") ? readFileSync(expression.slice(1), "utf8") : expression;
    const value = await evaluate(await tab(id), source);
    console.log(typeof value === "string" ? value : JSON.stringify(value, null, 1));
  },

  async call(id, ...pairs) {
    const page = await tab(id);
    for (let i = 0; i < pairs.length; i += 2) {
      const result = await page.send(pairs[i], JSON.parse(pairs[i + 1] ?? "{}"));
      console.log(JSON.stringify(result).slice(0, 2000));
    }
  },

  async shot(id, out) {
    const page = await tab(id);
    const { data } = await capture(page, { format: "png" });
    writeFileSync(out, Buffer.from(data, "base64"));
    console.log(out);
  },

  async crop(id, out, targets, scale = 2) {
    const page = await tab(id);
    const boxes = [];
    for (const target of targets.split("|").map((t) => t.trim()).filter(Boolean)) {
      const found = await find(page, target);
      if (!found) fail(`"${target}" is not on the page.`);
      const { x, y, width, height } = found.css;
      boxes.push({ left: x - width / 2, top: y - height / 2, right: x + width / 2, bottom: y + height / 2 });
    }
    const [scrollX, scrollY, viewWidth, viewHeight] = await evaluate(page, "[scrollX, scrollY, innerWidth, innerHeight]");
    const outside = boxes.some((b) => b.left < 0 || b.top < 0 || b.right > viewWidth || b.bottom > viewHeight);
    if (outside) fail(`"${targets}" is not fully in the viewport. Scroll it into view before the shot.`);
    const margin = 8;
    const left = Math.max(0, Math.min(...boxes.map((b) => b.left)) - margin);
    const top = Math.max(0, Math.min(...boxes.map((b) => b.top)) - margin);
    const clip = {
      x: left + scrollX,
      y: top + scrollY,
      width: Math.max(...boxes.map((b) => b.right)) + margin - left,
      height: Math.max(...boxes.map((b) => b.bottom)) + margin - top,
      scale: Number(scale),
    };
    const { data } = await capture(page, { format: "png", clip });
    writeFileSync(out, Buffer.from(data, "base64"));
    console.log(`${out}  ${Math.round(clip.width)}x${Math.round(clip.height)} css px at ${clip.scale}x`);
  },

  async listen(id, out, seconds, pattern = "") {
    const page = await tab(id);
    const filter = new RegExp(pattern, "i");
    const started = Date.now();
    const requests = new Map();
    const log = (entry) => appendFileSync(out, `${JSON.stringify({ t: Number(((Date.now() - started) / 1000).toFixed(1)), ...entry })}\n`);
    writeFileSync(out, "");
    page.on(({ method, params: p }) => {
      if (method === "Network.requestWillBeSent") {
        const request = { method: p.request.method, url: p.request.url };
        const api = p.type === "XHR" || p.type === "Fetch";
        requests.set(p.requestId, { ...request, logged: api && filter.test(request.url) });
        if (!requests.get(p.requestId).logged) return;
        log({ ev: "req", ...request, body: p.request.postData?.slice(0, 2000) });
      } else if (method === "Network.responseReceived") {
        const { logged, ...request } = requests.get(p.requestId) ?? {};
        if (p.response.status >= 400) log({ ev: "fail", status: p.response.status, ...request });
        else if (logged) log({ ev: "res", status: p.response.status, ...request });
      } else if (method === "Network.loadingFailed") {
        const { logged, ...request } = requests.get(p.requestId) ?? {};
        log({ ev: "loadingFailed", error: p.errorText, canceled: p.canceled, ...request });
      } else if (method === "Runtime.consoleAPICalled" && (p.type === "error" || p.type === "warning")) {
        const text = p.args.map((arg) => arg.value ?? arg.description ?? "").join(" ");
        log({ ev: "console", type: p.type, text: text.slice(0, 400) });
      } else if (method === "Runtime.exceptionThrown") {
        log({ ev: "exception", text: (p.exceptionDetails.exception?.description ?? p.exceptionDetails.text).slice(0, 400) });
      } else if (method === "Log.entryAdded" && p.entry.level === "error") {
        log({ ev: "log", text: p.entry.text.slice(0, 300), url: p.entry.url });
      }
    });
    for (const domain of ["Network", "Runtime", "Log"]) await page.send(`${domain}.enable`);
    await Promise.race([pause(Number(seconds)), page.closed]);
  },
};

if (!commands[command] || args.length < commands[command].length) fail(usage);
try {
  await commands[command](...args);
  process.exit(0);
} catch (error) {
  fail(error.message);
}
