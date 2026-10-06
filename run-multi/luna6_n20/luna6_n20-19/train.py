import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from sklearn.ensemble import VotingClassifier
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    dep_minutes = (df["CRSDepTime"] // 100) * 60 + (df["CRSDepTime"] % 100)
    X["DepTimeSin"] = np.sin(2 * np.pi * dep_minutes / 1440)
    X["DepTimeCos"] = np.cos(2 * np.pi * dep_minutes / 1440)
    X["DepTimeSin2"] = np.sin(4 * np.pi * dep_minutes / 1440)
    X["DepTimeCos2"] = np.cos(4 * np.pi * dep_minutes / 1440)
    month_starts = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    month_number = df["Month"].str[2:].astype(int).to_numpy()
    day_of_year = month_starts[month_number - 1] + df["DayofMonth"].str[2:].astype(int).to_numpy()
    X["YearSin"] = np.sin(2 * np.pi * day_of_year / 365)
    X["YearCos"] = np.cos(2 * np.pi * day_of_year / 365)
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
        (f"depth{depth}", xgb.XGBClassifier(
            n_estimators=800,
            max_depth=depth,
            min_child_weight=25,
            learning_rate=0.0125,
            enable_categorical=True,
            random_state=42,
            n_jobs=-1,
        ))
        for depth in (3, 4)
    ],
    voting="soft",
    n_jobs=1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
