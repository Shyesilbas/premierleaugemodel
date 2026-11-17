export default function KpiCard({ label, value, meta, icon: Icon }) {
  return (
    <div className="bg-background-primary border border-border rounded p-3 sm:p-4 flex flex-col gap-1 min-w-0">
      <span className="text-xs text-text-secondary truncate">{label}</span>
      <span className="flex items-baseline gap-1 text-xl font-semibold text-text-primary tabular-nums">
        {value}
        {Icon && <Icon className="w-4 h-4 shrink-0 self-center text-text-secondary" strokeWidth={1.5} aria-hidden="true" />}
      </span>
      <span className="text-xs text-text-tertiary truncate tabular-nums">{meta}</span>
    </div>
  );
}
