# Research log — oct5

Setup completed on 2026-10-05. The one-hour experiment clock started after confirmation.

## Baseline — b15ec66

- Ran the untouched `train.py` through `harness.py run`.
- Eval AUC: **0.6743**; status: `ok`.
- Establishes the comparison point for all changes.

## Experiment 1 — cyclic schedule features (exploration)

**Hypothesis:** paired sine/cosine encodings of scheduled departure time, month, and weekday will make periodic proximity explicit to the trees, especially at midnight, year-end, and week boundaries. Keep the original raw and categorical features so this is a feature addition, not a replacement.

**Research:** scikit-learn's time-related feature engineering example explains that paired trigonometric features avoid the discontinuity between the end and start of periodic ranges: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html. XGBoost's categorical-data guide documents categorical one-hot and partition-based splits, which remain available alongside these numeric encodings: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html.

**Implementation:** decode `CRSDepTime` from HHMM to minutes since midnight; parse `Month` and `DayOfWeek` from their observed `c-N` strings; add one sine/cosine pair for each period (1440 minutes, 12 months, 7 weekdays). All features are computed row-wise in `prepare`.

**Result:** pending.

- **Result:** Eval AUC **0.6734** (`ok`), below the 0.6743 baseline; discarded by the keep rule. The cyclic features did not improve this tree setup as added.

## Experiment 2 — directed route category (exploration)

**Hypothesis:** a native categorical key for `Origin → Dest` will expose a stable directional-route effect that separate origin and destination features cannot express as compactly. This is an inference from flight-delay studies that find airport/flight context informative; no route-specific rate is fitted from the labels, and no evaluation rows contribute to the lookup.

**Research:** the XGBoost parameter guide describes `max_cat_to_onehot` and `max_cat_threshold`, which govern how categorical features are split and limit category consideration to control overfitting: https://xgboost.readthedocs.io/en/stable/parameter.html. A departure-delay study uses flight information and airport situational-awareness features, finding airport context important: https://arxiv.org/abs/1911.01605.

**Implementation:** create train-fitted route levels (4,290 directed routes) and add the route as a native categorical column. Keep the existing airport and carrier features and XGBoost settings.

**Result:** pending.

- **Result:** Eval AUC **0.6667** (`ok`), substantially below the 0.6743 baseline; discarded. The 4,290-level route category did not generalize well to the following year's evaluation set and may have added noisy high-cardinality splits.

## Experiment 3 — shallower trees (follow-up to baseline)

**Hypothesis:** reducing `max_depth` from 6 to 4 will reduce spurious interactions and improve generalization from the 2005 training sample to the 2006 evaluation set.

**Research:** XGBoost's parameter guide states that increasing `max_depth` increases model complexity and makes overfitting more likely: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** change only `max_depth` (6 → 4); leave all feature preparation and other hyperparameters at baseline.

**Result:** pending.

- **Result:** Eval AUC **0.6789** (`ok`), above the 0.6743 baseline; kept `550a8c4`. This supports the hypothesis that reducing tree complexity helps this year-ahead split.

## Experiment 4 — test depth 3 (follow-up to `550a8c4`)

**Hypothesis:** if the depth-4 improvement came from reducing overfit interactions, a further step to depth 3 may help; the direct comparison isolates tree depth.

**Research:** follows the XGBoost complexity guidance already consulted for Experiment 3: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** change only `max_depth` (4 → 3).

**Result:** pending.

- **Result:** Eval AUC **0.6798** (`ok`), above depth 4's 0.6789; kept `875ca90`. The improvement is small but qualifies under the four-decimal keep rule.

## Experiment 5 — test depth 2 (follow-up to `875ca90`)

**Hypothesis:** a further reduction in tree complexity may improve cross-year generalization, though depth 2 may begin to underfit.

**Research:** continued follow-up based on XGBoost's guidance that greater depth increases complexity and overfit risk: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** change only `max_depth` (3 → 2).

**Result:** pending.

- **Result:** Eval AUC **0.6751** (`ok`), below depth 3's 0.6798; discarded. Depth 2 appears too shallow; depth 3 remains best.

## Experiment 6 — smaller learning rate with twice the rounds (follow-up to `875ca90`)

**Hypothesis:** smaller per-tree updates may rank more smoothly on the 2006 distribution while 200 trees preserve adequate model capacity.

**Research:** XGBoost's tuning notes recommend reducing `eta` to control overfit and increasing `num_round` when doing so: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** keep depth 3 and set `learning_rate=0.05`, `n_estimators=200` (from 0.1 and 100).

