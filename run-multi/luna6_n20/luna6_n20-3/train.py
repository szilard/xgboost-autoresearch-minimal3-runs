import pandas as pd
import numpy as np
import time
import xgboost as xgb
from sklearn.ensemble import VotingClassifier
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
target_y = (train[target] == "Y").astype(float)
target_prior = float(target_y.mean())
origin_rate_stats = target_y.groupby(train["Origin"]).agg(["sum", "count"])
origin_delay_rate = (
    (origin_rate_stats["sum"] + 500 * target_prior)
    / (origin_rate_stats["count"] + 500)
)

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["OriginDelayRate"] = df["Origin"].map(origin_delay_rate).fillna(target_prior)
    dep_minutes = (df["CRSDepTime"] // 100) * 60 + (df["CRSDepTime"] % 100)
    angle = 2 * np.pi * dep_minutes / 1440
    X["DepTimeSin"] = np.sin(angle)
    X["DepTimeCos"] = np.cos(angle)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = VotingClassifier(
    estimators=[
        ("slow", xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            enable_categorical=True,
            random_state=42,
            n_jobs=-1,
        )),
        ("stochastic", xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            enable_categorical=True,
            random_state=7,
            n_jobs=-1,
            subsample=0.8,
            colsample_bytree=0.4,
        )),
    ],
    voting="soft",
    weights=[1, 1],
    n_jobs=1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
