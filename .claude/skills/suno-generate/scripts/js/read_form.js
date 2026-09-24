async () => {
  const vis = e => !!e && e.offsetParent !== null;
  const on = b => b.className.includes('variant-standard-legacy');
  const leaf = label => [...document.querySelectorAll('*')].find(e => e.childElementCount === 0 && e.textContent.trim() === label && vis(e));
  const row = label => {
    const t = leaf(label); if (!t) return null;
    let r = t.parentElement;
    for (let i = 0; i < 3 && r.querySelectorAll('button').length < 2; i++) r = r.parentElement;
    return [...r.querySelectorAll('button')].filter(on).map(b => b.innerText.trim());
  };
  const ed = document.querySelector('[aria-label="Lyrics editor"]');
  const lyrics = ed ? [...ed.children].map(p => p.textContent).join('\n') : null;
  const lyricsCount = [...document.querySelectorAll('*')].map(e => e.childElementCount === 0 ? e.textContent : '').find(s => /of 5000 characters/.test(s)) || null;
  const tas = [...document.querySelectorAll('textarea')].filter(t => vis(t) && t.getAttribute('aria-label') !== 'Cowriter prompt');
  const near1000 = t => { let r = t; for (let i = 0; i < 4 && r; i++) { r = r.parentElement; if (r && /\d+\s*\/\s*1000/.test(r.innerText)) return true; } return false; };
  const styleBox = tas.find(near1000) || (tas.length === 1 ? tas[0] : null);
  const input = sel => [...document.querySelectorAll(sel)].find(vis) || null;
  const credits = [...document.querySelectorAll('button')].map(b => b.getAttribute('aria-label') || '').find(s => /^Credits remaining/.test(s));
  const modeBtns = [...document.querySelectorAll('button')].filter(b => vis(b) && /^(Simple|Advanced|Custom)$/.test(b.innerText.trim()))
    .map(b => ({ text: b.innerText.trim(), on: on(b), selected: b.getAttribute('aria-selected') }));
  return {
    url: location.href,
    mode_buttons: modeBtns,
    model: [...document.querySelectorAll('button')].find(b => vis(b) && /^v\d/.test(b.innerText.trim()))?.innerText.trim() || null,
    voice: (() => { const rm = document.querySelector('button[aria-label="Remove selected Voice"]'); if (!rm) return null;
      let r = rm; for (let i = 0; i < 6 && r; i++) { r = r.parentElement; const t = (r?.innerText || '').trim(); if (t) return t.split('\n')[0].trim(); }
      return null; })(),
    lyrics, lyrics_count: lyricsCount,
    style: styleBox ? styleBox.value : null,
    style_candidates: tas.length,
    exclude: input('[aria-label="Exclude styles"], input[placeholder="Exclude styles"]')?.value ?? null,
    title: input('[aria-label="Song Title (Optional)"], input[placeholder="Song Title (Optional)"]')?.value ?? null,
    style_counter: [...document.querySelectorAll('*')].map(e => e.childElementCount === 0 ? e.textContent.trim() : '').find(t => /^\d+\/1000$/.test(t)) || null,
    vocal_gender: row('Vocal Gender'),
    max_mode: row('Max Mode'),
    personalize: row('Personalize'),
    duration: input('input[aria-label="Duration"]')?.value || (leaf('Duration') ? 'Auto' : null),
    sliders: Object.fromEntries([...document.querySelectorAll('[role=slider]')].filter(vis)
      .map(s => [s.getAttribute('aria-label'), Number(s.getAttribute('aria-valuenow'))])),
    credits: credits ? Number(credits.replace(/[^0-9]/g, '')) : null,
    create_button: !!document.querySelector('button[aria-label="Create song"]'),
  };
}
