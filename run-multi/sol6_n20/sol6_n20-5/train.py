import pandas as pd
import time
import math
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
month_start = {
    f"c-{m}": sum([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][:m - 1])
    for m in range(1, 13)
}
day_number = {f"c-{d}": d for d in range(1, 32)}
year_sin = {d: math.sin(2 * math.pi * d / 365) for d in range(1, 366)}
year_cos = {d: math.cos(2 * math.pi * d / 365) for d in range(1, 366)}
holidays = [1, 185, 327, 328, 359]
holiday_distance = {
    d: min(min(abs(d - h), 365 - abs(d - h)) for h in holidays)
    for d in range(1, 366)
}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DepHour"] = df["CRSDepTime"] // 100
    X["DayOfYear"] = df["Month"].map(month_start) + df["DayofMonth"].map(day_number)
    X["HolidayDistance"] = X["DayOfYear"].map(holiday_distance)
    X["YearSin"] = X["DayOfYear"].map(year_sin)
    X["YearCos"] = X["DayOfYear"].map(year_cos)
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
        (f"seed{seed}", xgb.XGBClassifier(
            n_estimators=275,
            max_depth=6,
            min_child_weight=10,
            learning_rate=0.025,
            subsample=0.8,
            colsample_bynode=0.4,
            max_bin=32,
            enable_categorical=True,
            random_state=seed,
            n_jobs=-1,
        ))
        for seed in (42, 43, 44, 45, 46)
    ],
    voting="soft",
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
