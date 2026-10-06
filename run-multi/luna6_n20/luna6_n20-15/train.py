import numpy as np
import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    month = df["Month"].str[2:].astype(int)
    day_of_week = df["DayOfWeek"].str[2:].astype(int)
    X["MonthSin"] = np.sin(2.0 * np.pi * (month - 1) / 12.0)
    X["MonthCos"] = np.cos(2.0 * np.pi * (month - 1) / 12.0)
    X["DayOfWeekSin"] = np.sin(2.0 * np.pi * (day_of_week - 1) / 7.0)
    X["DayOfWeekCos"] = np.cos(2.0 * np.pi * (day_of_week - 1) / 7.0)
    dep_minutes = (df["CRSDepTime"] // 100) * 60 + df["CRSDepTime"] % 100
    X["DepTimeSin"] = np.sin(2.0 * np.pi * dep_minutes / 1440.0)
    X["DepTimeCos"] = np.cos(2.0 * np.pi * dep_minutes / 1440.0)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=4,
    gamma=2.0,
    reg_lambda=2.0,
    reg_alpha=0.1,
    learning_rate=0.1,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
