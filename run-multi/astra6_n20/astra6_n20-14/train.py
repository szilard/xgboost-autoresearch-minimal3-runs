import pandas as pd
import numpy as np
from sklearn.ensemble import VotingClassifier
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_maps = {
    col: {value: i for i, value in enumerate(sorted(train[col].unique()))}
    for col in cat_cols
}


station_median = (
    train.assign(minutes=(train["CRSDepTime"] // 100) * 60 + train["CRSDepTime"] % 100)
    .groupby(["UniqueCarrier", "Origin"])["minutes"].median().to_dict()
)

carrier_distance = train.groupby("UniqueCarrier")["Distance"].median().to_dict()

def prepare(df):
    values = {col: df[col].to_numpy() for col in num_cols}
    month = np.array([int(value[2:]) for value in df["Month"].to_numpy()])
    day = np.array([int(value[2:]) for value in df["DayofMonth"].to_numpy()])
    weekday = np.array([int(value[2:]) for value in df["DayOfWeek"].to_numpy()])
    month_start = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    day_of_year = month_start[month - 1] + day
    for name, holiday in (("Christmas", 359), ("July4", 185)):
        offset = (day_of_year - holiday + 182) % 365 - 182
        values[f"{name}Offset"] = np.where(np.abs(offset) <= 10, offset, np.nan)
    november_weekday = (weekday - day_of_year + 304) % 7
    thanksgiving = 326 + (3 - november_weekday) % 7
    offset = day_of_year - thanksgiving
    values["ThanksgivingOffset"] = np.where(np.abs(offset) <= 7, offset, np.nan)
    values["MonthSin"] = np.sin(2 * np.pi * month / 12)
    values["MonthCos"] = np.cos(2 * np.pi * month / 12)
    for col in cat_cols:
        lookup = cat_maps[col]
        values[col] = [lookup.get(value, np.nan) for value in df[col].to_numpy()]
    departure = df["CRSDepTime"].to_numpy()
    values["NightPhase"] = np.where(departure < 500, departure - 500, np.maximum(departure - 2100, 0))
    station_reference = np.array([
        station_median.get(pair, np.nan)
        for pair in zip(df["UniqueCarrier"].to_numpy(), df["Origin"].to_numpy())
    ])
    values["StationTimeOffset"] = (departure // 100) * 60 + departure % 100 - station_reference
    values["CarrierDistanceOffset"] = df["Distance"].to_numpy() - np.array([
        carrier_distance.get(carrier, np.nan) for carrier in df["UniqueCarrier"].to_numpy()
    ])
    X = pd.DataFrame(values, index=df.index, dtype=np.float32)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


params = dict(
    n_estimators=600,
    max_depth=3,
    learning_rate=0.05,
    min_child_weight=30,
    reg_lambda=100,
    reg_alpha=10,
    subsample=0.5,
    tree_method="hist",
    max_bin=1024,
    colsample_bynode=0.8,
    enable_categorical=True,
    feature_types=["c" if col in cat_cols else "q" for col in X_train.columns],
    n_jobs=-1,
)

model = VotingClassifier(
    estimators=[(str(seed), xgb.XGBClassifier(**params, random_state=seed))
                for seed in (42, 137, 271, 509, 733)] + [
        (f"depth{depth}", xgb.XGBClassifier(
            **(params | dict(max_depth=depth, n_estimators=rounds)), random_state=42
        )) for depth, rounds in ((2, 1200), (4, 300), (5, 150))
    ],
    weights=[1, 1, 1, 1, 1, 5/3, 5/3, 5/3],
    voting="soft",
    n_jobs=1,
)

t0 = time.time()
training_month = train["Month"].str[2:].astype(int).to_numpy()
fit_weight = np.exp2((training_month - 12) / 6)
fit_weight /= fit_weight.mean()
model.fit(X_train, y_train, sample_weight=fit_weight)


class MarginEnsemble:
    def __init__(self, ensemble):
        self.ensemble = ensemble

    def predict_proba(self, X):
        margins = np.stack([
            member.predict(X, output_margin=True)
            for member in self.ensemble.estimators_
        ])
        margin = np.average(margins, axis=0, weights=self.ensemble.weights)
        probability = 1 / (1 + np.exp(-margin))
        return np.column_stack([1 - probability, probability])


model = MarginEnsemble(model)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
