import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
cat_dtypes = {col: pd.CategoricalDtype(levels) for col, levels in cat_levels.items()}

schedule_groups = {"Origin": ["Origin"], "CarrierOrigin": ["UniqueCarrier", "Origin"],
                   "Route": ["Origin", "Dest"]}
schedule_train = train.assign(DepMinutes=(train["CRSDepTime"] // 100 * 60 + train["CRSDepTime"] % 100))
schedule_medians = {
    name: schedule_train.groupby(cols)["DepMinutes"].median().to_dict()
    for name, cols in schedule_groups.items()
}

def prepare(df):
    values = {col: df[col].to_numpy() for col in num_cols}
    values.update({col: pd.Categorical.from_codes(
        cat_dtypes[col].categories.get_indexer(df[col]), dtype=cat_dtypes[col]
    ) for col in cat_cols})
    month = np.array([int(v[2:]) for v in df["Month"].to_numpy()])
    day = np.array([int(v[2:]) for v in df["DayofMonth"].to_numpy()])
    deptime = df["CRSDepTime"].to_numpy()
    values["DayOfMonthNum"] = day
    values["DayOfYear"] = np.take([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], month - 1) + day
    values["DepHour"] = deptime // 100
    minutes = deptime // 100 * 60 + deptime % 100
    for name, cols in schedule_groups.items():
        keys = df[cols[0]].to_numpy() if len(cols) == 1 else zip(*(df[col].to_numpy() for col in cols))
        median = np.array([schedule_medians[name].get(key, np.nan) for key in keys])
        values[f"{name}DepOffset"] = minutes - median
    X = pd.DataFrame(values, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model_params = dict(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.08,
    min_child_weight=20,
    reg_lambda=10,
    subsample=0.9,
    colsample_bynode=0.8,
    num_parallel_tree=4,
    interaction_constraints=[
        [col for col in X_train.columns if col not in ("DayOfMonthNum", "DayOfYear")],
        ["DayOfMonthNum", "DayOfYear"],
    ],
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


class AveragedXGBoost:
    def __init__(self, models):
        self.models = models

    def predict_proba(self, X):
        return np.mean([member.predict_proba(X) for member in self.models], axis=0)


t0 = time.time()
members = []
for seed in (42, 137, 2026):
    member = xgb.XGBClassifier(**{**model_params, "random_state": seed})
    member.fit(X_train, y_train)
    members.append(member)
for depth, rounds, seed in ((3, 400, 31415), (5, 100, 2718)):
    member = xgb.XGBClassifier(**{**model_params, "max_depth": depth,
                                 "n_estimators": rounds, "random_state": seed})
    member.fit(X_train, y_train)
    members.append(member)
model = AveragedXGBoost(members)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
