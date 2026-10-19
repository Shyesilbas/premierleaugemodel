import AuditMatchCard from './model-audit/AuditMatchCard';
import { formatSeasonLabel } from '../utils/dateFormatters';
import React, { useState, useEffect } from 'react';
import { getModelAudit } from '../services/auditService';
import { AlertCircle, ChevronDown, RotateCw } from 'lucide-react';

const SEASON_OPTIONS = [
  { value: '2026_27', label: '2026/27 · Canlı' },
  { value: '2025_26', label: '2025/26 · Tüm sezon' },
  { value: '2024_25', label: '2024/25 · Tüm sezon' },
];

const fmt = (value, prefix = '') => (value === null || value === undefined ? '—' : `${prefix}${value}`);

function StatusDot({ tone = 'muted' }) {
  const tones = {
    success: 'bg-status-success',
    warning: 'bg-status-warning',
    error: 'bg-status-error',
    muted: 'bg-text-muted',
  };
  return <span aria-hidden="true" className={`inline-block w-1.5 h-1.5 rounded-full ${tones[tone]}`} />;
}

function KpiCard({ label, meta, value, secondary, footnote, className = '' }) {
  return (
    <div className={`bg-background-primary border border-border rounded p-4 flex flex-col gap-1 ${className}`}>
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="font-medium text-text-secondary">{label}</span>
        {meta && <span className="text-xs text-text-tertiary tabular-nums">{meta}</span>}
      </div>
      <div className="text-2xl font-semibold text-text-primary tabular-nums">
        {value}
        {secondary && <span className="ml-1 text-sm font-normal text-text-tertiary">{secondary}</span>}
      </div>
      {footnote && <span className="text-xs text-text-tertiary">{footnote}</span>}
    </div>
  );
}

function FilterButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`h-9 px-3 rounded text-sm font-medium inline-flex items-center gap-2 shrink-0 border transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
        active
          ? 'bg-primary border-primary text-white'
          : 'bg-background-primary border-border text-text-secondary hover:text-text-primary hover:border-card-border-hover'
      }`}
    >
      {children}
    </button>
  );
}

function AuditSkeleton() {
  return (
    <div className="flex flex-col gap-6 pb-12 animate-pulse motion-reduce:animate-none" aria-busy="true" aria-label="Yükleniyor">
      <div className="bg-background-primary border border-border rounded p-5 flex flex-col gap-3">
        <div className="h-4 w-48 bg-background-tertiary rounded-sm" />
        <div className="h-7 w-80 max-w-full bg-background-tertiary rounded-sm" />
        <div className="h-4 w-full max-w-xl bg-background-tertiary rounded-sm" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="bg-background-primary border border-border rounded p-4 h-28" />
        ))}
      </div>
      <div className="h-12 bg-background-primary border border-border rounded" />
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-24 bg-background-primary border border-border rounded" />
      ))}
    </div>
  );
}

