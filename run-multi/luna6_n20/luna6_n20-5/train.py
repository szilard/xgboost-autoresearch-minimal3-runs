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
target_encoding_signature_cols = [
    "Month", "DayofMonth", "DayOfWeek", "CRSDepTime",
    "UniqueCarrier", "Origin", "Dest", "Distance",
]
target_encoding_labels = (train[target] == "Y").astype(float)
target_encoding_hashes = pd.util.hash_pandas_object(
    train[target_encoding_signature_cols], index=False
).to_numpy()
target_encoding_folds = (target_encoding_hashes % 5).astype(int)
target_encoding_prior = float(target_encoding_labels.mean())
target_encoding_smoothing = 100.0

def fit_target_rate_lookup(values):
    stats = pd.DataFrame({
        "category": values,
        "label": target_encoding_labels,
        "fold": target_encoding_folds,
    })
    totals = stats.groupby("category", sort=False)["label"].agg(["sum", "count"])
    fold_totals = stats.groupby(["category", "fold"], sort=False)["label"].agg(["sum", "count"])
    fold_sums = fold_totals["sum"].to_dict()
    fold_counts = fold_totals["count"].to_dict()
    rates = {}
    for category, total in totals.iterrows():
        for fold in range(5):
            other_count = total["count"] - fold_counts.get((category, fold), 0)
            other_sum = total["sum"] - fold_sums.get((category, fold), 0.0)
            rates[(category, fold)] = (
                other_sum + target_encoding_smoothing * target_encoding_prior
            ) / (other_count + target_encoding_smoothing)
    return rates

origin_target_rates = fit_target_rate_lookup(train["Origin"])

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    signature_hashes = pd.util.hash_pandas_object(
        df[target_encoding_signature_cols], index=False
    ).to_numpy()
    row_folds = (signature_hashes % 5).astype(int)
    X["OriginTargetRate"] = [
        origin_target_rates.get((category, int(fold)), target_encoding_prior)
        for category, fold in zip(df["Origin"], row_folds)
    ]
    dep_hour = (df["CRSDepTime"] // 100).astype(int)
    X["DepHour"] = pd.Categorical(dep_hour, categories=range(24))
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
