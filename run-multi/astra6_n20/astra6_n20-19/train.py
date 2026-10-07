import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from sklearn.base import clone
from sklearn.ensemble import VotingClassifier
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
cat_dtypes = {col: pd.CategoricalDtype(cat_levels[col]) for col in cat_cols}
schedule_pairs = {
    "Route": ("Origin", "Dest"),
    "CarrierOrigin": ("UniqueCarrier", "Origin"),
}
training_minutes = train["CRSDepTime"] // 100 * 60 + train["CRSDepTime"] % 100
schedule_medians = {
    name: training_minutes.groupby(train[left] + "|" + train[right]).median().to_dict()
    for name, (left, right) in schedule_pairs.items()
}

def prepare(df):
    values = {col: df[col].to_numpy() for col in num_cols}
    departure = values["CRSDepTime"]
    hour, minute = departure // 100, departure % 100
    angle = 2 * np.pi * (60 * hour + minute) / 1440
    values["DepSin"] = np.sin(angle)
    values["DepCos"] = np.cos(angle)
    month = np.array([int(value[2:]) for value in df["Month"]])
    day = np.array([int(value[2:]) for value in df["DayofMonth"]])
    weekday = np.array([int(value[2:]) - 1 for value in df["DayOfWeek"]])
    month_offsets = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    day_of_year = month_offsets[month - 1] + day
    jan1_weekday = (weekday - day_of_year + 1) % 7
    memorial = 151 - (jan1_weekday + 150) % 7
    labor = 244 + (-(jan1_weekday + 243)) % 7
    thanksgiving = 326 + (3 - (jan1_weekday + 304) % 7) % 7
    holidays = np.column_stack([
        np.full(len(df), 1), memorial, np.full(len(df), 185),
        labor, thanksgiving, np.full(len(df), 359),
    ])
    relative = (day_of_year[:, None] - holidays + 182) % 365 - 182
    nearest_index = np.abs(relative).argmin(axis=1)
    nearest = relative[np.arange(len(df)), nearest_index]
    values["HolidayType"] = pd.Categorical(
        np.where(np.abs(nearest) <= 7, nearest_index + 1, 0), categories=range(7),
    )
    values["DaysBeforeHoliday"] = np.where((nearest <= 0) & (nearest >= -7), -nearest, 8)
    values["DaysAfterHoliday"] = np.where((nearest >= 0) & (nearest <= 7), nearest, 8)
    for name, (left, right) in schedule_pairs.items():
        keys = df[left].to_numpy() + "|" + df[right].to_numpy()
        medians = np.array([schedule_medians[name].get(key, np.nan) for key in keys])
        values[f"{name}DepartureOffset"] = 60 * hour + minute - medians
    for col in cat_cols:
        dtype = cat_dtypes[col]
        values[col] = pd.Categorical.from_codes(
            dtype.categories.get_indexer(df[col]), dtype=dtype,
        )
    X = pd.DataFrame(values, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


base_model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    min_child_weight=300,
    reg_lambda=50,
    subsample=0.9,
    max_cat_threshold=32,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
model = VotingClassifier(
    [(f"seed_{seed}", clone(base_model).set_params(random_state=seed))
     for seed in (42, 43, 44)],
    voting="soft",
)


t0 = time.time()
training_month = np.array([int(value[2:]) for value in train["Month"]])
sample_weight = np.exp2((training_month - 12) / 6)
month_rate = pd.Series(y_train).groupby(training_month).transform("mean").to_numpy()
sample_weight *= np.where(y_train == 1, 0.5 / month_rate, 0.5 / (1 - month_rate))
sample_weight /= sample_weight.mean()
model.fit(X_train, y_train, sample_weight=sample_weight)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
