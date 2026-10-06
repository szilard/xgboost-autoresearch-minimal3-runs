import pandas as pd
import numpy as np
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["DayOfWeek", "UniqueCarrier", "Origin", "Dest"]
num_cols = ["Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols}
cat_dtypes = {col: pd.CategoricalDtype(cat_levels[col]) for col in cat_cols}

def prepare(df):
    columns = {col: df[col].to_numpy() for col in num_cols}
    columns["MonthNumber"] = df["Month"].str[2:].to_numpy(dtype=int)
    day = df["DayofMonth"].str[2:].to_numpy(dtype=int)
    weekday = df["DayOfWeek"].str[2:].to_numpy(dtype=int) - 1
    month_starts = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])
    day_of_year = month_starts[columns["MonthNumber"] - 1] + day
    jan_weekday = (weekday - (day_of_year - 1)) % 7
    thanksgiving = 326 + (3 - (jan_weekday + 304) % 7) % 7
    memorial = 151 - (jan_weekday + 150) % 7
    labor = 244 + (-(jan_weekday + 243)) % 7
    holidays = {"Thanksgiving": thanksgiving, "Christmas": 359,
                "July4": 185, "Memorial": memorial, "Labor": labor}
    for name, date in holidays.items():
        columns[name + "Offset"] = np.clip(day_of_year - date, -7, 7)
    columns["NewYearOffset"] = np.clip((day_of_year - 1 + 182) % 365 - 182, -7, 7)
    departure = df["CRSDepTime"].to_numpy()
    columns["DepHour"] = departure // 100
    columns["DepMinute"] = departure % 100
    phase = 2 * np.pi * ((departure // 100) * 60 + departure % 100) / 1440
    columns["DepSin"] = np.sin(phase)
    columns["DepCos"] = np.cos(phase)
    columns.update({col: pd.Categorical.from_codes(
        cat_dtypes[col].categories.get_indexer(df[col]), dtype=cat_dtypes[col])
        for col in cat_cols})
    X = pd.DataFrame(columns, index=df.index)
    y = (df[target].to_numpy() == "Y").astype(int)
    return X, y

X_train, y_train = prepare(train)


def smoothed_logistic(y_true, margin, sample_weight=None):
    probability = 1 / (1 + np.exp(-margin))
    smoothed_target = 0.9 * y_true + 0.05
    gradient = probability - smoothed_target
    hessian = probability * (1 - probability)
    if sample_weight is not None:
        gradient *= sample_weight
        hessian *= sample_weight
    return gradient, hessian


model = xgb.XGBClassifier(
    objective=smoothed_logistic,
    n_estimators=100,
    max_depth=0,
    max_leaves=24,
    grow_policy="lossguide",
    tree_method="hist",
    learning_rate=0.05,
    min_child_weight=20,
    reg_lambda=10,
    reg_alpha=5,
    subsample=0.7,
    num_parallel_tree=3,
    colsample_bynode=0.8,
    max_bin=64,
    max_cat_threshold=16,
    enable_categorical=True,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
sample_weight = np.exp((X_train["MonthNumber"].to_numpy() - 12) * np.log(2) / 12)
sample_weight /= sample_weight.mean()
model.fit(X_train, y_train, sample_weight=sample_weight)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
