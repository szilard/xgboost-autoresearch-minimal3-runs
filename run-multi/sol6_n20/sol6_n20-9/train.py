import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_starts = {f"c-{i}": start for i, start in enumerate(
    [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], start=1
)}
day_numbers = {f"c-{i}": i for i in range(1, 32)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DepHour"] = df["CRSDepTime"] // 100
    X["DayOfYear"] = df["Month"].map(month_starts) + df["DayofMonth"].map(day_numbers)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model_params = dict(
    n_estimators=400,
    max_depth=3,
    min_child_weight=10,
    gamma=2,
    max_bin=128,
    learning_rate=0.05,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)

class AveragedModel:
    def __init__(self, models):
        self.models = models

    def predict_proba(self, X):
        return sum(m.predict_proba(X) for m in self.models) / len(self.models)

members = [
    xgb.XGBClassifier(**model_params),
    xgb.XGBClassifier(**model_params, colsample_bytree=0.8),
    xgb.XGBClassifier(**model_params, subsample=0.8),
]

t0 = time.time()
for member in members:
    member.fit(X_train, y_train)
model = AveragedModel(members)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
