import React, { useEffect, useState } from 'react';
import { ChevronDown, ClipboardList, Info, RotateCw, SearchX, ShieldCheck } from 'lucide-react';
import { useCompetition } from '../context/competitionState';
import { getModelAudit } from '../services/auditService';
import { formatSeasonLabel } from '../utils/dateFormatters';
import { Badge } from './common/Badge';
import { Button } from './common/Button';
import { Card } from './common/Card';
import EmptyState from './common/EmptyState';
import InlineError from './common/InlineError';
import { Select } from './common/Select';
import Skeleton from './common/Skeleton';
import AuditBacktestCalibration from './model-audit/AuditBacktestCalibration';
import AuditBaselinesSection from './model-audit/AuditBaselinesSection';
import AuditChartsSection from './model-audit/AuditChartsSection';
import AuditMatchCard from './model-audit/AuditMatchCard';

const SEASON_OPTIONS = [
  { value: '2026_27', label: '2026/27 · Canlı' },
  { value: '2025_26', label: '2025/26 · Tüm sezon' },
  { value: '2024_25', label: '2024/25 · Tüm sezon' },
  { value: '2023_24', label: '2023/24 · Tüm sezon' },
  { value: '2022_23', label: '2022/23 · Tüm sezon' },
];

const SUB_TABS = [
  { id: 'predictions', label: 'Haftalık Tahminler' },
  { id: 'baselines', label: 'Sürüm ve Baseline' },
  { id: 'calibration', label: 'Kalibrasyon ve Trend' },
];

const pickCurrentGameweek = (gameweeks = []) => {
  if (gameweeks.length === 0) return 'all';
  const open = gameweeks.find((g) => (g.upcoming_count || 0) > 0);
  return String((open || gameweeks[gameweeks.length - 1]).gameweek);
};

const fmt = (value, prefix = '') => (value === null || value === undefined ? '—' : `${prefix}${value}`);

function KpiCard({ label, value, meta, badge }) {
  return (
    <Card padding="sm" className="flex flex-col justify-between gap-1.5 min-w-0">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-text-secondary truncate">{label}</span>
        {badge}
      </div>
      <div className="text-2xl font-semibold text-text-primary tabular-nums">{value}</div>
      {meta && <span className="text-xs text-text-tertiary tabular-nums">{meta}</span>}
    </Card>
  );
}

