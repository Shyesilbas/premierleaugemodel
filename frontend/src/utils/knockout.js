// Presentation helpers for knockout fixtures (two-legged ties and the final).

export const STAGE_LABELS = {
  playoff: 'Play-off',
  r16: 'Son 16',
  qf: 'Çeyrek final',
  sf: 'Yarı final',
  final: 'Final',
};

export const REASON_SUFFIX = {
  WIN_ON_EXTRA_TIME: 'uzatmalarda',
  WIN_ON_PENALTIES: 'penaltılarla',
};

export function penaltyText(home, away) {
  return home != null && away != null ? `P ${home}-${away}` : null;
}

// One short line per match: "1. maç" / "2. maç". Who went through is shown on the deciding match only:
// the second leg of a tie, or the final (a single match).
export function tieNote(match) {
  const tie = match?.tie;
  if (!tie) return null;
  const leg = tie.legs > 1 && tie.leg ? `${tie.leg}. maç` : null;
  const isFirstLeg = tie.legs > 1 && tie.leg === 1;
  if (!tie.decided || isFirstLeg) return { leg, result: null };

  const isFinal = match.stage === 'final';
  const how = REASON_SUFFIX[tie.advance_reason];
  const total = tie.aggregate ? `Toplam ${tie.aggregate.home}-${tie.aggregate.away}` : null;
  const parts = [isFinal ? `${tie.advanced_team_name} şampiyon` : `${tie.advanced_team_name} tur atladı`];
  if (total) parts.push(total);
  if (how) parts.push(how);
  return { leg, result: parts.join(' · '), advancedTeamId: tie.advanced_team_id };
}
