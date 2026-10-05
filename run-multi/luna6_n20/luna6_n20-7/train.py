import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


target_encode_cols = ["Origin"]
train["__train_row_id"] = np.arange(len(train))
target_encoder = TargetEncoder(
    target_type="binary",
    smooth="auto",
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
)
train_oof_target_rates = target_encoder.fit_transform(
    train[target_encode_cols], (train[target] == "Y").astype(int)
).astype(np.float32)
target_global_mean = target_encoder.target_mean_
target_rate_maps = {
    col: dict(zip(target_encoder.categories_[i], target_encoder.encodings_[i]))
    for i, col in enumerate(target_encode_cols)
}

cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    if "__train_row_id" in df:
        target_rates = train_oof_target_rates[df["__train_row_id"].to_numpy()]
    else:
        target_rates = np.column_stack([
            df[col].map(target_rate_maps[col]).fillna(target_global_mean).to_numpy(dtype=np.float32)
            for col in target_encode_cols
        ])
    for i, col in enumerate(target_encode_cols):
        X[f"{col}TargetRate"] = target_rates[:, i]
    for col in cat_cols:
        X[col] = pd.Categorical(X[col], categories=cat_levels[col])
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)
train_oof_target_rates = None


model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
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
