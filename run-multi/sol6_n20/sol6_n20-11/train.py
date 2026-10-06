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
month_start = dict(zip((f"c-{i}" for i in range(1, 13)),
                       (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)))
day_number = {f"c-{i}": i for i in range(1, 32)}
holiday_window = {}
for code, days in enumerate((
    list(range(47, 54)),        # Presidents' Day
    list(range(142, 153)),      # Memorial Day
    list(range(181, 192)),      # Independence Day
    list(range(242, 251)),      # Labor Day
    list(range(321, 334)),      # Thanksgiving
    list(range(348, 366)) + list(range(1, 5)),  # winter holidays
), start=1):
    holiday_window.update({day: code for day in days})

def prepare(df):
    X = df[num_cols + cat_cols].copy()
    X["DayOfYear"] = df["Month"].map(month_start) + df["DayofMonth"].map(day_number)
    X["HolidayWindow"] = pd.Categorical(
        X["DayOfYear"].map(holiday_window).fillna(0).astype(int), categories=range(7)
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
    n_estimators=500,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.7,
    colsample_bytree=0.6,
    reg_lambda=50,
    reg_alpha=10,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
