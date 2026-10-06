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
cat_dtypes = {col: pd.CategoricalDtype(levels) for col, levels in cat_levels.items()}

cat_codes = {col: {value: i for i, value in enumerate(levels)}
             for col, levels in cat_levels.items()}

# Fit schedule lookups on train; prepare only applies them to each row.
training_minutes = train["CRSDepTime"] // 100 * 60 + train["CRSDepTime"] % 100
schedule_pairs = {
    "CarrierOrigin": ("UniqueCarrier", "Origin"),
}
schedule_medians = {
    name: training_minutes.groupby(train[a] + "|" + train[b]).median().to_dict()
    for name, (a, b) in schedule_pairs.items()
}

def prepare(df):
    columns = {col: df[col].to_numpy() for col in num_cols}
    columns.update({
        col: pd.Categorical.from_codes(
            [cat_codes[col].get(value, -1) for value in df[col].to_numpy()],
            dtype=cat_dtypes[col],
        )
        for col in cat_cols
    })
    departure = df["CRSDepTime"].to_numpy()
    minutes = departure // 100 * 60 + departure % 100
    for name, (a, b) in schedule_pairs.items():
        keys = df[a].to_numpy() + "|" + df[b].to_numpy()
        medians = np.array([schedule_medians[name].get(key, np.nan) for key in keys])
        columns[f"DepartureVs{name}Median"] = minutes - medians
    def calendar_flags(month, day, weekday):
        month = int(month[2:])
        day = int(day[2:])
        weekday = int(weekday[2:])
        delta = 90
        if month == 11:
            first_weekday = (weekday - day) % 7
            delta = day - (22 + (3 - first_weekday) % 7)
        elif month == 12:
            delta = day - (32 if day >= 29 else 25)
        elif month == 1:
            delta = day - 1
        elif month == 7:
            delta = day - 4
        return 6 <= month <= 8, delta == 0, -3 <= delta < 0, 0 < delta <= 3

    flags = np.asarray([
        calendar_flags(month, day, weekday)
        for month, day, weekday in zip(
            df["Month"].to_numpy(), df["DayofMonth"].to_numpy(),
            df["DayOfWeek"].to_numpy(),
        )
    ], dtype="int8").reshape(-1, 4)
    for i, name in enumerate(("Summer", "Holiday", "PreHoliday", "PostHoliday")):
        columns[name] = flags[:, i]
    X = pd.DataFrame(columns, index=df.index)
    y = (df[target].to_numpy() == "Y").astype("int8")
    return X, y

X_train, y_train = prepare(train)


class DepthEnsemble:
    def __init__(self, estimators):
        self.estimators = estimators

    def fit(self, X, y, sample_weight):
        for estimator in self.estimators:
            estimator.fit(X, 0.9 * y + 0.05, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        predictions = [estimator.predict(X) for estimator in self.estimators]
        p = (predictions[0] + 2 * predictions[1] + predictions[2]) / 4
        return np.column_stack((1 - p, p))


model = DepthEnsemble([
    xgb.XGBRegressor(
        objective="reg:logistic",
        n_estimators=rounds,
        max_depth=0,
        max_leaves=2 ** depth,
        grow_policy="lossguide",
        tree_method="hist",
        learning_rate=0.05,
        min_child_weight=20,
        reg_lambda=10,
        reg_alpha=10,
        enable_categorical=True,
        random_state=42,
        n_jobs=-1,
    )
    for depth, rounds in ((2, 500), (3, 300), (4, 200))
])


t0 = time.time()
month_rates = train[target].eq("Y").groupby(train["Month"]).mean()
row_rates = train["Month"].map(month_rates).to_numpy()
sample_weight = np.where(y_train == 1, 0.5 / row_rates, 0.5 / (1 - row_rates))
months = train["Month"].str[2:].astype(int).to_numpy()
sample_weight *= np.exp2((months - 12) / 6)
sample_weight /= sample_weight.mean()
model.fit(X_train, y_train, sample_weight=sample_weight)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
