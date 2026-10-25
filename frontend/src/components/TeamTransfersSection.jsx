import { useState, useEffect, useMemo } from 'react';
import { ChevronDown, Search, ArrowLeftRight } from 'lucide-react';
import { getTeamTransfers } from '../services/teamService';
import { formatSeasonLabel } from '../utils/dateFormatters';
import Skeleton from './common/Skeleton';
import InlineError from './common/InlineError';
import EmptyState from './common/EmptyState';

const TRANSFER_TYPES = [
  { value: 'all', label: 'Tüm türler' },
  { value: 'Bonservis', label: 'Bonservisli' },
  { value: 'Kiralık', label: 'Kiralık' },
  { value: 'Kiradan Geri Dönüş', label: 'Kiradan dönüş' },
  { value: 'Serbest', label: 'Serbest / bedelsiz' },
  { value: 'Altyapı', label: 'Altyapı terfisi' },
];

const FIELD_CLASS = 'h-10 rounded border border-border bg-background-primary text-sm text-text-primary transition-colors duration-150 ease-out hover:border-card-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus';

function StatusDot({ tone }) {
  const tones = { success: 'bg-status-success', muted: 'bg-text-muted' };
  return <span aria-hidden="true" className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${tones[tone]}`} />;
}

function KpiCell({ label, value, meta, tone = 'default' }) {
  return (
    <div className="bg-background-primary p-3 sm:p-4 flex flex-col gap-1 min-w-0">
      <span className="text-xs text-text-secondary truncate">{label}</span>
      <span className={`text-xl font-semibold tabular-nums ${tone === 'positive' ? 'text-status-success' : 'text-text-primary'}`}>
        {value}
      </span>
      <span className="text-xs text-text-tertiary truncate">{meta}</span>
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

function TransfersSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Yükleniyor">
      <Skeleton className="h-20 w-full" />
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

export default function TeamTransfersSection({ teamId, season = '2026_27', onSelectPlayer }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [directionFilter, setDirectionFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (!teamId) return;
    let isMounted = true;
    setLoading(true);
    setError(false);

    const s = season === 'all' ? '2026_27' : season;
    getTeamTransfers(teamId, s)
      .then(resData => {
        if (!isMounted) return;
        setData(resData);
        setLoading(false);
      })
      .catch(err => {
        if (!isMounted) return;
        console.error('Failed to load team transfers:', err);
        setError(true);
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [teamId, season, reloadKey]);

  const summary = data?.summary;

  const allTransfers = useMemo(() => {
    const list = [...(data?.arrivals || []), ...(data?.departures || [])];
    list.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    return list;
  }, [data]);

  const arrivalsCount = allTransfers.filter(t => t.direction === 'in').length;
  const departuresCount = allTransfers.length - arrivalsCount;

  const filteredTransfers = useMemo(() => {
    const query = searchTerm.toLowerCase().trim();
    return allTransfers.filter(item => {
      if (directionFilter !== 'all' && item.direction !== directionFilter) return false;
      if (typeFilter !== 'all' && item.transfer_type !== typeFilter) return false;
      if (query) {
        const inPlayer = (item.player_name || '').toLowerCase().includes(query);
        const inClub = (item.counterpart_club_name || '').toLowerCase().includes(query);
        if (!inPlayer && !inClub) return false;
      }
      return true;
    });
  }, [allTransfers, directionFilter, typeFilter, searchTerm]);

  if (loading) return <TransfersSkeleton />;

  if (error) {
    return <InlineError message="Transfer geçmişi yüklenemedi." onRetry={() => setReloadKey(k => k + 1)} />;
  }

  const seasonLabel = season && season !== 'all' ? `${formatSeasonLabel(season, '/')} sezonu` : 'Tüm sezonlar';
  const positive = summary && summary.net_balance_eur >= 0;

  return (
    <div className="flex flex-col gap-6">
      {summary && (
        <section
          aria-label="Transfer özeti"
          className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border rounded overflow-hidden"
        >
          <KpiCell label="Harcama" value={summary.total_spent_formatted} meta={`${summary.arrivals_count} gelen oyuncu`} />
          <KpiCell label="Gelir" value={summary.total_income_formatted} meta={`${summary.departures_count} giden oyuncu`} />
          <KpiCell
            label="Net bilanço"
            value={summary.net_balance_formatted}
            meta={positive ? 'Pozitif bakiye' : 'Yatırım ağırlıklı'}
            tone={positive ? 'positive' : 'default'}
          />
          <KpiCell
            label="Toplam hareket"
            value={summary.arrivals_count + summary.departures_count}
            meta={seasonLabel}
          />
        </section>
      )}

      <section aria-label="Transfer listesi" className="flex flex-col gap-3">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-3 pb-4 border-b border-border">
          <div className="flex items-center gap-2 overflow-x-auto" role="group" aria-label="Yön filtresi">
            <FilterButton active={directionFilter === 'all'} onClick={() => setDirectionFilter('all')}>
              Tümü <span className="tabular-nums opacity-70">{allTransfers.length}</span>
            </FilterButton>
            <FilterButton active={directionFilter === 'in'} onClick={() => setDirectionFilter('in')}>
              Gelenler <span className="tabular-nums opacity-70">{arrivalsCount}</span>
            </FilterButton>
            <FilterButton active={directionFilter === 'out'} onClick={() => setDirectionFilter('out')}>
              Gidenler <span className="tabular-nums opacity-70">{departuresCount}</span>
            </FilterButton>
          </div>

          <div className="flex items-end gap-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="transfer-type" className="text-xs text-text-secondary">Transfer türü</label>
              <div className="relative">
                <select
                  id="transfer-type"
                  value={typeFilter}
                  onChange={e => setTypeFilter(e.target.value)}
                  className={`${FIELD_CLASS} appearance-none pl-3 pr-9 cursor-pointer`}
                >
                  {TRANSFER_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label htmlFor="transfer-search" className="text-xs text-text-secondary">Ara</label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
                <input
                  id="transfer-search"
                  type="text"
                  placeholder="Oyuncu veya kulüp"
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className={`${FIELD_CLASS} w-44 sm:w-56 pl-9 pr-3 placeholder:text-text-tertiary`}
                />
              </div>
            </div>
          </div>
        </div>

        {filteredTransfers.length === 0 ? (
          <EmptyState icon={ArrowLeftRight}>Seçilen filtrelere uygun transfer kaydı yok.</EmptyState>
        ) : (
          <div className="overflow-x-auto bg-background-primary border border-border rounded">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="bg-background-tertiary border-b border-border text-text-secondary">
                  <th scope="col" className="py-2 px-3 font-medium">Tarih</th>
                  <th scope="col" className="py-2 px-3 font-medium border-l border-border">Oyuncu</th>
                  <th scope="col" className="py-2 px-3 font-medium border-l border-border">Yön ve kulüp</th>
                  <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Piyasa değeri</th>
                  <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Bonservis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {filteredTransfers.map((item, idx) => {
                  const isArrival = item.direction === 'in';
                  return (
                    <tr key={item.id || idx} className="transition-colors duration-150 ease-out hover:bg-background-tertiary">
                      <td className="py-3 px-3 whitespace-nowrap align-middle">
                        <span className="block text-text-primary tabular-nums">{item.date_formatted}</span>
                        <span className="block text-xs text-text-tertiary tabular-nums">{item.season}</span>
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap align-middle border-l border-border-light">
                        <div className="flex items-center gap-2">
                          <div className="min-w-0">
                            <button
                              type="button"
                              onClick={() => onSelectPlayer?.({
                                id: item.player_id,
                                tm_id: item.player_id,
                                name: item.player_name,
                              })}
                              title={`${item.player_name} piyasa değeri geçmişi`}
                              className="block max-w-48 truncate text-left font-medium text-text-primary hover:underline cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus rounded-sm"
                            >
                              {item.player_name}
                            </button>
                            {item.age && <span className="block text-xs text-text-tertiary tabular-nums">{item.age} yaş</span>}
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap align-middle border-l border-border-light">
                        <span className="flex items-center gap-1.5">
                          <StatusDot tone={isArrival ? 'success' : 'muted'} />
                          <span className={`text-sm ${isArrival ? 'text-status-success font-medium' : 'text-text-secondary'}`}>
                            {isArrival ? 'Gelen' : 'Giden'}
                          </span>
                          <span className="text-text-muted">·</span>
                          <span className="max-w-44 truncate font-medium text-text-primary">{item.counterpart_club_name}</span>
                        </span>
                        <span className="block text-xs text-text-tertiary">{item.transfer_type}</span>
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap align-middle text-right text-text-secondary tabular-nums border-l border-border-light">
                        {item.market_value_formatted}
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap align-middle text-right font-medium text-text-primary tabular-nums border-l border-border-light">
                        {item.fee_formatted}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <p className="text-xs text-text-secondary tabular-nums">
          {filteredTransfers.length} kayıt · Kaynak: Transfermarkt
        </p>
      </section>
    </div>
  );
}
