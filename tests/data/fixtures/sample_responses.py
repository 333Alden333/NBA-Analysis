"""Realistic mock responses matching nba_api endpoint output."""

import pandas as pd


def player_info_df():
    """CommonPlayerInfo response DataFrame."""
    return pd.DataFrame([{
        "PERSON_ID": 201939,
        "DISPLAY_FIRST_LAST": "Stephen Curry",
        "FIRST_NAME": "Stephen",
        "LAST_NAME": "Curry",
        "TEAM_ID": 1610612744,
        "TEAM_ABBREVIATION": "GSW",
        "JERSEY": "30",
        "POSITION": "G",
        "HEIGHT": "6-2",
        "WEIGHT": "185",
        "BIRTHDATE": "1988-03-14T00:00:00",
        "COUNTRY": "USA",
        "SEASON_EXP": 15,
        "ROSTERSTATUS": "Active",
    }])


def player_game_log_df():
    """PlayerGameLog response DataFrame."""
    return pd.DataFrame([
        {
            "SEASON_ID": "22024",
            "GAME_ID": "0022400100",
            "GAME_DATE": "DEC 25, 2024",
            "MATCHUP": "GSW vs. LAL",
            "WL": "W",
            "MIN": 36,
            "PTS": 32,
            "REB": 5,
            "AST": 8,
            "STL": 2,
            "BLK": 0,
            "TOV": 3,
            "FGM": 11,
            "FGA": 22,
            "FG3M": 6,
            "FG3A": 13,
            "FTM": 4,
            "FTA": 4,
            "OREB": 1,
            "DREB": 4,
            "PF": 2,
            "PLUS_MINUS": 12,
        },
        {
            "SEASON_ID": "22024",
            "GAME_ID": "0022400101",
            "GAME_DATE": "DEC 27, 2024",
            "MATCHUP": "GSW @ LAC",
            "WL": "L",
            "MIN": 34,
            "PTS": 24,
            "REB": 4,
            "AST": 6,
            "STL": 1,
            "BLK": 0,
            "TOV": 4,
            "FGM": 8,
            "FGA": 20,
            "FG3M": 4,
            "FG3A": 11,
            "FTM": 4,
            "FTA": 5,
            "OREB": 0,
            "DREB": 4,
            "PF": 3,
            "PLUS_MINUS": -5,
        },
    ])


def box_score_player_stats_df():
    """BoxScoreTraditionalV3 PlayerStats DataFrame."""
    return pd.DataFrame([
        {
            "gameId": "0022400100",
            "teamId": 1610612744,
            "personId": 201939,
            "firstName": "Stephen",
            "familyName": "Curry",
            "minutes": "PT36M00.00S",
            "points": 32,
            "reboundsTotal": 5,
            "assists": 8,
            "steals": 2,
            "blocks": 0,
            "turnovers": 3,
            "fieldGoalsMade": 11,
            "fieldGoalsAttempted": 22,
            "threePointersMade": 6,
            "threePointersAttempted": 13,
            "freeThrowsMade": 4,
            "freeThrowsAttempted": 4,
            "plusMinusPoints": 12.0,
            "reboundsOffensive": 1,
            "reboundsDefensive": 4,
            "foulsPersonal": 2,
        },
    ])


def box_score_team_stats_df():
    """BoxScoreTraditionalV3 TeamStats DataFrame."""
    return pd.DataFrame([
        {
            "gameId": "0022400100",
            "teamId": 1610612744,
            "teamTricode": "GSW",
            "points": 112,
            "reboundsTotal": 44,
            "assists": 28,
        },
    ])


def play_by_play_df():
    """PlayByPlayV3 response DataFrame."""
    return pd.DataFrame([
        {
            "actionNumber": 1,
            "period": 1,
            "clock": "PT12M00.00S",
            "actionType": "jumpball",
            "description": "Jump Ball",
            "personId": 201939,
            "teamId": 1610612744,
            "scoreHome": "0",
            "scoreAway": "0",
        },
        {
            "actionNumber": 2,
            "period": 1,
            "clock": "PT11M45.00S",
            "actionType": "2pt",
            "description": "Curry 2' Layup (2 PTS)",
            "personId": 201939,
            "teamId": 1610612744,
            "scoreHome": "2",
            "scoreAway": "0",
        },
    ])


