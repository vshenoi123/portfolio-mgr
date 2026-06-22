'use client';

import { useState, useEffect, useCallback } from 'react';
import { getTickerDetails } from '@/lib/api';

const cache = {};

export function useTickerDetails(tickers = []) {
  const [details, setDetails] = useState({});
  const [loading, setLoading] = useState(false);

  const key = tickers.sort().join(',');

  const fetchDetails = useCallback(async () => {
    const missing = tickers.filter((t) => !cache[t]);
    if (missing.length === 0) {
      const result = {};
      tickers.forEach((t) => { result[t] = cache[t]; });
      setDetails(result);
      return;
    }

    setLoading(true);
    try {
      const data = await getTickerDetails(missing);
      if (data.details) {
        Object.entries(data.details).forEach(([ticker, info]) => {
          cache[ticker] = info;
        });
      }
      const result = {};
      tickers.forEach((t) => { result[t] = cache[t] || {}; });
      setDetails(result);
    } catch {
      const result = {};
      tickers.forEach((t) => { result[t] = cache[t] || {}; });
      setDetails(result);
    } finally {
      setLoading(false);
    }
  }, [key]);

  useEffect(() => {
    if (tickers.length > 0) fetchDetails();
  }, [key]);

  return { details, loading };
}
