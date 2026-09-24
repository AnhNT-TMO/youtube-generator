// Dự phòng khi không bắt được response của POST /api/generate/v2-web/: tìm clip mới nhất theo title, tạo sau `since`.
// P = {"title": "...", "since": "2026-09-23T02:50:00Z"}. Chỉ đọc.
async () => {
  const P = /*PARAMS*/null;
  const tok = document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('__session=')).slice(10);
  const r = await fetch('https://studio-api-prod.suno.com/api/feed/v3', { method: 'POST',
    headers: { 'content-type': 'application/json', authorization: 'Bearer ' + tok }, body: JSON.stringify({ limit: 20 }) });
  const clips = (await r.json()).clips || [];
  return clips.filter(c => c.title === P.title && new Date(c.created_at) >= new Date(P.since))
    .map(c => ({ id: c.id, title: c.title, status: c.status, created_at: c.created_at, duration: c.metadata?.duration }));
}
