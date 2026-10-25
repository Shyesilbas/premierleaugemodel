import { Trophy } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';
import { useCompetition } from '../../context/CompetitionContext';

// Zone ids come from the API (src/api/routes/fixtures.py); the row colour follows the team's overall zone.
const ZONE_BAR = {
  direct_r16: 'bg-status-success',
  champions_league: 'bg-status-info',
  playoff: 'bg-status-info',
  europa_league: 'bg-status-warning',
  relegation: 'bg-status-error',
  eliminated: 'bg-border-focus',
};

// Group stage: green stripe for the teams going through, yellow for the Europa League route; no stripe when out.
const GROUP_ZONE_BAR = {
  direct_r16: 'bg-status-success',
  playoff: 'bg-status-warning',
};

const LEGENDS = {
  league: [
    { dot: 'bg-status-success', label: 'Son 16 Turu - Doğrudan Katılım (1-8)' },
    { dot: 'bg-status-info', label: 'Play-off Eleme Turu (9-24)' },
    { dot: 'bg-border-focus', label: 'Elendi (25-36)' },
  ],
  groups_champions_league: [
    { dot: 'bg-status-success', label: 'Üst tur: Son 16 (1-2)' },
    { dot: 'bg-status-warning', label: 'Avrupa Ligi play-off (3)' },
  ],
  groups_europa_league: [
    { dot: 'bg-status-success', label: 'Üst tur: Son 16 (1)' },
    { dot: 'bg-status-warning', label: 'Play-off turu (2)' },
  ],
  premier_league: [
    { dot: 'bg-status-info', label: 'Şampiyonlar Ligi (1-4)' },
    { dot: 'bg-status-warning', label: 'Avrupa Ligi (5)' },
    { dot: 'bg-status-error', label: 'Küme Düşme Hattı (18-20)' },
  ],
};

