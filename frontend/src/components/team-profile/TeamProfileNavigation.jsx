import { Activity, Calendar, Coins, Shield, Users } from 'lucide-react';

export default function TeamProfileNavigation({ profile, activeTeamTab, setActiveTeamTab, displayedSquad, managerChanges }) {
  if (!profile) return null;

  return (
    <div className="flex items-center gap-1.5 p-1 bg-background-tertiary rounded border border-border overflow-x-auto">
      <button
        type="button"
        onClick={() => setActiveTeamTab('fixtures')}
        className={`flex items-center gap-2 px-3.5 py-2 rounded-sm text-xs font-medium transition-colors whitespace-nowrap ${
          activeTeamTab === 'fixtures'
            ? 'bg-primary text-white'
            : 'text-text-secondary hover:text-text-primary hover:bg-border-light'
        }`}
      >
        <Calendar className="w-3.5 h-3.5" />
        <span>Fikstür & Sonuçlar</span>
        <span className={`text-xs tabular-nums font-medium px-1.5 py-0.2 rounded-sm tabular-nums ${
          activeTeamTab === 'fixtures' ? 'bg-white/20 text-white' : 'bg-background-primary text-text-secondary border border-border'
        }`}>
          {profile?.matches?.length || 0}
        </span>
      </button>

      <button
        type="button"
        onClick={() => setActiveTeamTab('profile')}
        className={`flex items-center gap-2 px-3.5 py-2 rounded-sm text-xs font-medium transition-colors whitespace-nowrap ${
          activeTeamTab === 'profile'
            ? 'bg-primary text-white'
            : 'text-text-secondary hover:text-text-primary hover:bg-border-light'
        }`}
      >
        <Activity className="w-3.5 h-3.5" />
        <span>Oyun Profili & Analiz</span>
      </button>

      <button
        type="button"
        onClick={() => setActiveTeamTab('squad')}
        className={`flex items-center gap-2 px-3.5 py-2 rounded-sm text-xs font-medium transition-colors whitespace-nowrap ${
          activeTeamTab === 'squad'
            ? 'bg-primary text-white'
            : 'text-text-secondary hover:text-text-primary hover:bg-border-light'
        }`}
      >
        <Users className="w-3.5 h-3.5" />
        <span>Kadro Listesi</span>
        <span className={`text-xs tabular-nums font-medium px-1.5 py-0.2 rounded-sm tabular-nums ${
          activeTeamTab === 'squad' ? 'bg-white/20 text-white' : 'bg-background-primary text-text-secondary border border-border'
        }`}>
          {displayedSquad.length}
        </span>
      </button>

      <button
        type="button"
        onClick={() => setActiveTeamTab('managers')}
        className={`flex items-center gap-2 px-3.5 py-2 rounded-sm text-xs font-medium transition-colors whitespace-nowrap ${
          activeTeamTab === 'managers'
            ? 'bg-primary text-white'
            : 'text-text-secondary hover:text-text-primary hover:bg-border-light'
        }`}
      >
        <Shield className="w-3.5 h-3.5" />
        <span>Teknik Direktörler</span>
        {managerChanges.length > 0 && (
          <span className={`text-xs tabular-nums font-medium px-1.5 py-0.2 rounded-sm tabular-nums ${
            activeTeamTab === 'managers' ? 'bg-white/20 text-white' : 'bg-background-primary text-text-secondary border border-border'
          }`}>
            {managerChanges.length}
          </span>
        )}
      </button>

      <button
        type="button"
        onClick={() => setActiveTeamTab('transfers')}
        className={`flex items-center gap-2 px-3.5 py-2 rounded-sm text-xs font-medium transition-colors whitespace-nowrap ${
          activeTeamTab === 'transfers'
            ? 'bg-primary text-white'
            : 'text-text-secondary hover:text-text-primary hover:bg-border-light'
        }`}
      >
        <Coins className="w-3.5 h-3.5" />
        <span>Transfer Geçmişi</span>
      </button>
    </div>
  );
}
