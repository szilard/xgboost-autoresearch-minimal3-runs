# Research log

## Baseline — `b15ec66`

- Ran the starter model unchanged: 100 trees, depth 6, learning rate 0.1, native categorical features.
- Eval AUC: **0.6743** (`ok`). Training took 0.7s and row-by-row evaluation took 30.7s.
- The baseline commit is the branch's starting commit; `train.py` was unchanged.

## Initial research and experiment plan

- XGBoost's tuning notes describe depth and `min_child_weight` as complexity controls, and row/column subsampling and a lower learning rate as ways to reduce overfitting. They also warn that the useful balance depends on the data. Sources: [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) and [XGBoost tree parameters](https://xgboost.readthedocs.io/en/latest/parameter.html).
- The XGBoost categorical-data guide explains one-hot and partition-based categorical splits. Partitioning can group categories with similar leaf values. Source: [XGBoost categorical data](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html).
- A flight-delay study describes origin-destination links and route-based delay propagation as spatial signals. This supports testing a route identity as a compact interaction of the available origin and destination fields; the study uses additional temporal, weather, and operational inputs, so the relevance here is a hypothesis rather than a directly transferable result. Source: [FlightNet-ST study](https://link.springer.com/article/10.1007/s44196-025-00932-2).
- Read-only inspection of `train.csv` found 283 distinct origins, 283 destinations, and 4,290 unique origin-destination routes.

### Experiment 1 — planned

- **Hypothesis:** A route category may capture route-specific delay structure that separate `Origin` and `Dest` splits do not represent as directly. Native categorical splits can combine route categories, which may help manage the route feature's cardinality.
- **Classification:** exploration (new feature family; no prior route-feature result in this run).
- **Change:** add a train-fitted route-code lookup and derive each row's `Route` category inside `prepare(df)`. Unknown routes map to missing. Keep all starter model parameters unchanged.
- **Guardrail:** the feature uses only that row's origin and destination and a lookup fitted on `train`; it does not aggregate the frame passed to `prepare` or use labels.
- **Result:** commit `659c008`, Eval AUC **0.6667** (`ok`), versus baseline 0.6743. Evaluation took 42.7s and the artifact was 17.4 MB, versus 30.7s and 2.6 MB for baseline. Discarded. The route identity did not generalize as encoded here and added scoring cost; retain only the separate origin and destination fields.

### Experiment 2 — planned

- **Hypothesis:** The train/eval split crosses years, so a less complex model with row and column sampling may generalize better than the starter's depth-6 trees trained on every row and feature.
- **Classification:** exploration (first experiment with this regularization/sampling combination).
- **Change:** keep the baseline features, 100 trees, and learning rate; set `max_depth=4`, `min_child_weight=5`, `subsample=0.8`, and `colsample_bytree=0.8`.
- **Research basis:** XGBoost's tuning notes describe depth and child weight as complexity controls, row/column sampling as noise-robustness controls, and advise tuning for the data rather than assuming a universal best configuration ([tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Result:** commit `33ed01e`, Eval AUC **0.6794** (`ok`), +0.0051 over baseline; training 0.4s, evaluation 30.2s, artifact 0.6 MB. Keep as current best.

### Experiment 3 — planned

- **Hypothesis:** The regularized depth-4 model improved over baseline; depth 5 may recover useful interactions while retaining the other three settings that reduce variance.
- **Classification:** follow-up to experiment 2.
- **Change:** change only `max_depth` from 4 to 5; retain `min_child_weight=5`, `subsample=0.8`, and `colsample_bytree=0.8`.
- **Why this is distinct:** this isolates tree capacity within the winning configuration, rather than repeating the full regularization bundle.
- **Result:** commit `3c11a5e`, Eval AUC **0.6790** (`ok`), below the kept 0.6794. Discard and restore `33ed01e`. Increasing tree depth did not help with the same regularization settings.

### Experiment 4 — planned

- **Hypothesis:** The winning depth-4 model may be able to use smaller local splits if `min_child_weight` is lowered, while the shallower depth and row/column sampling continue to constrain variance.
- **Classification:** follow-up to experiment 2.
- **Change:** change only `min_child_weight` from 5 to 1; retain depth 4 and both sampling rates at 0.8.
- **Research basis:** the XGBoost parameter reference says higher `min_child_weight` is more conservative because it blocks partitions whose child has too little summed Hessian ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Result:** commit `939b3d1`, Eval AUC **0.6790** (`ok`), below the kept 0.6794. Discard and restore `33ed01e`; the less conservative child-weight setting did not recover useful splits.

### Experiment 5 — planned

- **Hypothesis:** Scheduled departure time repeats every 24 hours. Adding sine and cosine features may represent the midnight wrap more naturally than raw `CRSDepTime` alone, while retaining the raw value for threshold-based splits.
- **Classification:** exploration (cyclic temporal feature representation).
- **Change:** derive `DepTimeSin` and `DepTimeCos` inside `prepare(df)` from each row's HHMM scheduled departure time using a 1,440-minute period. Keep the winning model parameters and all existing features.
- **Research basis:** scikit-learn's time-feature example encodes periodic features with sine and cosine at the matching period to avoid a jump between the endpoints; an aviation disruption study also encodes scheduled times as 24-hour periodic vectors ([scikit-learn guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), [flight schedule study](https://www.sciencedirect.com/science/article/pii/S2666827021000517)). This motivates the representation; whether it helps XGBoost ranking is an empirical question.
- **Guardrail:** the values are computed from each row's `CRSDepTime`; no statistics are fitted from the frame passed to `prepare`.
- **Result:** commit `2fbecb8`, Eval AUC **0.6792** (`ok`), below 0.6794. Evaluation took 35.8s versus 30.2s for the kept model. Discard and restore `33ed01e`; the cyclic representation did not improve this XGBoost model.

## Plateau research after experiment 5

- Experiments 3–5 were consecutive small misses (0.6790, 0.6790, 0.6792) against the kept 0.6794, so I paused for targeted research.
- XGBoost's version 3.4.1 source sets `max_cat_threshold` to 64. Its Python API describes the parameter as experimental and says it limits categories considered per partition split to prevent overfitting. Sources: [3.4.1 tree parameters](https://github.com/dmlc/xgboost/blob/v3.4.1/src/tree/param.h), [XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html).
- The XGBoost tuning notes list `max_cat_threshold` with tree-complexity controls. Our existing `Origin` and `Dest` each have 283 categories, so I’ll test a stricter cap to regularize those partitions. The previous explicit route feature hurt, which argues for testing how the existing airport categories are split before adding more high-cardinality identifiers.

### Experiment 6 — planned

- **Hypothesis:** Limiting partition search for the 283-category airport fields may reduce noisy airport splits and improve year-to-year generalization.
- **Classification:** exploration (categorical split regularization, a direction distinct from the prior feature and general tree-regularization trials).
- **Change:** set `max_cat_threshold=32` (from the installed XGBoost 3.4.1 default of 64); keep features and winning depth-4 regularization settings fixed.
- **Research basis:** XGBoost describes this parameter as a categorical overfitting control ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), [3.4.1 Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)).
- **Result:** commit `39efb99`, Eval AUC **0.6790** (`ok`), below 0.6794. Discard and restore `33ed01e`; the stricter cap did not improve generalization.

