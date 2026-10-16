import { Activity, CheckCircle2, RotateCw } from 'lucide-react';
import PlayerAvatar from '../PlayerAvatar';
import { getPositionLabel } from './teamProfileUtils';
import TeamTacticalMetric from './TeamTacticalMetric';

export default function TeamGameProfileSection({
  activeTeamTab,
  isProfileCached,
  handleManualRefresh,
  isRefreshing,
  tacticalProfile,
  activeTacticalTab,
  setActiveTacticalTab,
  tacticalTabs,
  activeTab,
  scenariosLoading,
  scenarioProfile,
  formatNumber,
  tacticsLoading,
  attackersLoading,
  attackingLeaders,
}) {
  return (
    <>
      {/* TAB: OYUN PROFİLİ & ANALİZ */}
      {activeTeamTab === 'profile' && (
        <section className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-500" />
              <h3 className="text-sm font-black text-slate-900">Takım Oyun Profili</h3>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Değerler seçili dönem ve aynı dönem lig ortalamasıyla karşılaştırılır.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {isProfileCached && (
              <span 
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"
                title={isProfileCached.nextMatchLabel || "Sonraki maça kadar önbellekte saklanır"}
              >
                <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                <span className="hidden sm:inline">
                  {isProfileCached.isPermanent ? 'Kalıcı Sezon Verisi' : (isProfileCached.nextMatchLabel || 'Sonraki maça kadar güncel')}
                </span>
                <span className="sm:hidden">Önbellekte</span>
              </span>
            )}
            <button
              type="button"
              onClick={handleManualRefresh}
              disabled={isRefreshing}
              title="Sunucudan en güncel veriyi çek ve önbelleği yenile"
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold text-slate-700 hover:text-slate-950 bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-slate-300 rounded-lg transition-all active:scale-95 disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 text-slate-500 ${isRefreshing ? 'animate-spin text-emerald-600' : ''}`} />
              <span>{isRefreshing ? 'Yenileniyor...' : 'Yenile'}</span>
            </button>
            {tacticalProfile?.matches > 0 && activeTacticalTab !== 'game-state' && (
              <span className="text-[10px] text-slate-600 font-mono font-medium whitespace-nowrap bg-slate-100 px-2.5 py-1 rounded-lg border border-slate-200">
                {tacticalProfile.matches} maç
              </span>
            )}
          </div>
        </div>

        <div role="tablist" aria-label="Takım oyun profili kategorileri" className="flex gap-1 overflow-x-auto border-b border-slate-200 mb-4">
          {tacticalTabs.map(tab => (
            <button
              key={tab.id}
              id={`team-profile-tab-${tab.id}`}
              type="button"
              role="tab"
              aria-selected={activeTacticalTab === tab.id}
              aria-controls="team-profile-tabpanel"
              onClick={() => setActiveTacticalTab(tab.id)}
              className={`px-3 py-2.5 text-xs font-bold border-b-2 whitespace-nowrap transition-colors ${
                activeTacticalTab === tab.id
                  ? 'border-slate-800 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div role="tabpanel" id="team-profile-tabpanel" aria-labelledby={`team-profile-tab-${activeTacticalTab}`}>
        {activeTacticalTab === 'game-state' ? (
          scenariosLoading ? (
            <div className="py-7 text-center text-xs text-slate-500">Maç akışları inceleniyor...</div>
          ) : !scenarioProfile?.matches ? (
            <div className="py-7 text-center text-xs text-slate-500">Bu dönem için maç akışı bulunamadı.</div>
          ) : (
            <div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 mb-4">
                <p className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1">Takım yorumu</p>
                <p className="text-xs leading-5 text-slate-700">{teamComment()}</p>
                <p className="text-[10px] leading-4 text-slate-500 mt-2">Oranlar ilgili skor durumunda oynanan dakikalar 90 dakikaya ölçeklenerek hesaplanır. Karşılaştırma için en az 90 dakika gerekir; yüksek tempo tek başına etkinlik veya neden göstermez.</p>
              </div>
              <h4 className="text-[11px] font-bold text-slate-600 mb-2">{activeTab.title}</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                  ['level', 'Skor eşit'],
                  ['leading', 'Öndeyken'],
                  ['trailing', 'Gerideyken'],
                ].map(([key, label]) => {
                  const state = scenarioProfile.states?.[key];
                  return (
                    <div key={key} className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
                      <div className="flex items-center justify-between gap-2">
                        <h5 className="text-xs font-bold text-slate-800">{label}</h5>
                        <span className="text-[10px] font-mono text-slate-400">{formatNumber(state?.minutes || 0)} dk</span>
                      </div>
                      <div className="grid grid-cols-2 gap-3 mt-4">
                        {[
                          ['shots', 'Şut'],
                          ['corners', 'Korner'],
                        ].map(([type, metricLabel]) => {
                          const rateKey = `${type}_per_90`;
                          const qualified = state?.[`${rateKey}_qualified`];
                          return (
                            <div key={type}>
                              <p className="text-[10px] uppercase tracking-wide font-bold text-slate-500">{metricLabel} / 90 dk</p>
                              {qualified ? (
                                <>
                                  <p className="text-xl font-black text-slate-900 mt-1">{formatNumber(state[rateKey])}</p>
                                  <p className="text-[10px] text-slate-400 mt-1">Lig ort. {state[`${rateKey}_league_average`] == null ? '—' : formatNumber(state[`${rateKey}_league_average`])}</p>
                                </>
                              ) : (
                                <p className="text-[10px] text-slate-400 mt-2">Yeterli dakika yok</p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )
        ) : tacticsLoading ? (
          <div className="py-7 text-center text-xs text-slate-500">Oyun profili hazırlanıyor...</div>
        ) : !tacticalProfile?.matches ? (
          <div className="py-7 text-center text-xs text-slate-500">Bu dönem için yeterli maç verisi yok.</div>
        ) : (
          <div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 mb-4">
              <p className="text-[10px] uppercase tracking-wide font-bold text-slate-500 mb-1">Takım yorumu</p>
              <p className="text-xs leading-5 text-slate-700">{teamComment()}</p>
              <p className="text-[10px] leading-4 text-slate-500 mt-2">
                {activeTab.explanation} “Lig p80”, değerin lig takımlarının yaklaşık %80’inden yüksek olduğu yüzdelik dilimi anlatır. Yüksek yüzdelik her metrikte daha iyi performans demek değildir.
                {activeTacticalTab === 'defense' && ' PPDA yalnızca takım ve lig verisi en az %80 kapsandığında hesaplanır. PPDA yüzdeliği ham değerin sırasıdır; düşük PPDA daha yoğun pres anlamına gelir.'}
              </p>
            </div>
            <h4 className="text-[11px] font-bold text-slate-600 mb-2">{activeTab.title}</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3">
              {activeTab.keys.map(key => (
                <TeamTacticalMetric key={key} metric={tacticalProfile.metrics?.[key]} totalMatches={tacticalProfile.matches} />
              ))}
            </div>
            {activeTacticalTab === 'attack' && (
              <section className="mt-6 border-t border-slate-200 pt-5" aria-labelledby="team-attacking-leaders-title">
                <div className="mb-3">
                  <h4 id="team-attacking-leaders-title" className="text-sm font-bold text-slate-900">Ofansif reytingde öne çıkan 3 oyuncu</h4>
                  <p className="mt-1 text-[10px] leading-4 text-slate-500">
                    Reyting; 90 dakika başına şut pası, şut, asist ve gol oranlarının takım içindeki en yüksek oranlara göre eşit ağırlıklı puanıdır. En az 180 dakika oynayanlar sıralanır.
                  </p>
                </div>
                {attackersLoading ? (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs text-slate-500">Oyuncu katkıları hesaplanıyor...</div>
                ) : !attackingLeaders?.available ? (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs text-slate-500">
                    {attackingLeaders?.reason || 'Bu sezon için oyuncu bazlı hücum verisi bulunamadı.'}
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {attackingLeaders.players.map(player => (
                        <article key={player.id} className="rounded-lg border border-slate-200 bg-white p-4">
                          <div className="flex items-center gap-3">
                            <PlayerAvatar
                              player={player}
                              shape="circle"
                              size="w-11 h-11 text-xs"
                              fallback="initials"
                              className="border-slate-200 bg-slate-50 shrink-0"
                            />
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-xs font-bold text-slate-900" title={player.name}>{player.name}</p>
                              <p className="mt-0.5 text-[10px] text-slate-500">{getPositionLabel(player.position)} · {player.appearances} maç · {formatNumber(player.minutes)} dk</p>
                            </div>
                            <div className="text-right">
                              <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">Reyting /100</p>
                              <p className="text-xl font-semibold tabular-nums text-slate-900">{formatNumber(player.rating)}</p>
                            </div>
                          </div>
                          <div className="mt-4 grid grid-cols-4 divide-x divide-slate-200 border-t border-slate-100 pt-3">
                            {[
                              ['Şut pası', player.shot_assists],
                              ['Şut', player.shots],
                              ['Asist', player.assists],
                              ['Gol', player.goals],
                            ].map(([label, value]) => (
                              <div key={label} className="px-1 text-center first:pl-0 last:pr-0">
                                <p className="text-base font-semibold tabular-nums text-slate-800">{formatNumber(value)}</p>
                                <p className="mt-0.5 text-[9px] text-slate-500">{label}</p>
                              </div>
                            ))}
                          </div>
                        </article>
                      ))}
                    </div>
                    <p className="mt-2 text-[9px] leading-4 text-slate-400">
                      Şut pası, şut olayında doğrudan asist yapan olarak kaydedilen oyuncuyu sayar; bu, tüm yaratılan fırsatların resmi toplamı değildir.
                      {attackingLeaders.shot_assist_coverage_pct != null && ` Takım şutlarının %{formatNumber(attackingLeaders.shot_assist_coverage_pct)} kadarında bu bilgi mevcut.`}
                    </p>
                  </>
                )}
              </section>
            )}
          </div>
        )}
        </div>
        </section>
      )}

    </>
  );
}
