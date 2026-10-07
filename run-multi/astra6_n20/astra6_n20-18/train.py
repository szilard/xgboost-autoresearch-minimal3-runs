import pandas as pd
import numpy as np
from scipy.sparse.csgraph import shortest_path
from sklearn.ensemble import VotingClassifier
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_dtypes = {
    col: pd.CategoricalDtype(categories=sorted(train[col].unique()))
    for col in cat_cols
}

# Fit a compact airport geometry using only observed training route distances.
airports = pd.Index(sorted(set(train["Origin"]) | set(train["Dest"])))
graph = np.full((len(airports), len(airports)), np.inf)
np.fill_diagonal(graph, 0)
for (origin, dest), distance in train.groupby(["Origin", "Dest"])["Distance"].median().items():
    i, j = airports.get_loc(origin), airports.get_loc(dest)
    graph[i, j] = graph[j, i] = min(graph[i, j], graph[j, i], distance)
path_distances = shortest_path(graph, method="FW", directed=False)
assert np.isfinite(path_distances).all()
squared = path_distances ** 2
kernel = -0.5 * (squared - squared.mean(axis=0)[None, :]
                 - squared.mean(axis=1)[:, None] + squared.mean())
eigenvalues, eigenvectors = np.linalg.eigh(kernel)
coordinates = eigenvectors[:, -2:] * np.sqrt(np.maximum(eigenvalues[-2:], 0))
airport_coordinates = {
    airport: tuple(coordinates[i]) for i, airport in enumerate(airports)
}
geo_features = [f"{col}Geo{axis}" for col in ("Origin", "Dest") for axis in range(2)]

def prepare(df):
    values = {col: df[col].to_numpy() for col in num_cols}
    values.update({
        col: pd.Categorical.from_codes(dtype.categories.get_indexer(df[col]), dtype=dtype)
        for col, dtype in cat_dtypes.items()
    })
    for col in ("Origin", "Dest"):
        coords = np.asarray([airport_coordinates.get(a, (np.nan, np.nan)) for a in df[col]])
        for axis in range(2):
            values[f"{col}Geo{axis}"] = coords[:, axis]
    month = np.fromiter((int(v[2:]) for v in df["Month"]), dtype=int)
    day = np.fromiter((int(v[2:]) for v in df["DayofMonth"]), dtype=int)
    weekday = np.fromiter((int(v[2:]) - 1 for v in df["DayOfWeek"]), dtype=int)
    # Both 2005 and 2006 are non-leap years; the weekday fixes movable holidays.
    month_starts = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    day_of_year = month_starts[month - 1] + day
    jan1_weekday = (weekday - day_of_year + 1) % 7
    holiday_dates = np.column_stack([
        np.full(len(df), 1), np.full(len(df), 366), np.full(len(df), 359),
        np.full(len(df), 185),
        151 - (jan1_weekday + 150) % 7,
        244 + (-jan1_weekday - 243) % 7,
        326 + (3 - jan1_weekday - 304) % 7,
    ])
    offsets = day_of_year[:, None] - holiday_dates
    nearest = offsets[np.arange(len(df)), np.abs(offsets).argmin(axis=1)]
    values["HolidayPhase"] = np.where(np.abs(nearest) <= 3, np.sign(nearest), 2)
    X = pd.DataFrame(values, index=df.index)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


def smoothed_logistic(labels, margins):
    probabilities = 1.0 / (1.0 + np.exp(-np.asarray(margins).reshape(-1)))
    return probabilities - (0.05 + 0.9 * labels), probabilities * (1.0 - probabilities)


model_params = dict(
    objective=smoothed_logistic,
    n_estimators=1200,
    max_depth=0,
    grow_policy="lossguide",
    max_leaves=16,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=10,
    subsample=0.8,
    num_parallel_tree=1,
    colsample_bynode=0.8,
    enable_categorical=True,
    max_cat_to_onehot=1024,
    interaction_constraints=[
        ["CRSDepTime", "Distance", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"] + geo_features,
        ["Month"],
        ["HolidayPhase"],
    ],
    n_jobs=-1,
)


class SeasonShrinkXGB(xgb.XGBClassifier):
    def fit(self, X, y, **kwargs):
        super().fit(X, y, **kwargs)
        levels = X["Month"].cat.categories
        effects = []
        for position in (0, len(X) - 1):
            probes = pd.concat([X.iloc[[position]]] * len(levels), ignore_index=True)
            probes["Month"] = pd.Categorical(levels, dtype=X["Month"].dtype)
            margins = super().predict(probes, output_margin=True)
            effects.append(margins - margins.mean())
        np.testing.assert_allclose(effects[0], effects[1], atol=2e-5, rtol=0)
        self.month_effects_ = dict(zip(levels, effects[0]))
        return self

    def predict_proba(self, X):
        margins = super().predict(X, output_margin=True)
        correction = np.asarray([self.month_effects_.get(m, 0.0) for m in X["Month"]])
        p = 1.0 / (1.0 + np.exp(-(margins - 0.625 * correction)))
        return np.column_stack([1.0 - p, p])


model = VotingClassifier(
    estimators=[
        (f"seed_{seed}", SeasonShrinkXGB(**model_params, random_state=seed))
        for seed in (42, 137, 2026)
    ],
    voting="soft",
    n_jobs=1,
)

t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
