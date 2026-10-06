import pandas as pd
import numpy as np
from scipy.sparse.csgraph import shortest_path
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
cat_levels["UniqueCarrier"] = sorted({"US" if v == "HP" else v for v in cat_levels["UniqueCarrier"]})
cat_dtypes = {col: pd.CategoricalDtype(levels) for col, levels in cat_levels.items()}
cat_codes = {col: {value: i for i, value in enumerate(levels)} for col, levels in cat_levels.items()}

# Fit geometry only from training routes and distances.
airports = sorted(set(train["Origin"]) | set(train["Dest"]))
airport_index = {airport: i for i, airport in enumerate(airports)}
route_distances = np.full((len(airports), len(airports)), np.inf)
np.fill_diagonal(route_distances, 0.0)
for (origin, dest), distance in train.groupby(["Origin", "Dest"])["Distance"].median().items():
    i, j = airport_index[origin], airport_index[dest]
    route_distances[i, j] = route_distances[j, i] = min(route_distances[i, j], distance)
geodesic = shortest_path(route_distances, directed=False)
assert np.isfinite(geodesic).all(), "Training airport graph is disconnected"
squared = geodesic ** 2
gram = -0.5 * (squared - squared.mean(axis=0)[None, :] - squared.mean(axis=1)[:, None] + squared.mean())
eigenvalues, eigenvectors = np.linalg.eigh(gram)
coordinates = eigenvectors[:, -2:] * np.sqrt(np.maximum(eigenvalues[-2:], 0))
airport_geometry = {airport: tuple(coordinates[i]) for i, airport in enumerate(airports)}

def prepare(df):
    features = {col: df[col].to_numpy() for col in num_cols}
    for col in cat_cols:
        values = df[col].to_numpy()
        if col == "UniqueCarrier":
            values = ["US" if value == "HP" else value for value in values]
        features[col] = pd.Categorical.from_codes(
            [cat_codes[col].get(value, -1) for value in values], dtype=cat_dtypes[col],
        )
    features["DepartureMinute"] = features["CRSDepTime"] % 100
    for col in ["Origin", "Dest"]:
        geometry = np.asarray([airport_geometry.get(value, (np.nan, np.nan)) for value in df[col].to_numpy()])
        for axis in range(2):
            features[f"{col}Geo{axis}"] = geometry[:, axis]
    month = np.fromiter((int(value[2:]) for value in df["Month"].to_numpy()), dtype=np.int16)
    day = np.fromiter((int(value[2:]) for value in df["DayofMonth"].to_numpy()), dtype=np.int16)
    weekday = np.fromiter((int(value[2:]) for value in df["DayOfWeek"].to_numpy()), dtype=np.int16)
    thanksgiving = 22 + (day - weekday - 18) % 7
    thanksgiving_delta = day - thanksgiving
    features["HolidayTravelWindow"] = (
        ((month == 11) & (thanksgiving_delta >= -6) & (thanksgiving_delta <= 5))
        | ((month == 12) & (day >= 19))
        | ((month == 1) & (day <= 3))
        | ((month == 7) & (day <= 7))
    ).astype(np.int8)
    X = pd.DataFrame(features, index=df.index)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


class BlendedModel:
    def __init__(self, primary, secondary):
        self.primary = primary
        self.secondary = secondary

    def predict_proba(self, X):
        return 0.5 * self.primary.predict_proba(X) + 0.5 * self.secondary.predict_proba(X)


model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=3,
    learning_rate=0.1,
    min_child_weight=50,
    reg_lambda=20,
    num_parallel_tree=4,
    subsample=0.8,
    colsample_bynode=0.9,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


month_delay_rates = train[target].eq("Y").groupby(train["Month"]).mean()
training_rates = train["Month"].map(month_delay_rates).to_numpy()
training_weights = np.where(y_train == 1, 0.5 / training_rates, 0.5 / (1.0 - training_rates))

t0 = time.time()
model.fit(X_train, y_train, sample_weight=training_weights)
secondary = xgb.XGBClassifier(
    n_estimators=500,
    max_depth=7,
    learning_rate=0.05,
    min_child_weight=50,
    reg_lambda=20,
    max_cat_to_onehot=1024,
    subsample=0.8,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
secondary.fit(X_train, y_train, sample_weight=training_weights)
model = BlendedModel(model, secondary)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
