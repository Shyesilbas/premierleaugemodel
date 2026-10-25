export default function Skeleton({ className = '' }) {
  return <div aria-hidden="true" className={`animate-pulse motion-reduce:animate-none bg-background-tertiary rounded ${className}`} />;
}
