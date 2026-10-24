const RESULT_META = {
  W: { label: 'G', title: 'Galibiyet', className: 'bg-status-success text-white' },
  D: { label: 'B', title: 'Beraberlik', className: 'bg-text-muted text-white' },
  L: { label: 'M', title: 'Mağlubiyet', className: 'bg-status-error text-white' },
};

export default function TeamForm({
  results = [],
  className = '',
  itemClassName = '',
  getKey = (_, index) => index,
  getTitle,
  label,
}) {
  return (
    <div className={`flex items-center gap-1 ${className}`} aria-label={label}>
      {results.map((item, index) => {
        const result = typeof item === 'string' ? item : item?.result;
        const meta = RESULT_META[result] || RESULT_META.L;
        return (
          <span
            key={getKey(item, index)}
            className={`w-4 h-4 rounded-full flex items-center justify-center text-xs font-semibold ${itemClassName} ${meta.className}`}
            title={getTitle ? getTitle(item, meta) : meta.title}
          >
            {meta.label}
          </span>
        );
      })}
    </div>
  );
}
