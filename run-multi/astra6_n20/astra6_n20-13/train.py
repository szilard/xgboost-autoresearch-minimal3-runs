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
cat_codes = {col: {value: i for i, value in enumerate(cat_levels[col])} for col in cat_cols}

def prepare(df):
    """Prepare row-local features using fixed training category mappings."""
    values = {col: df[col].to_numpy() for col in num_cols}
    values["Month"] = np.array([int(v[2:]) for v in df["Month"].to_numpy()])
    for col in cat_cols:
        codes = [cat_codes[col].get(value, -1) for value in df[col].to_numpy()]
        values[col] = pd.Categorical.from_codes(codes, dtype=cat_dtypes[col])
    departure = df["CRSDepTime"].to_numpy()
    values["OperationalTime"] = ((departure // 100) * 60 + departure % 100 - 300) % 1440
    month = values["Month"]
    day = np.array([int(v[2:]) for v in df["DayofMonth"].to_numpy()])
    weekday = np.array([int(v[2:]) - 1 for v in df["DayOfWeek"].to_numpy()])
    doy = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])[month - 1] + day
    values["SeasonFortnight"] = (doy - 1) // 14
    jan1_weekday = (weekday - doy + 1) % 7
    thanksgiving = 326 + (3 - (jan1_weekday + 304) % 7) % 7
    thanksgiving_delta = doy - thanksgiving
    christmas_delta = (doy - 359 + 182) % 365 - 182
    memorial = 151 - (jan1_weekday + 150) % 7
    labor = 244 + (-(jan1_weekday + 243)) % 7
    summer_delta = np.stack([doy - memorial, doy - 185, doy - labor], axis=1)
    nearest_summer = summer_delta[np.arange(len(df)), np.abs(summer_delta).argmin(axis=1)]
    values["ThanksgivingWindow"] = np.where(np.abs(thanksgiving_delta) <= 7, thanksgiving_delta, 99)
    values["ChristmasWindow"] = np.where(np.abs(christmas_delta) <= 14, christmas_delta, 99)
    values["SummerHolidayWindow"] = np.where(np.abs(nearest_summer) <= 4, nearest_summer, 99)
    X = pd.DataFrame(values, index=df.index)
    y = (df[target].to_numpy() == "Y").astype(np.int8)
    return X, y

X_train, y_train = prepare(train)


calendar_groups = [
    ["Month", "SeasonFortnight"],
    ["ThanksgivingWindow"],
    ["ChristmasWindow"],
    ["SummerHolidayWindow"],
]
calendar_features = {feature for group in calendar_groups for feature in group}
interaction_groups = calendar_groups + [
    [feature for feature in X_train.columns if feature not in calendar_features]
]

model = xgb.XGBClassifier(
    n_estimators=600,
    num_parallel_tree=4,
    max_depth=0,
    max_leaves=16,
    grow_policy="lossguide",
    learning_rate=0.05,
    reg_lambda=250,
    reg_alpha=10,
    subsample=0.8,
    colsample_bytree=0.8,
    enable_categorical=True,
    max_cat_threshold=16,
    interaction_constraints=interaction_groups,
    random_state=42,
    n_jobs=-1,
)


class SamplingAverage:
    def __init__(self, template):
        parameters = template.get_params()
        self.models = [
            xgb.XGBClassifier(**parameters),
            xgb.XGBClassifier(**{
                **parameters, "subsample": 0.5,
                "reg_lambda": 156.25, "reg_alpha": 6.25,
            }),
        ]

    def fit(self, X, y, sample_weight=None):
        for estimator in self.models:
            estimator.fit(X, y, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        return np.mean([
            estimator.predict_proba(X) for estimator in self.models
        ], axis=0, dtype=np.float64)

model = SamplingAverage(model)
t0 = time.time()
recency_weights = np.exp2((X_train["Month"].to_numpy() - 12) / 12)
recency_weights /= recency_weights.mean()
model.fit(X_train, y_train, sample_weight=recency_weights)
print(f"Training time: {time.time() - t0:.1f}s")


# Saves {model, prepare} to artifacts/ and scores eval.csv row by row. Keep this call last.
save_and_evaluate(model, prepare)
