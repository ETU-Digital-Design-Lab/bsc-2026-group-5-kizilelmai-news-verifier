/**
 * api.js — Tüm backend HTTP istekleri merkezi servis katmanı.
 * Bileşenler doğrudan fetch() çağırmaz, bu modülü kullanır.
 */

const BASE_URL = 'http://127.0.0.1:5000';

function authHeader(token) {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchStatus() {
  const res = await fetch(`${BASE_URL}/api/status`);
  if (!res.ok) throw new Error('status_offline');
  return res.json();
}

export async function sendChat(query, token = null, forceRefresh = false) {
  const headers = {
    'Content-Type': 'application/json',
    ...authHeader(token),
  };
  if (forceRefresh) {
    headers['Cache-Control'] = 'no-cache';
    headers['Pragma'] = 'no-cache';
  }
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, force_refresh: forceRefresh }),
  });
  if (!res.ok) throw new Error('chat_error');
  return res.json();
}

export async function clearChat(token = null) {
  const res = await fetch(`${BASE_URL}/api/chat/clear`, {
    method: 'POST',
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error('clear_error');
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function register(email, password, firstName, lastName) {
  const res = await fetch(`${BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, first_name: firstName, last_name: lastName }),
  });
  return res.json();
}

export async function verifyEmail(email, code) {
  const res = await fetch(`${BASE_URL}/api/auth/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, code }),
  });
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  return res.json();
}

// ── Admin: Knowledge Base ─────────────────────────────────────────────────────

export async function fetchRecords(token, page = 1, limit = 50, sort = 'oldest') {
  const res = await fetch(`${BASE_URL}/api/veri?page=${page}&limit=${limit}&sort=${sort}`, {
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error('fetch_records_error');
  return res.json();
}

export async function fetchRecord(token, id) {
  const res = await fetch(`${BASE_URL}/api/veri/${id}`, { headers: authHeader(token) });
  if (!res.ok) throw new Error('fetch_record_error');
  return res.json();
}

export async function injectRecord(token, payload) {
  const res = await fetch(`${BASE_URL}/api/inject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader(token) },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('inject_error');
  return res.json();
}

export async function updateRecord(token, id, payload) {
  const res = await fetch(`${BASE_URL}/api/admin/veri/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeader(token) },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('update_error');
  return res.json();
}

export async function deleteRecord(token, id) {
  const res = await fetch(`${BASE_URL}/api/admin/veri/${id}`, {
    method: 'DELETE',
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error('delete_error');
  return res.json();
}

// ── Reports ───────────────────────────────────────────────────────────────────

export async function createReport(token, payload) {
  const res = await fetch(`${BASE_URL}/api/reports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader(token) },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('report_error');
  return res.json();
}

export async function fetchMyReports(token, page = 1, limit = 50) {
  const res = await fetch(`${BASE_URL}/api/reports/my?page=${page}&limit=${limit}`, {
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error('my_reports_error');
  return res.json();
}

export async function fetchAdminReports(token, page = 1, limit = 50, status = 'all') {
  const res = await fetch(`${BASE_URL}/api/admin/reports?page=${page}&limit=${limit}&status=${status}`, {
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error('admin_reports_error');
  return res.json();
}

export async function respondReport(token, reportId, adminResponse, status) {
  const res = await fetch(`${BASE_URL}/api/admin/reports/${reportId}/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader(token) },
    body: JSON.stringify({ admin_response: adminResponse, status }),
  });
  if (!res.ok) throw new Error('respond_error');
  return res.json();
}
