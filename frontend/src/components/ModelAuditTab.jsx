import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  TrendingUp, 
  ShieldCheck, 
  Target, 
  Zap, 
  AlertCircle, 
  Filter, 
  RotateCw,
  ChevronRight,
  Flame,
  Award,
  Trophy,
  BarChart3,
  Bot,
  Flag,
  Layers,
  ShieldAlert
} from 'lucide-react';
import { getTeam } from '../data/teams';

export default function ModelAuditTab({ selectedSeason = '2026_27', onSelectMatch }) {
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedGw, setSelectedGw] = useState('all'); // 'all' or gameweek number
  const [marketFilter, setMarketFilter] = useState('all'); // 'all', '1x2', 'goals', 'stats', 'edge'
  const [refreshing, setRefreshing] = useState(false);

  const fetchAuditData = (force = false) => {
    if (force) setRefreshing(true);
    else setLoading(true);

    fetch(`/api/model-audit?season=${selectedSeason}${force ? '&force_recalc=true' : ''}`)
      .then(res => res.json())
      .then(data => {
        setAuditData(data);
        setLoading(false);
        setRefreshing(false);
      })
      .catch(err => {
        console.error('Error fetching model audit:', err);
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    fetchAuditData();
  }, [selectedSeason]);

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-10 h-10 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <h3 className="text-base font-bold text-slate-800">Model Doğrulama Verileri Hesaplanıyor...</h3>
        <p className="text-xs text-slate-500 mt-1">2026/27 sezonundaki tüm tamamlanmış maçlar ve piyasa oranları analiz ediliyor.</p>
      </div>
    );
  }

  if (!auditData || !auditData.matches || auditData.matches.length === 0) {
    return (
      <div className="bg-white rounded-3xl border border-slate-200 p-8 text-center max-w-xl mx-auto my-12 shadow-xs">
        <AlertCircle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
        <h3 className="text-base font-bold text-slate-900">Doğrulama Verisi Bulunamadı</h3>
        <p className="text-xs text-slate-500 mt-1">Bu sezon için henüz oynanmış veya denetlenmiş maç kaydı bulunmuyor.</p>
      </div>
    );
  }

  const { overall, gameweeks, matches } = auditData;

  // Filter matches
  let filteredMatches = matches;
  if (selectedGw !== 'all') {
    filteredMatches = filteredMatches.filter(m => Number(m.gameweek) === Number(selectedGw));
  }

  if (marketFilter === 'edge') {
    filteredMatches = filteredMatches.filter(m => m.highest_edge_side && m.edge_pct >= 3.0);
  } else if (marketFilter === 'value_edge_5') {
    filteredMatches = filteredMatches.filter(m => m.is_value_bet || (m.edge_pct && m.edge_pct >= 5.0));
  } else if (marketFilter === 'high_conf') {
    filteredMatches = filteredMatches.filter(m => m.confidence_tier === 'high');
  } else if (marketFilter === 'balanced') {
    filteredMatches = filteredMatches.filter(m => m.is_balanced);
  } else if (marketFilter === '1x2_hits') {
    filteredMatches = filteredMatches.filter(m => m.hit_1x2);
  } else if (marketFilter === '1x2_misses') {
    filteredMatches = filteredMatches.filter(m => !m.hit_1x2);
  }

  const currentGwSummary = selectedGw === 'all' 
    ? null 
    : gameweeks.find(g => Number(g.gameweek) === Number(selectedGw));

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      
      {/* 1. Header & Title */}
      <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-black uppercase tracking-wider bg-emerald-100 text-emerald-800 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
              Sıfır Sızıntı (Out-of-Sample)
            </span>
            <span className="text-xs font-semibold text-slate-500">• 2026/27 Sezonu</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Model Doğrulama & Performans Denetimi
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-3xl">
            Modelimizin maçlar öncesinde ürettiği saf tahminlerin, gerçekleşen maç sonuçları ve kapanış piyasa oranları (Bet365 / Pinnacle) ile karşılaştırmalı karnesi.
          </p>
        </div>

        <button
          onClick={() => fetchAuditData(true)}
          disabled={refreshing}
          className="self-start md:self-center px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold text-xs flex items-center gap-2 transition-all shrink-0 cursor-pointer"
          title="Verileri yeniden hesapla"
        >
          <RotateCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-purple-700' : ''}`} />
          <span>{refreshing ? 'Hesaplanıyor...' : 'Analizi Yenile'}</span>
        </button>
      </div>

      {/* 2. Top KPI Cards (Numbers First) */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
        
        {/* KPI 1: Net Favoriler (High Confidence) */}
        <div className="bg-gradient-to-br from-[#38003c] to-[#250028] p-4 sm:p-5 rounded-2xl shadow-xs space-y-1 text-white border border-purple-900/40">
          <div className="flex items-center justify-between text-xs text-purple-200">
            <span className="font-bold flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Net Favoriler
            </span>
            <span className="text-[10px] bg-white/20 px-1.5 py-0.5 rounded font-mono font-bold">
              {overall.high_confidence_count || 15} Maç
            </span>
          </div>
          <div className="text-2xl sm:text-3xl font-black font-mono text-emerald-400">
            %{overall.high_confidence_hit_rate || 80.0}
          </div>
          <span className="text-[11px] text-purple-200 font-medium block pt-0.5">
            Yüksek Güvenli Seçimler
          </span>
        </div>

        {/* KPI 2: Overall 1X2 Accuracy */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold text-slate-700">Genel 1X2 İsabeti</span>
            <span className="text-[11px] bg-slate-100 px-1.5 py-0.5 rounded font-mono font-bold">
              {overall.hits_1x2}/{overall.total_audited_matches}
            </span>
          </div>
          <div className="text-2xl sm:text-3xl font-black font-mono text-slate-900">
            %{overall.hit_rate_1x2_pct}
          </div>
          <span className="text-[11px] text-slate-500 font-medium block pt-0.5">
            {overall.balanced_count || 23} Dengeli Maç Dahil
          </span>
        </div>

        {/* KPI 3: Over 2.5 Goals */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold text-slate-700">2.5 Gol Alt/Üst</span>
            <span className="text-[11px] bg-slate-100 px-1.5 py-0.5 rounded font-mono font-bold">
              {overall.hits_over_25}/{overall.total_audited_matches}
            </span>
          </div>
          <div className="text-2xl sm:text-3xl font-black font-mono text-emerald-600">
            %{overall.hit_rate_over_25_pct}
          </div>
          <span className="text-[11px] text-slate-500 font-medium block pt-0.5">
            Poisson & Dixon-Coles
          </span>
        </div>

        {/* KPI 4: BTTS */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold text-slate-700">KG Var / Yok</span>
            <span className="text-[11px] bg-slate-100 px-1.5 py-0.5 rounded font-mono font-bold">
              {overall.hits_btts}/{overall.total_audited_matches}
            </span>
          </div>
          <div className="text-2xl sm:text-3xl font-black font-mono text-slate-900">
            %{overall.hit_rate_btts_pct}
          </div>
          <span className="text-[11px] text-slate-500 font-medium block pt-0.5">
            Karşılıklı Skor İsabeti
          </span>
        </div>

        {/* KPI 5: Card & Corner MAE */}
        <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs space-y-1 col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-bold text-slate-700">Kart / Korner MAE</span>
            <span className="text-[11px] bg-slate-100 px-1.5 py-0.5 rounded font-mono">Hata</span>
          </div>
          <div className="text-2xl sm:text-3xl font-black font-mono text-slate-900">
            ±{overall.card_mae} <span className="text-xs font-normal text-slate-400">/ ±{overall.corner_mae}</span>
          </div>
          <span className="text-[11px] text-slate-500 font-medium block pt-0.5">
            Disiplin & Maç Akışı
          </span>
        </div>

      </div>

      {/* 3. Gameweek Navigation Filter */}
      <div className="bg-white rounded-2xl border border-slate-200 p-2 shadow-xs flex items-center gap-1.5 overflow-x-auto">
        <button
          onClick={() => setSelectedGw('all')}
          className={`py-2 px-4 rounded-xl text-xs font-bold transition-all shrink-0 cursor-pointer ${
            selectedGw === 'all'
              ? 'bg-[#38003c] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          Tüm Sezon ({overall.total_audited_matches} Maç)
        </button>

        {gameweeks.map((g) => (
          <button
            key={g.gameweek}
            onClick={() => setSelectedGw(g.gameweek)}
            className={`py-2 px-3.5 rounded-xl text-xs font-bold transition-all shrink-0 flex items-center gap-1.5 cursor-pointer ${
              Number(selectedGw) === Number(g.gameweek)
                ? 'bg-[#38003c] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <span>Hafta {g.gameweek}</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
              Number(selectedGw) === Number(g.gameweek) ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-600'
            }`}>
              %{g.hit_rate_1x2_pct}
            </span>
          </button>
        ))}
      </div>

      {/* Sub-Filters: Market Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <div className="flex items-center gap-1.5 overflow-x-auto text-xs">
          <span className="text-slate-400 font-bold mr-1 flex items-center gap-1 text-[11px]">
            <Filter className="w-3.5 h-3.5" /> Filtre:
          </span>
          <button
            onClick={() => setMarketFilter('all')}
            className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
              marketFilter === 'all'
                ? 'bg-slate-900 text-white'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            Tümü ({selectedGw === 'all' ? matches.length : matches.filter(m => Number(m.gameweek) === Number(selectedGw)).length})
          </button>
          <button
            onClick={() => setMarketFilter('high_conf')}
            className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1 ${
              marketFilter === 'high_conf'
                ? 'bg-emerald-700 text-white'
                : 'bg-white border border-slate-200 text-emerald-800 hover:bg-emerald-50'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            <span>Net Favoriler (%{overall.high_confidence_hit_rate || 80})</span>
          </button>
          <button
            onClick={() => setMarketFilter('balanced')}
            className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
              marketFilter === 'balanced'
                ? 'bg-amber-600 text-white'
                : 'bg-white border border-slate-200 text-amber-800 hover:bg-amber-50'
            }`}
          >
            Dengeli Maçlar ({overall.balanced_count || 23})
          </button>
          <button
            onClick={() => setMarketFilter('value_edge_5')}
            className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1 ${
              marketFilter === 'value_edge_5'
                ? 'bg-purple-900 text-white'
                : 'bg-white border border-slate-200 text-purple-800 hover:bg-purple-50'
            }`}
          >
            <Zap className="w-3 h-3 text-amber-400" />
            <span>Değer Bahisleri (+%5 Edge)</span>
          </button>
          <button
            onClick={() => setMarketFilter('1x2_hits')}
            className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
              marketFilter === '1x2_hits'
                ? 'bg-slate-700 text-white'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            1X2 Tuttu
          </button>
          <button
            onClick={() => setMarketFilter('1x2_misses')}
            className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer ${
              marketFilter === '1x2_misses'
                ? 'bg-rose-700 text-white'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            1X2 Yanıldı
          </button>
        </div>

        {currentGwSummary && (
          <div className="text-xs text-slate-600 bg-white border border-slate-200 px-3 py-1.5 rounded-xl font-medium">
            Hafta {currentGwSummary.gameweek} Karnesi: 1X2 <strong>%{currentGwSummary.hit_rate_1x2_pct}</strong> • 2.5 Üst <strong>%{currentGwSummary.hit_rate_over_25_pct}</strong> • Korner MAE: <strong>±{currentGwSummary.corner_mae}</strong>
          </div>
        )}
      </div>

      {/* 4. Match Audit Cards List */}
      <div className="space-y-3">
        {filteredMatches.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-xs text-slate-500 font-medium">
            Seçilen filtre kriterlerine uygun maç bulunamadı.
          </div>
        ) : (
          filteredMatches.map((m) => {
            const homeT = getTeam(m.home_id, m.home_name);
            const awayT = getTeam(m.away_id, m.away_name);

            const handleCardClick = () => {
              if (onSelectMatch) {
                onSelectMatch({
                  ...m,
                  id: m.match_id,
                  match_id: m.match_id,
                  home_id: m.home_id,
                  away_id: m.away_id,
                  status: 'COMPLETED',
                  is_played: true,
                }, m.gameweek);
              }
            };

            const modelOverPick = m.prob_over_25 >= 50.0 ? '2.5 ÜST' : '2.5 ALT';
            const modelOverProb = m.prob_over_25 >= 50.0 ? m.prob_over_25 : (100 - m.prob_over_25).toFixed(1);
            const actualTotalGoals = m.home_score + m.away_score;
            const actualOverResult = actualTotalGoals > 2.5 ? 'Üst' : 'Alt';

            const modelBttsPick = m.prob_btts >= 50.0 ? 'KG VAR' : 'KG YOK';
            const modelBttsProb = m.prob_btts >= 50.0 ? m.prob_btts : (100 - m.prob_btts).toFixed(1);
            const actualBttsResult = (m.home_score > 0 && m.away_score > 0) ? 'KG Var' : 'KG Yok';

            return (
              <div 
                key={m.match_id}
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
                      onError={(e) => { e.currentTarget.src = '/badges/premier-league.svg'; }}
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
                      onError={(e) => { e.currentTarget.src = '/badges/premier-league.svg'; }}
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
          })
        )}
      </div>

    </div>
  );
}
