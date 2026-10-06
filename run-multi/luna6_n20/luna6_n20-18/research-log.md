# Research log

## Baseline — b15ec66

- Result: Eval AUC 0.6743; run completed successfully in 32.0s.
- Hypothesis: Establish the starter model's performance before changing features or hyperparameters.
- Observation: Baseline uses XGBoost's native categorical handling for six categorical columns, two numeric columns, and 100 depth-6 trees at learning rate 0.1.
- Decision: Keep as the reference commit. Before the first non-baseline experiment, research XGBoost tuning and useful categorical/tabular techniques as required by `program.md`.

## Experiment 1 — add departure hour (exploration)

- Hypothesis: `CRSDepTime` is encoded as HHMM. Adding `CRSDepTime // 100` gives the model an explicit hour-of-day signal that may capture hourly delay patterns more directly while retaining the original scheduled-time value.
- Research: Flight-delay studies identify scheduled departure hour/time-of-day as predictive ([Wiley study on flight delay generation and prediction](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057)); XGBoost's tuning guide emphasizes knowing the data and preprocessing ([XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: Add row-wise `DepHour` in `prepare(df)`.
- Result: Eval AUC 0.6751, up from 0.6743 (+0.0008); run completed successfully in 34.4s.
- Decision: Keep `088f052`; the explicit hour feature improved the evaluation score.

## Experiment 2 — add directed route category (exploration)

- Hypothesis: Origin and destination effects may interact; a directed route category gives the model that combination directly.
- Research: Flight-delay studies use route/airport factors ([Wiley study](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057)); XGBoost's categorical splits can partition categories by learned outcome ([categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- Change: Fit route category levels on `train` and map each row's origin-destination pair in `prepare(df)`; unseen routes become missing.
- Result: Eval AUC 0.6673, down from the kept 0.6751 (−0.0078); run completed in 51.4s, with evaluation time rising to 49.2s.
- Decision: Discard `1a97956` and reset to `088f052`. The 4,290-level route category was costly in row-by-row evaluation and hurt AUC.

## Experiment 3 — shallower trees (exploration)

- Hypothesis: Shallower trees may generalize better across the 2005 training to 2006 evaluation shift by limiting feature interactions and leaf specialization.
- Research: XGBoost's parameter guide describes `max_depth` as a direct control on model complexity and overfitting ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: Reduce `max_depth` from 6 to 4; keep the departure-hour feature and other parameters fixed.
- Result: Eval AUC 0.6794, up from 0.6751 (+0.0043); run completed successfully in 33.7s.
- Decision: Keep `3b9c40a`; reducing depth to 4 gave a clear improvement.

## Experiment 4 — reduce depth to 3 (follow-up)

- Hypothesis: The depth-4 gain may continue with still shallower trees, or it may identify depth 4 as the better complexity level.
- Motivation: `3b9c40a` improved AUC by 0.0043 over depth 6.
- Change: Reduce `max_depth` from 4 to 3; keep other settings fixed.
- Result: Eval AUC 0.6803, up from 0.6794 (+0.0009); run completed successfully in 33.7s.
- Decision: Keep `40cbb4f`; reducing depth to 3 improved the score again, though by less than the depth-4 change.

## Experiment 5 — reduce depth to 2 (follow-up)

- Hypothesis: Test whether the improvement from shallower trees continues; if AUC ties, a smaller/faster model could still qualify under the keep rule.
- Motivation: Depth 4 and depth 3 both beat the previous kept commit.
- Change: Reduce `max_depth` from 3 to 2; keep other settings fixed.
- Result: Eval AUC 0.6751, down from the kept 0.6803 (−0.0052); run completed successfully in 33.6s.
- Decision: Discard `288debc` and reset to `40cbb4f`. Depth 2 lost much of the improvement from depth 3.

## Experiment 6 — smaller steps with more rounds (follow-up)

- Hypothesis: A smaller learning rate with more boosting rounds may fit the shallower depth-3 trees more gradually and improve generalization.
- Research: XGBoost's parameter tuning guide recommends reducing the step size while increasing boosting rounds ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: Set `learning_rate=0.05` and `n_estimators=200`; keep `max_depth=3`.
- Result: Eval AUC 0.6800, down from the kept 0.6803 (−0.0003); run completed successfully in 33.8s.
- Decision: Discard `f12939a` and reset to `40cbb4f`. This paired change did not improve the depth-3 model.

