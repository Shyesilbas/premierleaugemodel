import React, { useState, useEffect } from 'react';
import { User } from 'lucide-react';

export default function PlayerAvatar({
  player,
  photoUrl,
  name,
  shirt,
  size = 'md',
  shape = 'circle',
  fallback = 'initials',
  className = '',
  imgClassName = '',
}) {
  const [imgError, setImgError] = useState(false);

  const resolvedPhoto = photoUrl !== undefined ? photoUrl : player?.photo_url;
  const resolvedName = name !== undefined ? name : player?.name;
  const resolvedShirt = shirt !== undefined ? shirt : player?.shirt;

  useEffect(() => {
    setImgError(false);
  }, [resolvedPhoto]);

  // Size mapping
  const sizeMap = {
    xs: 'w-6 h-6 text-xs',
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-xs',
    lg: 'w-14 h-14 text-sm',
    xl: 'w-16 h-16 text-base',
    '2xl': 'w-20 h-20 text-lg',
  };

  const shapeClass = shape === 'circle' ? 'rounded-full' : 'rounded';
  const sizeClass = sizeMap[size] || size;

  const hasPhoto = Boolean(resolvedPhoto && !imgError);

  // Compute initials as fallback
  const getInitials = (n) => {
    if (!n) return '';
    const parts = n.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const initials = getInitials(resolvedName);

  return (
    <div
      className={`relative flex items-center justify-center shrink-0 overflow-hidden bg-background-tertiary border border-border select-none ${shapeClass} ${sizeClass} ${className}`}
    >
      {hasPhoto ? (
        <img
          src={resolvedPhoto}
          alt={resolvedName || ''}
          className={`w-full h-full object-cover ${imgClassName}`}
          onError={() => setImgError(true)}
          loading="lazy"
        />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center bg-background-tertiary text-text-secondary font-mono font-medium">
          {fallback === 'shirt' && resolvedShirt ? (
            <span className="leading-none">#{resolvedShirt}</span>
          ) : initials ? (
            <span className="leading-none font-sans font-semibold text-text-primary tracking-tight">{initials}</span>
          ) : resolvedShirt ? (
            <span className="leading-none">#{resolvedShirt}</span>
          ) : (
            <User className="w-1/2 h-1/2 text-text-muted" />
          )}
        </div>
      )}
    </div>
  );
}

