import { TrendingUp } from 'lucide-react';
import EmptyState from '../common/EmptyState';
import Skeleton from '../common/Skeleton';

export default function MatchOddsTab({ loadingOdds, oddsData, selectedBookmaker, setSelectedBookmaker, homeTeam, awayTeam }) {
  return (
    <div className="space-y-4 max-w-2xl mx-auto py-2">
                  {loadingOdds ? (
                    <div className="space-y-3" role="status" aria-label="Yükleniyor">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-24 w-full" />
                    <Skeleton className="h-24 w-full" />
                  </div>
                  ) : oddsData.length === 0 ? (
                    <EmptyState icon={TrendingUp}>Bu karşılaşma için kaydedilmiş bahis piyasası oranı bulunmuyor. Oranlar şu anda 2026/27 sezonunda tamamlanan maçlar için aktiftir.</EmptyState>
                  ) : (
                    <>
                  {/* Bookmaker Selector Tabs */}
                  <div className="flex items-center gap-1.5 p-1 bg-background-tertiary rounded border border-border overflow-x-auto">
                    {oddsData.map((bm) => (
                      <button
                        key={bm.bookmaker}
                        onClick={() => setSelectedBookmaker(bm.bookmaker)}
                        className={`flex-1 min-w-24 py-1.5 px-3 text-xs font-semibold rounded transition-all text-center ${
                          selectedBookmaker === bm.bookmaker
                            ? 'bg-background-primary text-text-primary  border border-border'
                            : 'text-text-secondary hover:text-text-primary'
                        }`}
                      >
                        {bm.bookmaker}
                      </button>
                    ))}
                  </div>

                  {(() => {
                    const currentBm = oddsData.find(b => b.bookmaker === selectedBookmaker) || oddsData[0];
                    if (!currentBm) return null;

                    return (
                      <div className="space-y-3">
                        {/* 1X2 Kapanış Oranları */}
                        <div className="bg-background-primary border border-border rounded p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
                            <span className="font-semibold text-text-primary">1X2 Maç Sonucu (Kapanış Oranları)</span>
                            <span className="font-semibold text-text-secondary bg-background-tertiary px-2 py-0.5 rounded">
                              {currentBm.bookmaker}
                            </span>
                          </div>

                          <div className="grid grid-cols-3 gap-3 pt-1 text-center">
                            <div className="bg-background-tertiary p-3 rounded">
                              <span className="text-xs font-semibold text-text-secondary truncate block">{homeTeam.name}</span>
                              <div className="text-2xl font-semibold tabular-nums text-text-primary my-1">
                                {currentBm.home_last_seen ? currentBm.home_last_seen.toFixed(2) : '-'}
                              </div>
                              <span className="text-xs text-text-tertiary">1 (Ev Sahibi)</span>
                              {currentBm.home_open && (
                                <span className="text-xs text-text-tertiary block mt-0.5">Açılış: {currentBm.home_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-background-tertiary p-3 rounded">
                              <span className="text-xs font-semibold text-text-secondary block">Beraberlik</span>
                              <div className="text-2xl font-semibold tabular-nums text-text-primary my-1">
                                {currentBm.draw_last_seen ? currentBm.draw_last_seen.toFixed(2) : '-'}
                              </div>
                              <span className="text-xs text-text-tertiary">X (Eşitlik)</span>
                              {currentBm.draw_open && (
                                <span className="text-xs text-text-tertiary block mt-0.5">Açılış: {currentBm.draw_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-background-tertiary p-3 rounded">
                              <span className="text-xs font-semibold text-text-secondary truncate block">{awayTeam.name}</span>
                              <div className="text-2xl font-semibold tabular-nums text-text-primary my-1">
                                {currentBm.away_last_seen ? currentBm.away_last_seen.toFixed(2) : '-'}
                              </div>
                              <span className="text-xs text-text-tertiary">2 (Deplasman)</span>
                              {currentBm.away_open && (
                                <span className="text-xs text-text-tertiary block mt-0.5">Açılış: {currentBm.away_open.toFixed(2)}</span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Gol & KG Piyasaları */}
                        <div className="bg-background-primary border border-border rounded p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
                            <span className="font-semibold text-text-primary">Gol & Karşılıklı Skor Oranları</span>
                            <span className="text-xs text-text-secondary">Piyasa Kapanışı</span>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-center">
                            <div className="bg-background-tertiary p-2.5 rounded">
                              <span className="text-xs text-text-secondary block">2.5 Gol Üst</span>
                              <strong className="text-lg font-semibold tabular-nums text-text-primary">
                                {currentBm.over_25_last_seen ? currentBm.over_25_last_seen.toFixed(2) : '-'}
                              </strong>
                              {currentBm.over_25_open && (
                                <span className="text-xs text-text-tertiary block">Açılış: {currentBm.over_25_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-background-tertiary p-2.5 rounded">
                              <span className="text-xs text-text-secondary block">2.5 Gol Alt</span>
                              <strong className="text-lg font-semibold tabular-nums text-text-primary">
                                {currentBm.under_25_last_seen ? currentBm.under_25_last_seen.toFixed(2) : '-'}
                              </strong>
                              {currentBm.under_25_open && (
                                <span className="text-xs text-text-tertiary block">Açılış: {currentBm.under_25_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-background-tertiary p-2.5 rounded">
                              <span className="text-xs text-text-secondary block">KG Var (Evet)</span>
                              <strong className="text-lg font-semibold tabular-nums text-text-primary">
                                {currentBm.btts_yes_last_seen ? currentBm.btts_yes_last_seen.toFixed(2) : '-'}
                              </strong>
                              {currentBm.btts_yes_open && (
                                <span className="text-xs text-text-tertiary block">Açılış: {currentBm.btts_yes_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-background-tertiary p-2.5 rounded">
                              <span className="text-xs text-text-secondary block">KG Yok (Hayır)</span>
                              <strong className="text-lg font-semibold tabular-nums text-text-primary">
                                {currentBm.btts_no_last_seen ? currentBm.btts_no_last_seen.toFixed(2) : '-'}
                              </strong>
                              {currentBm.btts_no_open && (
                                <span className="text-xs text-text-tertiary block">Açılış: {currentBm.btts_no_open.toFixed(2)}</span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Korner & Kart Piyasaları (Varsa) */}
                        {(currentBm.corners_over_last_seen || currentBm.cards_over_last_seen) && (
                          <div className="bg-background-primary border border-border rounded p-4 space-y-3">
                            <div className="flex items-center justify-between pb-2 border-b border-border text-xs">
                              <span className="font-semibold text-text-primary">Özel Bahis Pazarları (Korner & Kart)</span>
                              <span className="text-xs text-text-secondary">Piyasa Çizgileri</span>
                            </div>

                            <div className="grid grid-cols-2 gap-3 pt-1">
                              {currentBm.corners_over_last_seen && (
                                <div className="bg-background-tertiary p-3 rounded flex items-center justify-between">
                                  <div>
                                    <span className="text-xs font-semibold text-text-primary block">9.5 Korner</span>
                                    <span className="text-xs text-text-secondary">Kapanış Çizgisi</span>
                                  </div>
                                  <div className="text-right">
                                    <span className="text-xs tabular-nums font-semibold text-text-primary block">Üst: {currentBm.corners_over_last_seen.toFixed(2)}</span>
                                    {currentBm.corners_under_last_seen && (
                                      <span className="text-xs tabular-nums text-text-secondary block">Alt: {currentBm.corners_under_last_seen.toFixed(2)}</span>
                                    )}
                                  </div>
                                </div>
                              )}

                              {currentBm.cards_over_last_seen && (
                                <div className="bg-background-tertiary p-3 rounded flex items-center justify-between">
                                  <div>
                                    <span className="text-xs font-semibold text-text-primary block">4.5 Kart</span>
                                    <span className="text-xs text-text-secondary">Disiplin Pazarı</span>
                                  </div>
                                  <div className="text-right">
                                    <span className="text-xs tabular-nums font-semibold text-text-primary block">Üst: {currentBm.cards_over_last_seen.toFixed(2)}</span>
                                    {currentBm.cards_under_last_seen && (
                                      <span className="text-xs tabular-nums text-text-secondary block">Alt: {currentBm.cards_under_last_seen.toFixed(2)}</span>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Tüm Bahis Şirketleri Karşılaştırma Tablosu */}
                        <div className="bg-background-primary border border-border rounded overflow-hidden mt-3">
                          <div className="px-4 py-2.5 bg-background-tertiary border-b border-border text-xs font-semibold text-text-primary flex items-center justify-between">
                            <span>Tüm Sağlayıcıların Kapanış Oranları</span>
                            <span className="text-xs font-normal text-text-secondary">{oddsData.length} Sağlayıcı</span>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-xs text-left">
                              <thead className="bg-background-tertiary text-xs text-text-secondary border-b border-border-light">
                                <tr>
                                  <th className="py-2 px-3 font-semibold">Bahis Şirketi</th>
                                  <th className="py-2 px-3 font-semibold text-center">1 (Ev)</th>
                                  <th className="py-2 px-3 font-semibold text-center">X (Eşitlik)</th>
                                  <th className="py-2 px-3 font-semibold text-center">2 (Deplasman)</th>
                                  <th className="py-2 px-3 font-semibold text-center">2.5 Üst</th>
                                  <th className="py-2 px-3 font-semibold text-center">KG Var</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-border-light tabular-nums">
                                {oddsData.map(b => (
                                  <tr key={b.bookmaker} className={b.bookmaker === selectedBookmaker ? 'bg-background-tertiary font-semibold' : 'hover:bg-background-tertiary'}>
                                    <td className="py-2 px-3 font-sans font-medium text-text-primary">{b.bookmaker}</td>
                                    <td className="py-2 px-3 text-center text-text-primary">{b.home_last_seen ? b.home_last_seen.toFixed(2) : '-'}</td>
                                    <td className="py-2 px-3 text-center text-text-primary">{b.draw_last_seen ? b.draw_last_seen.toFixed(2) : '-'}</td>
                                    <td className="py-2 px-3 text-center text-text-primary">{b.away_last_seen ? b.away_last_seen.toFixed(2) : '-'}</td>
                                    <td className="py-2 px-3 text-center text-text-primary">{b.over_25_last_seen ? b.over_25_last_seen.toFixed(2) : '-'}</td>
                                    <td className="py-2 px-3 text-center text-text-primary">{b.btts_yes_last_seen ? b.btts_yes_last_seen.toFixed(2) : '-'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>

                      </div>
                    );
                  })()}
                    </>
                  )}
                </div>
  );
}
