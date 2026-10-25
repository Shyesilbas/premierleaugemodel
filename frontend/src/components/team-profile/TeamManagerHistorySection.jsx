import { ChevronRight, Shield } from 'lucide-react';
import { formatSeasonLabel } from '../../utils/dateFormatters';

export default function TeamManagerHistorySection({ activeTeamTab, teamSeason, managerChanges }) {
  if (activeTeamTab !== 'managers') return null;

  return (
            <section className="overflow-hidden rounded border border-border bg-background-primary">
              <div className="flex items-center justify-between gap-3 border-b border-border-light bg-background-tertiary-violet-50 to-white px-4 py-3.5 sm:px-5">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded bg-background-tertiary text-text-primary">
                    <Shield className="h-4 w-4" />
                  </span>
                  <div>
                    <h3 className="text-xs font-semibold text-text-primary">Teknik direktör geçmişi</h3>
                    <p className="mt-0.5 text-xs text-text-secondary">
                      {teamSeason === 'all' ? 'Tüm kayıtlı sezonlar' : `${formatSeasonLabel(teamSeason)} sezonu`}
                    </p>
                  </div>
                </div>
                <span className="rounded-full border border-border bg-background-primary px-2.5 py-1 text-xs font-semibold text-text-primary">
                  {managerChanges.length} değişiklik
                </span>
              </div>
              {managerChanges.length ? (
                <div className="divide-y divide-border-light">
                  {managerChanges.map((change, index) => {
                    const interim = change.appointment_type === 'interim';
                    return (
                      <div key={`${change.season}-${change.appointment_date}-${index}`} className="flex items-center gap-3 px-4 py-3 sm:px-5">
                        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ring-4 ${interim ? 'bg-status-warning ring-border' : 'bg-primary ring-border'}`} />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                            <span className="text-xs font-semibold text-text-primary">{change.outgoing_manager}</span>
                            <ChevronRight className="h-3 w-3 text-text-muted" />
                            <span className="text-xs font-semibold text-text-primary">{change.incoming_manager}</span>
                          </div>
                          <p className="mt-1 text-xs text-text-secondary">
                            {new Date(`${change.appointment_date}T12:00:00`).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })}
                            <span className="mx-1.5 text-text-muted">·</span>{formatSeasonLabel(change.season)}
                            <span className="mx-1.5 text-text-muted">·</span>Hafta {change.gameweek}
                          </p>
                        </div>
                        <span className={`shrink-0 rounded-full px-2 py-1 text-xs font-semibold ${interim ? 'bg-background-tertiary text-status-warning' : 'bg-background-tertiary text-text-primary'}`}>
                          {interim ? 'Geçici' : 'Atama'}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="px-4 py-8 text-center text-xs text-text-secondary">Bu sezon için kayıtlı teknik direktör değişikliği yok.</p>
              )}
            </section>
  );
}
