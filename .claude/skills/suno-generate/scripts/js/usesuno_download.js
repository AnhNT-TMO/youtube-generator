// Tải 1 clip qua usesuno.com/tools/downloader/ (KHÔNG bao giờ dùng Download của Suno). Chạy trên tab usesuno
// ngay sau khi navigate/reload trang (modal "Download complete" của lần trước sẽ chặn nếu không reload).
// P = {"url": "https://suno.com/song/<id>", "expect": ["3:16", "3:17"]}  (thời lượng m:ss của đúng clip này)
// Chỉ bấm tải khi trang hiện đúng thời lượng → tránh tải nhầm clip. File về ~/Downloads/<slug> [usesuno.com].wav
async () => {
  const P = /*PARAMS*/null;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const btn = re => [...document.querySelectorAll('button')].find(b => re.test((b.getAttribute('aria-label') || '') + ' ' + b.innerText));
  const waitFor = async (fn, n = 60, ms = 300) => { for (let i = 0; i < n; i++) { const v = fn(); if (v) return v; await sleep(ms); } return null; };
  const find = await waitFor(() => btn(/Find download options/));
  const ta = document.querySelector('textarea');
  if (!find || !ta) return { ok: false, step: 'page', error: 'không thấy ô link / nút Find download options' };
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, P.url);
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  await sleep(300);
  find.click();
  const ready = await waitFor(() => /Ready —/.test(document.body.innerText) && P.expect.some(d => document.body.innerText.includes(d)), 80, 300);
  const title = document.querySelector('article h2')?.innerText || null;
  if (!ready) return { ok: false, step: 'find', title, error: `không thấy "Ready —" kèm thời lượng ${P.expect.join('/')} (sai clip hoặc chưa tải xong)` };
  const audio = await waitFor(() => btn(/Audio\s*CHOOSE FORMAT/i));
  if (!audio) return { ok: false, step: 'audio', title };
  audio.click();
  const wav = await waitFor(() => btn(/^\s*WAV\b/));
  if (!wav) return { ok: false, step: 'wav', title };
  wav.click();
  const cont = await waitFor(() => btn(/Continue download/), 10, 300);
  if (cont) { const cb = document.querySelector('input[type=checkbox]'); if (cb && !cb.checked) cb.click(); cont.click(); }
  return { ok: true, title, notice_accepted: !!cont, started_at: new Date().toISOString() };
}
