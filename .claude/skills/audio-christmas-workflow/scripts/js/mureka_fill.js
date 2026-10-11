async () => {
  const P = /*PARAMS*/null;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const setText = (el, value) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const style = document.querySelector('textarea[placeholder^="Enter style"]');
  const title = [...document.querySelectorAll('input[placeholder="Enter song title"]')].find(t => t.maxLength === 50);
  const toggle = () => [...document.querySelectorAll('button.mu-switch, [role=switch]')].find(s => /Instrumental/.test(s.parentElement?.parentElement?.innerText || ''));
  const sw = toggle();
  if (!style || !title || !sw) return { ok: false, error: 'không thấy ô Style / Title / công tắc Instrumental' };
  const lyricsBox = () => document.querySelector('textarea[placeholder^="Enter lyrics"]');
  if (P.instrumental && lyricsBox()?.value) { setText(lyricsBox(), ''); await sleep(300); }
  if ((sw.getAttribute('aria-checked') === 'true') !== P.instrumental) { sw.click(); await sleep(1000); }
  if (!P.instrumental) {
    if (!lyricsBox()) return { ok: false, error: 'tắt Instrumental nhưng không thấy ô Lyrics' };
    setText(lyricsBox(), P.lyrics);
  }
  const box = () => document.querySelector('textarea[placeholder^="Enter style"]');
  const name = () => [...document.querySelectorAll('input[placeholder="Enter song title"]')].find(t => t.maxLength === 50);
  setText(box(), P.prompt);
  setText(name(), P.title);
  await sleep(800);
  const remixCard = [...document.querySelectorAll('*')].find(e => e.childElementCount === 0 && [P.source, `${P.source}(Remix)`].includes((e.innerText || '').trim()));
  const create = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Create');
  const form = {
    remix_source: remixCard ? P.source : null,
    instrumental: toggle()?.getAttribute('aria-checked') === 'true',
    lyrics: lyricsBox()?.value || '',
    style: box().value,
    title: name().value,
    card: remixCard?.parentElement?.parentElement?.innerText?.replace(/\s+/g, ' ').trim() || null,
    create_enabled: !!create && !create.disabled && !create.classList.contains('is-disabled'),
    gold: Number([...document.body.innerText.matchAll(/(\d[\d,]*)\s*Gold\b/g)].pop()?.[1]?.replace(/,/g, '')) || null,
  };
  const problems = [];
  if (form.remix_source !== P.source) problems.push(`Remix chưa gắn file ${P.source}`);
  if (form.instrumental !== P.instrumental) problems.push(P.instrumental ? 'Instrumental chưa bật' : 'Instrumental chưa tắt');
  if (P.instrumental && form.lyrics) problems.push('ô Lyrics không trống');
  if (!P.instrumental && form.lyrics !== P.lyrics) problems.push('ô Lyrics lệch lyrics ahh/ooh');
  if (form.style !== P.prompt) problems.push(`Style lệch prompt (${form.style.length}/${P.prompt.length} ký tự)`);
  if (form.title !== P.title) problems.push(`Title lệch: ${form.title}`);
  if (!form.create_enabled) problems.push('nút Create đang tắt');
  return { ok: problems.length === 0, problems, form };
}
