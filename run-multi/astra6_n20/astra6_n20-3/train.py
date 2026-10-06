import pandas as pd
import numpy as np
import time
import xgboost as xgb
from scipy.sparse.csgraph import shortest_path
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier"]
num_cols = ["Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
cat_dtypes = {col: pd.CategoricalDtype(cat_levels[col]) for col in cat_cols}
cat_codes = {col: {value: i for i, value in enumerate(cat_levels[col])} for col in cat_cols}

airports = sorted(set(train["Origin"]) | set(train["Dest"]))
route_distances = train.groupby(["Origin", "Dest"])["Distance"].median().unstack()
route_matrix = route_distances.reindex(index=airports, columns=airports).to_numpy()
route_matrix = np.where(np.isnan(route_matrix), np.inf, route_matrix)
route_matrix = np.minimum(route_matrix, route_matrix.T)
np.fill_diagonal(route_matrix, 0)
typical_route_mileage = np.nanmedian(np.where(np.isfinite(route_matrix) & (route_matrix > 0), route_matrix, np.nan), axis=1)
airport_route_mileage = dict(zip(airports, typical_route_mileage))
network_distances = shortest_path(route_matrix, directed=False)
landmarks = ["ATL", "ORD", "DFW", "DEN", "LAX", "JFK"]
geography = {
    airport: network_distances[i, [airports.index(anchor) for anchor in landmarks]] / 1000
    for i, airport in enumerate(airports)
}
missing_geography = np.full(len(landmarks), np.nan)
month_offsets = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])

def prepare(df):
    data = {col: df[col].to_numpy() for col in num_cols}
    data.update({col: pd.Categorical.from_codes(
        [cat_codes[col].get(value, -1) for value in df[col].to_numpy()],
        dtype=cat_dtypes[col]) for col in cat_cols})
    departure = df["CRSDepTime"].to_numpy()
    hour, minute = departure // 100, departure % 100
    minutes = hour * 60 + minute
    data.update({
        "FlightDayTime": (minutes - 300) % 1440,
        "DepSin": np.sin(minutes * (2 * np.pi / 1440)),
        "DepCos": np.cos(minutes * (2 * np.pi / 1440)),
    })
    for side in ("Origin", "Dest"):
        locations = np.array([geography.get(code, missing_geography) for code in df[side].to_numpy()])
        typical = np.array([airport_route_mileage.get(code, np.nan) for code in df[side].to_numpy()])
        data[side + "TypicalRouteMileage"] = typical
        data[side + "RelativeRouteMileage"] = data["Distance"] / typical
        for j, anchor in enumerate(landmarks):
            data[side + "MilesTo" + anchor] = locations[:, j]
    month = np.array([int(value[2:]) for value in df["Month"].to_numpy()])
    data["SeasonSin"] = np.sin((month - 1) * (2 * np.pi / 12))
    data["SeasonCos"] = np.cos((month - 1) * (2 * np.pi / 12))
    day = np.array([int(value[2:]) for value in df["DayofMonth"].to_numpy()])
    weekday = np.array([int(value[2:]) - 1 for value in df["DayOfWeek"].to_numpy()])
    day_of_year = month_offsets[month - 1] + day
    january_weekday = (weekday - (day_of_year - 1)) % 7
    memorial_day = 151 - (january_weekday + 150) % 7
    labor_day = 244 + (-(january_weekday + 243)) % 7
    thanksgiving = 305 + (3 - (january_weekday + 304)) % 7 + 21
    holidays = np.column_stack((np.ones_like(day), memorial_day, np.full_like(day, 185),
                                labor_day, thanksgiving, np.full_like(day, 359)))
    differences = (day_of_year[:, None] - holidays + 182) % 365 - 182
    data["DaysSinceHoliday"] = np.minimum(np.where(differences >= 0, differences, 365).min(axis=1), 7)
    data["DaysUntilHoliday"] = np.minimum(np.where(differences <= 0, -differences, 365).min(axis=1), 7)
    X = pd.DataFrame(data, index=df.index)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


class MixedLossClassifier:
    def __init__(self, classifier, regressor):
        self.classifier = classifier
        self.regressor = regressor

    def predict_proba(self, X):
        probability = 0.5 * (self.classifier.predict_proba(X)[:, 1]
                             + np.clip(self.regressor.predict(X), 0, 1))
        return np.column_stack((1 - probability, probability))


model = xgb.XGBClassifier(
    n_estimators=600,
    max_depth=0,
    grow_policy="lossguide",
    tree_method="approx",
    max_leaves=32,
    learning_rate=0.04,
    min_child_weight=100,
    reg_lambda=50,
    gamma=5,
    subsample=0.8,
    colsample_bytree=0.7,
    enable_categorical=True,
    max_cat_threshold=8,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
training_month = train["Month"].str[2:].astype(float).to_numpy()
sample_weight = np.power(2.0, (training_month - 12) / 6)
monthly_rates = pd.Series(y_train, index=train.index).groupby(train["Month"]).mean()
month_probability = train["Month"].map(monthly_rates).to_numpy()
sample_weight *= np.where(y_train == 1, 0.5 / month_probability, 0.5 / (1 - month_probability))
sample_weight /= sample_weight.mean()
parameters = model.get_params()
regression_parameters = {**parameters, "objective": "reg:squarederror",
                         "min_child_weight": 400, "reg_lambda": 200, "tree_method": "hist", "gamma": 0}
regressor = xgb.XGBRegressor(**regression_parameters)
model.fit(X_train, y_train, sample_weight=sample_weight)
regressor.fit(X_train, y_train, sample_weight=sample_weight)
model = MixedLossClassifier(model, regressor)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
