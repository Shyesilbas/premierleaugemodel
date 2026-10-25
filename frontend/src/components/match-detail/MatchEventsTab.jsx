import { Activity } from 'lucide-react';
import EmptyState from '../common/EmptyState';

export default function MatchEventsTab({ events }) {
  if (events.length === 0) {
    return <EmptyState icon={Activity}>Bu karşılaşma için Opta olay akışı kaydı bulunamadı.</EmptyState>;
  }

  return (
    <ul className="bg-background-primary border border-border rounded divide-y divide-border-light">
      {events.map((ev, idx) => (
        <li key={ev.id || idx} className="flex items-start gap-3 px-4 py-3">
          <span className="w-10 shrink-0 text-xs font-semibold tabular-nums text-text-primary pt-0.5">
            {ev.time?.label || ev.minute || '-'}'
          </span>
          <div className="min-w-0 flex-1">
            <span className="block text-xs text-text-secondary">{ev.type || ev.event_type || 'olay'}</span>
            <p className="text-sm text-text-primary">{ev.text}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