### Experiment 7 — planned

- **Hypothesis:** The winning model may generalize better with smaller boosting updates. Doubling the number of trees while halving the learning rate keeps a similar overall boosting budget and makes each update less aggressive.
- **Classification:** follow-up to experiment 2's winning model.
- **Change:** change `learning_rate` from 0.1 to 0.05 and `n_estimators` from 100 to 200; keep depth 4, child weight 5, and row/column sampling at 0.8.
- **Research basis:** XGBoost's tuning notes advise reducing `eta` while increasing boosting rounds ([parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `152f3e3`, Eval AUC **0.6802** (`ok`), +0.0008 over the previous best; training 0.8s, evaluation 30.6s, artifact 1.2 MB. Keep as current best.

### Experiment 8 — planned

- **Hypothesis:** With the improved lower-rate schedule, depth 5 may recover useful interactions without the larger per-tree updates that made the earlier depth-5 trial slightly worse.
- **Classification:** follow-up to experiment 7.
- **Change:** change only `max_depth` from 4 to 5; retain 200 trees, learning rate 0.05, child weight 5, and row/column sampling at 0.8.
- **Why this is distinct:** the previous depth-5 result used 100 trees at learning rate 0.1, so this tests depth under the newly improved shrinkage schedule.
- **Result:** commit `33a2d0a`, Eval AUC **0.6811** (`ok`), +0.0009 over the previous best. Keep as current best.

