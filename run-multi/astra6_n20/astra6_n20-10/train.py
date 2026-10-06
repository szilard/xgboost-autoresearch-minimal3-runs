import pandas as pd
import numpy as np
from scipy.sparse.csgraph import shortest_path
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
interactions = {
    "Route": ("Origin", "Dest"),
    "CarrierOrigin": ("UniqueCarrier", "Origin"),
    "CarrierDest": ("UniqueCarrier", "Dest"),
}
for name, (left, right) in interactions.items():
    cat_dtypes[name] = pd.CategoricalDtype(sorted((train[left] + "-" + train[right]).unique()))
category_codes = {name: {value: code for code, value in enumerate(dtype.categories)}
                  for name, dtype in cat_dtypes.items()}

airports = pd.Index(sorted(set(train["Origin"]) | set(train["Dest"])))
route_distances = train.groupby(["Origin", "Dest"])["Distance"].median()
distance_graph = np.full((len(airports), len(airports)), np.inf)
distance_graph[airports.get_indexer(route_distances.index.get_level_values(0)),
               airports.get_indexer(route_distances.index.get_level_values(1))] = route_distances.to_numpy()
distance_graph = np.minimum(distance_graph, distance_graph.T)
np.fill_diagonal(distance_graph, 0.0)
geodesic = shortest_path(distance_graph, directed=False, method="FW")
assert np.isfinite(geodesic).all(), "Training airport graph must be connected"
squared = geodesic ** 2
kernel = -0.5 * (squared - squared.mean(axis=0)[None, :] - squared.mean(axis=1)[:, None] + squared.mean())
eigenvalues, eigenvectors = np.linalg.eigh(kernel)
coordinates = eigenvectors[:, -3:] * np.sqrt(np.maximum(eigenvalues[-3:], 0)) / 1000.0
geo_tables = {
    col: np.vstack([np.full((1, 3), np.nan), coordinates[airports.get_indexer(cat_dtypes[col].categories)]]).astype(np.float32)
    for col in ["Origin", "Dest"]
}
landmarks = ["ATL", "ORD", "DFW", "LAX", "JFK"]
landmark_distances = geodesic[:, airports.get_indexer(landmarks)] / 1000.0
landmark_tables = {
    col: np.vstack([np.full((1, len(landmarks)), np.nan),
                    landmark_distances[airports.get_indexer(cat_dtypes[col].categories)]]).astype(np.float32)
    for col in ["Origin", "Dest"]
}

def prepare(df):
    def categorical(name, values):
        return pd.Categorical.from_codes(
            [category_codes[name].get(value, -1) for value in values], dtype=cat_dtypes[name]
        )

    columns = {col: df[col].to_numpy() for col in num_cols}
    departure = df["CRSDepTime"].to_numpy()
    minutes = departure // 100 * 60 + departure % 100
    columns["OperationalMinute"] = (minutes - 240) % 1440
    columns["DepartureSin"] = np.sin(2 * np.pi * minutes / 1440)
    columns["DepartureCos"] = np.cos(2 * np.pi * minutes / 1440)
    arrival_proxy = (minutes + 30 + df["Distance"].to_numpy() / 8) % 1440
    columns["ArrivalClockProxy"] = arrival_proxy
    columns["ArrivalProxySin"] = np.sin(2 * np.pi * arrival_proxy / 1440)
    columns["ArrivalProxyCos"] = np.cos(2 * np.pi * arrival_proxy / 1440)
    month = np.fromiter((int(value[2:]) for value in df["Month"].to_numpy()), dtype=np.int32)
    day = np.fromiter((int(value[2:]) for value in df["DayofMonth"].to_numpy()), dtype=np.int32)
    weekday = np.fromiter((int(value[2:]) for value in df["DayOfWeek"].to_numpy()), dtype=np.int32)
    november_day = np.where(month == 12, day + 30, day)
    thanksgiving = 22 + (november_day - weekday - 18) % 7
    holiday_offsets = {
        "ThanksgivingOffset": np.where((month == 11) | (month == 12), november_day - thanksgiving, 999),
        "ChristmasOffset": np.where(month == 12, day - 25, np.where(month == 1, day + 6, 999)),
        "NewYearOffset": np.where(month == 1, day - 1, np.where(month == 12, day - 32, 999)),
        "July4Offset": np.where(month == 7, day - 4, np.where(month == 6, day - 34, 999)),
    }
    for name, offset in holiday_offsets.items():
        lead_days = 14 if name == "ChristmasOffset" else 7
        columns[name] = np.where((offset >= -lead_days) & (offset <= 7), offset, np.nan)
    for col in cat_cols:
        columns[col] = categorical(col, df[col].to_numpy())
    for name, (left, right) in interactions.items():
        values = df[left].to_numpy() + "-" + df[right].to_numpy()
        columns[name] = categorical(name, values)
    origin_geo = geo_tables["Origin"][columns["Origin"].codes + 1]
    dest_geo = geo_tables["Dest"][columns["Dest"].codes + 1]
    for axis in range(3):
        columns[f"OriginGeo{axis}"] = origin_geo[:, axis]
        columns[f"DestGeo{axis}"] = dest_geo[:, axis]
        columns[f"Direction{axis}"] = dest_geo[:, axis] - origin_geo[:, axis]
    for col in ["Origin", "Dest"]:
        distances = landmark_tables[col][columns[col].codes + 1]
        for index, airport in enumerate(landmarks):
            columns[f"{col}DistanceTo{airport}"] = distances[:, index]
    X = pd.DataFrame(columns, index=df.index)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=400,
    num_parallel_tree=3,
    max_depth=8,
    min_child_weight=30,
    reg_lambda=20,
    reg_alpha=5,
    subsample=0.8,
    colsample_bytree=0.85,
    learning_rate=0.05,
    enable_categorical=True,
    max_cat_to_onehot=20000,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