**Result:** pending.

- **Result:** Eval AUC **0.6807** (`ok`), above `875ca90`'s 0.6798; kept `cea9349`. Smaller updates with twice the rounds gave a modest gain.

## Experiment 7 — halve the step size again (follow-up to `cea9349`)

**Hypothesis:** another reduction in `learning_rate`, paired with twice the rounds, may further improve ranking through smoother updates.

**Research:** same XGBoost tuning recommendation as Experiment 6: reduce `eta` for conservatism and increase boosting rounds as compensation: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** keep depth 3; change `learning_rate=0.05`, `n_estimators=200` to `learning_rate=0.025`, `n_estimators=400`.

**Result:** pending.

- **Result:** Eval AUC **0.6803** (`ok`), below `cea9349`'s 0.6807; discarded. The second step-size reduction did not help further.

## Experiment 8 — row subsampling (exploration)

**Hypothesis:** sampling 80% of training rows per tree may reduce dependence on noisy 2005-specific patterns and improve generalization to 2006.

**Research:** XGBoost's tuning notes describe `subsample` and `colsample_bytree` as randomness controls that can make training more robust to noise: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** keep `n_estimators=200`, `learning_rate=0.05`, `max_depth=3`; add only `subsample=0.8` (random seed remains fixed at 42).

**Result:** pending.

- **Result:** Eval AUC **0.6787** (`ok`), below `cea9349`'s 0.6807; discarded. Row sampling hurt on this split.

## Experiment 9 — column subsampling (exploration)

**Hypothesis:** allowing each tree to use 80% of columns may reduce reliance on the same noisy predictors and complement depth/learning-rate tuning. Unlike the prior failed row-sampling run, this changes feature sampling only.

**Research:** XGBoost's tuning notes identify `colsample_bytree` as a randomness control for robust training: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** keep the `cea9349` model and add only `colsample_bytree=0.8`; no row subsampling.

**Result:** pending.

- **Result:** Eval AUC **0.6809** (`ok`), slightly above `cea9349`'s 0.6807; kept `ae06c37`. Feature sampling helped marginally while row sampling hurt.

## Experiment 10 — stronger column subsampling (follow-up to `ae06c37`)

**Hypothesis:** lowering `colsample_bytree` from 0.8 to 0.6 may increase the robustness benefit of feature sampling; the prior 0.8 setting gave a small gain.

**Research:** the XGBoost parameter guide defines `colsample_bytree` as the fraction of columns sampled per tree: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** change only `colsample_bytree` (0.8 → 0.6).

**Result:** pending.

- **Result:** Eval AUC **0.6799** (`ok`), below 0.8's 0.6809; discarded. Stronger column sampling erased the small benefit.

## Synthesis after Experiment 10

- **Current best:** Eval AUC **0.6809**, commit `ae06c37` (`max_depth=3`, `learning_rate=0.05`, `n_estimators=200`, `colsample_bytree=0.8`).
- **What helped:** reducing depth from 6 to 3 gave the largest gain (0.6743 → 0.6798); halving the learning rate while doubling rounds added 0.0009; moderate column sampling added another 0.0002.
- **What did not:** sine/cosine time encodings and a 4,290-level route category lowered AUC. Depth 2 underfit. A second step-size reduction, row subsampling, and stronger column subsampling also reduced AUC.
- **Current theory:** generalization across years favors simpler, more conservative trees. The small benefit from `colsample_bytree=0.8` suggests feature-level regularization can help, while aggressive or row-level randomness removes useful signal. Hand-built periodic and route features have not added stable signal.
- **Next direction:** research supervised group-propensity encodings or native categorical split controls, with careful safeguards against training-label leakage and train/eval row-wise feature mismatch.

## Experiment 11 — one-hot splits for smaller categorical fields (exploration)

**Hypothesis:** individual one-hot category tests may work better than partitioned splits for Month (12 levels), DayofMonth (31), DayOfWeek (7), and UniqueCarrier (20), while Origin and Dest (283 each) remain partitioned.

**Research:** XGBoost documents `max_cat_to_onehot` as the threshold selecting one-hot versus partition-based categorical splits: https://xgboost.readthedocs.io/en/stable/parameter.html. scikit-learn's target-encoding guidance shows why label-derived category encodings require cross-fitting to prevent leakage; I defer that route and test the native categorical control instead: https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html.

