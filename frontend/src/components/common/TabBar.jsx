import { useRef } from 'react';

export default function TabBar({ tabs, active, onChange, label, idPrefix = 'tab' }) {
  const refs = useRef({});

  const onKeyDown = (e, index) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const next = tabs[(index + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  };

  return (
    <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto border-b border-border">
      {tabs.map((tab, index) => {
        const selected = tab.id === active;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            ref={el => { refs.current[tab.id] = el; }}
            type="button"
            role="tab"
            id={`${idPrefix}-${tab.id}`}
            aria-selected={selected}
            aria-controls={`${idPrefix}-panel`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={e => onKeyDown(e, index)}
            className={`flex items-center gap-2 px-3 min-h-11 sm:min-h-10 text-sm font-medium border-b-2 whitespace-nowrap transition-colors cursor-pointer focus-visible:outline-none focus-visible:bg-background-tertiary ${
              selected
                ? 'border-primary text-text-primary'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            {Icon && <Icon className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />}
            <span>{tab.label}</span>
            {tab.count > 0 && <span className="text-xs tabular-nums text-text-secondary">{tab.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
