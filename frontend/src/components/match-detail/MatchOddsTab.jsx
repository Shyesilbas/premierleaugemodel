import { TrendingUp } from 'lucide-react';

export default function MatchOddsTab({ loadingOdds, oddsData, selectedBookmaker, setSelectedBookmaker, homeTeam, awayTeam }) {
  return (
    <div className="space-y-4 max-w-2xl mx-auto py-2">
                  {loadingOdds ? (
                    <div className="py-12 text-center">
                      <div className="w-6 h-6 border-2 border-slate-900 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                      <p className="text-xs font-semibold text-slate-700">Piyasa oranları yükleniyor...</p>
                    </div>
                  ) : oddsData.length === 0 ? (
                    <div className="py-12 text-center bg-slate-50 border border-slate-200 rounded-xl p-6">
                      <TrendingUp className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                      <p className="text-xs font-semibold text-slate-700">Bu karşılaşma için kaydedilmiş bahis piyasası oranı bulunmuyor.</p>
                      <p className="text-[11px] text-slate-500 mt-1">Oranlar şu anda 2026/27 sezonunda tamamlanan maçlar için aktiftir.</p>
                    </div>
                  ) : (
                    <>
                  {/* Bookmaker Selector Tabs */}
                  <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl border border-slate-200 overflow-x-auto">
                    {oddsData.map((bm) => (
                      <button
                        key={bm.bookmaker}
                        onClick={() => setSelectedBookmaker(bm.bookmaker)}
                        className={`flex-1 min-w-[100px] py-1.5 px-3 text-xs font-bold rounded-lg transition-all text-center ${
                          selectedBookmaker === bm.bookmaker
                            ? 'bg-white text-slate-900 shadow-xs border border-slate-200/80'
                            : 'text-slate-600 hover:text-slate-900'
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
                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                            <span className="font-bold text-slate-800">1X2 Maç Sonucu (Kapanış Oranları)</span>
                            <span className="font-semibold text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                              {currentBm.bookmaker}
                            </span>
                          </div>

                          <div className="grid grid-cols-3 gap-3 pt-1 text-center">
                            <div className="bg-white p-3 rounded-lg border border-slate-200">
                              <span className="text-xs font-semibold text-slate-600 truncate block">{homeTeam.name}</span>
                              <div className="text-2xl font-black font-mono text-slate-900 my-1">
                                {currentBm.home_last_seen ? currentBm.home_last_seen.toFixed(2) : '-'}
                              </div>
                              <span className="text-[11px] text-slate-400">1 (Ev Sahibi)</span>
                              {currentBm.home_open && (
                                <span className="text-[10px] text-slate-400 block mt-0.5">Açılış: {currentBm.home_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-white p-3 rounded-lg border border-slate-200">
                              <span className="text-xs font-semibold text-slate-600 block">Beraberlik</span>
                              <div className="text-2xl font-black font-mono text-slate-900 my-1">
                                {currentBm.draw_last_seen ? currentBm.draw_last_seen.toFixed(2) : '-'}
                              </div>
                              <span className="text-[11px] text-slate-400">X (Eşitlik)</span>
                              {currentBm.draw_open && (
                                <span className="text-[10px] text-slate-400 block mt-0.5">Açılış: {currentBm.draw_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-white p-3 rounded-lg border border-slate-200">
                              <span className="text-xs font-semibold text-slate-600 truncate block">{awayTeam.name}</span>
                              <div className="text-2xl font-black font-mono text-slate-900 my-1">
                                {currentBm.away_last_seen ? currentBm.away_last_seen.toFixed(2) : '-'}
                              </div>
                              <span className="text-[11px] text-slate-400">2 (Deplasman)</span>
                              {currentBm.away_open && (
                                <span className="text-[10px] text-slate-400 block mt-0.5">Açılış: {currentBm.away_open.toFixed(2)}</span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Gol & KG Piyasaları */}
                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                          <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                            <span className="font-bold text-slate-800">Gol & Karşılıklı Skor Oranları</span>
                            <span className="text-[11px] text-slate-500">Piyasa Kapanışı</span>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-center">
                            <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                              <span className="text-[11px] text-slate-500 block">2.5 Gol Üst</span>
                              <strong className="text-lg font-black font-mono text-slate-900">
                                {currentBm.over_25_last_seen ? currentBm.over_25_last_seen.toFixed(2) : '-'}
                              </strong>
                              {currentBm.over_25_open && (
                                <span className="text-[10px] text-slate-400 block">Açılış: {currentBm.over_25_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                              <span className="text-[11px] text-slate-500 block">2.5 Gol Alt</span>
                              <strong className="text-lg font-black font-mono text-slate-900">
                                {currentBm.under_25_last_seen ? currentBm.under_25_last_seen.toFixed(2) : '-'}
                              </strong>
                              {currentBm.under_25_open && (
                                <span className="text-[10px] text-slate-400 block">Açılış: {currentBm.under_25_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                              <span className="text-[11px] text-slate-500 block">KG Var (Evet)</span>
                              <strong className="text-lg font-black font-mono text-slate-900">
                                {currentBm.btts_yes_last_seen ? currentBm.btts_yes_last_seen.toFixed(2) : '-'}
                              </strong>
                              {currentBm.btts_yes_open && (
                                <span className="text-[10px] text-slate-400 block">Açılış: {currentBm.btts_yes_open.toFixed(2)}</span>
                              )}
                            </div>

                            <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                              <span className="text-[11px] text-slate-500 block">KG Yok (Hayır)</span>
                              <strong className="text-lg font-black font-mono text-slate-900">
                                {currentBm.btts_no_last_seen ? currentBm.btts_no_last_seen.toFixed(2) : '-'}
                              </strong>
                              {currentBm.btts_no_open && (
                                <span className="text-[10px] text-slate-400 block">Açılış: {currentBm.btts_no_open.toFixed(2)}</span>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Korner & Kart Piyasaları (Varsa) */}
                        {(currentBm.corners_over_last_seen || currentBm.cards_over_last_seen) && (
                          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                            <div className="flex items-center justify-between pb-2 border-b border-slate-200 text-xs">
                              <span className="font-bold text-slate-800">Özel Bahis Pazarları (Korner & Kart)</span>
                              <span className="text-[11px] text-slate-500">Piyasa Çizgileri</span>
                            </div>

                            <div className="grid grid-cols-2 gap-3 pt-1">
                              {currentBm.corners_over_last_seen && (
                                <div className="bg-white p-3 rounded-lg border border-slate-200 flex items-center justify-between">
                                  <div>
                                    <span className="text-xs font-bold text-slate-800 block">9.5 Korner</span>
                                    <span className="text-[11px] text-slate-500">Kapanış Çizgisi</span>
                                  </div>
                                  <div className="text-right">
                                    <span className="text-xs font-mono font-bold text-slate-900 block">Üst: {currentBm.corners_over_last_seen.toFixed(2)}</span>
                                    {currentBm.corners_under_last_seen && (
                                      <span className="text-[11px] font-mono text-slate-600 block">Alt: {currentBm.corners_under_last_seen.toFixed(2)}</span>
                                    )}
                                  </div>
                                </div>
                              )}

                              {currentBm.cards_over_last_seen && (
                                <div className="bg-white p-3 rounded-lg border border-slate-200 flex items-center justify-between">
                                  <div>
                                    <span className="text-xs font-bold text-slate-800 block">4.5 Kart</span>
                                    <span className="text-[11px] text-slate-500">Disiplin Pazarı</span>
                                  </div>
                                  <div className="text-right">
                                    <span className="text-xs font-mono font-bold text-slate-900 block">Üst: {currentBm.cards_over_last_seen.toFixed(2)}</span>
                                    {currentBm.cards_under_last_seen && (
                                      <span className="text-[11px] font-mono text-slate-600 block">Alt: {currentBm.cards_under_last_seen.toFixed(2)}</span>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Tüm Bahis Şirketleri Karşılaştırma Tablosu */}
                        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden mt-3">
                          <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-800 flex items-center justify-between">
                            <span>Tüm Sağlayıcıların Kapanış Oranları</span>
                            <span className="text-[11px] font-normal text-slate-500">{oddsData.length} Sağlayıcı</span>
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-xs text-left">
                              <thead className="bg-slate-50/50 text-[11px] text-slate-500 border-b border-slate-100">
                                <tr>
                                  <th className="py-2 px-3 font-semibold">Bahis Şirketi</th>
                                  <th className="py-2 px-3 font-semibold text-center">1 (Ev)</th>
                                  <th className="py-2 px-3 font-semibold text-center">X (Eşitlik)</th>
                                  <th className="py-2 px-3 font-semibold text-center">2 (Deplasman)</th>
                                  <th className="py-2 px-3 font-semibold text-center">2.5 Üst</th>
                                  <th className="py-2 px-3 font-semibold text-center">KG Var</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100 font-mono">
                                {oddsData.map(b => (
                                  <tr key={b.bookmaker} className={b.bookmaker === selectedBookmaker ? 'bg-purple-50/40 font-bold' : 'hover:bg-slate-50/50'}>
                                    <td className="py-2 px-3 font-sans font-medium text-slate-800">{b.bookmaker}</td>
                                    <td className="py-2 px-3 text-center text-slate-900">{b.home_last_seen ? b.home_last_seen.toFixed(2) : '-'}</td>
                                    <td className="py-2 px-3 text-center text-slate-700">{b.draw_last_seen ? b.draw_last_seen.toFixed(2) : '-'}</td>
                                    <td className="py-2 px-3 text-center text-slate-900">{b.away_last_seen ? b.away_last_seen.toFixed(2) : '-'}</td>
                                    <td className="py-2 px-3 text-center text-slate-700">{b.over_25_last_seen ? b.over_25_last_seen.toFixed(2) : '-'}</td>
                                    <td className="py-2 px-3 text-center text-slate-700">{b.btts_yes_last_seen ? b.btts_yes_last_seen.toFixed(2) : '-'}</td>
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
