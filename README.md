# HermesAnalysis NBA Prediction Platform

AI-powered NBA analysis and prediction platform with ML models, pattern recognition, and natural language querying.

## Features

- **ML Predictions**: Custom GBM models with 73.5% accuracy
- **Pattern Recognition**: Matchup analysis (EXPLOITABLE/TOUGH/NEUTRAL)
- **ELO Rankings**: Team strength ratings
- **CLI Dashboard**: Interactive terminal interface
- **MCP Integration**: Query via Hermes Agent natural language

## Quick Start

```bash
cd ~/HermesAnalysis
python3 scripts/cli.py
```

## CLI Commands

- `/elo` - Team ELO rankings
- `/predict <team1> <team2>` - Matchup prediction
- `/player <name>` - Player stats
- `/matchup <player> vs <team>` - Matchup classification
- `/momentum` - Who's hot/cold
- `/help` - All commands

## Requirements

- Python 3.10+
- SQLite
- See `pyproject.toml` for dependencies

## License

MIT License - See LICENSE file
