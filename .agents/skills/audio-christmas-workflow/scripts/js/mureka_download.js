async () => {
  const P = /*PARAMS*/null;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const waitFor = async (fn, n = 60, ms = 500) => { for (let i = 0; i < n; i++) { const v = fn(); if (v) return v; await sleep(ms); } return null; };
  if (!location.href.includes(P.share_key)) return { ok: false, step: 'page', error: `tab chưa mở link ${P.share_key}: navigate_page tới ${P.page_url}` };
  const wav = await waitFor(() => document.querySelector('#format-wav'));
  if (!wav) return { ok: false, step: 'fetch', error: 'murekadownloader không hiện lựa chọn WAV', text: document.body.innerText.slice(0, 300) };
  const shown = (document.querySelector('h1')?.parentElement?.innerText.match(/\b(\d+:\d\d)\b/) || [])[1] || null;
  if (shown !== P.expect) return { ok: false, step: 'duration', shown, error: `trang hiện ${shown}, bài cần ${P.expect}` };
  if (wav.getAttribute('aria-checked') !== 'true') { wav.click(); await sleep(400); }
  const input = await waitFor(() => document.querySelector('#filename'));
  if (!input) return { ok: false, step: 'filename', error: 'không thấy ô File Name' };
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, P.filename);
  input.dispatchEvent(new Event('input', { bubbles: true }));
  await sleep(300);
  const btn = [...document.querySelectorAll('button')].find(b => /Download WAV/.test(b.innerText));
  if (!btn || input.value !== P.filename) return { ok: false, step: 'button', value: input.value, error: 'không đặt được tên file / không thấy Download WAV' };
  btn.click();
  return { ok: true, shown, filename: input.value, started_at: new Date().toISOString() };
}