function AuditSkeleton() {
  return (
    <div className="space-y-5 pb-12" aria-busy="true" aria-label="Model takibi verileri yükleniyor">
      <Skeleton className="h-20 w-full" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
      <Skeleton className="h-10 w-80" />
      {Array.from({ length: 5 }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}

export default function ModelAuditTab({ selectedSeason = '2026_27', onSelectMatch }) {
  const { competitionKey, hasRichData } = useCompetition();
  const [seasonOverride, setSeasonOverride] = useState({ prop: selectedSeason, value: selectedSeason });
  const [auditResult, setAuditResult] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('predictions');
  const [showGuide, setShowGuide] = useState(false);
  const [gwOverride, setGwOverride] = useState({ key: '', value: 'all' });
  const [marketFilter, setMarketFilter] = useState('all');
  const [reloadState, setReloadState] = useState({ seq: 0, force: false });

  const auditSeason = seasonOverride.prop === selectedSeason
    ? (seasonOverride.value || '2026_27')
    : (selectedSeason || '2026_27');
  const requestKey = `${auditSeason}:${competitionKey}:${reloadState.seq}`;

  useEffect(() => {
    let cancelled = false;
    getModelAudit(auditSeason, reloadState.force, competitionKey)
      .then((data) => {
        if (!cancelled) {
          setAuditResult({ key: requestKey, data, error: false });
        }
      })
      .catch((err) => {
        console.error('Error fetching model audit:', err);
        if (!cancelled) {
          setAuditResult({ key: requestKey, data: null, error: true });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [auditSeason, competitionKey, reloadState.force, requestKey]);

  const settled = auditResult?.key === requestKey;
  const refreshing = Boolean(!settled && reloadState.force);
  const loading = !auditResult || (!settled && !reloadState.force);
  const error = settled && auditResult.error;
  const auditData = settled ? auditResult.data : auditResult?.data || null;
  const selectedGw = gwOverride.key === requestKey
    ? gwOverride.value
    : pickCurrentGameweek(auditData?.gameweeks);

  const triggerReload = (force = false) => {
    setReloadState((prev) => ({ seq: prev.seq + 1, force }));
  };

  const handleSeasonChange = (e) => {
    const nextSeason = e.target.value;
    setSeasonOverride({ prop: selectedSeason, value: nextSeason });
    setReloadState((prev) => ({ seq: prev.seq + 1, force: false }));
  };

  if (loading) return <AuditSkeleton />;

  if (error) {
    return (
      <InlineError
        message="Model takibi verisi yüklenemedi. Bağlantıyı kontrol edip tekrar deneyin."
        onRetry={() => triggerReload(false)}
      />
    );
  }

  if (!auditData || !auditData.matches || auditData.matches.length === 0) {
    return (
      <EmptyState icon={ClipboardList}>
        {formatSeasonLabel(auditSeason, '/')} sezonu için henüz kayıtlı model tahmini yok.
      </EmptyState>
    );
  }

  const {
    overall = {},
    gameweeks = [],
    matches = [],
    benchmark = {},
    calibration_bands: calibrationBands = [],
    rolling_accuracy: rollingAccuracy = [],
    prospective_scorecard: prospectiveScorecard = {},
    backtest_calibration: backtestCalibration = {},
  } = auditData;

  const isLive = auditSeason === '2026_27';
  const gwMatches = selectedGw === 'all'
    ? matches
    : matches.filter((m) => Number(m.gameweek) === Number(selectedGw));

  let filteredMatches = gwMatches;
  if (marketFilter === 'prospective') {
    filteredMatches = filteredMatches.filter((m) => m.evaluation_type === 'prospective');
  } else if (marketFilter === 'backfill') {
    filteredMatches = filteredMatches.filter((m) => m.evaluation_type === 'in_sample_backfill');
  } else if (marketFilter === 'value_edge_5') {
    filteredMatches = filteredMatches.filter((m) => m.is_value_bet || (m.edge_pct && m.edge_pct >= 5.0));
  } else if (marketFilter === 'high_conf') {
    filteredMatches = filteredMatches.filter((m) => m.confidence_tier === 'high');
  } else if (marketFilter === '1x2_hits') {
    filteredMatches = filteredMatches.filter((m) => m.hit_1x2 === true);
  } else if (marketFilter === '1x2_misses') {
    filteredMatches = filteredMatches.filter((m) => m.hit_1x2 === false);
  } else if (marketFilter === 'upcoming') {
    filteredMatches = filteredMatches.filter((m) => m.is_played === false);
  }

  const playedInGw = gwMatches.filter((m) => m.is_played !== false).length;
  const prospectiveInGw = gwMatches.filter((m) => m.evaluation_type === 'prospective').length;
  const currentGwSummary = selectedGw === 'all'
    ? null
    : gameweeks.find((g) => Number(g.gameweek) === Number(selectedGw));

  const homeDiffPp = overall.hit_rate_1x2_pct != null && overall.home_baseline_accuracy != null
    ? Number((overall.hit_rate_1x2_pct - overall.home_baseline_accuracy).toFixed(1))
    : null;

  const filters = [
    { id: 'all', label: 'Tümü', count: gwMatches.length },
    ...(prospectiveInGw > 0 ? [{ id: 'prospective', label: 'Canlı kayıt', count: prospectiveInGw }] : []),
    { id: 'high_conf', label: 'Net favoriler' },
    ...(hasRichData ? [{ id: 'value_edge_5', label: 'Değerli oran' }] : []),
    { id: 'upcoming', label: 'Oynanmamış', count: gwMatches.length - playedInGw },
    { id: '1x2_hits', label: 'Tuttu' },
    { id: '1x2_misses', label: 'Yanıldı' },
    { id: 'backfill', label: 'Geriye dönük' },
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Header + Controls */}
      <header className="flex flex-col gap-4 border-b border-border pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <ShieldCheck className="h-5 w-5 text-text-secondary shrink-0" strokeWidth={1.5} aria-hidden="true" />
            <h1 className="text-2xl font-semibold text-text-primary tracking-tight">Model takibi</h1>
            <Badge variant={isLive ? 'success' : 'neutral'} dot={isLive}>
              {isLive ? 'Canlı izleme (kilitli sezon)' : 'Tarihsel denetim'}
            </Badge>
          </div>
          <p className="text-sm text-text-secondary max-w-2xl">
            Maç öncesi dondurulan tahminlerin gerçek sonuçlar, saf Elo referansı ve kapanış oranlarıyla sızıntısız doğrulama günlüğü.
          </p>
          <button
            type="button"
            onClick={() => setShowGuide((prev) => !prev)}
            aria-expanded={showGuide}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-text-primary transition-colors cursor-pointer pt-0.5"
          >
            <Info className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Bu sayfa nasıl çalışır?</span>
            <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-150 ${showGuide ? 'rotate-180' : ''}`} aria-hidden="true" />
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <div className="w-44">
            <Select
              id="audit-season"
              aria-label="Sezon"
              value={auditSeason}
              onChange={handleSeasonChange}
              options={SEASON_OPTIONS}
            />
          </div>
          <Button
            variant="secondary"
            size="md"
            isLoading={refreshing}
            leftIcon={<RotateCw className="h-4 w-4" strokeWidth={1.5} aria-hidden="true" />}
            onClick={() => triggerReload(true)}
          >
            {refreshing ? 'Hesaplanıyor' : 'Yenile'}
          </Button>
        </div>
      </header>

      {/* Expandable 3-column Methodology Guide */}
      {showGuide && (
        <Card padding="md" className="bg-background-secondary">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3 text-xs leading-relaxed text-text-secondary">
            <div>
              <h3 className="font-semibold text-text-primary mb-1">1. Sızıntısız Canlı Kayıt</h3>
              <p>
                Maç başlamadan önce üretilen 1X2 ve gol olasılıkları tek yönlü günlüğe (1x2_forecast_log.jsonl) artifact SHA256 kimliğiyle yazılır; sonradan geriye dönük tahminlerden ayrı tutulur.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-text-primary mb-1">2. Taban ve Piyasa Testi</h3>
              <p>
                Yalnızca isabet yüzdesi yanıltıcıdır. Aktif model; Taban Oran, Saf Elo Referansı ve Bet365/Pinnacle kapanış olasılıklarına karşı Log Loss, Brier ve RPS ile %95 bootstrap aralığında sınanır.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-text-primary mb-1">3. Kalibrasyon ve Walk-Forward</h3>
              <p>
                Güven bantlarının (%40-%70+) gerçekleşme uyumu hem canlı sezonda hem 2023-2026 dış test sezonlarında takip edilir; 2026/27 verisi hiçbir eğitim/ayar kararına sokulmaz.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* 4-Card Season KPI Strip */}
      <section aria-label="Model takip özeti" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="1X2 Doğruluğu"
          value={fmt(overall.hit_rate_1x2_pct, '%')}
          meta={`${overall.hits_1x2 ?? 0}/${overall.total_audited_matches ?? 0} maç · 2.5 Üst %${overall.hit_rate_over_25_pct ?? 0}`}
        />

        <KpiCard
          label="Model Farkı vs Ev Sahibi"
          value={homeDiffPp != null ? `${homeDiffPp > 0 ? '+' : ''}${homeDiffPp} yp` : '—'}
          meta={`Ev sahibi kazanma: %${overall.home_baseline_accuracy ?? '—'} · Net fav: %${overall.high_confidence_hit_rate ?? '—'}`}
          badge={homeDiffPp != null && (
            <Badge variant={homeDiffPp >= 0 ? 'success' : 'error'} size="sm">
              {homeDiffPp >= 0 ? 'Üzerinde' : 'Altında'}
            </Badge>
          )}
        />

        <KpiCard
          label="Kayıt Kapsamı"
          value={`${overall.total_audited_matches ?? 0} maç`}
          meta={`${overall.prospective_matches_count ?? 0} canlı · ${overall.in_sample_backfill_matches_count ?? 0} geriye dönük · ${overall.upcoming_predicted_matches ?? 0} bekleyen`}
        />

        <KpiCard
          label="Olasılık Kalitesi"
          value={overall.log_loss != null ? Number(overall.log_loss).toFixed(4) : '—'}
          meta={`Log Loss · Brier ${overall.brier ?? '—'} · RPS ${overall.rps ?? '—'}`}
        />
      </section>

      {/* 3 Sub-Tabs matching PaperTrading structure */}
      <div className="flex flex-col gap-3 border-b border-border pb-3 sm:flex-row sm:items-center sm:justify-between">
        <div role="tablist" aria-label="Model takip sekmeleri" className="flex flex-wrap items-center gap-1.5">
          {SUB_TABS.map((tab) => {
            const active = activeSubTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setActiveSubTab(tab.id)}
                className={`h-9 rounded border px-3.5 text-sm font-medium transition-colors cursor-pointer ${
                  active
                    ? 'border-primary bg-primary text-white'
                    : 'border-border bg-background-primary text-text-secondary hover:text-text-primary hover:border-card-border-hover'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeSubTab === 'predictions' && (
          <div className="w-full sm:w-56">
            <Select
              id="audit-gw"
              aria-label="Hafta seç"
              value={String(selectedGw)}
              onChange={(e) => setGwOverride({ key: requestKey, value: e.target.value })}
              options={[
                { value: 'all', label: `Tüm sezon (${matches.length})` },
                ...gameweeks.map((g) => ({
                  value: String(g.gameweek),
                  label: `Hafta ${g.gameweek}${g.hit_rate_1x2_pct != null ? ` · %${g.hit_rate_1x2_pct}` : ` · ${g.upcoming_count} bekliyor`}`,
                })),
              ]}
            />
          </div>
        )}
      </div>

      {/* Tab 1: Weekly Predictions & Scorecard List */}
      {activeSubTab === 'predictions' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1" role="group" aria-label="Maç filtresi">
              {filters.map((f) => {
                const active = marketFilter === f.id;
                return (
                  <button
                    key={f.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => setMarketFilter(f.id)}
                    className={`h-8 shrink-0 rounded border px-3 text-xs font-medium inline-flex items-center gap-1.5 transition-colors cursor-pointer ${
                      active
                        ? 'border-primary bg-primary text-white'
                        : 'border-border bg-background-primary text-text-secondary hover:text-text-primary hover:border-card-border-hover'
                    }`}
                  >
                    <span>{f.label}</span>
                    {f.count !== undefined && <span className="tabular-nums opacity-75">{f.count}</span>}
                  </button>
                );
              })}
            </div>

            {currentGwSummary && currentGwSummary.matches_count > 0 && (
              <p className="text-xs text-text-secondary tabular-nums">
                Hafta {currentGwSummary.gameweek}: 1X2 <strong className="text-text-primary">%{currentGwSummary.hit_rate_1x2_pct}</strong>
                <span className="mx-1.5 text-text-muted">·</span>
                2.5 Üst <strong className="text-text-primary">%{currentGwSummary.hit_rate_over_25_pct}</strong>
                <span className="mx-1.5 text-text-muted">·</span>
                Korner hatası <strong className="text-text-primary">±{currentGwSummary.corner_mae}</strong>
              </p>
            )}
          </div>

          <section aria-label="Maç denetimleri" className="flex flex-col gap-2">
            {filteredMatches.length === 0 ? (
              <EmptyState
                icon={SearchX}
                action={
                  <Button variant="secondary" size="sm" onClick={() => setMarketFilter('all')}>
                    Filtreyi temizle
                  </Button>
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
      )}

      {/* Tab 2: Versions & Baselines */}
      {activeSubTab === 'baselines' && (
        <AuditBaselinesSection
          benchmark={benchmark}
          overall={overall}
          prospectiveScorecard={prospectiveScorecard}
          season={auditSeason}
        />
      )}

      {/* Tab 3: Calibration & Walk-Forward Trend */}
      {activeSubTab === 'calibration' && (
        <div className="space-y-6">
          <AuditChartsSection rollingAccuracy={rollingAccuracy} calibrationBands={calibrationBands} />
          <AuditBacktestCalibration backtestCalibration={backtestCalibration} />
        </div>
      )}
    </div>
  );
}
