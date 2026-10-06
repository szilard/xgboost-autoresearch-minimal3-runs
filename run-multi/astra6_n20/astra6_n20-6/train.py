import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance", "DayofMonth"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}

cat_maps = {col: {value: i for i, value in enumerate(levels)}
            for col, levels in cat_levels.items()}
cat_dtypes = {col: pd.CategoricalDtype(levels) for col, levels in cat_levels.items()}

schedule_specs = {
    "OriginRelativeDeparture": ("Origin",),
    "RouteRelativeDeparture": ("Origin", "Dest"),
    "CarrierOriginRelativeDeparture": ("UniqueCarrier", "Origin"),
}
training_minutes = 60 * (train["CRSDepTime"] // 100) + train["CRSDepTime"] % 100
schedule_medians = {}
for name, columns in schedule_specs.items():
    keys = ["|".join(parts) for parts in zip(*(train[col] for col in columns))]
    schedule_medians[name] = pd.DataFrame({"key": keys, "minutes": training_minutes}).groupby("key")["minutes"].median().to_dict()

def prepare(df):
    data = {col: df[col].to_numpy() for col in num_cols}
    data["DayofMonth"] = [int(value[2:]) for value in df["DayofMonth"]]
    for col in cat_cols:
        data[col] = pd.Categorical.from_codes(
            [cat_maps[col].get(value, -1) for value in df[col]], dtype=cat_dtypes[col]
        )
    departure = df["CRSDepTime"].to_numpy()
    minutes = 60 * (departure // 100) + departure % 100
    for name, columns in schedule_specs.items():
        medians = np.array([schedule_medians[name].get("|".join(parts), np.nan)
                            for parts in zip(*(df[col] for col in columns))], dtype=float)
        data[name] = minutes - medians
    X = pd.DataFrame(data, index=df.index)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=500,
    max_depth=0,
    grow_policy="lossguide",
    max_leaves=16,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=10,
    reg_alpha=10,
    gamma=3,
    subsample=0.8,
    colsample_bynode=0.8,
    num_parallel_tree=4,
    max_cat_threshold=128,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
