import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
dep_hour_levels = sorted((train["CRSDepTime"] // 100).unique())
month_offsets = {1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151,
                 7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    day_of_year = (
        df["Month"].str.rsplit("-", n=1).str[-1].astype(int).map(month_offsets)
        + df["DayofMonth"].str.rsplit("-", n=1).str[-1].astype(int)
        - 1
    )
    year_angle = 2 * np.pi * day_of_year / 365
    X["DayOfYearSin"] = np.sin(year_angle)
    X["DayOfYearCos"] = np.cos(year_angle)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    dep_hour = df["CRSDepTime"] // 100
    X["CRSDepHour"] = pd.Categorical(
        dep_hour.where(dep_hour.isin(dep_hour_levels)),
        categories=dep_hour_levels,
    )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=3,
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
