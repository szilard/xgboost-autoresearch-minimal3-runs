import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from sklearn.ensemble import VotingClassifier
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_starts = dict(zip(
    (f"c-{month}" for month in range(1, 13)),
    (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334),
))
day_numbers = {f"c-{day}": day for day in range(1, 32)}

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DayOfYear"] = df["Month"].map(month_starts) + df["DayofMonth"].map(day_numbers)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


shared_params = dict(
    learning_rate=0.05,
    enable_categorical=True,
    gamma=5,
    random_state=42,
    n_jobs=-1,
)
model = VotingClassifier(
    estimators=[
        ("depth3", xgb.XGBClassifier(n_estimators=400, max_depth=3, **shared_params)),
        ("depth2", xgb.XGBClassifier(n_estimators=700, max_depth=2, **shared_params)),
        ("depth4", xgb.XGBClassifier(n_estimators=18, max_depth=4, **shared_params)),
    ],
    voting="soft",
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
