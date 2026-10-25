import { Trophy } from 'lucide-react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';

export default function FixturesStandingsView({ displayedStandings, standingsType, setStandingsType, loadingStandings, onSelectTeam }) {
  return (
    <div className="bg-background-primary border border-border rounded p-4 sm:p-5 space-y-4">
      {/* Table Header: Title + Overall/Home/Away toggle */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-border-light">
        <div className="flex items-center gap-2">
          <Trophy className="w-5 h-5 text-text-primary" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              Premier League Puan Durumu
            </h3>
            <p className="text-xs text-text-secondary">
              Sezon Sıralaması
            </p>
          </div>
        </div>

        {/* Genel / İç Saha / Deplasman Filtresi */}
        <div className="flex items-center bg-background-tertiary p-0.5 rounded border border-border gap-1 self-stretch sm:self-auto justify-center">
          <button
            onClick={() => setStandingsType('all')}
            className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
              standingsType === 'all'
                ? 'bg-primary text-white'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Genel
          </button>
          <button
            onClick={() => setStandingsType('home')}
            className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
              standingsType === 'home'
                ? 'bg-primary text-white'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            İç Saha
          </button>
          <button
            onClick={() => setStandingsType('away')}
            className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-colors ${
              standingsType === 'away'
                ? 'bg-primary text-white'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            Deplasman
          </button>
        </div>
      </div>

      {/* Table Content */}
      {loadingStandings ? (
        <div className="py-12 space-y-2">
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
          <div className="h-8 bg-background-tertiary animate-pulse rounded" />
        </div>
      ) : displayedStandings.length === 0 ? (
        <div className="py-12 text-center text-xs text-text-secondary">
          Puan tablosu verisi bulunamadı.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-border text-xs font-semibold text-text-secondary bg-background-tertiary">
                <th className="py-2.5 px-3 w-12 text-center">#</th>
                <th className="py-2.5 px-3 min-w-44">Kulüp</th>
                <th className="py-2.5 px-2 text-center w-10" title="Oynanan Maç">O</th>
                <th className="py-2.5 px-2 text-center w-10" title="Galibiyet">G</th>
                <th className="py-2.5 px-2 text-center w-10" title="Beraberlik">B</th>
                <th className="py-2.5 px-2 text-center w-10" title="Mağlubiyet">M</th>
                <th className="py-2.5 px-2 text-center w-12 hidden md:table-cell" title="Attığı Gol">AG</th>
                <th className="py-2.5 px-2 text-center w-12 hidden md:table-cell" title="Yediği Gol">YG</th>
                <th className="py-2.5 px-2 text-center w-12" title="Averaj">AV</th>
                <th className="py-2.5 px-3 text-center w-14 font-semibold text-text-primary" title="Puan">P</th>
                <th className="py-2.5 px-3 text-center w-36 hidden sm:table-cell" title="Son 5 Maç">Form</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light tabular-nums">
              {displayedStandings.map((t, idx) => {
                const rank = idx + 1;
                const stats = standingsType === 'all' ? t : (t[standingsType] || t);
                const isUcl = rank <= 4;
                const isUel = rank === 5;
                const isRelegation = rank >= 18;

                const borderClass = isUcl 
                  ? 'border-l-2 border-l-status-info' 
                  : isUel 
                  ? 'border-l-2 border-l-status-warning' 
                  : isRelegation 
                  ? 'border-l-2 border-l-status-error' 
                  : 'border-l-2 border-l-transparent';

                const gdFormatted = stats.gd > 0 ? `+${stats.gd}` : `${stats.gd}`;

                return (
                  <tr 
                    key={t.id}
                    className={`hover:bg-background-tertiary transition-colors ${borderClass}`}
                  >
                    <td className="py-2.5 px-3 text-center font-medium text-text-secondary">
                      <span className={`inline-flex items-center justify-center w-5 h-5 rounded-sm text-xs font-medium ${
                        rank === 1 ? 'bg-background-tertiary text-text-primary border border-border' : 'text-text-muted'
                      }`}>
                        {rank}
                      </span>
                    </td>

                    <td className="py-2.5 px-3 font-sans">
                      <div className="flex items-center gap-2.5">
                        <img 
                          src={t.badge} 
                          alt={t.name} 
                          className="w-5 h-5 object-contain shrink-0"
                          onError={handleTeamBadgeError}
                        />
                        <button
                          type="button"
                          onClick={() => onSelectTeam?.(t.id)}
                          className="font-medium text-text-primary truncate text-left hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-border-focus"
                          aria-label={`${t.name} takım profiline git`}
                        >
                          {t.name}
                        </button>
                        {t.abbr && (
                          <span className="text-xs tabular-nums font-medium text-text-muted hidden lg:inline">
                            {t.abbr}
                          </span>
                        )}
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
                      <span className="inline-block px-2 py-0.5 rounded-sm bg-primary text-white font-semibold text-xs">
                        {stats.points}
                      </span>
                    </td>

                    <td className="py-2.5 px-3 text-center hidden sm:table-cell">
                      <div className="flex items-center justify-center gap-1 font-sans">
                        {(t.form || []).map((res, fIdx) => {
                          const bg = res === 'W' 
                            ? 'bg-status-success text-white' 
                            : res === 'D' 
                            ? 'bg-text-muted text-white' 
                            : 'bg-status-error text-white';
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
      )}

      {/* Legend Footer */}
      <div className="pt-3 border-t border-border-light flex flex-wrap items-center justify-between gap-3 text-xs text-text-secondary font-medium">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-status-info" />
            <span>Şampiyonlar Ligi (1-4)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-status-warning" />
            <span>Avrupa Ligi (5)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-status-error" />
            <span>Küme Düşme Hattı (18-20)</span>
          </div>
        </div>
        <div className="tabular-nums text-xs text-text-muted">
          O: Oynanan • G: Galibiyet • B: Beraberlik • M: Mağlubiyet • AV: Averaj • P: Puan
        </div>
      </div>
    </div>
  );
}
