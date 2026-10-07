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
cat_dtypes = {col: pd.CategoricalDtype(cat_levels[col]) for col in cat_cols}
cat_maps = {col: {value: i for i, value in enumerate(cat_levels[col])} for col in cat_cols}
carrier_origin_levels = sorted((train["UniqueCarrier"] + "|" + train["Origin"]).unique())
carrier_origin_dtype = pd.CategoricalDtype(carrier_origin_levels)
carrier_origin_map = {value: i for i, value in enumerate(carrier_origin_levels)}
airports = sorted(set(train["Origin"]) | set(train["Dest"]))
airport_indices = {airport: i for i, airport in enumerate(airports)}
route_graph = np.full((len(airports), len(airports)), np.inf)
origin_indices = train["Origin"].map(airport_indices).to_numpy()
dest_indices = train["Dest"].map(airport_indices).to_numpy()
np.minimum.at(route_graph, (origin_indices, dest_indices), train["Distance"].to_numpy())
np.minimum.at(route_graph, (dest_indices, origin_indices), train["Distance"].to_numpy())
np.fill_diagonal(route_graph, 0.0)
landmarks = ["LAX", "ORD", "ATL"]
network_distances = shortest_path(
    route_graph, directed=False, indices=[airport_indices[name] for name in landmarks]
)
landmark_distances = {
    landmark: {airport: float(distance) for airport, distance in zip(airports, distances)
               if np.isfinite(distance)}
    for landmark, distances in zip(landmarks, network_distances)
}

def prepare(df):
    values = {col: df[col].to_numpy() for col in num_cols}
    values["DayofMonth"] = [int(value[2:]) for value in df["DayofMonth"].to_numpy()]
    values["Month"] = [int(value[2:]) for value in df["Month"].to_numpy()]
    carrier_origin = df["UniqueCarrier"].to_numpy() + "|" + df["Origin"].to_numpy()
    values["CarrierOrigin"] = pd.Categorical.from_codes(
        np.fromiter((carrier_origin_map.get(value, -1) for value in carrier_origin), dtype=np.int16),
        dtype=carrier_origin_dtype,
    )
    for landmark, lookup in landmark_distances.items():
        for col in ["Origin", "Dest"]:
            values[f"{col}DistanceTo{landmark}"] = [
                lookup.get(airport, np.nan) for airport in df[col].to_numpy()
            ]
    values.update({
        col: pd.Categorical.from_codes(
            np.fromiter((cat_maps[col].get(value, -1) for value in df[col].to_numpy()), dtype=np.int16),
            dtype=cat_dtypes[col],
        )
        for col in cat_cols
    })
    X = pd.DataFrame(values, index=df.index)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


class RankedFlightModel:
    def __init__(self, ranker):
        self.ranker = ranker

    def predict_proba(self, X):
        score = self.ranker.predict(X).astype(float)
        probability = 1.0 / (1.0 + np.exp(-np.clip(score, -50, 50)))
        return np.column_stack([1.0 - probability, probability])


model = xgb.XGBRanker(
    objective="rank:pairwise",
    lambdarank_pair_method="mean",
    lambdarank_num_pair_per_sample=1,
    lambdarank_score_normalization=False,
    n_estimators=600,
    max_depth=0,
    max_leaves=32,
    grow_policy="lossguide",
    learning_rate=0.05,
    min_child_weight=30,
    reg_lambda=10,
    subsample=0.8,
    num_parallel_tree=4,
    colsample_bynode=0.8,
    max_cat_to_onehot=10000,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
ranking_order = np.random.default_rng(42).permutation(len(y_train))
ranking_groups = np.diff(np.linspace(0, len(y_train), 33, dtype=int))
model.fit(X_train.iloc[ranking_order], y_train[ranking_order], group=ranking_groups)
print(f"Training time: {time.time() - t0:.1f}s")
model = RankedFlightModel(model)


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
