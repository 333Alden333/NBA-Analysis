"""Enhanced training with all features and proper evaluation."""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score, brier_score_loss
import joblib


def load_data(path: str = "data/poc_training_data_v2.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} games with {len(df.columns)} features")
    return df


def prepare_features(df: pd.DataFrame):
    """Prepare feature matrix."""
    feature_cols = [
        # Team rolling
        "t1_avg_pts", "t1_avg_ast", "t1_avg_reb",
        "t2_avg_pts", "t2_avg_ast", "t2_avg_reb",
        "pt_diff", "ast_diff", "reb_diff",
        # Rest days
        "t1_rest_days", "t2_rest_days",
        "t1_b2b", "t2_b2b",
        "rest_advantage",
        # Head-to-head
        "h2h_win_pct", "h2h_games",
        # Player-level
        "t1_top_player_pts", "t2_top_player_pts",
        "t1_top3_pts", "t2_top3_pts",
        # Momentum
        "t1_momentum", "t2_momentum", "t1_hot_players", "t2_hot_players", "momentum_diff",
        # Home advantage
        "t1_home_advantage", "t2_home_advantage",
    ]
    
    X = df[feature_cols].fillna(0)
    y = df["target"]
    
    return X, y, feature_cols


def analyze_feature_importance(model, feature_cols, X):
    """Detailed feature analysis with explanations."""
    print("\n" + "="*70)
    print("FEATURE IMPORTANCE ANALYSIS")
    print("="*70)
    
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importance = np.abs(model.coef_[0])
    else:
        return
    
    # Feature explanations
    explanations = {
        "pt_diff": "Point differential - strongest predictor",
        "t2_avg_pts": "Opponent scoring ability",
        "t1_avg_pts": "Team's scoring ability",
        "t2_avg_reb": "Opponent rebounding",
        "t1_avg_reb": "Team rebounding",
        "t1_avg_ast": "Team playmaking",
        "ast_diff": "Assist differential",
        "t2_avg_ast": "Opponent playmaking",
        "reb_diff": "Rebounding differential",
        "t1_rest_days": "Rest advantage - fresher team scores more",
        "t2_rest_days": "Opponent rest",
        "t1_b2b": "Back-to-back game penalty",
        "t2_b2b": "Opponent B2B",
        "rest_advantage": "Net rest days advantage",
        "h2h_win_pct": "Historical head-to-head record",
        "h2h_games": "Number of prior matchups",
        "t1_top_player_pts": "Best player scoring",
        "t2_top_player_pts": "Opponent's best player",
        "t1_top3_pts": "Top 3 players avg",
        "t2_top3_pts": "Opponent top 3",
        "t1_momentum": "Team momentum (positive=heating up)",
        "t2_momentum": "Opponent momentum",
        "t1_hot_players": "Count of players on hot streak",
        "t2_hot_players": "Opponent hot players",
        "momentum_diff": "Momentum differential",
        "t1_home_advantage": "Home court ~2-3 pts advantage (domain)",
        "t2_home_advantage": "Unknown - can't derive from data",
    }
    
    # Sort by importance
    sorted_features = sorted(zip(feature_cols, importance), key=lambda x: x[1], reverse=True)
    
    total = sum(importance)
    print(f"\n{'Feature':<25} {'Importance':<12} {'Weight %':<10} Explanation")
    print("-"*70)
    
    for feat, imp in sorted_features:
        pct = 100 * imp / total
        expl = explanations.get(feat, "")
        print(f"{feat:<25} {imp:.4f}       {pct:>5.1f}%      {expl}")
    
    return sorted_features


def train_and_evaluate(X, y, feature_cols):
    """Train models and evaluate."""
    # Time-based split (last 20% for testing)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )
    
    print(f"\n=== DATA SPLIT ===")
    print(f"Train: {len(X_train)} games | Test: {len(X_test)} games")
    print(f"Train win rate: {y_train.mean():.1%}")
    print(f"Test win rate: {y_test.mean():.1%}")
    
    # Scale for logistic regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {
        "Logistic Regression": (LogisticRegression(max_iter=1000, random_state=42), True),
        "Random Forest": (RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42), False),
        "Gradient Boosting": (GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42), False),
    }
    
    results = {}
    print(f"\n=== MODEL COMPARISON ===")
    print(f"{'Model':<25} {'Accuracy':<10} {'AUC-ROC':<10} {'Brier':<10}")
    print("-"*55)
    
    for name, (model, use_scaled) in models.items():
        if use_scaled:
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        brier = brier_score_loss(y_test, y_proba)
        
        print(f"{name:<25} {acc:.3f}       {auc:.3f}       {brier:.3f}")
        
        results[name] = {
            "accuracy": acc,
            "auc": auc,
            "brier": brier,
            "model": model,
            "scaled": use_scaled,
        }
    
    # Best model
    best_name = max(results, key=lambda x: results[x]["accuracy"])
    best = results[best_name]
    
    print(f"\n*** BEST: {best_name} ***")
    print(f"    Accuracy: {best['accuracy']:.1%}")
    print(f"    AUC-ROC: {best['auc']:.3f}")
    print(f"    Brier Score: {best['brier']:.3f} (lower is better)")
    
    return results, best_name, scaler


