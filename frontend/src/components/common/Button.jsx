import React, { forwardRef } from 'react';

export const Button = forwardRef(function Button(
  {
    variant = 'primary',
    size = 'md',
    isLoading = false,
    leftIcon = null,
    rightIcon = null,
    className = '',
    disabled = false,
    type = 'button',
    children,
    ...props
  },
  ref,
) {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-border-focus focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed select-none cursor-pointer';

  const sizeStyles = {
    sm: 'h-8 px-2.5 text-xs gap-1.5',
    md: 'h-9 px-3.5 text-xs sm:text-sm gap-2',
    lg: 'h-11 px-5 text-sm sm:text-base gap-2.5',
  }[size];

  const variantStyles = {
    primary: 'bg-primary text-white hover:bg-primary-hover active:bg-primary-hover',
    secondary: 'border border-border bg-background-primary text-text-primary hover:bg-background-tertiary active:bg-background-tertiary',
    ghost: 'bg-transparent text-text-secondary hover:bg-background-tertiary hover:text-text-primary active:bg-background-tertiary',
    danger: 'border border-status-error bg-background-primary text-status-error hover:bg-status-error/10 active:bg-status-error/15',
  }[variant];

  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || isLoading}
      className={`${baseStyles} ${sizeStyles} ${variantStyles} ${className}`.trim()}
      {...props}
    >
      {isLoading ? (
        <span
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      ) : (
        leftIcon && <span className="shrink-0">{leftIcon}</span>
      )}
      <span>{children}</span>
      {!isLoading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
    </button>
  );
});
