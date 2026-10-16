import React, { useState, useEffect, useMemo } from 'react';
import { getTeamTransfers } from '../services/teamService';
import { formatSeasonLabel } from '../utils/dateFormatters';
import { 
  ArrowDownLeft, 
  ArrowUpRight, 
  Coins, 
  TrendingUp, 
  TrendingDown, 
  Search, 
  Loader2
} from 'lucide-react';
import PlayerAvatar from './PlayerAvatar';

export default function TeamTransfersSection({ teamId, teamName, season = '2026_27', onSelectPlayer }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [directionFilter, setDirectionFilter] = useState('all'); // 'all', 'in', 'out'
  const [typeFilter, setTypeFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (!teamId) return;
    let isMounted = true;
    setLoading(true);
    setError(null);

    const s = season === 'all' ? '2026_27' : season;
    getTeamTransfers(teamId, s)
      .then(resData => {
        if (isMounted) {
          setData(resData);
          setLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          console.error('Failed to load team transfers:', err);
          setError('Transfer geçmişi yüklenemedi.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [teamId, season]);

  const summary = data?.summary;
  const arrivals = data?.arrivals || [];
  const departures = data?.departures || [];

  const allTransfers = useMemo(() => {
    const list = [...arrivals, ...departures];
    list.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    return list;
  }, [arrivals, departures]);

  const filteredTransfers = useMemo(() => {
    return allTransfers.filter(item => {
      if (directionFilter === 'in' && item.direction !== 'in') return false;
      if (directionFilter === 'out' && item.direction !== 'out') return false;
      if (typeFilter !== 'all' && item.transfer_type !== typeFilter) return false;

      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase().trim();
        const pMatch = (item.player_name || '').toLowerCase().includes(query);
        const cMatch = (item.counterpart_club_name || '').toLowerCase().includes(query);
        if (!pMatch && !cMatch) return false;
      }

      return true;
    });
  }, [allTransfers, directionFilter, typeFilter, searchTerm]);

  if (loading) {
    return (
      <section className="bg-white border border-slate-200 rounded-2xl p-12 text-center shadow-xs">
        <Loader2 className="w-7 h-7 animate-spin text-slate-400 mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-600">
          {teamName || 'Takım'} için Transfermarkt transfer geçmişi yükleniyor...
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="bg-white border border-slate-200 rounded-2xl p-8 text-center shadow-xs">
        <p className="text-sm font-bold text-slate-700 mb-2">{error}</p>
        <button
          onClick={() => {
            setData(null);
            setError(null);
            setLoading(true);
          }}
          className="px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition cursor-pointer"
        >
          Yeniden Dene
        </button>
      </section>
    );
  }

  return (
    <div className="space-y-4">
      {/* Clean unified KPI strip */}
      {summary && (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
          <div className="grid grid-cols-2 divide-y divide-slate-100 sm:grid-cols-4 sm:divide-y-0 sm:divide-x">
            {/* Toplam Harcama */}
            <div className="p-4 sm:p-5">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Toplam Harcama
              </span>
              <div className="mt-1 flex items-baseline gap-1.5">
                <strong className="text-xl sm:text-2xl font-black font-mono text-slate-900">
                  {summary.total_spent_formatted}
                </strong>
              </div>
              <span className="mt-0.5 block text-xs text-slate-500 font-medium">
                {summary.arrivals_count} Gelen Oyuncu
              </span>
            </div>

            {/* Toplam Gelir */}
            <div className="p-4 sm:p-5">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Toplam Gelir
              </span>
              <div className="mt-1 flex items-baseline gap-1.5">
                <strong className="text-xl sm:text-2xl font-black font-mono text-slate-900">
                  {summary.total_income_formatted}
                </strong>
              </div>
              <span className="mt-0.5 block text-xs text-slate-500 font-medium">
                {summary.departures_count} Giden Oyuncu
              </span>
            </div>

            {/* Net Bilanço */}
            <div className="p-4 sm:p-5">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Net Bilanço
              </span>
              <div className="mt-1 flex items-baseline gap-1.5">
                <strong className={`text-xl sm:text-2xl font-black font-mono ${
                  summary.net_balance_eur >= 0 ? 'text-emerald-700' : 'text-slate-900'
                }`}>
                  {summary.net_balance_formatted}
                </strong>
                {summary.net_balance_eur >= 0 ? (
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-600 shrink-0 self-center" />
                ) : (
                  <TrendingDown className="w-3.5 h-3.5 text-slate-400 shrink-0 self-center" />
                )}
              </div>
              <span className="mt-0.5 block text-xs text-slate-500 font-medium">
                {summary.net_balance_eur >= 0 ? 'Pozitif Bakiye (Kâr)' : 'Yatırım Dengesi'}
              </span>
            </div>

            {/* Transfer Hacmi */}
            <div className="p-4 sm:p-5">
              <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Transfer Hacmi
              </span>
              <div className="mt-1 flex items-baseline gap-1.5">
                <strong className="text-xl sm:text-2xl font-black font-mono text-slate-900">
                  {summary.arrivals_count + summary.departures_count}
                </strong>
                <span className="text-xs text-slate-500 font-medium">Hareket</span>
              </div>
              <span className="mt-0.5 block text-xs text-slate-500 font-medium">
                {season && season !== 'all' ? `${formatSeasonLabel(season)} Sezonu` : 'Transfermarkt Arşivi'}
              </span>
            </div>
          </div>
        </section>
      )}

      {/* Main Table Card */}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
        {/* Controls Bar */}
        <div className="flex flex-col gap-3 border-b border-slate-100 p-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          
          {/* Segmented Control for Direction (Tümü, Gelenler, Gidenler) */}
          <div className="inline-flex rounded-xl bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => setDirectionFilter('all')}
              className={`rounded-lg px-3 py-1.5 text-xs font-bold transition cursor-pointer ${
                directionFilter === 'all'
                  ? 'bg-white text-slate-950 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Tümü ({allTransfers.length})
            </button>
            <button
              type="button"
              onClick={() => setDirectionFilter('in')}
              className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-bold transition cursor-pointer ${
                directionFilter === 'in'
                  ? 'bg-white text-slate-950 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <ArrowDownLeft className="w-3 h-3 text-emerald-600" />
              <span>Gelenler ({arrivals.length})</span>
            </button>
            <button
              type="button"
              onClick={() => setDirectionFilter('out')}
              className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-bold transition cursor-pointer ${
                directionFilter === 'out'
                  ? 'bg-white text-slate-950 shadow-2xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <ArrowUpRight className="w-3 h-3 text-slate-500" />
              <span>Gidenler ({departures.length})</span>
            </button>
          </div>

          {/* Type Filter & Search */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none focus:border-slate-400 cursor-pointer shadow-2xs"
            >
              <option value="all">Tüm Transfer Türleri</option>
              <option value="Bonservis">Bonservisli Transferler</option>
              <option value="Kiralık">Kiralık</option>
              <option value="Kiradan Geri Dönüş">Kiradan Geri Dönüş</option>
              <option value="Serbest">Serbest / Bedelsiz</option>
              <option value="Altyapı">Altyapı Terfisi</option>
            </select>

            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Oyuncu veya kulüp..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-40 sm:w-48 rounded-xl border border-slate-200 bg-white pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 outline-none focus:border-slate-400 shadow-2xs"
              />
            </div>
          </div>
        </div>

        {/* Clean Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-100 bg-slate-50/60 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-2.5 px-4">Tarih</th>
                <th className="py-2.5 px-4">Oyuncu</th>
                <th className="py-2.5 px-2 text-center">Yaş</th>
                <th className="py-2.5 px-4">Yön & Karşı Takım</th>
                <th className="py-2.5 px-4">Transfer Türü</th>
                <th className="py-2.5 px-4 text-right">Piyasa Değeri</th>
                <th className="py-2.5 px-4 text-right">Bonservis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredTransfers.length > 0 ? (
                filteredTransfers.map((item, idx) => {
                  const isArrival = item.direction === 'in';

                  return (
                    <tr
                      key={item.id || idx}
                      className="transition hover:bg-slate-50/70"
                    >
                      {/* Tarih */}
                      <td className="py-3 px-4 whitespace-nowrap text-slate-600">
                        <span className="font-semibold text-slate-900 block">{item.date_formatted}</span>
                        <span className="text-[10px] text-slate-400 font-mono">{item.season}</span>
                      </td>

                      {/* Oyuncu Adı + Avatar */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2.5">
                          <PlayerAvatar
                            name={item.player_name}
                            size="sm"
                            shape="rounded"
                            fallback="initials"
                            className="bg-slate-100 border border-slate-200/80 shadow-2xs shrink-0"
                          />
                          <div className="min-w-0">
                            <button
                              type="button"
                              onClick={() => onSelectPlayer && onSelectPlayer({
                                id: item.player_id,
                                tm_id: item.player_id,
                                name: item.player_name,
                              })}
                              title={`${item.player_name} kariyer piyasa değeri grafiğini görüntüle`}
                              className="font-bold text-slate-900 hover:text-slate-600 transition cursor-pointer text-left truncate block max-w-[180px] group"
                            >
                              <span className="group-hover:underline">{item.player_name}</span>
                            </button>
                            {item.player_id && (
                              <span className="text-[10px] text-slate-400 font-mono block">
                                #{item.player_id}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* Yaş */}
                      <td className="py-3 px-2 text-center font-mono text-slate-600">
                        {item.age || '—'}
                      </td>

                      {/* Yön & Karşı Takım */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex items-center gap-1 text-[11px] font-semibold shrink-0 ${
                            isArrival ? 'text-emerald-700' : 'text-slate-500'
                          }`}>
                            {isArrival ? (
                              <ArrowDownLeft className="w-3.5 h-3.5 text-emerald-600" />
                            ) : (
                              <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
                            )}
                            {isArrival ? 'Gelen' : 'Giden'}
                          </span>

                          <span className="text-slate-300">·</span>

                          <span className="font-semibold text-slate-800 truncate max-w-[170px]">
                            {item.counterpart_club_name}
                          </span>
                        </div>
                      </td>

                      {/* Transfer Türü (Minimalist rozet) */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="inline-block px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200/80">
                          {item.transfer_type}
                        </span>
                      </td>

                      {/* Piyasa Değeri */}
                      <td className="py-3 px-4 text-right font-mono text-xs text-slate-500 whitespace-nowrap">
                        {item.market_value_formatted}
                      </td>

                      {/* Bonservis Bedeli */}
                      <td className="py-3 px-4 text-right font-mono whitespace-nowrap">
                        <span className="font-bold text-slate-900 text-xs sm:text-sm">
                          {item.fee_formatted}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="7" className="py-10 text-center text-slate-400 text-xs">
                    Seçilen filtre kriterlerine uygun transfer kaydı bulunamadı.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Clean Footer */}
        <div className="border-t border-slate-100 bg-slate-50/40 px-4 py-2.5 text-[11px] text-slate-400 flex flex-wrap items-center justify-between gap-2">
          <span>Transfermarkt resmi veritabanı kayıtları</span>
          <span className="font-mono">{filteredTransfers.length} kayıt</span>
        </div>
      </section>
    </div>
  );
}
