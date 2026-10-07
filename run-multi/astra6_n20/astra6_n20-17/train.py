import pandas as pd
import numpy as np
import time
import xgboost as xgb
from scipy.sparse.csgraph import shortest_path
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
cat_codes = {
    col: {value: i for i, value in enumerate(levels)}
    for col, levels in cat_levels.items()
}
airports = sorted(set(train["Origin"]) | set(train["Dest"]))
airport_index = {airport: i for i, airport in enumerate(airports)}
airport_distances = np.full((len(airports), len(airports)), np.inf)
np.fill_diagonal(airport_distances, 0)
for (origin, dest), distance in train.groupby(["Origin", "Dest"])["Distance"].median().items():
    i, j = airport_index[origin], airport_index[dest]
    airport_distances[i, j] = airport_distances[j, i] = min(airport_distances[i, j], distance)
airport_distances = shortest_path(airport_distances, directed=False)
assert np.isfinite(airport_distances).all(), "Training airport graph must be connected"
squared = airport_distances ** 2
kernel = -0.5 * (squared - squared.mean(axis=0) - squared.mean(axis=1)[:, None] + squared.mean())
eigenvalues, eigenvectors = np.linalg.eigh(kernel)
coordinates = eigenvectors[:, -3:] * np.sqrt(np.maximum(eigenvalues[-3:], 0))
airport_coordinates = {airport: coordinates[i] for i, airport in enumerate(airports)}
train_labels = (train[target] == "Y").astype(float)
carrier_stats = train_labels.groupby(train["UniqueCarrier"]).agg(["sum", "count"])
risk_lookups = {}
for airport_col in ["Origin", "Dest"]:
    airport_stats = train_labels.groupby(train[airport_col]).agg(["sum", "count"])
    pair_stats = train_labels.groupby([train[airport_col], train["UniqueCarrier"]]).agg(["sum", "count"])
    airport_risk = {}
    carrier_risk = {}
    for (airport, carrier), pair in pair_stats.iterrows():
        airport_total = airport_stats.loc[airport]
        airport_risk[(airport, carrier)] = (
            airport_total["sum"] - pair["sum"] + 100
        ) / (airport_total["count"] - pair["count"] + 200)
        if airport_col == "Origin":
            carrier_total = carrier_stats.loc[carrier]
            carrier_risk[(carrier, airport)] = (
                carrier_total["sum"] - pair["sum"] + 100
            ) / (carrier_total["count"] - pair["count"] + 200)
    airport_default = ((airport_stats["sum"] + 100) / (airport_stats["count"] + 200)).to_dict()
    risk_lookups[airport_col + "PeerRisk"] = (airport_col, "UniqueCarrier", airport_risk, airport_default)
    if airport_col == "Origin":
        carrier_default = ((carrier_stats["sum"] + 100) / (carrier_stats["count"] + 200)).to_dict()
        risk_lookups["CarrierElsewhereRisk"] = ("UniqueCarrier", "Origin", carrier_risk, carrier_default)

def prepare(df):
    columns = {col: df[col].to_numpy() for col in num_cols}
    columns.update({
        col: np.fromiter((cat_codes[col].get(v, np.nan) for v in df[col]), dtype=np.float32)
        for col in cat_cols
    })
    for name in ["Origin", "Dest"]:
        coordinates = np.asarray([airport_coordinates.get(v, (np.nan, np.nan, np.nan)) for v in df[name]])
        for dimension in range(3):
            columns[name + "Geo" + str(dimension)] = coordinates[:, dimension]
    for name, (left, right, lookup, defaults) in risk_lookups.items():
        columns[name] = np.fromiter(
            (lookup.get((a, b), defaults.get(a, 0.5)) for a, b in zip(df[left], df[right])),
            dtype=np.float32,
        )
    departure = df["CRSDepTime"].to_numpy()
    month = np.fromiter((int(v[2:]) for v in df["Month"]), dtype=np.int16)
    day = np.fromiter((int(v[2:]) for v in df["DayofMonth"]), dtype=np.int16)
    columns["DepHour"] = departure // 100
    columns["DepMinute"] = departure % 100
    columns["MonthNum"] = month
    columns["MonthSin"] = np.sin(2 * np.pi * (month - 1) / 12)
    columns["MonthCos"] = np.cos(2 * np.pi * (month - 1) / 12)
    columns["DayNum"] = day
    columns["DayOfYear"] = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])[month - 1] + day
    X = pd.DataFrame(columns, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)
date_features = ["DayNum", "DayOfYear"]


class MeanProbabilityModel:
    def __init__(self, models):
        self.models = models

    def predict_proba(self, X):
        return np.mean([model.predict_proba(X) for model in self.models], axis=0)


model = xgb.XGBClassifier(
    n_estimators=500,
    max_depth=4,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=200,
    gamma=5,
    subsample=0.8,
    num_parallel_tree=4,
    colsample_bynode=0.8,
    interaction_constraints=[date_features, [col for col in X_train.columns if col not in date_features]],
    enable_categorical=True,
    max_cat_threshold=16,
    feature_types=["c" if col in cat_cols else "q" for col in X_train.columns],
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
models = [model]
for seed in [137]:
    member = xgb.XGBClassifier(**{**model.get_params(), "random_state": seed})
    member.fit(X_train, y_train)
    models.append(member)
model = MeanProbabilityModel(models)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
