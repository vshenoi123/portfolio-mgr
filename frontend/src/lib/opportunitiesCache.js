const cache = {};

export function getCachedOpportunities(strategyType) {
  const entry = cache[strategyType];
  if (!entry) return null;
  return entry;
}

export function setCachedOpportunities(strategyType, data) {
  cache[strategyType] = data;
}

export function clearOpportunitiesCache() {
  Object.keys(cache).forEach((key) => delete cache[key]);
}
