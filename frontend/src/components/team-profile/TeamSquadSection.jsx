import { TrendingUp, Users } from 'lucide-react';
import PlayerAvatar from '../PlayerAvatar';
import { SQUAD_POSITION_TABS, getPositionBadgeStyle, getPositionLabel } from './teamProfileUtils';

export default function TeamSquadSection({
  activeTeamTab,
  displayedSquad,
  currentMeta,
  selectedSquadTab,
  setSelectedSquadTab,
  teamStaff,
  displayedSquadCounts,
  filteredSquad,
  handleSquadSort,
  squadSortField,
  squadSortDirection,
  setSelectedPlayerForMv,
}) {
  return (
    <>
      {/* TAB: KADRO LİSTESİ */}
      {activeTeamTab === 'squad' && displayedSquad.length > 0 && (
        <div className="bg-background-primary border border-border rounded p-5  space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border-light">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-text-primary" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-secondary">
                {currentMeta.name} — Kadro Listesi ({selectedSquadTab === 'all' ? displayedSquad.length : `${filteredSquad.length} / ${displayedSquad.length}`} Oyuncu)
              </h3>
              {teamStaff?.players?.length > 0 && <span className="text-xs text-text-muted">PulseLive lisanslı kadro</span>}
            </div>

            {/* Position Tabs: Kaleci, Savunma, Orta Saha, Forvet (plus Tümü) */}
            <div
              role="tablist"
              aria-label="Oyuncu pozisyon sekmeleri"
              className="flex items-center bg-background-tertiary p-1 rounded border border-border gap-1 overflow-x-auto scrollbar-none"
            >
              {SQUAD_POSITION_TABS.map(tab => {
                const isSelected = selectedSquadTab === tab.id;
                const count = displayedSquadCounts[tab.id] || 0;
                return (
                  <button
                    key={tab.id}
                    id={`squad-tab-${tab.id}`}
                    type="button"
                    role="tab"
                    aria-selected={isSelected}
                    aria-controls="squad-tabpanel"
                    onClick={() => setSelectedSquadTab(tab.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-bold transition-all whitespace-nowrap ${
                      isSelected
                        ? 'bg-primary text-white '
                        : 'text-text-secondary hover:text-text-primary hover:bg-slate-200/60'
                    }`}
                  >
                    <span>{tab.label}</span>
                    <span
                      className={`text-xs font-mono font-bold px-1.5 py-0.2 rounded-full ${
                        isSelected
                          ? 'bg-background-primary/20 text-white'
                          : 'bg-slate-200 text-text-secondary'
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <div role="tabpanel" id="squad-tabpanel" aria-labelledby={`squad-tab-${selectedSquadTab}`}>
            {filteredSquad.length === 0 ? (
              <div className="py-12 text-center text-xs text-text-secondary font-medium">
                Bu mevkide kayıtlı oyuncu bulunamadı.
              </div>
            ) : (
              <div className="overflow-x-auto scrollbar-thin">
                <div className="min-w-[620px] border border-border rounded bg-background-primary shadow-2xs overflow-hidden">
                  <div className="max-h-[560px] overflow-y-auto divide-y divide-slate-100 scrollbar-thin">
                    {/* Liste Başlık Satırı (Sticky) */}
                    <div className="sticky top-0 z-10 px-3.5 py-2.5 bg-background-tertiary text-text-secondary font-bold text-xs uppercase tracking-wider flex items-center gap-3 select-none border-b border-border shadow-2xs">
                      <button
                        type="button"
                        onClick={() => handleSquadSort('shirt')}
                        className="w-10 text-center shrink-0 hover:text-text-primary transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Forma Numarasına göre sırala"
                      >
                        <span>#</span>
                        {squadSortField === 'shirt' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('name')}
                        className="flex-1 min-w-[170px] text-left hover:text-text-primary transition-colors flex items-center gap-1 cursor-pointer"
                        title="İsme göre sırala"
                      >
                        <span>Oyuncu</span>
                        {squadSortField === 'name' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('position')}
                        className="w-20 text-center shrink-0 hover:text-text-primary transition-colors hidden sm:flex items-center justify-center gap-1 cursor-pointer"
                        title="Mevkiye göre sırala"
                      >
                        <span>Mevki</span>
                        {squadSortField === 'position' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('market_value_eur')}
                        className="w-22 text-center shrink-0 hover:text-text-primary transition-colors hidden sm:flex items-center justify-center gap-1 cursor-pointer font-bold text-amber-800"
                        title="Transfermarkt piyasa değerine göre sırala"
                      >
                        <span>Piyasa Değeri</span>
                        {squadSortField === 'market_value_eur' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('appearances')}
                        className="w-14 text-center shrink-0 hover:text-text-primary transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Oynadığı toplam maç sayısına göre sırala"
                      >
                        <span>Maç</span>
                        {squadSortField === 'appearances' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('starts')}
                        className="w-14 text-center shrink-0 hover:text-text-primary transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="İlk 11 başladığı maç sayısına göre sırala"
                      >
                        <span>İlk 11</span>
                        {squadSortField === 'starts' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('goals')}
                        className="w-14 text-center shrink-0 text-emerald-700 hover:text-emerald-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Bu sezon attığı gole göre sırala"
                      >
                        <span>Gol</span>
                        {squadSortField === 'goals' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('assists')}
                        className="w-14 text-center shrink-0 text-sky-700 hover:text-sky-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Bu sezon yaptığı asiste göre sırala"
                      >
                        <span>Asist</span>
                        {squadSortField === 'assists' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('yellow_cards')}
                        className="w-14 text-center shrink-0 text-amber-700 hover:text-amber-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Sarı karta göre sırala"
                      >
                        <span className="w-2 h-3 bg-amber-400 rounded-xs inline-block shadow-2xs" />
                        <span>Sarı</span>
                        {squadSortField === 'yellow_cards' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('red_cards')}
                        className="w-14 text-center shrink-0 text-rose-700 hover:text-rose-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Kırmızı karta göre sırala"
                      >
                        <span className="w-2 h-3 bg-rose-500 rounded-xs inline-block shadow-2xs" />
                        <span>Kırmızı</span>
                        {squadSortField === 'red_cards' && (
                          <span className="text-xs">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>
                    </div>

                    {/* Oyuncu Satırları (Aynı Fikstür Listesi Tasarımı) */}
                    {filteredSquad.map(player => (
                      <div
                        key={player.id}
                        className="px-3.5 py-2.5 hover:bg-background-tertiary/80 transition-colors flex items-center gap-3 text-xs group"
                      >
                        {/* 1. Forma Numarası */}
                        <div className="w-10 text-center shrink-0 font-mono font-semibold text-text-secondary text-xs sm:text-sm">
                          {player.shirt != null && player.shirt !== '' ? `#${player.shirt}` : '—'}
                        </div>

                        {/* 2. Oyuncu (Avatar + İsim + Kaptan) */}
                        <div className="flex items-center gap-2.5 flex-1 min-w-[170px]">
                          <PlayerAvatar
                            player={player}
                            size="w-8 h-8 text-xs shrink-0"
                            shape="rounded"
                            fallback="shirt"
                            className="bg-background-tertiary border border-border shadow-2xs shrink-0"
                            imgClassName="object-contain"
                          />
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-text-primary text-xs sm:text-sm truncate">
                                {player.name}
                              </span>
                              {player.captain && (
                                <span className="shrink-0 px-1 py-0.2 rounded bg-amber-100 text-amber-800 text-xs font-semibold font-mono border border-amber-300">
                                  C
                                </span>
                              )}
                            </div>
                            <div className="sm:hidden text-xs text-text-secondary font-medium">
                              {getPositionLabel(player.position)}
                            </div>
                          </div>
                        </div>

                        {/* 3. Mevki */}
                        <div className="w-20 text-center shrink-0 hidden sm:block">
                          <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold border ${getPositionBadgeStyle(player.position)}`}>
                            {getPositionLabel(player.position)}
                          </span>
                        </div>

                        {/* 3.5. Piyasa Değeri */}
                        <div className="w-22 text-center shrink-0 hidden sm:block">
                          {player.market_value_formatted ? (
                            <button
                              type="button"
                              onClick={() => setSelectedPlayerForMv(player)}
                              title={`${player.name} kariyer piyasa değeri grafiğini görüntüle`}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono font-bold text-xs bg-amber-50 hover:bg-amber-100 text-amber-950 border border-amber-200 hover:border-amber-300 shadow-2xs transition cursor-pointer active:scale-95 group"
                            >
                              <span>{player.market_value_formatted}</span>
                              <TrendingUp className="w-2.5 h-2.5 text-amber-600 opacity-60 group-hover:opacity-100 transition-opacity" />
                            </button>
                          ) : (
                            <span className="text-slate-300 font-mono text-xs">—</span>
                          )}
                        </div>

                        {/* 4. Oynadığı Toplam Maç */}
                        <div className="w-14 text-center shrink-0 font-mono font-bold text-text-primary text-xs">
                          {player.appearances ?? 0}
                        </div>

                        {/* 5. İlk 11 Başladığı */}
                        <div className="w-14 text-center shrink-0 font-mono font-semibold text-text-secondary text-xs">
                          {player.starts ?? 0}
                        </div>

                        {/* 6. Bu Sezon Attığı Gol */}
                        <div className="w-14 text-center shrink-0 font-mono font-semibold text-emerald-600 text-xs">
                          {(player.goals || 0) > 0 ? (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                              {player.goals}
                            </span>
                          ) : (
                            <span className="text-text-muted">0</span>
                          )}
                        </div>

                        {/* 7. Asist */}
                        <div className="w-14 text-center shrink-0 font-mono font-bold text-sky-600 text-xs">
                          {(player.assists || 0) > 0 ? (
                            <span className="px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 font-bold border border-sky-200">
                              {player.assists}
                            </span>
                          ) : (
                            <span className="text-text-muted">0</span>
                          )}
                        </div>

                        {/* 8. Sarı Kart */}
                        <div className="w-14 text-center shrink-0 font-mono text-xs flex items-center justify-center gap-1">
                          {(player.yellow_cards || 0) > 0 ? (
                            <span className="inline-flex items-center gap-1 font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                              <span className="w-2 h-2.5 bg-amber-400 rounded-xs inline-block" />
                              {player.yellow_cards}
                            </span>
                          ) : (
                            <span className="text-slate-300 font-medium">0</span>
                          )}
                        </div>

                        {/* 9. Kırmızı Kart */}
                        <div className="w-14 text-center shrink-0 font-mono text-xs flex items-center justify-center gap-1">
                          {(player.red_cards || 0) > 0 ? (
                            <span className="inline-flex items-center gap-1 font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                              <span className="w-2 h-2.5 bg-rose-500 rounded-xs inline-block" />
                              {player.red_cards}
                            </span>
                          ) : (
                            <span className="text-slate-300 font-medium">0</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

    </>
  );
}
