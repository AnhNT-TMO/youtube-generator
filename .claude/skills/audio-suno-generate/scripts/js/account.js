async () => {
  const tok = document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('__session=')).slice(10);
  const r = await fetch('https://studio-api-prod.suno.com/api/billing/info/', { headers: { authorization: 'Bearer ' + tok } });
  if (!r.ok) return { error: r.status, body: (await r.text()).slice(0, 300) };
  const b = await r.json();
  return { credits: b.total_credits_left, downloads_used: b.download_usage?.current_period_downloads_used,
           downloads_limit: b.download_usage?.current_period_downloads_limit, at: new Date().toISOString() };
}