**Implementation:** keep the best model and set `max_cat_to_onehot=32`, covering the observed categories below 32 levels while leaving the 283-level airport features on partition splits.

**Result:** pending.

- **Result:** Eval AUC **0.6794** (`ok`), below the 0.6809 best; discarded. One-hot splits for the smaller categorical fields did not help.

## Experiment 12 — increase minimum child weight (exploration)

**Hypothesis:** requiring more Hessian mass in each child may suppress noisy low-support splits, especially in airport categories, improving year-ahead generalization.

**Research:** XGBoost's parameter guide defines `min_child_weight` as the minimum sum of instance weight (Hessian) in a child; larger values make partitioning more conservative: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** add only `min_child_weight=5` to the `ae06c37` model.

**Result:** pending.

- **Result:** Eval AUC **0.6809** (`ok`), equal to the best without a simplification or speed gain; discarded under the keep rule.

## Experiment 13 — limit categories considered in partition splits (exploration)

**Hypothesis:** lowering the categorical split candidate limit may regularize the high-cardinality airport fields (283 levels each) without changing their representation or affecting small categories.

**Research:** XGBoost documents `max_cat_threshold` as the maximum number of categories considered per partition-based split, for preventing overfitting: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** keep `ae06c37` settings and set `max_cat_threshold=32`.

**Result:** pending.

- **Result:** Eval AUC **0.6777** (`ok`), well below the 0.6809 best; discarded. The 32-category limit was too restrictive for this representation.

## Experiment 14 — require positive split gain (exploration)

**Hypothesis:** `gamma=1.0` may remove low-value splits and reduce noise without restricting categorical partitions as much as `max_cat_threshold=32` did.

**Research:** XGBoost documents `gamma` (`min_split_loss`) as the minimum loss reduction required for another tree partition; larger values make the model more conservative: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** add only `gamma=1.0` to the `ae06c37` settings.

**Result:** pending.

- **Result:** Eval AUC **0.6809** (`ok`), equal to `ae06c37`. The roughly 0.3-second evaluation-time difference is within observed run variation, so there is no clear speed gain; discarded under the keep rule.

## Experiment 15 — increase histogram resolution (exploration)

**Hypothesis:** 512 bins may give the numeric `CRSDepTime` and `Distance` features more precise split candidates than the default 256, at modest training cost.

**Research:** XGBoost documents `max_bin` as the maximum number of discrete bins for continuous features; increasing it can improve split optimality while increasing computation: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** add only `max_bin=512` to `ae06c37`.

**Result:** pending.

- **Result:** Eval AUC **0.6805** (`ok`), below the best; discarded. More numeric split resolution did not help.

## Experiment 16 — carrier-at-origin interaction (exploration)

**Hypothesis:** the carrier/origin pairing may express local airline operations more directly than the separate fields, while its 1,551 levels are much fewer than the 4,290 directed routes that hurt in Experiment 2. The interaction is motivated by delay studies identifying carrier and airport context as useful; whether the pair generalizes is an empirical question.

**Research:** an XGBoost flight-delay study reports departure time and carrier as influential predictors: https://www.sciencedirect.com/science/article/pii/S2772415822000050. A departure-delay study reports significant airport-context factors: https://arxiv.org/abs/1911.01605.

**Implementation:** fit `UniqueCarrier × Origin` levels on `train.csv` and add a native categorical feature with unknown pairs mapped to missing. Preserve the original carrier and origin fields; all feature values are row-local.

**Result:** pending.

- **Result:** Eval AUC **0.6760** (`ok`), below the 0.6809 best; discarded. The 1,551-level carrier/origin interaction did not generalize better than the separate fields.

## Experiment 17 — add 100 trees at the successful step size (follow-up to `ae06c37`)

**Hypothesis:** the 200-tree, 0.05-step model may benefit from additional boosting rounds without the very small 0.025 step size that hurt at 400 trees.

**Research:** XGBoost's tuning guide advises increasing rounds when using a smaller step size; this tests whether 200 rounds are enough at 0.05: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** change only `n_estimators` (200 → 300) from `ae06c37`.

**Result:** pending.

- **Result:** Eval AUC **0.6819** (`ok`), above the prior best 0.6809; kept `ade92c8`. More rounds helped at the 0.05 step size.

## Experiment 18 — continue the tree-count sweep (follow-up to `ade92c8`)

**Hypothesis:** if 300 rounds at learning rate 0.05 improved over 200, 400 rounds may add useful capacity, though overfitting remains possible.

