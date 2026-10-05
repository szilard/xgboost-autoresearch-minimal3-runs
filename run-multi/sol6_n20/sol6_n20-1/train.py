import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
month_start = {1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151, 7: 181,
               8: 212, 9: 243, 10: 273, 11: 304, 12: 334}
weekday_block_levels = sorted((train["DayOfWeek"] + "-" +
                               (train["CRSDepTime"] // 300).astype(str)).unique())

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    month = df["Month"].str[2:].astype(int)
    X["DayofMonth"] = df["DayofMonth"].str[2:].astype(int)
    X["DayOfYear"] = month.map(month_start) + X["DayofMonth"]
    X["WeekdayTimeBlock"] = pd.Categorical(
        df["DayOfWeek"] + "-" + (df["CRSDepTime"] // 300).astype(str),
        categories=weekday_block_levels,
    )
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


class AveragedModels:
    def __init__(self):
        common = dict(learning_rate=0.1, enable_categorical=True,
                      random_state=42, n_jobs=-1)
        self.primary = xgb.XGBClassifier(n_estimators=150, max_depth=3, **common)
        self.secondary = xgb.XGBClassifier(n_estimators=100, max_depth=4, **common)

    def fit(self, X, y):
        self.primary.fit(X, y)
        self.secondary.fit(X, y)
        return self

    def predict_proba(self, X):
        return 0.7 * self.primary.predict_proba(X) + 0.3 * self.secondary.predict_proba(X)


model = AveragedModels()


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
