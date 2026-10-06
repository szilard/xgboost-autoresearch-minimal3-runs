import pandas as pd
import time
import xgboost as xgb
from sklearn.ensemble import VotingClassifier
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_offsets = dict(zip((f"c-{i}" for i in range(1, 13)),
                         (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)))
day_numbers = {f"c-{i}": i for i in range(1, 32)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DayOfYear"] = df["Month"].map(month_offsets) + df["DayofMonth"].map(day_numbers)
    slot = (df["CRSDepTime"] // 100) % 24
    X["DepSlot"] = pd.Categorical(slot, categories=range(24))
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


base_model = xgb.XGBClassifier(
    n_estimators=500,
    max_depth=0,
    max_leaves=8,
    min_child_weight=10,
    reg_lambda=200,
    reg_alpha=10,
    gamma=5,
    grow_policy="lossguide",
    num_parallel_tree=3,
    subsample=0.8,
    colsample_bytree=0.8,
    learning_rate=0.05,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
alternate_model = xgb.XGBClassifier(**{
    **base_model.get_params(),
    "reg_lambda": 50,
    "reg_alpha": 0,
    "gamma": 0,
    "max_leaves": 12,
    "random_state": 137,
})
model = VotingClassifier(
    estimators=[("regularized", base_model), ("lighter", alternate_model)],
    voting="soft",
    weights=[2, 1],
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
