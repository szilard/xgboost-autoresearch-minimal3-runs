import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_number = {value: int(value.split("-")[1]) for value in train["Month"].unique()}
day_number = {value: int(value.split("-")[1]) for value in train["DayofMonth"].unique()}
weekday_number = {value: int(value.split("-")[1]) for value in train["DayOfWeek"].unique()}
month_start_day = {1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151,
                   7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    day_of_year = (
        df["Month"].map(month_number).map(month_start_day)
        + df["DayofMonth"].map(day_number) - 1
    ).to_numpy()
    X["DayOfYear"] = day_of_year
    weekday = df["DayOfWeek"].map(weekday_number).to_numpy()
    week_angle = 2 * np.pi * (weekday - 1) / 7
    X["WeekSin"] = np.sin(week_angle)
    X["WeekCos"] = np.cos(week_angle)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    colsample_bytree=0.8,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