def shot_chart_df():
    """ShotChartDetail response DataFrame."""
    return pd.DataFrame([
        {
            "GAME_ID": "0022400100",
            "PLAYER_ID": 201939,
            "TEAM_ID": 1610612744,
            "PERIOD": 1,
            "MINUTES_REMAINING": 10,
            "SECONDS_REMAINING": 30,
            "ACTION_TYPE": "Jump Shot",
            "SHOT_TYPE": "3PT Field Goal",
            "SHOT_ZONE_BASIC": "Above the Break 3",
            "SHOT_ZONE_AREA": "Center(C)",
            "SHOT_ZONE_RANGE": "24+ ft.",
            "SHOT_DISTANCE": 25,
            "LOC_X": 10,
            "LOC_Y": 200,
            "SHOT_MADE_FLAG": 1,
        },
        {
            "GAME_ID": "0022400100",
            "PLAYER_ID": 201939,
            "TEAM_ID": 1610612744,
            "PERIOD": 2,
            "MINUTES_REMAINING": 5,
            "SECONDS_REMAINING": 15,
            "ACTION_TYPE": "Layup Shot",
            "SHOT_TYPE": "2PT Field Goal",
            "SHOT_ZONE_BASIC": "Restricted Area",
            "SHOT_ZONE_AREA": "Center(C)",
            "SHOT_ZONE_RANGE": "Less Than 8 ft.",
            "SHOT_DISTANCE": 2,
            "LOC_X": -5,
            "LOC_Y": 10,
            "SHOT_MADE_FLAG": 0,
        },
    ])


def league_standings_df():
    """LeagueStandingsV3 response DataFrame."""
    return pd.DataFrame([
        {
            "TeamID": 1610612744,
            "TeamCity": "Golden State",
            "TeamName": "Warriors",
            "TeamAbbreviation": "GSW",
            "Conference": "West",
            "Division": "Pacific",
            "WINS": 25,
            "LOSSES": 15,
            "ConferenceRank": 4,
        },
        {
            "TeamID": 1610612747,
            "TeamCity": "Los Angeles",
            "TeamName": "Lakers",
            "TeamAbbreviation": "LAL",
            "Conference": "West",
            "Division": "Pacific",
            "WINS": 22,
            "LOSSES": 18,
            "ConferenceRank": 7,
        },
    ])


def season_games_df():
    """LeagueGameFinder response DataFrame."""
    return pd.DataFrame([
        {
            "GAME_ID": "0022400100",
            "GAME_DATE": "2024-12-25",
            "TEAM_ID": 1610612744,
            "TEAM_ABBREVIATION": "GSW",
            "MATCHUP": "GSW vs. LAL",
            "WL": "W",
            "PTS": 112,
        },
        {
            "GAME_ID": "0022400101",
            "GAME_DATE": "2024-12-27",
            "TEAM_ID": 1610612744,
            "TEAM_ABBREVIATION": "GSW",
            "MATCHUP": "GSW @ LAC",
            "WL": "L",
            "PTS": 98,
        },
    ])


def schedule_df():
    """ScheduleLeagueV2 response DataFrame."""
    return pd.DataFrame([
        {
            "GAME_ID": "0022400100",
            "GAME_DATE": "2024-12-25",
            "HOME_TEAM_ID": 1610612744,
            "AWAY_TEAM_ID": 1610612747,
            "ARENA_NAME": "Chase Center",
            "GAME_STATUS_TEXT": "Final",
        },
        {
            "GAME_ID": "0022400101",
            "GAME_DATE": "2024-12-27",
            "HOME_TEAM_ID": 1610612746,
            "AWAY_TEAM_ID": 1610612744,
            "ARENA_NAME": "Crypto.com Arena",
            "GAME_STATUS_TEXT": "Final",
        },
    ])
