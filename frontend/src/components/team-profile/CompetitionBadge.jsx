import { useState } from 'react';
import { COMPETITIONS } from './teamProfileUtils';

// The competition's logo; the short code (PL / ŞL / AL) only appears if the image cannot be loaded.
export default function CompetitionBadge({ competition, size = 'md' }) {
  const [failed, setFailed] = useState(false);
  const known = COMPETITIONS[competition?.key] || competition;
  const logo = known?.logo;

  if (!logo || failed) {
    return (
      <span
        title={known?.name}
        className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-xs font-medium tabular-nums ${known?.className || 'border-border text-text-secondary'}`}
      >
        {known?.abbr}
      </span>
    );
  }
  return (
    <img
      src={logo}
      alt={known.name}
      title={known.name}
      onError={() => setFailed(true)}
      className={`${size === 'sm' ? 'h-4' : 'h-5'} w-auto object-contain shrink-0`}
    />
  );
}
