const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

async function fetchApi(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function getPortfolioSummary() { return fetchApi('/portfolio'); }
export function getPortfolioHealth() { return fetchApi('/portfolio/health'); }
export function getOpportunities() { return fetchApi('/opportunities'); }
export function getMonitoringSummary() { return fetchApi('/monitoring/summary'); }
export function getPositions() { return fetchApi('/trading/positions'); }
