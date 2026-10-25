export default function EmptyState({ icon: Icon, children, action }) {
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center">
      {Icon && <Icon className="w-8 h-8 text-text-muted" strokeWidth={1.5} aria-hidden="true" />}
      <p className="max-w-sm text-sm text-text-secondary">{children}</p>
      {action}
    </div>
  );
}
