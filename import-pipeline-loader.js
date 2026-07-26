(function() {
  const s = JSON.parse(arguments[0] || '[]');
  if (!Array.isArray(s)) { console.error('Not an array'); return; }
  const k = 'daybook-v1';
  const state = JSON.parse(localStorage.getItem(k) || '{}');
  state.jobs = state.jobs || [];
  let added = 0, updated = 0;
  for (const j of s) {
    const idx = state.jobs.findIndex(x => x.id === j.id);
    if (idx >= 0) { state.jobs[idx] = Object.assign(state.jobs[idx], j); updated++; }
    else { state.jobs.unshift(j); added++; }
  }
  localStorage.setItem(k, JSON.stringify(state));
  if (window.cloud && window.cloudUser) {
    try { window.cloud.from('daybook_data').upsert({ user_id: window.cloudUser.id, data: state, updated_at: new Date().toISOString() }); } catch(e) {}
  }
  console.log('Import complete. Added: ' + added + ', Updated: ' + updated + '. Reload the page to see them.');
})()
