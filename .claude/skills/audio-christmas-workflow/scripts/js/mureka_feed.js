async () => {
  const P = /*PARAMS*/null;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const t0 = Date.now();
  const pick = list => list.find(f => P.feed_id ? String(f.feed_id) === String(P.feed_id)
    : f.generate_at >= P.after_s && f.songs?.some(s => s.title === P.title));
  let feed = null;
  while (true) {
    const r = await fetch(`/api/pgc/feed/list?time=${Date.now()}&t=1&query_type=mysong&listRenderType=mysong&folder_id=${P.folder_id}`);
    if (r.ok) feed = pick((await r.json()).data?.list || []) || null;
    const done = !!feed && feed.state === 3 && (feed.songs || []).every(s => s.generate_state === 3);
    if (done || Date.now() - t0 > (P.timeout_s || 240) * 1000) {
      return { done, waited_s: Math.round((Date.now() - t0) / 1000), feed: feed && {
        feed_id: String(feed.feed_id), state: feed.state, model: feed.model, mode: feed.mode,
        generation_method: feed.generation_method, generate_at: feed.generate_at,
        songs: feed.songs.map(s => ({ song_id: String(s.song_id), title: s.title, share_key: s.share_key,
          duration_ms: s.duration_milliseconds, bpm: s.bpm, generate_state: s.generate_state, is_liked: s.is_liked,
          model: s.model, description: s.description, mp3_url: s.mp3_url })) } };
    }
    await sleep(8000);
  }
}
