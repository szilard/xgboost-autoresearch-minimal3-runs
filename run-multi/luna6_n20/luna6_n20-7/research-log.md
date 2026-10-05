# Research log — oct5

## Baseline — commit b15ec66

Ran the untouched starter model: native categorical `XGBClassifier`, 100 trees, depth 6, learning rate 0.1, seed 42. Eval AUC was **0.6743**; status `keep`.

## Pre-experiment research

- The [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frame tree depth and regularization as bias/variance controls and point out that preprocessing can matter as much as parameter tuning. Keep the first experiment focused on one feature change before tuning model capacity.
- The [XGBoost categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents native categorical input and partition-based categorical splits. The installed XGBoost version is 3.4.1; the starter already uses this categorical interface.
- Li et al., [“Generation and prediction of flight delays in air transport”](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057) distinguish airport-local and network effects, and describe temporal, seasonal, airline, and airport factors used in delay prediction. This dataset lacks operational history and weather, so test a static directed-route feature using only its available attributes.
- Read-only inspection of `train.csv`: 200,000 rows, 4,290 directed routes, and 6,588 carrier-route combinations. `CRSDepTime` ranges from 5 to 2359. No counts will be used as model features.

## Experiment 1 hypothesis — proposed before editing

**Classification:** exploration (feature engineering).

Add a directed `Origin→Dest` categorical feature. The current model sees origin and destination separately; a route category gives it a direct split for route-specific risk patterns without requiring it to build that interaction through multiple tree levels. Use category levels fitted on `train`, so unseen evaluation routes become missing. Keep the model parameters unchanged. Also pass categorical values directly to `pd.Categorical`; its declared train categories preserve the current known/unknown behavior while avoiding a per-row `.isin()` over the route level list during row-wise evaluation.

Success criterion: keep only if eval AUC exceeds the previous kept result (0.6743), unless it ties and the implementation is demonstrably faster/simpler.

## Experiment 1 result — commit aa49049

Eval AUC was **0.6667**, below the baseline, so this experiment is discarded. Adding the explicit route category did not help this model on the 2006 evaluation split; the route-level pattern may be too specific or redundant with the separate airport features. The result does not distinguish that from a change in how the categorical features competed for splits. Next, return to the baseline and test time representation separately.

## Experiment 2 hypothesis — proposed before editing

**Classification:** exploration (feature engineering), on top of the last kept baseline.

The raw `CRSDepTime` is HHMM. Add sine and cosine of its correctly decoded minute-of-day, while retaining the raw input. This gives trees an alternate representation where times near midnight are adjacent around the cycle; the scikit-learn [time-related feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) uses a sine/cosine pair for periodic features and notes that the benefit depends on the estimator. This experiment tests that representation without changing the model or removing information. Each feature depends only on its row's scheduled time.

## Experiment 2 result — commit 322d976

Eval AUC was **0.6734**, a small decrease from 0.6743, so the experiment is discarded. Adding the periodic representation while keeping HHMM did not improve the baseline. Return to the baseline before the next experiment.

## Experiment 3 hypothesis — proposed before editing

**Classification:** follow-up (model capacity / parameter tuning) to the baseline.

The [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend reducing the step size together with increasing the number of boosting rounds. Test `learning_rate=0.05` and `n_estimators=200` against the starter's 0.1 and 100, holding all other parameters and features fixed. The paired change gives the booster finer updates at roughly the same learning-rate-times-rounds scale; the 2006 Eval AUC decides whether this helps.

## Experiment 3 result — commit 855b078

Eval AUC was **0.6764**, up from 0.6743. Keep the commit as the new best. The lower learning rate with twice as many rounds improved the 2006 result, supporting a follow-up that tests whether a further increase in rounds helps.

## Experiment 4 hypothesis — proposed before editing

**Classification:** follow-up to promising Experiment 3.

Keep `learning_rate=0.05` and all other model settings fixed, but increase `n_estimators` from 200 to 300. Experiment 3 improved Eval AUC, so more rounds may continue useful learning; if not, this will show that 200 rounds was already at or beyond the better stopping point. Keep only if Eval AUC exceeds the current best 0.6764.

## Experiment 4 result — commit 87783a8

Eval AUC was **0.6743**, below the current best 0.6764, so discard. Increasing from 200 to 300 rounds erased the gain and returned to the baseline score; retain the 200-round setting for subsequent experiments.

## Experiment 5 hypothesis — proposed before editing

**Classification:** follow-up (regularization) to the current best.

With 200 trees at learning rate 0.05 retained, reduce `max_depth` from 6 to 4. The [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe depth as a model-complexity control; shallower trees may generalize better across the 2005-to-2006 split. Keep only if Eval AUC exceeds 0.6764, or ties with a faster run.

## Experiment 5 result — commit 7224585

Eval AUC was **0.6800**, improving on the previous best of 0.6764. Keep this as the new best. The shallower trees improved the year-forward result, so the next experiment will test the intermediate depth 5 at the same learning rate and number of rounds.

## Experiment 6 hypothesis — proposed before editing

**Classification:** follow-up to promising Experiment 5.

Keep 200 trees and learning rate 0.05, but raise `max_depth` from 4 to 5. This tests whether depth 4 reduced complexity too much or whether an intermediate setting retains its generalization gain. Keep only if Eval AUC exceeds 0.6800, or ties with a faster run.

## Experiment 6 result — commit 6ec1b0e

Eval AUC was **0.6775**, below 0.6800, so discard and return to depth 4. The depth 4 configuration remains the best among the tested depths.

## Experiment 7 hypothesis — proposed before editing

**Classification:** follow-up (stochastic regularization) to the current best.

Set `subsample=0.8` while keeping 200 trees, learning rate 0.05, and depth 4 unchanged. The [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify row subsampling as a way to add randomness and control overfitting. Test whether this improves year-forward generalization and reduces training time. Keep only if Eval AUC improves on 0.6800, or ties with a faster run.

## Experiment 7 result — commit 4f79577

Eval AUC was **0.6793**, 0.0007 below the current best. Discard under the strict keep rule; 20% row subsampling did not improve this run.

## Experiment 8 hypothesis — proposed before editing

**Classification:** ablation/simplification, isolating a change that was bundled with the discarded route experiment.

Replace `X[col].where(X[col].isin(cat_levels[col]))` with `pd.Categorical(X[col], categories=cat_levels[col])`. The [pandas `Categorical` API](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) specifies that values outside the supplied categories become missing, which matches the existing mask. The explicit membership pass is therefore redundant and may cost time because `prepare` is called for each evaluation row. Keep if AUC is unchanged with the simpler conversion, or improves.

## Experiment 8 result — commit 845ac3d

Eval AUC remained **0.6800**. The harness run took 22.5 seconds, and the preparation code is shorter, so keep. Direct categorical construction retained the same best score while reducing per-row evaluation work.

## Experiment 9 hypothesis — proposed before editing

**Classification:** exploration (native categorical split strategy).

The training categories have 7 values for `DayOfWeek`, 12 for `Month`, 20 for `UniqueCarrier`, 31 for `DayofMonth`, and 283 each for `Origin` and `Dest`. The [XGBoost categorical parameter reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html) says `max_cat_to_onehot` selects one-hot splits below a threshold and partition-based splits otherwise. Set it to 32: this lets the low-cardinality calendar and carrier fields use one-vs-rest splits while leaving the airport fields partitioned. Test whether that split bias improves Eval AUC with all other settings fixed.

## Experiment 9 result — commit 2b23ad5

Eval AUC was **0.6793**, below 0.6800, so discard. Setting the threshold to 32 for low-cardinality one-hot splits did not help; return to XGBoost's default categorical strategy.

## Experiment 10 hypothesis — proposed before editing

**Classification:** follow-up (leaf regularization) to the current best.

Set `min_child_weight=5` while keeping 200 trees, learning rate 0.05, and depth 4. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as the minimum Hessian sum required in a child and says larger values make the model more conservative. Test whether requiring more support for leaf splits improves generalization across years. Keep only if Eval AUC beats 0.6800 or ties with a faster run.

## Experiment 10 result — commit a753666

Eval AUC was **0.6799**, below 0.6800, so discard. Raising `min_child_weight` to 5 did not preserve the best score.

## Synthesis after 10 non-baseline experiments

- **What helped:** lowering the learning rate to 0.05 while increasing rounds to 200 raised AUC to 0.6764; reducing depth to 4 raised it again to 0.6800. Removing the redundant categorical membership mask preserved 0.6800 with shorter preparation code and a 22.5-second harness run.
- **What did not help:** a directed route category (0.6667), sine/cosine departure time (0.6734), 300 rounds (0.6743), depth 5 (0.6775), row subsampling (0.6793), one-hot splits for smaller categories (0.6793), and `min_child_weight=5` (0.6799) all scored below the best and were discarded.
- **Current theory:** the year-forward score benefits more from conservative tree structure and finer boosting steps than from the tested static route/time additions. The airport categoricals remain high-cardinality (283 origins and destinations), so their partition-based splits are a plausible place to target regularization next.
- **Next direction:** cap categorical partition candidates with `max_cat_threshold`; continue using only features available before departure.

## Fresh research after experiment 10

- The current [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) list `max_cat_threshold` among complexity controls. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says it limits the number of categories considered in a partition-based split to help prevent overfitting. This directly motivates testing it on the 283-level airport features.
- A recent [FlightNet-ST study](https://link.springer.com/article/10.1007/s44196-025-00932-2) combines schedule variables with operational history and weather. Those additional inputs are unavailable under this experiment's feature and data rules, so the next change stays within XGBoost's handling of the permitted categorical fields.

## Experiment 11 hypothesis — proposed before editing

**Classification:** exploration (high-cardinality categorical regularization).

Set `max_cat_threshold=32`, keeping the best 200 trees, learning rate 0.05, depth 4, native categorical representation, and all features unchanged. XGBoost uses this parameter to cap category candidates in partition-based splits, which may reduce overfitting in the 283-level origin and destination features. Keep only if Eval AUC exceeds 0.6800, or ties with a faster run.

## Experiment 11 result — commit b97b074

Eval AUC was **0.6797**, below 0.6800, so discard. Capping the candidate categories did not help. This is the third consecutive discard within 0.001 of the best, triggering a plateau research pause before the next experiment.

## Plateau research after Experiment 11

- The installed scikit-learn is 1.9.1 and provides `TargetEncoder`. Its [API documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) describes smoothed category means and warns that `fit(X, y).transform(X)` can leak labels; `fit_transform` uses internal cross-fitting instead. The [cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) explains that each training fold is encoded from the other folds.
- CatBoost's [categorical feature documentation](https://catboost.ai/docs/en/concepts/algorithm-main-stages_cat-to-numberic) describes target statistics with a prior and statistics over categorical combinations. This supports testing a smoothed numeric risk summary, while the scikit-learn cross-fitting path avoids using each training row's own label in its encoded values.

## Experiment 12 hypothesis — proposed before editing

**Classification:** exploration (target encoding for categorical features).

Add smoothed target-mean features for `UniqueCarrier`, `Origin`, and `Dest`, alongside their existing native categorical columns. Use scikit-learn `TargetEncoder(smooth="auto", target_type="binary")` with five-fold stratified cross-fitting for the training rows. `prepare(train)` will retrieve each row's precomputed out-of-fold encodings by an internal training-row key; a single evaluation row will map through the encoder's full-train category statistics, with unseen categories falling back to the training target mean. This keeps each feature row-local, uses only `train.csv` to fit lookups, and avoids training-label leakage. Keep only if Eval AUC exceeds 0.6800.

## Experiment 12 result — commit dfd1a5d

Eval AUC was **0.6802**, a new best. Keep. The cross-fitted smoothed rates for carrier, origin, and destination added a small improvement over native categoricals alone.

## Experiment 13 hypothesis — proposed before editing

**Classification:** follow-up to the target-encoding improvement.

Add one more smoothed, out-of-fold target-rate feature for the directed `Origin→Dest` pair, leaving the route out of the native categorical columns. The raw route category previously reduced AUC, but a target rate is a different representation: it provides a shrunken numeric estimate instead of a high-cardinality tree split. CatBoost's [categorical statistics documentation](https://catboost.ai/docs/en/concepts/algorithm-main-stages_cat-to-numberic) describes statistics on categorical combinations; the same idea is tested here with scikit-learn cross-fitting to avoid target leakage. Keep only if Eval AUC exceeds 0.6802.

## Experiment 13 result — commit f913aea

Eval AUC was **0.6791**, below 0.6802, so discard. The smoothed route interaction did not transfer as well as the separate carrier, origin, and destination rates.

## Experiment 14 hypothesis — proposed before editing

**Classification:** ablation/simplification of promising Experiment 12.

Remove only `UniqueCarrierTargetRate`, keeping the cross-fitted origin and destination rates. This tests whether the airline-level target summary contributes to Experiment 12's 0.0002 improvement. If the score ties, keep the smaller encoding; if it falls, restore all three rates.

## Experiment 14 result — commit a98744e

Eval AUC remained **0.6802** with just origin and destination target rates. Keep the smaller encoding; the carrier rate was not needed for the measured score.

## Experiment 15 hypothesis — proposed before editing

**Classification:** ablation/simplification of the kept two-rate model.

Remove `DestTargetRate` and retain only `OriginTargetRate`. Departure delay may be more directly tied to the departure airport's local operating conditions; this tests whether the destination summary adds anything beyond origin. Keep if AUC ties or improves, since the model then has a shorter encoding path.

## Experiment 15 result — commit 218232c

Eval AUC improved to **0.6805** with only the origin rate. Keep as the new best; the destination target rate was not useful alongside it.

## Experiment 16 hypothesis — proposed before editing

**Classification:** follow-up (target-encoded interaction) to the origin-rate gain.

Add a cross-fitted target rate for `Origin × 4-hour departure block` alongside `OriginTargetRate`. Delay risk at a departure airport may vary by scheduled departure bank; the FlightNet-ST paper reviewed above combines airport and time features, though its operational sequence data are unavailable here. This interaction uses only `Origin` and `CRSDepTime` from each row, with its target statistics fitted on train and cross-fitted for training. Keep only if Eval AUC exceeds 0.6805.

## Experiment 16 result — commit 7e23191

Eval AUC was **0.6795**, below 0.6805, so discard. The airport-by-time interaction was too specific at this granularity; restore the origin-only encoding.

## Experiment 17 hypothesis — proposed before editing

**Classification:** exploration (coarse time target encoding).

Add a cross-fitted target rate for six global 4-hour departure blocks alongside `OriginTargetRate`. Experiment 16's airport-by-time cells were too specific; this broader encoding has far more support per category and tests whether a general time-of-day risk pattern helps without the airport interaction. The raw scheduled time remains available. Keep only if Eval AUC exceeds 0.6805.

## Experiment 17 result — commit 7b1db57

Eval AUC was **0.6788**, below 0.6805, so discard. A target rate for the global departure block did not help; restore the origin-only encoder.

## Experiment 18 hypothesis — proposed before editing

**Classification:** ablation/simplification of the current best.

Remove raw `Origin` from the native categorical columns while retaining `OriginTargetRate`. This tests whether the cross-fitted numeric risk estimate can replace the 283-level origin split, potentially reducing overfitting and redundant signal. Keep only if Eval AUC is at least 0.6805; equality favors the smaller input set.

## Experiment 18 result — commit c3321c8

Eval AUC fell to **0.6778**, so discard. The target rate works as a complement to the raw origin category; it cannot replace it.

## Experiment 19 hypothesis — proposed before editing

**Classification:** follow-up to the origin-only target-rate improvement.

Add `UniqueCarrierTargetRate` back alongside `OriginTargetRate`, but keep `DestTargetRate` absent. Experiment 14 showed carrier was removable when both airport rates were present; this tests whether it helps in the stronger origin-only configuration. Keep only if Eval AUC exceeds 0.6805.

## Experiment 19 result — commit aa6b99a

Eval AUC remained **0.6805**. Discard the extra carrier rate: it tied without making the implementation simpler or faster, so it does not meet the tie rule.

## Experiment 20 hypothesis — proposed before editing

**Classification:** follow-up (target-rate regularization) to the origin-rate improvement.

Set `TargetEncoder(smooth=50.0)` instead of `smooth="auto"`, retaining the origin-only rate. The [TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) says a larger smoothing value gives more weight to the global target mean. This tests whether stronger shrinkage stabilizes airport rates across the 2005-to-2006 shift. Keep only if Eval AUC exceeds 0.6805.

## Experiment 20 result — commit f881ece

Eval AUC was **0.6801**, below 0.6805, so discard. The empirical-Bayes `smooth="auto"` setting remains preferable to a fixed smoothing value of 50.

## Synthesis after 20 non-baseline experiments

- **Current best:** commit `218232c`, Eval AUC **0.6805**. Relative to the starter baseline (0.6743), the gain comes from 200 trees at learning rate 0.05 and depth 4, plus a cross-fitted, smoothed `OriginTargetRate` alongside native categoricals. Simplifying categorical preparation preserved the score and reduced evaluation time.
- **Target encoding findings:** the carrier and destination rates were unnecessary; origin alone scored 0.6805. Removing native `Origin` lost AUC, so the numeric rate complements rather than replaces the categorical feature. Route, origin-by-time, and global time-block rates reduced AUC. Fixed smoothing at 50 also reduced AUC relative to empirical-Bayes `auto`.
- **Other directions:** explicit route and cyclical-time features, row subsampling, alternative categorical split thresholds, higher `min_child_weight`, more trees, and depth 5 did not beat the best.
- **Current theory:** the useful signal is a broad, stable airport-level delay propensity, while more specific rates add noise. The boosted model also benefits from smaller trees and slower updates. Next, test split-gain regularization to prune marginal splits without changing features or target encodings.

## Fresh research after experiment 20

- The installed-version [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `gamma` (`min_split_loss`) as the minimum loss reduction required for another tree partition; higher values make the model more conservative. Unlike `min_child_weight`, this directly rejects low-gain splits, so it is a distinct regularization test after the child-weight experiment failed.

## Experiment 21 hypothesis — proposed before editing

**Classification:** follow-up (split-gain regularization) to the current best.

Set `gamma=1.0`, keeping all features, target encoding, depth 4, 200 trees, and learning rate 0.05 unchanged. A modest positive loss threshold may prune marginal splits that do not transfer to 2006. Keep only if Eval AUC exceeds 0.6805.

## Experiment 21 result — commit 93495ab

Eval AUC was **0.6803**, below 0.6805, so discard. A split-gain threshold of 1.0 slightly reduced the score.

## Experiment 22 hypothesis — proposed before editing

**Classification:** follow-up (capacity check) to the target-encoding improvement.

Reduce `max_depth` from 4 to 3 while keeping the origin target rate, learning rate 0.05, and 200 rounds fixed. The earlier depth sweep preceded target encoding; the origin-rate feature may let shallower trees generalize better. Keep only if Eval AUC exceeds 0.6805, or ties with a faster run.

## Experiment 22 result — commit 24d9ef4

Eval AUC was **0.6799**, below 0.6805, so discard. Depth 4 remains better even with the origin target rate.

## Experiment 23 hypothesis — proposed before editing

**Classification:** exploration (feature-sampling regularization).

Set `colsample_bytree=0.8`, keeping the origin-only target rate and all other model settings fixed. XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) list column sampling as a way to add randomness. This tests feature-level regularization, distinct from the row-subsampling experiment, with the new target-rate feature present. Keep only if Eval AUC exceeds 0.6805.

## Experiment 23 result — commit e91e44a

Eval AUC improved to **0.6813**, the new best. Keep. Column subsampling helped with the origin-rate feature, even though row subsampling without target encoding had hurt.

## Experiment 24 hypothesis — proposed before editing

**Classification:** follow-up to promising Experiment 23.

Raise `colsample_bytree` from 0.8 to 0.9, keeping the origin target rate and all other settings fixed. Since 0.8 improved AUC, test whether milder column sampling retains more useful splits while keeping some feature-level randomness. Keep only if Eval AUC exceeds 0.6813.

## Experiment 24 result — commit 5b44a85

Eval AUC was **0.6810**, below the 0.6813 result at `colsample_bytree=0.8`; discard and restore the stronger sampling setting.

## Final summary

- **Best Eval AUC:** **0.6813** at kept commit `e91e44a`, up from baseline 0.6743.
- **Best configuration:** 200 estimators, depth 4, learning rate 0.05, `colsample_bytree=0.8`, native categorical features, and a cross-fitted smoothed target rate for `Origin` alongside the raw category. Direct construction of train-level pandas categories kept the same AUC while reducing row-wise preparation time.
- **What worked:** slower boosting with 200 rounds, shallower depth 4, the out-of-fold origin target rate, and feature sampling at 0.8.
- **What did not:** explicit route and cyclical time features, time-block target rates, route target rates, deeper or shallower trees, 300 rounds, row subsampling, higher child weight, stronger target smoothing, categorical split threshold changes, and `colsample_bytree=0.9` all failed to beat the best.
- **Next:** continue a narrow search around `colsample_bytree=0.8` and test modest split regularization with the origin rate retained. The holdout set remains uninspected.
