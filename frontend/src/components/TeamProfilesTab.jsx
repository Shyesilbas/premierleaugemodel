import React, { useState, useEffect, useMemo } from 'react';
import { getTeam } from '../data/teams';
import { Shield, Trophy, Users, Calendar, ChevronRight, Activity, Target, Flag, MapPin, Clock } from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';

const SQUAD_POSITION_TABS = [
  { id: 'all', label: 'Tümü' },
  { id: 'G', label: 'Kaleci' },
  { id: 'D', label: 'Savunma' },
  { id: 'M', label: 'Orta Saha' },
  { id: 'F', label: 'Forvet' },
];

function getPlayerCategory(pos) {
  if (!pos) return 'other';
  const p = String(pos).trim().toUpperCase();
  if (['G', 'GK', 'GOALKEEPER'].includes(p)) return 'G';
  if (['D', 'DEF', 'DEFENDER', 'CB', 'LB', 'RB', 'LWB', 'RWB'].includes(p)) return 'D';
  if (['M', 'MID', 'MIDFIELDER', 'CM', 'DM', 'AM', 'LM', 'RM'].includes(p)) return 'M';
  if (['F', 'FWD', 'FORWARD', 'ST', 'CF', 'RW', 'LW', 'ATT'].includes(p)) return 'F';
  return 'other';
}

function getPositionOrder(cat) {
  switch (cat) {
    case 'G': return 1;
    case 'D': return 2;
    case 'M': return 3;
    case 'F': return 4;
    default: return 5;
  }
}

function getPositionLabel(pos) {
  const cat = getPlayerCategory(pos);
  switch (cat) {
    case 'G': return 'Kaleci';
    case 'D': return 'Savunma';
    case 'M': return 'Orta Saha';
    case 'F': return 'Forvet';
    default: return pos || 'Oyuncu';
  }
}

function parseKickoff(label) {
  if (!label) return { date: '-', time: '' };
  const parts = label.split(',');
  if (parts.length >= 2) {
    return {
      date: parts[0].trim(),
      time: parts[1].trim().replace(/\s+(BST|GMT)/gi, ''),
    };
  }
  return { date: label, time: '' };
}

