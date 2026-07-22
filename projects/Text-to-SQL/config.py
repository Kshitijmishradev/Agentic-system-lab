"""
Config for the database analyst — the schema description fed to every model,
and the list of local models used in the debate.

The schema description is what makes text-to-SQL work: the models can't see
the database, so we describe it to them. The notes about api_id joins and
home/away goals are included on purpose — they're the exact things models
get wrong, and stating them upfront improves query quality.
"""

DB_FILENAME = "database.sqlite"

MODELS = ["llama3.1", "gemma3:4b", "deepseek-coder:6.7b"]  # edit to match `ollama list`
CRITIC_MODEL = "llama3.1"

SCHEMA_DESCRIPTION = """You are querying the European Soccer Database (SQLite).
It covers 11 leagues across 11 countries, ~25,000 matches, ~11,000 players.

Tables and key columns:

Country(id, name)
League(id, country_id, name)   -- league belongs to a country
Team(id, team_api_id, team_long_name, team_short_name)
Player(id, player_api_id, player_name, birthday, height, weight)
Player_Attributes(id, player_api_id, date, overall_rating, potential, ...many skill columns...)
Team_Attributes(id, team_api_id, date, buildUpPlaySpeed, ...many tactic columns...)
Match(id, country_id, league_id, season, stage, date,
      home_team_api_id, away_team_api_id, home_team_goal, away_team_goal, ...)

CRITICAL JOIN RULES (models often get these wrong — follow them exactly):
- To join Match to Team, use Team.team_api_id = Match.home_team_api_id
  (or away_team_api_id). Do NOT join on Team.id.
- To join Player_Attributes or Team_Attributes to Player/Team, use player_api_id
  / team_api_id, NOT id.
- There is no single "goals scored by a team" column. A team's total goals =
  sum of home_team_goal in matches where it was home, PLUS away_team_goal in
  matches where it was away. Use a UNION ALL subquery for this.
- League.name already encodes the country (e.g. "Spain LIGA BBVA").

Write ONE valid SQLite SELECT statement to answer the question. Only SELECT
is permitted — never INSERT/UPDATE/DELETE/DROP/ALTER.
"""
