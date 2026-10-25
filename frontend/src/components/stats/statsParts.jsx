import { useState } from 'react';
import { handleTeamBadgeError } from '../../utils/imageFallbacks';

/** Flat bordered card with a title row; every ranking on the Statistics page sits in one. */
export function StatsCard({ title, meta, children, className = '' }) {
  return (
    <section className={`bg-background-primary border border-border rounded flex flex-col min-w-0 ${className}`}>
      <div className="flex items-baseline justify-between gap-3 px-4 py-3 border-b border-border-light">
        <h4 className="text-sm font-semibold text-text-primary">{title}</h4>
        {meta && <span className="text-xs text-text-secondary tabular-nums text-right">{meta}</span>}
      </div>
      {children}
    </section>
  );
}

export function BlockHeader({ title, description }) {
  return (
    <div className="flex flex-col gap-1 pb-3 border-b border-border">
      <h3 className="text-lg font-semibold text-text-primary">{title}</h3>
      {description && <p className="text-sm text-text-secondary">{description}</p>}
    </div>
  );
}

export function TeamCell({ team }) {
  return (
    <span className="flex items-center gap-2 min-w-0">
      <img src={team.badge} alt="" className="w-5 h-5 object-contain shrink-0" onError={handleTeamBadgeError} />
      <span className="truncate font-medium text-text-primary">{team.name}</span>
    </span>
  );
}

export function PlayerCell({ player }) {
  return (
    <span className="flex flex-col min-w-0">
      <span className="truncate font-medium text-text-primary">{player.name}</span>
      {player.team_name && <span className="truncate text-xs text-text-tertiary">{player.team_name}</span>}
    </span>
  );
}

/**
 * Dense ranking table. `columns` is [{ key, label, render(row), align, hideOnMobile }];
 * the first `limit` rows show and a toggle reveals the rest.
 */
export function RankTable({ columns, rows, rowKey, limit = 5, emptyText = 'Bu kapsamda kayıt yok.' }) {
  const [expanded, setExpanded] = useState(false);

  if (!rows || rows.length === 0) {
    return <p className="px-4 py-8 text-center text-sm text-text-secondary">{emptyText}</p>;
  }

  const visible = expanded ? rows : rows.slice(0, limit);
  const alignClass = (align) => (align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left');

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-xs text-text-secondary border-b border-border-light">
              <th scope="col" className="w-8 py-2 pl-4 pr-1 font-medium text-left">#</th>
              {columns.map(col => (
                <th
                  key={col.key}
                  scope="col"
                  className={`py-2 px-2 font-medium whitespace-nowrap ${alignClass(col.align)} ${col.hideOnMobile ? 'hidden sm:table-cell' : ''}`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-light">
            {visible.map((row, index) => (
              <tr key={rowKey(row)} className="transition-colors duration-150 ease-out hover:bg-background-tertiary">
                <td className="py-2 pl-4 pr-1 text-text-tertiary tabular-nums">{index + 1}</td>
                {columns.map(col => (
                  <td
                    key={col.key}
                    className={`py-2 px-2 tabular-nums ${alignClass(col.align)} ${col.hideOnMobile ? 'hidden sm:table-cell' : ''} ${col.align === 'right' || col.align === 'center' ? 'whitespace-nowrap' : 'max-w-0 w-full'}`}
                  >
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > limit && (
        <button
          type="button"
          onClick={() => setExpanded(value => !value)}
          aria-expanded={expanded}
          className="h-9 border-t border-border-light text-sm font-medium text-text-secondary transition-colors duration-150 ease-out hover:text-text-primary hover:bg-background-tertiary cursor-pointer rounded-b focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-border-focus"
        >
          {expanded ? 'Daha az göster' : `Tümünü göster (${rows.length})`}
        </button>
      )}
    </>
  );
}
