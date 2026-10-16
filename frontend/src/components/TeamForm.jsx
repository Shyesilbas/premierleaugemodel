const RESULT_META = {
  W: { label: 'G', title: 'Galibiyet', className: 'bg-emerald-500 text-white' },
  D: { label: 'B', title: 'Beraberlik', className: 'bg-slate-400 text-white' },
  L: { label: 'M', title: 'Mağlubiyet', className: 'bg-rose-500 text-white' },
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
            className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black ${itemClassName} ${meta.className}`}
            title={getTitle ? getTitle(item, meta) : meta.title}
          >
            {meta.label}
          </span>
        );
      })}
    </div>
  );
}
