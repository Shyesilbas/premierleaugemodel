import { Activity, Calendar, Coins, Shield, Users } from 'lucide-react';

export default function TeamProfileNavigation({ profile, activeTeamTab, setActiveTeamTab, displayedSquad, managerChanges }) {
  if (!profile) return null;

  return (
    <div className="flex items-center gap-1.5 p-1.5 bg-slate-100 rounded-2xl border border-slate-200 overflow-x-auto scrollbar-none">
              <button
                type="button"
                onClick={() => setActiveTeamTab('fixtures')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
                  activeTeamTab === 'fixtures'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <Calendar className="w-4 h-4" />
                <span>Fikstür & Sonuçlar</span>
                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
                  activeTeamTab === 'fixtures' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
                }`}>
                  {profile?.matches?.length || 0}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTeamTab('profile')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
                  activeTeamTab === 'profile'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <Activity className="w-4 h-4" />
                <span>Oyun Profili & Analiz</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTeamTab('squad')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
                  activeTeamTab === 'squad'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <Users className="w-4 h-4" />
                <span>Kadro Listesi</span>
                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
                  activeTeamTab === 'squad' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
                }`}>
                  {displayedSquad.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTeamTab('managers')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
                  activeTeamTab === 'managers'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <Shield className="w-4 h-4" />
                <span>Teknik Direktörler</span>
                {managerChanges.length > 0 && (
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full ${
                    activeTeamTab === 'managers' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-600'
                  }`}>
                    {managerChanges.length}
                  </span>
                )}
              </button>

              <button
                type="button"
                onClick={() => setActiveTeamTab('transfers')}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-black transition-all whitespace-nowrap ${
                  activeTeamTab === 'transfers'
                    ? 'bg-[#38003c] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                <Coins className="w-4 h-4 text-amber-500" />
                <span>Transfer Geçmişi</span>
              </button>
            </div>
  );
}
