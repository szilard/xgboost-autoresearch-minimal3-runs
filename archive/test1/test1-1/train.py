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

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    month = df["Month"].str[2:].astype(int)
    day_of_month = df["DayofMonth"].str[2:].astype(int)
    X["Month"] = month
    X["DayofMonth"] = day_of_month
    X["DepHour"] = pd.Categorical(df["CRSDepTime"] // 100, categories=range(24))
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


class Blend:
    def __init__(self, shallow, deeper):
        self.shallow = shallow
        self.deeper = deeper

    def predict_proba(self, X):
        return 0.75 * self.shallow.predict_proba(X) + 0.25 * self.deeper.predict_proba(X)


model3 = xgb.XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.1,
                           enable_categorical=True, random_state=42, n_jobs=-1)
model4 = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1,
                           enable_categorical=True, random_state=42, n_jobs=-1)


t0 = time.time()
model3.fit(X_train, y_train)
model4.fit(X_train, y_train)
model = Blend(model3, model4)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