**Research:** follows the earlier XGBoost guidance to tune boosting rounds together with learning rate: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** change only `n_estimators` (300 → 400) at learning rate 0.05 and depth 3.

**Result:** pending.

- **Result:** Eval AUC **0.6815** (`ok`), below 300 trees at 0.6819; discarded. The tree-count trend peaked at 300 in this sweep.

## Experiment 19 — depth 4 with 300 smaller-step trees (follow-up to `ade92c8`)

**Hypothesis:** the depth-4 model may benefit from 300 trees at learning rate 0.05, even though depth 4 at 100 trees scored below depth 3. This tests a depth/round-count interaction.

**Research:** XGBoost's tuning guidance treats tree depth as a complexity control and recommends increasing boosting rounds when lowering the step size: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** from `ade92c8`, change only `max_depth` (3 → 4); keep 300 trees and learning rate 0.05.

**Result:** pending.

- **Result:** Eval AUC **0.6816** (`ok`), below depth 3's 0.6819; discarded. The depth-4 model remained slightly worse at 300 rounds.

## Experiment 20 — remove column subsampling at 300 trees (ablation/simplification)

**Hypothesis:** the `colsample_bytree=0.8` gain may not persist at 300 trees; removing it tests the default full-column model and simplifies the parameter list if AUC is unchanged.

**Research:** XGBoost defines `colsample_bytree` as the fraction of columns sampled to construct each tree: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** remove only the explicit `colsample_bytree=0.8` argument from `ade92c8` (default is 1.0).

**Result:** pending.

- **Result:** Eval AUC **0.6812** (`ok`), below `ade92c8`'s 0.6819; discarded. The modest 0.8 column-sampling benefit persisted with 300 trees.

## Synthesis after Experiment 20

- **Current best:** Eval AUC **0.6819**, commit `ade92c8` (`max_depth=3`, `learning_rate=0.05`, `n_estimators=300`, `colsample_bytree=0.8`).
- **What helped:** reducing depth from 6 to 3, increasing rounds to 300 at learning rate 0.05, and sampling 80% of columns.
- **What did not:** cyclic schedule features, route and carrier/origin interaction categories, low-card one-hot splits, and limiting categorical split candidates. Row subsampling, 400 trees, depth 4 at 300 trees, and removing 0.8 column sampling also reduced AUC.
- **Neutral:** `min_child_weight=5` and `gamma=1` tied at four decimals without a reliable speed gain; higher `max_bin` was worse.
- **Current theory:** the native categorical representation and separate airport/carrier fields are already effective. Extra categorical combinations overfit this 2005→2006 shift. Shallow trees and moderate feature sampling give the clearest gains; the optimal boosting rounds are around 300 at step size 0.05.
- **Next direction:** investigate train-fitted, target-free group summaries of schedule timing (for example, departure-time deviation from the carrier/origin average), which can express useful context without adding a high-cardinality category or using target labels.

## Experiment 21 — scheduled departure hour category (exploration)

**Hypothesis:** an hour-of-day category may capture specific morning/afternoon/evening delay patterns more directly than raw HHMM thresholds or the cyclic sine/cosine representation that did not help.

**Research:** an airport-delay study describes time-of-day as busy/off-busy periods and uses one-hot auxiliary features: https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071. A flight-delay feature-engineering project also extracts the scheduled hour and describes its temporal operational patterns: https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches.

**Implementation:** derive `DepHour = CRSDepTime // 100`, encode fixed levels 0–23 as a native categorical column, and keep the raw departure-time field. The feature is row-local.

**Result:** pending.

- **Result:** Eval AUC **0.6799** (`ok`), below the 0.6819 best; discarded. A 24-level hour category did not improve on raw scheduled time.

## Experiment 22 — busy-hours indicator (follow-up to Experiment 21)

**Hypothesis:** a broad peak-period flag may generalize better than the 24-level hour category and give the shallow trees a direct split for an evening/overnight congestion interval.

**Research:** an airport-delay study groups 18:00–02:00 as a busy period and uses time of day as an auxiliary feature: https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071.

**Implementation:** add a row-wise binary indicator for scheduled hours 18 through 1; retain raw HHMM and all other best-model features.

**Result:** pending.

- **Result:** Eval AUC **0.6807** (`ok`), below the 0.6819 best; discarded. The broad 18:00–02:00 flag did not transfer to this dataset.

## Experiment 23 — four-hour departure blocks (follow-up to Experiments 21–22)