def backtest_by_season(df):
    """Backtest by season."""
    print(f"\n=== BACKTEST BY SEASON ===")
    
    # Extract season from game_date
    df = df.copy()
    df["game_date"] = pd.to_datetime(df["game_date"])
    df["season"] = df["game_date"].dt.year.apply(
        lambda y: f"{y}-{str(y+1)[-2:]}" if pd.notna(y) else "Unknown"
    )
    
    feature_cols = [
        "t1_avg_pts", "t1_avg_ast", "t1_avg_reb",
        "t2_avg_pts", "t2_avg_ast", "t2_avg_reb",
        "pt_diff", "ast_diff", "reb_diff",
        "t1_rest_days", "t2_rest_days", "t1_b2b", "t2_b2b", "rest_advantage",
        "h2h_win_pct", "h2h_games",
        "t1_top_player_pts", "t2_top_player_pts", "t1_top3_pts", "t2_top3_pts",
        "t1_momentum", "t2_momentum", "t1_hot_players", "t2_hot_players", "momentum_diff",
        "t1_home_advantage", "t2_home_advantage",
    ]
    
    seasons = sorted(df["season"].unique())
    
    print(f"\n{'Season':<12} {'Games':<8} {'Accuracy':<10} {'AUC':<8} {'Notes'}")
    print("-"*60)
    
    all_results = []
    
    for season in seasons:
        season_df = df[df["season"] == season]
        
        if len(season_df) < 50:
            continue
        
        # Train on all prior seasons
        prior_df = df[df["season"] < season]
        
        if len(prior_df) < 500:
            # For first season, use random split
            X_train = prior_df[feature_cols].fillna(0) if len(prior_df) > 0 else season_df[feature_cols].fillna(0)
            y_train = prior_df["target"] if len(prior_df) > 0 else season_df["target"]
            X_test = season_df[feature_cols].fillna(0)
            y_test = season_df["target"]
            train_note = "First season (no prior)"
        else:
            X_train = prior_df[feature_cols].fillna(0)
            y_train = prior_df["target"]
            X_test = season_df[feature_cols].fillna(0)
            y_test = season_df["target"]
            train_note = f"Trained on {len(prior_df)} prior games"
        
        if len(X_train) < 100:
            continue
        
        # Train simple model
        model = GradientBoostingClassifier(n_estimators=50, max_depth=3, random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        
        print(f"{season:<12} {len(season_df):<8} {acc:.3f}       {auc:.3f}   {train_note}")
        
        all_results.append({
            "season": season,
            "games": len(season_df),
            "accuracy": acc,
            "auc": auc,
        })
    
    # Summary
    if all_results:
        avg_acc = np.mean([r["accuracy"] for r in all_results])
        avg_auc = np.mean([r["auc"] for r in all_results])
        print("-"*60)
        print(f"{'AVERAGE':<12} {'':<8} {avg_acc:.3f}       {avg_auc:.3f}")
    
    return all_results


if __name__ == "__main__":
    # Load data
    df = load_data()
    
    # Prepare
    X, y, feature_cols = prepare_features(df)
    
    # Train and evaluate
    results, best_name, scaler = train_and_evaluate(X, y, feature_cols)
    
    # Feature importance
    best_model = results[best_name]["model"]
    use_scaled = results[best_name]["scaled"]
    
    if use_scaled:
        analyze_feature_importance(best_model, feature_cols, scaler.transform(X))
    else:
        analyze_feature_importance(best_model, feature_cols, X)
    
    # Backtest
    backtest_results = backtest_by_season(df)
    
    # Save model
    joblib.dump({
        "model": best_model,
        "scaler": scaler,
        "feature_cols": feature_cols,
        "use_scaled": use_scaled,
    }, "data/poc_model_v2.pkl")
    print(f"\n✓ Model saved to data/poc_model_v2.pkl")
