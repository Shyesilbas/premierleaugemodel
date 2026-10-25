import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { handleImageFallback } from '../../utils/imageFallbacks';
import { getTeam } from '../../data/teams';

const BADGE_FALLBACK = '/badges/premier-league.svg';

const fairOdds = (prob) => {
  const p = Number(prob);
  return p > 0 ? (100 / p).toFixed(2) : '—';
};
const odds = (value) => (value ? Number(value).toFixed(2) : '—');
const signed = (value) => (value > 0 ? `+${value}` : `${value}`);

function StatusDot({ tone }) {
  const tones = {
    success: 'bg-status-success',
    warning: 'bg-status-warning',
    error: 'bg-status-error',
    muted: 'bg-text-muted',
  };
  return <span aria-hidden="true" className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 ${tones[tone]}`} />;
}

function HitStatus({ hit }) {
  if (hit === null || hit === undefined) {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm text-text-secondary whitespace-nowrap">
        <StatusDot tone="muted" />
        Bekleniyor
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-medium whitespace-nowrap ${hit ? 'text-status-success' : 'text-status-error'}`}>
      <StatusDot tone={hit ? 'success' : 'error'} />
      {hit ? 'Tuttu' : 'Yanıldı'}
    </span>
  );
}

function DeviationStatus({ error, tolerance }) {
  if (error === null || error === undefined) return null;
  const close = Math.abs(error) <= tolerance;
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm whitespace-nowrap tabular-nums ${close ? 'text-status-success' : 'text-text-secondary'}`}>
      <StatusDot tone={close ? 'success' : 'muted'} />
      {signed(error)} sapma
    </span>
  );
}

/** Three-way 1X2 cells; `highlight` marks the selected outcome. */
function ThreeWay({ items, highlight }) {
  return (
    <div className="grid grid-cols-3 gap-1 text-center min-w-40">
      {items.map(({ key, label, value, sub }) => {
        const active = highlight === key;
        return (
          <div
            key={key}
            className={`rounded-sm border px-1 py-1 ${active ? 'border-primary bg-background-tertiary' : 'border-border-light'}`}
          >
            <span className="block text-xs text-text-tertiary">{label}</span>
            <span className={`block text-sm tabular-nums ${active ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>{value}</span>
            {sub && <span className="block text-xs text-text-tertiary tabular-nums">{sub}</span>}
          </div>
        );
      })}
    </div>
  );
}

function ValueLine({ primary, secondary, meta }) {
  return (
    <div className="flex flex-col">
      <span className="text-sm text-text-primary tabular-nums whitespace-nowrap">
        <span className="font-medium">{primary}</span>
        {secondary && <span className="ml-1 text-text-tertiary">{secondary}</span>}
      </span>
      {meta && <span className="text-xs text-text-tertiary tabular-nums whitespace-nowrap">{meta}</span>}
    </div>
  );
}

function TeamName({ team, name, isWinner, align = 'left' }) {
  const img = (
    <img
      src={team.badge}
      alt=""
      className="w-6 h-6 object-contain shrink-0"
      onError={event => handleImageFallback(event, BADGE_FALLBACK)}
    />
  );
  return (
    <div className={`flex items-center gap-2 min-w-0 ${align === 'right' ? 'justify-end text-right' : ''}`}>
      {align === 'left' && img}
      <span className={`text-sm truncate ${isWinner ? 'font-semibold text-text-primary' : 'text-text-secondary'}`}>
        {name}
      </span>
      {align === 'right' && img}
    </div>
  );
}

