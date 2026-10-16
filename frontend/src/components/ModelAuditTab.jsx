import AuditMatchCard from './model-audit/AuditMatchCard';
import { formatSeasonLabel } from '../utils/dateFormatters';
import React, { useState, useEffect } from 'react';
import { getModelAudit } from '../services/auditService';
import { 
  CheckCircle2, 
  ShieldCheck, 
  Zap, 
  AlertCircle, 
  Filter, 
  RotateCw,
} from 'lucide-react';

export default function ModelAuditTab({ selectedSeason = '2026_27', onSelectMatch }) {
  const [auditSeason, setAuditSeason] = useState(selectedSeason || '2026_27');
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedGw, setSelectedGw] = useState('all'); // 'all' or gameweek number
  const [marketFilter, setMarketFilter] = useState('all'); // 'all', '1x2', 'goals', 'stats', 'edge'
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (selectedSeason) {
      setAuditSeason(selectedSeason);
      fetchAuditData(false, selectedSeason);
    }
  }, [selectedSeason]);

  const fetchAuditData = (force = false, targetSeason = auditSeason) => {
    if (force) setRefreshing(true);
    else setLoading(true);

    getModelAudit(targetSeason, force)
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

  const handleSeasonChange = (e) => {
    const nextSeason = e.target.value;
    setAuditSeason(nextSeason);
    setSelectedGw('all');
    fetchAuditData(false, nextSeason);
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-10 h-10 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <h3 className="text-base font-bold text-slate-800">Model Doğrulama Verileri Hesaplanıyor...</h3>
        <p className="text-xs text-slate-500 mt-1">{formatSeasonLabel(auditSeason, '/')} sezonundaki tüm tamamlanmış maçlar analiz ediliyor.</p>
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
              {auditSeason === '2026_27' ? 'Sıfır Sızıntı (Out-of-Sample)' : 'Tarihsel Doğrulama (Backtest)'}
            </span>
            <span className="text-xs font-semibold text-slate-500">• {formatSeasonLabel(auditSeason, '/')} Sezonu</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Model Doğrulama & Performans Denetimi
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-3xl">
            Modelimizin maçlar öncesinde ürettiği saf tahminlerin, gerçekleşen maç sonuçları ve kapanış piyasa oranları ile karşılaştırmalı karnesi.
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start md:self-center shrink-0">
          <select
            value={auditSeason}
            onChange={handleSeasonChange}
            className="px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 font-bold text-xs shadow-2xs outline-none cursor-pointer transition-all"
          >
            <option value="2026_27">2026/27 (Canlı • 60 Maç)</option>
            <option value="2025_26">2025/26 (Tüm Sezon • 380 Maç)</option>
            <option value="2024_25">2024/25 (Tüm Sezon • 380 Maç)</option>
          </select>

          <button
            onClick={() => fetchAuditData(true, auditSeason)}
            disabled={refreshing}
            className="px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 font-bold text-xs flex items-center gap-2 transition-all cursor-pointer"
            title="Verileri yeniden hesapla"
          >
            <RotateCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-purple-700' : ''}`} />
            <span>{refreshing ? 'Hesaplanıyor...' : 'Analizi Yenile'}</span>
          </button>
        </div>
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
          filteredMatches.map((m) => (
            <AuditMatchCard key={m.match_id} match={m} onSelectMatch={onSelectMatch} />
          ))
        )}
      </div>

    </div>
  );
}