## Experiment 7 — double rounds at original learning rate (ablation)

- Hypothesis: The depth-3 model may benefit from more boosting rounds even if the smaller learning rate did not help.
- Motivation: Isolate the tree-count effect from the learning-rate change in `f12939a`.
- Change: Increase `n_estimators` from 100 to 200, retaining `learning_rate=0.1` and `max_depth=3`.
- Result: Eval AUC 0.6811, up from 0.6803 (+0.0008); run completed successfully in 33.7s.
- Decision: Keep `675d861`; 200 trees helped when the original learning rate was retained.

## Experiment 8 — 300 boosting rounds (follow-up)

- Hypothesis: The gain at 200 rounds may continue with a modest increase, or additional trees may overfit.
- Motivation: `675d861` improved Eval AUC by 0.0008 over the 100-tree depth-3 model.
- Change: Increase `n_estimators` from 200 to 300; retain `learning_rate=0.1` and `max_depth=3`.
- Result: Eval AUC 0.6804, down from the kept 0.6811 (−0.0007); run completed successfully in 34.1s.
- Decision: Discard `dc3d1c7` and reset to `675d861`; 300 rounds did not improve over 200.

## Experiment 9 — row subsampling (exploration)

- Hypothesis: Sampling 80% of rows per tree may reduce overfitting to the 2005 training sample and improve transfer to 2006.
- Research: XGBoost's tuning notes identify `subsample` as a randomness-based overfitting control ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: Set `subsample=0.8`; retain depth 3, 200 trees, and learning rate 0.1.
- Result: Eval AUC 0.6791, down from the kept 0.6811 (−0.0020); run completed successfully in 33.9s.
- Decision: Discard `b1301b9` and reset to `675d861`; row subsampling hurt on this dataset.

## Experiment 10 — column subsampling (exploration)

- Hypothesis: Mild feature sampling may reduce dependence on a few predictors, though this model has only nine input columns.
- Research: XGBoost's parameter tuning notes identify `colsample_bytree` as a randomness-based regularization control ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: Set `colsample_bytree=0.8`; leave `subsample` at 1.0 and retain the depth-3, 200-tree model.
- Result: Eval AUC 0.6803, down from the kept 0.6811 (−0.0008); run completed successfully in 33.7s.
- Decision: Discard `af10941` and reset to `675d861`; column sampling also hurt compared with the full feature set.

## Synthesis after 10 experiments

- Best so far: Eval AUC 0.6811 at `675d861` (depth 3, 200 trees, learning rate 0.1), +0.0068 over the 0.6743 baseline.
- What helped: An explicit departure-hour feature improved AUC by 0.0008. Lowering depth from 6 to 4 produced the largest single gain (+0.0043), and depth 3 improved again (+0.0009). Increasing from 100 to 200 trees at learning rate 0.1 added another 0.0008.
- What did not help: A 4,290-level directed route category reduced AUC and lengthened row-by-row evaluation. Depth 2 underfit. Learning rate 0.05 with 200 trees, 300 trees at learning rate 0.1, row subsampling at 0.8, and column subsampling at 0.8 all scored below the best.
- Current theory: Moderate tree complexity transfers better from 2005 to 2006; hour-of-day is a useful direct feature, while route memorization and random sampling are poor fits for this small set of known-in-advance fields.
- Next: Research lower-cardinality calendar/time features and train-fitted encodings that can be applied per row without using evaluation labels or row counts.

### Research update before Experiment 11

- A recent flight-delay study lists day-of-year and departure-hour bins among its engineered calendar features ([study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/)). Since Month and DayofMonth are available here, a day-of-year value is a deterministic, row-wise calendar feature worth testing.
- Scikit-learn's target-encoding guide shows that cross-fitting prevents each training row from encoding itself and warns that full-data fit/transform can overfit ([cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)). Avoid naive target-rate features unless they can be represented without leaking labels or changing `prepare` semantics.
- XGBoost's categorical guide explains that native splits can group categories by learned effect ([categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)); the high-cardinality route trial was still harmful here, so prioritize simpler row-wise features next.

