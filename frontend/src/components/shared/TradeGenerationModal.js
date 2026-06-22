'use client';

import { useState, useEffect } from 'react';
import { X, RefreshCw, Send, AlertTriangle, CheckCircle } from 'lucide-react';
import { generateTrade, executeTrade } from '@/lib/api';

function formatCurrency(v) {
  if (v == null) return '-';
  return `$${Number(v).toFixed(2)}`;
}

export default function TradeGenerationModal({ ticker, onClose }) {
  const [dte, setDte] = useState(30);
  const [targetDelta, setTargetDelta] = useState(0.30);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [trade, setTrade] = useState(null);
  const [strategy, setStrategy] = useState(null);
  const [context, setContext] = useState(null);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [liveData, setLiveData] = useState(false);

  const fetchTrade = async () => {
    setLoading(true);
    setError(null);
    setTrade(null);
    setStrategy(null);
    setContext(null);
    setLiveData(false);
    try {
      const data = await generateTrade(ticker, dte, targetDelta);
      setTrade(data.trade);
      setStrategy(data.strategy_output);
      setContext(data.context);
      setLiveData(data.live_data || false);
      if (!data.trade) {
        setError(data.message || 'No trade generated for this recommendation');
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTrade(); }, [ticker, dte, targetDelta]);

  const handleExecute = async () => {
    setExecuting(true);
    setResult(null);
    try {
      const res = await executeTrade(ticker, dte, targetDelta, quantity);
      setResult(res);
    } catch (e) {
      setResult({ success: false, message: e.message });
    } finally {
      setExecuting(false);
    }
  };

  const strategyLabel = strategy?.recommendation?.replace(/_/g, ' ').toUpperCase() || '';
  const confidence = strategy?.confidence ?? 0;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-terminal-bg-card border border-terminal-border rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-terminal-border">
          <div>
            <h2 className="text-lg font-sans font-bold text-terminal-text">Generate Trade — {ticker}</h2>
            {strategy && (
              <div className="flex items-center gap-2 mt-1">
                <span className="px-2 py-0.5 text-xs font-mono rounded bg-terminal-green/10 text-terminal-green border border-terminal-green/20 uppercase">
                  {strategyLabel}
                </span>
                <span className="text-xs font-mono text-terminal-text-muted">
                  {Math.round(confidence * 100)}% confidence
                </span>
                {liveData && (
                  <span className="px-2 py-0.5 text-xs font-mono rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                    LIVE DATA
                  </span>
                )}
                {!liveData && trade && (
                  <span className="px-2 py-0.5 text-xs font-mono rounded bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                    CALCULATED
                  </span>
                )}
              </div>
            )}
          </div>
          <button onClick={onClose} className="text-terminal-text-muted hover:text-terminal-text">
            <X size={20} />
          </button>
        </div>

        {/* Parameters */}
        <div className="p-5 border-b border-terminal-border">
          <h3 className="text-sm font-sans font-semibold text-terminal-text mb-3">Parameters</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Days to Expiry</label>
              <select value={dte} onChange={(e) => setDte(Number(e.target.value))}
                className="w-full mt-1 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono text-terminal-text focus:outline-none focus:border-terminal-green/50">
                <option value={7}>7 DTE</option>
                <option value={14}>14 DTE</option>
                <option value={21}>21 DTE</option>
                <option value={30}>30 DTE</option>
                <option value={45}>45 DTE</option>
                <option value={60}>60 DTE</option>
                <option value={90}>90 DTE</option>
                <option value={180}>180 DTE</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Target Delta</label>
              <select value={targetDelta} onChange={(e) => setTargetDelta(Number(e.target.value))}
                className="w-full mt-1 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono text-terminal-text focus:outline-none focus:border-terminal-green/50">
                <option value={0.10}>0.10 (Conservative)</option>
                <option value={0.20}>0.20</option>
                <option value={0.30}>0.30 (Standard)</option>
                <option value={0.40}>0.40</option>
                <option value={0.50}>0.50 (ATM)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Quantity</label>
              <input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))}
                className="w-full mt-1 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono text-terminal-text focus:outline-none focus:border-terminal-green/50" />
            </div>
          </div>
          <button onClick={fetchTrade} disabled={loading}
            className="mt-3 flex items-center gap-2 px-3 py-1.5 text-xs font-mono text-terminal-green border border-terminal-green/30 rounded-lg hover:bg-terminal-green/10 transition-colors">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Recalculate
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-5 mt-4 bg-terminal-red/10 border border-terminal-red/30 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle size={16} className="text-terminal-red shrink-0" />
            <p className="text-sm font-mono text-terminal-red">{error}</p>
          </div>
        )}

        {/* Loading */}
        {loading && !trade && (
          <div className="p-10 text-center">
            <RefreshCw size={24} className="text-terminal-green animate-spin mx-auto" />
            <p className="text-sm font-mono text-terminal-text-muted mt-3">Calculating trade...</p>
          </div>
        )}

        {/* Trade Details */}
        {trade && (
          <div className="p-5">
            <h3 className="text-sm font-sans font-semibold text-terminal-text mb-3">Trade Details</h3>
            <div className="grid grid-cols-2 gap-4">
              {trade.strike != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Strike</p>
                  <p className="text-lg font-mono font-bold text-terminal-green">{formatCurrency(trade.strike)}</p>
                </div>
              )}
              {trade.long_strike != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Long Strike / Short Strike</p>
                  <p className="text-lg font-mono font-bold text-terminal-green">{formatCurrency(trade.long_strike)} / {formatCurrency(trade.short_strike)}</p>
                </div>
              )}
              {trade.premium != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Premium</p>
                  <p className="text-lg font-mono font-bold text-terminal-text">{formatCurrency(trade.premium)}</p>
                </div>
              )}
              {trade.net_debit != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Net Debit</p>
                  <p className="text-lg font-mono font-bold text-terminal-text">{formatCurrency(trade.net_debit)}</p>
                </div>
              )}
              {trade.delta != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Delta</p>
                  <p className="text-sm font-mono text-terminal-text">{trade.delta.toFixed(4)}</p>
                </div>
              )}
              {trade.annualized_yield != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Annualized Yield</p>
                  <p className="text-sm font-mono text-terminal-green">{(trade.annualized_yield * 100).toFixed(1)}%</p>
                </div>
              )}
              {trade.probability_of_profit != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Prob. of Profit</p>
                  <p className="text-sm font-mono text-terminal-text">{(trade.probability_of_profit * 100).toFixed(1)}%</p>
                </div>
              )}
              {trade.max_profit != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Max Profit</p>
                  <p className="text-sm font-mono text-terminal-green">{formatCurrency(trade.max_profit)}</p>
                </div>
              )}
              {trade.max_loss != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Max Loss</p>
                  <p className="text-sm font-mono text-terminal-red">{formatCurrency(trade.max_loss)}</p>
                </div>
              )}
              {trade.break_even != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Break Even</p>
                  <p className="text-sm font-mono text-terminal-text">{formatCurrency(trade.break_even)}</p>
                </div>
              )}
              {trade.leverage_factor != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Leverage</p>
                  <p className="text-sm font-mono text-terminal-text">{trade.leverage_factor.toFixed(1)}x</p>
                </div>
              )}
              {trade.underlying_price != null && (
                <div>
                  <p className="text-xs font-mono text-terminal-text-muted uppercase tracking-wider">Underlying</p>
                  <p className="text-sm font-mono text-terminal-text">{formatCurrency(trade.underlying_price)}</p>
                </div>
              )}
            </div>

            {/* Live Market Data */}
            {trade && (trade.bid != null || trade.open_interest != null) && (
              <div className="mt-4 p-3 rounded-lg bg-terminal-bg-light">
                <p className="text-xs font-mono text-terminal-text-muted mb-2">Market Data</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                  {trade.bid != null && (
                    <div>
                      <p className="text-terminal-text-muted">Bid</p>
                      <p className="text-terminal-text">{formatCurrency(trade.bid)}</p>
                    </div>
                  )}
                  {trade.ask != null && (
                    <div>
                      <p className="text-terminal-text-muted">Ask</p>
                      <p className="text-terminal-text">{formatCurrency(trade.ask)}</p>
                    </div>
                  )}
                  {trade.bid != null && trade.ask != null && (
                    <div>
                      <p className="text-terminal-text-muted">Spread</p>
                      <p className="text-terminal-text">{formatCurrency(trade.ask - trade.bid)}</p>
                    </div>
                  )}
                  {trade.open_interest != null && trade.open_interest > 0 && (
                    <div>
                      <p className="text-terminal-text-muted">Open Interest</p>
                      <p className="text-terminal-text">{trade.open_interest.toLocaleString()}</p>
                    </div>
                  )}
                  {trade.volume != null && trade.volume > 0 && (
                    <div>
                      <p className="text-terminal-text-muted">Volume</p>
                      <p className="text-terminal-text">{trade.volume.toLocaleString()}</p>
                    </div>
                  )}
                  {trade.implied_volatility != null && (
                    <div>
                      <p className="text-terminal-text-muted">IV</p>
                      <p className="text-terminal-text">{(trade.implied_volatility * 100).toFixed(1)}%</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Context */}
            {context && (
              <div className="mt-4 p-3 rounded-lg bg-terminal-bg-light">
                <p className="text-xs font-mono text-terminal-text-muted mb-2">Market Context</p>
                <div className="flex gap-4 text-xs font-mono">
                  <span className="text-terminal-text-muted">Regime: <span className="text-terminal-text">{context.regime}</span></span>
                  <span className="text-terminal-text-muted">RSI: <span className="text-terminal-text">{context.rsi?.toFixed(0)}</span></span>
                  <span className="text-terminal-text-muted">IV%: <span className="text-terminal-text">{(context.iv_percentile * 100).toFixed(0)}%</span></span>
                  <span className="text-terminal-text-muted">Momentum: <span className="text-terminal-text">{(context.momentum * 100).toFixed(1)}%</span></span>
                </div>
              </div>
            )}

            {/* Strategy reasoning */}
            {strategy?.reasoning && (
              <div className="mt-4 p-3 rounded-lg bg-terminal-bg-light">
                <p className="text-xs font-mono text-terminal-text-muted mb-1">Reasoning</p>
                <p className="text-sm font-sans text-terminal-text">{strategy.reasoning}</p>
                {strategy.risk_assessment && (
                  <p className="text-xs font-mono text-terminal-text-muted mt-2">Risk: {strategy.risk_assessment}</p>
                )}
              </div>
            )}

            {/* Execution result */}
            {result && (
              <div className={`mt-4 p-4 rounded-lg border ${result.success ? 'bg-terminal-green/10 border-terminal-green/30' : 'bg-terminal-red/10 border-terminal-red/30'}`}>
                <div className="flex items-center gap-2">
                  {result.success ? <CheckCircle size={16} className="text-terminal-green" /> : <AlertTriangle size={16} className="text-terminal-red" />}
                  <p className={`text-sm font-mono ${result.success ? 'text-terminal-green' : 'text-terminal-red'}`}>
                    {result.message || (result.success ? 'Order submitted successfully' : 'Order failed')}
                  </p>
                </div>
                {result.alpaca_order_id && (
                  <p className="text-xs font-mono text-terminal-text-muted mt-1">Order ID: {result.alpaca_order_id}</p>
                )}
              </div>
            )}

            {/* Execute Button */}
            {!result && (
              <button onClick={handleExecute} disabled={executing}
                className="mt-5 w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-mono font-semibold bg-terminal-green text-black rounded-lg hover:bg-terminal-green-dark transition-colors disabled:opacity-50 disabled:cursor-wait">
                <Send size={16} />
                {executing ? 'Placing Order...' : `Execute Trade (${quantity}x)`}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
