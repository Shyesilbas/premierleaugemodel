import AuditMatchCard from './model-audit/AuditMatchCard';
import { formatSeasonLabel } from '../utils/dateFormatters';
import React, { useState, useEffect } from 'react';
import { getModelAudit } from '../services/auditService';
import { useCompetition } from '../context/CompetitionContext';
import { ChevronDown, RotateCw, SearchX, ClipboardList } from 'lucide-react';
import Skeleton from './common/Skeleton';
import InlineError from './common/InlineError';
import EmptyState from './common/EmptyState';

const SEASON_OPTIONS = [
  { value: '2026_27', label: '2026/27 · Canlı' },
  { value: '2025_26', label: '2025/26 · Tüm sezon' },
  { value: '2024_25', label: '2024/25 · Tüm sezon' },
];

// The first gameweek that still has unplayed matches; a finished season falls back to its last week.
const pickCurrentGameweek = (gameweeks = []) => {
  if (gameweeks.length === 0) return 'all';
  const open = gameweeks.find(g => (g.upcoming_count || 0) > 0);
  return (open || gameweeks[gameweeks.length - 1]).gameweek;
};

const fmt = (value, prefix = '') => (value === null || value === undefined ? '—' : `${prefix}${value}`);

function KpiCell({ label, meta, value, secondary }) {
  return (
    <div className="bg-background-primary p-3 sm:p-4 flex flex-col gap-1 min-w-0">
      <span className="text-xs text-text-secondary truncate">{label}</span>
      <div className="text-xl font-semibold text-text-primary tabular-nums">
        {value}
        {secondary && <span className="ml-1 text-sm font-normal text-text-tertiary">{secondary}</span>}
      </div>
      {meta && <span className="text-xs text-text-tertiary tabular-nums truncate">{meta}</span>}
    </div>
  );
}

function FilterButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`h-8 px-3 rounded text-sm font-medium inline-flex items-center gap-1.5 shrink-0 border transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
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
    <div className="flex flex-col gap-4 pb-12" aria-busy="true" aria-label="Yükleniyor">
      <Skeleton className="h-16 w-full max-w-xl" />
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}

export default function ModelAuditTab({ selectedSeason = '2026_27', onSelectMatch }) {
  const { competitionKey, hasRichData } = useCompetition();
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
  }, [selectedSeason, competitionKey]);

  const fetchAuditData = (force = false, targetSeason = auditSeason) => {
    if (force) setRefreshing(true);
    else setLoading(true);
    setError(false);

    getModelAudit(targetSeason, force, competitionKey)
      .then(data => {
        setAuditData(data);
        if (!force) setSelectedGw(pickCurrentGameweek(data?.gameweeks));
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
    fetchAuditData(false, nextSeason);
  };

  if (loading) return <AuditSkeleton />;

  if (error) {
    return (
      <InlineError
        message="Doğrulama verisi yüklenemedi. Bağlantıyı kontrol edip tekrar deneyin."
        onRetry={() => fetchAuditData(false, auditSeason)}
      />
    );
  }

  if (!auditData || !auditData.matches || auditData.matches.length === 0) {
    return (
      <EmptyState icon={ClipboardList}>
        {formatSeasonLabel(auditSeason, '/')} sezonu için henüz denetlenmiş maç kaydı yok.
      </EmptyState>
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
    filteredMatches = filteredMatches.filter(m => m.hit_1x2 === true);
  } else if (marketFilter === '1x2_misses') {
    filteredMatches = filteredMatches.filter(m => m.hit_1x2 === false);
  } else if (marketFilter === 'upcoming') {
    filteredMatches = filteredMatches.filter(m => m.is_played === false);
  }

  const currentGwSummary = selectedGw === 'all'
    ? null
    : gameweeks.find(g => Number(g.gameweek) === Number(selectedGw));

  const isLive = auditSeason === '2026_27';

  const playedInGw = gwMatches.filter(m => m.is_played !== false).length;
  const filters = [
    { id: 'all', label: 'Tümü', count: gwMatches.length },
    { id: 'high_conf', label: 'Net favoriler' },
    { id: 'balanced', label: 'Dengeli' },
    ...(hasRichData ? [{ id: 'value_edge_5', label: 'Değerli oran' }] : []),
    { id: 'upcoming', label: 'Oynanmamış', count: gwMatches.length - playedInGw },
    { id: '1x2_hits', label: 'Tuttu' },
    { id: '1x2_misses', label: 'Yanıldı' },
  ];

  const selectClass = 'appearance-none h-10 pl-3 pr-9 rounded border border-border bg-background-primary text-sm font-medium text-text-primary cursor-pointer transition-colors duration-150 ease-out hover:border-card-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus';

  return (
    <div className="flex flex-col gap-6 pb-12">

      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-border">
        <div className="flex flex-col gap-1 min-w-0">
          <h2 className="text-2xl font-semibold text-text-primary">Model doğrulama</h2>
          <p className="text-sm text-text-secondary max-w-2xl">
            Maç öncesi tahminlerin gerçek sonuçlar ve kapanış oranlarıyla karşılaştırması.{' '}
            {auditData?.method === 'walk_forward'
              ? 'Her maç, yalnızca kendisinden önce oynanmış sezonlarla eğitilen modelle tahmin edilir (walk-forward, sızıntısız).'
              : isLive ? 'Canlı sezon, sızıntısız (out-of-sample).' : 'Geçmiş sezon, backtest.'}
          </p>
        </div>

        <div className="flex items-end gap-2 shrink-0">
          <div className="flex flex-col gap-1">
            <label htmlFor="audit-season" className="text-xs text-text-secondary">Sezon</label>
            <div className="relative">
              <select id="audit-season" value={auditSeason} onChange={handleSeasonChange} className={selectClass}>
                {SEASON_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="audit-gw" className="text-xs text-text-secondary">Hafta</label>
            <div className="relative">
              <select
                id="audit-gw"
                value={selectedGw}
                onChange={e => setSelectedGw(e.target.value)}
                className={selectClass}
              >
                <option value="all">Tüm sezon ({matches.length})</option>
                {gameweeks.map(g => (
                  <option key={g.gameweek} value={g.gameweek}>
                    Hafta {g.gameweek}{g.hit_rate_1x2_pct != null ? ` · %${g.hit_rate_1x2_pct}` : ` · ${g.upcoming_count} bekliyor`}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
            </div>
          </div>

          <button
            type="button"
            onClick={() => fetchAuditData(true, auditSeason)}
            disabled={refreshing}
            aria-label="Analizi yenile"
            className="h-10 px-3 rounded border border-border bg-background-primary text-sm font-medium text-text-primary inline-flex items-center gap-2 transition-colors duration-150 ease-out hover:border-card-border-hover disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
          >
            <RotateCw className={`w-4 h-4 ${refreshing ? 'animate-spin motion-reduce:animate-none' : ''}`} strokeWidth={1.5} />
            <span className="hidden sm:inline">{refreshing ? 'Hesaplanıyor' : 'Yenile'}</span>
          </button>
        </div>
      </header>

      <section aria-label="Performans özeti" className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-px bg-border border border-border rounded overflow-hidden">
        <KpiCell
          label="Net favoriler"
          value={fmt(overall.high_confidence_hit_rate, '%')}
          meta={overall.high_confidence_count != null ? `${overall.high_confidence_count} maç` : null}
        />
        <KpiCell
          label="1X2 isabeti"
          value={fmt(overall.hit_rate_1x2_pct, '%')}
          meta={`${overall.hits_1x2}/${overall.total_audited_matches} maç`}
        />
        <KpiCell
          label="2.5 alt / üst"
          value={fmt(overall.hit_rate_over_25_pct, '%')}
          meta={`${overall.hits_over_25}/${overall.total_audited_matches} maç`}
        />
        <KpiCell
          label="Karşılıklı gol"
          value={fmt(overall.hit_rate_btts_pct, '%')}
          meta={`${overall.hits_btts}/${overall.total_audited_matches} maç`}
        />
        <KpiCell
          label="Kart / korner hatası"
          value={fmt(overall.card_mae, '±')}
          secondary={`/ ${fmt(overall.corner_mae, '±')}`}
          meta="Ortalama sapma"
        />
      </section>

      {auditData?.benchmark?.scores && (
        <section aria-label="Karşılaştırma" className="flex flex-col gap-2">
          <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
            <h3 className="text-sm font-semibold text-text-primary">Log-loss karşılaştırması</h3>
            <p className="text-xs text-text-secondary">
              {auditData.benchmark.role === 'monitor' ? 'Canlı izleme: karar için kullanılmaz' : auditData.benchmark.role === 'hold_out' ? 'Sınama sezonu' : 'Geçmiş sezon'}
              {auditData.benchmark.serving === 'elo_baseline' ? '. Gösterilen tahmin Elo temelli referanstır' : ''}. Düşük değer daha iyi.
            </p>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border rounded overflow-hidden">
            <KpiCell label="Model" value={fmt(auditData.benchmark.scores.model?.log_loss)} meta={`RPS ${fmt(auditData.benchmark.scores.model?.rps)}`} />
            <KpiCell label="Taban oran" value={fmt(auditData.benchmark.scores.base_rate?.log_loss)} meta="Ev / beraberlik / deplasman sıklığı" />
            <KpiCell label="Elo referansı" value={fmt(auditData.benchmark.scores.elo?.log_loss)} meta="Elo farkı ve ev sahibi avantajı" />
            <KpiCell
              label="Piyasa"
              value={fmt(auditData.benchmark.scores.market?.log_loss)}
              meta={auditData.benchmark.scores.market ? `${auditData.benchmark.scores.market.n} maç, kapanış oranı` : 'Bu sezon için oran yok'}
            />
          </div>
        </section>
      )}

      <div className="flex flex-col gap-3 pb-6 border-b border-border">
        <div className="flex items-center gap-2 overflow-x-auto" role="group" aria-label="Maç filtresi">
          {filters.map(f => (
            <FilterButton key={f.id} active={marketFilter === f.id} onClick={() => setMarketFilter(f.id)}>
              {f.label}
              {f.count !== undefined && <span className="tabular-nums opacity-70">{f.count}</span>}
            </FilterButton>
          ))}
        </div>

        {currentGwSummary && currentGwSummary.matches_count > 0 && (
          <p className="text-sm text-text-secondary tabular-nums">
            Hafta {currentGwSummary.gameweek}:{' '}
            1X2 <span className="font-medium text-text-primary">%{currentGwSummary.hit_rate_1x2_pct}</span>
            <span className="text-text-muted"> · </span>
            2.5 üst <span className="font-medium text-text-primary">%{currentGwSummary.hit_rate_over_25_pct}</span>
            <span className="text-text-muted"> · </span>
            Korner hatası <span className="font-medium text-text-primary">±{currentGwSummary.corner_mae}</span>
          </p>
        )}
      </div>

      <section aria-label="Maç denetimleri" className="flex flex-col gap-2">
        {filteredMatches.length === 0 ? (
          <EmptyState
            icon={SearchX}
            action={
              <button
                type="button"
                onClick={() => setMarketFilter('all')}
                className="h-9 px-3 rounded border border-border text-sm font-medium text-text-primary hover:border-card-border-hover transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
              >
                Filtreyi temizle
              </button>
            }
          >
            Seçilen filtrelere uygun maç yok.
          </EmptyState>
        ) : (
          filteredMatches.map((m) => (
            <AuditMatchCard key={m.match_id} match={m} onSelectMatch={onSelectMatch} />
          ))
        )}
      </section>

    </div>
  );
}
