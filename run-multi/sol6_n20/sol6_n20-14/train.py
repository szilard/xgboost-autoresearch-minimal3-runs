import pandas as pd
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
month_start = dict(zip((f"c-{m}" for m in range(1, 13)),
                       (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)))
day_number = {f"c-{d}": d for d in range(1, 32)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    X["DepHour"] = pd.Categorical(df["CRSDepTime"] // 100, categories=list(range(24)))
    X["DayOfYear"] = df["Month"].map(month_start) + df["DayofMonth"].map(day_number)
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


class AveragedModels:
    def __init__(self, models):
        self.models = models

    def fit(self, X, y):
        for fitted_model in self.models:
            fitted_model.fit(X, y)
        return self

    def predict_proba(self, X):
        return (2 * self.models[0].predict_proba(X) + self.models[1].predict_proba(X)) / 3


base_params = dict(
    n_estimators=100,
    learning_rate=0.1,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
model = AveragedModels([
    xgb.XGBClassifier(max_depth=3, **base_params),
    xgb.XGBClassifier(max_depth=4, booster="dart", rate_drop=0.05,
                      skip_drop=0.5, normalize_type="forest", **base_params),
])


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
