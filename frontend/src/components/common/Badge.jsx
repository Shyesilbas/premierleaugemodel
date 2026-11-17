import React from 'react';

export function Badge({ variant = 'neutral', size = 'md', dot = false, className = '', children, ...props }) {
  const sizeStyles = {
    sm: 'px-1.5 py-0.5 text-xs leading-tight',
    md: 'px-2 py-0.5 text-xs font-medium',
  }[size];

  const variantStyles = {
    neutral: 'border border-border bg-background-tertiary text-text-secondary',
    success: 'border border-status-success/30 bg-status-success/10 text-status-success',
    error: 'border border-status-error/30 bg-status-error/10 text-status-error',
    warning: 'border border-status-warning/30 bg-status-warning/10 text-status-warning',
    info: 'border border-status-info/30 bg-status-info/10 text-status-info',
    primary: 'border border-accent/30 bg-accent-soft text-accent font-semibold',
  }[variant];

  const dotColors = {
    neutral: 'bg-text-muted',
    success: 'bg-status-success',
    error: 'bg-status-error',
    warning: 'bg-status-warning',
    info: 'bg-status-info',
    primary: 'bg-accent',
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm ${sizeStyles} ${variantStyles} ${className}`.trim()}
      {...props}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dotColors}`} aria-hidden="true" />}
      <span>{children}</span>
    </span>
  );
}
