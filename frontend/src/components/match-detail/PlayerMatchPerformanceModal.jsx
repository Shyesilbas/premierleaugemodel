import { Activity, AlertCircle, Clock, Flame, ShieldCheck, Star, X } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import PlayerAvatar from '../PlayerAvatar';
import { RedCardIcon, YellowCardIcon } from './eventIcons';

export default function PlayerMatchPerformanceModal({
  selectedPlayerModal,
  onClose,
  modalTab,
  setModalTab,
  formatPosition,
  getPositionBadgeClass,
}) {
  if (!selectedPlayerModal) return null;

  const p = selectedPlayerModal.player;
  const s = selectedPlayerModal.stats;
  const team = selectedPlayerModal.team;
  const pos = p.position || s.position || 'M';
  const posUpper = String(pos).toUpperCase();
  const isGK = ['G', 'GK'].includes(posUpper);
  const isDEF = ['D', 'DEF', 'CB', 'LB', 'RB', 'LWB', 'RWB'].includes(posUpper);
  const isMID = ['M', 'MID', 'CM', 'DM', 'AM', 'LM', 'RM'].includes(posUpper);
  const rating = s.rating != null ? Number(s.rating) : (p.rating != null ? Number(p.rating) : null);
  const attRating = s.attack_rating != null ? Number(s.attack_rating) : null;
  const defRating = s.defense_rating != null ? Number(s.defense_rating) : null;
  const shotsTotal = Number(s.shots || 0);
  const shotsOnTarget = Number(s.shots_ontarget || 0);
  const shotAccPct = shotsTotal > 0 ? Math.round((shotsOnTarget / shotsTotal) * 100) : 0;

return (
  <div 
    className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-950/75 backdrop-blur-md animate-fadeIn"
    onClick={() => onClose()}
  >
    <div 
      className="bg-white border border-slate-200 rounded-3xl max-w-xl w-full shadow-2xl overflow-hidden relative animate-scaleUp flex flex-col max-h-[92vh]"
      onClick={e => e.stopPropagation()}
    >
      {/* Modal Premium Header */}
      <div className="p-5 sm:p-6 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-900 text-white relative shrink-0">
        <button
          onClick={() => onClose()}
          className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white transition-colors cursor-pointer z-10"
          title="Kapat"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3.5 sm:gap-4 min-w-0">
            <div className="relative shrink-0">
              <PlayerAvatar 
                photoUrl={p.photo_url}
                name={p.name}
                shirt={p.shirt}
                fallback="initials"
                size="w-16 h-16 sm:w-18 sm:h-18 text-xl"
                className="border-2 border-white/20 bg-slate-800 shadow-lg"
              />
              {p.captain && (
                <span className="absolute -bottom-1 -right-1 px-1.5 py-0.5 rounded-full bg-amber-400 text-slate-950 font-black text-[9px] border border-slate-900 shadow-xs">
                  C
                </span>
              )}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono font-bold text-slate-400">
                  #{p.shirt || '-'}
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getPositionBadgeClass(p.position)}`}>
                  {formatPosition(p.position)}
                </span>
                {p.captain && (
                  <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-amber-400/20 text-amber-300 border border-amber-400/30">
                    KAPTAN
                  </span>
                )}
              </div>
              <h3 className="text-lg sm:text-xl font-black text-white truncate mt-1">
                {p.name}
              </h3>
              <div className="flex items-center gap-1.5 text-xs text-slate-300 mt-1">
                <img src={team.badge} alt="" className="w-4 h-4 object-contain" onError={handleTeamBadgeError} />
                <span className="font-medium truncate">{team.name}</span>
              </div>
            </div>
          </div>

          {/* Hero Match Rating Box */}
          <div className="shrink-0 text-right">
            <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 mb-1">
              Maç Reytingi
            </div>
            <div className={`inline-flex flex-col items-center justify-center min-w-[62px] px-3 py-1.5 rounded-2xl border font-mono shadow-md ${
              rating == null
                ? 'bg-slate-800/80 border-slate-700 text-slate-400'
                : rating >= 8.5
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                : rating >= 7.5
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                : rating >= 6.8
                ? 'bg-teal-500/15 border-teal-500/40 text-teal-300'
                : rating >= 6.0
                ? 'bg-sky-500/15 border-sky-500/40 text-sky-300'
                : rating >= 5.0
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-300'
                : 'bg-rose-500/20 border-rose-500/40 text-rose-300'
            }`}>
              <span className="text-2xl sm:text-3xl font-black leading-none">
                {rating != null ? rating.toFixed(1) : '—'}
              </span>
              <span className="text-[9px] text-slate-400 font-sans font-medium mt-0.5">
                {rating != null ? '/ 10' : 'Değerlendirilmedi'}
              </span>
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${s.is_starter ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            <span className="font-semibold text-slate-200">
              {s.is_starter ? 'İlk 11 Başlangıç' : 'Yedek (Sonradan Girdi)'}
            </span>
          </div>
          <div className="flex items-center gap-1.5 font-mono text-white bg-white/10 px-2.5 py-0.5 rounded-lg text-xs font-bold">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>{s.minutes || 0}' dk süre</span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation (Genel / Hücum / Savunma) */}
      <div className="px-5 pt-3 pb-2 bg-slate-50 border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-1.5 p-1 bg-slate-200/70 rounded-xl">
          <button
            onClick={() => setModalTab('general')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              modalTab === 'general'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-[#38003c]" />
            <span>Genel</span>
          </button>
          <button
            onClick={() => setModalTab('attack')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              modalTab === 'attack'
                ? 'bg-white text-rose-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Flame className="w-3.5 h-3.5 text-rose-500" />
            <span>Hücum</span>
          </button>
          <button
            onClick={() => setModalTab('defense')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              modalTab === 'defense'
                ? 'bg-white text-sky-700 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-sky-600" />
            <span>Savunma</span>
          </button>
        </div>
      </div>

      {/* Modal Body (Scrollable) */}
      <div className="p-5 sm:p-6 overflow-y-auto space-y-4 flex-1">
        {modalTab === 'general' && (
          <div className="space-y-4">
            {/* Position-Aware Spotlight Header */}
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                Öne Çıkan Metrikler ({formatPosition(p.position)})
              </span>
              <span className="text-[10px] text-slate-400 font-medium">Pozisyona Göre Ağırlıklı</span>
            </div>

            {/* Spotlight Grid Customized by Position */}
            <div className="grid grid-cols-2 gap-3">
              {isGK ? (
                <>
                  <div className={`p-3.5 rounded-2xl border ${Number(s.saves) > 0 ? 'bg-emerald-50/80 border-emerald-300' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Kurtarış Sayısı</span>
                    <div className="text-2xl font-black font-mono mt-0.5 text-emerald-800 flex items-baseline gap-1">
                      <span>{s.saves || 0}</span>
                      <span className="text-xs font-medium text-emerald-600">kurtarış</span>
                    </div>
                  </div>
                  <div className={`p-3.5 rounded-2xl border ${Number(s.opp_score) === 0 ? 'bg-sky-50/80 border-sky-300' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Kalesini Kapatma</span>
                    <div className="text-base font-black font-mono mt-1 text-slate-900">
                      {Number(s.opp_score) === 0 ? 'Gol Yemedi ✅' : `${s.opp_score} Gol Yedi`}
                    </div>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Penaltı Durumu</span>
                    <div className="text-sm font-bold text-slate-800 mt-1">
                      {Number(s.penalties_conceded) > 0 ? `${s.penalties_conceded} Penaltı Yaptırdı ⚠️` : 'Penaltı Hatası Yok'}
                    </div>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Disiplin</span>
                    <div className="text-sm font-bold text-slate-800 mt-1 flex items-center gap-2">
                      <span>{s.yellow_cards || 0} Sarı</span>
                      <span>·</span>
                      <span>{s.red_cards || 0} Kırmızı</span>
                    </div>
                  </div>
                </>
              ) : isDEF ? (
                <>
                  <div className={`p-3.5 rounded-2xl border ${Number(s.opp_score) === 0 ? 'bg-emerald-50/80 border-emerald-300' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Savunma / Clean Sheet</span>
                    <div className="text-base font-black font-mono mt-1 text-slate-900">
                      {Number(s.opp_score) === 0 ? 'Clean Sheet ✅' : `${s.opp_score} Gol Yenildi`}
                    </div>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">İkili Mücadele</span>
                    <div className="text-sm font-bold text-slate-800 mt-1">
                      {s.fouls_won || 0} Faul Kazandı / {s.fouls_committed || 0} Faul
                    </div>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Penaltı Hatası</span>
                    <div className="text-sm font-bold text-slate-800 mt-1">
                      {Number(s.penalties_conceded) > 0 ? `${s.penalties_conceded} Penaltı Yaptırdı ⚠️` : 'Penaltı Hatası Yok'}
                    </div>
                  </div>
                  <div className={`p-3.5 rounded-2xl border ${(Number(s.goals) > 0 || Number(s.assists) > 0) ? 'bg-purple-50/80 border-purple-300' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Hücuma Katkı</span>
                    <div className="text-sm font-bold text-slate-800 mt-1">
                      {s.goals || 0} Gol · {s.assists || 0} Asist
                    </div>
                  </div>
                </>
              ) : isMID ? (
                <>
                  <div className={`p-3.5 rounded-2xl border ${Number(s.assists) > 0 ? 'bg-purple-50/80 border-purple-300' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Asist & Şans Yaratma</span>
                    <div className="text-2xl font-black font-mono mt-0.5 text-purple-900">
                      {s.assists || 0}
                    </div>
                  </div>
                  <div className={`p-3.5 rounded-2xl border ${Number(s.goals) > 0 ? 'bg-emerald-50/80 border-emerald-300' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Gol Katkısı</span>
                    <div className="text-2xl font-black font-mono mt-0.5 text-emerald-900">
                      {s.goals || 0}
                    </div>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Şut Tehdidi</span>
                    <div className="text-sm font-bold text-slate-800 mt-1">
                      {s.shots || 0} Şut ({s.shots_ontarget || 0} İsabetli)
                    </div>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Orta Saha Mücadelesi</span>
                    <div className="text-sm font-bold text-slate-800 mt-1">
                      {s.fouls_won || 0} Kazanılan / {s.fouls_committed || 0} Faul
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className={`p-3.5 rounded-2xl border ${Number(s.goals) > 0 ? 'bg-emerald-50/80 border-emerald-300' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Gol</span>
                    <div className="text-2xl font-black font-mono mt-0.5 text-emerald-900">
                      {s.goals || 0}
                    </div>
                  </div>
                  <div className={`p-3.5 rounded-2xl border ${Number(s.assists) > 0 ? 'bg-purple-50/80 border-purple-300' : 'bg-slate-50 border-slate-200'}`}>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Asist</span>
                    <div className="text-2xl font-black font-mono mt-0.5 text-purple-900">
                      {s.assists || 0}
                    </div>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">İsabetli Şut</span>
                    <div className="text-sm font-bold text-slate-800 mt-1">
                      {s.shots_ontarget || 0} / {s.shots || 0} (%{shotAccPct} İsabet)
                    </div>
                  </div>
                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Ofsayt & Penaltı</span>
                    <div className="text-sm font-bold text-slate-800 mt-1">
                      {s.offsides || 0} Ofsayt {Number(s.penalties_won) > 0 ? `· ${s.penalties_won} Pen. Kazandı` : ''}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Match Decisive Moments Badges */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 block">
                Karşılaşmadaki Önemli Olaylar
              </span>
              <div className="flex flex-wrap gap-2">
                {Number(s.goals) > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-emerald-100 text-emerald-900 font-bold text-xs border border-emerald-300">
                    ⚽ {s.goals} Gol Attı
                  </span>
                )}
                {Number(s.assists) > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-purple-100 text-purple-900 font-bold text-xs border border-purple-300">
                    🎯 {s.assists} Asist Yaptı
                  </span>
                )}
                {Number(s.saves) > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-amber-100 text-amber-900 font-bold text-xs border border-amber-300">
                    🧤 {s.saves} Kurtarış
                  </span>
                )}
                {Number(s.penalties_won) > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-emerald-100 text-emerald-900 font-bold text-xs border border-emerald-300">
                    ⭐ {s.penalties_won} Penaltı Kazandırdı
                  </span>
                )}
                {Number(s.penalties_conceded) > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-rose-100 text-rose-900 font-bold text-xs border border-rose-300">
                    ⚠️ {s.penalties_conceded} Penaltı Yaptırdı
                  </span>
                )}
                {Number(s.penalties_missed) > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-rose-100 text-rose-900 font-bold text-xs border border-rose-300">
                    ❌ {s.penalties_missed} Penaltı Kaçırdı
                  </span>
                )}
                {Number(s.red_cards) > 0 && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-rose-600 text-white font-bold text-xs">
                    <RedCardIcon /> Kırmızı Kart Gördü
                  </span>
                )}
                {Number(s.yellow_cards) > 0 && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-amber-100 text-amber-900 font-bold text-xs border border-amber-300">
                    <YellowCardIcon /> {s.yellow_cards} Sarı Kart
                  </span>
                )}
                {Number(s.opp_score) === 0 && Number(s.minutes) >= 60 && (isGK || isDEF) && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-sky-100 text-sky-900 font-bold text-xs border border-sky-300">
                    🛡️ Clean Sheet Başarısı
                  </span>
                )}
                {!(Number(s.goals) > 0 || Number(s.assists) > 0 || Number(s.saves) > 0 || Number(s.yellow_cards) > 0 || Number(s.red_cards) > 0 || Number(s.penalties_won) > 0 || Number(s.penalties_conceded) > 0 || Number(s.penalties_missed) > 0) && (
                  <span className="text-xs text-slate-500 italic">
                    Belirleyici kart veya skor aksiyonu kaydedilmedi.
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {modalTab === 'attack' && (
          <div className="space-y-4">
            {/* Attack Rating Banner */}
            <div className="p-3.5 rounded-2xl bg-gradient-to-r from-purple-50 to-rose-50 border border-purple-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-rose-600" />
                <span className="text-xs font-bold text-purple-950">Hücum Katkı Skoru</span>
              </div>
              <span className="text-base font-black font-mono text-purple-950">
                {attRating != null ? attRating.toFixed(1) : (rating != null ? rating.toFixed(1) : '—')} / 10
              </span>
            </div>

            {/* Attacking Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className={`p-3 rounded-2xl border text-center ${Number(s.goals) > 0 ? 'bg-emerald-50 border-emerald-300' : 'bg-slate-50 border-slate-200'}`}>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Gol</span>
                <div className={`text-2xl font-black font-mono mt-1 ${Number(s.goals) > 0 ? 'text-emerald-700' : 'text-slate-900'}`}>
                  {s.goals || 0}
                </div>
              </div>

              <div className={`p-3 rounded-2xl border text-center ${Number(s.assists) > 0 ? 'bg-purple-50 border-purple-300' : 'bg-slate-50 border-slate-200'}`}>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Asist</span>
                <div className={`text-2xl font-black font-mono mt-1 ${Number(s.assists) > 0 ? 'text-purple-700' : 'text-slate-900'}`}>
                  {s.assists || 0}
                </div>
              </div>

              <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Toplam Şut</span>
                <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                  {shotsTotal}
                </div>
              </div>

              <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">İsabetli Şut</span>
                <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                  {shotsOnTarget}
                  <span className="text-xs font-normal text-slate-500 ml-1">
                    (%{shotAccPct})
                  </span>
                </div>
              </div>

              <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Kazanılan Penaltı</span>
                <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                  {s.penalties_won || 0}
                </div>
              </div>

              <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Ofsayt</span>
                <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                  {s.offsides || 0}
                </div>
              </div>
            </div>

            {Number(s.penalties_missed) > 0 && (
              <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span>Bu maçta kaçırılan penaltı vuruşu bulunmaktadır (-1.15 reyting cezası).</span>
              </div>
            )}
          </div>
        )}

        {modalTab === 'defense' && (
          <div className="space-y-4">
            {/* Defense Rating Banner */}
            <div className="p-3.5 rounded-2xl bg-gradient-to-r from-sky-50 to-slate-50 border border-sky-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-sky-600" />
                <span className="text-xs font-bold text-sky-950">Savunma Katkı Skoru</span>
              </div>
              <span className="text-base font-black font-mono text-sky-950">
                {defRating != null ? defRating.toFixed(1) : (rating != null ? rating.toFixed(1) : '—')} / 10
              </span>
            </div>

            {/* Defense Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className={`p-3 rounded-2xl border text-center ${Number(s.saves) > 0 ? 'bg-amber-50 border-amber-300' : 'bg-slate-50 border-slate-200'}`}>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Kurtarış (GK)</span>
                <div className={`text-2xl font-black font-mono mt-1 ${Number(s.saves) > 0 ? 'text-amber-800' : 'text-slate-900'}`}>
                  {s.saves || 0}
                </div>
              </div>

              <div className={`p-3 rounded-2xl border text-center ${Number(s.opp_score) === 0 ? 'bg-emerald-50 border-emerald-300' : 'bg-slate-50 border-slate-200'}`}>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Yenen Gol</span>
                <div className={`text-2xl font-black font-mono mt-1 ${Number(s.opp_score) === 0 ? 'text-emerald-700' : 'text-slate-900'}`}>
                  {s.opp_score || 0}
                </div>
              </div>

              <div className={`p-3 rounded-2xl border text-center ${Number(s.penalties_conceded) > 0 ? 'bg-rose-50 border-rose-300' : 'bg-slate-50 border-slate-200'}`}>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Penaltı Yaptırdı</span>
                <div className={`text-2xl font-black font-mono mt-1 ${Number(s.penalties_conceded) > 0 ? 'text-rose-700' : 'text-slate-900'}`}>
                  {s.penalties_conceded || 0}
                </div>
              </div>

              <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Faul Yaptı</span>
                <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                  {s.fouls_committed || 0}
                </div>
              </div>

              <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Faul Kazandı</span>
                <div className="text-2xl font-black font-mono text-slate-900 mt-1">
                  {s.fouls_won || 0}
                </div>
              </div>

              <div className="p-3 rounded-2xl border border-slate-200 bg-slate-50 text-center">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">Disiplin Kartları</span>
                <div className="text-lg font-black font-mono text-slate-900 mt-2 flex items-center justify-center gap-2">
                  <span className="flex items-center gap-1 text-xs font-bold text-amber-700">
                    <YellowCardIcon /> {s.yellow_cards || 0}
                  </span>
                  <span className="flex items-center gap-1 text-xs font-bold text-rose-700">
                    <RedCardIcon /> {s.red_cards || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal Footer */}
      <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-between shrink-0">
        <span className="text-xs text-slate-500">
          {team.name} · Premier League
        </span>
        <button
          onClick={() => onClose()}
          className="px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs transition-colors cursor-pointer shadow-xs"
        >
          Kapat
        </button>
      </div>
    </div>
  </div>
);
 
}
