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
  const compareWithLeague = key => {
    const metric = tacticalProfile?.metrics?.[key];
    if (metric?.value == null || metric?.league_average == null) return null;
    const difference = Number(metric.value) - Number(metric.league_average);
    if (Math.abs(difference) < 0.05) return `${metric.label.toLocaleLowerCase('tr-TR')} lig ortalamasına yakın`;
    const amount = formatNumber ? formatNumber(Math.abs(difference)) : Number(Math.abs(difference)).toFixed(1);
    const label = metric.label.toLocaleLowerCase('tr-TR');
    if (metric.unit === 'PPDA') {
      return `PPDA lig ortalamasından ${amount} ${difference < 0 ? 'düşük (daha yoğun pres göstergesi)' : 'yüksek (daha düşük pres yoğunluğu göstergesi)'}`;
    }
    if (metric.unit === '%') {
      return `${label}, lig ortalamasından ${amount} yüzde puan ${difference > 0 ? 'yüksek' : 'düşük'}`;
    }
    return `${label}, lig ortalamasından maç başına ${amount} ${difference > 0 ? 'fazla' : 'az'}`;
  };

  const teamComment = () => {
    const name = tacticalProfile?.team_name || 'Takım';
    if (activeTacticalTab === 'general') {
      const possession = compareWithLeague('possession');
      const forwardPasses = compareWithLeague('forward_pass_share');
      if (!possession && !forwardPasses) return 'Karşılaştırmalı yorum için henüz yeterli veri yok.';
      return `${name} için ${[possession, forwardPasses].filter(Boolean).join('; ')}. Bu iki ölçü topu ne kadar tuttuğunu ve pasların ne kadarının ileri bölgeye yöneldiğini anlatır; tek başına hücum başarısı veya maç sonucu göstermez.`;
    }
    if (activeTacticalTab === 'attack') {
      const boxTouches = compareWithLeague('opposition_box_touches');
      const entries = compareWithLeague('final_third_entries');
      const shots = compareWithLeague('shots_per_match');
      const onTarget = compareWithLeague('shots_on_target_share');
      const passAccuracy = compareWithLeague('final_third_pass_accuracy');
      const observations = [entries, boxTouches, shots, onTarget, passAccuracy].filter(Boolean);
      if (!observations.length) return 'Karşılaştırmalı yorum için henüz yeterli veri yok.';
      return `${name} için ${observations.join('; ')}. Son bölgeye giriş ve ceza sahası dokunuşu hücum alanına erişimi, şut sayısı üretim hacmini gösterir. Son bölge pas isabeti tamamlanan pasların; isabetli şut oranı ise kaleyi bulan şutların payıdır. Bu ölçüler şut kalitesini veya gol beklentisini tek başına göstermez.`;
    }
    if (activeTacticalTab === 'passing') {
      const longPassShare = compareWithLeague('long_ball_share');
      const crosses = compareWithLeague('crosses_per_match');
      const observations = [longPassShare, crosses].filter(Boolean);
      if (!observations.length) return 'Karşılaştırmalı yorum için henüz yeterli veri yok.';
      return `${name} için ${observations.join('; ')}. İsabet kartları başarılı pasların tüm denemelere oranını gösterir; hedef oyuncuyu, pasın saha içindeki noktasını veya oluşan fırsatın kalitesini göstermez.`;
    }
    if (activeTacticalTab === 'set-pieces') {
      const corners = compareWithLeague('corners_into_box_share');
      if (!corners) return 'Karşılaştırmalı yorum için henüz yeterli veri yok.';
      return `${name} için ${corners}. Bu oran korner tercihini anlatır; ceza sahasına gönderilen topların isabetini veya oluşturduğu şut ve gol sayısını göstermez.`;
    }
    if (activeTacticalTab === 'defense') {
      const shotsConceded = compareWithLeague('shots_conceded_per_match');
      const ppda = compareWithLeague('pressing_intensity');
      const attackingThird = compareWithLeague('attacking_third_recoveries');
      const aerialDuels = compareWithLeague('aerial_duel_success');
      const observations = [shotsConceded, ppda, attackingThird, aerialDuels].filter(Boolean);
      if (!observations.length) return 'Karşılaştırmalı yorum için henüz yeterli veri yok.';
      return `${name} için ${observations.join('; ')}. İzin verilen şut kaleye gelen toplam şut hacmini, PPDA düşükse baskının yoğunluğunu; hücum bölgesindeki top kazanımları topun nerede geri alındığını, hava topu oranı ise bu mücadelelerin ne kadarının kazanıldığını gösterir.`;
    }
    if (activeTacticalTab === 'losses') {
      const totalLosses = compareWithLeague('possession_losses');
      const controlledLosses = compareWithLeague('controlled_possession_losses');
      const observations = [totalLosses, controlledLosses].filter(Boolean);
      if (!observations.length) return 'Karşılaştırmalı yorum için henüz yeterli veri yok.';
      return `${name} için ${observations.join('; ')}. Bunlar maç içindeki kayıp aksiyonlarının sayısıdır; daha çok topa sahip olan veya daha çok pas yapan takımda bu sayı da artabilir. Bu yüzden tek başına hata oranı olarak okunmamalıdır.`;
    }

    const stateNames = { level: 'skor eşitken', leading: 'öndeyken', trailing: 'gerideyken' };
    const candidates = Object.entries(scenarioProfile?.states || {}).flatMap(([stateKey, state]) => (
      ['shots', 'corners'].map(type => {
        const rateKey = `${type}_per_90`;
        const averageKey = `${rateKey}_league_average`;
        if (!state?.[`${rateKey}_qualified`] || state[rateKey] == null || state[averageKey] == null) return null;
        return {
          state: stateNames[stateKey],
          label: type === 'shots' ? 'şut' : 'korner',
          difference: Number(state[rateKey]) - Number(state[averageKey]),
        };
      }).filter(Boolean)
    ));
    if (!candidates.length) return 'Skor durumlarına göre yorum için en az 90 dakikalık karşılaştırılabilir örnek gerekir.';
    const strongest = candidates.reduce((best, candidate) => (
      Math.abs(candidate.difference) > Math.abs(best.difference) ? candidate : best
    ));
    const direction = strongest.difference > 0.05 ? 'yüksek' : strongest.difference < -0.05 ? 'düşük' : 'yakın';
    const delta = Math.abs(strongest.difference);
    const comparison = direction === 'yakın'
      ? 'lig ortalamasına yakın'
      : `lig ortalamasından ${formatNumber ? formatNumber(delta) : Number(delta).toFixed(1)} / 90 dakika daha ${direction}`;
    return `${name} ${strongest.state} ${strongest.label} temposunda ${comparison}. Bu, ilgili skor durumundaki aksiyon hacmini gösterir; skor değişikliğinin nedeni olduğunu kanıtlamaz.`;
  };

  return (
    <>
      {/* TAB: OYUN PROFİLİ & ANALİZ */}
      {activeTeamTab === 'profile' && (
        <section className="bg-background-primary border border-border rounded p-5 ">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4 pb-3 border-b border-border-light">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-text-secondary" />
              <h3 className="text-sm font-semibold text-text-primary">Takım Oyun Profili</h3>
            </div>
            <p className="text-xs text-text-secondary mt-1">Değerler seçili dönem ve aynı dönem lig ortalamasıyla karşılaştırılır.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {isProfileCached && (
              <span 
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm text-xs font-semibold bg-background-tertiary text-status-success border border-border"
                title={isProfileCached.nextMatchLabel || "Sonraki maça kadar önbellekte saklanır"}
              >
                <CheckCircle2 className="w-3 h-3 text-status-success shrink-0" />
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
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-text-secondary hover:text-slate-950 bg-background-tertiary hover:bg-background-tertiary border border-border hover:border-slate-300 rounded transition-all  disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 text-text-secondary ${isRefreshing ? 'animate-spin text-status-success' : ''}`} />
              <span>{isRefreshing ? 'Yenileniyor...' : 'Yenile'}</span>
            </button>
            {tacticalProfile?.matches > 0 && activeTacticalTab !== 'game-state' && (
              <span className="text-xs text-text-secondary font-mono font-medium whitespace-nowrap bg-background-tertiary px-2.5 py-1 rounded border border-border">
                {tacticalProfile.matches} maç
              </span>
            )}
          </div>
        </div>

        <div role="tablist" aria-label="Takım oyun profili kategorileri" className="flex gap-1 overflow-x-auto border-b border-border mb-4">
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
                  ? 'border-slate-800 text-text-primary'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div role="tabpanel" id="team-profile-tabpanel" aria-labelledby={`team-profile-tab-${activeTacticalTab}`}>
        {activeTacticalTab === 'game-state' ? (
          scenariosLoading ? (
            <div className="py-7 text-center text-xs text-text-secondary">Maç akışları inceleniyor...</div>
          ) : !scenarioProfile?.matches ? (
            <div className="py-7 text-center text-xs text-text-secondary">Bu dönem için maç akışı bulunamadı.</div>
          ) : (
            <div>
              <div className="rounded border border-border bg-background-tertiary p-4 mb-4">
                <p className="text-xs uppercase tracking-wide font-bold text-text-secondary mb-1">Takım yorumu</p>
                <p className="text-xs leading-5 text-text-secondary">{teamComment()}</p>
                <p className="text-xs leading-4 text-text-secondary mt-2">Oranlar ilgili skor durumunda oynanan dakikalar 90 dakikaya ölçeklenerek hesaplanır. Karşılaştırma için en az 90 dakika gerekir; yüksek tempo tek başına etkinlik veya neden göstermez.</p>
              </div>
              <h4 className="text-xs font-bold text-text-secondary mb-2">{activeTab.title}</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                  ['level', 'Skor eşit'],
                  ['leading', 'Öndeyken'],
                  ['trailing', 'Gerideyken'],
                ].map(([key, label]) => {
                  const state = scenarioProfile.states?.[key];
                  return (
                    <div key={key} className="rounded border border-border bg-background-tertiary/60 p-4">
                      <div className="flex items-center justify-between gap-2">
                        <h5 className="text-xs font-bold text-text-primary">{label}</h5>
                        <span className="text-xs font-mono text-text-muted">{formatNumber(state?.minutes || 0)} dk</span>
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
                              <p className="text-xs uppercase tracking-wide font-bold text-text-secondary">{metricLabel} / 90 dk</p>
                              {qualified ? (
                                <>
                                  <p className="text-xl font-semibold text-text-primary mt-1">{formatNumber(state[rateKey])}</p>
                                  <p className="text-xs text-text-muted mt-1">Lig ort. {state[`${rateKey}_league_average`] == null ? '—' : formatNumber(state[`${rateKey}_league_average`])}</p>
                                </>
                              ) : (
                                <p className="text-xs text-text-muted mt-2">Yeterli dakika yok</p>
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
          <div className="py-7 text-center text-xs text-text-secondary">Oyun profili hazırlanıyor...</div>
        ) : !tacticalProfile?.matches ? (
          <div className="py-7 text-center text-xs text-text-secondary">Bu dönem için yeterli maç verisi yok.</div>
        ) : (
          <div>
            <div className="rounded border border-border bg-background-tertiary p-4 mb-4">
              <p className="text-xs uppercase tracking-wide font-bold text-text-secondary mb-1">Takım yorumu</p>
              <p className="text-xs leading-5 text-text-secondary">{teamComment()}</p>
              <p className="text-xs leading-4 text-text-secondary mt-2">
                {activeTab.explanation} “Lig p80”, değerin lig takımlarının yaklaşık %80’inden yüksek olduğu yüzdelik dilimi anlatır. Yüksek yüzdelik her metrikte daha iyi performans demek değildir.
                {activeTacticalTab === 'defense' && ' PPDA yalnızca takım ve lig verisi en az %80 kapsandığında hesaplanır. PPDA yüzdeliği ham değerin sırasıdır; düşük PPDA daha yoğun pres anlamına gelir.'}
              </p>
            </div>
            <h4 className="text-xs font-bold text-text-secondary mb-2">{activeTab.title}</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3">
              {activeTab.keys.map(key => (
                <TeamTacticalMetric key={key} metric={tacticalProfile.metrics?.[key]} totalMatches={tacticalProfile.matches} />
              ))}
            </div>
            {activeTacticalTab === 'attack' && (
              <section className="mt-6 border-t border-border pt-5" aria-labelledby="team-attacking-leaders-title">
                <div className="mb-3">
                  <h4 id="team-attacking-leaders-title" className="text-sm font-bold text-text-primary">Ofansif reytingde öne çıkan 3 oyuncu</h4>
                  <p className="mt-1 text-xs leading-4 text-text-secondary">
                    Reyting; 90 dakika başına şut pası, şut, asist ve gol oranlarının takım içindeki en yüksek oranlara göre eşit ağırlıklı puanıdır. En az 180 dakika oynayanlar sıralanır.
                  </p>
                </div>
                {attackersLoading ? (
                  <div className="rounded border border-border bg-background-tertiary p-4 text-xs text-text-secondary">Oyuncu katkıları hesaplanıyor...</div>
                ) : !attackingLeaders?.available ? (
                  <div className="rounded border border-border bg-background-tertiary p-4 text-xs text-text-secondary">
                    {attackingLeaders?.reason || 'Bu sezon için oyuncu bazlı hücum verisi bulunamadı.'}
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {attackingLeaders.players.map(player => (
                        <article key={player.id} className="rounded border border-border bg-background-primary p-4">
                          <div className="flex items-center gap-3">
                            <PlayerAvatar
                              player={player}
                              shape="circle"
                              size="w-11 h-11 text-xs"
                              fallback="initials"
                              className="border-border bg-background-tertiary shrink-0"
                            />
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-xs font-bold text-text-primary" title={player.name}>{player.name}</p>
                              <p className="mt-0.5 text-xs text-text-secondary">{getPositionLabel(player.position)} · {player.appearances} maç · {formatNumber(player.minutes)} dk</p>
                            </div>
                            <div className="text-right">
                              <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Reyting /100</p>
                              <p className="text-xl font-semibold tabular-nums text-text-primary">{formatNumber(player.rating)}</p>
                            </div>
                          </div>
                          <div className="mt-4 grid grid-cols-4 divide-x divide-slate-200 border-t border-border-light pt-3">
                            {[
                              ['Şut pası', player.shot_assists],
                              ['Şut', player.shots],
                              ['Asist', player.assists],
                              ['Gol', player.goals],
                            ].map(([label, value]) => (
                              <div key={label} className="px-1 text-center first:pl-0 last:pr-0">
                                <p className="text-base font-semibold tabular-nums text-text-primary">{formatNumber(value)}</p>
                                <p className="mt-0.5 text-xs text-text-secondary">{label}</p>
                              </div>
                            ))}
                          </div>
                        </article>
                      ))}
                    </div>
                    <p className="mt-2 text-xs leading-4 text-text-muted">
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