## Experiment 11 — add day of year (exploration)

- Hypothesis: A numeric calendar position lets shallow trees model broad seasonal changes across month boundaries, beyond separate Month and DayofMonth categories.
- Research: A flight-delay feature-engineering study includes day-of-year and departure-hour features ([study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/)). Both the 2005 train year and 2006 eval year are non-leap years, so a fixed non-leap month-offset table preserves the same date meaning.
- Change: Add `DayOfYear` inside `prepare(df)` from row month/day values; no target or row aggregates.
- Initial run (`615d08f`): crash during training because `Month` and `DayofMonth` use string values like `c-11`, so the integer-key month lookup produced an unsupported string feature.
- Repair: Parse the numeric suffixes inside `prepare(df)` and rerun this same feature experiment.
- Result (`b1cad70`): Eval AUC 0.6832, up from 0.6811 (+0.0021); run completed successfully in 39.0s.
- Decision: Keep `b1cad70`; the smooth day-of-year signal improved the calendar features.

## Experiment 12 — carrier by departure hour category (follow-up)

- Hypothesis: Delay patterns by hour may differ by carrier; an explicit carrier-hour feature may capture this with less sparsity than a route interaction.
- Research: A flight-delay feature study reports that late-hour patterns differ by carrier ([Berkeley study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)); XGBoost can partition native categories by learned effect ([categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- Motivation: The route category had 4,290 levels and hurt AUC; this training data has 401 observed carrier-hour combinations (about 499 rows per observed combination on average).
- Change: Fit carrier-hour category levels on `train` and look up each row's combination in `prepare(df)`; unseen combinations become missing.
- Result: Eval AUC 0.6806, down from the kept 0.6832 (−0.0026); run completed successfully in 47.1s, with evaluation time rising to 45.3s.
- Decision: Discard `166afeb` and reset to `b1cad70`; the carrier-hour category hurt despite its lower cardinality than route.

## Experiment 13 — late-night indicator (follow-up)

- Hypothesis: A binary flag for hours 21 through 2 explicitly groups a high-delay window that crosses midnight, which separate hour thresholds represent less directly.
- Research: A flight-delay feature study reports worsening delay patterns from 21:00 to 02:00 ([Berkeley study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)).
- Change: Add row-wise `LateNight` from `DepHour >= 21` or `DepHour <= 2`.
- Result: Eval AUC 0.6832, tied the kept score; run completed in 42.0s, slower than the 39.0s best run.
- Decision: Discard `28d0463`; equal AUC with an extra feature and slower evaluation does not qualify under the keep rule.

### Research update before Experiment 14

- A study on airline disruption management transforms day-of-year and other Gregorian calendar features into periodic sine/cosine vectors ([study](https://www.sciencedirect.com/science/article/pii/S2666827021000517)). A flight-delay prediction paper also says time features are encoded trigonometrically to preserve periodicity ([study](https://www.mdpi.com/2226-4310/8/6/152)).
- The successful numeric `DayOfYear` feature is linear and puts December and January at opposite ends; a sine/cosine pair can represent their seasonal proximity. Test this alongside the retained raw value.

## Experiment 14 — cyclic day-of-year features (follow-up)

- Hypothesis: Sine/cosine of annual phase can make adjacent dates near year-end look nearby while retaining the useful linear day index.
- Research: Airline disruption research uses periodic encodings for day-of-year and other calendar fields ([study](https://www.sciencedirect.com/science/article/pii/S2666827021000517)); another flight-delay study describes trig encoding to preserve periodicity ([study](https://www.mdpi.com/2226-4310/8/6/152)).
- Change: Add `DayOfYearSin` and `DayOfYearCos` from the row's `DayOfYear`.
- Result: Eval AUC 0.6832, tied the kept score; run completed in 42.4s, slower than the 39.0s best run.
- Decision: Discard `ba56037`; the added pair did not improve AUC and increased evaluation time.

## Experiment 15 — remove month/day categorical inputs (ablation)

- Hypothesis: The numeric `DayOfYear` feature may carry enough calendar information to replace separate Month and DayofMonth categories.
- Motivation: `b1cad70` improved AUC by 0.0021 after adding DayOfYear.
- Change: Remove Month and DayofMonth from model inputs while retaining their use to compute DayOfYear inside `prepare(df)`.
- Result: Eval AUC 0.6838, up from 0.6832 (+0.0006); evaluation fell from 37.3s to 29.6s.
- Decision: Keep `dc9842a`; `DayOfYear` replaced the two categories with a simpler, faster representation and slightly improved AUC.

## Experiment 16 — cyclic calendar features after ablation (follow-up)

- Hypothesis: With Month and DayofMonth categories removed, sine/cosine of annual phase may add useful year-end continuity to the remaining DayOfYear feature without as much redundancy.
- Motivation: The earlier cyclic pair tied and slowed evaluation with the categorical date fields still present; the date ablation subsequently improved both AUC and speed.
- Change: Add `DayOfYearSin` and `DayOfYearCos` alongside `DayOfYear`.
- Result: Eval AUC 0.6828, down from the kept 0.6838 (−0.0010); run completed successfully in 35.1s.
- Decision: Discard `6d796f9` and reset to `dc9842a`; cyclic annual terms did not help beyond numeric DayOfYear.

## Experiment 17 — cyclic departure-time features (exploration)

- Hypothesis: A sine/cosine pair derived from minutes after midnight may represent the 24-hour wrap more smoothly than a linear hour or a single late-night flag.
- Research: Airline disruption analysis encodes scheduled departure time as periodic vectors based on a 24-hour clock ([study](https://www.sciencedirect.com/science/article/pii/S2666827021000517)).
- Change: Add `DepTimeSin` and `DepTimeCos` from row-wise minutes after midnight; retain raw `CRSDepTime` and `DepHour`.
- Result: Eval AUC 0.6847, up from 0.6838 (+0.0009); run completed successfully in 36.0s.
- Decision: Keep `7b0bb0f`; the cyclic departure-time pair improved AUC.

## Experiment 18 — depth 4 with engineered time features (follow-up)

- Hypothesis: The day-of-year and cyclic departure-time features may support slightly deeper interactions than the earlier feature set did.
- Motivation: Depth 3 beat depth 4 before these row-wise time features were introduced; the reduced calendar inputs and stronger time representation may shift the preferred complexity.
- Research: XGBoost identifies `max_depth` as a primary control on tree complexity and overfitting ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: Increase `max_depth` from 3 to 4; retain 200 trees, learning rate 0.1, and current features.
- Result: Eval AUC 0.6818, down from the kept 0.6847 (−0.0029); run completed successfully in 36.3s.
- Decision: Discard `cfc0324` and reset to `7b0bb0f`; depth 4 still overfit relative to depth 3 with the updated features.

## Experiment 19 — raise minimum child weight (exploration)

- Hypothesis: Requiring more Hessian weight in each child may prevent weak, poorly supported splits and improve generalization.
- Research: XGBoost describes `min_child_weight` as the minimum sum of instance weight needed for a child; raising it makes the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: Set `min_child_weight=5`; retain depth 3, 200 trees, and learning rate 0.1.
- Result: Eval AUC 0.6849, up from 0.6847 (+0.0002); run completed successfully in 36.3s.
- Decision: Keep `3867890`; the conservative split threshold gave a small improvement.

## Experiment 20 — raise minimum child weight to 10 (follow-up)

- Hypothesis: Stronger split support may extend the modest gain at value 5, or begin to underfit.
- Motivation: `3867890` improved AUC by 0.0002.
- Change: Increase `min_child_weight` from 5 to 10; retain the rest of the best model.
- Result: Eval AUC 0.6848, down from the kept 0.6849 (−0.0001); run completed successfully in 36.3s.
- Decision: Discard `240c74e` and reset to `3867890`; value 5 remains better than 10.

## Synthesis after 20 experiments

- Best so far: Eval AUC 0.6849 at `3867890`, +0.0106 over the 0.6743 baseline. The model uses depth 3, 200 trees, learning rate 0.1, `min_child_weight=5`, explicit departure hour, numeric day-of-year, and cyclic departure-time features; Month and DayofMonth are removed as separate inputs.
- What helped: Shallower trees, 200 rounds at learning rate 0.1, `DayOfYear`, dropping redundant month/day categories, cyclic scheduled departure time, and a modest increase to `min_child_weight=5`.
- What did not: High-cardinality route and carrier-hour categories hurt both AUC and row-by-row speed. Depth 2 underfit; depth 4 lost on the current features. Row/column subsampling, 300 rounds, and lower learning rate did not help. Annual sine/cosine, late-night, and stronger child-weight features did not beat the best.
- Current theory: Compact numeric encodings for schedule and seasonality plus shallow trees generalize best across years. Interactions that add many categorical levels are expensive and noisy.
- Next: Research XGBoost's remaining categorical split and histogram controls, plus simple calendar groupings such as season/weekend that preserve per-row semantics.

### Research update before Experiment 21

- XGBoost documents `max_cat_threshold` as the maximum number of categories considered per partition split, with its purpose being overfit control ([parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html)). This is a possible later tuning direction for Origin/Dest.
- A flight-delay feature-engineering study includes season and weekend groupings to capture broad calendar effects ([study](https://www.mdpi.com/2079-3397/13/24/4910)); test a four-season category as a compact complement to numeric DayOfYear.

## Experiment 21 — add meteorological season category (exploration)

- Hypothesis: A compact four-season category may capture broad calendar shifts or let trees interact season with carrier/airport more directly than a single numeric DayOfYear threshold.
- Research: A flight-delay feature-engineering study adds a season grouping alongside month and day-of-week features ([study](https://www.mdpi.com/2079-3397/13/24/4910)).
- Change: Map each row's month to winter, spring, summer, or fall and pass it as a native categorical feature.
- Result: Eval AUC 0.6842, down from the kept 0.6849 (−0.0007); run completed successfully in 40.3s.
- Decision: Discard `5aa14af` and reset to `3867890`; the season category added cost without improving the calendar representation.

## Experiment 22 — increase categorical split threshold (exploration)

- Hypothesis: Allowing more categories in a partition split may help XGBoost capture useful airport groupings in the 283-level Origin and Dest features.
- Research: XGBoost defines `max_cat_threshold` as the maximum number of categories considered in a partition split, used to control overfitting ([parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: Set `max_cat_threshold=128`; leave the current features and other model parameters fixed.
- Result: Eval AUC 0.6836, down from the kept 0.6849 (−0.0013); run completed successfully in 36.0s.
- Decision: Discard `4700ccd` and reset to `3867890`; widening the category search did not improve the model.

## Experiment 23 — increase histogram resolution (exploration)

- Hypothesis: More histogram bins may expose useful split points in scheduled time, day-of-year, and distance while retaining the model's current regularization.
- Research: XGBoost documents that increasing `max_bin` improves split optimality at additional computation cost ([parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html)).
- Change: Set `max_bin=512`; retain all current features and other hyperparameters.
- Result: Eval AUC 0.6839, down from the kept 0.6849 (−0.0010); run completed successfully in 36.8s.
- Decision: Discard `da0aeab` and reset to `3867890`; finer numeric bins did not improve AUC.

## Experiment 24 — coarser histogram resolution (follow-up)

- Hypothesis: Fewer numeric bins may smooth split choices and reduce sensitivity to small variations in time and distance.
- Motivation: `max_bin=512` fell below the default-bin best model.
- Research: XGBoost's `max_bin` parameter sets the number of discrete buckets for histogram-based tree methods ([parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html)).
- Change: Set `max_bin=128`; keep all other parameters and features fixed.
- Result: Eval AUC 0.6845, down from the kept 0.6849 (−0.0004); run completed successfully in 35.9s.
- Decision: Discard `979d9ed` and reset to `3867890`; both coarser and finer histogram settings lost to the default.

## Experiment 25 — tighten categorical partition limit (follow-up)

- Hypothesis: Limiting category partitions more aggressively may reduce airport-category overfit.
- Motivation: Raising the threshold to 128 reduced AUC, suggesting that deeper category partitions may be noisy.
- Research: XGBoost documents `max_cat_threshold` as a categorical overfit control ([parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: Set `max_cat_threshold=32`; retain all current features and other parameters.
- Result: Eval AUC 0.6837, down from the kept 0.6849 (−0.0012); run completed successfully in 35.9s.
- Decision: Discard `5f675a6` and reset to `3867890`; a tighter category cap also reduced AUC.

## Experiment 26 — minimum split loss (exploration)

- Hypothesis: Requiring a positive loss reduction before splitting may prune weak interactions and improve cross-year generalization.
- Research: XGBoost defines `gamma` (minimum split loss) as the loss reduction required for a further partition; larger values make the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: Set `gamma=1.0`; retain depth 3, 200 trees, and `min_child_weight=5`.
- Result: Eval AUC 0.6849, tied the kept score; evaluation took 34.4s versus 34.7s for `3867890`.
- Decision: Keep `dfccd9c` under the tie rule because scoring was slightly faster at the same four-decimal AUC.

## Experiment 27 — increase gamma to 2 (follow-up)

- Hypothesis: A stronger minimum split-loss requirement may preserve the gamma-1 score while pruning more weak splits, or it may underfit.
- Motivation: `dfccd9c` tied the best AUC and was slightly faster.
- Change: Increase `gamma` from 1 to 2; retain all other parameters and features.
- Result: Eval AUC 0.6849, tied the kept score; evaluation took 34.7s versus 34.4s at gamma 1.
- Decision: Discard `44a4b3b` and reset to `dfccd9c`; stronger gamma was slower without an AUC gain.

## Experiment 28 — increase L2 leaf regularization (exploration)

- Hypothesis: A modestly stronger L2 penalty may shrink noisy leaf scores and improve transfer to 2006.
- Research: XGBoost's parameter reference says increasing `reg_lambda` makes the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: Set `reg_lambda=2.0`; retain `gamma=1.0`, `min_child_weight=5`, and all other settings.
- Result: Eval AUC 0.6840, down from the kept 0.6849 (−0.0009); run completed successfully in 36.3s.
- Decision: Discard `b01379a` and reset to `dfccd9c`; stronger L2 regularization reduced AUC.

## Experiment 29 — remove redundant departure-time inputs (ablation)

- Hypothesis: The cyclic pair may carry enough scheduled-time signal by itself; removing raw HHMM and integer hour may simplify scoring and reduce redundant split opportunities.
- Motivation: Adding the cyclic pair improved Eval AUC by 0.0009 in `7b0bb0f`.
- Research: Airline disruption research uses periodic vectors for scheduled times ([study](https://www.sciencedirect.com/science/article/pii/S2666827021000517)).
- Change: Remove raw `CRSDepTime` and `DepHour` from model inputs; keep `DepTimeSin` and `DepTimeCos` based on the row's HHMM value.
- Result: Eval AUC 0.6843, down from the kept 0.6849 (−0.0006); evaluation was faster at 32.5s.
- Decision: Discard `304e289`; the cyclic pair alone did not replace raw HHMM and hour without an AUC cost.

## Experiment 30 — reduce gamma to 0.5 (follow-up)

- Hypothesis: The gamma-1 model tied the best and was slightly faster; a lower threshold may recover useful splits while retaining some regularization.
- Motivation: `dfccd9c` with gamma 1 tied the best, while gamma 2 tied but was slower.
- Change: Reduce `gamma` from 1 to 0.5; keep all other settings fixed.
- Result: Eval AUC 0.6849, tied the kept score; evaluation took 34.4s, the same as gamma 1.
- Decision: Discard `9c27131`; no AUC or speed improvement over `dfccd9c`.

### Research update after the plateau

- Scikit-learn describes target encoding as a category's shrunk target mean and recommends cross-fitting training encodings to prevent self-target leakage ([cross-fitting guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)). A flight-delay study also describes target encoding airline/airport features ([TU Delft study](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)).
- Try low-cardinality train-fitted carrier/origin/destination delay rates with strong smoothing. These lookups use only `train`; the row counts are only internal to smoothing and are not returned as features. This simple version is not cross-fitted, so it has residual training self-influence and will be discarded unless Eval AUC improves.

## Experiment 31 — smoothed train-fitted delay-rate encodings (exploration)

- Hypothesis: The carrier and airports have stable differences in delay propensity; their smoothed training target rates may provide a useful numeric signal beside native categories.
- Research: Scikit-learn's target encoder shrinks category means toward the global mean and uses cross-fitting to avoid overfitting ([guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)); flight-delay modeling has used target-encoded airline/airport fields ([TU Delft study](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)).
- Change: Fit smoothed delay-rate lookups for carrier, origin, and destination on `train`; look them up per row in `prepare(df)`. Use smoothing strength 200; no evaluation labels or counts are model features.
- Result: Eval AUC 0.6840, down from the kept 0.6849 (−0.0009); evaluation rose to 39.8s.
- Decision: Discard `7ea4842` and reset to `dfccd9c`; the combined smoothed target-rate features hurt and slowed scoring.

## Experiment 32 — isolate carrier delay-rate encoding (ablation)

- Hypothesis: The three-rate experiment may have been hurt by sparse airport estimates; carrier has only 20 categories and substantially more training support, so its rate alone may add stable ordering information.
- Research: Target encoders use smoothed category means, with cross-fitting recommended to reduce self-target leakage ([scikit-learn guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)). Strong smoothing is retained here; carrier rates are fit only on training labels.
- Change: Add only the smoothed carrier delay rate (smoothing 200); remove origin and destination rates.
- Result: Eval AUC 0.6849, tied the kept score; evaluation took 36.5s, slower than the best 34.4s.
- Decision: Discard `8474fe9` and reset to `dfccd9c`; carrier-rate encoding did not meet the tie rule.

### Research update after the plateau

- BTS specifies day-of-week codes as Monday=1 through Sunday=7 ([field definition](https://www.bts.gov/topics/airlines-and-airports/number-26-technical-directive-time-reporting-effective-jan-1-2017)). A flight-delay study includes an explicit Saturday/Sunday indicator to separate weekend traffic patterns ([study](https://www.mdpi.com/2079-3397/13/24/4910)).
- The values in this dataset use the `c-` category prefix, so parse the suffix and map 6/7 to weekend in a stable row-wise feature.

## Experiment 33 — weekend indicator (exploration)

- Hypothesis: Explicitly grouping Saturday and Sunday may capture a shared traffic pattern more directly than asking a shallow tree to group two DayOfWeek categories.
- Research: BTS defines Monday=1 through Sunday=7 ([field definition](https://www.bts.gov/topics/airlines-and-airports/number-26-technical-directive-time-reporting-effective-jan-1-2017)); a flight-delay study uses a weekend feature ([study](https://www.mdpi.com/2079-3397/13/24/4910)).
- Change: Add `IsWeekend` from the row's parsed `DayOfWeek` value (6 or 7).
- Result: Eval AUC 0.6849, tied the kept score; evaluation took 37.7s versus 34.4s.
- Decision: Discard `b52b90a`; equal AUC with slower scoring does not qualify under the keep rule.

## Experiment 34 — weekend-only day-of-week representation (ablation)

- Hypothesis: A single weekend distinction may retain the useful day-group signal while dropping seven-level category handling.
- Motivation: The separate weekend flag tied the best score but was slower alongside the full DayOfWeek category.
- Change: Remove `DayOfWeek` from model inputs and retain a row-wise `IsWeekend` flag for codes 6/7.
- Result: Eval AUC 0.6799, down from the kept 0.6849 (−0.0050); run completed successfully in 35.4s.
- Decision: Discard `b836e46` and reset to `dfccd9c`; weekend-only loses useful day-of-week detail.

## Final summary

- Best Eval AUC: **0.6849** at commit `dfccd9c`, up 0.0106 from the 0.6743 baseline. The branch is restored to this best kept commit.
- Most effective changes: explicit departure hour; reducing tree depth to 3; 200 trees at learning rate 0.1; numeric DayOfYear replacing Month/DayofMonth categories; cyclic departure-time features; `min_child_weight=5`; and `gamma=1` at tied AUC with slightly faster scoring.
- Unhelpful directions: high-cardinality route/carrier-time features, random row/column sampling, extra annual cyclic and season features, raw-time ablation, and most additional regularization/binning variants. Smoothed target-rate lookups did not improve the score.
- Next direction: investigate low-cost, row-wise features such as distance bands or holiday windows; evaluate any target-derived encodings with a leakage-safe training transform before relying on them.
