// LUXE.TECH — Official Client API Library (/js/api.js)

const API_BASE = (typeof window !== 'undefined' && window.LUXE_API_URL) || 'http://127.0.0.1:8000/api';

let authToken = typeof window !== 'undefined' ? localStorage.getItem('luxe_auth_token') : null;

export function setAuthToken(token) {
  authToken = token;
  if (typeof window !== 'undefined') {
    if (token) localStorage.setItem('luxe_auth_token', token);
    else localStorage.removeItem('luxe_auth_token');
  }
}

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {}),
    ...(options.headers || {})
  };

  const res = await fetch(url, { ...options, headers });
  const json = await res.json().catch(() => null);

  if (!res.ok) {
    const msg = json?.error?.message || json?.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  if (json && typeof json === 'object' && json.success === false) {
    throw new Error(json.error?.message || 'Intelligence request failed');
  }

  return (json && json.success === true && json.data !== undefined) ? json.data : json;
}

export async function getDashboard() {
  return request('/dashboard');
}

export async function getTrends(params = {}) {
  const q = new URLSearchParams(params).toString();
  return request(`/trends${q ? `?${q}` : ''}`);
}

export async function getTrend(slug) {
  return request(`/trends/${encodeURIComponent(slug)}`);
}

export async function getSignals(trendId) {
  return request(`/signals/${encodeURIComponent(trendId)}`);
}

export async function getCollection(trendId) {
  return request(`/collections/${encodeURIComponent(trendId)}`);
}

export async function getProducts(trendId) {
  if (trendId) return request(`/products/trend/${encodeURIComponent(trendId)}`);
  return request('/products');
}

export async function getRetail(trendId) {
  if (trendId) return request(`/retail/trend/${encodeURIComponent(trendId)}`);
  return request('/retail');
}

export async function getForecast(trendId, horizon = '3_months') {
  return request(`/forecast/${encodeURIComponent(trendId)}?horizon=${horizon}`);
}

export async function getProphecy(trendId) {
  return request(`/prophecy/${encodeURIComponent(trendId)}`);
}

export async function search(query) {
  if (!query) return { trends: [], products: [], collections: [], retail: [], prophecy: [] };
  return request(`/search?q=${encodeURIComponent(query)}`);
}

export async function analyzeImage(file, trendId = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (trendId) formData.append('trend_id', trendId);

  const url = `${API_BASE}/images/analyze`;
  const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};

  const res = await fetch(url, { method: 'POST', body: formData, headers });
  const json = await res.json();
  if (!res.ok || json.success === false) {
    throw new Error(json?.error?.message || 'Image analysis failed');
  }
  return json.data;
}
