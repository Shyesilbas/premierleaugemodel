import { BarChart3, Bot, CheckCircle2, ChevronRight, Flag, Layers, ShieldAlert, Trophy, XCircle, Zap } from 'lucide-react';
import { handleImageFallback } from '../../utils/imageFallbacks';
import { getTeam } from '../../data/teams';

export default function AuditMatchCard({ match: m, onSelectMatch }) {
  const homeT = getTeam(m.home_id, m.home_name);
  const awayT = getTeam(m.away_id, m.away_name);
  const modelOverPick = m.prob_over_25 >= 50.0 ? '2.5 ÜST' : '2.5 ALT';
  const modelOverProb = m.prob_over_25 >= 50.0 ? m.prob_over_25 : (100 - m.prob_over_25).toFixed(1);
  const actualTotalGoals = m.home_score + m.away_score;
  const actualOverResult = actualTotalGoals > 2.5 ? 'Üst' : 'Alt';
  const bttsThreshold = m.btts_threshold || 56.6;
  const modelBttsPick = m.prob_btts >= bttsThreshold ? 'KG VAR' : 'KG YOK';
  const modelBttsProb = m.prob_btts >= bttsThreshold ? m.prob_btts : (100 - m.prob_btts).toFixed(1);
  const actualBttsResult = m.home_score > 0 && m.away_score > 0 ? 'KG Var' : 'KG Yok';

  const handleCardClick = () => {
    onSelectMatch?.({
      ...m,
      id: m.match_id,
      match_id: m.match_id,
      home_id: m.home_id,
      away_id: m.away_id,
      status: 'COMPLETED',
      is_played: true,
    }, m.gameweek);
  };

  return (
<div 
  className="bg-white rounded-2xl border border-slate-200 p-4 sm:p-5 shadow-xs hover:border-purple-300 transition-all space-y-3 cursor-pointer group"
  onClick={handleCardClick}
>
  {/* Header: GW, Date & Result Badges */}
  <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-100 text-xs">
    <div className="flex items-center gap-2">
      <span className="font-bold text-[#38003c] bg-purple-50 px-2 py-0.5 rounded-md text-[11px]">
        Hafta {m.gameweek}
      </span>
      <span className="text-slate-400">•</span>
      <span className="text-slate-500 font-medium">{m.match_date}</span>
    </div>

    <div className="flex items-center gap-1.5">
      {m.confidence_tier === 'high' && (
        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-900 border border-emerald-300">
          Net Favori
        </span>
      )}

      {m.is_balanced && (
        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-amber-100 text-amber-900 border border-amber-300">
          Dengeli Maç
        </span>
      )}

      {m.highest_edge_side && (
        <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-purple-100 text-purple-900 border border-purple-200 flex items-center gap-1">
          <Zap className="w-3 h-3 text-amber-500" />
          +{m.edge_pct}% Edge ({m.highest_edge_side === 'home' ? m.home_name : (m.highest_edge_side === 'away' ? m.away_name : 'Beraberlik')})
        </span>
      )}

      {m.hit_1x2 ? (
        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          1X2 Tuttu
        </span>
      ) : (
        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-50 text-rose-800 border border-rose-200 flex items-center gap-1">
          <XCircle className="w-3.5 h-3.5 text-rose-600" />
          1X2 Yanıldı
        </span>
      )}
    </div>
  </div>

  {/* Score Line */}
  <div className="flex items-center justify-between py-1">
    {/* Home */}
    <div className="flex items-center gap-2.5 flex-1 min-w-0">
      <img 
        src={homeT.badge} 
        alt={m.home_name} 
        className="w-7 h-7 sm:w-8 sm:h-8 object-contain shrink-0" 
        onError={event => handleImageFallback(event, '/badges/premier-league.svg')}
      />
      <span className={`font-black text-sm sm:text-base truncate ${m.home_score > m.away_score ? 'text-slate-900 font-black' : 'text-slate-700'}`}>
        {m.home_name}
      </span>
    </div>

    {/* Score */}
    <div className="px-4 text-center shrink-0">
      <span className="text-xl sm:text-2xl font-black font-mono tracking-tight text-slate-900 bg-slate-100 px-3 py-1 rounded-xl group-hover:bg-purple-100 group-hover:text-purple-950 transition-colors">
        {m.score}
      </span>
    </div>

    {/* Away */}
    <div className="flex items-center justify-end gap-2.5 flex-1 min-w-0 text-right">
      <span className={`font-black text-sm sm:text-base truncate ${m.away_score > m.home_score ? 'text-slate-900 font-black' : 'text-slate-700'}`}>
        {m.away_name}
      </span>
      <img 
        src={awayT.badge} 
        alt={m.away_name} 
        className="w-7 h-7 sm:w-8 sm:h-8 object-contain shrink-0" 
        onError={event => handleImageFallback(event, '/badges/premier-league.svg')}
      />
    </div>
  </div>

  {/* XY Matrisi: Sol tarafta Prop'lar (Y-Axis), Üstte Model | Piyasa | Gerçek (X-Axis) */}
  <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs mt-3" onClick={(e) => e.stopPropagation()}>
    <table className="w-full text-left text-xs border-collapse">
      <thead>
        <tr className="bg-slate-50/90 text-slate-600 font-bold border-b border-slate-200 text-[11px]">
          <th className="py-2.5 px-3.5 w-[24%] font-semibold uppercase tracking-wider text-slate-500">
            <div className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-slate-400" />
              <span>Prop (Bahis Pazarı)</span>
            </div>
          </th>
          <th className="py-2.5 px-3.5 w-[30%] text-purple-950 bg-purple-50/60 border-x border-purple-100 font-extrabold">
            <div className="flex items-center gap-1.5">
              <Bot className="w-3.5 h-3.5 text-purple-600" />
              <span>Bizim Modelimiz (Öngörü & Adil Oran)</span>
            </div>
          </th>
          <th className="py-2.5 px-3.5 w-[22%] text-slate-800 font-extrabold border-r border-slate-200">
            <div className="flex items-center gap-1.5">
              <BarChart3 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Piyasa Oranı ({m.bookmaker || 'Bet365'})</span>
            </div>
          </th>
          <th className="py-2.5 px-3.5 w-[24%] text-slate-800 font-extrabold">
            <div className="flex items-center gap-1.5">
              <Trophy className="w-3.5 h-3.5 text-amber-500" />
              <span>Sahadaki Gerçek & Sonuç</span>
            </div>
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100 bg-white font-sans">
        
        {/* ROW 1: Kim Kazanır (1X2) */}
        <tr className="hover:bg-purple-50/20 transition-colors">
          <td className="py-3 px-3.5 align-middle">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-purple-100 text-purple-800 flex items-center justify-center font-black text-[10px] shrink-0">
                1X2
              </span>
              <div>
                <div className="font-extrabold text-slate-900 text-xs">Kim Kazanır</div>
                <span className="text-[10px] text-slate-500 block font-medium">
                  Öngörü: <strong className="text-purple-900">{m.favorite_label}</strong>
                </span>
              </div>
            </div>
          </td>
          <td className="py-3 px-3.5 bg-purple-50/20 border-x border-purple-100 align-middle">
            <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
              <div className={`p-1.5 rounded-lg border transition-all ${
                m.predicted_winner === 'home' 
                  ? 'bg-purple-100/90 border-purple-400 text-purple-950 font-bold ring-1 ring-purple-400 shadow-xs' 
                  : 'bg-white/80 border-slate-200 text-slate-700 hover:border-slate-300'
              }`}>
                <span className="text-[10px] text-slate-400 block font-sans">1 (Ev)</span>
                <strong className="text-xs">%{m.prob_home}</strong>
                <span className="text-[9px] font-bold text-purple-700 bg-purple-50 px-1 py-0.2 rounded block mt-0.5">
                  {(100 / m.prob_home).toFixed(2)}
                </span>
              </div>
              <div className={`p-1.5 rounded-lg border transition-all ${
                m.predicted_winner === 'draw' 
                  ? 'bg-purple-100/90 border-purple-400 text-purple-950 font-bold ring-1 ring-purple-400 shadow-xs' 
                  : 'bg-white/80 border-slate-200 text-slate-700 hover:border-slate-300'
              }`}>
                <span className="text-[10px] text-slate-400 block font-sans">X (Ber)</span>
                <strong className="text-xs">%{m.prob_draw}</strong>
                <span className="text-[9px] font-bold text-purple-700 bg-purple-50 px-1 py-0.2 rounded block mt-0.5">
                  {(100 / m.prob_draw).toFixed(2)}
                </span>
              </div>
              <div className={`p-1.5 rounded-lg border transition-all ${
                m.predicted_winner === 'away' 
                  ? 'bg-purple-100/90 border-purple-400 text-purple-950 font-bold ring-1 ring-purple-400 shadow-xs' 
                  : 'bg-white/80 border-slate-200 text-slate-700 hover:border-slate-300'
              }`}>
                <span className="text-[10px] text-slate-400 block font-sans">2 (Dep)</span>
                <strong className="text-xs">%{m.prob_away}</strong>
                <span className="text-[9px] font-bold text-purple-700 bg-purple-50 px-1 py-0.2 rounded block mt-0.5">
                  {(100 / m.prob_away).toFixed(2)}
                </span>
              </div>
            </div>
          </td>
          <td className="py-3 px-3.5 border-r border-slate-200 align-middle">
            <div className="grid grid-cols-3 gap-1.5 text-center font-mono">
              <div className={`p-1.5 rounded-lg border ${
                m.actual_result === 'home' 
                  ? 'bg-emerald-50 border-emerald-400 text-emerald-950 font-black ring-1 ring-emerald-300 shadow-xs' 
                  : 'bg-slate-50/70 border-slate-200 text-slate-600'
              }`}>
                <span className="text-[10px] text-slate-400 block font-sans">1 (Ev)</span>
                <strong className="text-xs font-black text-slate-900 block mt-1">
                  {m.market_home_odds ? m.market_home_odds.toFixed(2) : '-'}
                </strong>
              </div>
              <div className={`p-1.5 rounded-lg border ${
                m.actual_result === 'draw' 
                  ? 'bg-emerald-50 border-emerald-400 text-emerald-950 font-black ring-1 ring-emerald-300 shadow-xs' 
                  : 'bg-slate-50/70 border-slate-200 text-slate-600'
              }`}>
                <span className="text-[10px] text-slate-400 block font-sans">X (Ber)</span>
                <strong className="text-xs font-black text-slate-900 block mt-1">
                  {m.market_draw_odds ? m.market_draw_odds.toFixed(2) : '-'}
                </strong>
              </div>
              <div className={`p-1.5 rounded-lg border ${
                m.actual_result === 'away' 
                  ? 'bg-emerald-50 border-emerald-400 text-emerald-950 font-black ring-1 ring-emerald-300 shadow-xs' 
                  : 'bg-slate-50/70 border-slate-200 text-slate-600'
              }`}>
                <span className="text-[10px] text-slate-400 block font-sans">2 (Dep)</span>
                <strong className="text-xs font-black text-slate-900 block mt-1">
                  {m.market_away_odds ? m.market_away_odds.toFixed(2) : '-'}
                </strong>
              </div>
            </div>
          </td>
          <td className="py-3 px-3.5 align-middle">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <span className="text-xs font-bold text-slate-900 block truncate">
                  {m.actual_result === 'home' ? m.home_name : m.actual_result === 'away' ? m.away_name : 'Beraberlik'}
                </span>
                <span className="text-[11px] font-mono text-slate-500 font-semibold whitespace-nowrap block">
                  Skor: <strong className="text-slate-800">{m.score}</strong>
                </span>
              </div>
              <span className={`px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-wider shrink-0 whitespace-nowrap flex items-center gap-1 ${
                m.hit_1x2 ? 'bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300' : 'bg-rose-100 text-rose-800 ring-1 ring-rose-300'
              }`}>
                {m.hit_1x2 ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                <span>{m.hit_1x2 ? 'TUTTU' : 'YANILDI'}</span>
              </span>
            </div>
          </td>
        </tr>

        {/* ROW 2: 2.5 Gol Alt/Üst */}
        <tr className="hover:bg-purple-50/20 transition-colors">
          <td className="py-2.5 px-3.5 align-middle">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-emerald-100 text-emerald-800 flex items-center justify-center font-black text-[10px] shrink-0">
                2.5
              </span>
              <div>
                <div className="font-extrabold text-slate-900 text-xs">2.5 Gol Alt / Üst</div>
                <span className="text-[10px] text-slate-500 block font-medium">
                  Beklenen xG: <strong className="text-slate-700 font-mono">{m.expected_goals}</strong>
                </span>
              </div>
            </div>
          </td>
          <td className="py-2.5 px-3.5 bg-purple-50/20 border-x border-purple-100 align-middle">
            <div className="flex items-center justify-between bg-white/90 border border-purple-200/90 rounded-lg px-2.5 py-1.5 shadow-xs">
              <div>
                <span className="font-extrabold text-slate-900 text-xs">{modelOverPick}</span>{' '}
                <span className="text-[11px] text-purple-900 font-mono font-semibold">(%{modelOverProb})</span>
              </div>
              <div className="text-right">
                <span className="text-[9px] text-purple-600 font-sans block leading-none font-medium">Adil Oran</span>
                <strong className="text-xs font-black text-purple-900 font-mono">
                  {(100 / Number(modelOverProb)).toFixed(2)}
                </strong>
              </div>
            </div>
          </td>
          <td className="py-2.5 px-3.5 border-r border-slate-200 align-middle">
            <div className="flex items-center justify-between bg-slate-50/80 border border-slate-200 rounded-lg px-2.5 py-1.5 font-mono">
              <span className="text-[11px] text-slate-500 font-sans">2.5 Üst Kapanış:</span>
              <strong className="text-xs font-black text-slate-900">
                {m.market_over_25_odds ? m.market_over_25_odds.toFixed(2) : '-'}
              </strong>
            </div>
          </td>
          <td className="py-2.5 px-3.5 align-middle">
            <div className="flex items-center justify-between gap-2 whitespace-nowrap">
              <span className="font-bold text-slate-900 text-xs">
                {actualTotalGoals} Gol <span className="text-slate-500 font-normal">({actualOverResult})</span>
              </span>
              <span className={`px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-wider shrink-0 whitespace-nowrap flex items-center gap-1 ${
                m.hit_over_25 ? 'bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300' : 'bg-rose-100 text-rose-800 ring-1 ring-rose-300'
              }`}>
                {m.hit_over_25 ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                <span>{m.hit_over_25 ? 'TUTTU' : 'YANILDI'}</span>
              </span>
            </div>
          </td>
        </tr>

        {/* ROW 3: Karşılıklı Gol (KG) */}
        <tr className="hover:bg-purple-50/20 transition-colors">
          <td className="py-2.5 px-3.5 align-middle">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-blue-100 text-blue-800 flex items-center justify-center font-black text-[10px] shrink-0">
                KG
              </span>
              <div>
                <div className="font-extrabold text-slate-900 text-xs">Karşılıklı Gol (KG)</div>
                <span className="text-[10px] text-slate-500 block font-medium">İki Takım da Atar mı?</span>
              </div>
            </div>
          </td>
          <td className="py-2.5 px-3.5 bg-purple-50/20 border-x border-purple-100 align-middle">
            <div className="flex items-center justify-between bg-white/90 border border-purple-200/90 rounded-lg px-2.5 py-1.5 shadow-xs">
              <div>
                <span className="font-extrabold text-slate-900 text-xs">{modelBttsPick}</span>{' '}
                <span className="text-[11px] text-purple-900 font-mono font-semibold">(%{modelBttsProb})</span>
              </div>
              <div className="text-right">
                <span className="text-[9px] text-purple-600 font-sans block leading-none font-medium">Adil Oran</span>
                <strong className="text-xs font-black text-purple-900 font-mono">
                  {(100 / Number(modelBttsProb)).toFixed(2)}
                </strong>
              </div>
            </div>
          </td>
          <td className="py-2.5 px-3.5 border-r border-slate-200 align-middle">
            <div className="flex items-center justify-between bg-slate-50/80 border border-slate-200 rounded-lg px-2.5 py-1.5 font-mono">
              <span className="text-[11px] text-slate-500 font-sans">KG Var Kapanış:</span>
              <strong className="text-xs font-black text-slate-900">
                {m.market_btts_odds ? m.market_btts_odds.toFixed(2) : '-'}
              </strong>
            </div>
          </td>
          <td className="py-2.5 px-3.5 align-middle">
            <div className="flex items-center justify-between gap-2 whitespace-nowrap">
              <span className="font-bold text-slate-900 text-xs">
                {actualBttsResult}
              </span>
              <span className={`px-2 py-1 rounded-md text-[10px] font-black uppercase tracking-wider shrink-0 whitespace-nowrap flex items-center gap-1 ${
                m.hit_btts ? 'bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300' : 'bg-rose-100 text-rose-800 ring-1 ring-rose-300'
              }`}>
                {m.hit_btts ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                <span>{m.hit_btts ? 'TUTTU' : 'YANILDI'}</span>
              </span>
            </div>
          </td>
        </tr>

        {/* ROW 4: Toplam Korner */}
        <tr className="hover:bg-purple-50/20 transition-colors">
          <td className="py-2.5 px-3.5 align-middle">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-amber-100 text-amber-800 flex items-center justify-center font-black text-[10px] shrink-0">
                <Flag className="w-3.5 h-3.5" />
              </span>
              <div>
                <div className="font-extrabold text-slate-900 text-xs">Toplam Korner</div>
                <span className="text-[10px] text-slate-500 block font-medium">Model Beklentisi</span>
              </div>
            </div>
          </td>
          <td className="py-2.5 px-3.5 bg-purple-50/20 border-x border-purple-100 align-middle">
            <div className="flex items-center justify-between bg-white/90 border border-purple-200/90 rounded-lg px-2.5 py-1.5 shadow-xs">
              <span className="font-mono text-xs font-bold text-slate-900">
                {m.expected_corners} Korner
              </span>
              <span className="text-[9px] font-bold text-purple-700 bg-purple-100/80 px-1.5 py-0.5 rounded">
                Model xC
              </span>
            </div>
          </td>
          <td className="py-2.5 px-3.5 border-r border-slate-200 align-middle">
            <div className="flex items-center justify-between bg-slate-50/80 border border-slate-200 rounded-lg px-2.5 py-1.5 font-mono">
              <span className="text-[11px] text-slate-500 font-sans">Standart Çizgi:</span>
              <strong className="text-xs font-bold text-slate-800">9.5</strong>
            </div>
          </td>
          <td className="py-2.5 px-3.5 align-middle">
            <div className="flex items-center justify-between gap-2 whitespace-nowrap">
              <span className="font-mono font-bold text-slate-900 text-xs">
                {m.actual_corners ?? '-'} Korner
              </span>
              {m.corner_error !== null && (
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md font-bold whitespace-nowrap border ${
                  Math.abs(m.corner_error) <= 2 
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                  : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}>
                  {m.corner_error > 0 ? `+${m.corner_error}` : m.corner_error} sapma
                </span>
              )}
            </div>
          </td>
        </tr>

        {/* ROW 5: Toplam Kart */}
        <tr className="hover:bg-purple-50/20 transition-colors">
          <td className="py-2.5 px-3.5 align-middle">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-rose-100 text-rose-800 flex items-center justify-center font-black text-[10px] shrink-0">
                <ShieldAlert className="w-3.5 h-3.5" />
              </span>
              <div>
                <div className="font-extrabold text-slate-900 text-xs">Toplam Kart</div>
                <span className="text-[10px] text-slate-500 block font-medium">Disiplin & Agresyon</span>
              </div>
            </div>
          </td>
          <td className="py-2.5 px-3.5 bg-purple-50/20 border-x border-purple-100 align-middle">
            <div className="flex items-center justify-between bg-white/90 border border-purple-200/90 rounded-lg px-2.5 py-1.5 shadow-xs">
              <span className="font-mono text-xs font-bold text-slate-900">
                {m.expected_cards} Kart
              </span>
              <span className="text-[9px] font-bold text-purple-700 bg-purple-100/80 px-1.5 py-0.5 rounded">
                Disiplin Skoru
              </span>
            </div>
          </td>
          <td className="py-2.5 px-3.5 border-r border-slate-200 align-middle">
            <div className="flex items-center justify-between bg-slate-50/80 border border-slate-200 rounded-lg px-2.5 py-1.5 font-mono">
              <span className="text-[11px] text-slate-500 font-sans">Standart Çizgi:</span>
              <strong className="text-xs font-bold text-slate-800">3.5 / 4.5</strong>
            </div>
          </td>
          <td className="py-2.5 px-3.5 align-middle">
            <div className="flex items-center justify-between gap-2 whitespace-nowrap">
              <span className="font-mono font-bold text-slate-900 text-xs">
                {m.actual_cards ?? '-'} Kart
              </span>
              {m.card_error !== null && (
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md font-bold whitespace-nowrap border ${
                  Math.abs(m.card_error) <= 1 
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                  : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}>
                  {m.card_error > 0 ? `+${m.card_error}` : m.card_error} sapma
                </span>
              )}
            </div>
          </td>
        </tr>

      </tbody>
    </table>
  </div>

  {/* Footer Link to full match card */}
  {onSelectMatch && (
    <div className="flex justify-end pt-1">
      <button
        onClick={(e) => {
          e.stopPropagation();
          handleCardClick();
        }}
        className="text-[11px] font-bold text-[#38003c] hover:text-purple-700 flex items-center gap-1 transition-colors cursor-pointer group-hover:underline"
      >
        <span>Maç Detaylarını ve Tüm İstatistikleri Aç</span>
        <ChevronRight className="w-3.5 h-3.5" />
      </button>
    </div>
  )}

</div>
  );
}
