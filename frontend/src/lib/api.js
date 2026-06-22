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
export function getPortfolioHoldings() { return fetchApi('/portfolio/holdings'); }
export function getPortfolioHealth() { return fetchApi('/portfolio/health'); }
export function getPortfolioExposure() { return fetchApi('/portfolio/exposure'); }
export function getPortfolioAllocation() { return fetchApi('/portfolio/allocation'); }

export function getOpportunities(strategyType = 'all', topN = 20) {
  const params = new URLSearchParams({ strategy_type: strategyType, top_n: topN });
  return fetchApi(`/opportunities?${params}`);
}

export function getMonitoringSummary() { return fetchApi('/monitoring/summary'); }
export function getMonitoringHealth() { return fetchApi('/monitoring/health'); }
export function getMonitoringAlerts() { return fetchApi('/monitoring/alerts'); }

export function getRegime() { return fetchApi('/analysis/regime'); }

export function getDailyReport() { return fetchApi('/ai/report'); }

export function getPositions() { return fetchApi('/trading/positions'); }
export function syncPositions() { return fetchApi('/trading/sync', { method: 'POST' }); }

export function triggerAction(endpoint, options = {}) { return fetchApi(endpoint, options); }
