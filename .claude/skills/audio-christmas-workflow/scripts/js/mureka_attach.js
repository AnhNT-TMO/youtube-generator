async () => {
  const P = /*PARAMS*/null;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const waitFor = async (fn, n = 40, ms = 300) => { for (let i = 0; i < n; i++) { const v = fn(); if (v) return v; await sleep(ms); } return null; };
  const leaf = re => [...document.querySelectorAll('*')].find(e => e.childElementCount === 0 && re.test((e.innerText || '').trim()));
  const button = re => [...document.querySelectorAll('button')].find(b => re.test(b.innerText.trim()));
  const custom = leaf(/^Custom$/);
  if (custom) { custom.click(); await sleep(400); }
  const attached = [...document.querySelectorAll('*')].find(e => e.childElementCount === 0 && (e.innerText || '').trim() === `${P.name}(Remix)`);
  if (attached) return { ok: true, already_attached: true };
  const remix = leaf(/^Remix$/);
  if (!remix) return { ok: false, step: 'remix', error: 'không thấy nút + Remix trên tab Custom' };
  remix.click();
  const upload = await waitFor(() => button(/^Upload$/));
  if (!upload) return { ok: false, step: 'dialog', error: 'không mở được hộp Remix' };
  upload.click();
  await sleep(800);
  const row = await waitFor(() => [...document.querySelectorAll('.shared-resource-library__row')].find(r =>
    r.querySelector('.shared-resource-library__row-title')?.textContent.trim() === P.name
    && P.durations.includes(r.querySelector('.shared-resource-library__row-primary-desc')?.textContent.trim())), 10, 300);
  if (!row) return { ok: false, step: 'pick', need_upload: true, error: `chưa có file ${P.name} (${P.durations.join(' hoặc ')}) trong Upload: upload_file ${P.upload} vào input "歌曲文件" rồi chạy lại` };
  const use = row.querySelector('.shared-resource-library__row-use button');
  if (!use) return { ok: false, step: 'use', error: 'không thấy nút Use' };
  use.click();
  const loaded = await waitFor(() => { const m = (document.body.innerText.match(/00:00\/(\d\d:\d\d)/) || [])[1]; return m && m !== '00:00' ? m : null; }, 60, 300);
  const save = await waitFor(() => button(/^Save$/));
  if (!save) return { ok: false, step: 'save', error: 'không thấy nút Save' };
  if (!P.durations.includes(loaded)) return { ok: false, step: 'clip', error: `clip dài ${loaded}, cần ${P.durations.join(' hoặc ')}` };
  let closed = false;
  for (let i = 0; i < 8 && !closed; i++) {
    await sleep(1000);
    button(/^Save$/)?.click();
    closed = !!(await waitFor(() => !button(/^Save$/), 5, 300));
  }
  if (!closed) return { ok: false, step: 'save', error: 'bấm Save mà hộp Select Music Clip không đóng' };
  return { ok: true, clip: loaded };
}
