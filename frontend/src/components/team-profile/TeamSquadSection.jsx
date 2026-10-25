import { ArrowDown, ArrowUp, Users } from 'lucide-react';
import EmptyState from '../common/EmptyState';
import { SQUAD_POSITION_TABS, getPositionLabel } from './teamProfileUtils';

const COLUMNS = [
  { field: 'shirt', label: 'No', align: 'left', title: 'Forma numarasına göre sırala' },
  { field: 'name', label: 'Oyuncu', align: 'left', title: 'İsme göre sırala' },
  { field: 'position', label: 'Mevki', align: 'left', title: 'Mevkiye göre sırala', hideOnMobile: true },
  { field: 'market_value_eur', label: 'Piyasa değeri', align: 'right', title: 'Piyasa değerine göre sırala', hideOnMobile: true },
  { field: 'appearances', label: 'Maç', align: 'right', title: 'Oynadığı maç sayısına göre sırala' },
  { field: 'starts', label: 'İlk 11', align: 'right', title: 'İlk 11 başlama sayısına göre sırala' },
  { field: 'goals', label: 'Gol', align: 'right', title: 'Gol sayısına göre sırala' },
  { field: 'assists', label: 'Asist', align: 'right', title: 'Asist sayısına göre sırala' },
  { field: 'yellow_cards', label: 'Sarı', align: 'right', title: 'Sarı karta göre sırala' },
  { field: 'red_cards', label: 'Kırmızı', align: 'right', title: 'Kırmızı karta göre sırala' },
];

function FilterButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`h-8 px-3 rounded text-sm font-medium inline-flex items-center gap-1.5 shrink-0 border transition-colors duration-150 ease-out cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus ${
        active
          ? 'bg-primary border-primary text-white'
          : 'bg-background-primary border-border text-text-secondary hover:text-text-primary hover:border-card-border-hover'
      }`}
    >
      {children}
    </button>
  );
}

const count = (value) => value ?? 0;

export default function TeamSquadSection({
  activeTeamTab,
  displayedSquad,
  currentMeta,
  selectedSquadTab,
  setSelectedSquadTab,
  teamStaff,
  displayedSquadCounts,
  filteredSquad,
  handleSquadSort,
  squadSortField,
  squadSortDirection,
  setSelectedPlayerForMv,
}) {
  if (activeTeamTab !== 'squad' || displayedSquad.length === 0) return null;

  return (
    <section aria-label="Kadro listesi" className="flex flex-col gap-4">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-3 pb-4 border-b border-border">
        <div className="flex flex-col gap-1 min-w-0">
          <h3 className="text-lg font-semibold text-text-primary">Kadro</h3>
          <p className="text-sm text-text-secondary tabular-nums">
            {currentMeta.name} · {selectedSquadTab === 'all' ? displayedSquad.length : `${filteredSquad.length} / ${displayedSquad.length}`} oyuncu
            {teamStaff?.players?.length > 0 && ' · PulseLive lisanslı kadro'}
          </p>
        </div>

        <div className="flex items-center gap-2 overflow-x-auto" role="group" aria-label="Mevki filtresi">
          {SQUAD_POSITION_TABS.map(tab => (
            <FilterButton key={tab.id} active={selectedSquadTab === tab.id} onClick={() => setSelectedSquadTab(tab.id)}>
              {tab.label}
              <span className="tabular-nums opacity-70">{displayedSquadCounts[tab.id] || 0}</span>
            </FilterButton>
          ))}
        </div>
      </div>

      {filteredSquad.length === 0 ? (
        <EmptyState icon={Users}>Bu mevkide kayıtlı oyuncu bulunamadı.</EmptyState>
      ) : (
        <div className="overflow-x-auto bg-background-primary border border-border rounded">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="bg-background-tertiary border-b border-border text-text-secondary">
                {COLUMNS.map((col, index) => {
                  const active = squadSortField === col.field;
                  const Arrow = squadSortDirection === 'asc' ? ArrowUp : ArrowDown;
                  return (
                    <th
                      key={col.field}
                      scope="col"
                      aria-sort={active ? (squadSortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
                      className={`font-medium ${index > 0 ? 'border-l border-border' : ''} ${col.align === 'right' ? 'text-right' : ''} ${col.hideOnMobile ? 'hidden sm:table-cell' : ''}`}
                    >
                      <button
                        type="button"
                        onClick={() => handleSquadSort(col.field)}
                        title={col.title}
                        className={`w-full py-2 px-3 inline-flex items-center gap-1 whitespace-nowrap cursor-pointer transition-colors duration-150 ease-out hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-border-focus ${col.align === 'right' ? 'justify-end' : ''} ${active ? 'text-text-primary' : ''}`}
                      >
                        {col.label}
                        {active && <Arrow className="w-3.5 h-3.5" strokeWidth={1.5} aria-hidden="true" />}
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light">
              {filteredSquad.map(player => (
                <tr key={player.id} className="transition-colors duration-150 ease-out hover:bg-background-tertiary">
                  <td className="py-2.5 px-3 whitespace-nowrap text-text-secondary tabular-nums">
                    {player.shirt != null && player.shirt !== '' ? player.shirt : '—'}
                  </td>

                  <td className="py-2.5 px-3 border-l border-border-light">
                    <span className="flex items-center gap-2 min-w-36">
                      <span className="font-medium text-text-primary truncate">{player.name}</span>
                      {player.captain && <span className="shrink-0 text-xs text-text-secondary">Kaptan</span>}
                    </span>
                    <span className="sm:hidden block text-xs text-text-tertiary">{getPositionLabel(player.position)}</span>
                  </td>

                  <td className="hidden sm:table-cell py-2.5 px-3 whitespace-nowrap text-text-secondary border-l border-border-light">
                    {getPositionLabel(player.position)}
                  </td>

                  <td className="hidden sm:table-cell py-2.5 px-3 whitespace-nowrap text-right tabular-nums border-l border-border-light">
                    {player.market_value_formatted ? (
                      <button
                        type="button"
                        onClick={() => setSelectedPlayerForMv(player)}
                        title={`${player.name} piyasa değeri geçmişi`}
                        className="text-text-primary hover:underline cursor-pointer rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
                      >
                        {player.market_value_formatted}
                      </button>
                    ) : (
                      <span className="text-text-muted">—</span>
                    )}
                  </td>

                  <td className="py-2.5 px-3 text-right tabular-nums text-text-primary border-l border-border-light">{count(player.appearances)}</td>
                  <td className="py-2.5 px-3 text-right tabular-nums text-text-secondary border-l border-border-light">{count(player.starts)}</td>
                  <td className={`py-2.5 px-3 text-right tabular-nums border-l border-border-light ${player.goals > 0 ? 'font-medium text-text-primary' : 'text-text-muted'}`}>{count(player.goals)}</td>
                  <td className={`py-2.5 px-3 text-right tabular-nums border-l border-border-light ${player.assists > 0 ? 'font-medium text-text-primary' : 'text-text-muted'}`}>{count(player.assists)}</td>
                  <td className={`py-2.5 px-3 text-right tabular-nums border-l border-border-light ${player.yellow_cards > 0 ? 'text-text-primary' : 'text-text-muted'}`}>{count(player.yellow_cards)}</td>
                  <td className={`py-2.5 px-3 text-right tabular-nums border-l border-border-light ${player.red_cards > 0 ? 'font-medium text-status-error' : 'text-text-muted'}`}>{count(player.red_cards)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
