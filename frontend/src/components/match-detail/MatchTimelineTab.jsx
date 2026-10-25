import { ArrowRightLeft, Clock, Timer } from 'lucide-react';
import PlayerAvatar from '../PlayerAvatar';
import EmptyState from '../common/EmptyState';
import { BallIcon, MissedPenaltyIcon, PenaltyBallIcon, RedCardIcon, YellowCardIcon } from './eventIcons';

function EventIcon({ item }) {
  const isGoal = item.type === 'goal';
  if (isGoal && item.is_penalty) return <PenaltyBallIcon className="w-4 h-4 text-status-success" />;
  if (isGoal && item.is_own_goal) return <BallIcon className="w-4 h-4 text-status-error" />;
  if (isGoal) return <BallIcon className="w-4 h-4 text-text-primary" />;
  if (item.type === 'penalty_missed') return <MissedPenaltyIcon className="w-4 h-4 text-status-error" />;
  if (item.type === 'yellow_card') return <YellowCardIcon className="w-3 h-4" />;
  if (item.type === 'red_card') return <RedCardIcon className="w-3 h-4" />;
  if (item.type === 'substitution') return <ArrowRightLeft className="w-4 h-4 text-text-secondary" strokeWidth={1.5} />;
  return <Clock className="w-4 h-4 text-text-secondary" strokeWidth={1.5} />;
}

function Tag({ tone, children }) {
  const color = tone === 'success' ? 'text-status-success border-status-success' : 'text-status-error border-status-error';
  return <span className={`text-xs font-medium border rounded-sm px-1.5 shrink-0 ${color}`}>{children}</span>;
}

function EventBody({ item, isHome }) {
  const align = isHome ? 'flex-row-reverse text-right' : 'flex-row text-left';
  const justify = isHome ? 'justify-end' : 'justify-start';

  if (item.type === 'goal') {
    return (
      <div className={`flex items-center gap-3 ${align}`}>
        <PlayerAvatar photoUrl={item.photo_url} name={item.player_name} size="w-8 h-8 text-xs" className="shrink-0" />
        <div className="min-w-0 flex-1">
          <div className={`flex items-center gap-2 text-sm font-semibold text-text-primary ${justify}`}>
            <span className="truncate">{item.player_name}</span>
            {item.is_penalty && <Tag tone="success">Penaltı</Tag>}
            {item.is_own_goal && <Tag tone="error">Kendi kalesine</Tag>}
          </div>
          {item.assist_name && (
            <p className="text-xs text-text-secondary truncate">Asist: {item.assist_name}</p>
          )}
        </div>
        {item.score && (
          <span className="text-sm font-semibold tabular-nums text-text-primary shrink-0">{item.score}</span>
        )}
      </div>
    );
  }

  if (item.type === 'penalty_missed') {
    return (
      <div className={isHome ? 'text-right' : 'text-left'}>
        <p className="text-sm font-semibold text-status-error">
          Kaçan penaltı{item.player_name ? <span className="text-text-primary"> · {item.player_name}</span> : null}
        </p>
        {item.description && <p className="text-xs text-text-secondary truncate">{item.description}</p>}
      </div>
    );
  }

  if (item.type === 'yellow_card' || item.type === 'red_card') {
    return (
      <div className={`flex items-center gap-3 ${align}`}>
        <PlayerAvatar photoUrl={item.photo_url} name={item.player_name} size="w-8 h-8 text-xs" className="shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-text-primary truncate">{item.player_name}</p>
          <p className="text-xs text-text-secondary">{item.type === 'yellow_card' ? 'Sarı kart' : 'Kırmızı kart'}</p>
        </div>
      </div>
    );
  }

  if (item.type === 'substitution') {
    return (
      <div className={`space-y-0.5 text-sm ${isHome ? 'text-right' : 'text-left'}`}>
        <p className={`flex items-center gap-1.5 ${justify}`}>
          <span className="text-xs text-status-success" aria-label="Giren">&#9650;</span>
          <span className="font-semibold text-text-primary truncate">{item.player_in_name}</span>
        </p>
        <p className={`flex items-center gap-1.5 text-xs text-text-secondary ${justify}`}>
          <span className="text-status-error" aria-label="Çıkan">&#9660;</span>
          <span className="truncate">{item.player_out_name}</span>
        </p>
      </div>
    );
  }

  return null;
}

export default function MatchTimelineTab({ timeline, homeTeam, awayTeam, homeTeamId }) {
  if (timeline.length === 0) {
    return <EmptyState icon={Clock}>Bu karşılaşma için zaman akışı kaydı bulunamadı.</EmptyState>;
  }

  return (
    <div className="bg-background-primary border border-border rounded">
      <div className="flex items-center border-b border-border text-sm font-semibold text-text-primary">
        <div className="flex flex-1 min-w-0 items-center justify-end gap-2 px-4 py-3">
          <span className="truncate">{homeTeam.name}</span>
          <img src={homeTeam.badge} alt="" className="w-5 h-5 object-contain shrink-0" />
        </div>
        <div className="w-16 shrink-0" />
        <div className="flex flex-1 min-w-0 items-center justify-start gap-2 px-4 py-3">
          <img src={awayTeam.badge} alt="" className="w-5 h-5 object-contain shrink-0" />
          <span className="truncate">{awayTeam.name}</span>
        </div>
      </div>

      <ol>
        {timeline.map((item, idx) => {
          if (item.type === 'period_start' || item.type === 'period_end' || item.type === 'added_time') {
            const isAddedTime = item.type === 'added_time';
            const Icon = isAddedTime ? Timer : Clock;
            return (
              <li key={idx} className="flex items-center justify-center gap-2 px-4 py-2 bg-background-tertiary border-t border-border-light text-xs text-text-secondary">
                <Icon className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />
                <span className="font-semibold text-text-primary">
                  {item.label}{isAddedTime && item.description ? ` (${item.description})` : ''}
                </span>
                {item.score && <span className="font-semibold tabular-nums text-text-primary">{item.score}</span>}
                {item.minute && <span className="tabular-nums">{item.minute}</span>}
              </li>
            );
          }

          const isHome = Boolean(
            (item.team_id && Number(item.team_id) === Number(homeTeamId)) ||
            (item.team_name && homeTeam.name && item.team_name.toLowerCase().includes(homeTeam.name.toLowerCase()))
          );

          return (
            <li key={idx} className="flex items-center border-t border-border-light first:border-t-0">
              <div className="flex-1 min-w-0 px-4 py-3">{isHome && <EventBody item={item} isHome />}</div>
              <div className="w-16 shrink-0 flex flex-col items-center gap-0.5 py-2">
                <EventIcon item={item} />
                <span className="text-xs font-semibold tabular-nums text-text-secondary">{item.minute}</span>
              </div>
              <div className="flex-1 min-w-0 px-4 py-3">{!isHome && <EventBody item={item} isHome={false} />}</div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
