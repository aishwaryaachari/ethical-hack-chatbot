export const API = 'http://localhost:8000';

export async function chatAsk(prompt: string, user_id: string, mode: string) {
  const r = await fetch(`${API}/api/attack1/simulate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, user_id, mode })
  });
  return r.json();
}
export async function uploadDoc(file: File, owner_id: string, tenant_id: string, topic_id?: string) {
  const fd = new FormData();
  fd.append('file', file); fd.append('owner_id', owner_id); fd.append('tenant_id', tenant_id);
  if (topic_id) fd.append('topic_id', topic_id);
  const r = await fetch(`${API}/api/rag/upload`, { method: 'POST', body: fd });
  return r.json();
}
export async function queryDocs(question: string, user_id: string, tenant_id: string, mode: string, topic_id?: string) {
  const r = await fetch(`${API}/api/rag/query`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, victim_id: user_id, victim_tenant: tenant_id, mode, topic_id: topic_id ?? null })
  });
  return r.json();
}
export async function getStats() {
  return (await fetch(`${API}/api/dashboard/stats`)).json();
}
export async function getEvents() {
  return (await fetch(`${API}/api/events?limit=50`)).json();
}
export async function getLlmStatus() {
  return (await fetch(`${API}/api/llm/status`)).json();
}
export async function getUsers() {
  const r = await fetch(`${API}/api/users`);
  if (!r.ok) throw new Error('users unavailable');
  return r.json();
}
export async function listTopics(owner_id: string) {
  return (await fetch(`${API}/api/rag/topics?owner_id=${encodeURIComponent(owner_id)}`)).json();
}
export async function createTopic(owner_id: string, tenant_id: string, title: string) {
  const r = await fetch(`${API}/api/rag/topics`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner_id, tenant_id, title })
  });
  return r.json();
}
export async function deleteTopic(topic_id: string, owner_id: string) {
  const r = await fetch(`${API}/api/rag/topics/${topic_id}?owner_id=${encodeURIComponent(owner_id)}`, { method: 'DELETE' });
  return r.json();
}
export async function topicDocs(topic_id: string, owner_id: string) {
  return (await fetch(`${API}/api/rag/topics/${topic_id}/docs?owner_id=${encodeURIComponent(owner_id)}`)).json();
}
export async function resetKb() {
  const r = await fetch(`${API}/api/rag/reset`, { method: 'POST' });
  return r.json();
}
export async function deleteDoc(doc_id: string, owner_id: string) {
  const r = await fetch(`${API}/api/rag/docs/${encodeURIComponent(doc_id)}?owner_id=${encodeURIComponent(owner_id)}`, { method: 'DELETE' });
  return r.json();
}
