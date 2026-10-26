const EUROPEAN_KEYS = ['champions_league', 'europa_league'];

/** Only competitions with a prediction model (the Premier League) predict; every other match shows data only. */
export const hasModelPrediction = (match, competitionHasModel) => (
  Boolean(competitionHasModel)
  && !EUROPEAN_KEYS.includes(match?.competition?.key)
  && ![2, 3].includes(Number(match?.competition_id))
);
