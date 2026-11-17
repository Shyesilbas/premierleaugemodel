import React, { forwardRef, useId } from 'react';

export const Input = forwardRef(function Input(
  { label, error, helperText, leftIcon = null, rightIcon = null, id, className = '', disabled = false, ...props },
  ref,
) {
  const generatedId = useId();
  const inputId = id || generatedId;
  const errorId = `${inputId}-error`;
  const helperId = `${inputId}-helper`;

  return (
    <div className="w-full space-y-1.5 text-left">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-text-primary">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {leftIcon && <span className="pointer-events-none absolute left-3 text-text-muted">{leftIcon}</span>}
        <input
          ref={ref}
          id={inputId}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : helperText ? helperId : undefined}
          className={`w-full rounded border bg-background-primary py-2 text-xs sm:text-sm text-text-primary placeholder:text-text-muted outline-none transition-colors duration-150 disabled:bg-background-tertiary disabled:opacity-60 ${
            leftIcon ? 'pl-9' : 'pl-3'
          } ${rightIcon ? 'pr-9' : 'pr-3'} ${
            error
              ? 'border-status-error focus:border-status-error focus:ring-1 focus:ring-status-error'
              : 'border-border hover:border-card-border-hover focus:border-border-focus focus:ring-1 focus:ring-border-focus'
          } ${className}`.trim()}
          {...props}
        />
        {rightIcon && <span className="pointer-events-none absolute right-3 text-text-muted">{rightIcon}</span>}
      </div>
      {error && (
        <p id={errorId} role="alert" className="text-xs text-status-error">
          {error}
        </p>
      )}
      {!error && helperText && (
        <p id={helperId} className="text-xs text-text-muted">
          {helperText}
        </p>
      )}
    </div>
  );
});
