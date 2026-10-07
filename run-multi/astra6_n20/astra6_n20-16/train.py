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

cat_dtypes = {col: pd.CategoricalDtype(categories=cat_levels[col]) for col in cat_cols}


month_numbers = {value: int(value[2:]) for value in train["Month"].unique()}
day_numbers = {value: int(value[2:]) for value in train["DayofMonth"].unique()}
weekday_numbers = {value: int(value[2:]) for value in train["DayOfWeek"].unique()}


route_median_departure = (
    (train["CRSDepTime"] // 100) * 60 + train["CRSDepTime"] % 100
).groupby([train["Origin"], train["Dest"]]).median().to_dict()


carrier_origin_median_departure = (
    (train["CRSDepTime"] // 100) * 60 + train["CRSDepTime"] % 100
).groupby([train["UniqueCarrier"], train["Origin"]]).median().to_dict()


def prepare(df):
    values = {col: df[col].to_numpy() for col in num_cols}
    for col in cat_cols:
        dtype = cat_dtypes[col]
        values[col] = pd.Categorical.from_codes(dtype.categories.get_indexer(df[col]), dtype=dtype)
    month = np.fromiter((month_numbers[v] for v in df["Month"].to_numpy()), dtype=float)
    values["MonthNumber"] = month
    values["MonthSin"] = np.sin(2 * np.pi * month / 12)
    values["MonthCos"] = np.cos(2 * np.pi * month / 12)
    departure = df["CRSDepTime"].to_numpy()
    values["DepartureHour"] = departure // 100
    keys = zip(df["Origin"].to_numpy(), df["Dest"].to_numpy())
    route_median = np.fromiter((route_median_departure.get(key, np.nan) for key in keys), dtype=float)
    values["DepartureVsRouteMedian"] = (departure // 100) * 60 + departure % 100 - route_median
    carrier_keys = zip(df["UniqueCarrier"].to_numpy(), df["Origin"].to_numpy())
    carrier_median = np.fromiter((carrier_origin_median_departure.get(key, np.nan) for key in carrier_keys), dtype=float)
    values["DepartureVsCarrierOriginMedian"] = (departure // 100) * 60 + departure % 100 - carrier_median
    day = np.fromiter((day_numbers[v] for v in df["DayofMonth"].to_numpy()), dtype=np.int64)
    weekday = np.fromiter((weekday_numbers[v] for v in df["DayOfWeek"].to_numpy()), dtype=np.int64)
    month_starts = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    doy = month_starts[month.astype(int) - 1] + day
    november_first_weekday = (weekday - 1 - (doy - 305)) % 7
    thanksgiving = 326 + (3 - november_first_weekday) % 7
    new_year_distance = np.minimum(doy - 1, 366 - doy)
    holiday_distance = np.minimum.reduce([
        new_year_distance, np.abs(doy - 185), np.abs(doy - 359), np.abs(doy - thanksgiving),
    ])
    values["HolidayDistance"] = np.minimum(holiday_distance, 21)
    X = pd.DataFrame(values, index=df.index)
    y = (df[target].to_numpy() == "Y").astype("int32")
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=180,
    rate_drop=0.05,
    skip_drop=0.5,
    normalize_type="forest",
    max_depth=4,
    learning_rate=0.1,
    min_child_weight=20,
    reg_lambda=300,
    tree_method="hist",
    max_bin=64,
    subsample=0.75,
    colsample_bynode=0.8,
    enable_categorical=True,
    max_cat_threshold=16,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
recency_weights = np.exp2((X_train["MonthNumber"].to_numpy() - 12) / 12)
recency_weights /= recency_weights.mean()
members = []
for seed in (42, 137):
    member = xgb.XGBClassifier(**{**model.get_params(), "random_state": seed})
    member.fit(X_train, y_train, sample_weight=recency_weights)
    members.append(member)


class AveragedClassifier:
    def __init__(self, members):
        self.members = members

    def predict_proba(self, X):
        return np.mean([member.predict_proba(X) for member in self.members], axis=0, dtype=np.float64)


model = AveragedClassifier(members)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