### Experiment 9 — planned

- **Hypothesis:** The lower learning rate and depth-5 model improved at 200 trees; adding 100 more small updates may capture remaining signal without changing the per-tree complexity.
- **Classification:** follow-up to experiment 8.
- **Change:** increase only `n_estimators` from 200 to 300; retain learning rate 0.05 and all other settings.
- **Research basis:** XGBoost's tuning notes pair lower `eta` with an increased boosting-round count ([parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `9cb236b`, Eval AUC **0.6813** (`ok`), +0.0002 over the previous best. Keep as current best.

### Experiment 10 — planned

- **Hypothesis:** The score rose from 0.6811 at 200 trees to 0.6813 at 300, so another 100 trees may add a small amount of useful signal before the lower-rate ensemble saturates.
- **Classification:** follow-up to experiment 9.
- **Change:** increase only `n_estimators` from 300 to 400; retain learning rate 0.05 and all other settings.
- **Decision point:** compare the gain to the 200-to-300 increase to see whether the round-count benefit is flattening.
- **Result:** commit `3b6d61f`, Eval AUC **0.6811** (`ok`), below the kept 0.6813. Discard and restore `9cb236b`; the score flattened and dipped at 400 trees.

## Synthesis after 10 non-baseline experiments

- Best score so far is **0.6813** at `9cb236b`, up 0.0070 from the 0.6743 baseline.
- The largest gain came from moderate tree regularization: depth 4, child weight 5, and 0.8 row/column sampling reached 0.6794. Halving the learning rate while increasing rounds helped further; depth 5 at 0.05/200 reached 0.6811, and 300 trees reached 0.6813. Increasing to 400 trees reduced AUC to 0.6811, suggesting diminishing returns or mild overfit.
- Adding a 4,290-level route category reduced AUC to 0.6667, increased artifact size from 2.6 MB to 17.4 MB, and added evaluation time. The cyclic scheduled-time features and a stricter categorical split cap also failed to improve AUC. Tested depth and child-weight variants around the first kept model were slightly worse.
- Current theory: this year-to-year task benefits most from controlling tree complexity and using smaller boosting steps. Explicit high-cardinality interactions and extra rounds past 300 have not helped. The next research pass should look for a new modeling or flight-schedule feature direction instead of making another small adjustment to the same settings.

## Research after synthesis

