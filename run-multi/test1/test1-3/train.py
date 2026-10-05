import pandas as pd
import time
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
month_offset = {f"c-{m}": sum(month_days[:m - 1]) for m in range(1, 13)}
day_number = {f"c-{d}": d for d in range(1, 32)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DayOfYear"] = df["Month"].map(month_offset) + df["DayofMonth"].map(day_number)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


class AveragedModel:
    def __init__(self, models):
        self.models = models

    def fit(self, X, y):
        for member in self.models:
            member.fit(X, y)
        return self

    def predict_proba(self, X):
        return (0.4 * self.models[0].predict_proba(X)
                + 0.4 * self.models[1].predict_proba(X)
                + 0.2 * self.models[2].predict_proba(X))


common = dict(n_estimators=250, learning_rate=0.05, enable_categorical=True,
              random_state=42, n_jobs=-1)
linear = Pipeline([
    ("features", ColumnTransformer([
        ("categories", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ("time", SplineTransformer(n_knots=10, knots="quantile"), ["CRSDepTime"]),
        ("season", SplineTransformer(n_knots=8, knots="quantile"), ["DayOfYear"]),
        ("distance", SplineTransformer(n_knots=4, knots="quantile"), ["Distance"]),
    ])),
    ("classifier", LogisticRegression(C=1.0, max_iter=200)),
])
model = AveragedModel([
    xgb.XGBClassifier(max_depth=3, **common),
    xgb.XGBClassifier(max_depth=4, **common),
    linear,
])


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
