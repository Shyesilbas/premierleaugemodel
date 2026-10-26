// Seasons that have data, per competition. UEFA competitions have no "all seasons" view: tables, squads and
// ties are per season, so a mixed view would be misleading.
export const PREMIER_LEAGUE_SEASONS = ['2026_27', '2025_26', '2024_25', '2023_24', '2022_23', 'all'];
export const UEFA_SEASONS = ['2026_27', '2025_26', '2024_25', '2023_24', '2022_23'];

export const NATIONAL_LEAGUE_SEASONS = ['2026_27', '2025_26', '2024_25', '2023_24', '2022_23'];

export const seasonsFor = competitionKey => {
  if (competitionKey === 'premier_league') return PREMIER_LEAGUE_SEASONS;
  if (competitionKey === 'champions_league' || competitionKey === 'europa_league') return UEFA_SEASONS;
  return NATIONAL_LEAGUE_SEASONS;
};
