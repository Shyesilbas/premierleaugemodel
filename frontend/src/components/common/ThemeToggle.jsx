import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/themeState';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const label = theme === 'dark' ? 'Tema değiştir (Açık tema)' : 'Tema değiştir (Koyu tema)';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded border border-border bg-background-primary text-text-secondary transition-colors duration-150 hover:bg-background-tertiary hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
    >
      {theme === 'dark' ? (
        <Sun className="w-4 h-4 text-status-warning" strokeWidth={1.5} aria-hidden="true" />
      ) : (
        <Moon className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />
      )}
    </button>
  );
}
