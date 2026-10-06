import pandas as pd
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
month_categories = sorted(train["Month"].unique())
route_median_time = train.groupby(["Origin", "Dest"])["CRSDepTime"].median().to_dict()
carrier_origin_median_time = train.groupby(["UniqueCarrier", "Origin"])["CRSDepTime"].median().to_dict()
origin_weekday_median_time = train.groupby(["Origin", "DayOfWeek"])["CRSDepTime"].median().to_dict()
month_starts = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    month_number = df["Month"].str[2:].astype("int8")
    X["MonthCategory"] = pd.Categorical(df["Month"], categories=month_categories)
    X["DayofMonth"] = df["DayofMonth"].str[2:].astype("int8")
    X["DayOfYear"] = [month_starts[m - 1] + d for m, d in zip(month_number, X["DayofMonth"])]
    X["OffFiveMinuteMark"] = (df["CRSDepTime"] % 5 != 0).astype("int8")
    X["RouteTimeOffset"] = [
        t - route_median_time.get((o, d), float("nan"))
        for t, o, d in zip(df["CRSDepTime"], df["Origin"], df["Dest"])
    ]
    X["CarrierOriginTimeOffset"] = [
        t - carrier_origin_median_time.get((c, o), float("nan"))
        for t, c, o in zip(df["CRSDepTime"], df["UniqueCarrier"], df["Origin"])
    ]
    X["OriginWeekdayTimeOffset"] = [
        t - origin_weekday_median_time.get((origin, weekday), float("nan"))
        for t, origin, weekday in zip(df["CRSDepTime"], df["Origin"], df["DayOfWeek"])
    ]
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col],
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=150,
    max_depth=3,
    min_child_weight=30,
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
