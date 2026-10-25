import { AlertCircle } from 'lucide-react';

export default function InlineError({ message, onRetry }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded border border-status-error bg-background-primary p-4">
      <div className="flex items-center gap-2 text-sm text-status-error">
        <AlertCircle className="w-4 h-4 shrink-0" strokeWidth={1.5} aria-hidden="true" />
        <span>{message}</span>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="h-9 px-3 rounded border border-border bg-background-primary text-sm font-medium text-text-primary hover:bg-background-tertiary transition-colors cursor-pointer focus-visible:outline-none focus-visible:border-border-focus"
        >
          Tekrar dene
        </button>
      )}
    </div>
  );
}
