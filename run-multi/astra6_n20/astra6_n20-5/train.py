import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: pd.Index(sorted(train[col].unique())) for col in cat_cols}
cat_codes = {col: {value: i for i, value in enumerate(levels)}
             for col, levels in cat_levels.items()}

def prepare(df):
    columns = {col: df[col].to_numpy() for col in num_cols}
    month = np.array([int(value[2:]) for value in df["Month"].to_numpy()])
    day = np.array([int(value[2:]) for value in df["DayofMonth"].to_numpy()])
    weekday = np.array([int(value[2:]) for value in df["DayOfWeek"].to_numpy()])
    first_weekday = (weekday - day) % 7
    thanksgiving = 22 + (3 - first_weekday) % 7
    memorial = 31 - (first_weekday + 30) % 7
    labor = 1 + (-first_weekday) % 7
    holiday_delta = np.select(
        [month == 1, month == 5, month == 7, month == 9, month == 11, month == 12],
        [day - 1, day - memorial, day - 4, day - labor, day - thanksgiving,
         np.where(day <= 28, day - 25, day - 32)], default=99,
    )
    columns["HolidayWindow"] = np.abs(holiday_delta) <= 4
    columns["HolidayDay"] = holiday_delta == 0
    for col in cat_cols:
        columns[col] = pd.Categorical.from_codes(
            [cat_codes[col].get(value, -1) for value in df[col].to_numpy()],
            categories=cat_levels[col],
        )
    X = pd.DataFrame(columns, index=df.index)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=3,
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=100,
    reg_alpha=10,
    gamma=5,
    num_parallel_tree=4,
    colsample_bynode=0.8,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
training_month = train["Month"].str[2:].astype(int).to_numpy()
training_weight = 2.0 ** ((training_month - 12) / 6.0)
training_weight /= training_weight.mean()
model.fit(X_train, y_train, sample_weight=training_weight)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
