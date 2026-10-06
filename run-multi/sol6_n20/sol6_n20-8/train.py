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
hour_levels = list(range(24))

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    X["DepHour"] = pd.Categorical(
        df["CRSDepTime"] // 100, categories=hour_levels
    )
    X["DayNum"] = df["DayofMonth"].str[2:].astype("int16")
    X["MonthNum"] = df["Month"].str[2:].astype("int8")
    X["YearEndTravel"] = (
        ((X["MonthNum"] == 12) & (X["DayNum"] >= 21))
        | ((X["MonthNum"] == 1) & (X["DayNum"] <= 6))
    ).astype("int8")
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model_params = dict(
    n_estimators=300,
    max_depth=3,
    min_child_weight=5,
    learning_rate=0.05,
    subsample=0.8,
    max_bin=512,
    enable_categorical=True,
    n_jobs=-1,
)

class AveragedModel:
    def __init__(self, models):
        self.models = models

    def predict_proba(self, X):
        return sum(m.predict_proba(X) for m in self.models) / len(self.models)


t0 = time.time()
models = []
for seed, depth in ((42, 3), (43, 3), (44, 4), (45, 3), (46, 3)):
    fitted = xgb.XGBClassifier(**model_params, random_state=seed)
    fitted.set_params(max_depth=depth)
    if seed in (45, 46):
        fitted.set_params(booster="dart", n_estimators=200, rate_drop=0.2, skip_drop=0.5)
    fitted.fit(X_train, y_train)
    models.append(fitted)
model = AveragedModel(models)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
