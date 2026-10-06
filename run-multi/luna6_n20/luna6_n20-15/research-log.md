# Experiment research log

## Setup — 2026-10-05

- Run branch: `oct5`, created from the current HEAD as specified.
- Data check: `data/train.csv` and `data/eval.csv` are present.
- Baseline: pending. The starter `train.py` is unchanged; run it first after the experiment clock starts.
- Research for the first non-baseline experiment will be done before that experiment.

## Baseline — commit `b15ec66`

- Ran the unmodified starter model as required.
- Eval AUC: **0.6743**; harness status: `ok`.
- Baseline: 100 trees, depth 6, learning rate 0.1, native categorical splits, seed 42.

## Research before experiment 1

Sources reviewed:

- [XGBoost notes on parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): `max_depth`, `min_child_weight`, and `gamma` directly control model complexity; the guide recommends balancing added fit capacity against overfitting and also describes sampling as a regularization option.
- [XGBoost categorical data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): pandas categorical columns with `enable_categorical=True` are supported, and categorical splits can use one-hot or category partitioning. This supports retaining the starter's native categorical representation for this first comparison.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): higher `min_child_weight` makes partitioning more conservative.

The starter has 100 trees at depth 6 with the default `min_child_weight=1`. It trains on 2005 and is evaluated on 2006, so a less complex tree ensemble may transfer better across the year boundary. The 2005 training file contains 200,000 rows and the categorical features range from 7 to 283 levels.

### Experiment 1 hypothesis — exploration

Try `max_depth=4` and `min_child_weight=5`, leaving the number of trees, learning rate, native categorical handling, and all other settings fixed. The parameter-tuning guide treats these as complementary complexity controls; reducing both should discourage brittle splits and could improve AUC on the later-year evaluation data. This is an exploration of regularization relative to the baseline, not a change to feature engineering. Keep or discard strictly by the harness AUC rule.

## Experiment 1 — commit `de98aaa`

- Change: reduced `max_depth` from 6 to 4 and raised `min_child_weight` from its default 1 to 5; all other settings stayed fixed.
- Eval AUC: **0.6793** (`ok`), up from 0.6743. Kept as the new best.
- Observation: the conservative tree setting transferred better to 2006. The change is consistent with the year-shift/generalization hypothesis, though this single comparison does not isolate which of the two paired parameters contributed most.

## Research before experiment 2

Sources reviewed:

