export const TEAMS = [
  { id: 1, name: 'Arsenal', short: 'Arsenal', abbr: 'ARS', color: '#EF0107', accent: '#063672', badge: '/badges/1.svg', stadium: 'Emirates Stadium' },
  { id: 2, name: 'Aston Villa', short: 'Aston Villa', abbr: 'AVL', color: '#95BFE5', accent: '#670E36', badge: '/badges/2.svg', stadium: 'Villa Park' },
  { id: 127, name: 'Bournemouth', short: 'Bournemouth', abbr: 'BOU', color: '#DA291C', accent: '#000000', badge: '/badges/127.svg', stadium: 'Vitality Stadium' },
  { id: 130, name: 'Brentford', short: 'Brentford', abbr: 'BRE', color: '#E30613', accent: '#FBB800', badge: '/badges/130.svg', stadium: 'Gtech Community Stadium' },
  { id: 131, name: 'Brighton & Hove Albion', short: 'Brighton', abbr: 'BHA', color: '#0057B8', accent: '#FFCD00', badge: '/badges/131.svg', stadium: 'Amex Stadium' },
  { id: 43, name: 'Burnley', short: 'Burnley', abbr: 'BUR', color: '#6C1D45', accent: '#99D6EA', badge: '/badges/43.svg', stadium: 'Turf Moor' },
  { id: 4, name: 'Chelsea', short: 'Chelsea', abbr: 'CHE', color: '#034694', accent: '#EE242C', badge: '/badges/4.svg', stadium: 'Stamford Bridge' },
  { id: 5, name: 'Coventry City', short: 'Coventry', abbr: 'COV', color: '#0084BD', accent: '#FFFFFF', badge: '/badges/5.svg', stadium: 'Coventry Building Society Arena' },
  { id: 6, name: 'Crystal Palace', short: 'Crystal Palace', abbr: 'CRY', color: '#1B458F', accent: '#C4122E', badge: '/badges/6.svg', stadium: 'Selhurst Park' },
  { id: 7, name: 'Everton', short: 'Everton', abbr: 'EVE', color: '#003399', accent: '#FFFFFF', badge: '/badges/7.svg', stadium: 'Goodison Park' },
  { id: 34, name: 'Fulham', short: 'Fulham', abbr: 'FUL', color: '#000000', accent: '#CC0000', badge: '/badges/34.svg', stadium: 'Craven Cottage' },
  { id: 41, name: 'Hull City', short: 'Hull City', abbr: 'HUL', color: '#F5911E', accent: '#000000', badge: '/badges/41.svg', stadium: 'MKM Stadium' },
  { id: 8, name: 'Ipswich Town', short: 'Ipswich', abbr: 'IPS', color: '#003399', accent: '#FFFFFF', badge: '/badges/8.svg', stadium: 'Portman Road' },
  { id: 9, name: 'Leeds United', short: 'Leeds', abbr: 'LEE', color: '#FFCD00', accent: '#1D428A', badge: '/badges/9.svg', stadium: 'Elland Road' },
  { id: 26, name: 'Leicester City', short: 'Leicester', abbr: 'LEI', color: '#003090', accent: '#FDBE11', badge: '/badges/26.svg', stadium: 'King Power Stadium' },
  { id: 10, name: 'Liverpool', short: 'Liverpool', abbr: 'LIV', color: '#C8102E', accent: '#00B2A9', badge: '/badges/10.svg', stadium: 'Anfield' },
  { id: 11, name: 'Manchester City', short: 'Man City', abbr: 'MCI', color: '#6CABDD', accent: '#1C2C5B', badge: '/badges/11.svg', stadium: 'Etihad Stadium' },
  { id: 12, name: 'Manchester United', short: 'Man Utd', abbr: 'MUN', color: '#DA291C', accent: '#FBE122', badge: '/badges/12.svg', stadium: 'Old Trafford' },
  { id: 23, name: 'Newcastle United', short: 'Newcastle', abbr: 'NEW', color: '#241F20', accent: '#41B6E6', badge: '/badges/23.svg', stadium: 'St. James\' Park' },
  { id: 15, name: 'Nottingham Forest', short: 'Nott\'m Forest', abbr: 'NFO', color: '#DD0000', accent: '#FFFFFF', badge: '/badges/15.svg', stadium: 'The City Ground' },
  { id: 20, name: 'Southampton', short: 'Southampton', abbr: 'SOU', color: '#D71920', accent: '#130C0E', badge: '/badges/20.svg', stadium: 'St. Mary\'s Stadium' },
  { id: 29, name: 'Sunderland', short: 'Sunderland', abbr: 'SUN', color: '#EB172B', accent: '#000000', badge: '/badges/29.svg', stadium: 'Stadium of Light' },
  { id: 21, name: 'Tottenham Hotspur', short: 'Spurs', abbr: 'TOT', color: '#132257', accent: '#FFFFFF', badge: '/badges/21.svg', stadium: 'Tottenham Hotspur Stadium' },
  { id: 25, name: 'West Ham United', short: 'West Ham', abbr: 'WHU', color: '#7A263A', accent: '#1BB1E7', badge: '/badges/25.svg', stadium: 'London Stadium' },
  { id: 38, name: 'Wolverhampton Wanderers', short: 'Wolves', abbr: 'WOL', color: '#FDB913', accent: '#231F20', badge: '/badges/38.svg', stadium: 'Molineux Stadium' },
];

export const TEAM_MAP = Object.fromEntries(TEAMS.map(t => [t.id, t]));

export function getTeam(teamId, fallbackName = 'Takım') {
  if (TEAM_MAP[teamId]) return TEAM_MAP[teamId];
  return {
    id: teamId,
    name: fallbackName,
    short: fallbackName,
    abbr: fallbackName ? fallbackName.substring(0, 3).toUpperCase() : 'PL',
    badge: `/badges/${teamId}.svg`,
    color: '#38003c',
    accent: '#059669',
    stadium: 'Premier League Ground',
  };
}
