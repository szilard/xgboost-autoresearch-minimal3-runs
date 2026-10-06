import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from scipy.sparse.csgraph import shortest_path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: pd.Index(sorted(train[col].unique())) for col in cat_cols}
airport_levels = pd.Index(sorted(set(train["Origin"]) | set(train["Dest"])))
routes = train.groupby(["Origin", "Dest"])["Distance"].median().reset_index()
route_graph = np.full((len(airport_levels), len(airport_levels)), np.inf)
route_graph[
    airport_levels.get_indexer(routes["Origin"]),
    airport_levels.get_indexer(routes["Dest"]),
] = routes["Distance"]
route_graph = np.minimum(route_graph, route_graph.T)
np.fill_diagonal(route_graph, 0)
geo_distances = shortest_path(route_graph, directed=False)
geo_squared = geo_distances ** 2
geo_kernel = -0.5 * (
    geo_squared - geo_squared.mean(axis=0)
    - geo_squared.mean(axis=1)[:, None] + geo_squared.mean()
)
geo_values, geo_vectors = np.linalg.eigh(geo_kernel)
airport_geometry = np.vstack([
    geo_vectors[:, -3:] * np.sqrt(geo_values[-3:]),
    np.full((1, 3), np.nan),
])
hash_cols = [col for col in train.columns if col != target]
train_folds = (
    pd.util.hash_pandas_object(train[hash_cols], index=False, categorize=False).to_numpy() % 5
).astype(int)
encoding_groups = {
    "OriginRisk": ("Origin",),
    "DestRisk": ("Dest",),
    "CarrierOriginRisk": ("UniqueCarrier", "Origin"),
    "CarrierDestRisk": ("UniqueCarrier", "Dest"),
    "RouteRisk": ("Origin", "Dest"),
}
encoding_levels = {}
encoding_tables = {}
train_target = train[target].eq("Y").astype(float)
for name, group in encoding_groups.items():
    keys = train[group[0]]
    if len(group) == 2:
        keys = keys + "_" + train[group[1]]
    levels = pd.Index(sorted(keys.unique()))
    table = np.full((len(levels) + 1, 5), 0.5, dtype=np.float32)
    for fold in range(5):
        mask = train_folds != fold
        stats = train_target[mask].groupby(keys[mask]).agg(["sum", "count"])
        table[levels.get_indexer(stats.index), fold] = (
            (stats["sum"] + 50) / (stats["count"] + 100)
        )
    encoding_levels[name] = levels
    encoding_tables[name] = table

def prepare(df):
    columns = {col: df[col].to_numpy() for col in num_cols}
    hhmm = df["CRSDepTime"].to_numpy()
    minutes = (hhmm // 100) * 60 + hhmm % 100
    columns["DepHour"] = hhmm // 100
    columns["DepMinute"] = hhmm % 100
    columns["DepSin"] = np.sin(2 * np.pi * minutes / 1440)
    columns["DepCos"] = np.cos(2 * np.pi * minutes / 1440)
    month = np.array([int(v[2:]) for v in df["Month"]])
    day = np.array([int(v[2:]) for v in df["DayofMonth"]])
    weekday = np.array([int(v[2:]) for v in df["DayOfWeek"]])
    month_start = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    day_of_year = month_start[month - 1] + day
    jan1_weekday = (weekday - day_of_year) % 7
    memorial = 151 - (jan1_weekday + 150) % 7
    labor = 244 + (-(jan1_weekday + 243)) % 7
    thanksgiving = 326 + (3 - jan1_weekday - 325) % 7
    offsets = np.column_stack([
        day_of_year - 1, day_of_year - 366,
        day_of_year - 185, day_of_year - 359,
        day_of_year - memorial, day_of_year - labor,
        day_of_year - thanksgiving,
    ])
    nearest = offsets[np.arange(len(df)), np.abs(offsets).argmin(axis=1)]
    columns["HolidayOffset"] = np.clip(nearest, -14, 14)
    for endpoint in ("Origin", "Dest"):
        coordinates = airport_geometry[airport_levels.get_indexer(df[endpoint])]
        for axis in range(3):
            columns[f"{endpoint}Geo{axis}"] = coordinates[:, axis]
    folds = (
        pd.util.hash_pandas_object(df[hash_cols], index=False, categorize=False).to_numpy() % 5
    ).astype(int)
    for name, group in encoding_groups.items():
        keys = df[group[0]]
        if len(group) == 2:
            keys = keys + "_" + df[group[1]]
        codes = encoding_levels[name].get_indexer(keys)
        columns[name] = encoding_tables[name][codes, folds]
    for col in cat_cols:
        columns[col] = pd.Categorical.from_codes(
            cat_levels[col].get_indexer(df[col]), categories=cat_levels[col]
        )
    X = pd.DataFrame(columns, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=1000,
    num_parallel_tree=4,
    max_depth=5,
    learning_rate=0.02,
    min_child_weight=100,
    reg_lambda=100,
    subsample=0.8,
    colsample_bynode=0.8,
    max_cat_threshold=8,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
