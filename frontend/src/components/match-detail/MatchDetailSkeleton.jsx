import Skeleton from '../common/Skeleton';

export default function MatchDetailSkeleton() {
  return (
    <div className="space-y-3" role="status" aria-label="Maç detayları yükleniyor">
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
    </div>
  );
}
