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
carrier_origin_levels = sorted((train["UniqueCarrier"] + ">" + train["Origin"]).unique())

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    carrier_origin = df["UniqueCarrier"] + ">" + df["Origin"]
    X["CarrierOrigin"] = pd.Categorical(
        carrier_origin.where(carrier_origin.isin(carrier_origin_levels)),
        categories=carrier_origin_levels,
    )
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=4,
    min_child_weight=10,
    reg_alpha=10.0,
    max_cat_threshold=32,
    learning_rate=0.03,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
