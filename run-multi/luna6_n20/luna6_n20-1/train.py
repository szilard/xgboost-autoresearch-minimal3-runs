import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate
from sklearn.model_selection import StratifiedKFold


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")
TRAIN_INDEX_START = 1_000_000_000
TRAIN_INDEX_STOP = TRAIN_INDEX_START + len(train)
train.index = range(TRAIN_INDEX_START, TRAIN_INDEX_STOP)

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}

# Cross-fitted target-rate lookups: training rows use rates from other folds,
# while evaluation rows use smoothed rates fitted on all of train.
target_values = (train[target] == "Y").astype(float)
global_target_rate = float(target_values.mean())
target_rate_keys = {
    "CarrierTargetRate": train["UniqueCarrier"],
    "OriginTargetRate": train["Origin"],
    "DestTargetRate": train["Dest"],
}
target_rate_smoothing = 100.0
target_rate_maps = {}
target_rate_oof = {}
folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(
    np.arange(len(train)), target_values.to_numpy()
))
for name, keys in target_rate_keys.items():
    full_sum = target_values.groupby(keys).sum()
    full_count = keys.value_counts()
    target_rate_maps[name] = (
        (full_sum + target_rate_smoothing * global_target_rate)
        / (full_count + target_rate_smoothing)
    ).to_dict()

    oof_values = np.empty(len(train), dtype=np.float32)
    for fit_pos, valid_pos in folds:
        fit_y = target_values.iloc[fit_pos]
        fit_keys = keys.iloc[fit_pos]
        prior = float(fit_y.mean())
        group_sum = fit_y.groupby(fit_keys).sum()
        group_count = fit_keys.value_counts()
        fold_map = (
            (group_sum + target_rate_smoothing * prior)
            / (group_count + target_rate_smoothing)
        ).to_dict()
        valid_keys = keys.iloc[valid_pos]
        oof_values[valid_pos] = valid_keys.map(fold_map).fillna(prior).to_numpy(dtype=np.float32)
    target_rate_oof[name] = oof_values

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DepHour"] = df["CRSDepTime"] // 100
    X["DepMinute"] = df["CRSDepTime"] % 100
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    row_keys = {
        "CarrierTargetRate": df["UniqueCarrier"],
        "OriginTargetRate": df["Origin"],
        "DestTargetRate": df["Dest"],
    }
    for name, keys in row_keys.items():
        values = np.empty(len(df), dtype=np.float32)
        for pos, (row_idx, key) in enumerate(zip(df.index, keys)):
            if TRAIN_INDEX_START <= row_idx < TRAIN_INDEX_STOP:
                values[pos] = target_rate_oof[name][row_idx - TRAIN_INDEX_START]
            else:
                values[pos] = target_rate_maps[name].get(key, global_target_rate)
        X[name] = values
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=800,
    max_depth=6,
    max_bin=512,
    learning_rate=0.02,
    reg_alpha=0.1,
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
