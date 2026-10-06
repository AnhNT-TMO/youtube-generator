async () => {
  const vis = e => !!e && e.offsetParent !== null;
  const buttons = [...document.querySelectorAll('button')].filter(vis);
  const tabs = [...document.querySelectorAll('[role=tab]')].filter(vis)
    .map(t => ({ text: t.innerText.trim(), selected: t.getAttribute('aria-selected') === 'true' }));
  const boxes = [...document.querySelectorAll('textarea')].filter(vis)
    .filter(t => !['Cowriter prompt', 'Search clips'].includes(t.getAttribute('aria-label')));
  const leafText = re => [...document.querySelectorAll('*')].some(e => e.childElementCount === 0 && vis(e) && re.test(e.textContent.trim()));
  const removes = buttons.map(b => b.getAttribute('aria-label') || '').filter(s => /^Remove/i.test(s));
  const credits = buttons.map(b => b.getAttribute('aria-label') || '').find(s => /^Credits remaining/.test(s));
  const addVoice = buttons.some(b => b.getAttribute('aria-label') === 'Add Voice');
  const chips = [...document.querySelectorAll('span[data-thumb][title]')].filter(vis).map(s => s.title);
  const create = document.querySelector('button[aria-label="Create song"]');
  return {
    url: location.href,
    tabs,
    model: buttons.find(b => /^v\d/.test(b.innerText.trim()))?.innerText.trim() || null,
    prompt: boxes.length === 1 ? boxes[0].value : null,
    prompt_boxes: boxes.length,
    lyrics_editor: vis(document.querySelector('[aria-label="Lyrics editor"]')),
    style_counter: leafText(/^\d+\/1000$/),
    voice_selected: removes.includes('Remove selected Voice') || !addVoice,
    voice_name: !addVoice && chips.length === 1 && removes.includes('Remove ' + chips[0]) ? chips[0] : null,
    voice_chips: chips,
    remove_buttons: removes,
    credits: credits ? Number(credits.replace(/[^0-9]/g, '')) : null,
    create_button: !!create,
    create_enabled: !!create && !create.disabled,
    read_at: new Date().toISOString(),
  };
}