export default function AuditMatchCard({ match: m, onSelectMatch }) {
  const [open, setOpen] = useState(false);
  const homeT = getTeam(m.home_id, m.home_name);
  const awayT = getTeam(m.away_id, m.away_name);
  const modelOverPick = m.prob_over_25 >= 50.0 ? '2.5 üst' : '2.5 alt';
  const modelOverProb = m.prob_over_25 >= 50.0 ? m.prob_over_25 : (100 - m.prob_over_25).toFixed(1);
  const played = m.is_played !== false;
  const actualTotalGoals = m.home_score + m.away_score;
  const actualOverResult = actualTotalGoals > 2.5 ? 'üst' : 'alt';
  const bttsThreshold = m.btts_threshold || 56.6;
  const modelBttsPick = m.prob_btts >= bttsThreshold ? 'KG var' : 'KG yok';
  const modelBttsProb = m.prob_btts >= bttsThreshold ? m.prob_btts : (100 - m.prob_btts).toFixed(1);
  const actualBttsResult = m.home_score > 0 && m.away_score > 0 ? 'KG var' : 'KG yok';
  const actualWinnerLabel = m.actual_result === 'home' ? m.home_name : m.actual_result === 'away' ? m.away_name : 'Beraberlik';
  const edgeSideLabel = m.highest_edge_side === 'home' ? m.home_name : m.highest_edge_side === 'away' ? m.away_name : 'Beraberlik';

  const openMatch = () => {
    onSelectMatch?.({
      ...m,
      id: m.match_id,
      match_id: m.match_id,
      home_id: m.home_id,
      away_id: m.away_id,
      status: played ? 'COMPLETED' : 'UPCOMING',
      is_played: played,
    }, m.gameweek);
  };

  const rows = [
    {
      key: '1x2',
      title: 'Maç sonucu',
      sub: `Öngörü: ${m.favorite_label}`,
      model: (
        <ThreeWay
          highlight={m.predicted_winner}
          items={[
            { key: 'home', label: '1', value: `%${m.prob_home}`, sub: fairOdds(m.prob_home) },
            { key: 'draw', label: 'X', value: `%${m.prob_draw}`, sub: fairOdds(m.prob_draw) },
            { key: 'away', label: '2', value: `%${m.prob_away}`, sub: fairOdds(m.prob_away) },
          ]}
        />
      ),
      market: (
        <ThreeWay
          highlight={played ? m.actual_result : null}
          items={[
            { key: 'home', label: '1', value: odds(m.market_home_odds) },
            { key: 'draw', label: 'X', value: odds(m.market_draw_odds) },
            { key: 'away', label: '2', value: odds(m.market_away_odds) },
          ]}
        />
      ),
      actual: played ? <ValueLine primary={actualWinnerLabel} secondary={m.score} /> : <ValueLine primary="—" />,
      status: <HitStatus hit={m.hit_1x2} />,
    },
    {
      key: 'ou25',
      title: '2.5 alt / üst',
      sub: `Beklenen gol: ${m.expected_goals}`,
      model: <ValueLine primary={modelOverPick} secondary={`%${modelOverProb}`} meta={`Adil oran ${fairOdds(modelOverProb)}`} />,
      market: <ValueLine primary={odds(m.market_over_25_odds)} meta="Üst kapanış" />,
      actual: played ? <ValueLine primary={`${actualTotalGoals} gol`} secondary={actualOverResult} /> : <ValueLine primary="—" />,
      status: <HitStatus hit={m.hit_over_25} />,
    },
    {
      key: 'btts',
      title: 'Karşılıklı gol',
      sub: 'İki takım da atar mı',
      model: <ValueLine primary={modelBttsPick} secondary={`%${modelBttsProb}`} meta={`Adil oran ${fairOdds(modelBttsProb)}`} />,
      market: <ValueLine primary={odds(m.market_btts_odds)} meta="KG var kapanış" />,
      actual: played ? <ValueLine primary={actualBttsResult} /> : <ValueLine primary="—" />,
      status: <HitStatus hit={m.hit_btts} />,
    },
    {
      key: 'corners',
      title: 'Toplam korner',
      sub: 'Model beklentisi',
      model: <ValueLine primary={`${m.expected_corners} korner`} />,
      market: <ValueLine primary="9.5" meta="Standart çizgi" />,
      actual: <ValueLine primary={`${m.actual_corners ?? '—'} korner`} />,
      status: <DeviationStatus error={m.corner_error} tolerance={2} />,
    },
    {
      key: 'cards',
      title: 'Toplam kart',
      sub: 'Disiplin',
      model: <ValueLine primary={`${m.expected_cards} kart`} />,
      market: <ValueLine primary="3.5 / 4.5" meta="Standart çizgi" />,
      actual: <ValueLine primary={`${m.actual_cards ?? '—'} kart`} />,
      status: <DeviationStatus error={m.card_error} tolerance={1} />,
    },
  ];

  const tags = [
    m.confidence_tier === 'high' && 'Net favori',
    m.is_balanced && 'Dengeli maç',
  ].filter(Boolean);

  return (
    <article className="bg-background-primary border border-border rounded transition-colors duration-150 ease-out hover:border-card-border-hover">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        className="w-full text-left px-3 py-3 sm:px-4 flex flex-col gap-2 cursor-pointer rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
      >
        <div className="grid grid-cols-versus items-center gap-3">
          <TeamName team={homeT} name={m.home_name} isWinner={played && m.home_score > m.away_score} />
          <span className="min-w-12 text-center text-lg font-semibold text-text-primary tabular-nums">{played ? m.score : 'vs'}</span>
          <TeamName team={awayT} name={m.away_name} isWinner={played && m.away_score > m.home_score} align="right" />
        </div>

        <div className="flex items-center justify-between gap-3 text-xs text-text-secondary">
          <p className="min-w-0 truncate tabular-nums">
            Hafta {m.gameweek} · {m.match_date}
            {m.favorite_label && <> · Öngörü: <span className="text-text-primary">{m.favorite_label}</span></>}
            {tags.length > 0 && <> · {tags.join(' · ')}</>}
            {m.highest_edge_side && <> · +{m.edge_pct}% avantaj ({edgeSideLabel})</>}
          </p>
          <span className="flex items-center gap-2 shrink-0">
            <HitStatus hit={m.hit_1x2} />
            <ChevronDown className={`w-4 h-4 text-text-tertiary transition-transform duration-150 ease-out motion-reduce:transition-none ${open ? 'rotate-180' : ''}`} strokeWidth={1.5} aria-hidden="true" />
          </span>
        </div>
      </button>

      {open && (
        <div className="border-t border-border-light px-3 py-3 sm:px-4 flex flex-col gap-3">
          <div className="overflow-x-auto border border-border rounded">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="bg-background-tertiary border-b border-border text-text-secondary">
                  <th scope="col" className="py-2 px-3 font-medium">Pazar</th>
                  <th scope="col" className="py-2 px-3 font-medium border-l border-border">Model</th>
                  <th scope="col" className="py-2 px-3 font-medium border-l border-border">Piyasa ({m.bookmaker || 'Bet365'})</th>
                  <th scope="col" className="py-2 px-3 font-medium border-l border-border">{played ? 'Gerçekleşen' : 'Sonuç'}</th>
                  <th scope="col" className="py-2 px-3 font-medium text-right border-l border-border">Durum</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-light">
                {rows.map(row => (
                  <tr key={row.key}>
                    <th scope="row" className="py-2 px-3 align-middle font-normal">
                      <span className="block font-medium text-text-primary whitespace-nowrap">{row.title}</span>
                      <span className="block text-xs text-text-tertiary whitespace-nowrap tabular-nums">{row.sub}</span>
                    </th>
                    <td className="py-2 px-3 align-middle border-l border-border-light">{row.model}</td>
                    <td className="py-2 px-3 align-middle border-l border-border-light">{row.market}</td>
                    <td className="py-2 px-3 align-middle border-l border-border-light">{row.actual}</td>
                    <td className="py-2 px-3 align-middle text-right border-l border-border-light">{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {onSelectMatch && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={openMatch}
                className="h-9 px-2 -mr-2 rounded inline-flex items-center gap-1 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
              >
                Maç detaylarını aç
                <ChevronRight className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
              </button>
            </div>
          )}
        </div>
      )}
    </article>
  );
}
