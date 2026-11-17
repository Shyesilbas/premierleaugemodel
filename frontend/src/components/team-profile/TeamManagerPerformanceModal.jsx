import { Activity, X } from 'lucide-react';
import KpiCard from '../common/KpiCard';
import ModalDialog from '../common/ModalDialog';
import Skeleton from '../common/Skeleton';
import EmptyState from '../common/EmptyState';
import { getTeam } from '../../data/teams';

export default function TeamManagerPerformanceModal({
  selectedManager,
  managerPerformanceLoading,
  managerPerformance,
  teamName,
  onClose,
}) {
  if (!selectedManager) return null;

  const managerName =
    selectedManager.name?.display ||
    [selectedManager.name?.first, selectedManager.name?.last].filter(Boolean).join(' ');

  const opponents = [...(managerPerformance?.opponents || [])].sort(
    (a, b) => b.matches - a.matches || a.opponent.localeCompare(b.opponent, 'tr'),
  );

  return (
    <ModalDialog
      open={Boolean(selectedManager)}
      onClose={onClose}
      ariaLabelledBy="manager-modal-title"
      maxWidthClass="max-w-4xl"
    >
      <header className="border-b border-border bg-background-primary px-5 sm:px-6 py-5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <Activity className="h-3.5 w-3.5 text-text-tertiary" strokeWidth={1.5} aria-hidden="true" />
            <span>Teknik direktör profili · {teamName || 'Takım'} · Tüm kayıtlı sezonlar</span>
          </div>
          <h2 id="manager-modal-title" className="mt-1.5 truncate text-xl sm:text-2xl font-semibold tracking-tight text-text-primary">
            {managerName}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          title="Kapat"
          aria-label="Kapat"
          className="rounded border border-border bg-background-primary hover:bg-background-tertiary p-2 text-text-secondary hover:text-text-primary transition-colors cursor-pointer shrink-0"
        >
          <X className="h-4 w-4" strokeWidth={1.5} aria-hidden="true" />
        </button>
      </header>

      <div className="p-5 sm:p-6 space-y-6">
        {managerPerformanceLoading ? (
          <div className="space-y-4" aria-busy="true" aria-label="Teknik direktör verileri yükleniyor">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
            <Skeleton className="h-56 w-full" />
          </div>
        ) : !managerPerformance?.total?.matches ? (
          <EmptyState icon={Activity}>
            Bu teknik direktör için kayıtlı sezonlarda tamamlanmış lig maçı bulunamadı.
          </EmptyState>
        ) : (
          <>
            <section aria-label="Toplam teknik direktör istatistikleri" className="space-y-3">
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold text-text-primary">Kariyer özeti</h3>
                <span className="text-xs text-text-secondary tabular-nums">
                  {managerPerformance.total.matches} maç · Tüm kayıtlı lig maçları
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <KpiCard label="Maç" value={managerPerformance.total.matches} meta="Toplam" />
                <KpiCard label="Galibiyet" value={managerPerformance.total.wins} meta="Kazanılan" />
                <KpiCard label="Beraberlik" value={managerPerformance.total.draws} meta="Berabere" />
                <KpiCard label="Mağlubiyet" value={managerPerformance.total.losses} meta="Kaybedilen" />
                <KpiCard label="Attığı gol" value={managerPerformance.total.gf} meta="Lehine" />
                <KpiCard label="Yediği gol" value={managerPerformance.total.ga} meta="Aleyhine" />
              </div>
            </section>

            <section aria-label="Rakiplere göre istatistikler" className="space-y-3">
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold text-text-primary">Rakiplere karşı</h3>
                <span className="text-xs text-text-secondary tabular-nums">
                  {opponents.length} takım
                </span>
              </div>
              <div
                tabIndex={0}
                role="region"
                aria-label="Teknik direktörün rakiplere karşı istatistik tablosu"
                className="overflow-auto rounded border border-border max-h-80"
              >
                <table className="w-full text-left text-sm border-collapse">
                  <thead className="sticky top-0 z-10">
                    <tr className="bg-background-tertiary border-b border-border text-text-secondary">
                      <th scope="col" className="py-2.5 px-3 font-medium">Rakip takım</th>
                      <th scope="col" className="py-2.5 px-3 font-medium text-right border-l border-border">Maç</th>
                      <th scope="col" className="py-2.5 px-3 font-medium text-right border-l border-border">G</th>
                      <th scope="col" className="py-2.5 px-3 font-medium text-right border-l border-border">B</th>
                      <th scope="col" className="py-2.5 px-3 font-medium text-right border-l border-border">M</th>
                      <th scope="col" className="py-2.5 px-3 font-medium text-right border-l border-border">AG</th>
                      <th scope="col" className="py-2.5 px-3 font-medium text-right border-l border-border">YG</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-light bg-background-primary">
                    {opponents.map((item) => {
                      const opponentTeam = getTeam(item.opponent_id, item.opponent);
                      return (
                        <tr key={item.opponent_id} className="hover:bg-background-tertiary transition-colors">
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-2.5 min-w-0">
                              <img
                                src={opponentTeam.badge}
                                alt=""
                                className="h-5 w-5 object-contain shrink-0"
                                loading="lazy"
                              />
                              <span className="font-medium text-text-primary truncate">{item.opponent}</span>
                            </div>
                          </td>
                          <td className="py-2.5 px-3 text-right font-medium text-text-primary tabular-nums border-l border-border-light">{item.matches}</td>
                          <td className="py-2.5 px-3 text-right font-medium text-status-success tabular-nums border-l border-border-light">{item.wins}</td>
                          <td className="py-2.5 px-3 text-right text-text-secondary tabular-nums border-l border-border-light">{item.draws}</td>
                          <td className="py-2.5 px-3 text-right font-medium text-status-error tabular-nums border-l border-border-light">{item.losses}</td>
                          <td className="py-2.5 px-3 text-right text-text-primary tabular-nums border-l border-border-light">{item.gf}</td>
                          <td className="py-2.5 px-3 text-right text-status-warning tabular-nums border-l border-border-light">{item.ga}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </ModalDialog>
  );
}
