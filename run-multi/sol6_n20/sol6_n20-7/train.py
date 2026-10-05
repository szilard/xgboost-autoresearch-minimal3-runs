import pandas as pd
import time
import xgboost as xgb
from sklearn.ensemble import VotingClassifier
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
week_of_month = {f"c-{d}": min((d - 1) // 7, 3) for d in range(1, 32)}
train_deptime_minutes = train["CRSDepTime"] // 100 * 60 + train["CRSDepTime"] % 100
carrier_origin_median_deptime = train_deptime_minutes.groupby(
    train["UniqueCarrier"] + "-" + train["Origin"]
).median()

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["WeekOfMonth"] = df["DayofMonth"].map(week_of_month)
    X["TimeVsCarrierOriginMedian"] = (df["CRSDepTime"] // 100 * 60 + df["CRSDepTime"] % 100) - (
        df["UniqueCarrier"] + "-" + df["Origin"]
    ).map(carrier_origin_median_deptime)
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


main_model = xgb.XGBClassifier(
    n_estimators=130,
    max_depth=3,
    learning_rate=0.1,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)
deep_model = xgb.XGBClassifier(
    n_estimators=130,
    max_depth=4,
    learning_rate=0.1,
    enable_categorical=True,
    random_state=43,
    n_jobs=-1,
)
alternate_model = xgb.XGBClassifier(
    n_estimators=160,
    max_depth=3,
    learning_rate=0.1,
    enable_categorical=True,
    max_cat_to_onehot=20,
    random_state=44,
    n_jobs=-1,
)
model = VotingClassifier(
    estimators=[("main", main_model), ("deep", deep_model), ("alternate", alternate_model)],
    voting="soft",
    weights=[3, 1, 1],
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
