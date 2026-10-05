import pandas as pd
import math
import time
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_starts = dict(zip([f"c-{i}" for i in range(1, 13)], [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]))
day_numbers = {f"c-{i}": i for i in range(1, 32)}
season_cos = {day: math.cos(2 * math.pi * (day - 1) / 365) for day in range(1, 366)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DepHour"] = pd.Categorical(df["CRSDepTime"] // 100, categories=range(24))
    X["DayOfYear"] = df["Month"].map(month_starts) + df["DayofMonth"].map(day_numbers)
    X["SeasonCos"] = X["DayOfYear"].map(season_cos)
    X["Flight"] = df["Origin"] + "-" + df["Dest"]
    X["CarrierOrigin"] = df["UniqueCarrier"] + "-" + df["Origin"]
    X["CarrierHour"] = df["UniqueCarrier"] + "-" + (df["CRSDepTime"] // 100).astype(str)
    X["OriginHour"] = df["Origin"] + "-" + (df["CRSDepTime"] // 100).astype(str)
    for col in cat_cols:
        X[col] = pd.Categorical(X[col], categories=cat_levels[col])
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)

def tree_columns(X):
    return X.drop(columns=["Flight", "CarrierOrigin", "CarrierHour", "OriginHour"])


boosted_model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=3,
    learning_rate=0.1,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
linear_features = ColumnTransformer([
    ("categories", OneHotEncoder(handle_unknown="ignore"), cat_cols + ["DepHour", "Flight", "CarrierOrigin", "CarrierHour", "OriginHour"]),
    ("numeric", StandardScaler(), num_cols + ["DayOfYear", "SeasonCos"]),
])
additive_model = make_pipeline(linear_features, LogisticRegression(solver="liblinear", C=0.1, max_iter=150))
model = VotingClassifier(
    estimators=[("boosted", make_pipeline(FunctionTransformer(tree_columns), boosted_model)), ("additive", additive_model)],
    voting="soft",
    weights=[3, 1],
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