export default function TeamProfilesTab({ selectedSeason }) {
  const [selectedTeamId, setSelectedTeamId] = useState(1); // Default Arsenal
  const [currentLeagueTeams, setCurrentLeagueTeams] = useState(null);
  const [teamSeason, setTeamSeason] = useState(selectedSeason || '2026_27');
  const [profile, setProfile] = useState(null);
  const [tacticalProfile, setTacticalProfile] = useState(null);
  const [attackingLeaders, setAttackingLeaders] = useState(null);
  const [scenarioProfile, setScenarioProfile] = useState(null);
  const [activeTacticalTab, setActiveTacticalTab] = useState('general');
  const [selectedSquadTab, setSelectedSquadTab] = useState('all');
  const [tacticsLoading, setTacticsLoading] = useState(false);
  const [attackersLoading, setAttackersLoading] = useState(false);
  const [scenariosLoading, setScenariosLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeModalMatch, setActiveModalMatch] = useState(null);

  useEffect(() => {
    fetch('/api/teams?season=2026_27')
      .then(res => res.json())
      .then(data => setCurrentLeagueTeams(data.teams || []))
      .catch(err => {
        console.error('Error fetching current season teams:', err);
        setCurrentLeagueTeams([]);
      });
  }, []);

  const currentSeasonTeams = (currentLeagueTeams || []).map(team =>
    getTeam(team.id, team.name)
  );

  useEffect(() => {
    if (currentSeasonTeams.length && !currentSeasonTeams.some(team => team.id === selectedTeamId)) {
      setSelectedTeamId(currentSeasonTeams[0].id);
    }
  }, [currentLeagueTeams, selectedTeamId]);

  useEffect(() => {
    if (selectedSeason) {
      setTeamSeason(selectedSeason);
    }
  }, [selectedSeason]);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/teams/profile?team_id=${selectedTeamId}&season=${teamSeason}`)
      .then(res => res.json())
      .then(data => {
        setProfile(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching team profile:', err);
        setLoading(false);
      });
  }, [selectedTeamId, teamSeason]);

  useEffect(() => {
    const controller = new AbortController();
    setScenariosLoading(true);
    fetch(`/api/teams/scenarios?team_id=${selectedTeamId}&season=${teamSeason}`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error('Score-state profile request failed');
        return res.json();
      })
      .then(data => setScenarioProfile(data))
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team score-state profile:', err);
          setScenarioProfile(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setScenariosLoading(false);
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason]);

  useEffect(() => {
    const controller = new AbortController();
    setTacticsLoading(true);
    fetch(`/api/teams/tactics?team_id=${selectedTeamId}&season=${teamSeason}`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error('Tactical profile request failed');
        return res.json();
      })
      .then(data => setTacticalProfile(data))
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team tactical profile:', err);
          setTacticalProfile(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setTacticsLoading(false);
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason]);

  useEffect(() => {
    const controller = new AbortController();
    setAttackersLoading(true);
    fetch(`/api/teams/attacking-leaders?team_id=${selectedTeamId}&season=${teamSeason}`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error('Attacking leaders request failed');
        return res.json();
      })
      .then(data => setAttackingLeaders(data))
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team attacking leaders:', err);
          setAttackingLeaders(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setAttackersLoading(false);
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason]);

  const currentMeta = getTeam(selectedTeamId);
  const tacticalTabs = [
    {
      id: 'general',
      label: 'Genel',
      title: 'Oyun karakteri',
      explanation: 'Takımın topa ne kadar sahip olduğunu ve paslarının ne ölçüde ileri yöneldiğini özetler. Hücum üretimi ve savunma aksiyonları kendi bölümlerinde yer alır.',
      keys: ['possession', 'forward_pass_share'],
    },
    {
      id: 'attack',
      label: 'Hücum',
      title: 'Hücum üretimi ve şut profili',
      explanation: 'Son bölgeye ilerlemeyi, ceza sahasına erişimi ve bu hücumların şuta dönüşmesini birlikte gösterir. Şut konumu ve isabet oranı, şut kalitesinin yerini tutmaz.',
      keys: [
        'final_third_entries',
        'final_third_passes',
        'final_third_pass_accuracy',
        'opposition_box_touches',
        'shots_per_match',
        'shots_on_target_share',
        'inside_box_shot_share',
        'outside_box_shot_share',
      ],
    },
    {
      id: 'passing',
      label: 'Pas tercihleri',
      title: 'Uzun pas ve orta kullanımı',
      explanation: 'Uzun pas payı ve orta sıklığı takımın tercihlerini; isabet oranları ise bu pasların ne kadarının tamamlandığını gösterir.',
      keys: ['long_ball_share', 'long_ball_accuracy', 'crosses_per_match', 'cross_accuracy'],
    },
    {
      id: 'set-pieces',
      label: 'Duran toplar',
      title: 'Korner tercihi',
      explanation: 'Kullanılan kornerlerin ne kadarının doğrudan ceza sahasına gönderildiğini gösterir. Tek başına kornerlerin tehlike üretip üretmediğini ölçmez.',
      keys: ['corners_into_box_share'],
    },
    {
      id: 'defense',
      label: 'Savunma',
      title: 'Savunma aksiyonları',
      explanation: 'Top kazanma, pas arası, müdahale ve uzaklaştırma aksiyonlarının maç başına düzeyini gösterir.',
      keys: [
        'ball_recoveries',
        'defensive_third_recoveries',
        'mid_third_recoveries',
        'attacking_third_recoveries',
        'pressing_intensity',
        'interceptions',
        'tackle_success',
        'aerial_duel_success',
        'clearances',
      ],
    },
    {
      id: 'losses',
      label: 'Top kaybı',
      title: 'Top kaybı profili',
      explanation: 'Maç başına toplam ve kontrollü top kayıplarını ayrı ayrı gösterir.',
      keys: ['possession_losses', 'controlled_possession_losses'],
    },
    {
      id: 'game-state',
      label: 'Skor durumu',
      title: 'Skor durumuna göre oyun',
      explanation: 'Takımın skor eşitken, öndeyken ve gerideyken şut ve korner temposunu karşılaştırır.',
      keys: [],
    },
  ];

  const activeTab = tacticalTabs.find(tab => tab.id === activeTacticalTab) || tacticalTabs[0];
  const formatNumber = value => Number(value).toLocaleString('tr-TR', { maximumFractionDigits: 1 });

  const compareWithLeague = key => {
    const metric = tacticalProfile?.metrics?.[key];
    if (metric?.value == null || metric?.league_average == null) return null;
    const difference = Number(metric.value) - Number(metric.league_average);
    if (Math.abs(difference) < 0.05) return `${metric.label.toLocaleLowerCase('tr-TR')} lig ortalamasına yakın`;
    const amount = formatNumber(Math.abs(difference));
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
    const name = tacticalProfile?.team_name || currentMeta.name;
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
      const ppda = compareWithLeague('pressing_intensity');
      const attackingThird = compareWithLeague('attacking_third_recoveries');
      const aerialDuels = compareWithLeague('aerial_duel_success');
      const observations = [ppda, attackingThird, aerialDuels].filter(Boolean);
      if (!observations.length) return 'Karşılaştırmalı yorum için henüz yeterli veri yok.';
      return `${name} için ${observations.join('; ')}. PPDA düşükse baskı daha yoğundur; hücum bölgesindeki top kazanımları topun nerede geri alındığını, hava topu oranı ise bu mücadelelerin ne kadarının kazanıldığını gösterir.`;
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
      : `lig ortalamasından ${formatNumber(delta)} / 90 dakika daha ${direction}`;
    return `${name} ${strongest.state} ${strongest.label} temposunda ${comparison}. Bu, ilgili skor durumundaki aksiyon hacmini gösterir; skor değişikliğinin nedeni olduğunu kanıtlamaz.`;
  };

  const renderTacticalMetric = (key, metrics) => {
    const metric = metrics[key];
    if (!metric) return null;
    const hasValue = metric.value !== null && metric.value !== undefined;
    const valueLabel = hasValue
      ? `${Number(metric.value).toFixed(1)}${metric.unit === '%' ? '%' : ''}`
      : '—';
    const difference = hasValue && metric.league_average !== null && metric.league_average !== undefined
      ? Number(metric.value) - Number(metric.league_average)
      : null;
    const differenceLabel = difference === null
      ? null
      : `${difference > 0 ? '+' : ''}${formatNumber(difference)}${metric.unit === '%' ? ' yüzde puan' : metric.unit === 'PPDA' ? '' : ' / maç'}`;
    return (
      <div key={key} className="min-h-[218px] rounded-lg border border-slate-200 bg-white p-4 transition-colors hover:border-slate-400 hover:bg-slate-50/40">
        <div className="flex min-h-8 items-start justify-between gap-3">
          <p className="text-[11px] font-semibold leading-4 text-slate-600">{metric.label}</p>
          <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wide text-slate-400">
            {metric.unit === '%' ? 'Oran' : metric.unit === 'PPDA' ? 'PPDA' : 'Maç başı'}
          </span>
        </div>

        <div className="mt-3 flex items-baseline gap-1.5">
          <p className="text-[32px] font-semibold leading-none tracking-tight tabular-nums text-slate-950">{valueLabel}</p>
          {metric.unit === 'PPDA' && <span className="text-[10px] text-slate-400">düşük = yoğun pres</span>}
        </div>
        <p className="mt-2 min-h-9 text-[10px] leading-[1.15rem] text-slate-500">{metric.description}</p>

        <div className="mt-3 border-t border-slate-100 pt-2.5">
          <div className="flex items-center justify-between gap-2 text-[10px]">
            <span className="text-slate-500">Lig ortalaması</span>
            <span className="font-semibold tabular-nums text-slate-700">
              {metric.league_average === null || metric.league_average === undefined
                ? '—'
                : `${Number(metric.league_average).toFixed(1)}${metric.unit === '%' ? '%' : ''}`}
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between gap-2 text-[10px]">
            <span className="text-slate-500">Lig ortalamasına fark</span>
            <span className="font-semibold tabular-nums text-slate-700">{differenceLabel || '—'}</span>
          </div>
          {metric.percentile !== null && metric.percentile !== undefined && (
            <div className="mt-2.5">
              <div className="mb-1 flex items-center justify-between text-[9px] text-slate-500">
                <span>Lig dağılımı</span>
                <span className="font-semibold tabular-nums text-slate-700">P{metric.percentile}</span>
              </div>
              <div className="h-1 rounded-full bg-slate-200" title={`Lig dağılımında P${metric.percentile}`}>
                <div className="h-full rounded-full bg-slate-700" style={{ width: `${metric.percentile}%` }} />
              </div>
            </div>
          )}
          <p className="mt-2 text-[9px] text-slate-400">
            {metric.matches}/{tacticalProfile?.matches || 0} maç · %{formatNumber(metric.coverage_pct || 0)} veri kapsamı
          </p>
          {metric.unit === 'PPDA' && (
            <p className="mt-1 text-[9px] leading-4 text-slate-500">
              Lig kapsaması %{formatNumber(metric.league_coverage_pct || 0)}
              {metric.value == null && ' · Karşılaştırma için en az %80 kapsam gerekir.'}
            </p>
          )}
        </div>
      </div>
    );
  };

  const squadCounts = useMemo(() => {
    const counts = { all: profile?.squad?.length || 0, G: 0, D: 0, M: 0, F: 0 };
    (profile?.squad || []).forEach(p => {
      const cat = getPlayerCategory(p.position);
      if (counts[cat] !== undefined) {
        counts[cat]++;
      }
    });
    return counts;
  }, [profile?.squad]);

  const filteredSquad = useMemo(() => {
    if (!profile?.squad) return [];
    let list = profile.squad;
    if (selectedSquadTab !== 'all') {
      list = list.filter(p => getPlayerCategory(p.position) === selectedSquadTab);
    }
    return [...list].sort((a, b) => {
      const posA = getPositionOrder(getPlayerCategory(a.position));
      const posB = getPositionOrder(getPlayerCategory(b.position));
      if (posA !== posB) return posA - posB;
      const shirtA = a.shirt != null && !isNaN(Number(a.shirt)) ? Number(a.shirt) : 999;
      const shirtB = b.shirt != null && !isNaN(Number(b.shirt)) ? Number(b.shirt) : 999;
      if (shirtA !== shirtB) return shirtA - shirtB;
      return (a.name || '').localeCompare(b.name || '', 'tr');
    });
  }, [profile?.squad, selectedSquadTab]);

  return (
    <div className="space-y-6">

      {/* Team Selection Carousel / Grid */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3 px-1">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-[#38003c]" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Kulüp Seçin
            </h3>
          </div>
          <span className="text-[11px] text-slate-500 font-medium">{currentSeasonTeams.length} Premier League Takımı</span>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {currentSeasonTeams.map(t => {
            const isSelected = t.id === selectedTeamId;
            return (
              <button
                key={t.id}
                onClick={() => setSelectedTeamId(t.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold transition-all shrink-0 border ${
                  isSelected
                    ? 'bg-[#38003c] text-white border-[#38003c] shadow-sm'
                    : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
                }`}
              >
                <img 
                  src={t.badge} 
                  alt={t.name} 
                  className="w-5 h-5 object-contain"
                  onError={(e) => { e.target.src = '/badges/1.svg'; }}
                />
                <span className="truncate max-w-[110px]">{t.short || t.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Team Profile Hero & Record Card */}
      {profile && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-20 h-20 rounded-2xl bg-slate-50 border border-slate-200 p-2 flex items-center justify-center shrink-0 shadow-inner">
              <img 
                src={currentMeta.badge} 
                alt={currentMeta.name} 
                className="w-16 h-16 object-contain" 
              />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h2 className="text-2xl font-black text-slate-900 tracking-tight">
                  {currentMeta.name}
                </h2>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                  {currentMeta.abbr}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" /> {currentMeta.stadium || 'Premier League Stadium'}
              </p>
            </div>
          </div>

          {/* Season Switcher & Stats Pills */}
          <div className="flex flex-col items-end gap-3 w-full md:w-auto">
            <div className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1">
              <button
                onClick={() => setTeamSeason('2026_27')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === '2026_27'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2026-27
              </button>
              <button
                onClick={() => setTeamSeason('2025_26')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === '2025_26'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2025-26
              </button>
              <button
                onClick={() => setTeamSeason('2024_25')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === '2024_25'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2024-25
              </button>
              <button
                onClick={() => setTeamSeason('2023_24')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === '2023_24'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                2023-24
              </button>
              <button
                onClick={() => setTeamSeason('all')}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                  teamSeason === 'all'
                    ? 'bg-[#38003c] text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Tümü
              </button>
            </div>

            {/* Record Pills */}
            {profile.record && (
              <div className="flex items-center gap-2 font-mono text-xs">
                <div className="bg-emerald-50 border border-emerald-200 px-3 py-1 rounded-xl text-center">
                  <span className="text-[10px] text-emerald-700 font-sans block">GALİBİYET</span>
                  <strong className="text-emerald-800 text-sm font-bold">{profile.record.wins}</strong>
                </div>
                <div className="bg-slate-100 border border-slate-200 px-3 py-1 rounded-xl text-center">
                  <span className="text-[10px] text-slate-500 font-sans block">BERABERLİK</span>
                  <strong className="text-slate-800 text-sm font-bold">{profile.record.draws}</strong>
                </div>
                <div className="bg-rose-50 border border-rose-200 px-3 py-1 rounded-xl text-center">
                  <span className="text-[10px] text-rose-700 font-sans block">MAĞLUBİYET</span>
                  <strong className="text-rose-800 text-sm font-bold">{profile.record.losses}</strong>
                </div>
                <div className="bg-purple-50 border border-purple-200 px-3 py-1 rounded-xl text-center">
                  <span className="text-[10px] text-purple-700 font-sans block">GOL (AV)</span>
                  <strong className="text-purple-900 text-sm font-bold">
                    {profile.record.gf}:{profile.record.ga}
                  </strong>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Explainable team profile, split into focused tabs */}
      <section className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-500" />
              <h3 className="text-sm font-black text-slate-900">Takım Oyun Profili</h3>
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Değerler seçili dönem ve aynı dönem lig ortalamasıyla karşılaştırılır.</p>
          </div>
          {tacticalProfile?.matches > 0 && activeTacticalTab !== 'game-state' && (
            <span className="text-[10px] text-slate-500 font-mono whitespace-nowrap">{tacticalProfile.matches} maç</span>
          )}
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
              {activeTab.keys.map(key => renderTacticalMetric(key, tacticalProfile.metrics || {}))}
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
                      {attackingLeaders.players.map((player, index) => (
                        <article key={player.id} className="rounded-lg border border-slate-200 bg-white p-4">
                          <div className="flex items-center gap-3">
                            <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full border border-slate-200 bg-slate-50">
                              {player.photo_url ? (
                                <img src={player.photo_url} alt="" className="h-full w-full object-cover" loading="lazy" />
                              ) : (
                                <span className="text-xs font-bold text-slate-500">{index + 1}</span>
                              )}
                            </div>
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

      {/* Main Content: League Matches Preview List */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-[#38003c]" />
            <h3 className="text-sm font-black text-slate-900">
              {currentMeta.name} — Sezon Lig Maçları ve Skor Önizlemeleri
            </h3>
          </div>
          <span className="text-xs font-mono font-bold text-slate-500">
            {profile?.matches?.length || 0} Maç
          </span>
        </div>

        {loading ? (
          <div className="py-16 text-center">
            <div className="w-7 h-7 border-3 border-[#38003c] border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-xs font-bold text-slate-600">Takım maçları yükleniyor...</p>
          </div>
        ) : !profile?.matches?.length ? (
          <div className="py-12 text-center text-xs text-slate-500 font-medium">
            Bu sezon için kayıtlı maç bulunamadı.
          </div>
        ) : (
          <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 bg-white shadow-2xs overflow-hidden">
            {profile.matches.map(m => {
              const opp = getTeam(m.opponent_id, m.opponent_name);
              const isPlayed = (m.team_score !== null && m.team_score !== undefined);
              const isWin = m.result === 'W';
              const isDraw = m.result === 'D';
              const isLoss = m.result === 'L';

              const resBadgeClass = isWin 
                ? 'bg-emerald-100 text-emerald-800 border-emerald-300' 
                : isDraw 
                ? 'bg-slate-100 text-slate-700 border-slate-300' 
                : 'bg-rose-100 text-rose-800 border-rose-300';

              const resLabel = isWin ? 'G' : isDraw ? 'B' : 'M';
              const kickoff = parseKickoff(m.kickoff_label);

              const homeTeam = m.is_home ? currentMeta : opp;
              const awayTeam = m.is_home ? opp : currentMeta;
              const homeScore = m.is_home ? m.team_score : m.opp_score;
              const awayScore = m.is_home ? m.opp_score : m.team_score;

              // Synthetic match object for MatchDetailModal
              const modalMatchObj = {
                match_id: m.match_id,
                status: isPlayed ? 'COMPLETED' : (m.status || 'UNPLAYED'),
                gameweek: m.gameweek,
                kickoff_label: m.kickoff_label,
                home_id: homeTeam.id,
                home_name: homeTeam.name,
                home_score: homeScore,
                away_id: awayTeam.id,
                away_name: awayTeam.name,
                away_score: awayScore,
                ground_name: m.is_home ? currentMeta.stadium : opp.stadium,
              };

              return (
                <div
                  key={m.match_id}
                  onClick={() => setActiveModalMatch(modalMatchObj)}
                  className="px-3.5 py-2.5 hover:bg-slate-50/80 transition-colors cursor-pointer group flex items-center justify-between gap-3 text-xs"
                >
                  {/* 1. Tarih & Saat (En Başta) */}
                  <div className="flex items-center gap-2 min-w-[130px] sm:min-w-[160px] shrink-0">
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0 hidden sm:block" />
                    <div className="flex flex-col sm:flex-row sm:items-center gap-0.5 sm:gap-2">
                      <span className="font-bold text-slate-900 text-[11px] sm:text-xs whitespace-nowrap">
                        {kickoff.date}
                      </span>
                      {kickoff.time && (
                        <span className="font-mono text-slate-500 font-semibold text-[10px] sm:text-[11px] whitespace-nowrap">
                          {kickoff.time}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 2. Hafta & Saha Rozeti */}
                  <div className="flex items-center gap-1.5 shrink-0 hidden sm:flex">
                    <span className="font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
                      H{Math.round(Number(m.gameweek) || 1)}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      m.is_home ? 'bg-sky-50 text-sky-700 border border-sky-200' : 'bg-slate-100 text-slate-600'
                    }`}>
                      {m.is_home ? 'İç' : 'Dep'}
                    </span>
                  </div>

                  {/* 3. Karşılaşma ve Skor (Ortada Tek Sıra) */}
                  <div className="flex items-center justify-center gap-2 sm:gap-3 flex-1 min-w-0">
                    {/* Ev Sahibi */}
                    <div className="flex items-center gap-1.5 justify-end flex-1 min-w-0 text-right">
                      <span className={`truncate text-xs ${homeTeam.id === selectedTeamId ? 'font-black text-slate-900' : 'font-medium text-slate-600'}`}>
                        {homeTeam.short || homeTeam.name}
                      </span>
                      <img 
                        src={homeTeam.badge} 
                        alt={homeTeam.name} 
                        className="w-5 h-5 object-contain shrink-0"
                        onError={(e) => { e.target.src = '/badges/1.svg'; }}
                      />
                    </div>

                    {/* Skor / Durum */}
                    <div className="shrink-0 flex items-center justify-center min-w-[55px]">
                      {isPlayed ? (
                        <span className="px-2 py-0.5 rounded bg-slate-900 text-white font-mono font-black text-xs tracking-wider shadow-2xs">
                          {homeScore} - {awayScore}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-500 font-mono text-[10px] font-bold border border-slate-200">
                          {kickoff.time || 'vs'}
                        </span>
                      )}
                    </div>

                    {/* Deplasman */}
                    <div className="flex items-center gap-1.5 justify-start flex-1 min-w-0 text-left">
                      <img 
                        src={awayTeam.badge} 
                        alt={awayTeam.name} 
                        className="w-5 h-5 object-contain shrink-0"
                        onError={(e) => { e.target.src = '/badges/1.svg'; }}
                      />
                      <span className={`truncate text-xs ${awayTeam.id === selectedTeamId ? 'font-black text-slate-900' : 'font-medium text-slate-600'}`}>
                        {awayTeam.short || awayTeam.name}
                      </span>
                    </div>
                  </div>

                  {/* 4. Sonuç Rozeti (G/B/M) & Ok */}
                  <div className="flex items-center gap-2 shrink-0">
                    {isPlayed && (
                      <span className={`w-5 h-5 flex items-center justify-center text-[10px] font-mono font-black rounded border ${resBadgeClass}`}>
                        {resLabel}
                      </span>
                    )}
                    <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-slate-700 group-hover:translate-x-0.5 transition-all" />
                  </div>

                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Squad Roster Preview with Position Tabs */}
      {profile?.squad && profile.squad.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-[#38003c]" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                {currentMeta.name} — Kadro Listesi ({selectedSquadTab === 'all' ? profile.squad.length : `${filteredSquad.length} / ${profile.squad.length}`} Oyuncu)
              </h3>
            </div>

            {/* Position Tabs: Kaleci, Savunma, Orta Saha, Forvet (plus Tümü) */}
            <div
              role="tablist"
              aria-label="Oyuncu pozisyon sekmeleri"
              className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1 overflow-x-auto scrollbar-none"
            >
              {SQUAD_POSITION_TABS.map(tab => {
                const isSelected = selectedSquadTab === tab.id;
                const count = squadCounts[tab.id] || 0;
                return (
                  <button
                    key={tab.id}
                    id={`squad-tab-${tab.id}`}
                    type="button"
                    role="tab"
                    aria-selected={isSelected}
                    aria-controls="squad-tabpanel"
                    onClick={() => setSelectedSquadTab(tab.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all whitespace-nowrap ${
                      isSelected
                        ? 'bg-[#38003c] text-white shadow-sm'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                    }`}
                  >
                    <span>{tab.label}</span>
                    <span
                      className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
                        isSelected
                          ? 'bg-white/20 text-white'
                          : 'bg-slate-200 text-slate-600'
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
              <div className="py-12 text-center text-xs text-slate-500 font-medium">
                Bu mevkide kayıtlı oyuncu bulunamadı.
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5 pt-1">
                {filteredSquad.map(p => (
                  <div
                    key={p.id}
                    className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 hover:bg-white hover:border-slate-300 hover:shadow-xs transition-all flex flex-col justify-between"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-b from-slate-100 to-slate-200 border border-slate-300 overflow-hidden shrink-0 flex items-center justify-center shadow-inner">
                        {p.photo_url ? (
                          <img
                            src={p.photo_url}
                            alt={p.name}
                            className="w-full h-full object-contain"
                            onError={(e) => { e.target.style.display = 'none'; }}
                            loading="lazy"
                          />
                        ) : (
                          <span className="font-mono text-xs font-black text-slate-600">#{p.shirt || '-'}</span>
                        )}
                      </div>
                      <div className="min-w-0">
                        <span className="font-mono text-xs font-black text-slate-900 block leading-tight">
                          #{p.shirt || '-'}
                        </span>
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-700 block mt-0.5 w-fit truncate">
                          {getPositionLabel(p.position)}
                        </span>
                      </div>
                    </div>
                    <h4 className="font-bold text-xs text-slate-900 truncate" title={p.name}>
                      {p.name}
                    </h4>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 mt-1.5 pt-1.5 border-t border-slate-200 font-mono">
                      <span>{p.total_appearances} Maç</span>
                      <span className="font-bold text-emerald-700">{p.total_goals} Gol</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Match Detail Modal */}
      {activeModalMatch && (
        <MatchDetailModal
          match={activeModalMatch}
          onClose={() => setActiveModalMatch(null)}
        />
      )}

    </div>
  );
}
