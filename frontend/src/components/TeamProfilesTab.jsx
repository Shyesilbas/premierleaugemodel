import React, { useState, useEffect, useMemo } from 'react';
import { getTeam } from '../data/teams';

import { Shield, Trophy, Users, Calendar, ChevronRight, Activity, Target, Flag, MapPin, Clock, X, RotateCw, CheckCircle2, Search, ChevronDown, ChevronsUpDown } from 'lucide-react';
import MatchDetailModal from './MatchDetailModal';
import PlayerAvatar from './PlayerAvatar';
import { getCachedTeamData, setCachedTeamData, calculateTeamExpiry, clearTeamCache } from '../utils/teamProfileCache';

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

function getPositionBadgeStyle(pos) {
  const cat = getPlayerCategory(pos);
  switch (cat) {
    case 'G': return 'bg-amber-50 text-amber-700 border-amber-200';
    case 'D': return 'bg-sky-50 text-sky-700 border-sky-200';
    case 'M': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'F': return 'bg-purple-50 text-purple-700 border-purple-200';
    default: return 'bg-slate-50 text-slate-700 border-slate-200';
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

export default function TeamProfilesTab({ selectedSeason, onSelectMatch, selectedTeamId = 1, onSelectTeam }) {
  const [currentLeagueTeams, setCurrentLeagueTeams] = useState(null);
  const [teamSeason, setTeamSeason] = useState(selectedSeason || '2026_27');
  const [activeTeamTab, setActiveTeamTab] = useState('fixtures'); // 'fixtures' | 'profile' | 'squad' | 'managers'
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
  const [teamStaff, setTeamStaff] = useState(null);
  const [managerChanges, setManagerChanges] = useState([]);
  const [selectedManager, setSelectedManager] = useState(null);
  const [managerPerformance, setManagerPerformance] = useState(null);
  const [managerPerformanceLoading, setManagerPerformanceLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [squadSortField, setSquadSortField] = useState('position');
  const [squadSortDirection, setSquadSortDirection] = useState('asc');

  const handleSquadSort = (field) => {
    if (squadSortField === field) {
      setSquadSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSquadSortField(field);
      if (['appearances', 'starts', 'goals', 'assists', 'yellow_cards', 'red_cards'].includes(field)) {
        setSquadSortDirection('desc');
      } else {
        setSquadSortDirection('asc');
      }
    }
  };

  // Standings data & Quick Club Selector Popover
  const [standings, setStandings] = useState([]);
  const [isTeamSelectorOpen, setIsTeamSelectorOpen] = useState(false);
  const [teamSearchQuery, setTeamSearchQuery] = useState('');
  const teamSelectorRef = React.useRef(null);

  useEffect(() => {
    if (teamSeason === 'all') {
      setStandings([]);
      return;
    }
    fetch(`/api/standings?season=${teamSeason}`)
      .then(res => res.ok ? res.json() : { standings: [] })
      .then(data => setStandings(data.standings || []))
      .catch(err => {
        console.error('Error fetching standings for team profile:', err);
        setStandings([]);
      });
  }, [teamSeason]);

  const currentStanding = useMemo(() => {
    if (!standings?.length) return null;
    const idx = standings.findIndex(s => Number(s.id) === Number(selectedTeamId));
    if (idx === -1) return null;
    return {
      rank: idx + 1,
      ...standings[idx]
    };
  }, [standings, selectedTeamId]);

  const standingsMap = useMemo(() => {
    const map = {};
    (standings || []).forEach((s, idx) => {
      map[s.id] = { rank: idx + 1, points: s.points, played: s.played };
    });
    return map;
  }, [standings]);

  useEffect(() => {
    if (!isTeamSelectorOpen) return;
    const handleClickOutside = (e) => {
      if (teamSelectorRef.current && !teamSelectorRef.current.contains(e.target)) {
        setIsTeamSelectorOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setIsTeamSelectorOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isTeamSelectorOpen]);

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

  const filteredClubs = useMemo(() => {
    if (!teamSearchQuery.trim()) return currentSeasonTeams;
    const q = teamSearchQuery.toLowerCase().trim();
    return currentSeasonTeams.filter(t => 
      t.name.toLowerCase().includes(q) || 
      (t.short && t.short.toLowerCase().includes(q)) ||
      (t.abbr && t.abbr.toLowerCase().includes(q))
    );
  }, [currentSeasonTeams, teamSearchQuery]);

  useEffect(() => {
    if (currentSeasonTeams.length && !currentSeasonTeams.some(team => team.id === selectedTeamId)) {
      onSelectTeam?.(currentSeasonTeams[0].id);
    }
  }, [currentLeagueTeams, selectedTeamId, onSelectTeam]);

  useEffect(() => {
    if (selectedSeason) {
      setTeamSeason(selectedSeason);
    }
  }, [selectedSeason]);

  useEffect(() => {
    const cached = getCachedTeamData('profile', selectedTeamId, teamSeason);
    if (cached) {
      setProfile(cached.data);
      setLoading(false);
      return;
    }

    setLoading(true);
    fetch(`/api/teams/profile?team_id=${selectedTeamId}&season=${teamSeason}`)
      .then(res => res.json())
      .then(data => {
        setProfile(data);
        const { expiresAt, label } = calculateTeamExpiry(data?.next_match, teamSeason);
        setCachedTeamData('profile', selectedTeamId, teamSeason, data, expiresAt, label);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching team profile:', err);
        setLoading(false);
      });
  }, [selectedTeamId, teamSeason, refreshKey]);

  useEffect(() => {
    const staffSeason = teamSeason === 'all' ? '2026_27' : teamSeason;
    const controller = new AbortController();
    setTeamStaff(null);
    fetch(`/api/teams/staff?season=${staffSeason}&team_id=${selectedTeamId}`, { signal: controller.signal })
      .then(res => res.ok ? res.json() : null)
      .then(data => setTeamStaff(data?.staff || null))
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team staff:', err);
          setTeamStaff(null);
        }
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason]);

  useEffect(() => {
    const requestedSeason = teamSeason === 'all' ? 'all' : teamSeason;
    const isPastSeason = requestedSeason !== '2026_27' && requestedSeason !== 'all';

    // Past seasons are static, so cache them permanently. Current season is kept live.
    if (isPastSeason) {
      const cached = getCachedTeamData('manager_changes', 'all', requestedSeason);
      if (cached?.data) {
        const changes = Object.values(cached.data.events_by_match || {}).flat()
          .filter(event => Number(event.team_id) === Number(selectedTeamId));
        setManagerChanges(changes.sort((a, b) => a.appointment_date.localeCompare(b.appointment_date)));
        return;
      }
    }

    const controller = new AbortController();
    fetch(`/api/teams/manager-changes?season=${requestedSeason}`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error('Manager history request failed');
        return res.json();
      })
      .then(data => {
        if (isPastSeason) {
          setCachedTeamData('manager_changes', 'all', requestedSeason, data, null, 'Geçmiş sezon teknik direktör geçmişi');
        }
        const changes = Object.values(data.events_by_match || {}).flat()
          .filter(event => Number(event.team_id) === Number(selectedTeamId));
        setManagerChanges(changes.sort((a, b) => a.appointment_date.localeCompare(b.appointment_date)));
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching team manager change history:', err);
          setManagerChanges([]);
        }
      });
    return () => controller.abort();
  }, [selectedTeamId, teamSeason, refreshKey]);

  useEffect(() => {
    const cached = getCachedTeamData('scenarios', selectedTeamId, teamSeason);
    if (cached) {
      setScenarioProfile(cached.data);
      setScenariosLoading(false);
      return;
    }

    const controller = new AbortController();
    setScenariosLoading(true);
    fetch(`/api/teams/scenarios?team_id=${selectedTeamId}&season=${teamSeason}`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error('Score-state profile request failed');
        return res.json();
      })
      .then(data => {
        setScenarioProfile(data);
        const { expiresAt, label } = calculateTeamExpiry(profile?.next_match, teamSeason);
        setCachedTeamData('scenarios', selectedTeamId, teamSeason, data, expiresAt, label);
      })
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
  }, [selectedTeamId, teamSeason, refreshKey]);

  useEffect(() => {
    const cached = getCachedTeamData('tactics', selectedTeamId, teamSeason);
    if (cached) {
      setTacticalProfile(cached.data);
      setTacticsLoading(false);
      return;
    }

    const controller = new AbortController();
    setTacticsLoading(true);
    fetch(`/api/teams/tactics?team_id=${selectedTeamId}&season=${teamSeason}`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error('Tactical profile request failed');
        return res.json();
      })
      .then(data => {
        setTacticalProfile(data);
        const { expiresAt, label } = calculateTeamExpiry(profile?.next_match, teamSeason);
        setCachedTeamData('tactics', selectedTeamId, teamSeason, data, expiresAt, label);
      })
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
  }, [selectedTeamId, teamSeason, refreshKey]);

  useEffect(() => {
    const cached = getCachedTeamData('attackers', selectedTeamId, teamSeason);
    if (cached) {
      setAttackingLeaders(cached.data);
      setAttackersLoading(false);
      return;
    }

    const controller = new AbortController();
    setAttackersLoading(true);
    fetch(`/api/teams/attacking-leaders?team_id=${selectedTeamId}&season=${teamSeason}`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error('Attacking leaders request failed');
        return res.json();
      })
      .then(data => {
        setAttackingLeaders(data);
        const { expiresAt, label } = calculateTeamExpiry(profile?.next_match, teamSeason);
        setCachedTeamData('attackers', selectedTeamId, teamSeason, data, expiresAt, label);
      })
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
  }, [selectedTeamId, teamSeason, refreshKey]);

  // When profile updates with next_match, align the TTL for all cached endpoints
  useEffect(() => {
    if (profile?.next_match) {
      const { expiresAt, label } = calculateTeamExpiry(profile.next_match, teamSeason);
      ['tactics', 'scenarios', 'attackers'].forEach(cat => {
        const item = getCachedTeamData(cat, selectedTeamId, teamSeason);
        if (item?.data && item.expiresAt !== expiresAt) {
          setCachedTeamData(cat, selectedTeamId, teamSeason, item.data, expiresAt, label);
        }
      });
    }
  }, [profile, selectedTeamId, teamSeason]);

  // Handle manual refresh
  const handleManualRefresh = () => {
    setIsRefreshing(true);
    clearTeamCache(selectedTeamId, teamSeason);
    setRefreshKey(prev => prev + 1);
  };

  useEffect(() => {
    if (isRefreshing && !loading && !tacticsLoading && !scenariosLoading && !attackersLoading) {
      setIsRefreshing(false);
    }
  }, [isRefreshing, loading, tacticsLoading, scenariosLoading, attackersLoading]);

  const isProfileCached = useMemo(() => {
    const item = getCachedTeamData('tactics', selectedTeamId, teamSeason);
    return item ? { nextMatchLabel: item.nextMatchLabel, isPermanent: item.isPermanent } : null;
  }, [selectedTeamId, teamSeason, tacticalProfile, refreshKey]);

  const currentMeta = getTeam(selectedTeamId);
  const teamOfficials = useMemo(() => {
    const uniqueOfficials = new Map();
    (teamStaff?.officials || []).forEach(official => {
      const role = (official.role || '').toLowerCase();
      if (!['manager', 'assistant manager', 'matchday manager'].includes(role)) return;
      const key = `${official.id || official.officialId || official.name?.display}-${role}`;
      if (!uniqueOfficials.has(key)) uniqueOfficials.set(key, official);
    });
    return [...uniqueOfficials.values()].sort((a, b) => {
      const order = role => role === 'Manager' ? 0 : role === 'Assistant Manager' ? 1 : 2;
      return order(a.role) - order(b.role) || (a.name?.display || '').localeCompare(b.name?.display || '', 'tr');
    });
  }, [teamStaff]);
  const teamManager = teamOfficials.find(official => official.role === 'Manager' && official.active)
    || teamOfficials.find(official => official.role === 'Manager');
  // Chelsea's 2026/27 feed lists both its interim and first-team manager as active.
  const displayManager = Number(selectedTeamId) === 4 && teamSeason === '2026_27'
    ? teamOfficials.find(official => (official.name?.display || '').toLowerCase() === 'xabi alonso') || teamManager
    : teamManager;

  useEffect(() => {
    if (!selectedManager) return;
    const controller = new AbortController();
    setManagerPerformanceLoading(true);
    setManagerPerformance(null);
    const managerName = selectedManager.name?.display || [selectedManager.name?.first, selectedManager.name?.last].filter(Boolean).join(' ');
    fetch(`/api/teams/manager-performance?team_id=${selectedTeamId}&season=all&manager_name=${encodeURIComponent(managerName)}`, { signal: controller.signal })
      .then(res => res.ok ? res.json() : Promise.reject(new Error('Manager performance request failed')))
      .then(setManagerPerformance)
      .catch(err => { if (err.name !== 'AbortError') setManagerPerformance(null); })
      .finally(() => { if (!controller.signal.aborted) setManagerPerformanceLoading(false); });
    return () => controller.abort();
  }, [selectedManager, selectedTeamId]);
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
      explanation: 'İzin verilen şut, top kazanma, pas arası, müdahale ve uzaklaştırma aksiyonlarının maç başına düzeyini gösterir.',
      keys: [
        'shots_conceded_per_match',
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

  const displayedSquad = useMemo(() => {
    // Prefer profile.squad which has accurate season statistics
    if (profile?.squad?.length) {
      return profile.squad.map(player => ({
        id: player.id,
        name: player.name,
        position: player.position,
        shirt: player.shirt,
        appearances: player.appearances ?? 0,
        starts: player.starts ?? 0,
        goals: player.goals ?? 0,
        assists: player.assists ?? 0,
        yellow_cards: player.yellow_cards ?? 0,
        red_cards: player.red_cards ?? 0,
        photo_url: player.photo_url || null,
        captain: player.captain || false,
      }));
    }
    if (!teamStaff?.players?.length) return [];
    return teamStaff.players.map(player => ({
      id: player.id || player.playerId,
      name: player.name?.display || [player.name?.first, player.name?.last].filter(Boolean).join(' '),
      position: player.info?.position || player.latestPosition,
      shirt: player.info?.shirtNum,
      appearances: player.appearances || 0,
      starts: 0,
      goals: player.goals ?? player.goalsScored ?? 0,
      assists: 0,
      yellow_cards: 0,
      red_cards: 0,
      photo_url: null,
      captain: false,
    }));
  }, [profile?.squad, teamStaff]);

  const displayedSquadCounts = useMemo(() => {
    const counts = { all: displayedSquad.length, G: 0, D: 0, M: 0, F: 0 };
    displayedSquad.forEach(player => {
      const category = getPlayerCategory(player.position);
      if (counts[category] !== undefined) counts[category]++;
    });
    return counts;
  }, [displayedSquad]);

  const filteredSquad = useMemo(() => {
    if (!displayedSquad.length) return [];
    let list = displayedSquad;
    if (selectedSquadTab !== 'all') {
      list = list.filter(p => getPlayerCategory(p.position) === selectedSquadTab);
    }
    return [...list].sort((a, b) => {
      let comparison = 0;
      if (squadSortField === 'name') {
        comparison = (a.name || '').localeCompare(b.name || '', 'tr');
      } else if (squadSortField === 'shirt') {
        const sA = a.shirt != null && !isNaN(Number(a.shirt)) ? Number(a.shirt) : 999;
        const sB = b.shirt != null && !isNaN(Number(b.shirt)) ? Number(b.shirt) : 999;
        comparison = sA - sB;
      } else if (squadSortField === 'position') {
        const posA = getPositionOrder(getPlayerCategory(a.position));
        const posB = getPositionOrder(getPlayerCategory(b.position));
        if (posA !== posB) {
          comparison = posA - posB;
        } else {
          const appsDiff = (b.appearances || 0) - (a.appearances || 0);
          if (appsDiff !== 0) comparison = appsDiff;
          else {
            const sA = a.shirt != null && !isNaN(Number(a.shirt)) ? Number(a.shirt) : 999;
            const sB = b.shirt != null && !isNaN(Number(b.shirt)) ? Number(b.shirt) : 999;
            comparison = sA - sB;
          }
        }
      } else {
        const valA = Number(a[squadSortField]) || 0;
        const valB = Number(b[squadSortField]) || 0;
        comparison = valA - valB;
      }
      return squadSortDirection === 'asc' ? comparison : -comparison;
    });
  }, [displayedSquad, selectedSquadTab, squadSortField, squadSortDirection]);

  const last5Matches = useMemo(() => {
    if (!profile?.matches?.length) return [];
    const played = profile.matches.filter(m => m.team_score !== null && m.team_score !== undefined && m.result);
    return played.slice(-5);
  }, [profile?.matches]);

  return (
    <div className="space-y-6">

      {/* Team Profile Hero & Record Card with Integrated Club Selector */}
      {profile && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-sm relative">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
            
            {/* Left: Badge, Form Dots, Names, Stadium, Manager, League Standing & Club Switcher */}
            <div className="flex items-start sm:items-center gap-4 sm:gap-5 flex-1 min-w-0">
              
              {/* Badge with Click to Switch Team and Form Dots */}
              <div className="flex flex-col items-center shrink-0">
                <button
                  type="button"
                  onClick={() => setIsTeamSelectorOpen(prev => !prev)}
                  title="Kulüp değiştirmek için tıklayın"
                  className="w-20 h-20 rounded-2xl bg-slate-50 border border-slate-200 p-2 flex items-center justify-center shadow-inner hover:border-[#38003c] hover:shadow-md transition-all group relative cursor-pointer"
                >
                  <img 
                    src={currentMeta.badge} 
                    alt={currentMeta.name} 
                    className="w-16 h-16 object-contain group-hover:scale-105 transition-transform" 
                  />
                  <div className="absolute inset-0 bg-black/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <ChevronsUpDown className="w-5 h-5 text-[#38003c] bg-white/90 rounded-full p-0.5 shadow-sm" />
                  </div>
                </button>

                {last5Matches.length > 0 && (
                  <div className="mt-2 flex items-center gap-1" aria-label="Son 5 maç formu" title="Son 5 Maç Formu">
                    {last5Matches.map((m, idx) => {
                      const isW = m.result === 'W';
                      const isD = m.result === 'D';
                      const colors = isW 
                        ? 'bg-emerald-500 text-white' 
                        : isD 
                        ? 'bg-slate-400 text-white' 
                        : 'bg-rose-500 text-white';
                      const label = isW ? 'G' : isD ? 'B' : 'M';
                      return (
                        <span
                          key={m.match_id || idx}
                          className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black shadow-2xs ${colors}`}
                          title={`vs ${m.opponent_name}: ${m.team_score}-${m.opp_score} (${isW ? 'Galibiyet' : isD ? 'Beraberlik' : 'Mağlubiyet'})`}
                        >
                          {label}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Team Info & Actions */}
              <div className="min-w-0 flex-1 relative">
                
                {/* Team Name + Abbr + Quick Switcher Button */}
                <div className="flex flex-wrap items-center gap-2 mb-1.5">
                  <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight truncate">
                    {currentMeta.name}
                  </h2>
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                    {currentMeta.abbr}
                  </span>

                  {/* Kulüp Değiştir Trigger Button & Popover */}
                  <div className="relative inline-block" ref={teamSelectorRef}>
                    <button
                      type="button"
                      onClick={() => setIsTeamSelectorOpen(prev => !prev)}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold transition-all border ${
                        isTeamSelectorOpen
                          ? 'bg-[#38003c] text-white border-[#38003c] shadow-xs'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'
                      }`}
                      title="Premier League takımı seç"
                    >
                      <Shield className="w-3.5 h-3.5 text-[#38003c]" />
                      <span>Takım Değiştir</span>
                      <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isTeamSelectorOpen ? 'rotate-180' : ''}`} />
                    </button>

                    {/* Team Selector Popover Dropdown */}
                    {isTeamSelectorOpen && (
                      <div className="absolute left-0 top-full mt-2 w-72 sm:w-80 bg-white border border-slate-200 rounded-2xl shadow-xl p-3 z-50 animate-in fade-in zoom-in-95 duration-150">
                        {/* Popover Header */}
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
                          <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                            <Trophy className="w-3.5 h-3.5 text-amber-500" />
                            <span>Premier League Kulüpleri</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => setIsTeamSelectorOpen(false)}
                            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg text-xs"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        {/* Search Bar */}
                        <div className="relative mb-2">
                          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                          <input
                            type="text"
                            autoFocus
                            value={teamSearchQuery}
                            onChange={(e) => setTeamSearchQuery(e.target.value)}
                            placeholder="Takım ara (örn: Arsenal, MCI)..."
                            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-2.5 py-1.5 text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-[#38003c] focus:bg-white transition-all"
                          />
                        </div>

                        {/* Clubs List */}
                        <div className="max-h-60 overflow-y-auto space-y-1 scrollbar-thin pr-0.5">
                          {filteredClubs.map(club => {
                            const isSelected = Number(club.id) === Number(selectedTeamId);
                            const standing = standingsMap[club.id];
                            return (
                              <button
                                key={club.id}
                                type="button"
                                onClick={() => {
                                  onSelectTeam?.(club.id);
                                  setIsTeamSelectorOpen(false);
                                  setTeamSearchQuery('');
                                }}
                                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs transition-all text-left ${
                                  isSelected
                                    ? 'bg-[#38003c] text-white font-bold shadow-xs'
                                    : 'hover:bg-slate-100 text-slate-700 hover:text-slate-950 font-medium'
                                }`}
                              >
                                <div className="flex items-center gap-2 truncate">
                                  <img 
                                    src={club.badge} 
                                    alt={club.name} 
                                    className="w-4 h-4 object-contain shrink-0" 
                                    onError={(e) => { e.target.src = '/badges/1.svg'; }}
                                  />
                                  <span className="truncate">{club.name}</span>
                                </div>
                                {standing && (
                                  <span className={`text-[10px] font-mono shrink-0 px-1.5 py-0.5 rounded font-bold ${
                                    isSelected ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-600'
                                  }`}>
                                    #{standing.rank} • {standing.points}P
                                  </span>
                                )}
                              </button>
                            );
                          })}
                          {filteredClubs.length === 0 && (
                            <p className="py-4 text-center text-xs text-slate-400">Eşleşen kulüp bulunamadı.</p>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Stadium & Manager */}
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 font-medium mb-2">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" /> {currentMeta.stadium || 'Premier League Stadium'}
                  </span>
                  {displayManager?.name?.display && (
                    <span className="flex items-center gap-1">
                      <span className="text-slate-300">·</span>
                      <button 
                        type="button" 
                        onClick={() => setSelectedManager(displayManager)} 
                        className="text-violet-800 font-semibold hover:text-violet-950 hover:underline" 
                        aria-label={`${displayManager.name.display} rakip performansını aç`}
                      >
                        {displayManager.name.display}
                      </button>
                    </span>
                  )}
                </div>

                {/* League Standing Badge */}
                {currentStanding && (
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-xl bg-amber-50 border border-amber-200/80 text-amber-900 shadow-2xs">
                    <Trophy className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span className="text-xs font-black">
                      #{currentStanding.rank}. Sıra
                    </span>
                    <span className="text-amber-300">·</span>
                    <span className="text-xs font-mono font-bold text-amber-950">
                      {currentStanding.points} Puan
                    </span>
                    <span className="hidden sm:inline text-[11px] font-mono text-amber-800">
                      ({currentStanding.played} Maç: {currentStanding.won}G {currentStanding.drawn}B {currentStanding.lost}M)
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Season Switcher & Record Pills */}
            <div className="flex flex-col items-start lg:items-end gap-3 w-full lg:w-auto pt-4 lg:pt-0 border-t lg:border-t-0 border-slate-100">
              <div className="relative">
                <label htmlFor="team-profile-season" className="sr-only">Sezon seç</label>
                <select
                  id="team-profile-season"
                  value={teamSeason}
                  onChange={(event) => setTeamSeason(event.target.value)}
                  className="appearance-none min-w-36 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-xl pl-3 pr-9 py-2 text-xs font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#38003c]/30 cursor-pointer"
                >
                  {['2026_27', '2025_26', '2024_25', '2023_24', '2022_23', 'all'].map(season => (
                    <option key={season} value={season}>
                      {season === 'all' ? 'Tüm Sezonlar' : `${season.replace('_', '-') } Sezonu`}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              </div>

              {/* Record Pills */}
              {profile.record && (
                <div className="flex items-center gap-2 font-mono text-xs flex-wrap">
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
        </div>
      )}

      {/* Team Navigation Tabs: Fikstür (Default), Oyun Profili, Kadro Listesi, Teknik Direktör */}
      {profile && (
        <div className="flex items-center gap-1.5 p-1.5 bg-slate-100 rounded-2xl border border-slate-200 overflow-x-auto scrollbar-none">
          <button
            type="button"
            onClick={() => setActiveTeamTab('fixtures')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
              activeTeamTab === 'fixtures'
                ? 'bg-[#38003c] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Calendar className="w-4 h-4" />
            <span>Fikstür & Sonuçlar</span>
            <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
              activeTeamTab === 'fixtures' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
            }`}>
              {profile?.matches?.length || 0}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTeamTab('profile')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
              activeTeamTab === 'profile'
                ? 'bg-[#38003c] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Oyun Profili & Analiz</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTeamTab('squad')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
              activeTeamTab === 'squad'
                ? 'bg-[#38003c] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Kadro Listesi</span>
            <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
              activeTeamTab === 'squad' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
            }`}>
              {displayedSquad.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTeamTab('managers')}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
              activeTeamTab === 'managers'
                ? 'bg-[#38003c] text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Teknik Direktörler</span>
            {managerChanges.length > 0 && (
              <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
                activeTeamTab === 'managers' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
              }`}>
                {managerChanges.length}
              </span>
            )}
          </button>
        </div>
      )}

      {/* TAB: TEKNİK DİREKTÖRLER */}
      {activeTeamTab === 'managers' && (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 bg-gradient-to-r from-violet-50 to-white px-4 py-3.5 sm:px-5">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-100 text-violet-700">
                <Shield className="h-4 w-4" />
              </span>
              <div>
                <h3 className="text-xs font-black text-slate-900">Teknik direktör geçmişi</h3>
                <p className="mt-0.5 text-[10px] text-slate-500">
                  {teamSeason === 'all' ? 'Tüm kayıtlı sezonlar' : `${teamSeason.replace('_', '-')} sezonu`}
                </p>
              </div>
            </div>
            <span className="rounded-full border border-violet-200 bg-white px-2.5 py-1 text-[10px] font-bold text-violet-800">
              {managerChanges.length} değişiklik
            </span>
          </div>
          {managerChanges.length ? (
            <div className="divide-y divide-slate-100">
              {managerChanges.map((change, index) => {
                const interim = change.appointment_type === 'interim';
                return (
                  <div key={`${change.season}-${change.appointment_date}-${index}`} className="flex items-center gap-3 px-4 py-3 sm:px-5">
                    <span className={`h-2.5 w-2.5 shrink-0 rounded-full ring-4 ${interim ? 'bg-amber-400 ring-amber-50' : 'bg-violet-500 ring-violet-50'}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="text-[11px] font-bold text-slate-800">{change.outgoing_manager}</span>
                        <ChevronRight className="h-3 w-3 text-slate-400" />
                        <span className="text-[11px] font-extrabold text-slate-950">{change.incoming_manager}</span>
                      </div>
                      <p className="mt-1 text-[10px] text-slate-500">
                        {new Date(`${change.appointment_date}T12:00:00`).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })}
                        <span className="mx-1.5 text-slate-300">·</span>{change.season.replace('_', '-')}
                        <span className="mx-1.5 text-slate-300">·</span>Hafta {change.gameweek}
                      </p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2 py-1 text-[9px] font-bold ${interim ? 'bg-amber-50 text-amber-800' : 'bg-violet-50 text-violet-800'}`}>
                      {interim ? 'Geçici' : 'Atama'}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="px-4 py-8 text-center text-xs text-slate-500">Bu sezon için kayıtlı teknik direktör değişikliği yok.</p>
          )}
        </section>
      )}

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

      {/* TAB: FİKSTÜR & SONUÇLAR (DEFAULT) */}
      {activeTeamTab === 'fixtures' && (
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-[#38003c]" />
              <h3 className="text-xs sm:text-sm font-black text-slate-900">
                {currentMeta.name} — Sezon Lig Maçları ve Skor Önizlemeleri
              </h3>
            </div>
            <span className="text-xs font-mono font-bold text-slate-600 bg-white px-2.5 py-0.5 rounded-full border border-slate-200 shadow-2xs">
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
            <div className="max-h-[580px] overflow-y-auto divide-y divide-slate-100 scrollbar-thin">
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
                const matchDetails = getCachedTeamData('match_detail', m.match_id, 'all')?.data;
                const redCardsForSide = (side, team) => {
                  const redCardStat = (matchDetails?.team_stats || [])
                    .flatMap(category => category.items || [])
                    .find(item => item.label === 'Kırmızı Kart');
                  const statCount = Number(side === 'home' ? redCardStat?.home : redCardStat?.away);
                  if (Number.isFinite(statCount) && statCount > 0) return statCount;
                  return (matchDetails?.timeline || []).filter(event =>
                    event.type === 'red_card' && (
                      Number(event.team_id) === Number(team.id) ||
                      (event.team_name && event.team_name.toLowerCase() === team.name.toLowerCase())
                    )
                  ).length;
                };
                const homeRedCards = redCardsForSide('home', homeTeam);
                const awayRedCards = redCardsForSide('away', awayTeam);

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
                    onClick={() => {
                      if (onSelectMatch) {
                        onSelectMatch(modalMatchObj);
                      } else {
                        setActiveModalMatch(modalMatchObj);
                      }
                    }}
                    className="px-4 py-2.5 sm:px-6 sm:py-3 hover:bg-slate-50/90 transition-colors cursor-pointer group flex items-center justify-between gap-3 sm:gap-6 text-xs"
                  >
                    {/* 1. Hafta Sayısı */}
                    <div className="w-10 sm:w-12 text-left shrink-0">
                      <span className="font-mono font-bold text-slate-700 bg-slate-100 group-hover:bg-purple-100 group-hover:text-purple-900 group-hover:border-purple-200 px-2 py-0.5 rounded text-[11px] border border-slate-200 transition-colors">
                        H{Math.round(Number(m.gameweek) || 1)}
                      </span>
                    </div>

                    {/* 2. Tarih & Saat */}
                    <div className="min-w-[85px] sm:min-w-[115px] shrink-0 text-left">
                      <span className="font-semibold text-slate-800 text-[11px] sm:text-xs block whitespace-nowrap">
                        {kickoff.date}
                      </span>
                      {kickoff.time && (
                        <span className="font-mono text-slate-400 text-[10px] block whitespace-nowrap">
                          {kickoff.time}
                        </span>
                      )}
                    </div>

                    {/* 3. Karşılaşma ve Skor (Ortada Dengeli) */}
                    <div className="flex items-center justify-center gap-2 sm:gap-4 flex-1 min-w-0">
                      {/* Ev Sahibi */}
                      <div className="flex items-center gap-2 justify-end flex-1 min-w-0 text-right">
                        <span className={`truncate text-xs sm:text-sm ${homeTeam.id === selectedTeamId ? 'font-black text-slate-900' : 'font-medium text-slate-600'}`}>
                          {homeTeam.short || homeTeam.name}
                        </span>
                        {homeRedCards > 0 && (
                          <span className="inline-flex shrink-0 items-center gap-1" title={`${homeRedCards} kırmızı kart`} aria-label={`${homeRedCards} kırmızı kart`}>
                            <span className="inline-block h-3.5 w-2.5 rounded-[2px] border border-rose-700 bg-rose-600 shadow-sm" />
                            {homeRedCards > 1 && <span className="text-[10px] font-black text-rose-700">x{homeRedCards}</span>}
                          </span>
                        )}
                        <img 
                          src={homeTeam.badge} 
                          alt={homeTeam.name} 
                          className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
                          onError={(e) => { e.target.src = '/badges/1.svg'; }}
                        />
                      </div>

                      {/* Skor / Durum */}
                      <div className="shrink-0 flex items-center justify-center min-w-[55px] sm:min-w-[65px]">
                        {isPlayed ? (
                          <span className="px-2.5 py-1 rounded-lg bg-slate-900 text-white font-mono font-black text-xs sm:text-sm tracking-wider shadow-2xs">
                            {homeScore} - {awayScore}
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 font-mono text-xs font-bold border border-slate-200">
                            {kickoff.time || 'vs'}
                          </span>
                        )}
                      </div>

                      {/* Deplasman */}
                      <div className="flex items-center gap-2 justify-start flex-1 min-w-0 text-left">
                        <img 
                          src={awayTeam.badge} 
                          alt={awayTeam.name} 
                          className="w-5 h-5 sm:w-6 sm:h-6 object-contain shrink-0"
                          onError={(e) => { e.target.src = '/badges/1.svg'; }}
                        />
                        <span className={`truncate text-xs sm:text-sm ${awayTeam.id === selectedTeamId ? 'font-black text-slate-900' : 'font-medium text-slate-600'}`}>
                          {awayTeam.short || awayTeam.name}
                        </span>
                        {awayRedCards > 0 && (
                          <span className="inline-flex shrink-0 items-center gap-1" title={`${awayRedCards} kırmızı kart`} aria-label={`${awayRedCards} kırmızı kart`}>
                            <span className="inline-block h-3.5 w-2.5 rounded-[2px] border border-rose-700 bg-rose-600 shadow-sm" />
                            {awayRedCards > 1 && <span className="text-[10px] font-black text-rose-700">x{awayRedCards}</span>}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* 4. Sonuç Rozeti (G/B/M) & Ok */}
                    <div className="flex items-center gap-2 shrink-0 min-w-[45px] justify-end">
                      {isPlayed && (
                        <span className={`w-6 h-6 flex items-center justify-center text-[10px] font-mono font-black rounded-lg border shadow-2xs ${resBadgeClass}`}>
                          {resLabel}
                        </span>
                      )}
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#38003c] group-hover:translate-x-0.5 transition-all" />
                    </div>

                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB: KADRO LİSTESİ */}
      {activeTeamTab === 'squad' && displayedSquad.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-[#38003c]" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                {currentMeta.name} — Kadro Listesi ({selectedSquadTab === 'all' ? displayedSquad.length : `${filteredSquad.length} / ${displayedSquad.length}`} Oyuncu)
              </h3>
              {teamStaff?.players?.length > 0 && <span className="text-[10px] text-slate-400">PulseLive lisanslı kadro</span>}
            </div>

            {/* Position Tabs: Kaleci, Savunma, Orta Saha, Forvet (plus Tümü) */}
            <div
              role="tablist"
              aria-label="Oyuncu pozisyon sekmeleri"
              className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200 gap-1 overflow-x-auto scrollbar-none"
            >
              {SQUAD_POSITION_TABS.map(tab => {
                const isSelected = selectedSquadTab === tab.id;
                const count = displayedSquadCounts[tab.id] || 0;
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
              <div className="overflow-x-auto scrollbar-thin">
                <div className="min-w-[620px] border border-slate-200 rounded-xl bg-white shadow-2xs overflow-hidden">
                  <div className="max-h-[560px] overflow-y-auto divide-y divide-slate-100 scrollbar-thin">
                    {/* Liste Başlık Satırı (Sticky) */}
                    <div className="sticky top-0 z-10 px-3.5 py-2.5 bg-slate-50 text-slate-500 font-bold text-[11px] uppercase tracking-wider flex items-center gap-3 select-none border-b border-slate-200 shadow-2xs">
                      <button
                        type="button"
                        onClick={() => handleSquadSort('shirt')}
                        className="w-10 text-center shrink-0 hover:text-slate-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Forma Numarasına göre sırala"
                      >
                        <span>#</span>
                        {squadSortField === 'shirt' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('name')}
                        className="flex-1 min-w-[170px] text-left hover:text-slate-900 transition-colors flex items-center gap-1 cursor-pointer"
                        title="İsme göre sırala"
                      >
                        <span>Oyuncu</span>
                        {squadSortField === 'name' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('position')}
                        className="w-20 text-center shrink-0 hover:text-slate-900 transition-colors hidden sm:flex items-center justify-center gap-1 cursor-pointer"
                        title="Mevkiye göre sırala"
                      >
                        <span>Mevki</span>
                        {squadSortField === 'position' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('appearances')}
                        className="w-14 text-center shrink-0 hover:text-slate-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Oynadığı toplam maç sayısına göre sırala"
                      >
                        <span>Maç</span>
                        {squadSortField === 'appearances' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('starts')}
                        className="w-14 text-center shrink-0 hover:text-slate-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="İlk 11 başladığı maç sayısına göre sırala"
                      >
                        <span>İlk 11</span>
                        {squadSortField === 'starts' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('goals')}
                        className="w-14 text-center shrink-0 text-emerald-700 hover:text-emerald-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Bu sezon attığı gole göre sırala"
                      >
                        <span>Gol</span>
                        {squadSortField === 'goals' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('assists')}
                        className="w-14 text-center shrink-0 text-sky-700 hover:text-sky-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Bu sezon yaptığı asiste göre sırala"
                      >
                        <span>Asist</span>
                        {squadSortField === 'assists' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('yellow_cards')}
                        className="w-14 text-center shrink-0 text-amber-700 hover:text-amber-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Sarı karta göre sırala"
                      >
                        <span className="w-2 h-3 bg-amber-400 rounded-xs inline-block shadow-2xs" />
                        <span>Sarı</span>
                        {squadSortField === 'yellow_cards' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSquadSort('red_cards')}
                        className="w-14 text-center shrink-0 text-rose-700 hover:text-rose-900 transition-colors flex items-center justify-center gap-1 cursor-pointer"
                        title="Kırmızı karta göre sırala"
                      >
                        <span className="w-2 h-3 bg-rose-500 rounded-xs inline-block shadow-2xs" />
                        <span>Kırmızı</span>
                        {squadSortField === 'red_cards' && (
                          <span className="text-[9px]">{squadSortDirection === 'asc' ? '▲' : '▼'}</span>
                        )}
                      </button>
                    </div>

                    {/* Oyuncu Satırları (Aynı Fikstür Listesi Tasarımı) */}
                    {filteredSquad.map(player => (
                      <div
                        key={player.id}
                        className="px-3.5 py-2.5 hover:bg-slate-50/80 transition-colors flex items-center gap-3 text-xs group"
                      >
                        {/* 1. Forma Numarası */}
                        <div className="w-10 text-center shrink-0 font-mono font-black text-slate-700 text-xs sm:text-sm">
                          {player.shirt != null && player.shirt !== '' ? `#${player.shirt}` : '—'}
                        </div>

                        {/* 2. Oyuncu (Avatar + İsim + Kaptan) */}
                        <div className="flex items-center gap-2.5 flex-1 min-w-[170px]">
                          <PlayerAvatar
                            player={player}
                            size="w-8 h-8 text-xs shrink-0"
                            shape="rounded"
                            fallback="shirt"
                            className="bg-slate-100 border border-slate-200 shadow-2xs shrink-0"
                            imgClassName="object-contain"
                          />
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-slate-900 text-xs sm:text-sm truncate">
                                {player.name}
                              </span>
                              {player.captain && (
                                <span className="shrink-0 px-1 py-0.2 rounded bg-amber-100 text-amber-800 text-[9px] font-black font-mono border border-amber-300">
                                  C
                                </span>
                              )}
                            </div>
                            <div className="sm:hidden text-[10px] text-slate-500 font-medium">
                              {getPositionLabel(player.position)}
                            </div>
                          </div>
                        </div>

                        {/* 3. Mevki */}
                        <div className="w-20 text-center shrink-0 hidden sm:block">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold border ${getPositionBadgeStyle(player.position)}`}>
                            {getPositionLabel(player.position)}
                          </span>
                        </div>

                        {/* 4. Oynadığı Toplam Maç */}
                        <div className="w-14 text-center shrink-0 font-mono font-bold text-slate-800 text-xs">
                          {player.appearances ?? 0}
                        </div>

                        {/* 5. İlk 11 Başladığı */}
                        <div className="w-14 text-center shrink-0 font-mono font-semibold text-slate-600 text-xs">
                          {player.starts ?? 0}
                        </div>

                        {/* 6. Bu Sezon Attığı Gol */}
                        <div className="w-14 text-center shrink-0 font-mono font-black text-emerald-600 text-xs">
                          {(player.goals || 0) > 0 ? (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                              {player.goals}
                            </span>
                          ) : (
                            <span className="text-slate-400">0</span>
                          )}
                        </div>

                        {/* 7. Asist */}
                        <div className="w-14 text-center shrink-0 font-mono font-bold text-sky-600 text-xs">
                          {(player.assists || 0) > 0 ? (
                            <span className="px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 font-bold border border-sky-200">
                              {player.assists}
                            </span>
                          ) : (
                            <span className="text-slate-400">0</span>
                          )}
                        </div>

                        {/* 8. Sarı Kart */}
                        <div className="w-14 text-center shrink-0 font-mono text-xs flex items-center justify-center gap-1">
                          {(player.yellow_cards || 0) > 0 ? (
                            <span className="inline-flex items-center gap-1 font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                              <span className="w-2 h-2.5 bg-amber-400 rounded-xs inline-block" />
                              {player.yellow_cards}
                            </span>
                          ) : (
                            <span className="text-slate-300 font-medium">0</span>
                          )}
                        </div>

                        {/* 9. Kırmızı Kart */}
                        <div className="w-14 text-center shrink-0 font-mono text-xs flex items-center justify-center gap-1">
                          {(player.red_cards || 0) > 0 ? (
                            <span className="inline-flex items-center gap-1 font-bold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                              <span className="w-2 h-2.5 bg-rose-500 rounded-xs inline-block" />
                              {player.red_cards}
                            </span>
                          ) : (
                            <span className="text-slate-300 font-medium">0</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
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

      {selectedManager && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/50 p-4" onMouseDown={event => { if (event.target === event.currentTarget) setSelectedManager(null); }}>
          <section role="dialog" aria-modal="true" aria-label="Teknik direktör rakip performansı" className="w-full max-w-3xl max-h-[88vh] overflow-hidden rounded-3xl bg-slate-50 shadow-2xl ring-1 ring-white/30">
            <header className="relative overflow-hidden bg-gradient-to-br from-[#38003c] via-violet-950 to-slate-900 px-5 py-6 text-white sm:px-7">
              <div className="absolute -right-10 -top-16 h-48 w-48 rounded-full bg-violet-400/10 blur-2xl" />
              <div className="relative flex items-start justify-between gap-4">
                <div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-violet-200">Teknik direktör · Rakip analizi</p><h2 className="mt-2 text-2xl font-black tracking-tight">{selectedManager.name?.display || [selectedManager.name?.first, selectedManager.name?.last].filter(Boolean).join(' ')}</h2><div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-violet-100"><span className="font-semibold">{currentMeta?.name || 'Takım'}</span><span className="text-violet-300">•</span><span>Tüm kayıtlı sezonlar</span></div></div>
                <button type="button" onClick={() => setSelectedManager(null)} aria-label="Kapat" className="rounded-xl border border-white/15 bg-white/10 p-2.5 text-white transition hover:bg-white/20"><X className="h-4 w-4" /></button>
              </div>
            </header>
            {managerPerformanceLoading ? <div className="space-y-4 p-5 sm:p-7"><div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-20 animate-pulse rounded-2xl bg-slate-200" />)}</div><div className="h-48 animate-pulse rounded-2xl bg-slate-200" /></div> : !managerPerformance?.total?.matches ? <div className="px-6 py-14 text-center"><span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-100 text-violet-700"><Activity className="h-5 w-5" /></span><h3 className="mt-4 text-sm font-extrabold text-slate-900">Henüz maç kaydı yok</h3><p className="mx-auto mt-1 max-w-xs text-xs leading-5 text-slate-500">Bu teknik direktör için kayıtlı sezonlarda tamamlanmış maç bulunamadı.</p></div> : <div className="max-h-[calc(88vh-116px)] space-y-6 overflow-y-auto p-4 sm:p-7">
              <section aria-label="Toplam teknik direktör istatistikleri">
                <div className="mb-3 flex items-end justify-between gap-2"><div><h3 className="text-sm font-black text-slate-900">Kariyer özeti</h3><p className="mt-0.5 text-[11px] text-slate-500">Tüm kayıtlı lig maçları</p></div><span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-semibold text-slate-500">{managerPerformance.total.matches} maç</span></div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">{[['Maç', 'matches', 'text-slate-900'], ['Galibiyet', 'wins', 'text-emerald-700'], ['Beraberlik', 'draws', 'text-slate-700'], ['Mağlubiyet', 'losses', 'text-rose-700'], ['Attığı gol', 'gf', 'text-violet-800'], ['Yediği gol', 'ga', 'text-amber-700']].map(([label, key, color]) => <div key={key} className="rounded-2xl border border-slate-200/80 bg-white p-3.5 shadow-sm sm:p-4"><p className="text-[10px] font-bold text-slate-500">{label}</p><p className={`mt-1 text-2xl font-black tabular-nums ${color}`}>{managerPerformance.total[key]}</p></div>)}</div>
              </section>
              <section aria-label="Rakiplere göre istatistikler">
                <div className="mb-3 flex items-end justify-between"><div><h3 className="text-sm font-black text-slate-900">Rakiplere karşı</h3><p className="mt-0.5 text-[11px] text-slate-500">En çok karşılaşılan rakipler önce</p></div><span className="text-[10px] font-medium text-slate-400">{managerPerformance.opponents.length} takım</span></div>
                <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                  <div className="hidden grid-cols-[minmax(140px,1.5fr)_repeat(6,minmax(52px,1fr))] items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-3 text-[9px] font-bold uppercase tracking-wide text-slate-500 sm:grid"><span>Rakip takım</span><span className="text-center">Maç</span><span className="text-center">Galibiyet</span><span className="text-center">Beraberlik</span><span className="text-center">Mağlubiyet</span><span className="text-center">Attığı</span><span className="text-center">Yediği</span></div>
                  <div className="divide-y divide-slate-100">{[...managerPerformance.opponents].sort((a, b) => b.matches - a.matches || a.opponent.localeCompare(b.opponent, 'tr')).map(item => { const opponentTeam = getTeam(item.opponent_id, item.opponent); return <div key={item.opponent_id} className="grid grid-cols-3 items-center gap-x-2 gap-y-3 px-4 py-3.5 sm:grid-cols-[minmax(140px,1.5fr)_repeat(6,minmax(52px,1fr))] sm:gap-2"><div className="col-span-3 flex items-center gap-2 sm:col-span-1"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-100 bg-white p-1.5"><img src={opponentTeam.badge} alt="" className="h-full w-full object-contain" loading="lazy" /></span><span className="text-xs font-extrabold text-slate-800">{item.opponent}</span></div>{[['Maç', 'matches', 'text-slate-800'], ['Galibiyet', 'wins', 'text-emerald-700'], ['Beraberlik', 'draws', 'text-slate-600'], ['Mağlubiyet', 'losses', 'text-rose-700'], ['Attığı gol', 'gf', 'text-violet-800'], ['Yediği gol', 'ga', 'text-amber-700']].map(([label, key, color]) => <div key={key} className="flex items-center justify-between rounded-lg bg-slate-50 px-2 py-1.5 sm:block sm:bg-transparent sm:p-0 sm:text-center"><span className="text-[9px] font-semibold text-slate-400 sm:hidden">{label}</span><span className={`text-xs font-bold tabular-nums ${color}`}>{item[key]}</span></div>)}</div>; })}</div>
                </div>
              </section>
            </div>}
          </section>
        </div>
      )}

    </div>
  );
}
