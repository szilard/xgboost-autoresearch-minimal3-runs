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
month_start = dict(zip(
    [f"c-{m}" for m in range(1, 13)],
    [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334],
))
day_number = {f"c-{d}": d for d in range(1, 32)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    X["DayOfYear"] = df["Month"].map(month_start) + df["DayofMonth"].map(day_number)
    X["DepHour"] = pd.Categorical(
        (df["CRSDepTime"] // 100) % 24, categories=list(range(24))
    )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=0,
    grow_policy="lossguide",
    max_leaves=16,
    tree_method="hist",
    learning_rate=0.05,
    min_child_weight=5,
    reg_lambda=30,
    subsample=0.8,
    colsample_bytree=0.4,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
