import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from scipy.sparse.csgraph import shortest_path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
crosses = {"CarrierOrigin": ("UniqueCarrier", "Origin")}
for name, (left, right) in crosses.items():
    cat_levels[name] = sorted((train[left] + "|" + train[right]).unique())
cat_indexes = {name: pd.Index(levels) for name, levels in cat_levels.items()}

# Fit a distance-based airport embedding using only training routes.
airport_index = pd.Index(sorted(set(train["Origin"]) | set(train["Dest"])))
routes = train.groupby(["Origin", "Dest"])["Distance"].median().reset_index()
graph = np.full((len(airport_index), len(airport_index)), np.inf)
graph[airport_index.get_indexer(routes["Origin"]),
      airport_index.get_indexer(routes["Dest"])] = routes["Distance"]
graph = np.minimum(graph, graph.T)
np.fill_diagonal(graph, 0)
squared_distances = shortest_path(graph, directed=False) ** 2
kernel = -0.5 * (squared_distances - squared_distances.mean(axis=0)[None, :]
                 - squared_distances.mean(axis=1)[:, None] + squared_distances.mean())
eigenvalues, eigenvectors = np.linalg.eigh(kernel)
coordinates = eigenvectors[:, -2:] * np.sqrt(np.maximum(eigenvalues[-2:], 0))
airport_vectors = np.vstack([coordinates, np.full((1, 2), np.nan)])

def prepare(df):
    raw = {col: df[col].to_numpy() for col in num_cols + cat_cols}
    for name, (left, right) in crosses.items():
        raw[name] = [f"{a}|{b}" for a, b in zip(raw[left], raw[right])]
    values = {col: raw[col] for col in num_cols}
    for col in cat_levels:
        values[col] = pd.Categorical.from_codes(
            cat_indexes[col].get_indexer(raw[col]), categories=cat_levels[col],
        )
    origin = airport_vectors[airport_index.get_indexer(raw["Origin"])]
    for axis in range(2):
        values[f"OriginCoordinate{axis}"] = origin[:, axis]
    X = pd.DataFrame(values, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=1600,
    num_parallel_tree=3,
    max_depth=6,
    max_bin=1024,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=100,
    subsample=0.85,
    colsample_bytree=0.9,
    feature_weights=np.array([
        4.0 if col == "CRSDepTime" else 0.5 if col in {"Month", "DayofMonth"} else 1.0
        for col in X_train.columns
    ]),
    max_cat_to_onehot=10000,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
