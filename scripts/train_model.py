"""Train and evaluate prediction models for NBA game outcomes."""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
import joblib


def load_data(path: str = "data/poc_training_data.csv") -> pd.DataFrame:
    """Load training data."""
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} games")
    return df


def prepare_features(df: pd.DataFrame) -> tuple:
    """Prepare features and target."""
    feature_cols = [
        "t1_avg_pts", "t1_avg_ast", "t1_avg_reb",
        "t2_avg_pts", "t2_avg_ast", "t2_avg_reb", 
        "pt_diff", "ast_diff", "reb_diff",
    ]
    
    X = df[feature_cols].fillna(0)
    y = df["target"]
    
    return X, y, feature_cols


def train_models(X_train, X_test, y_train, y_test):
    """Train multiple models and compare."""
    results = {}
    
    # Scale features for logistic regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42),
    }
    
    print("\n" + "="*60)
    print("MODEL COMPARISON")
    print("="*60)
    
    for name, model in models.items():
        print(f"\n--- {name} ---")
        
        # Use scaled data for logistic regression
        if "Logistic" in name:
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_proba = model.predict_proba(X_test_scaled)[:, 1]
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        
        print(f"Accuracy: {acc:.3f}")
        print(f"AUC-ROC:  {auc:.3f}")
        
        results[name] = {
            "accuracy": acc,
            "auc": auc,
            "model": model,
        }
    
    # Find best model
    best_name = max(results, key=lambda x: results[x]["accuracy"])
    best = results[best_name]
    
    print("\n" + "="*60)
    print(f"BEST MODEL: {best_name}")
    print(f"Accuracy: {best['accuracy']:.3f}, AUC: {best['auc']:.3f}")
    print("="*60)
    
    return results, best_name, scaler


def analyze_features(model, feature_cols, X_train):
    """Show feature importance."""
    print("\n--- Feature Analysis ---")
    
    if hasattr(model, 'coef_'):
        # Logistic regression
        importance = model.coef_[0]
        print("Logistic Regression coefficients:")
        for feat, imp in sorted(zip(feature_cols, importance), key=lambda x: abs(x[1]), reverse=True):
            print(f"  {feat:15s}: {imp:+.3f}")
    elif hasattr(model, 'feature_importances_'):
        # Tree-based
        importance = model.feature_importances_
        print("Feature importances:")
        for feat, imp in sorted(zip(feature_cols, importance), key=lambda x: x[1], reverse=True):
            print(f"  {feat:15s}: {imp:.3f}")


def backtest(df, scaler=None):
    """Simple backtest by season."""
    print("\n--- Backtest by Season ---")
    
    # Extract season from game_id (e.g., "0022200001" -> "2022-23")
    df = df.copy()
    df["season_prefix"] = df["game_id"].astype(str).str[:2]
    df["season"] = df["season_prefix"].apply(lambda x: f"20{x[:2]}-{x[2:4]}")
    
    seasons = sorted(df["season"].unique())
    
    for season in seasons[-2:]:  # Last 2 seasons
        season_df = df[df["season"] == season]
        
        if len(season_df) < 100:
            continue
        
        feature_cols = [
            "t1_avg_pts", "t1_avg_ast", "t1_avg_reb",
            "t2_avg_pts", "t2_avg_ast", "t2_avg_reb", 
            "pt_diff", "ast_diff", "reb_diff",
        ]
        
        X = season_df[feature_cols].fillna(0)
        y = season_df["target"]
        
        # Train on prior seasons, test on this season
        prior_df = df[df["season"] < season]
        if len(prior_df) < 500:
            continue
            
        X_train = prior_df[feature_cols].fillna(0)
        y_train = prior_df["target"]
        
        # Train simple model
        model = GradientBoostingClassifier(n_estimators=50, max_depth=3, random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X)
        acc = accuracy_score(y, y_pred)
        
        print(f"  {season}: {len(season_df)} games, accuracy = {acc:.3f}")


if __name__ == "__main__":
    # Load data
    df = load_data("data/poc_training_data.csv")
    
    # Prepare
    X, y, feature_cols = prepare_features(df)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False  # Time-based split
    )
    
    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")
    print(f"Train target dist: {y_train.value_counts().to_dict()}")
    print(f"Test target dist: {y_test.value_counts().to_dict()}")
    
    # Train models
    results, best_name, scaler = train_models(X_train, X_test, y_train, y_test)
    
    # Feature analysis
    analyze_features(results[best_name]["model"], feature_cols, X_train)
    
    # Backtest
    backtest(df, scaler)
    
    # Save best model
    joblib.dump({
        "model": results[best_name]["model"],
        "scaler": scaler,
        "feature_cols": feature_cols,
    }, "data/poc_model.pkl")
    print(f"\n✓ Model saved to data/poc_model.pkl")