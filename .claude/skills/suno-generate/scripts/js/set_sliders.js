async () => {
  const P = /*PARAMS*/null;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const out = {};
  for (const [label, target] of Object.entries(P)) {
    const s = [...document.querySelectorAll(`[role=slider][aria-label="${label}"]`)].find(e => e.offsetParent !== null);
    if (!s) { out[label] = { ok: false, error: 'not found (More Options chưa mở? Audio Influence chỉ có khi đã chọn Voice)' }; continue; }
    s.focus();
    let cur = Number(s.getAttribute('aria-valuenow'));
    for (let i = 0; i < 150 && cur !== target; i++) {
      const key = cur < target ? 'ArrowRight' : 'ArrowLeft';
      s.dispatchEvent(new KeyboardEvent('keydown', { key, code: key, bubbles: true, cancelable: true }));
      s.dispatchEvent(new KeyboardEvent('keyup', { key, code: key, bubbles: true, cancelable: true }));
      await sleep(120);
      const nxt = Number(s.getAttribute('aria-valuenow'));
      if (nxt === cur) { await sleep(250); if (Number(s.getAttribute('aria-valuenow')) === cur) break; }
      cur = Number(s.getAttribute('aria-valuenow'));
    }
    out[label] = { ok: cur === target, value: cur, target };
  }
  return out;
}
