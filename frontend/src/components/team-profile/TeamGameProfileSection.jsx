import { Activity, CheckCircle2, RotateCw } from 'lucide-react';
import PlayerAvatar from '../PlayerAvatar';
import { getPositionLabel } from './teamProfileUtils';
import TeamTacticalMetric, { LOW_SAMPLE_MATCHES } from './TeamTacticalMetric';

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
    if (metric?.value == null || metric?.difference == null) return null;
    const difference = Number(metric.difference);
    const label = metric.label.toLocaleLowerCase('tr-TR');
    const tolerance = 0.5 * 10 ** -(metric.decimals ?? 1);
    if (Math.abs(difference) < tolerance) return `${label} diğer takımların ortalamasına yakın`;
    const amount = Math.abs(difference).toLocaleString('tr-TR', {
      minimumFractionDigits: metric.decimals ?? 1,
      maximumFractionDigits: metric.decimals ?? 1,
    });
    if (metric.unit === 'PPDA') {
      return `PPDA diğer takımların ortalamasından ${amount} ${difference < 0 ? 'düşük (daha yoğun pres göstergesi)' : 'yüksek (daha düşük pres yoğunluğu göstergesi)'}`;
    }
    if (metric.unit === '%') {
      return `${label}, diğer takımların ortalamasından ${amount} yüzde puan ${difference > 0 ? 'yüksek' : 'düşük'}`;
    }
    return `${label}, diğer takımların ortalamasından ${metric.unit} ${amount} ${difference > 0 ? 'fazla' : 'az'}`;
  };

  const TAB_NOTES = {
    general: 'Bu ölçüler topu ne kadar tuttuğunu ve pasların ne kadarının ileri bölgeye yöneldiğini anlatır; tek başına hücum başarısı veya maç sonucu göstermez.',
    attack: 'Son bölgeye giriş ve ceza sahası erişimi hücum alanına ulaşmayı, şut sayısı üretim hacmini gösterir. xG şutların konum ve türüne göre kalitesini hesaba katar; yine de gerçek golü garanti etmez.',
    passing: 'İsabet kartları başarılı pasların tüm denemelere oranını gösterir; hedef oyuncuyu, pasın saha içindeki noktasını veya oluşan fırsatın kalitesini göstermez.',
    'set-pieces': 'Bu ölçüler korner hacmini ve tercihini anlatır; ceza sahasına gönderilen topların isabetini veya oluşturduğu şut ve gol sayısını göstermez.',
    defense: 'İzin verilen şut ve xGA rakibin ürettiği tehlikeyi, ceza sahası içi payı şutların nereden geldiğini gösterir. PPDA düşükse baskı yoğundur; top kazanımları topun nerede geri alındığını anlatır.',
    losses: 'Maç başı kayıp sayısı topa sahip olan takımda doğal olarak artar. 100 dokunuş başına oran bu hacmi dengeler; ikisi birlikte okunmalıdır.',
    discipline: 'Faul ve kart sayıları oyun biçiminden ve hakem eğiliminden etkilenir; tek başına savunma kalitesini göstermez.',
  };

  const teamComment = () => {
    const name = tacticalProfile?.team_name || 'Takım';
    if (activeTacticalTab !== 'game-state') {
      // Surface the metrics that sit farthest from the middle of the league.
      const highlights = (activeTab?.keys || [])
        .map(key => ({ metric: tacticalProfile?.metrics?.[key], text: compareWithLeague(key) }))
        .filter(item => item.text)
        .sort((a, b) => Math.abs((b.metric.percentile ?? 50) - 50) - Math.abs((a.metric.percentile ?? 50) - 50))
        .slice(0, 3);
      if (!highlights.length) return 'Karşılaştırmalı yorum için henüz yeterli veri yok.';
      return `${name} için öne çıkanlar: ${highlights.map(item => item.text).join('; ')}. ${TAB_NOTES[activeTacticalTab] || ''}`.trim();
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
        <section className="bg-background-primary border border-border rounded p-5">
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
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-text-secondary hover:text-text-primary bg-background-tertiary hover:bg-background-tertiary border border-border hover:border-border rounded transition-all disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 text-text-secondary ${isRefreshing ? 'animate-spin text-status-success' : ''}`} />
              <span>{isRefreshing ? 'Yenileniyor...' : 'Yenile'}</span>
            </button>
            {tacticalProfile?.matches > 0 && activeTacticalTab !== 'game-state' && (
              <span className="text-xs text-text-secondary tabular-nums font-medium whitespace-nowrap bg-background-tertiary px-2.5 py-1 rounded border border-border">
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
              className={`px-3 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors ${
                activeTacticalTab === tab.id
                  ? 'border-border text-text-primary'
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
                <p className="text-xs font-semibold text-text-secondary mb-1">Takım yorumu</p>
                <p className="text-xs leading-5 text-text-secondary">{teamComment()}</p>
                <p className="text-xs leading-4 text-text-secondary mt-2">Oranlar ilgili skor durumunda oynanan dakikalar 90 dakikaya ölçeklenerek hesaplanır. Karşılaştırma için en az 90 dakika gerekir; yüksek tempo tek başına etkinlik veya neden göstermez.</p>
              </div>
              <h4 className="text-xs font-semibold text-text-secondary mb-2">{activeTab.title}</h4>
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
                        <h5 className="text-xs font-semibold text-text-primary">{label}</h5>
                        <span className="text-xs tabular-nums text-text-muted">{formatNumber(state?.minutes || 0)} dk</span>
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
                              <p className="text-xs font-semibold text-text-secondary">{metricLabel} / 90 dk</p>
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
              <p className="text-xs font-semibold text-text-secondary mb-1">Takım yorumu</p>
              <p className="text-xs leading-5 text-text-secondary">{teamComment()}</p>
              {tacticalProfile.matches < LOW_SAMPLE_MATCHES && (
                <p className="text-xs leading-4 text-status-warning mt-2">
                  Seçili dönemde yalnızca {tacticalProfile.matches} maç var; karşılaştırmalar değişken olabilir.
                </p>
              )}
              <p className="text-xs leading-4 text-text-secondary mt-2">
                {activeTab.explanation} “Lig p80”, değerin lig takımlarının yaklaşık %80’inden yüksek olduğu yüzdelik dilimi anlatır. Yüksek yüzdelik her metrikte daha iyi performans demek değildir.
                {activeTacticalTab === 'defense' && ' PPDA yalnızca takım ve lig verisi en az %80 kapsandığında hesaplanır. PPDA yüzdeliği ham değerin sırasıdır; düşük PPDA daha yoğun pres anlamına gelir.'}
              </p>
            </div>
            <h4 className="text-xs font-semibold text-text-secondary mb-2">{activeTab.title}</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3">
              {activeTacticalTab === 'general' && tacticalProfile.formations?.length > 0 && (
                <div className="rounded border border-border bg-background-primary p-4 transition-colors hover:border-card-border-hover">
                  <p className="text-xs font-semibold leading-4 text-text-secondary">Kullanılan diziliş</p>
                  <ul className="mt-3 space-y-1.5">
                    {tacticalProfile.formations.map(item => (
                      <li key={item.formation} className="flex items-baseline justify-between gap-2">
                        <span className="text-2xl font-semibold leading-none tracking-tight tabular-nums text-text-primary">{item.formation}</span>
                        <span className="text-xs text-text-secondary tabular-nums">{item.matches}/{tacticalProfile.matches} maç</span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-xs leading-4 text-text-muted">Maça başlanan diziliş; maç içi değişiklikleri göstermez.</p>
                </div>
              )}
              {activeTab.keys.map(key => (
                <TeamTacticalMetric key={key} metric={tacticalProfile.metrics?.[key]} totalMatches={tacticalProfile.matches} />
              ))}
            </div>
            {activeTacticalTab === 'attack' && (
              <section className="mt-6 border-t border-border pt-5" aria-labelledby="team-attacking-leaders-title">
                <div className="mb-3">
                  <h4 id="team-attacking-leaders-title" className="text-sm font-semibold text-text-primary">Ofansif reytingde öne çıkan 3 oyuncu</h4>
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
                              <p className="truncate text-xs font-semibold text-text-primary" title={player.name}>{player.name}</p>
                              <p className="mt-0.5 text-xs text-text-secondary">{getPositionLabel(player.position)} · {player.appearances} maç · {formatNumber(player.minutes)} dk</p>
                            </div>
                            <div className="text-right">
                              <p className="text-xs font-semibold text-text-muted">Reyting /100</p>
                              <p className="text-xl font-semibold tabular-nums text-text-primary">{formatNumber(player.rating)}</p>
                            </div>
                          </div>
                          <div className="mt-4 grid grid-cols-4 divide-x divide-border border-t border-border-light pt-3">
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