**Hypothesis:** six broad time blocks may capture recurring operating periods with less fragmentation than 24 hour levels and more flexibility than one busy-hours indicator.

**Research:** flight-delay studies use time-of-day and scheduled-hour features to capture operational patterns; the airport-delay study groups the day into broad busy/off-busy intervals: https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071.

**Implementation:** derive `DepTimeBlock = (CRSDepTime // 100) // 4`, encode fixed categories 0–5, and retain raw HHMM.

**Result:** pending.

- **Result:** Eval AUC **0.6812** (`ok`), below the best; discarded. Four-hour blocks did not beat raw scheduled time.

## Experiment 24 — stronger L2 leaf regularization (exploration)

**Hypothesis:** increasing `reg_lambda` may shrink extreme leaf weights and improve robustness under the year shift.

**Research:** XGBoost describes `lambda`/`reg_lambda` as L2 regularization on leaf weights; increasing it makes the model more conservative: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** add only `reg_lambda=5` (default 1) to `ade92c8`.

**Result:** pending.

- **Result:** Eval AUC **0.6806** (`ok`), below the best; discarded. Stronger L2 regularization did not help.

## Experiment 25 — mild L1 leaf regularization (exploration)

**Hypothesis:** a small `reg_alpha` penalty may remove weak leaf weights and improve robustness by a mechanism distinct from L2 shrinkage.

**Research:** XGBoost describes `alpha`/`reg_alpha` as L1 regularization on leaf weights, with larger values making the model more conservative: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** add only `reg_alpha=0.1` (default 0) to `ade92c8`.

**Result:** pending.

- **Result:** Eval AUC **0.6809** (`ok`), equal to the earlier 200-tree best but below the 300-tree best of 0.6819; discarded.

## Experiment 26 — smaller L1 penalty (follow-up to Experiment 25)

**Hypothesis:** `reg_alpha=0.1` reduced AUC; a smaller 0.01 penalty may avoid excessive shrinkage while still suppressing weak leaf weights.

**Research:** follows XGBoost's definition of `reg_alpha` as L1 regularization on leaf weights: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** set only `reg_alpha=0.01` from the `ade92c8` best.

**Result:** pending.

- **Result:** Eval AUC **0.6815** (`ok`), below the best; discarded. A smaller L1 penalty still did not help.

## Experiment 27 — test a smaller 250-tree model (follow-up to the tree-count sweep)

**Hypothesis:** 250 trees may preserve the 300-tree AUC with a smaller and faster artifact, since 200 trees scored lower and 400 trees fell from the peak.

**Research:** follows XGBoost's guidance to tune boosting rounds along with learning rate: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** change only `n_estimators` (300 → 250) from `ade92c8`.

**Result:** pending.

- **Result:** Eval AUC **0.6814** (`ok`), below 300 trees at 0.6819; discarded. The smaller model did not preserve the score.

## Experiment 28 — test 350 trees (follow-up to the tree-count sweep)

**Hypothesis:** 350 rounds may improve on the 300-tree score while avoiding the overfit seen at 400.

**Research:** continued tuning of boosting rounds with fixed learning rate: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** change only `n_estimators` (300 → 350) from `ade92c8`.

**Result:** pending.

- **Result:** Eval AUC **0.6815** (`ok`), below 300 trees at 0.6819; discarded. The 350-tree midpoint did not improve the peak.

## Experiment 29 — smaller steps at matched total step size (follow-up to the learning-rate sweep)

**Hypothesis:** `learning_rate=0.04` with 375 trees has a similar cumulative step size to 0.05 × 300, but smaller individual updates may improve ranking.

**Research:** XGBoost's tuning notes recommend reducing `eta` for more conservative updates and increasing rounds to compensate: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html.

**Implementation:** change the pair from 300 trees at 0.05 to 375 trees at 0.04; keep depth 3 and column sampling 0.8.

**Result:** pending.

- **Result:** Eval AUC **0.6808** (`ok`), below the best; discarded. The matched smaller-step configuration did not beat 300 trees at 0.05.

## Experiment 30 — DART dropout booster (exploration after plateau)

**Hypothesis:** dropping a fraction of existing trees during boosting may address over-specialization and improve generalization beyond the best gbtree model.

**Research:** the DART paper describes later boosted trees over-specializing on a few examples and proposes dropout to improve unseen-data performance: https://proceedings.mlr.press/v38/korlakaivinayak15.html. XGBoost documents DART's `rate_drop` control and notes that training can be slower than `gbtree`: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html.

