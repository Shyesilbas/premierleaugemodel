import PlayerMarketValueHistoryModal from '../PlayerMarketValueHistoryModal';
import MarketValueHistoryModal from './MarketValueHistoryModal';
import { getTeam } from '../../data/teams';
import { getPositionLabel } from './teamProfileUtils';

export default function TeamMarketValueDialogs({ profile, teamSeason, showMarketValueModal, onCloseMarketValue, selectedPlayer, onClosePlayer }) {
  return (
    <>
      {/* Market Value 5-Year Evolution Modal */}
            {showMarketValueModal && profile?.market_value && (
              <MarketValueHistoryModal
                isOpen={showMarketValueModal}
                onClose={() => onCloseMarketValue()}
                profile={profile}
                selectedSeason={teamSeason}
              />
            )}

            {/* Player Market Value Career Evolution Modal */}
            {selectedPlayer && (
              <PlayerMarketValueHistoryModal
                isOpen={Boolean(selectedPlayer)}
                onClose={onClosePlayer}
                player={selectedPlayer}
                playerId={selectedPlayer.tm_id || selectedPlayer.id}
                playerName={selectedPlayer.name}
                playerPhoto={selectedPlayer.photo_url}
                teamBadge={profile?.team?.badge || getTeam(profile?.team?.id, profile?.team?.name).badge}
                teamName={profile?.team?.name}
                position={getPositionLabel(selectedPlayer.position)}
              />
            )}
    </>
  );
}
