async () => {
  const P = /*PARAMS*/null;
  const tok = () => document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('__session=')).slice(10);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const t0 = Date.now();
  let clips = [];
  while (true) {
    const r = await fetch('https://studio-api-prod.suno.com/api/feed/v3', { method: 'POST',
      headers: { 'content-type': 'application/json', authorization: 'Bearer ' + tok() },
      body: JSON.stringify({ filters: { ids: { presence: 'True', clipIds: P.ids } }, limit: P.ids.length }) });
    if (r.ok) clips = (await r.json()).clips || [];
    const done = clips.length === P.ids.length && clips.every(c => ['complete', 'error'].includes(c.status));
    if (done || Date.now() - t0 > (P.timeout_s || 240) * 1000) {
      return { done, waited_s: Math.round((Date.now() - t0) / 1000), clips: clips.map(c => ({
        id: c.id, title: c.title, status: c.status, created_at: c.created_at, model_name: c.model_name,
        major_model_version: c.major_model_version, is_public: c.is_public,
        persona: c.persona ? { id: c.persona.id, name: c.persona.name } : null,
        duration: c.metadata?.duration, tags: c.metadata?.tags, negative_tags: c.metadata?.negative_tags,
        prompt: c.metadata?.prompt, is_max_mode: c.metadata?.is_max_mode, control_sliders: c.metadata?.control_sliders,
        vocal_gender: c.metadata?.vocal_gender, error: c.metadata?.error_message || c.metadata?.error_type || null,
        meta_keys: Object.keys(c.metadata || {}) })) };
    }
    await sleep(6000);
  }
}