- XGBoost's DART guide describes randomly dropping trees during training as a way to reduce overfitting, with the tradeoff of slower training. This remains a candidate for a later model-family experiment ([DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html)).
- A flight-delay study groups scheduled departures into five operational periods (overnight, morning, afternoon, evening, night) and reports different delay patterns across periods. Its dataset contains other features and comes from a separate study, so I will test only the time-block representation on this task ([study](https://arno.uvt.nl/show.cgi?fid=187024), pp. 14–15).

### Experiment 11 — planned

- **Hypothesis:** A low-cardinality time-of-day category may let shallow trees express broad operational-period effects and interactions more directly than raw time alone. The earlier sine/cosine representation did not help, but discrete blocks are a different representation.
- **Classification:** exploration (flight-schedule feature engineering).
- **Change:** derive five `PartOfDay` categories from each row's scheduled HHMM time: 00:00–05:59, 06:00–11:59, 12:00–16:59, 17:00–19:59, and 20:00–23:59. Keep all winning model settings and existing features.
- **Guardrail:** compute the period from each row inside `prepare(df)`; fit only the category levels on `train`.
- **Result:** commit `457bd43`, Eval AUC **0.6800** (`ok`), below 0.6813. Evaluation took 38.9s versus 30.5s for the kept model. Discard and restore `9cb236b`; the extra per-row category work added cost without improving AUC.

### Experiment 12 — planned

- **Hypothesis:** The current boosted tree ensemble may be sensitive to early trees. Dropout during boosting may reduce over-specialization and improve year-to-year AUC.
- **Classification:** exploration (new booster family: DART).
- **Change:** set `booster="dart"`, `rate_drop=0.1`, and `skip_drop=0.5`; keep the winning 300-tree, depth-5, 0.05 learning-rate and sampling settings.
- **Research basis:** XGBoost's DART guide describes tree dropout as an overfitting control and warns that it can train more slowly ([DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html)). The original DART paper motivates dropout by over-specialization and reports experiments on classification, ranking, and regression tasks ([PMLR paper](https://proceedings.mlr.press/v38/korlakaivinayak15.pdf)).
- **Result:** commit `ef4e495`, Eval AUC **0.6803** (`ok`), below 0.6813. Training took 47.7s (versus 2.3s for the kept model); evaluation took 30.5s. Discard and restore `9cb236b`. XGBoost also warned that `booster="dart"` is deprecated and recommends dropout parameters with the tree booster directly; research that API path before retrying.

### Experiment 13 — planned

- **Hypothesis:** Smaller updates may generalize better if paired with more rounds, even though 0.05 learning-rate performance flattened after 300 trees.
- **Classification:** follow-up to experiment 9's winning model.
- **Change:** set `learning_rate=0.03` and `n_estimators=500`; retain depth 5, child weight 5, and both sampling rates at 0.8.
- **Research basis:** XGBoost advises pairing a lower `eta` with an increased round count ([parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `1ad665c`, Eval AUC **0.6804** (`ok`), below 0.6813. Discard and restore `9cb236b`; this lower-rate schedule did not beat 0.05 with 300 trees.

### Experiment 14 — planned

- **Hypothesis:** Some splits in the 300-tree ensemble may fit weak training patterns. Requiring a minimum loss reduction before splitting could improve generalization.
- **Classification:** follow-up to the winning tree model (split regularization).
- **Change:** set `gamma=1`; keep 300 trees, depth 5, learning rate 0.05, child weight 5, and both sampling rates at 0.8.
- **Research basis:** XGBoost defines `gamma` as the minimum loss reduction required for a split; larger values make the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Result:** commit `d551d21`, Eval AUC **0.6813** at four decimals, tied with the best; runtime was 32.7s. Discard and restore `9cb236b`: the marginal timing difference was negligible and the model was no simpler.

### Plateau synthesis after experiments 11–14

- The best remains the 300-tree, depth-5 model at learning rate 0.05 (**0.6813**). More trees (400), a lower learning rate with 500 trees, DART, a time-of-day category, and `gamma=1` all failed to improve it. The gamma trial tied only at printed precision and had effectively unchanged runtime.
- A new, isolated regularization direction is to increase leaf-weight L2 regularization. XGBoost documents `reg_lambda` as defaulting to 1 and says larger values make the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).

### Experiment 15 — planned

- **Hypothesis:** Stronger L2 shrinkage on leaf weights could reduce noisy updates while preserving the winning depth and sampling structure.
- **Classification:** follow-up to the winning tree model (leaf-weight regularization).
- **Change:** set `reg_lambda=5`; retain 300 trees, depth 5, learning rate 0.05, child weight 5, and both sampling rates at 0.8.
- **Research basis:** XGBoost's parameter reference defines `reg_lambda` as L2 regularization and notes that increasing it makes the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Result:** commit `99bc9ba`, Eval AUC **0.6804** (`ok`), below 0.6813. Runtime was 33.1s. Discard and restore `9cb236b`; stronger L2 shrinkage did not improve validation ranking.

### Experiment 16 — planned

- **Hypothesis:** A small L1 penalty may remove weak leaf weights and improve ranking, unlike the stronger L2 penalty tested in experiment 15.
- **Classification:** follow-up to the winning tree model (leaf-weight regularization).
- **Change:** set `reg_alpha=0.1`; retain the winning 300-tree, depth-5 model with learning rate 0.05, child weight 5, and both sampling rates at 0.8.
- **Research basis:** XGBoost defines `reg_alpha` as L1 regularization and says larger values make the model more conservative; its default is 0 ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Result:** commit `b95e450`, Eval AUC **0.6797** (`ok`), below 0.6813. Runtime was 32.7s. Discard and restore `9cb236b`; the L1 penalty reduced validation ranking performance.

### Experiment 17 — planned

- **Hypothesis:** Delay patterns may vary by carrier across seasons. A `CarrierMonth` category could expose that interaction directly while preserving the original carrier and month features.
- **Classification:** feature-engineering experiment (train-fitted categorical interaction).
- **Change:** add a category formed from `UniqueCarrier` and `Month`; fit its levels on train and derive it row-wise for evaluation. Keep the original columns and winning model settings.
- **Research basis:** Flight-delay studies use airline and temporal variables, including month, together ([Wiley study](https://onlinelibrary.wiley.com/doi/10.1155/2024/3385463)). The carrier-by-month category is a hypothesis to model carrier-specific seasonality, not a reported result from that study.
- **Result:** commit `32020dd`, Eval AUC **0.6726** (`ok`), well below 0.6813. Runtime was 40.9s and the artifact grew to 4.5 MB. Discard and restore `9cb236b`; this categorical interaction added complexity without useful signal.

### Experiment 18 — planned

- **Hypothesis:** A binary weekend indicator may let the model pool the two weekend categories directly, capturing a broad schedule/traffic difference with a low-cardinality signal.
- **Classification:** feature-engineering exploration (calendar grouping).
- **Change:** add `IsWeekend` inside `prepare(df)`, true for `DayOfWeek` categories `c-6` and `c-7`; keep the original weekday feature and winning model settings.
- **Research basis:** A flight-delay analysis explicitly examined day-of-week and weekday/weekend groupings ([study](https://doi.org/10.1016/j.ijtst.2022.01.007)). The added binary feature tests whether that grouping helps this XGBoost model.
- **Result:** commit `a7936f9`, Eval AUC **0.6797** (`ok`), below 0.6813. Runtime was 35.6s. Discard and restore `9cb236b`; explicit weekend pooling did not help beyond the native weekday category.

### Experiment 19 — planned

- **Hypothesis:** Exact scheduled departure hour may capture non-monotonic hourly delay peaks that the raw HHMM numeric feature and the earlier coarse time-of-day bins do not express as directly.
- **Classification:** feature-engineering follow-up (scheduled-time representation).
- **Change:** add the derived 0–23 `CRSDepHour` as a native categorical feature in `prepare(df)`; retain raw `CRSDepTime` and the winning model settings.
- **Research basis:** Flight-delay modeling studies engineer hour-of-day bins and identify hourly patterns as relevant ([PLOS One study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0335141)). The exact 24-hour category tests finer granularity than the earlier five-level `PartOfDay` trial.
- **Result:** commit `7e1298f`, Eval AUC **0.6795** (`ok`), below 0.6813. Runtime was 37.0s. Discard and restore `9cb236b`; the finer hour category did not improve the raw scheduled-time feature.

### Experiment 20 — planned

- **Hypothesis:** The winning model uses only eight original features. Restoring `colsample_bytree=1.0` may let every tree retain useful airport and carrier information while row sampling continues to limit variance.
- **Classification:** follow-up to the winning tree model (column-sampling ablation).
- **Change:** set `colsample_bytree=1.0`; retain 300 trees, depth 5, learning rate 0.05, child weight 5, and `subsample=0.8`.
- **Research basis:** XGBoost's tuning notes describe column subsampling as a randomness/overfitting control, so this tests whether the current 0.8 level is too restrictive for this compact feature set ([tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `cc1fb90`, Eval AUC **0.6784** (`ok`), below 0.6813. Runtime was 33.0s. Discard and restore `9cb236b`; removing column sampling weakened performance.

## Synthesis after 20 non-baseline experiments

- Best remains `9cb236b` (**0.6813**), with the original features, 300 trees, depth 5, learning rate 0.05, child weight 5, and row/column sampling at 0.8. That is +0.0070 over the unchanged 0.6743 baseline.
- The gains came from general regularization and the lower learning-rate/round-count schedule. Going to 400 trees flattened the gain. Coarse/fine scheduled-time additions, route and carrier-month categories, a weekend flag, DART, stronger leaf penalties, and full column sampling all underperformed. `gamma=1` tied only at four decimals with no meaningful runtime gain.
- The next search direction is class imbalance and its XGBoost controls; first measure the train-label balance, then consider a single documented weighting parameter rather than more redundant calendar features.

## Research after 20 experiments

- `train.csv` has exactly 100,000 positive and 100,000 negative labels. XGBoost recommends `scale_pos_weight` for imbalance and gives the negative/positive ratio as a typical value; that ratio is 1 here, so class weighting offers no meaningful test. The same guide reserves `max_delta_step` for extreme imbalance ([tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- The untried structural option is loss-guided growth. XGBoost describes `lossguide` as prioritizing nodes with the largest loss change, versus `depthwise` splitting near the root; it requires `hist` or `approx` ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)). This may allocate capacity more selectively than the current symmetric depth cap.

### Experiment 21 — planned

- **Hypothesis:** A loss-guided tree with up to 32 leaves can allocate the same nominal leaf budget as a full depth-5 tree to the branches with the strongest loss reduction, potentially capturing useful asymmetric structure.
- **Classification:** exploration (tree-growth strategy).
- **Change:** use `tree_method="hist"`, `grow_policy="lossguide"`, `max_depth=0`, and `max_leaves=32`; retain 300 trees, learning rate 0.05, child weight 5, and both sampling rates at 0.8.
- **Research basis:** XGBoost documents loss-guided growth as selecting nodes by loss change and supports a maximum leaf count with histogram growth ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Result:** commit `0f090fb`, Eval AUC **0.6801** (`ok`), below 0.6813. Runtime was 33.5s. Discard and restore `9cb236b`; loss-guided growth under this leaf budget did not match the depthwise winner.

## Categorical split research

- XGBoost's native categorical splits can either test equality to one category (one-hot) or partition categories into groups. `max_cat_to_onehot` chooses between them by category count ([categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html), [parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)). The default in the installed-version era favors partitioning for the 283-level airports. Direct airport-specific splits may capture local risk that grouped splits smooth over; higher-cardinality one-hot features can also add overfit and runtime.

### Experiment 22 — planned

- **Hypothesis:** Individual airport effects may be useful enough that forcing one-hot splits for `Origin` and `Dest` improves ranking over partitioning airport codes into groups.
- **Classification:** follow-up to native categorical handling.
- **Change:** set `max_cat_to_onehot=300`; retain the winning features and model parameters.
- **Research basis:** XGBoost says `max_cat_to_onehot` selects one-hot versus partition-based splitting for native categorical features ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Result:** commit `787c199`, Eval AUC **0.6789** (`ok`), below 0.6813. Runtime was 32.7s and artifact size was 0.9 MB. Discard and restore `9cb236b`; one-hot airport splits did not improve the grouped categorical treatment.

### Experiment 23 — planned

- **Hypothesis:** More than 300 boosting rounds may create weak leaves; requiring more training support per split could improve generalization.
- **Classification:** follow-up to the winning model (minimum child-weight regularization).
- **Change:** set `min_child_weight=10`; retain 300 trees, depth 5, learning rate 0.05, and both sampling rates at 0.8.
- **Research basis:** XGBoost defines `min_child_weight` as the minimum Hessian sum in a child and says larger values make the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Result:** commit `1da0eaf`, Eval AUC **0.6803** (`ok`), below 0.6813. Runtime was 32.5s. Discard and restore `9cb236b`; stronger child-weight regularization did not improve the winning setting.

### Experiment 24 — planned

- **Hypothesis:** A modest increase from 80% to 90% row sampling may recover useful examples per tree while retaining some of the variance reduction that made 0.8 sampling part of the winning model.
- **Classification:** follow-up to the winning tree model (row-sampling adjustment).
- **Change:** set `subsample=0.9`; retain 300 trees, depth 5, learning rate 0.05, child weight 5, and `colsample_bytree=0.8`.
- **Research basis:** XGBoost's tuning notes describe subsampling as a way to add randomness and improve robustness against overfitting ([tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `ca52826`, Eval AUC **0.6806** (`ok`), below 0.6813. Runtime was 32.7s. Discard and restore `9cb236b`; 90% row sampling did not beat the winning 80% setting.
