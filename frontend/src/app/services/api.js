const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

async function request(path, options = {}) {
  const token = sessionStorage.getItem('urbansense_token');
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail || payload.error || `Request failed (${response.status})`;
    if (response.status === 401) {
      sessionStorage.removeItem('urbansense_token');
    }
    throw new Error(detail);
  }

  return response.status === 204 ? null : response.json();
}

export const api = {
  login: (email, password) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  getSummary: () => request('/api/summary'),
  getVehicles: () => request('/api/vehicles'),
  getIssues: () => request('/api/issues'),
  getManualReports: () => request('/api/manual-reports'),
  getAlerts: () => request('/api/alerts'),
  getMaintenance: () => request('/api/maintenance'),
  getEvents: () => request('/api/events'),
};

export default api;
