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
train_dep_minutes = (train["CRSDepTime"] // 100) * 60 + train["CRSDepTime"] % 100
origin_median_deptime = train_dep_minutes.groupby(train["Origin"]).median()

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["Month"] = df["Month"].str[2:].astype("int8")
    X["DayofMonth"] = df["DayofMonth"].str[2:].astype("int8")
    X["OriginRelativeDepTime"] = (
        (df["CRSDepTime"] // 100) * 60 + df["CRSDepTime"] % 100
        - df["Origin"].map(origin_median_deptime)
    )
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
    learning_rate=0.05,
    subsample=0.8,
    reg_lambda=30,
    reg_alpha=5,
    min_child_weight=5,
    enable_categorical=True,
    n_jobs=-1,
)
model = VotingClassifier(
    estimators=[
        ("seed42", xgb.XGBClassifier(**model_params, random_state=42)),
        ("seed123", xgb.XGBClassifier(**model_params, random_state=123)),
        ("seed999", xgb.XGBClassifier(**model_params, random_state=999)),
    ],
    voting="soft",
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