export default function ModelAuditTab({ selectedSeason = '2026_27', onSelectMatch }) {
  const [auditSeason, setAuditSeason] = useState(selectedSeason || '2026_27');
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selectedGw, setSelectedGw] = useState('all'); // 'all' or gameweek number
  const [marketFilter, setMarketFilter] = useState('all');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (selectedSeason) {
      setAuditSeason(selectedSeason);
      fetchAuditData(false, selectedSeason);
    }
  }, [selectedSeason]);

  const fetchAuditData = (force = false, targetSeason = auditSeason) => {
    if (force) setRefreshing(true);
    else setLoading(true);
    setError(false);

    getModelAudit(targetSeason, force)
      .then(data => {
        setAuditData(data);
        setLoading(false);
        setRefreshing(false);
      })
      .catch(err => {
        console.error('Error fetching model audit:', err);
        setError(true);
        setLoading(false);
        setRefreshing(false);
      });
  };

  const handleSeasonChange = (e) => {
    const nextSeason = e.target.value;
    setAuditSeason(nextSeason);
    setSelectedGw('all');
    fetchAuditData(false, nextSeason);
  };

  if (loading) return <AuditSkeleton />;

  if (error) {
    return (
      <div className="bg-background-primary border border-border rounded p-8 max-w-xl mx-auto my-12 flex flex-col items-center gap-3 text-center">
        <AlertCircle className="w-5 h-5 text-status-error" strokeWidth={1.5} />
        <h3 className="text-lg font-semibold text-text-primary">Doğrulama verisi yüklenemedi</h3>
        <p className="text-sm text-text-secondary">Bağlantıyı kontrol edip tekrar deneyin.</p>
        <button
          type="button"
          onClick={() => fetchAuditData(false, auditSeason)}
          className="h-9 px-4 rounded bg-primary hover:bg-primary-hover text-white text-sm font-medium transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus focus-visible:ring-offset-2"
        >
          Tekrar dene
        </button>
      </div>
    );
  }

  if (!auditData || !auditData.matches || auditData.matches.length === 0) {
    return (
      <div className="bg-background-primary border border-border rounded p-8 max-w-xl mx-auto my-12 flex flex-col items-center gap-2 text-center">
        <h3 className="text-lg font-semibold text-text-primary">Doğrulama verisi bulunamadı</h3>
        <p className="text-sm text-text-secondary">
          {formatSeasonLabel(auditSeason, '/')} sezonu için henüz denetlenmiş maç kaydı yok.
        </p>
      </div>
    );
  }

  const { overall, gameweeks, matches } = auditData;

  // Filter matches
  const gwMatches = selectedGw === 'all'
    ? matches
    : matches.filter(m => Number(m.gameweek) === Number(selectedGw));

  let filteredMatches = gwMatches;
  if (marketFilter === 'edge') {
    filteredMatches = filteredMatches.filter(m => m.highest_edge_side && m.edge_pct >= 3.0);
  } else if (marketFilter === 'value_edge_5') {
    filteredMatches = filteredMatches.filter(m => m.is_value_bet || (m.edge_pct && m.edge_pct >= 5.0));
  } else if (marketFilter === 'high_conf') {
    filteredMatches = filteredMatches.filter(m => m.confidence_tier === 'high');
  } else if (marketFilter === 'balanced') {
    filteredMatches = filteredMatches.filter(m => m.is_balanced);
  } else if (marketFilter === '1x2_hits') {
    filteredMatches = filteredMatches.filter(m => m.hit_1x2);
  } else if (marketFilter === '1x2_misses') {
    filteredMatches = filteredMatches.filter(m => !m.hit_1x2);
  }

  const currentGwSummary = selectedGw === 'all'
    ? null
    : gameweeks.find(g => Number(g.gameweek) === Number(selectedGw));

  const isLive = auditSeason === '2026_27';

  return (
    <div className="flex flex-col gap-6 pb-12">

      {/* 1. Header */}
      <header className="bg-background-primary border border-border rounded p-5 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex flex-col gap-1 min-w-0">
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <StatusDot tone="success" />
            <span>{isLive ? 'Sıfır sızıntı (out-of-sample)' : 'Tarihsel doğrulama (backtest)'}</span>
            <span className="text-text-muted">·</span>
            <span className="tabular-nums">{formatSeasonLabel(auditSeason, '/')} sezonu</span>
          </div>
          <h2 className="text-2xl font-semibold text-text-primary">Model doğrulama ve performans denetimi</h2>
          <p className="text-sm text-text-secondary max-w-3xl">
            Maç öncesi üretilen tahminlerin gerçekleşen sonuçlar ve kapanış oranlarıyla karşılaştırması.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="relative">
            <label htmlFor="audit-season" className="sr-only">Sezon seç</label>
            <select
              id="audit-season"
              value={auditSeason}
              onChange={handleSeasonChange}
              className="appearance-none h-10 pl-3 pr-9 rounded border border-border bg-background-primary text-sm font-medium text-text-primary cursor-pointer transition-colors duration-150 ease-out hover:border-card-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
            >
              {SEASON_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" strokeWidth={1.5} />
          </div>

          <button
            type="button"
            onClick={() => fetchAuditData(true, auditSeason)}
            disabled={refreshing}
            className="h-10 px-3 rounded border border-border bg-background-primary text-sm font-medium text-text-primary inline-flex items-center gap-2 transition-colors duration-150 ease-out hover:border-card-border-hover disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
          >
            <RotateCw className={`w-4 h-4 ${refreshing ? 'animate-spin motion-reduce:animate-none' : ''}`} strokeWidth={1.5} />
            <span>{refreshing ? 'Hesaplanıyor' : 'Analizi yenile'}</span>
          </button>
        </div>
      </header>

      {/* 2. KPI Cards */}
      <section aria-label="Performans özeti" className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          label="Net favoriler"
          meta={overall.high_confidence_count != null ? `${overall.high_confidence_count} maç` : null}
          value={fmt(overall.high_confidence_hit_rate, '%')}
          footnote="Yüksek güvenli seçimler"
        />
        <KpiCard
          label="Genel 1X2 isabeti"
          meta={`${overall.hits_1x2}/${overall.total_audited_matches}`}
          value={fmt(overall.hit_rate_1x2_pct, '%')}
          footnote={overall.balanced_count != null ? `${overall.balanced_count} dengeli maç dahil` : null}
        />
        <KpiCard
          label="2.5 gol alt/üst"
          meta={`${overall.hits_over_25}/${overall.total_audited_matches}`}
          value={fmt(overall.hit_rate_over_25_pct, '%')}
          footnote="Poisson ve Dixon-Coles"
        />
        <KpiCard
          label="KG var / yok"
          meta={`${overall.hits_btts}/${overall.total_audited_matches}`}
          value={fmt(overall.hit_rate_btts_pct, '%')}
          footnote="Karşılıklı skor isabeti"
        />
        <KpiCard
          className="col-span-2 lg:col-span-1"
          label="Kart / korner MAE"
          meta="Ortalama hata"
          value={fmt(overall.card_mae, '±')}
          secondary={`/ ${fmt(overall.corner_mae, '±')}`}
          footnote="Disiplin ve maç akışı"
        />
      </section>

      {/* 3. Gameweek navigation */}
      <nav aria-label="Hafta seçimi" className="bg-background-primary border border-border rounded p-2 flex items-center gap-1 overflow-x-auto">
        <button
          type="button"
          onClick={() => setSelectedGw('all')}
          aria-pressed={selectedGw === 'all'}
          className={`h-9 px-3 rounded text-sm font-medium shrink-0 transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
            selectedGw === 'all'
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
          }`}
        >
          Tüm sezon <span className="tabular-nums">({overall.total_audited_matches})</span>
        </button>

        {gameweeks.map((g) => {
          const active = Number(selectedGw) === Number(g.gameweek);
          return (
            <button
              key={g.gameweek}
              type="button"
              onClick={() => setSelectedGw(g.gameweek)}
              aria-pressed={active}
              className={`h-9 px-3 rounded text-sm font-medium shrink-0 inline-flex items-center gap-2 transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
                active
                  ? 'bg-primary text-white'
                  : 'text-text-secondary hover:text-text-primary hover:bg-background-tertiary'
              }`}
            >
              <span>Hafta {g.gameweek}</span>
              <span className={`text-xs tabular-nums ${active ? 'text-white/70' : 'text-text-tertiary'}`}>
                %{g.hit_rate_1x2_pct}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Market filters */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="flex items-center gap-2 overflow-x-auto" role="group" aria-label="Maç filtresi">
          <FilterButton active={marketFilter === 'all'} onClick={() => setMarketFilter('all')}>
            Tümü <span className="tabular-nums opacity-70">{gwMatches.length}</span>
          </FilterButton>
          <FilterButton active={marketFilter === 'high_conf'} onClick={() => setMarketFilter('high_conf')}>
            <StatusDot tone="success" /> Net favoriler
          </FilterButton>
          <FilterButton active={marketFilter === 'balanced'} onClick={() => setMarketFilter('balanced')}>
            <StatusDot tone="warning" /> Dengeli maçlar
          </FilterButton>
          <FilterButton active={marketFilter === 'value_edge_5'} onClick={() => setMarketFilter('value_edge_5')}>
            Değer bahisleri <span className="tabular-nums opacity-70">+%5</span>
          </FilterButton>
          <FilterButton active={marketFilter === '1x2_hits'} onClick={() => setMarketFilter('1x2_hits')}>
            1X2 tuttu
          </FilterButton>
          <FilterButton active={marketFilter === '1x2_misses'} onClick={() => setMarketFilter('1x2_misses')}>
            <StatusDot tone="error" /> 1X2 yanıldı
          </FilterButton>
        </div>

        {currentGwSummary && (
          <p className="text-sm text-text-secondary tabular-nums shrink-0">
            Hafta {currentGwSummary.gameweek}:{' '}
            1X2 <span className="font-medium text-text-primary">%{currentGwSummary.hit_rate_1x2_pct}</span>
            <span className="text-text-muted"> · </span>
            2.5 üst <span className="font-medium text-text-primary">%{currentGwSummary.hit_rate_over_25_pct}</span>
            <span className="text-text-muted"> · </span>
            Korner MAE <span className="font-medium text-text-primary">±{currentGwSummary.corner_mae}</span>
          </p>
        )}
      </div>

      {/* 4. Match audit list */}
      <section aria-label="Maç denetimleri" className="flex flex-col gap-3">
        {filteredMatches.length === 0 ? (
          <div className="bg-background-primary border border-border rounded p-8 flex flex-col items-center gap-3 text-center">
            <p className="text-sm text-text-secondary">Seçilen filtrelere uygun maç yok.</p>
            <button
              type="button"
              onClick={() => setMarketFilter('all')}
              className="h-9 px-3 rounded border border-border text-sm font-medium text-text-primary hover:border-card-border-hover transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
            >
              Filtreyi temizle
            </button>
          </div>
        ) : (
          filteredMatches.map((m) => (
            <AuditMatchCard key={m.match_id} match={m} onSelectMatch={onSelectMatch} />
          ))
        )}
      </section>

    </div>
  );
}
