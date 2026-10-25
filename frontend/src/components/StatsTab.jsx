import { useEffect, useState } from 'react';
import { BarChart3, ChevronDown } from 'lucide-react';
import { getLeagueStats } from '../services/statsService';
import { formatSeasonLabel } from '../utils/dateFormatters';
import Skeleton from './common/Skeleton';
import InlineError from './common/InlineError';
import EmptyState from './common/EmptyState';
import TeamForm from './TeamForm';
import TeamOfScope from './stats/TeamOfScope';
import GoalMinutes from './stats/GoalMinutes';
import { BlockHeader, PlayerCell, RankTable, StatsCard, TeamCell } from './stats/statsParts';

const SEASONS = ['2026_27', '2025_26', '2024_25', '2023_24', '2022_23'];
const dash = (value) => (value === null || value === undefined ? '—' : value);

const SELECT_CLASS = 'appearance-none h-10 pl-3 pr-9 rounded border border-border bg-background-primary text-sm font-medium text-text-primary cursor-pointer transition-colors duration-150 ease-out hover:border-card-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus';

function SelectField({ id, label, value, onChange, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs text-text-secondary">{label}</label>
      <div className="relative">
        <select id={id} value={value} onChange={onChange} className={SELECT_CLASS}>{children}</select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
      </div>
    </div>
  );
}

function ScopeButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`h-10 px-4 text-sm font-medium transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-border-focus ${
        active ? 'bg-primary text-white' : 'bg-background-primary text-text-secondary hover:text-text-primary'
      }`}
    >
      {children}
    </button>
  );
}

function StatsSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true" aria-label="Yükleniyor">
      <div className="grid lg:grid-cols-5 gap-4">
        <Skeleton className="h-80 w-full lg:col-span-2" />
        <Skeleton className="h-80 w-full lg:col-span-3" />
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-64 w-full" />
        ))}
      </div>
    </div>
  );
}

function Grid({ children }) {
  return <div className="grid md:grid-cols-2 gap-4 items-start">{children}</div>;
}

function Block({ title, description, children }) {
  return (
    <section className="flex flex-col gap-4">
      <BlockHeader title={title} description={description} />
      {children}
    </section>
  );
}

