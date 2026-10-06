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


cat_levels = {col: pd.Index(sorted(train[col].unique())) for col in cat_cols}
carrier_aliases = {"HP": "US"}
cat_levels["UniqueCarrier"] = pd.Index(sorted({
    carrier_aliases.get(value, value) for value in train["UniqueCarrier"].unique()
}))
train_minutes = train["CRSDepTime"] // 100 * 60 + train["CRSDepTime"] % 100
schedule_groups = {
    "Origin": train["Origin"],
    "Route": train["Origin"] + ":" + train["Dest"],
    "CarrierOrigin": train["UniqueCarrier"].replace(carrier_aliases) + ":" + train["Origin"],
}
schedule_medians = {name: train_minutes.groupby(keys).median().to_dict()
                    for name, keys in schedule_groups.items()}

def prepare(df):
    values = {col: df[col].to_numpy() for col in num_cols}
    for col in cat_cols:
        raw = df[col]
        if col == "UniqueCarrier":
            raw = [carrier_aliases.get(value, value) for value in raw]
        values[col] = pd.Categorical.from_codes(
            cat_levels[col].get_indexer(raw), categories=cat_levels[col])
    departure = df["CRSDepTime"].to_numpy()
    minutes = departure // 100 * 60 + departure % 100
    origin = df["Origin"].to_numpy()
    carrier = np.array([carrier_aliases.get(v, v) for v in df["UniqueCarrier"]])
    schedule_keys = {"Origin": origin,
                     "Route": origin + ":" + df["Dest"].to_numpy(),
                     "CarrierOrigin": carrier + ":" + origin}
    for name, keys in schedule_keys.items():
        lookup = schedule_medians[name]
        typical = np.array([lookup.get(key, np.nan) for key in keys])
        values[f"DepVs{name}Median"] = minutes - typical
    values["DepHour"] = departure // 100
    values["DepMinute"] = departure % 100
    values["TimeSin"] = np.sin(2 * np.pi * minutes / 1440)
    values["TimeCos"] = np.cos(2 * np.pi * minutes / 1440)
    arrival = (minutes + 30 + df["Distance"].to_numpy() / 8) % 1440
    values["ApproxArrivalHour"] = arrival / 60
    values["ApproxArrivalSin"] = np.sin(2 * np.pi * arrival / 1440)
    values["ApproxArrivalCos"] = np.cos(2 * np.pi * arrival / 1440)
    month = np.array([int(v[2:]) for v in df["Month"]])
    day = np.array([int(v[2:]) for v in df["DayofMonth"]])
    weekday = np.array([int(v[2:]) - 1 for v in df["DayOfWeek"]])
    starts = np.array([0, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    day_of_year = starts[month] + day
    jan1_weekday = (weekday - day_of_year + 1) % 7
    memorial = 151 - (jan1_weekday + 150) % 7
    labor = 244 + (-(jan1_weekday + 243)) % 7
    thanksgiving = 326 + (3 - (jan1_weekday + 304)) % 7
    mlk = 15 + (-jan1_weekday - 14) % 7
    presidents = 46 + (-jan1_weekday - 45) % 7
    holiday_days = np.column_stack([
        np.ones_like(day), memorial, np.full_like(day, 185),
        labor, thanksgiving, np.full_like(day, 359), mlk, presidents])
    offsets = (day_of_year[:, None] - holiday_days + 182) % 365 - 182
    nearest = np.argmin(np.abs(offsets), axis=1)
    offset = np.take_along_axis(offsets, nearest[:, None], axis=1).ravel()
    lower = np.array([-7, -7, -7, -5, -6, -11, -7, -4])
    upper = np.array([3, 2, 7, 2, 5, 7, 7, 1])
    nearby = (offset >= lower[nearest]) & (offset <= upper[nearest])
    values["HolidayOffset"] = np.where(nearby, offset, np.nan)
    values["HolidayType"] = pd.Categorical(np.where(nearby, nearest + 1, 0),
                                            categories=range(9))
    X = pd.DataFrame(values, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)
month_rates = pd.Series(y_train, index=train.index).groupby(train["Month"]).mean()
row_rate = train["Month"].map(month_rates).to_numpy()
training_weights = np.where(y_train == 1, 0.5 / row_rate,
                             0.5 / (1 - row_rate)).astype(np.float32)


model = xgb.XGBClassifier(
    objective="binary:logistic",
    n_estimators=500,
    max_depth=3,
    learning_rate=0.05,
    min_child_weight=100,
    reg_lambda=50,
    subsample=0.8,
    colsample_bytree=0.8,
    num_parallel_tree=2,
    max_bin=64,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train, sample_weight=training_weights)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
