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
train_dep_hour = train["CRSDepTime"] // 100
dep_hour_levels = sorted(train_dep_hour.unique())
train_dow_hour = train["DayOfWeek"].astype(str) + "->" + train_dep_hour.astype(str)
dow_hour_levels = sorted(train_dow_hour.unique())

te_fold_cols = num_cols + cat_cols
te_n_folds = 5
te_smoothing = 50.0
te_train_folds = (
    pd.util.hash_pandas_object(train[te_fold_cols], index=False).to_numpy() % te_n_folds
)
te_target = (train[target] == "Y").astype("float64").to_numpy()
te_train_keys = {
    "Carrier": train["UniqueCarrier"].astype(str),
    "Dest": train["Dest"].astype(str),
    "DOWHour": train_dow_hour,
}
te_priors = {}
te_lookups = {name: {} for name in te_train_keys}
for fold in range(te_n_folds):
    use_rows = te_train_folds != fold
    prior = float(te_target[use_rows].mean())
    te_priors[fold] = prior
    for name, keys in te_train_keys.items():
        stats = (
            pd.DataFrame({"key": keys.to_numpy()[use_rows], "target": te_target[use_rows]})
            .groupby("key", sort=False)["target"]
            .agg(["sum", "count"])
        )
        rates = (stats["sum"] + te_smoothing * prior) / (stats["count"] + te_smoothing)
        te_lookups[name].update(
            {(fold, str(key)): float(rate) for key, rate in rates.items()}
        )

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    dep_hour = df["CRSDepTime"] // 100
    X["DepHour"] = pd.Categorical(
        dep_hour.where(dep_hour.isin(dep_hour_levels)),
        categories=dep_hour_levels,
    )
    dow_hour = df["DayOfWeek"].astype(str) + "->" + dep_hour.astype(str)
    X["DOWHour"] = pd.Categorical(
        dow_hour.where(dow_hour.isin(dow_hour_levels)),
        categories=dow_hour_levels,
    )
    row_folds = (
        pd.util.hash_pandas_object(df[te_fold_cols], index=False).to_numpy() % te_n_folds
    )
    row_te_keys = {
        "Carrier": df["UniqueCarrier"].astype(str),
        "Dest": df["Dest"].astype(str),
        "DOWHour": dow_hour,
    }
    for name, keys in row_te_keys.items():
        X[f"{name}DelayRate"] = [
            te_lookups[name].get((int(fold), str(key)), te_priors[int(fold)])
            for fold, key in zip(row_folds, keys)
        ]
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=3,
    max_cat_to_onehot=25,
    gamma=0.1,
    learning_rate=0.1,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