- [scikit-learn time-related feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): represents periodic hour, weekday, and month with sine/cosine pairs so adjacent ends of the period remain close in the transformed space. Its examples include gradient boosting alongside linear models.
- [Universal patterns in passenger flight departure delays](https://doi.org/10.1038/s41598-020-62871-6): analyzes departure-delay patterns across multiple U.S. carriers over many years, supporting temporal and carrier-dependent structure as a relevant domain consideration.
- [Generation and prediction of flight delays in air transport](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057): survey of prior delay-prediction studies lists scheduled departure time, weekday, month, carrier, and airports among commonly used predictors.

### Experiment 2 hypothesis — exploration

Add sine/cosine pairs for `Month`, `DayOfWeek`, and scheduled departure time, retaining the original features and the kept `max_depth=4`, `min_child_weight=5` model. This tests whether explicit periodic geometry helps trees share signal between neighboring times and across wrap boundaries. The train-only check confirmed `CRSDepTime` is valid HHMM (5–2359; no invalid minute fields or 2400 values). All derived columns will be computed directly from each row inside `prepare(df)`, with no aggregates or evaluation-dependent state. Keep or discard by harness AUC.

### Experiment 2 attempt — commit `00e9c22` crashed

- The harness failed during `prepare(train)` before fitting: `Month` and `DayOfWeek` are pandas string columns, so subtracting an integer raised `TypeError`.
- Logged as `crash` with AUC 0.0000. The feature idea remains testable; the implementation will convert these row values to integers before applying the cyclic transform and rerun.

### Experiment 2 retry — commit `6c5db7e` crashed

- The harness again failed before fitting: calendar categories are strings like `c-11`, not plain numeric strings, so `.astype(int)` could not parse them.
- Logged as `crash` with AUC 0.0000. The training-only inspection confirmed these fields use the `c-<ordinal>` form; the next retry will convert the suffix to an integer.

### Experiment 2 — corrected run, commit `6c75204`

- Change: retained the six cyclic features for month, weekday, and scheduled departure time. Calendar labels use the dataset's `c-<ordinal>` format, parsed row-wise inside `prepare`.
- Eval AUC: **0.6799** (`ok`), up from 0.6793. Kept as the new best.
- Evaluation took 46.3s, within the 5-minute limit. The row-wise preparation stayed valid and consistent for training and evaluation.
- Observation: cyclic time representations provided a small additional gain on top of the shallower, regularized model.

## Research before experiment 3

Sources reviewed:

- [XGBoost categorical data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): native categorical splits use either category-specific splits or optimal category partitioning; the latter groups categories by their training statistics without one-hot expansion.
- [Predicting flight delay with spatio-temporal trajectory convolutional network and airport situational awareness map](https://www.sciencedirect.com/science/article/pii/S092523122101612X): original flight-delay research describes spatial/route information and airport context as useful signals for departure-delay prediction.
- [Airport dominance, route network design and flight delays](https://doi.org/10.1016/j.tre.2022.103000): estimates airport origin/destination effects and studies how route-network structure relates to delays.

The train-only inspection found 4,290 directed Origin–Destination pairs among 200,000 rows. This is enough repeated data for native categorical partitioning to learn route groupings, while staying far below the 283×283 theoretical pair space.

### Experiment 3 hypothesis — exploration

Add one `OriginDestRoute` categorical feature built from each row's Origin and Dest, with allowed route levels learned once from `train`. Keep the selected depth/child-weight settings and cyclic features fixed. Origin and Dest are already present separately, so the new feature tests whether explicitly exposing their interaction captures route-specific delay behavior. It is row-local, does not use counts or labels, and unseen evaluation routes will map to missing. Keep or discard by harness AUC.

## Experiment 3 — commit `8f35102` discarded

- Change: added an Origin–Destination categorical interaction with train-fitted levels; unseen routes mapped to missing.
- Eval AUC: **0.6719** (`ok`), down from 0.6799. Evaluation took 63.2s.
- Discarded and reverted. The route identity did not generalize across the year boundary in this encoding; its 4,290 levels likely made route-specific splits too sparse relative to the existing airport features.

## Research before experiment 4

Sources reviewed:

- [XGBoost 3.4.2 Python API reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html): `max_cat_threshold` limits the number of categories considered per split and is specifically intended to reduce overfitting for partition-based categorical splits.
- [XGBoost notes on parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): categorical split thresholds are among the direct complexity controls; the broader tuning guidance emphasizes balancing fit against generalization.

The route interaction with 4,290 levels lowered AUC, while Origin and Dest each have 283 levels. Rather than add another sparse feature, test whether constraining category candidates in the existing native categorical features makes airport splits more robust across the year shift.

### Experiment 4 hypothesis — exploration

Set `max_cat_threshold=32` on the current best model, leaving depth, child weight, cyclic features, and the rest unchanged. The official API describes this cap as a regularizer for partition-based categorical splits. If high-cardinality airport splits are overfitting, a smaller candidate set may improve transfer to 2006. Keep or discard by harness AUC.

## Experiment 4 — commit `650f847` discarded

- Change: set `max_cat_threshold=32`, constraining category candidates in partition-based splits.
- Eval AUC: **0.6795** (`ok`), slightly below the kept 0.6799. Discarded and reverted.
- Observation: this cap did not improve year-to-year transfer at the tested value; retain the XGBoost default for now.

### Experiment 5 hypothesis — follow-up to the kept model

The [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes `subsample` and `colsample_bytree` as randomness controls that can improve robustness. Test both at 0.8, holding the kept depth, child weight, cyclic features, and all other parameters fixed. The hypothesis is that sampling rows and features will regularize the 2005 fit and improve AUC on the 2006 distribution. Keep or discard by harness AUC.

## Experiment 5 — commit `527611b` discarded

- Change: set `subsample=0.8` and `colsample_bytree=0.8` together.
- Eval AUC: **0.6785** (`ok`), below 0.6799. Discarded and reverted.
- Observation: sampling reduced performance slightly at this setting; keep full row/feature sampling for the current best.

## Research before experiment 6

- [Spatio-Temporal Feature Engineering and Selection-Based Flight Arrival Delay Prediction](https://www.mdpi.com/2079-9292/13/24/4910) describes converting scheduled departure time in HHMM form into twelve 2-hour categories, alongside other temporal features. The study motivates checking a coarse time-of-day representation for operational regimes that may not be captured by a single numeric threshold.

### Experiment 6 hypothesis — exploration

Add one categorical `DepPeriod` feature using 12 fixed two-hour bins from the already validated HHMM departure time. Preserve the raw departure time and the successful cyclic features. Coarse bins may expose broad congestion and delay-propagation regimes to the tree, while the existing time encodings preserve finer detail. Compute each value from its row alone. Keep or discard by harness AUC.

## Experiment 6 — commit `9b7ee8f` discarded

- Change: added 12 categorical two-hour departure-time periods.
- Eval AUC: **0.6782** (`ok`), below 0.6799. Discarded and reverted.
- Observation: this coarse binning did not add useful signal beyond raw HHMM and the cyclic time features in this setup.

## Research before experiment 7

Sources reviewed:

- [Universal patterns in passenger flight departure delays](https://www.nature.com/articles/s41598-020-62871-6): a 20-year, 14-carrier study finds carrier-specific delay-propagation behavior and distinct operational delay distributions.
- [Effect of airline choice and temporality on flight delays](https://www.sciencedirect.com/science/article/pii/S096969971930537X): models departure-delay probability using airline choice and intra-day/inter-day temporal factors, and reports that temporal effects vary by airline.

### Experiment 7 hypothesis — exploration

Add a categorical interaction between `UniqueCarrier` and the 2-hour departure period, using levels fitted from `train` and missing for unseen pairs. The standalone 2-hour period feature did not help, but the cited work motivates allowing its effect to vary by carrier. With 20 carriers and 12 periods, the theoretical space is at most 240 levels, much smaller than the 4,290-level route feature that overfit. Preserve all currently kept features and model settings.

## Experiment 7 — commit `d80b528` discarded

- Change: added a categorical carrier × two-hour departure-period feature using levels learned from `train`.
- Eval AUC: **0.6787** (`ok`), below 0.6799. Discarded and reverted.
- Observation: the airline/time interaction did not improve this model despite the domain motivation; the raw carrier and temporal features appear to capture the useful signal more robustly.

## Research before experiment 8

- [XGBoost notes on parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends reducing `eta` to make updates more conservative and increasing `num_round` when doing so. The parameter reference describes `eta` as shrinkage intended to prevent overfitting.

### Experiment 8 hypothesis — follow-up to the kept model

Change the fit from 100 trees at learning rate 0.1 to 300 trees at 0.05, keeping the current depth 4, `min_child_weight=5`, and cyclic features. Smaller steps may build a smoother ranking, while extra rounds compensate for the slower learning rate. Training has been far below the 60-second limit, so 300 rounds should fit comfortably. Keep or discard by harness AUC.

## Experiment 8 — commit `ed15768` discarded

- Change: lowered the learning rate from 0.1 to 0.05 and raised the tree count from 100 to 300.
- Eval AUC: **0.6796** (`ok`), below 0.6799. Discarded and reverted.
- Observation: the additional rounds did not compensate for the smaller updates at this setting.

## Synthesis after 10 non-baseline harness attempts

This checkpoint counts each committed run attempt, including the two crashes while implementing cyclic features.

- **What helped:** the biggest gain came from reducing tree complexity (`max_depth=4`, `min_child_weight=5`), raising AUC from 0.6743 to 0.6793. Adding row-local sine/cosine encodings for month, weekday, and departure time raised it again to 0.6799.
- **What did not help:** the 4,290-level Origin–Destination category was too sparse and dropped to 0.6719. A categorical split cap of 32, 0.8 row/column sampling, standalone two-hour departure bins, the carrier × time-bin interaction, and 300 trees at learning rate 0.05 all scored below the best. The cyclic implementation took two crashes to match the dataset's `c-<ordinal>` calendar labels; the corrected implementation is stable and stayed within evaluation timeout.
- **Current theory:** year-to-year transfer benefits from a conservative model and compact, row-local temporal representations. Higher-cardinality identity interactions and added model randomness have not generalized in these tests.
- **Best so far:** Eval AUC **0.6799**, commit `6c75204`.
- **Next direction:** test compact origin-by-time effects or airport-level structure using low-cardinality time groups, and continue measured complexity tuning without increasing route-level sparsity.

## Research before experiment 9

- [Econometric Analysis of U.S. Airline Flight Delays with Time-of-Day Effects](https://its.berkeley.edu/node/5881) reports that the delay impact of arrival queuing varies by time of day, with stronger effects in the morning than later periods.
- [Departure delays, the pricing of congestion, and expansion proposals at Chicago O’Hare Airport](https://www.sciencedirect.com/science/article/pii/S096969970600007X) estimates airport-specific congestion effects and describes strong time-of-day variation in departure delays at a busy origin airport.

### Experiment 9 hypothesis — exploration

Add an `OriginDepPeriod` categorical interaction pairing Origin with one of four 6-hour periods. It tests airport-specific daily risk profiles with at most 283 × 4 = 1,132 possible levels, fewer than the 4,290-level directed route feature that overfit. Unlike the earlier carrier/time interaction, this uses spatial congestion at the departure airport. Train-fitted levels will map unseen evaluation pairs to missing; every row's category is determined from its own origin and scheduled time.

## Experiment 9 — commit `588b539` discarded

- Change: added an Origin × six-hour departure-period categorical interaction (at most 1,132 levels).
- Eval AUC: **0.6768** (`ok`), down from 0.6799. Discarded and reverted.
- Observation: airport/time combinations were still too sparse or unstable across years. Keep separate airport and time predictors instead of adding this interaction.

## Research before experiment 10

- [scikit-learn TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) defines target encoding as the shrunk mean target conditioned on a category and describes smoothing toward the global mean. It also warns that fitting and transforming the same training rows can leak target information; its `fit_transform` uses cross-fitting to prevent that.
- [Regularized target encoding outperforms traditional methods](https://link.springer.com/article/10.1007/s00180-022-01207-6) studies regularized encodings for high-cardinality categorical features and explains shrinkage of category effects toward a global baseline.

### Experiment 10 hypothesis — exploration

Add smoothed train-fitted late-rate lookups for Origin and Dest. For each airport, use `(positive_sum + 100 × global_rate) / (row_count + 100)`, and expose only the resulting numeric rate (never the count). Map unknown airports to the global rate. This tests whether compact airport risk priors can help after native category splits worked, while avoiding the sparse 4,290-level route identity that failed. The fixed lookup makes each row's feature identical whether prepared alone or in a frame. It is not cross-fitted, so each training row contributes slightly to its airport prior; the strength-100 shrinkage limits that self-influence, and the harness AUC decides whether the approach is useful.

## Experiment 10 — commit `de00d7b` discarded

- Change: added smoothed train-fitted positive-label priors for Origin and Dest with strength 100; counts were used only in the smoothing denominator and were not exposed as features.
- Eval AUC: **0.6797** (`ok`), just below 0.6799. Discarded and reverted.
- Observation: the airport priors added no gain beyond native categorical handling. Their training-row self-influence was limited by shrinkage but did not help the evaluation ranking.

### Experiment 11 hypothesis — ablation of a promising result

The first regularization run changed both depth and child weight at once, so their individual contributions are unclear. Remove the explicit `min_child_weight=5` setting (restoring XGBoost's default 1) while retaining `max_depth=4` and the kept cyclic features. If AUC is unchanged or higher, the simpler configuration wins under the keep rule; if it drops, the child-weight increase contributed to the gain.

## Experiment 11 — commit `b64e257` kept

- Change: removed explicit `min_child_weight=5`, reverting to default 1 while retaining depth 4 and cyclic features.
- Eval AUC: **0.6799** (`ok`), equal to the prior best at four decimals. Kept because the code is simpler.
- Observation: depth 4 appears to account for the useful regularization; the child-weight increase was not needed at the reported AUC precision.

### Experiment 12 hypothesis — follow-up to the kept model

Reduce `max_depth` from 4 to 3, leaving the default child weight and all features unchanged. The XGBoost tuning guide notes that greater depth increases complexity and overfitting risk; this tests whether one more step toward simpler trees helps the 2006 transfer, or instead underfits. Keep or discard by the strict AUC rule.

## Experiment 12 — commit `b30fb9e` discarded

- Change: reduced `max_depth` from 4 to 3.
- Eval AUC: **0.6797** (`ok`), below 0.6799, so it was discarded despite a smaller artifact (0.4 MB) and slightly faster evaluation. The keep rule does not allow a lower score for code/model size alone.

### Experiment 13 hypothesis — follow-up to the kept model

Set `gamma=1` (the default is 0) while retaining depth 4, default child weight, and the cyclic features. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists `gamma` as a direct complexity control; the parameter reference defines it as the minimum loss reduction required for another split. Requiring a modest gain may filter year-specific weak splits without imposing a smaller maximum depth. Keep or discard by harness AUC.

## Experiment 13 — commit `744705b` kept

- Change: set `gamma=1.0`, requiring a minimum split gain.
- Eval AUC: **0.6799** (`ok`), equal at four decimals to the prior best. The harness run took 47.8s versus 48.4s for the previous kept model (0.6s faster); kept under the equal-score speed rule.
- Observation: the speed difference is small and based on one run, but the model's reported score did not regress.

### Experiment 14 hypothesis — follow-up to the kept model

Raise `max_depth` from 4 to 5 while keeping `gamma=1` and all features fixed. Depth 3 scored slightly lower than 4, while the original depth-6 baseline was substantially lower without this split-gain regularizer. This tests the intermediate point: a little more interaction capacity may help if depth 4 underfits, while `gamma=1` filters weak splits. Keep or discard by harness AUC.

## Experiment 14 — commit `4ee7bee` discarded

- Change: increased `max_depth` from 4 to 5 while retaining `gamma=1`.
- Eval AUC: **0.6775** (`ok`), down from 0.6799. Discarded and reverted.
- Observation: depth 4 remains the better complexity level even with split-gain regularization.

### Experiment 15 hypothesis — follow-up to the kept gamma setting

Raise `gamma` from 1 to 2 at depth 4, keeping the features and other parameters fixed. This tests whether a stronger minimum split-gain threshold removes additional weak splits and improves transfer. The depth-5 run showed that simply adding complexity did not help; this experiment moves in the opposite direction. Keep or discard by AUC, with speed considered only on an exact tie.

## Experiment 15 — commit `41db4a7` kept

- Change: raised `gamma` from 1 to 2.
- Eval AUC: **0.6799** (`ok`), equal at four decimals. The run took 47.5s versus 47.8s for gamma 1 (0.3s faster), so it remains under the tie-speed rule.
- Observation: the reported score held while measured runtime edged down; both timing differences are small.

### Experiment 16 hypothesis — follow-up to the tied gamma result

Raise `gamma` from 2 to 3 at depth 4. This imposes a higher minimum gain per split; the prior gamma step tied in AUC and was slightly faster. Test whether that trend continues or begins to underfit. Keep or discard by AUC, using runtime only for an exact tie.

## Experiment 16 — commit `b2a5393` discarded

- Change: raised `gamma` from 2 to 3.
- Eval AUC: **0.6799** (`ok`), tied at four decimals, but total runtime was 47.8s versus 47.5s for gamma 2. Discarded under the tie-speed rule.
- Observation: the measured speed improvement did not continue at this stronger split threshold.

## Research before experiment 17

- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) documents `reg_lambda` as L2 regularization on leaf weights and says increasing it makes the model more conservative.

### Experiment 17 hypothesis — exploration

Set `reg_lambda=2` from its default 1, keeping depth 4, `gamma=2`, and all features fixed. This tests whether slightly shrinking leaf weights improves year-to-year ranking after the split threshold and tree depth have been regularized. Keep or discard by harness AUC.

## Experiment 17 — commit `ef8c1a8` kept

- Change: raised `reg_lambda` from 1 to 2 while retaining depth 4 and `gamma=2`.
- Eval AUC: **0.6802** (`ok`), a new best, up 0.0003 from 0.6799. Kept.
- Observation: modest L2 leaf-weight regularization improved the year-shifted ranking where additional tree-depth and feature-interaction complexity did not.

### Experiment 18 hypothesis — follow-up to the new best

Increase `reg_lambda` from 2 to 3, leaving depth 4, `gamma=2`, and features unchanged. Since 2 improved AUC over the default, test whether slightly stronger L2 shrinkage improves transfer further or begins to underfit. Keep or discard by the strict AUC and tie-speed rules.

## Experiment 18 — commit `2e8277e` discarded

- Change: raised `reg_lambda` from 2 to 3.
- Eval AUC: **0.6788** (`ok`), down from the 0.6802 best. Discarded and reverted.
- Observation: the L2 gain peaked at 2 in the tested range; stronger shrinkage underfit.

## Synthesis after 20 non-baseline harness attempts

As in the prior checkpoint, this count includes each committed harness run, including the two cyclic-feature implementation crashes.

- **What helped:** depth 4 was the most reliable tree size. Cyclic month, weekday, and departure-time features remain the only feature engineering gain. Removing the explicit `min_child_weight=5` setting held AUC at 0.6799 and simplified the code. `gamma=2` tied at 0.6799 and was marginally faster; most notably, increasing `reg_lambda` to 2 raised AUC to **0.6802**.
- **What did not help:** explicit route, carrier/time, and origin/time categorical interactions; coarse departure periods; smoothed airport target rates; row/column sampling at 0.8; a lower learning rate with more rounds; depth 3 or 5; and `reg_lambda=3`. Stronger regularization eventually reduced AUC.
- **Current theory:** modest complexity controls and compact row-local temporal structure transfer better across years than sparse identity interactions. A moderate L2 leaf penalty helps, but stronger shrinkage underfits. The timing differences among gamma settings are small; the AUC gain from `reg_lambda=2` is the strongest recent result.
- **Best so far:** Eval AUC **0.6802**, commit `ef8c1a8` (`max_depth=4`, `gamma=2`, `reg_lambda=2`, cyclic features).
- **Next direction:** keep changes small around this best, such as testing one L1 leaf penalty or another nearby regularization setting, then stop when less than two minutes remain.

### Experiment 19 hypothesis — follow-up to the new best

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_alpha` as L1 regularization on leaf weights; increasing it makes the model more conservative. Test a small `reg_alpha=0.1` with the kept `reg_lambda=2`, depth 4, and `gamma=2`. The small value may suppress weak leaf updates without disturbing the gains from L2. Keep or discard by AUC.

## Experiment 19 — commit `46c7ab3` kept

- Change: added `reg_alpha=0.1` alongside `reg_lambda=2`.
- Eval AUC: **0.6804** (`ok`), a new best, up 0.0002 from 0.6802. Kept.
- Observation: a small L1 leaf penalty improved the modest L2 regularization result.

### Experiment 20 hypothesis — follow-up to the new best

Raise `reg_alpha` from 0.1 to 0.2 while keeping `reg_lambda=2`, depth 4, and `gamma=2`. The 0.1 setting improved the score, so this tests whether a little stronger L1 shrinkage helps further or starts suppressing useful leaf updates. Keep or discard by AUC.

## Experiment 20 — commit `31305bc` discarded

- Change: raised `reg_alpha` from 0.1 to 0.2.
- Eval AUC: **0.6800** (`ok`), below the 0.6804 best. Discarded and reverted.
- Observation: the modest L1 value 0.1 was better than the stronger penalty.

### Experiment 21 hypothesis — follow-up to the L1 result

Reduce `reg_alpha` from 0.1 to 0.05, keeping `reg_lambda=2`, depth 4, and `gamma=2`. The 0.1 setting improved AUC while 0.2 regressed, so test whether a smaller L1 penalty retains or improves the gain. Keep or discard by AUC.

## Experiment 21 — commit `efec3cd` discarded

- Change: reduced `reg_alpha` from 0.1 to 0.05.
- Eval AUC: **0.6785** (`ok`), well below 0.6804. Discarded and reverted.
- Observation: the tested L1 benefit was specific to the 0.1 setting; less shrinkage lost performance.

### Experiment 22 hypothesis — final midpoint check

Test `reg_alpha=0.15` between the winning 0.1 and the lower-scoring 0.2, holding every other setting fixed. This is a bounded follow-up to the observed L1 response. The harness clock is near its limit, so no further experiment will start after this run.

## Experiment 22 — commit `e44fe1b` discarded

- Change: set `reg_alpha=0.15` between the tested 0.1 and 0.2 values.
- Eval AUC: **0.6787** (`ok`), below 0.6804. Discarded and reverted.

## Final summary — 2026-10-06

- **Best Eval AUC:** 0.6804 at commit `46c7ab3`.
- **What worked:** depth 4 with cyclic month, weekday, and departure-time features; `gamma=2`, `reg_lambda=2`, and `reg_alpha=0.1` gave the best result. The baseline was 0.6743.
- **What did not:** route and airport/time categorical interactions, coarse time bins, smoothed airport target priors, row/column sampling, more trees at a lower learning rate, and stronger L1/L2 settings. Their AUCs were lower.
- **Next:** if continuing this line, explore nearby leaf regularization around `reg_alpha=0.1` and `reg_lambda=2`, then test any candidate on the separate human holdout after the run.
