import React, { forwardRef } from 'react';

export const Card = forwardRef(function Card(
  { hoverable = false, padding = 'md', className = '', children, ...props },
  ref,
) {
  const paddingStyles = {
    none: '',
    sm: 'p-3',
    md: 'p-4 sm:p-5',
    lg: 'p-6',
  }[padding];

  const hoverStyles = hoverable
    ? 'hover:border-card-border-hover transition-colors duration-150 cursor-pointer'
    : '';

  return (
    <div
      ref={ref}
      className={`rounded border border-border bg-background-primary ${paddingStyles} ${hoverStyles} ${className}`.trim()}
      {...props}
    >
      {children}
    </div>
  );
});
