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
airports = pd.Index(sorted(set(train["Origin"]) | set(train["Dest"])))
airport_index = {airport: index for index, airport in enumerate(airports)}
distance_graph = np.full((len(airports), len(airports)), np.inf)
np.fill_diagonal(distance_graph, 0.0)
for (origin, dest), distance in train.groupby(["Origin", "Dest"])["Distance"].median().items():
    i, j = airport_index[origin], airport_index[dest]
    distance_graph[i, j] = distance_graph[j, i] = min(distance_graph[i, j], distance)
graph_distances = shortest_path(distance_graph, directed=False, method="FW")
assert np.isfinite(graph_distances).all(), "Training airport graph must be connected"
squared_distances = graph_distances ** 2
gram = -0.5 * (squared_distances - squared_distances.mean(axis=0)[None, :]
               - squared_distances.mean(axis=1)[:, None] + squared_distances.mean())
eigenvalues, eigenvectors = np.linalg.eigh(gram)
coordinates = eigenvectors[:, -3:] * np.sqrt(np.maximum(eigenvalues[-3:], 0.0))
airport_coordinates = {airport: tuple(coordinates[index]) for index, airport in enumerate(airports)}

def prepare(df):
    X = pd.DataFrame(
        {**{col: df[col].to_numpy() for col in num_cols},
         **{col: pd.Categorical.from_codes(cat_levels[col].get_indexer(df[col]),
                                          categories=cat_levels[col]) for col in cat_cols}},
        index=df.index,
    )
    X["DepMinute"] = df["CRSDepTime"].to_numpy() % 100
    endpoint_coords = {}
    for column in ("Origin", "Dest"):
        coords = np.array([airport_coordinates.get(airport, (np.nan,) * 3)
                           for airport in df[column]], dtype=np.float32)
        endpoint_coords[column] = coords
        for axis in range(1, 3):
            X[f"{column}Geo{axis}"] = coords[:, axis]
    direction = (endpoint_coords["Dest"] - endpoint_coords["Origin"]) / np.maximum(
        df["Distance"].to_numpy()[:, None], 1
    )
    for axis in range(1, 3):
        X[f"Direction{axis}"] = direction[:, axis]
    month = np.array([int(value[2:]) for value in df["Month"]])
    day = np.array([int(value[2:]) for value in df["DayofMonth"]])
    weekday = np.array([int(value[2:]) for value in df["DayOfWeek"]])
    january_day = np.where(month == 12, day - 31, day)
    may_day = np.where(month == 6, day + 31, day)
    july_day = np.where(month == 6, day - 30, day)
    september_day = np.where(month == 8, day - 31, day)
    november_day = np.where(month == 12, day + 30, day)
    december_day = np.where(month == 1, day + 31, day)
    offsets = np.column_stack([
        np.where((month == 12) | (month == 1), january_day - 1, np.nan),
        np.where((month == 5) | (month == 6), may_day - (31 - (weekday + 30 - may_day) % 7), np.nan),
        np.where((month == 6) | (month == 7), july_day - 4, np.nan),
        np.where((month == 8) | (month == 9), september_day - (1 + (september_day - weekday) % 7), np.nan),
        np.where((month == 11) | (month == 12), november_day - (22 + (4 - weekday + november_day - 22) % 7), np.nan),
        np.where((month == 12) | (month == 1), december_day - 25, np.nan),
    ])
    holiday_kind = np.where(np.isfinite(offsets), np.abs(offsets), np.inf).argmin(axis=1)
    holiday_offset = offsets[np.arange(len(df)), holiday_kind]
    near_holiday = np.abs(holiday_offset) <= 7
    X["HolidayOffset"] = np.where(near_holiday, holiday_offset, np.nan)
    X["HolidayType"] = pd.Categorical.from_codes(
        np.where(near_holiday, holiday_kind, -1),
        categories=["NewYear", "Memorial", "Independence", "Labor", "Thanksgiving", "Christmas"],
    )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


calendar_columns = ["Month", "HolidayOffset", "HolidayType"]
operational_columns = [column for column in X_train.columns if column not in calendar_columns]
calendar_model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=2,
    learning_rate=0.05,
    min_child_weight=200,
    reg_lambda=50,
    enable_categorical=True,
    max_cat_to_onehot=10000,
    random_state=42,
    n_jobs=-1,
)
operational_model = xgb.XGBClassifier(
    n_estimators=600,
    max_depth=0,
    grow_policy="lossguide",
    max_leaves=32,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=50,
    subsample=0.85,
    num_parallel_tree=4,
    colsample_bynode=0.85,
    max_cat_threshold=8,
    max_cat_to_onehot=10000,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
calendar_model.fit(X_train[calendar_columns], y_train)
calendar_margin = 0.5 * calendar_model.predict(X_train[calendar_columns], output_margin=True)
operational_model.fit(X_train[operational_columns], y_train, base_margin=calendar_margin)
print(f"Training time: {time.time() - t0:.1f}s")


class CalendarResidualModel:
    def __init__(self, calendar, operational, calendar_features, operational_features):
        self.calendar = calendar
        self.operational = operational
        self.calendar_features = calendar_features
        self.operational_features = operational_features

    def predict_proba(self, X):
        margin = 0.5 * self.calendar.predict(X[self.calendar_features], output_margin=True)
        return self.operational.predict_proba(X[self.operational_features], base_margin=margin)


model = CalendarResidualModel(calendar_model, operational_model, calendar_columns, operational_columns)


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