function StandingsTable({ rows, standingsType, showZones, grouped = false, onSelectTeam }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left border-collapse">
        <thead>
          <tr className="border-b border-border-light text-text-muted font-medium">
            <th className="py-2.5 px-3 text-center w-10">#</th>
            <th className="py-2.5 px-3">Takım</th>
            <th className="py-2.5 px-2 text-center w-10">O</th>
            <th className="py-2.5 px-2 text-center w-10">G</th>
            <th className="py-2.5 px-2 text-center w-10">B</th>
            <th className="py-2.5 px-2 text-center w-10">M</th>
            <th className="py-2.5 px-2 text-center w-10 hidden md:table-cell">AG</th>
            <th className="py-2.5 px-2 text-center w-10 hidden md:table-cell">YG</th>
            <th className="py-2.5 px-2 text-center w-12" title="Averaj">AV</th>
            <th className="py-2.5 px-3 text-center w-14 font-semibold text-text-primary" title="Puan">P</th>
            <th className="py-2.5 px-3 text-center w-36 hidden sm:table-cell" title="Son 5 Maç">Form</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-light tabular-nums">
          {rows.map((t, idx) => {
            const rank = idx + 1;
            const stats = standingsType === 'all' ? t : (t[standingsType] || t);
            const zoneBar = showZones ? (grouped ? GROUP_ZONE_BAR[t.zone] : ZONE_BAR[t.zone]) : null;
            const gdFormatted = stats.gd > 0 ? `+${stats.gd}` : `${stats.gd}`;

            return (
              <tr key={t.id} title={showZones ? t.zone_label || undefined : undefined} className="hover:bg-background-tertiary transition-colors">
                <td className="relative py-2.5 px-3 text-center font-medium text-text-secondary">
                  {zoneBar && <span aria-hidden="true" className={`absolute inset-y-0 left-0 ${grouped ? 'w-1' : 'w-0.5'} ${zoneBar}`} />}
                  <span className={`inline-flex items-center justify-center w-5 h-5 rounded-sm text-xs font-medium ${
                    rank === 1 ? 'bg-background-tertiary text-text-primary border border-border' : 'text-text-muted'
                  }`}>
                    {rank}
                  </span>
                </td>

                <td className="py-2.5 px-3 font-sans">
                  <div className="flex items-center gap-2.5">
                    <img src={t.badge} alt={t.name} className="w-5 h-5 object-contain shrink-0" onError={handleTeamBadgeError} />
                    <button
                      type="button"
                      onClick={() => onSelectTeam?.(t.id)}
                      className="font-medium text-text-primary truncate text-left hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-border-focus"
                      aria-label={`${t.name} takım profiline git`}
                    >
                      {t.name}
                    </button>
                    {t.abbr && <span className="text-xs tabular-nums font-medium text-text-muted hidden lg:inline">{t.abbr}</span>}
                  </div>
                </td>

                <td className="py-2.5 px-2 text-center font-medium text-text-primary">{stats.played}</td>
                <td className="py-2.5 px-2 text-center text-text-secondary">{stats.won}</td>
                <td className="py-2.5 px-2 text-center text-text-secondary">{stats.drawn}</td>
                <td className="py-2.5 px-2 text-center text-text-secondary">{stats.lost}</td>
                <td className="py-2.5 px-2 text-center text-text-muted hidden md:table-cell">{stats.gf}</td>
                <td className="py-2.5 px-2 text-center text-text-muted hidden md:table-cell">{stats.ga}</td>
                <td className={`py-2.5 px-2 text-center font-medium ${
                  stats.gd > 0 ? 'text-status-success' : stats.gd < 0 ? 'text-status-error' : 'text-text-secondary'
                }`}>
                  {gdFormatted}
                </td>
                <td className="py-2.5 px-3 text-center">
                  <span className="inline-block px-2 py-0.5 rounded-sm bg-primary text-white font-semibold text-xs">{stats.points}</span>
                </td>
                <td className="py-2.5 px-3 text-center hidden sm:table-cell">
                  <div className="flex items-center justify-center gap-1 font-sans">
                    {(t.form || []).map((res, fIdx) => {
                      const bg = res === 'W' ? 'bg-status-success text-white' : res === 'D' ? 'bg-text-muted text-white' : 'bg-status-error text-white';
                      const label = res === 'W' ? 'G' : res === 'D' ? 'B' : 'M';
                      return (
                        <span
                          key={fIdx}
                          className={`w-4 h-4 rounded-full flex items-center justify-center text-xs font-semibold ${bg}`}
                          title={res === 'W' ? 'Galibiyet' : res === 'D' ? 'Beraberlik' : 'Mağlubiyet'}
                        >
                          {label}
                        </span>
                      );
                    })}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// One group's table, shown under the fixtures once a group is picked.
export function GroupStandingsPanel({ group, rows, loading, onSelectTeam }) {
  const { competitionKey } = useCompetition();
  const legend = LEGENDS[`groups_${competitionKey}`] || [];
  return (
    <section aria-label={`Grup ${group} puan durumu`} className="bg-background-primary border border-border rounded p-4 sm:p-5 space-y-3">
      <h3 className="text-sm font-semibold text-text-primary">Grup {group} puan durumu</h3>
      {loading ? (
        <div className="space-y-2">
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
        </div>
      ) : rows.length === 0 ? (
        <p className="py-6 text-center text-sm text-text-secondary">Bu grup için puan durumu verisi bulunamadı.</p>
      ) : (
        <StandingsTable rows={rows} standingsType="all" showZones grouped onSelectTeam={onSelectTeam} />
      )}
      <div className="pt-3 border-t border-border-light flex flex-wrap items-center gap-4 text-xs text-text-secondary font-medium">
        {legend.map(item => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span className={`w-2.5 h-2.5 rounded-sm ${item.dot}`} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function FixturesStandingsView({ displayedStandings, groups = [], standingsType, setStandingsType, loadingStandings, onSelectTeam }) {
  const { competitionKey, activeCompetition } = useCompetition();
  const isGrouped = groups.length > 0;
  const legend = isGrouped ? LEGENDS[`groups_${competitionKey}`] : competitionKey === 'premier_league' ? LEGENDS.premier_league : LEGENDS.league;
  const subtitle = isGrouped
    ? `Grup Aşaması (${groups.length} grup)`
    : competitionKey === 'premier_league' ? 'Sezon Sıralaması' : 'Lig Aşaması (36 Takım Sıralaması)';
  const sections = isGrouped
    ? groups.map(name => ({ title: `Grup ${name}`, rows: displayedStandings.filter(team => team.group === name) }))
    : [{ title: null, rows: displayedStandings }];

  return (
    <div className="bg-background-primary border border-border rounded p-4 sm:p-5 space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-border-light">
        <div className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-text-primary" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">{activeCompetition?.name || 'Lig'} Puan Durumu</h3>
            <p className="text-xs text-text-secondary">{subtitle}</p>
          </div>
        </div>

        <div className="flex items-center bg-background-tertiary p-0.5 rounded border border-border gap-1 self-stretch sm:self-auto justify-center">
          {[['all', 'Genel'], ['home', 'İç Saha'], ['away', 'Deplasman']].map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setStandingsType(id)}
              className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
                standingsType === id ? 'bg-primary text-white' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loadingStandings ? (
        <div className="py-12 space-y-2">
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
        </div>
      ) : displayedStandings.length === 0 ? (
        <div className="py-12 text-center text-text-secondary text-sm">Puan durumu verisi bulunamadı.</div>
      ) : (
        <div className={isGrouped ? 'grid grid-cols-1 xl:grid-cols-2 gap-5' : ''}>
          {sections.map(section => (
            <section key={section.title || 'table'} aria-label={section.title || undefined} className="space-y-2">
              {section.title && <h4 className="text-xs font-semibold text-text-primary px-1">{section.title}</h4>}
              <StandingsTable rows={section.rows} standingsType={standingsType} showZones={standingsType === 'all'} grouped={isGrouped} onSelectTeam={onSelectTeam} />
            </section>
          ))}
        </div>
      )}

      <div className="pt-3 border-t border-border-light flex flex-wrap items-center justify-between gap-3 text-xs text-text-secondary font-medium">
        <div className="flex flex-wrap items-center gap-4">
          {legend.map(item => (
            <div key={item.label} className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-sm ${item.dot}`} />
              <span>{item.label}</span>
            </div>
          ))}
        </div>
        <div className="tabular-nums text-xs text-text-muted">
          O: Oynanan • G: Galibiyet • B: Beraberlik • M: Mağlubiyet • AV: Averaj • P: Puan
        </div>
      </div>
    </div>
  );
}
