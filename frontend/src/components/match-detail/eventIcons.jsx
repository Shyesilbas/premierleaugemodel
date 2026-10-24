export function BallIcon({ className = "w-4 h-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="m12 2 2.5 4.5-2.5 4.5-2.5-4.5z" />
      <path d="M12 11 8.5 15.5l1.5 5.5h4l1.5-5.5z" />
      <path d="M2.5 10 7 11.5l1.5 4-5 1.5z" />
      <path d="M21.5 10 17 11.5l-1.5 4 5 1.5z" />
      <path d="M4.5 4 8 7l-1 4.5L2.5 10z" />
      <path d="M19.5 4 16 7l1 4.5L21.5 10z" />
    </svg>
  );
}

export function PenaltyBallIcon({ className = "w-4 h-4" }) {
  return (
    <div className="relative inline-flex items-center justify-center">
      <BallIcon className={className} />
      <span className="absolute -bottom-1 -right-1 w-3 h-3 bg-background-tertiary text-text-primary text-xs font-semibold font-mono rounded-full flex items-center justify-center ">
        P
      </span>
    </div>
  );
}

export function MissedPenaltyIcon({ className = "w-4 h-4" }) {
  return (
    <div className="relative inline-flex items-center justify-center text-status-error">
      <BallIcon className={className} />
      <span className="absolute -bottom-1 -right-1 w-3 h-3 bg-background-tertiary text-text-primary text-xs font-semibold font-mono rounded-full flex items-center justify-center">
        X
      </span>
    </div>
  );
}

export function YellowCardIcon({ className = "w-2.5 h-3.5" }) {
  return <span className={`${className} bg-background-tertiary rounded  inline-block`} title="Sarı Kart" />;
}

export function RedCardIcon({ className = "w-2.5 h-3.5" }) {
  return <span className={`${className} bg-background-tertiary rounded  inline-block`} title="Kırmızı Kart" />;
}

