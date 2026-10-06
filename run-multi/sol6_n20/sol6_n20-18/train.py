import pandas as pd
import time
import xgboost as xgb
from sklearn.ensemble import VotingClassifier
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
train_dep_minutes = (train["CRSDepTime"] // 100) * 60 + train["CRSDepTime"] % 100
origin_median_departure = train_dep_minutes.groupby(train["Origin"]).median()
month_start = {1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151,
               7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(X[col], categories=cat_levels[col])
    X["DayofMonth"] = df["DayofMonth"].str[2:].astype(int)
    X["DayOfYear"] = df["Month"].str[2:].astype(int).map(month_start) + X["DayofMonth"]
    dep_minutes = (df["CRSDepTime"] // 100) * 60 + df["CRSDepTime"] % 100
    X["DepVsOriginMedian"] = dep_minutes - df["Origin"].map(origin_median_departure)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


params = dict(n_estimators=300, max_depth=3, learning_rate=0.05,
              enable_categorical=True, max_bin=512, gamma=1,
              random_state=42, n_jobs=-1)
model = VotingClassifier(
    estimators=[
        ("depth3", xgb.XGBClassifier(**params)),
        ("depth4", xgb.XGBClassifier(**{**params, "max_depth": 4})),
    ],
    voting="soft",
    weights=[2, 1],
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
