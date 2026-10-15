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
    xs: 'w-6 h-6 text-[10px]',
    sm: 'w-8 h-8 text-xs',
    md: 'w-10 h-10 text-xs',
    lg: 'w-14 h-14 text-sm',
    xl: 'w-16 h-16 text-base',
    '2xl': 'w-20 h-20 text-lg',
  };

  const shapeClass = shape === 'circle' ? 'rounded-full' : 'rounded-xl';
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
      className={`relative flex items-center justify-center shrink-0 overflow-hidden bg-slate-100 border border-slate-200/90 shadow-2xs select-none ${shapeClass} ${sizeClass} ${className}`}
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
        <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200 text-slate-700 font-mono font-black">
          {fallback === 'shirt' && resolvedShirt ? (
            <span className="leading-none">#{resolvedShirt}</span>
          ) : initials ? (
            <span className="leading-none font-sans font-bold text-slate-700 tracking-tight">{initials}</span>
          ) : resolvedShirt ? (
            <span className="leading-none">#{resolvedShirt}</span>
          ) : (
            <User className="w-1/2 h-1/2 text-slate-400" />
          )}
        </div>
      )}
    </div>
  );
}

