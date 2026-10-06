import pandas as pd
import time
import xgboost as xgb
from pathlib import Path
from harness import save_and_evaluate


data_dir = Path(__file__).parent / "data"
train = pd.read_csv(f"{data_dir}/train.csv")

cat_cols = ["Month", "DayofMonth", "DayOfWeek", "UniqueCarrier", "Origin", "Dest", "DepPeriod", "WeekPeriod", "HolidayWindow"]
num_cols = ["CRSDepTime", "Distance"]
target   = "dep_delayed_15min"


cat_levels = {col: sorted(train[col].unique()) for col in cat_cols if col not in ("DepPeriod", "WeekPeriod", "HolidayWindow")}
cat_levels["DepPeriod"] = sorted(((train["CRSDepTime"] // 100) // 6).unique())
cat_levels["WeekPeriod"] = sorted(
    (train["DayOfWeek"].astype(str) + "_" + ((train["CRSDepTime"] // 100) // 6).astype(str)).unique()
)
cat_levels["HolidayWindow"] = ["none", "thanksgiving", "winter", "july4", "memorial", "labor"]
month_number_by_category = {v: int(v.split("-")[-1]) for v in train["Month"].unique()}
day_number_by_category = {v: int(v.split("-")[-1]) for v in train["DayofMonth"].unique()}

def prepare(df):
    X = df[num_cols + [col for col in cat_cols if col not in ("DepPeriod", "WeekPeriod", "HolidayWindow")]].copy()
    X["DepPeriod"] = (df["CRSDepTime"] // 100) // 6
    X["WeekPeriod"] = df["DayOfWeek"].astype(str) + "_" + ((df["CRSDepTime"] // 100) // 6).astype(str)
    month_number = df["Month"].map(month_number_by_category)
    day_number = df["DayofMonth"].map(day_number_by_category)
    holiday = pd.Series("none", index=df.index, dtype="object")
    holiday.loc[(month_number == 11) & day_number.between(20, 30)] = "thanksgiving"
    holiday.loc[((month_number == 12) & (day_number >= 20)) | ((month_number == 1) & (day_number <= 3))] = "winter"
    holiday.loc[(month_number == 7) & day_number.between(1, 5)] = "july4"
    holiday.loc[(month_number == 5) & (day_number >= 25)] = "memorial"
    holiday.loc[(month_number == 9) & (day_number <= 7)] = "labor"
    X["HolidayWindow"] = holiday
    for col in cat_cols:
        X[col] = pd.Categorical(
            X[col].where(X[col].isin(cat_levels[col])),
            categories=cat_levels[col],
        )
    y = (df[target] == "Y").astype(int).to_numpy()
    return X, y

X_train, y_train = prepare(train)


model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=4,
    learning_rate=0.05,
    enable_categorical=True,
    max_cat_threshold=32,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
)


t0 = time.time()
model.fit(X_train, y_train)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
