import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate
from sklearn.model_selection import StratifiedKFold


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"
month_start_day = {1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151,
                   7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334}


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
cat_levels["DepHour"] = sorted((train["CRSDepTime"] // 100).unique())

target_rate_cols = ["UniqueCarrier", "Origin", "Dest"]
target_rate_alpha = 100.0
train_target = (train[target] == "Y").astype("float32").to_numpy()
target_prior = float(train_target.mean())
target_rate_maps = {}
oof_target_encodings = pd.DataFrame(index=train.index)
folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for col in target_rate_cols:
    oof = np.empty(len(train), dtype=np.float32)
    for fit_idx, held_idx in folds.split(train, train_target):
        fit_data = pd.DataFrame({col: train[col].to_numpy()[fit_idx], "_target": train_target[fit_idx]})
        stats = fit_data.groupby(col)["_target"].agg(["sum", "count"])
        fold_prior = float(train_target[fit_idx].mean())
        encoding = (stats["sum"] + target_rate_alpha * fold_prior) / (stats["count"] + target_rate_alpha)
        held_keys = pd.Series(train[col].to_numpy()[held_idx])
        oof[held_idx] = held_keys.map(encoding).fillna(fold_prior).to_numpy(dtype=np.float32)
    oof_target_encodings[f"{col}DelayRate"] = oof

    full_data = pd.DataFrame({col: train[col], "_target": train_target})
    stats = full_data.groupby(col)["_target"].agg(["sum", "count"])
    target_rate_maps[col] = (
        (stats["sum"] + target_rate_alpha * target_prior) / (stats["count"] + target_rate_alpha)
    )

training_target_encodings = True

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DepHour"] = df["CRSDepTime"] // 100
    month_num = df["Month"].str[2:].astype(int)
    day_num = df["DayofMonth"].str[2:].astype(int)
    X["DayOfYear"] = day_num + month_num.map(month_start_day)
    for col in cat_cols + ["DepHour"]:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    if training_target_encodings:
        for col in target_rate_cols:
            X[f"{col}DelayRate"] = oof_target_encodings[f"{col}DelayRate"].to_numpy()
    else:
        for col in target_rate_cols:
            X[f"{col}DelayRate"] = df[col].map(target_rate_maps[col]).fillna(target_prior).to_numpy()
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)
training_target_encodings = False
oof_target_encodings = None


model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