**Implementation:** preserve `ade92c8`'s depth, rounds, learning rate, and column sampling; switch to `booster="dart"` and set `rate_drop=0.1`.

**Result:** pending.

- **Result:** Eval AUC **0.6715** (`ok`), well below the best; discarded. DART with 0.1 dropout was too disruptive for this setup.

## Synthesis after Experiment 30

- **Current best:** Eval AUC **0.6819**, commit `ade92c8`: native gbtree, depth 3, 300 trees, learning rate 0.05, and `colsample_bytree=0.8`.
- **What helped:** shallow trees, 300 rounds at 0.05, and moderate column sampling.
- **What did not:** engineered periodic/hour/block/busy-period features, route and carrier-origin categories, most categorical split changes, stronger regularization, 250/350/400 rounds, and DART dropout.
- **Current theory:** the available schedule and airport/carrier features already carry most of the stable signal. The largest gains came from conservative gbtree complexity and an appropriate round count. Additional engineered interactions and stochastic training changes have generally hurt.
- **Next:** try one alternate tree-building method, then wrap up when the clock approaches the two-minute cutoff.

## Experiment 31 — approximate tree construction (exploration)

**Hypothesis:** the `approx` builder's per-iteration weighted sketch may produce better numeric split candidates than the default histogram method for scheduled time and distance.

**Research:** XGBoost documents `approx` as a quantile-sketch-based approximate method and `hist` as a faster histogram method: https://xgboost.readthedocs.io/en/stable/parameter.html. Its categorical-data guide lists `approx` and `hist` as supported with categorical columns: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html.

**Implementation:** keep `ade92c8`'s features and parameters; add only `tree_method="approx"`.

**Result:** pending.

- **Result:** Eval AUC **0.6818** (`ok`), just below the 0.6819 best; discarded. The approximate builder nearly matched the default but did not beat it.

## Experiment 32 — coarser numeric histograms (follow-up to Experiment 15)

**Hypothesis:** 128 bins may smooth numeric split boundaries and improve generalization after 512 bins performed worse than default.

**Research:** XGBoost's `max_bin` parameter controls continuous-feature histogram resolution; it trades split detail against computation: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** add only `max_bin=128` to `ade92c8`.

**Result:** pending.

- **Result:** Eval AUC **0.6810** (`ok`), below the 0.6819 best; discarded. Coarser bins did not improve the default histogram resolution.

## Experiment 33 — intermediate histogram resolution (parameter tuning)

**Hypothesis:** `max_bin=192` may preserve more useful numeric split detail than 128 bins while reducing histogram granularity relative to the default 256.

**Research:** XGBoost documents `max_bin` as the maximum number of discrete bins for continuous features; the default is 256: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** add only `max_bin=192` to the current best configuration.

**Result:** Eval AUC **0.6816** (`ok`), below the 0.6819 best; discarded. The intermediate bin count did not help.

**Additional check:** XGBoost's tuning guide recommends balancing classes for AUC when labels are imbalanced, but a count of `data/train.csv` shows 100,000 positive and 100,000 negative labels. The suggested ratio is therefore 1.0, identical to the current default, so no class-weight experiment was run. https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html

## Experiment 34 — intermediate column sampling (parameter tuning)

**Hypothesis:** `colsample_bytree=0.9` may retain more candidate features than the best 0.8 setting while keeping some regularization relative to 1.0.

**Research:** XGBoost documents `colsample_bytree` as the fraction of columns sampled per tree: https://xgboost.readthedocs.io/en/stable/parameter.html.

**Implementation:** change only `colsample_bytree` from 0.8 to 0.9.

**Result:** Eval AUC **0.6806** (`ok`), below the 0.6819 best; discarded. The 0.8 column-sampling setting remains better than this intermediate value.

## Final summary

- **Best checkpoint:** `ade92c8`, Eval AUC **0.6819**. Keep native categorical gbtree with depth 3, 300 estimators, learning rate 0.05, and `colsample_bytree=0.8`.
- **Experiments:** 34 nonbaseline attempts completed. The best gains came from shallower trees, 300 rounds at learning rate 0.05, and 0.8 column sampling. Feature engineering, deeper/shallower round-count variations, regularization changes, DART, alternate tree construction, histogram-bin changes, and `colsample_bytree=0.9` did not improve the best score.
- **Next direction:** if continuing, use a fresh validation strategy or investigate carefully justified categorical and schedule features; avoid more tiny parameter nudges on this same evaluation split.

