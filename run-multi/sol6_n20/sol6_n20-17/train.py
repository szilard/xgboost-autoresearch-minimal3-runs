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
month_offsets = dict(zip((f"c-{m}" for m in range(1, 13)),
                         (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)))
train_routes = train["Origin"] + "-" + train["Dest"]
train_dep_minutes = (train["CRSDepTime"] // 100) * 60 + train["CRSDepTime"] % 100
route_median_deptime = train_dep_minutes.groupby(train_routes).median().to_dict()

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    dep_minute = (df["CRSDepTime"] // 100) * 60 + df["CRSDepTime"] % 100
    X["DepHour"] = df["CRSDepTime"] // 100
    X["DepVsRouteMedian"] = dep_minute - (
        df["Origin"] + "-" + df["Dest"]
    ).map(route_median_deptime)
    X["DayOfYear"] = df["Month"].map(month_offsets) + df["DayofMonth"].str[2:].astype(int)
    day = X["DayOfYear"].to_numpy()
    X["FixedHolidayDistance"] = np.minimum.reduce((
        np.abs(day - 1), np.abs(day - 185), np.abs(day - 359), np.abs(day - 366)
    ))
    weekday = df["DayOfWeek"].str[2:].astype(int).to_numpy()
    jan1_weekday = (weekday - day) % 7 + 1
    nov1_weekday = (jan1_weekday - 1 + 304) % 7 + 1
    thanksgiving = 304 + 22 + (4 - nov1_weekday) % 7
    X["ThanksgivingDistance"] = np.abs(day - thanksgiving)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model_params = dict(
    n_estimators=250,
    min_child_weight=10,
    learning_rate=0.05,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
model = VotingClassifier(
    estimators=[
        ("depth3", xgb.XGBClassifier(max_depth=3, **model_params)),
        ("depth4", xgb.XGBClassifier(max_depth=4, **model_params)),
    ],
    voting="soft",
    weights=[1, 1],
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
