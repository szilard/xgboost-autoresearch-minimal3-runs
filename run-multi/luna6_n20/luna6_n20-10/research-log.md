# Research log

## Setup
- Run tag: `oct5`
- Baseline: `b15ec66` (Eval AUC 0.6743)

## Baseline — `b15ec66`
- Ran the starter `train.py` unchanged through `harness.py`.
- Eval AUC: 0.6743; run status: ok (32.1s total).
- Establishes the comparison point for later commits.

## Pre-experiment research and hypothesis
- XGBoost's tuning notes warn that deeper/more complex trees can overfit and say tabular performance often depends on preprocessing; its categorical tutorial explains that partition-based categorical splits can group categories with similar learned outputs ([tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [categorical data](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html)).
- A flight-delay study includes origin–destination pairs and airport-specific trends among its spatial/temporal inputs ([FlightNet-ST study](https://link.springer.com/article/10.1007/s44196-025-00932-2)). Its richer inputs and different model are not directly comparable; it motivates testing spatial interactions available in this dataset.
- **Experiment 1 — exploration, feature engineering.** Hypothesis: a directed `Origin→Dest` categorical feature will expose route-specific delay propensity directly, instead of requiring the depth-6 trees to compose separate origin and destination splits. Train has 4,290 distinct directed routes, so sparse-route overfit is a risk. Fit route levels once from `train`; compute each row's route from its own origin and destination in `prepare(df)`, with no row aggregation.

## Experiment 1 result — `042b6f1`
- Eval AUC: 0.6667 (baseline: 0.6743); status: ok, discarded.
- The explicit directed route category did not improve generalization and increased evaluation time from 30.6s to 47.1s. The 4,290 train routes are likely too sparse for this representation, or origin/destination splits already capture the useful signal.

## Experiment 2 hypothesis
- **Classification:** exploration, hyperparameter regularization.
- Based on XGBoost's tuning notes, which recommend `subsample` and `colsample_bytree` as randomness controls for robustness ([XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). Test both at 0.8, holding the baseline feature set, depth, learning rate, tree count, and seed fixed. Hypothesis: moderate row/column sampling can reduce overfit to the 2005 training sample and improve the year-shifted 2006 AUC.

## Experiment 2 result — `2ab6a58`
- Eval AUC: 0.6777 (previous kept: 0.6743); status: ok, keep.
- At 0.8 row and column sampling, the model improved by 0.0034 with baseline features/tree depth. This supports the hypothesis that moderate randomness helps across the year shift; evaluation time remained 30.5s.

## Experiment 3 hypothesis
- **Classification:** follow-up to the promising subsampling result.
- XGBoost's tuning notes frame `max_depth` as a complexity control and caution that more complex trees need more data ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). With 0.8 row/column sampling now kept, lower `max_depth` from 6 to 4 while holding all other settings fixed. Hypothesis: a smaller interaction budget may improve generalization from 2005 to 2006.

## Experiment 3 result — `b42aea2`
- Eval AUC: 0.6790 (previous kept: 0.6777); status: ok, keep.
- Reducing depth from 6 to 4 on top of 0.8 subsampling improved AUC by 0.0013; evaluation remained 30.5s. This supports limiting tree complexity on the year-shifted split.

## Experiment 4 hypothesis
- **Classification:** follow-up to the current best (`b42aea2`).
- XGBoost's tuning notes recommend reducing the step size `eta` while increasing boosting rounds ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). Change `learning_rate` from 0.1 to 0.05 and `n_estimators` from 100 to 200, leaving depth 4 and both 0.8 sampling rates fixed. Hypothesis: finer boosting steps may reach a better generalizing model at roughly comparable total shrinkage.

## Experiment 4 result — `061b357`
- Eval AUC: 0.6799 (previous kept: 0.6790); status: ok, keep.
- Doubling trees while halving the learning rate added 0.0009 AUC; run time stayed 32.4s. The smoother schedule is currently best.

## Experiment 5 hypothesis
- **Classification:** follow-up to the current best (`061b357`), regularization.
- XGBoost documents `min_child_weight` as the minimum Hessian weight for a child and says larger values make the algorithm more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Set it to 5 (default 1), leaving the kept depth-4, 200-tree, 0.05-rate, 0.8-sampling setup fixed. Hypothesis: blocking low-support leaves will reduce noise in the airport and calendar categories.

## Experiment 5 result — `2fcdaf8`
- Eval AUC: 0.6802 (previous kept: 0.6799); status: ok, keep.
- Raising `min_child_weight` to 5 improved AUC by 0.0003; evaluation remained 30.8s. The current best combines reduced depth, moderate sampling, slower boosting, and minimum child weight 5.

## Experiment 6 hypothesis
- **Classification:** exploration, categorical split strategy.
- XGBoost's categorical guide distinguishes equality-based one-hot splits from partition splits, while `max_cat_to_onehot` selects which strategy applies by category count ([categorical data](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Set the threshold to 8. Of the baseline categorical columns, only `DayOfWeek` (7 levels) should switch to one-hot splits; larger features stay partitioned. Hypothesis: day-specific effects may be easier to express as equality tests than grouped weekday partitions. Keep all other settings fixed.

## Experiment 6 result — `c5c5cef`
- Eval AUC: 0.6790 (previous kept: 0.6802); status: ok, discarded.
- Raising `max_cat_to_onehot` to 8 to change weekday splits reduced AUC by 0.0012; the default categorical partitioning remains preferable here.

## Experiment 7 hypothesis
- **Classification:** exploration, temporal feature engineering.
- A flight-delay study highlights scheduled departure time blocks and airport-specific trends ([FlightNet-ST study](https://link.springer.com/article/10.1007/s44196-025-00932-2)). The training data contains all 24 scheduled departure hours. Add a train-fitted `DepHour` categorical feature (hour extracted from `CRSDepTime`) while retaining the original time and all current-best model settings. Hypothesis: hour-level categories can express non-contiguous time-of-day effects and interactions with carrier/airport, using 24 levels rather than the sparse 4,290 route levels that hurt.

## Experiment 7 result — `38b27b0`
- Eval AUC: 0.6796 (previous kept: 0.6802); status: ok, discarded.
- Adding the 24-level scheduled-hour category did not improve AUC and raised evaluation time from 30.8s to 35.4s. The baseline numeric `CRSDepTime` representation is more effective here.

## Experiment 8 hypothesis
- **Classification:** follow-up to the promising subsampling result; isolate column sampling.
- XGBoost defines `colsample_bytree` as the fraction of columns considered for each tree ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). The first sampling trial changed rows and columns together; now lower only `colsample_bytree` from 0.8 to 0.6 while holding `subsample=0.8` and all other current-best settings fixed. Hypothesis: stronger per-tree feature diversity may improve year-shift generalization; isolating this control will show whether feature sampling helped the original gain.

## Experiment 8 result — `335f025`
- Eval AUC: 0.6808 (previous kept: 0.6802); status: ok, keep.
- Isolating per-tree column sampling at 0.6 improved AUC by 0.0006, supporting a benefit from stronger feature diversity. Evaluation time remained 30.7s.

## Experiment 9 hypothesis
- **Classification:** follow-up to the positive column-sampling result.
- AUC rose when `colsample_bytree` moved from 0.8 to 0.6. Lower it to 0.4, holding row sampling at 0.8 and all other current-best settings fixed. Hypothesis: further tree diversity may help the year shift; with only eight input columns, using roughly three per tree may instead underfit. This tests the next regularization level on the same documented control.

## Experiment 9 result — `393a45b`
- Eval AUC: 0.6790 (previous kept: 0.6808); status: ok, discarded.
- Reducing `colsample_bytree` from 0.6 to 0.4 dropped AUC by 0.0018, suggesting the stronger feature sampling began to underfit. Keep 0.6 as the current setting.

## Experiment 10 hypothesis
- **Classification:** follow-up to the kept subsampling result; isolate row sampling at the best column fraction.
- XGBoost describes `subsample` as the per-iteration fraction of training instances and notes it can prevent overfitting ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Lower only `subsample` from 0.8 to 0.6, keeping `colsample_bytree=0.6` and all other current-best settings fixed. Hypothesis: more row-level randomness may further reduce reliance on 2005-specific patterns; excessive sampling noise could instead hurt.

## Experiment 10 result — `bc936d9`
- Eval AUC: 0.6787 (previous kept: 0.6808); status: ok, discarded.
- Lowering row sampling from 0.8 to 0.6 with column sampling fixed at 0.6 reduced AUC by 0.0021. Keep row sampling at 0.8.

## Synthesis after 10 experiments
- **Current best:** `335f025`, Eval AUC 0.6808 versus baseline 0.6743.
- **What helped:** 0.8 row/column sampling (+0.0034), depth 4 (+0.0013), 200 trees at learning rate 0.05 (+0.0009), `min_child_weight=5` (+0.0003), and `colsample_bytree=0.6` (+0.0006). These results support a less complex, more randomized model for the 2005-to-2006 shift.
- **What did not:** the 4,290-level route category, weekday one-hot threshold, and 24-level departure-hour category all lost AUC; the latter two also cost more evaluation time. `colsample_bytree=0.4` and `subsample=0.6` lost, suggesting too much sampling loses useful signal.
- **Current theory:** most gains so far come from controlling model variance. Hand-built category expansions have not helped, but a cyclic numeric representation may communicate adjacency across period boundaries more directly. Scikit-learn's time-feature guide shows sine/cosine encodings for periodic features and periodic splines to avoid a discontinuity at the cycle boundary ([cyclical feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)). XGBoost's interaction-constraint tutorial also notes that unconstrained tree interactions can fit spurious relationships ([feature interaction constraints](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html)).
- **Next:** test train-fitted sine/cosine month features as a row-local seasonal encoding; preserve all current-best settings. If useful, compare other periodic fields separately. If not, explore XGBoost interaction or tree-growth controls.

## Experiment 11 hypothesis
- **Classification:** exploration, periodic temporal feature engineering.
- Scikit-learn's time-feature guide shows paired sine/cosine encodings for periodic values and explains that they remove the artificial gap between cycle endpoints ([cyclical feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)). Flight-delay research also uses month and schedule features ([FlightNet-ST study](https://link.springer.com/article/10.1007/s44196-025-00932-2)). Add `MonthSin`/`MonthCos` derived directly from each row's month, retaining the original categorical month, and hold all model parameters fixed at the best. Hypothesis: the continuous cycle coordinates help trees share seasonal patterns around December/January.

## Experiment 11 result — `ea78ce0`
- Eval AUC: 0.6811 (previous kept: 0.6808); status: ok, keep.
- Adding monthly sine/cosine features improved AUC by 0.0003; evaluation time rose from 30.7s to 35.6s. The cyclic representation adds a small signal while remaining within the harness limit.

## Experiment 12 hypothesis
- **Classification:** follow-up to the positive cyclic-month feature experiment.
- The same cyclical-feature guidance applies to weekdays (period 7), and delay studies include day-of-week effects ([scikit-learn cyclical feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), [FlightNet-ST study](https://link.springer.com/article/10.1007/s44196-025-00932-2)). Add sine/cosine encodings of `DayOfWeek` while retaining its native categorical column and the month cycle. Hypothesis: wraparound adjacency and smooth weekly structure may provide useful signal beyond the weekday category; all model parameters stay fixed.

## Experiment 12 result — `99f984b`
- Eval AUC: 0.6807 (previous kept: 0.6811); status: ok, discarded.
- Adding the weekly sine/cosine pair lowered AUC by 0.0004 and raised evaluation time to 39.9s. Keep the original weekday category without cyclic expansion.

## Experiment 13 hypothesis
- **Classification:** ablation/simplification of the positive monthly-cycle feature.
- `MonthSin`/`MonthCos` improved AUC while the original native month category remained. Remove only the categorical `Month` column from the model inputs, preserving the two row-derived cyclic features and all other settings. Hypothesis: the pair may carry the seasonal signal more compactly and avoid redundant representations; this ablation will determine whether the original category is still useful.

## Experiment 13 result — `bd5723a`
- Eval AUC: 0.6820 (previous kept: 0.6811); status: ok, keep.
- Removing native categorical `Month` while retaining `MonthSin`/`MonthCos` improved AUC by 0.0009 and reduced evaluation time from 35.6s to 31.9s. The cyclic representation is more useful here without the redundant category.

## Experiment 14 hypothesis
- **Classification:** ablation/simplification of the weekly-cycle feature.
- Month sine/cosine encoding helped only after removing the original month category (`bd5723a`), while adding weekday sine/cosine alongside the weekday category slightly hurt (`99f984b`). Remove `DayOfWeek` from categorical inputs and retain its sine/cosine pair, keeping all other features/model settings fixed. Hypothesis: the category may mask or duplicate the periodic geometry, as with month; the replacement may help or may lose day-specific behavior.

## Experiment 14 result — `c7d56cb`
- Eval AUC: 0.6814 (previous kept: 0.6820); status: ok, discarded.
- Replacing native categorical weekday with sine/cosine encodings lowered AUC by 0.0006. Keep the native weekday category and month cycles.

## Experiment 15 hypothesis
- **Classification:** exploration, tree-growth strategy.
- XGBoost documents `grow_policy="lossguide"` as adding nodes at the highest loss change and `max_leaves` as a leaf cap; lossguide is supported by `hist`/`approx` tree methods ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Replace depth-wise depth 4 with `grow_policy="lossguide"`, `max_depth=0`, and `max_leaves=16`, roughly matching the 16-leaf capacity of a full depth-4 tree while allowing asymmetric shapes. Hypothesis: allocating the same approximate leaf budget to higher-value splits may improve AUC.

## Experiment 15 result — `3fe2097`
- Eval AUC: 0.6826 (previous kept: 0.6820); status: ok, keep.
- Loss-guided growth with `max_leaves=16` improved AUC by 0.0006; evaluation time was 31.7s. The adaptive tree shape is promising.

## Experiment 16 hypothesis
- **Classification:** follow-up to promising loss-guided growth.
- The 16-leaf loss-guided model improved over depth-wise growth. Increase only `max_leaves` from 16 to 24, retaining `grow_policy="lossguide"`, `max_depth=0`, and all other best settings. Hypothesis: a modest extra leaf budget may capture additional useful interactions; greater capacity may overfit. XGBoost documents `max_leaves` as the node/leaf cap for this growth control ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).

## Experiment 16 result — `27fff39`
- Eval AUC: 0.6813 (previous kept: 0.6826); status: ok, discarded.
- Raising the loss-guided cap from 16 to 24 reduced AUC by 0.0013, consistent with overfitting at the larger capacity. Restore the 16-leaf version.

## Experiment 17 hypothesis
- **Classification:** follow-up to the loss-guided leaf-budget results.
- The 16-leaf cap improved over depth-wise growth, while 24 leaves hurt. Test an intermediate cap of 12 with all other current-best settings fixed. Hypothesis: 12 leaves may preserve adaptive loss-guided allocation while limiting the excess capacity seen at 24.

## Experiment 17 result — `03724b1`
- Eval AUC: 0.6819 (previous kept: 0.6826); status: ok, discarded.
- The 12-leaf cap was below the 16-leaf best, so the observed capacity optimum remains at 16 among tested caps.

## Experiment 18 hypothesis
- **Classification:** follow-up regularization of the current loss-guided best.
- XGBoost defines `gamma` as the minimum loss reduction required for a new split, with larger values making the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Set `gamma=1.0` while holding the 16-leaf loss-guided structure and other settings fixed. Hypothesis: refusing marginal splits may improve year-shift generalization; an overly high threshold may suppress useful interactions.

## Experiment 18 result — `bca3d61`
- Eval AUC: 0.6826 (previous kept: 0.6826); status: ok, discarded.
- `gamma=1.0` tied the best to four decimals but added a parameter and did not improve speed, so it fails the keep rule. No measurable benefit at this threshold.

## Experiment 19 hypothesis
- **Classification:** follow-up regularization of the current best.
- XGBoost's parameter reference defines `reg_lambda` as L2 regularization on leaf weights and notes that larger values make the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Set `reg_lambda=5` instead of the default 1, holding the 16-leaf loss-guided model and all other settings fixed. Hypothesis: shrinking leaf scores may improve robustness across the year shift without changing the learned split budget.

## Experiment 19 result — `055f214`
- Eval AUC: 0.6824 (previous kept: 0.6826); status: ok, discarded.
- Increasing `reg_lambda` to 5 lowered AUC by 0.0002 and slightly increased evaluation time. Keep the default L2 value for now.

## Experiment 20 hypothesis
- **Classification:** follow-up to the L2 regularization trial.
- `reg_lambda=5` was slightly worse than the default. Test `reg_lambda=0.5` instead, holding the current best tree/feature settings fixed. Hypothesis: the low-complexity, min-child-constrained model may benefit from less leaf shrinkage; a loss would support keeping the default. The parameter remains within XGBoost's documented non-negative range ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).

## Experiment 20 result — `c7335d8`
- Eval AUC: 0.6814 (previous kept: 0.6826); status: ok, discarded.
- Reducing `reg_lambda` to 0.5 dropped AUC by 0.0012. Together with the value 5 result, this supports keeping XGBoost's default L2 strength.

## Synthesis after 20 experiments
- **Current best:** `3fe2097`, Eval AUC 0.6826 versus baseline 0.6743.
- **What helped:** moderate row/column sampling, lower tree complexity, smaller learning rate with more rounds, a month cycle without redundant native `Month`, and loss-guided growth with 16 leaves. A 12- or 24-leaf cap was worse; gamma and L2 tweaks did not help.
- **What did not:** route and scheduled-hour categories, weekday cyclic encoding, stronger sampling, and non-default L2 strength.
- **New research:** scikit-learn defines target encoding as smoothed per-category target means and warns that fitting then transforming the same training rows can leak labels; its encoder cross-fits training encodings to prevent this ([TargetEncoder docs](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). A flight on-time study reports airport-specific patterns and finds historical airline delay rates predictive ([airport OTP study](https://arxiv.org/abs/2601.00875)).
- **Next:** test a smoothed `OriginDelayRate` lookup fitted only on `train.csv`. For training rows use leave-one-out values so each flight's own label is excluded; for evaluation use the full train-fitted lookup. The rate is the only model feature—row counts will not be added. If it helps, test carrier rate separately.

## Experiment 21 hypothesis
- **Classification:** exploration, train-fitted group statistic.
- Research identifies airport-specific patterns as useful and reports historical airline/flight delay rates among strong predictors ([airport OTP study](https://arxiv.org/abs/2601.00875)). Scikit-learn warns that target means computed on the same training rows can leak labels; its target encoder uses cross-fitting ([TargetEncoder docs](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). Test one numeric `OriginDelayRate` feature, with a global-prior smoothing weight of 100. For each training row, compute a leave-one-out rate so its own label is excluded; evaluation rows look up the full train-fitted rate. Counts are used only inside the smoothed mean formula and are not model inputs. Hold all current-best model settings fixed.

## Experiment 21 result — `5752cae`
- Eval AUC: 0.6008 (previous kept: 0.6826); status: ok, discarded.
- The smoothed leave-one-out origin rate transferred poorly from 2005 to 2006. The feature was row-local and used no evaluation labels, but its airport risk ranking was unstable enough to overwhelm useful model signal. Restore the prior best.

## Experiment 22 hypothesis
- **Classification:** follow-up to the failed airport-rate experiment, changing the group to carrier.
- The airport rate failed across the year shift, but the airport on-time study reports historical airline delay rates among its strongest predictors ([airport OTP study](https://arxiv.org/abs/2601.00875)). Carrier operational differences may be more stable than airport-specific annual conditions. Replace the origin rate with one smoothed `CarrierDelayRate` feature using the same leave-one-out training / full-train evaluation scheme and smoothing weight 100; keep the current-best model settings fixed.

## Experiment 22 result — `dd42c99`
- Eval AUC: 0.6110 (previous kept: 0.6826); status: ok, discarded.
- The smoothed leave-one-out carrier rate also transferred poorly from 2005 to 2006. Together with the origin-rate result, static target-rate lookups are not robust for these labels/splits; abandon this feature family for now.

## Experiment 23 hypothesis
- **Classification:** exploration, periodic schedule feature engineering.
- The raw numeric `CRSDepTime` orders 00:05 far from 23:55 even though those times are ten minutes apart. Scikit-learn's cyclical-feature guide explains that sine/cosine features encode this wraparound without an artificial cycle-boundary jump ([cyclical feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)); flight-delay studies also identify scheduled departure time as predictive ([FlightNet-ST study](https://link.springer.com/article/10.1007/s44196-025-00932-2)). Convert HHMM to minutes after midnight, add sine/cosine with period 1440, retain raw `CRSDepTime`, and keep all current-best model settings fixed. This differs from the failed nominal `DepHour` category by preserving minute-level periodic geometry.

## Experiment 23 result — `a8f4a38`
- Eval AUC: 0.6819 (previous kept: 0.6826); status: ok, discarded.
- Adding minute-level departure-time sine/cosine features alongside raw `CRSDepTime` reduced AUC by 0.0007 and increased evaluation time. Keep the raw time feature without this expansion.

## Experiment 24 hypothesis
- **Classification:** exploration, native categorical split capacity.
- XGBoost documents `max_cat_threshold` as the maximum number of categories considered by partition-based splits, used to limit overfitting ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Raise it to 128 from the default while holding other best settings fixed. Hypothesis: the 283-level origin/destination features may benefit from a larger candidate budget; the higher threshold could instead overfit.

## Experiment 24 result — `d38fcd9`
- Eval AUC: 0.6827 (previous kept: 0.6826); status: ok, keep.
- Raising `max_cat_threshold` to 128 improved AUC by 0.0001. The effect is small but positive; runtime was 32.0s.

## Experiment 25 hypothesis
- **Classification:** follow-up to the small positive categorical-threshold result.
- With `max_cat_threshold=128`, AUC rose by 0.0001. Increase only the threshold to 256, allowing partition-based splits to consider almost all 283 airport categories while retaining `min_child_weight=5`. Hypothesis: additional airport partitions may expose useful groupings; the existing minimum-child constraint may limit the added overfit risk.

## Experiment 25 result — `a075c0d`
- Eval AUC: 0.6821 (previous kept: 0.6827); status: ok, discarded.
- Raising the category threshold from 128 to 256 lowered AUC by 0.0006. Keep 128 as the categorical partition cap.

## Experiment 26 hypothesis
- **Classification:** exploration, numeric split resolution.
- XGBoost documents `max_bin` as the number of discrete bins for continuous features; increasing it can improve split optimality at extra computation cost ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Set `max_bin=512` from the default 256, leaving `max_cat_threshold=128` and all other current-best settings fixed. Hypothesis: finer thresholds may help the scheduled-time and distance signals; they may instead add noise or cost.

## Experiment 26 result — `22d129c`
- Eval AUC: 0.6825 (previous kept: 0.6827); status: ok, discarded.
- Raising `max_bin` to 512 slightly lowered AUC by 0.0002 with no useful speed or score benefit. Keep the default numeric bin count for now.

## Experiment 27 hypothesis
- **Classification:** follow-up to the numeric bin-resolution trial.
- `max_bin=512` was slightly worse than the default 256. Test 128 while retaining `max_cat_threshold=128` and all other best settings. Hypothesis: coarser numeric bins may regularize the two continuous features; they may also remove useful scheduled-time or distance thresholds.

## Experiment 27 result — `b0110e3`
- Eval AUC: 0.6828 (previous kept: 0.6827); status: ok, keep.
- Coarsening `max_bin` to 128 improved AUC by 0.0001; evaluation time was 32.2s. This is the current best.

## Experiment 28 hypothesis
- **Classification:** follow-up to the positive coarser-bin result.
- `max_bin=128` edged the best score up. Lower it to 64, holding `max_cat_threshold=128` and other settings fixed. Hypothesis: further binning may regularize scheduled-time/distance thresholds; it may underfit if their fine detail matters.

## Experiment 28 result — `8e3bdf6`
- Eval AUC: 0.6823 (previous kept: 0.6828); status: ok, discarded.
- Lowering `max_bin` from 128 to 64 removed too much numeric split resolution. Keep 128.

## Experiment 29 hypothesis
- **Classification:** follow-up to the positive minimum-child-weight result.
- `min_child_weight=5` helped earlier, while stronger leaf-weight shrinkage and other regularization did not. Test 3 as a less conservative intermediate value, keeping the current best loss-guided structure, `max_cat_threshold=128`, `max_bin=128`, and other settings fixed. Hypothesis: it may retain most of the small-leaf protection while allowing useful splits.

## Experiment 29 result — `209b19f`
- Eval AUC: 0.6828 (previous kept: 0.6828); status: ok, discarded.
- `min_child_weight=3` tied the best to four decimals and did not simplify or speed up the code, so it fails the keep rule. Retain 5.

## Experiment 30 hypothesis

- **Classification:** parameter tuning, regularization.
- Review: the kept `b0110e3` configuration scores 0.6828; `min_child_weight=5` improved over the earlier value 1, while value 3 tied the current best. XGBoost's parameter documentation says larger minimum child weight makes growth more conservative (reference above). Test 10 with all other settings fixed. Hypothesis: stronger support requirements may suppress noisy airport/category splits and improve the 2005-to-2006 evaluation score.

## Experiment 30 result — `9b20f9f`
- Eval AUC: 0.6828 (previous kept: 0.6828); status: ok, discarded.
- `min_child_weight=10` tied at four decimals and took 32.2s to evaluate, so it does not qualify to keep. Restore 5.

## Experiment 30 research synthesis
- Recent split-resolution trials favor moderate complexity: `max_cat_threshold=128` edged up to 0.6827 and 256 fell to 0.6821; `max_bin=128` edged the best score up to 0.6828, while 64 and 512 were lower. Recent minimum-child-weight trials also bracket a narrow useful region: 3, 5, and 10 all tied at 0.6828, while 5 was the earlier improvement. This aligns with the XGBoost tuning guidance cited above: these controls trade split flexibility against conservative growth. Future tuning should test small changes around kept settings rather than larger jumps.

## Experiment 31 hypothesis
- **Classification:** parameter tuning, split regularization.
- Earlier `gamma=1` tied the best of its time and was discarded. Test a gentler `gamma=0.1` on the current loss-guided, moderately binned model. Hypothesis: a small minimum loss reduction may filter marginal categorical splits without the stronger constraint of 1; keep all other settings fixed.

## Experiment 31 result — `a52f3e3`
- Eval AUC: 0.6828 (previous kept: 0.6828); status: ok, discarded.
- `gamma=0.1` tied at four decimals with no simpler or faster code. Restore the best checkpoint.

## Final summary
- Best checkpoint: `b0110e3` (`max_bin=128`), Eval AUC 0.6828, up from baseline 0.6743.
- The main gains came from moderate sampling and model complexity, slower boosting with more trees, cyclic month features, loss-guided growth capped at 16 leaves, and moderate categorical/numeric split resolution.
- Recent small adjustments to `min_child_weight` and `gamma` did not improve the score. Further work should preserve the kept configuration and test one parameter at a time.
