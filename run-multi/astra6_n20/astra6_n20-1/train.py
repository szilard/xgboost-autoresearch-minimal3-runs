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


cat_codes = {col: {value: code for code, value in enumerate(sorted(train[col].unique()))}
             for col in cat_cols}
schedule_groups = {"Origin": ["Origin"],
                   "CarrierOrigin": ["UniqueCarrier", "Origin"]}
train_minutes = train["CRSDepTime"] // 100 * 60 + train["CRSDepTime"] % 100
schedule_medians = {
    name: train_minutes.groupby([train[col] for col in cols]).median().to_dict()
    for name, cols in schedule_groups.items()
}

def prepare(df):
    values = {col: df[col].to_numpy() for col in num_cols}
    values.update({col: [cat_codes[col].get(value, np.nan) for value in df[col].to_numpy()]
                   for col in cat_cols})
    minutes = df["CRSDepTime"].to_numpy() // 100 * 60 + df["CRSDepTime"].to_numpy() % 100
    for name, cols in schedule_groups.items():
        keys = (df[cols[0]].to_numpy() if len(cols) == 1
                else zip(*(df[col].to_numpy() for col in cols)))
        typical = np.array([schedule_medians[name].get(key, np.nan) for key in keys])
        values[name + "TimeOffset"] = minutes - typical
    month = np.array([int(value[2:]) for value in df["Month"].to_numpy()])
    day = np.array([int(value[2:]) for value in df["DayofMonth"].to_numpy()])
    weekday = np.array([int(value[2:]) for value in df["DayOfWeek"].to_numpy()])
    first_weekday = (weekday - day) % 7 + 1
    thanksgiving_offset = day - (22 + (4 - first_weekday) % 7)
    values["ThanksgivingOffset"] = np.where(
        (month == 11) & (np.abs(thanksgiving_offset) <= 5), thanksgiving_offset, np.nan)
    winter_offset = np.where(month == 12, day - 25, np.where(month == 1, day + 6, 99))
    values["WinterHolidayOffset"] = np.where(
        (winter_offset >= -7) & (winter_offset <= 10), winter_offset, np.nan)
    values["July4Offset"] = np.where((month == 7) & (day <= 7), day - 4, np.nan)
    first_monday = 1 + (1 - first_weekday) % 7
    memorial_offset = day - (first_monday + 7 * ((31 - first_monday) // 7))
    labor_offset = day - first_monday
    values["MemorialOffset"] = np.where(
        (month == 5) & (np.abs(memorial_offset) <= 4), memorial_offset, np.nan)
    values["LaborOffset"] = np.where(
        (month == 9) & (np.abs(labor_offset) <= 4), labor_offset, np.nan)
    winter_monday_offset = day - (first_monday + 14)
    values["WinterMondayOffset"] = np.where(
        ((month == 1) | (month == 2)) & (np.abs(winter_monday_offset) <= 4),
        winter_monday_offset, np.nan)
    X = pd.DataFrame(values, index=df.index, dtype=np.float32)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


params = dict(
    n_estimators=400,
    max_depth=0,
    max_leaves=16,
    grow_policy="lossguide",
    learning_rate=0.025,
    min_child_weight=40,
    reg_lambda=10,
    subsample=0.85,
    max_cat_threshold=32,
    enable_categorical=True,
    feature_types=["q"] * len(num_cols) + ["c"] * len(cat_cols) + ["q"] * (len(schedule_groups) + 6),
    random_state=42,
    n_jobs=-1,
)


class SeedEnsemble:
    def __init__(self, members):
        self.members = members

    def predict_proba(self, X):
        return np.mean([member.predict_proba(X) for member in self.members], axis=0)


t0 = time.time()
members = []
for seed in [42, 137, 2026]:
    member = xgb.XGBClassifier(**{**params, "random_state": seed})
    member.fit(X_train, y_train)
    members.append(member)
model = SeedEnsemble(members)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
