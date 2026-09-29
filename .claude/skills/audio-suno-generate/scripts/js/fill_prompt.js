async () => {
  const P = /*PARAMS*/null;
  const vis = e => !!e && e.offsetParent !== null;
  const tab = [...document.querySelectorAll('[role=tab]')].find(t => vis(t) && t.innerText.trim() === 'Simple');
  if (!tab || tab.getAttribute('aria-selected') !== 'true') return { ok: false, error: 'chưa ở tab Simple: bấm tab "Simple" trước' };
  const boxes = [...document.querySelectorAll('textarea')].filter(vis)
    .filter(t => !['Cowriter prompt', 'Search clips'].includes(t.getAttribute('aria-label')));
  if (boxes.length !== 1) return { ok: false, error: `thấy ${boxes.length} ô textarea, Simple chỉ có 1 (đã bấm "+" thêm Lyrics/Styles?)` };
  const ta = boxes[0];
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, P.prompt);
  ta.dispatchEvent(new Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 500));
  const create = document.querySelector('button[aria-label="Create song"]');
  return { ok: ta.value === P.prompt, length: ta.value.length, expected: P.prompt.length,
           create_enabled: !!create && !create.disabled };
}