function Movers({ movers }) {
  const lists = [
    { title: 'Yükselenler', rows: movers.risers, tone: 'text-status-success', sign: '+' },
    { title: 'Düşenler', rows: movers.fallers, tone: 'text-status-error', sign: '' },
  ];
  if (!movers.reference_gameweek) {
    return <p className="px-4 py-8 text-center text-sm text-text-secondary">Karşılaştırma için yeterli hafta yok.</p>;
  }
  return (
    <div className="grid sm:grid-cols-2 sm:divide-x divide-border-light">
      {lists.map(({ title, rows, tone, sign }) => (
        <div key={title} className="p-4 flex flex-col gap-2">
          <span className="text-xs text-text-secondary">{title}</span>
          {rows.length === 0 ? (
            <span className="text-sm text-text-tertiary">Değişen takım yok.</span>
          ) : (
            <ul className="flex flex-col gap-2">
              {rows.map(row => (
                <li key={row.team.id} className="flex items-center justify-between gap-3 text-sm">
                  <TeamCell team={row.team} />
                  <span className="flex items-center gap-2 shrink-0 tabular-nums">
                    <span className="text-xs text-text-tertiary">{row.previous_rank}. → {row.rank}.</span>
                    <span className={`font-medium ${tone}`}>{sign}{row.change}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

export function StatsContent({ data, selectedSeason, pending, header, openMatch }) {
  const isWeek = data.scope === 'week';
  const scopeLabel = isWeek ? `Hafta ${data.gameweek}` : `${formatSeasonLabel(selectedSeason, '/')} sezonu`;
  const cumulativeLabel = isWeek ? `Hafta ${data.gameweek} itibarıyla` : 'Sezon geneli';
  const noun = isWeek ? 'Haftanın' : 'Sezonun';

  const goalColumns = [
    { key: 'player', label: 'Oyuncu', render: row => <PlayerCell player={row} /> },
    { key: 'goals', label: 'Gol', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.goals}</span> },
    { key: 'assists', label: 'Asist', align: 'right', render: row => row.assists },
    ...(isWeek ? [{ key: 'season', label: 'Sezon golü', align: 'right', hideOnMobile: true, render: row => row.season_goals }] : []),
  ];
  const assistColumns = [
    { key: 'player', label: 'Oyuncu', render: row => <PlayerCell player={row} /> },
    { key: 'assists', label: 'Asist', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.assists}</span> },
    { key: 'goals', label: 'Gol', align: 'right', render: row => row.goals },
    ...(isWeek ? [{ key: 'season', label: 'Sezon asisti', align: 'right', hideOnMobile: true, render: row => row.season_assists }] : []),
  ];
  const venueColumns = [
    { key: 'team', label: 'Takım', render: row => <TeamCell team={row.team} /> },
    { key: 'played', label: 'O', align: 'right', render: row => row.played },
    { key: 'won', label: 'G', align: 'right', hideOnMobile: true, render: row => row.won },
    { key: 'drawn', label: 'B', align: 'right', hideOnMobile: true, render: row => row.drawn },
    { key: 'lost', label: 'M', align: 'right', hideOnMobile: true, render: row => row.lost },
    { key: 'goals', label: 'A-Y', align: 'right', render: row => `${row.gf}-${row.ga}` },
    { key: 'points', label: 'P', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.points}</span> },
  ];

  const venue = data.venue;
  const venueMatches = venue.home_wins + venue.draws + venue.away_wins;
  const pct = (value) => (venueMatches ? Math.round((value / venueMatches) * 100) : 0);

  return (
    <div className="flex flex-col gap-8 pb-12">
      {header}

      <div className={`flex flex-col gap-8 transition-opacity duration-150 ease-out motion-reduce:transition-none ${pending ? 'opacity-60' : ''}`} aria-busy={pending}>
        <Block title={isWeek ? 'Haftanın özeti' : 'Sezonun özeti'} description={`${scopeLabel} · ${data.matches_in_scope} maç`}>
          <div className="grid lg:grid-cols-5 gap-4 items-start">
            <StatsCard title={`${noun} öne çıkanları`} meta={scopeLabel} className="lg:col-span-2">
              {data.highlights.length === 0 ? (
                <p className="px-4 py-8 text-center text-sm text-text-secondary">Öne çıkan bir olay yok.</p>
              ) : (
                <ul className="divide-y divide-border-light">
                  {data.highlights.map((item, index) => {
                    const body = (
                      <>
                        <span className="block text-sm font-medium text-text-primary">{item.title}</span>
                        <span className="block text-sm text-text-secondary">{item.detail}</span>
                      </>
                    );
                    return (
                      <li key={`${item.kind}-${index}`}>
                        {item.match ? (
                          <button
                            type="button"
                            onClick={() => openMatch(item.match)}
                            className="w-full px-4 py-3 text-left transition-colors duration-150 ease-out hover:bg-background-tertiary cursor-pointer focus:outline-none focus-visible:bg-background-tertiary"
                          >
                            {body}
                          </button>
                        ) : (
                          <div className="px-4 py-3">{body}</div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </StatsCard>

            <div className="lg:col-span-3">
              <TeamOfScope
                data={data.team_of_scope}
                title={`${noun} kadrosu`}
                scopeLabel={isWeek ? `${scopeLabel} maçlarına göre.` : 'Sezon ortalamasına göre.'}
              />
            </div>
          </div>
        </Block>

        <Block title="Takımlar" description="Hücum, savunma, form ve ev sahibi ile deplasman performansı.">
          <Grid>
            <StatsCard title="En iyi hücum" meta={scopeLabel}>
              <RankTable
                rowKey={row => row.team.id}
                rows={data.attack}
                columns={[
                  { key: 'team', label: 'Takım', render: row => <TeamCell team={row.team} /> },
                  { key: 'goals', label: 'Gol', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.goals}</span> },
                  { key: 'xg', label: 'xG', align: 'right', hideOnMobile: true, render: row => dash(row.xg) },
                  { key: 'sot', label: 'İsabetli şut', align: 'right', hideOnMobile: true, render: row => row.shots_on_target },
                ]}
              />
            </StatsCard>
            <StatsCard title="En iyi savunma" meta={scopeLabel}>
              <RankTable
                rowKey={row => row.team.id}
                rows={data.defence}
                columns={[
                  { key: 'team', label: 'Takım', render: row => <TeamCell team={row.team} /> },
                  { key: 'conceded', label: 'Yenen gol', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.conceded}</span> },
                  { key: 'clean', label: 'Gol yemeden', align: 'right', render: row => row.clean_sheets },
                  { key: 'xga', label: 'xG karşı', align: 'right', hideOnMobile: true, render: row => dash(row.xga) },
                ]}
              />
            </StatsCard>

            <StatsCard title="Form tablosu" meta={`${cumulativeLabel} · son 5 maç`}>
              <RankTable
                rowKey={row => row.team.id}
                rows={data.form}
                columns={[
                  { key: 'team', label: 'Takım', render: row => <TeamCell team={row.team} /> },
                  { key: 'form', label: 'Form', align: 'center', render: row => <span className="inline-flex"><TeamForm results={row.results} /></span> },
                  { key: 'points', label: 'P', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.points}</span> },
                  { key: 'gd', label: 'Averaj', align: 'right', hideOnMobile: true, render: row => (row.goal_difference > 0 ? `+${row.goal_difference}` : row.goal_difference) },
                ]}
              />
            </StatsCard>
            <StatsCard
              title="Sıralama hareketi"
              meta={data.movers.reference_gameweek ? `Hafta ${data.movers.reference_gameweek} sonrasına göre` : cumulativeLabel}
            >
              <Movers movers={data.movers} />
            </StatsCard>

            <StatsCard title="Ev sahibi gücü" meta={cumulativeLabel}>
              <RankTable rowKey={row => row.team.id} rows={venue.home} columns={venueColumns} />
            </StatsCard>
            <StatsCard title="Deplasman gücü" meta={cumulativeLabel}>
              <RankTable rowKey={row => row.team.id} rows={venue.away} columns={venueColumns} />
            </StatsCard>
          </Grid>

          <p className="text-sm text-text-secondary tabular-nums">
            Lig genelinde ({cumulativeLabel.toLowerCase()}): ev sahibi galibiyeti %{pct(venue.home_wins)}, beraberlik %{pct(venue.draws)}, deplasman galibiyeti %{pct(venue.away_wins)}.
          </p>

          <GoalMinutes data={data.goal_minutes} isWeek={isWeek} gameweek={data.gameweek} cumulativeLabel={cumulativeLabel} />
        </Block>

        <Block title="Oyuncular" description="Gol ve asist krallığı, süre alanlar, genç oyuncular ve kaleciler.">
          <Grid>
            <StatsCard title={isWeek ? 'Haftanın golcüleri' : 'Gol krallığı'} meta={scopeLabel}>
              <RankTable rowKey={row => row.id} rows={data.top_scorers} columns={goalColumns} limit={5} emptyText="Bu kapsamda gol atan oyuncu yok." />
            </StatsCard>
            <StatsCard title={isWeek ? 'Haftanın asistçileri' : 'Asist krallığı'} meta={scopeLabel}>
              <RankTable rowKey={row => row.id} rows={data.top_assists} columns={assistColumns} limit={5} emptyText="Bu kapsamda asist yapan oyuncu yok." />
            </StatsCard>

            <StatsCard title="En çok süre alan oyuncular" meta={cumulativeLabel}>
              <RankTable
                rowKey={row => row.id}
                rows={data.minutes}
                columns={[
                  { key: 'player', label: 'Oyuncu', render: row => <PlayerCell player={row} /> },
                  { key: 'minutes', label: 'Dakika', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.minutes}</span> },
                  { key: 'matches', label: 'Maç', align: 'right', hideOnMobile: true, render: row => row.matches },
                  { key: 'starts', label: 'İlk 11', align: 'right', hideOnMobile: true, render: row => row.starts },
                ]}
              />
            </StatsCard>
            <StatsCard title={`Genç oyuncular (${data.young_players.max_age} yaş ve altı)`} meta={cumulativeLabel}>
              <RankTable
                rowKey={row => row.id}
                rows={data.young_players.players}
                emptyText={data.young_players.available ? 'Bu kapsamda genç oyuncu yok.' : 'Bu sezon için yaş verisi yok.'}
                columns={[
                  { key: 'player', label: 'Oyuncu', render: row => <PlayerCell player={row} /> },
                  { key: 'age', label: 'Yaş', align: 'right', render: row => row.age },
                  { key: 'minutes', label: 'Dakika', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.minutes}</span> },
                  { key: 'ga', label: 'Gol + asist', align: 'right', hideOnMobile: true, render: row => row.goals + row.assists },
                ]}
              />
            </StatsCard>

            <StatsCard title="Gol yememe krallığı" meta={cumulativeLabel} className="md:col-span-2">
              <RankTable
                rowKey={row => row.id}
                rows={data.goalkeepers}
                columns={[
                  { key: 'player', label: 'Kaleci', render: row => <PlayerCell player={row} /> },
                  { key: 'clean', label: 'Gol yemeden', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.clean_sheets}</span> },
                  { key: 'conceded', label: 'Yenen gol', align: 'right', render: row => row.conceded },
                  { key: 'saves', label: 'Kurtarış', align: 'right', render: row => row.saves },
                  { key: 'matches', label: 'Maç', align: 'right', hideOnMobile: true, render: row => row.matches },
                ]}
              />
            </StatsCard>
          </Grid>
        </Block>

        <Block title="Disiplin ve hakemler" description="Kart görenler ve hakemlerin kart eğilimi.">
          <Grid>
            <StatsCard title="En çok kart gören oyuncular" meta={scopeLabel}>
              <RankTable
                rowKey={row => row.id}
                rows={data.discipline.players}
                emptyText="Bu kapsamda kart gören oyuncu yok."
                columns={[
                  { key: 'player', label: 'Oyuncu', render: row => <PlayerCell player={row} /> },
                  { key: 'yellow', label: 'Sarı', align: 'right', render: row => row.yellow },
                  { key: 'red', label: 'Kırmızı', align: 'right', render: row => <span className={row.red > 0 ? 'font-semibold text-status-error' : 'text-text-muted'}>{row.red}</span> },
                ]}
              />
            </StatsCard>
            <StatsCard title="En çok kart gören takımlar" meta={scopeLabel}>
              <RankTable
                rowKey={row => row.team.id}
                rows={data.discipline.teams}
                emptyText="Bu kapsamda kart gören takım yok."
                columns={[
                  { key: 'team', label: 'Takım', render: row => <TeamCell team={row.team} /> },
                  { key: 'yellow', label: 'Sarı', align: 'right', render: row => row.yellow },
                  { key: 'red', label: 'Kırmızı', align: 'right', render: row => <span className={row.red > 0 ? 'font-semibold text-status-error' : 'text-text-muted'}>{row.red}</span> },
                  { key: 'fouls', label: 'Faul', align: 'right', render: row => row.fouls },
                  { key: 'foulsPerMatch', label: 'Maç başı faul', align: 'right', hideOnMobile: true, render: row => row.fouls_per_match.toFixed(1) },
                ]}
              />
            </StatsCard>

            <StatsCard title="Hakem karnesi" meta={`${cumulativeLabel} · maç başı kart`} className="md:col-span-2">
              <RankTable
                rowKey={row => row.name}
                rows={data.referees}
                columns={[
                  { key: 'name', label: 'Hakem', render: row => <span className="font-medium text-text-primary truncate block">{row.name}</span> },
                  { key: 'matches', label: 'Maç', align: 'right', render: row => row.matches },
                  { key: 'yellow', label: 'Sarı', align: 'right', hideOnMobile: true, render: row => row.yellow },
                  { key: 'red', label: 'Kırmızı', align: 'right', hideOnMobile: true, render: row => row.red },
                  { key: 'avg', label: 'Maç başı kart', align: 'right', render: row => <span className="font-semibold text-text-primary">{row.cards_per_match.toFixed(1)}</span> },
                ]}
              />
            </StatsCard>
          </Grid>
        </Block>

        {data.surprises.length > 0 && (
          <Block title="Modelin sürprizleri" description="Modelin sonuca en düşük ihtimal verdiği maçlar.">
            <StatsCard title="En büyük sürprizler" meta={scopeLabel}>
              <ul className="divide-y divide-border-light">
                {data.surprises.map(item => (
                  <li key={item.match_id}>
                    <button
                      type="button"
                      onClick={() => openMatch({
                        match_id: item.match_id, gameweek: item.gameweek,
                        home_id: item.home.id, home_name: item.home.name,
                        away_id: item.away.id, away_name: item.away.name,
                        home_score: item.home_score, away_score: item.away_score,
                      })}
                      className="w-full px-4 py-3 flex items-center justify-between gap-3 text-left transition-colors duration-150 ease-out hover:bg-background-tertiary cursor-pointer focus:outline-none focus-visible:bg-background-tertiary"
                    >
                      <span className="flex items-center gap-2 min-w-0 text-sm">
                        <span className="truncate font-medium text-text-primary">{item.home.name}</span>
                        <span className="font-semibold text-text-primary tabular-nums shrink-0">{item.home_score}-{item.away_score}</span>
                        <span className="truncate font-medium text-text-primary">{item.away.name}</span>
                      </span>
                      <span className="text-sm text-text-secondary tabular-nums shrink-0">Model ihtimali %{item.probability.toFixed(0)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </StatsCard>
          </Block>
        )}
      </div>
    </div>
  );
}

export default function StatsTab({ selectedSeason = '2026_27', setSelectedSeason, onSelectMatch }) {
  const [scope, setScope] = useState('week');
  const [gameweek, setGameweek] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [result, setResult] = useState(null);

  const requestKey = `${selectedSeason}|${scope}|${gameweek ?? 'latest'}|${reloadKey}`;

  useEffect(() => {
    let active = true;
    getLeagueStats(selectedSeason, scope, gameweek)
      .then(data => {
        if (active) setResult({ key: requestKey, data, error: false });
      })
      .catch(err => {
        console.error('Failed to load league stats:', err);
        if (active) setResult({ key: requestKey, data: null, error: true });
      });
    return () => {
      active = false;
    };
  }, [selectedSeason, scope, gameweek, requestKey]);

  const settled = result?.key === requestKey;
  const failed = settled && result.error;
  const data = result?.data || null;
  const pending = !settled && Boolean(data);

  const openMatch = (ref) => {
    if (!ref) return;
    onSelectMatch?.({ ...ref, id: ref.match_id, status: 'COMPLETED', is_played: true }, ref.gameweek);
  };

  const changeSeason = (event) => {
    setGameweek(null);
    setSelectedSeason?.(event.target.value);
  };

  const controls = (
    <div className="flex flex-wrap items-end gap-2 shrink-0">
      <SelectField id="stats-season" label="Sezon" value={selectedSeason} onChange={changeSeason}>
        {SEASONS.map(season => (
          <option key={season} value={season}>{formatSeasonLabel(season, '/')}{season === '2026_27' ? ' · Canlı' : ''}</option>
        ))}
      </SelectField>

      <div className="flex flex-col gap-1">
        <span className="text-xs text-text-secondary">Kapsam</span>
        <div className="inline-flex rounded border border-border overflow-hidden" role="group" aria-label="Kapsam">
          <ScopeButton active={scope === 'week'} onClick={() => setScope('week')}>Hafta</ScopeButton>
          <ScopeButton active={scope === 'season'} onClick={() => setScope('season')}>Sezon</ScopeButton>
        </div>
      </div>

      {scope === 'week' && data && (
        <SelectField id="stats-gameweek" label="Hafta" value={data.gameweek ?? ''} onChange={event => setGameweek(Number(event.target.value))}>
          {data.gameweeks.map(week => (
            <option key={week} value={week}>Hafta {week}</option>
          ))}
        </SelectField>
      )}
    </div>
  );

  const header = (
    <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-border">
      <div className="flex flex-col gap-1 min-w-0">
        <h2 className="text-2xl font-semibold text-text-primary">İstatistikler</h2>
        <p className="text-sm text-text-secondary max-w-2xl">
          Haftanın ve sezonun öne çıkanları, en iyi takımlar ve oyuncular. Reytingler modelin hesapladığı değerlerdir.
        </p>
      </div>
      {controls}
    </header>
  );

  if (failed) {
    return (
      <div className="flex flex-col gap-6 pb-12">
        {header}
        <InlineError message="İstatistikler yüklenemedi. Bağlantıyı kontrol edip tekrar deneyin." onRetry={() => setReloadKey(k => k + 1)} />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-6 pb-12">
        {header}
        <StatsSkeleton />
      </div>
    );
  }

  if (data.matches_in_scope === 0) {
    return (
      <div className="flex flex-col gap-6 pb-12">
        {header}
        <EmptyState icon={BarChart3}>{formatSeasonLabel(selectedSeason, '/')} sezonu için henüz oynanmış maç yok.</EmptyState>
      </div>
    );
  }

  return (
    <StatsContent
      data={data}
      selectedSeason={selectedSeason}
      pending={pending}
      header={header}
      openMatch={openMatch}
    />
  );
}
