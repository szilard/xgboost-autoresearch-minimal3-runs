# Research log

## Baseline — b15ec66 — Eval AUC 0.6743

- Ran the starter `train.py` unchanged. The harness completed successfully (`ok`): 0.6 s model fit, 30.2 s evaluation, 31.8 s total.
- Baseline uses native XGBoost categorical splits on month, calendar day, weekday, carrier, origin and destination, plus scheduled departure time and distance; 100 trees, depth 6, learning rate 0.1.
- Feature engineering must preserve one-row meaning: evaluation calls `prepare(df)` on one row at a time, so any group lookup must be fitted from `train` outside `prepare`.
- Before the first non-baseline experiment, research XGBoost tuning guidance and schedule/route feature ideas.

## Experiment 1 — ff1f24b — Eval AUC 0.6734 — discard

- Hypothesis: replace HHMM integer with physical minutes since midnight and daily sine/cosine features to correct the nonuniform numeric spacing and expose the midnight cycle.
- Rationale: flight-delay literature commonly includes scheduled departure time and often models it categorically ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)); XGBoost guidance emphasizes data-aware preprocessing and warns that complexity can raise variance ([XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: AUC fell from 0.6743 to 0.6734; run completed in 36.2 s. Reverted to baseline. This encoding did not improve cross-year generalization here.
- Next: add Origin–Destination as one categorical route feature while retaining baseline time encoding. Prior delay studies use route pairs as predictors ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)); the baseline exposes origin and destination only as separate columns.

## Experiment 2 — 314cd3b — Eval AUC 0.6667 — discard

- Hypothesis: a combined Origin–Dest categorical feature could capture route-specific risk that separate airport features cannot.
- Rationale: route pairs appear among predictors summarized in flight-delay studies ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)). The train sample has 4,290 unique routes; median route support is 32 rows.
- Result: AUC fell to 0.6667. Eval emitted pandas warnings because some evaluation routes were missing from the train-fitted category dtype; the model completed but this feature generalized poorly. Reverted to baseline.
- Next: test lower tree depth alone, since XGBoost's tuning guide identifies max depth as a direct complexity/variance control ([XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).

## Experiment 3 — 9e938fa — Eval AUC 0.6789 — keep

- Classification: follow-up to baseline complexity tuning.
- Hypothesis: depth 6 allows interactions too specific to the 2005 training sample; depth 4 may generalize better to the 2006 evaluation set.
- Rationale: XGBoost's tuning guide describes depth as a model-complexity control and warns that more complex trees need more data ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: only `max_depth` changed, from 6 to 4. All features and other parameters stayed at baseline.
- Result: AUC rose from 0.6743 to 0.6789; run completed in 32.0 s. Kept this as the new best commit.
- Next: compare depth 5 with the new depth-4 best to test whether added interaction capacity retains the gain.

## Experiment 4 — 0792e38 — Eval AUC 0.6777 — discard

- Classification: follow-up to the promising depth-4 result.
- Hypothesis: depth 5 might recover useful interaction capacity while staying shallower than the baseline depth 6.
- Change: only `max_depth` changed from the kept value 4 to 5.
- Result: AUC was 0.6777, below depth 4's 0.6789; run completed in 31.7 s. Reverted to depth 4.
- Next: test depth 3 to bracket the local depth setting on the lower-complexity side.

## Experiment 5 — 5748ed2 — Eval AUC 0.6798 — keep

- Classification: follow-up to depth regularization.
- Hypothesis: depth 3 may reduce year-specific interactions further than depth 4 and improve transfer to 2006.
- Change: only `max_depth` changed from 4 to 3.
- Result: AUC rose from 0.6789 to 0.6798; run completed in 31.9 s. This is the current best.
- Next: test depth 2 to check whether another step toward a simpler tree helps.

## Experiment 6 — 05564bf — Eval AUC 0.6751 — discard

- Classification: follow-up to depth regularization.
- Hypothesis: depth 2 might further reduce sample-specific complexity after depth 3 outperformed depth 4.
- Change: only `max_depth` changed from the kept value 3 to 2.
- Result: AUC fell to 0.6751; run completed in 31.3 s. Reverted to depth 3, which remains the best tested depth (3, 4, 5, and 6).
- Next: investigate `min_child_weight`, a different regularization control over whether child leaves have enough training weight.

## Experiment 7 — e969a15 — Eval AUC 0.6798 — discard

- Classification: follow-up to the depth-3 best.
- Hypothesis: raising `min_child_weight` to 5 would stop small leaf splits and further regularize the model.
- Rationale: XGBoost documents this as the minimum Hessian weight required for a child, with larger values making the model more conservative ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: added `min_child_weight=5`; kept `max_depth=3` and other settings.
- Result: AUC remained 0.6798 and total runtime remained 31.9 s. Because the added setting neither improved the rounded score nor simplified or sped up the code, discarded per keep rule.
- Next: test row subsampling, a different regularization mechanism.

## Experiment 8 — 8a8cb66 — Eval AUC 0.6780 — discard

- Classification: follow-up using a different regularization mechanism.
- Hypothesis: `subsample=0.8` could reduce dependence on idiosyncratic 2005 rows and help the 2006 distribution.
- Rationale: XGBoost documents row subsampling as a way to prevent overfitting ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: added only `subsample=0.8` to the depth-3 model; random seed remained 42.
- Result: AUC fell to 0.6780; run completed in 31.6 s. Reverted to the depth-3 best.
- Next: test a smaller learning rate with proportionally more boosting rounds, as the tuning guide recommends when reducing step size ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).

## Experiment 9 — 8700cd6 — Eval AUC 0.6807 — keep

- Classification: follow-up to the depth-3 model.
- Hypothesis: smaller updates over more boosting rounds could improve ranking while retaining the regularizing effect of depth 3.
- Rationale: XGBoost's tuning guide recommends reducing `eta` with more rounds for conservative updates ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: `n_estimators` 100→200 and `learning_rate` 0.1→0.05; depth stayed 3.
- Result: AUC rose from 0.6798 to 0.6807; run completed in 32.0 s. Kept as new best.
- Next: test column subsampling at 0.8. XGBoost documents `colsample_bytree` as per-tree feature sampling and notes subsampling can improve robustness ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

## Experiment 10 — 126bb8f — Eval AUC 0.6809 — keep

- Classification: follow-up to the lower-learning-rate model.
- Hypothesis: selecting a subset of features per tree could reduce correlated tree decisions and improve robustness.
- Rationale: XGBoost documents `colsample_bytree` as per-tree feature sampling and describes subsampling as a way to reduce overfitting ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: added `colsample_bytree=0.8` to depth 3, 200 trees, learning rate 0.05.
- Result: AUC rose from 0.6807 to 0.6809; run completed in 32.2 s. Kept as new best.

## Synthesis after 10 non-baseline experiments

- **What helped:** reducing `max_depth` from 6 to 3 lifted AUC from 0.6743 to 0.6798. Pairing depth 3 with `learning_rate=0.05` and 200 estimators raised it to 0.6807; `colsample_bytree=0.8` added a small further gain to 0.6809.
- **What did not help:** replacing HHMM with minute-of-day and sine/cosine features (0.6734); a high-cardinality Origin–Dest category (0.6667, with unseen-route warnings); depths 2 and 5; `min_child_weight=5` (equal AUC without a simplification); and row subsampling at 0.8.
- **Current theory:** the starter's depth-6 model overfits year-specific patterns; shallow trees with slower updates generalize better. Mild column sampling appears compatible, while row sampling did not help. Hand-built continuous clock features and a sparse route identity were not useful in their first forms.
- **Current best:** 0.6809 at commit `126bb8f` (depth 3, 200 trees, learning rate 0.05, `colsample_bytree=0.8`).
- **Next direction:** investigate schedule-hour categories or compact time-of-day groupings, which may let the shallow trees model non-monotone operating periods. Continue to avoid train-row frequency features; train/eval scoring is row-wise and the sample is balanced by undersampling.

## Experiment 11 — 4745198 — Eval AUC 0.6791 — discard

- Classification: exploration of schedule-hour feature engineering.
- Hypothesis: a train-defined categorical departure hour could let shallow trees group non-contiguous clock hours. A 2025 flight-delay study includes a departure-hour-bin feature ([PLOS One](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0335141)); XGBoost's categorical guide explains learned category partitioning ([guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html)).
- Change: added `DepHour` as a categorical derived from scheduled `CRSDepTime // 100`, retaining the raw HHMM feature. Category levels were fitted from `train`.
- Result: AUC fell to 0.6791; evaluation took 34.0 s. Reverted to the current best.
- Next: test the categorical hour as a replacement for raw HHMM, to determine whether the loss came from redundant representations.

## Experiment 12 — 54818e3 — Eval AUC 0.6799 — discard

- Classification: ablation of the schedule-hour category experiment.
- Hypothesis: the previous loss may have come from redundancy, so use categorical departure hour instead of raw HHMM.
- Change: removed raw `CRSDepTime` from numeric features; retained a train-fitted categorical `DepHour`.
- Result: AUC was 0.6799, below the 0.6809 best; evaluation took 33.6 s. Reverted to current best. Both adding and replacing with hour category were slightly worse.
- Next: explore XGBoost's categorical split strategy. The categorical guide documents a threshold between one-hot and partition-based splits ([XGBoost categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html)).

## Experiment 13 — bca87cf — Eval AUC 0.6794 — discard

- Classification: exploration of native categorical split strategy.
- Hypothesis: individual one-hot splits for low-cardinality categories might capture month/day/carrier effects better than category partitions.
- Rationale: XGBoost's categorical parameter `max_cat_to_onehot` selects one-hot versus partition-based splits by category count ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)). Train cardinalities are 12 Month, 31 DayofMonth, 7 DayOfWeek, 20 carriers, and 283 each for Origin and Dest.
- Change: set `max_cat_to_onehot=32` on the current best, making all but Origin/Dest one-hot eligible.
- Result: AUC fell to 0.6794; run completed in 32.0 s. Reverted to current best.
- Next: try threshold 16, which limits one-hot treatment to Month and DayOfWeek, to isolate whether DayofMonth or carrier one-hot splits caused the loss.

## Experiment 14 — b5ca68f — Eval AUC 0.6808 — discard

- Classification: follow-up to categorical split-threshold exploration.
- Hypothesis: one-hot splits could help very small calendar categories while leaving day-of-month, carrier, and airport categories partitioned.
- Change: set `max_cat_to_onehot=16`, which permits one-hot splits for Month and DayOfWeek based on the train cardinalities.
- Result: AUC was 0.6808, just below the 0.6809 best; runtime was 31.8 s. Reverted to the best. Neither threshold 16 nor 32 improved on the default handling.
- Next: compare a finer boosting schedule, 300 trees at learning rate 0.033, with the kept 200 trees at 0.05. XGBoost's tuning guide recommends increasing rounds when reducing the step size ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).

## Experiment 15 — a7de956 — Eval AUC 0.6801 — discard

- Classification: follow-up to the successful smaller-step schedule.
- Hypothesis: 300 trees with learning rate 0.033 could improve on the 200-tree, 0.05 model using finer updates at a similar total learning-rate sum.
- Change: `n_estimators` 200→300 and `learning_rate` 0.05→0.033; other settings unchanged.
- Result: AUC fell to 0.6801; run completed in 32.3 s. Reverted to the current best.
- Next: increase histogram `max_bin` from its default 256 to 512 to test finer numeric split candidates for scheduled time and distance. XGBoost documents that larger bins can improve split optimality at added computation ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

## Experiment 16 — 50e12c0 — Eval AUC 0.6805 — discard

- Classification: exploration of numeric split resolution.
- Hypothesis: using 512 histogram bins instead of the 256 default could provide better cut points for scheduled departure time and distance.
- Rationale: XGBoost documents `max_bin` as the number of buckets for continuous features and notes larger values can improve split optimality at a compute cost ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: added `max_bin=512` to the current best; histogram-based automatic tree method remains in use.
- Result: AUC fell to 0.6805; run completed in 31.9 s. Reverted.
- Next: test `gamma=1` to require a minimum loss reduction for a split.

## Experiment 17 — 41f50b6 — Eval AUC 0.6809 — discard

- Classification: exploration of split-gain regularization.
- Hypothesis: requiring a gain of 1.0 before a split could remove weak, sample-specific branches.
- Rationale: XGBoost defines `gamma` as the minimum loss reduction for further splitting; larger values make the model more conservative ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: added `gamma=1.0` to the current best.
- Result: AUC remained 0.6809. The total run was 31.9 s versus 32.2 s for the best, a small difference not enough to establish a repeatable speed-up; the code also added a parameter. Discarded per keep rule.
- Next: test stronger feature subsampling (`colsample_bytree=0.6`) after 0.8 gave a small gain.

## Experiment 18 — a628aef — Eval AUC 0.6799 — discard

- Classification: follow-up to the promising column-subsampling result.
- Hypothesis: stronger per-tree feature sampling at 0.6 could increase tree diversity beyond the 0.8 setting.
- Change: only `colsample_bytree` changed from 0.8 to 0.6.
- Result: AUC fell to 0.6799; run completed in 32.1 s. Reverted to 0.8.
- Plateau note: recent parameter refinements cluster within about 0.001 of the best. Researching category-specific regularization and alternative boosting before selecting another direction.

## Experiment 19 — 3244428 — Eval AUC 0.6709 — discard

- Classification: plateau exploration of an alternative boosting method.
- Hypothesis: DART's tree dropout could reduce overfitting in the cross-year setting.
- Rationale: XGBoost's DART guide describes dropping trees during training to address overfitting, while noting training can be slower ([DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html)).
- Change: used the DART booster and `rate_drop=0.1`; retained the current best's depth 3, 200 trees, learning rate 0.05, and column sampling.
- Result: completed `ok`, training 12.9 s and evaluation 30.5 s, but AUC fell to 0.6709. XGBoost also emitted a deprecation warning for the `dart` booster name. Reverted.
- Next: regularize high-cardinality airport category partitions with `max_cat_threshold=32`. XGBoost describes this as a categorical split overfitting control ([Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)).

## Experiment 20 — 04da107 — Eval AUC 0.6777 — discard

- Classification: plateau exploration of high-cardinality categorical regularization.
- Hypothesis: capping categories considered per partition split at 32 could reduce overfitting in Origin and Dest.
- Rationale: XGBoost documents `max_cat_threshold` as a control used only for partition-based splits to prevent overfitting ([Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)).
- Change: added `max_cat_threshold=32` to the current best.
- Result: AUC fell to 0.6777; run completed in 32.2 s. Reverted.

## Synthesis after 20 non-baseline experiments

- **What helped:** depth 3 beat the starter's depth 6; using 200 trees at learning rate 0.05 raised the result further; `colsample_bytree=0.8` gave the current small additional gain. These gains are modest but consistent with reduced model complexity and slower updates helping year-to-year transfer.
- **What did not help:** clock transformations or categorical hour features; route category; depths 2 and 5; stronger row subsampling; more trees at a still smaller learning rate; histogram bin increase; split gamma; categorical one-hot thresholds; high-cardinality category cap; and DART. DART was much slower to train and substantially worse.
- **Current theory:** the reliable signal is mostly in the starter features, and the main gain comes from controlling tree complexity. Some individual temporal or route features have not transferred to 2006. Mild column sampling at 0.8 is the only tested randomness that helped.
- **Current best:** Eval AUC 0.6809, commit `126bb8f` (depth 3, 200 trees, learning rate 0.05, column sampling 0.8).
- **Next direction:** research domain-grounded interactions among existing known-in-advance fields, especially carrier and airport/time combinations. Avoid row-count features and any lookup that depends on evaluation rows.

## Experiment 21 — 155e256 — Eval AUC 0.6784 — discard

- Classification: exploration of a carrier-by-time interaction.
- Hypothesis: delay behavior can vary by carrier and hour, so their combination may capture operational patterns beyond separate features. A UC Berkeley flight-delay project examines departure-delay patterns by hour for each carrier ([project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)).
- Train-only diagnostics: 401 carrier-hour combinations, median support 360 rows, six singleton combinations (compared with 4,290 Origin–Dest routes and median support 32).
- Change: added a train-fitted categorical `CarrierHour` feature built from carrier and scheduled departure hour; unseen combinations map to missing. The feature is row-local.
- Result: AUC fell to 0.6784; evaluation increased to 37.3 s. Reverted.
- Next: test annual sine/cosine date position, a compact cyclic seasonal representation noted in flight-delay feature work ([MDPI study](https://www.mdpi.com/2226-4310/8/6/152)).

## Experiment 22 — 22a16f2 — Eval AUC 0.6819 — keep

- Classification: exploration of a smooth annual calendar feature.
- Hypothesis: a cyclic day-of-year representation could model seasonal changes continuously across month boundaries while retaining existing month/day categories.
- Rationale: flight-delay feature work includes day-of-year and trigonometric calendar encodings ([MDPI study](https://www.mdpi.com/2226-4310/8/6/152)); the model's only inputs are still scheduled calendar fields available for each row.
- Change: added sine/cosine of day-of-year computed from the row's Month and DayofMonth using train-derived month/day mappings; preserved all prior features.
- Result: AUC rose from 0.6809 to 0.6819; evaluation took 38.0 s and the complete run 39.7 s. New best, kept.
- Next: test depth 4 with the annual features to see if one extra interaction level improves on depth 3.

## Experiment 23 — 3c07450 — Eval AUC 0.6822 — keep

- Classification: follow-up to the annual seasonal feature result.
- Hypothesis: one additional tree level may help model interactions between the seasonal cycle and airport/carrier features.
- Change: increased `max_depth` from 3 to 4; kept the annual features, 200 trees, learning rate 0.05, and `colsample_bytree=0.8`.
- Result: AUC rose from 0.6819 to 0.6822; run completed in 39.2 s. New best.
- Next: compare depth 5 against this depth-4 model with annual features.

## Experiment 24 — 7137744 — Eval AUC 0.6814 — discard

- Classification: follow-up to depth 4 with annual features.
- Hypothesis: depth 5 might capture additional seasonal interactions.
- Change: raised `max_depth` from 4 to 5; all other settings and features unchanged.
- Result: AUC fell to 0.6814; run completed in 39.7 s. Reverted to depth 4.
- Next: compare the sine/cosine annual pair with one linear day-of-year feature, testing whether a simpler seasonal encoding is sufficient for trees.

## Experiment 25 — a8dd92a — Eval AUC 0.6841 — keep

- Classification: comparison/ablation of annual date representations.
- Hypothesis: a single ordered day-of-year feature may work better with tree thresholds than sine/cosine values, which require several splits to approximate a seasonal interval.
- Change: replaced `SeasonSin` and `SeasonCos` with linear `DayOfYear`; removed the now-unused NumPy import. Month/day maps remain fitted from train and the value is row-local.
- Result: AUC rose from 0.6822 to 0.6841; evaluation fell from 37.4 s to 36.5 s. Kept as new best.
- Next: test depth 3 with linear `DayOfYear` to see whether the gain persists with shallower trees.

## Experiment 26 — 68ee66b — Eval AUC 0.6830 — discard

- Classification: follow-up to the linear annual date feature.
- Hypothesis: depth 3 might be sufficient with a compact ordered day index.
- Change: lowered `max_depth` from 4 to 3; kept all features and other settings.
- Result: AUC fell to 0.6830; run completed in 37.9 s. Reverted to depth 4.
- Next: test whether linear `DayOfYear` can replace the separate Month and DayofMonth categories without losing AUC.

## Experiment 27 — f3bd7b2 — Eval AUC 0.6847 — keep

- Classification: ablation/simplification of the promising linear `DayOfYear` encoding.
- Hypothesis: the train-derived day index may subsume separate Month and DayofMonth categories, reducing redundant calendar representations.
- Change: removed Month and DayofMonth from model categorical features while retaining them as row inputs to derive `DayOfYear`; kept DayOfWeek, carrier, airports, raw time, and distance.
- Result: AUC rose from 0.6841 to 0.6847; evaluation dropped from 36.5 s to 28.7 s. New best and simpler/faster feature matrix.
- Next: add Month alone to see whether month-specific effects complement the linear annual index.

## Experiment 28 — 2d587b3 — Eval AUC 0.6845 — discard

- Classification: ablation follow-up to replacing separate calendar categories with linear `DayOfYear`.
- Hypothesis: Month-specific discontinuities or holiday-season effects might complement the annual index.
- Change: restored Month alone as a categorical feature; continued to omit DayofMonth.
- Result: AUC was 0.6845, below the 0.6847 best; evaluation took 32.3 s versus 28.7 s. Reverted.
- Next: test DayofMonth alone beside the annual index to isolate within-month effects.

## Experiment 29 — 7476f3f — Eval AUC 0.6840 — discard

- Classification: ablation follow-up to replacing calendar categories with linear `DayOfYear`.
- Hypothesis: day-of-month effects such as within-month patterns might add signal beyond the annual index.
- Change: restored DayofMonth alone as a categorical feature; continued to omit Month.
- Result: AUC was 0.6840, below the 0.6847 best; evaluation took 33.3 s. Reverted.
- Next: replace categorical DayOfWeek with a sine/cosine weekly cycle to test whether a periodic numeric representation generalizes better.

## Experiment 30 — 28a9f98 — Eval AUC 0.6850 — keep

- Classification: exploration of a cyclic weekly calendar representation.
- Hypothesis: sine/cosine weekday features can encode the week wraparound with a smooth pair of numeric inputs, potentially generalizing better than an unordered seven-level category.
- Change: replaced categorical DayOfWeek with row-local sine/cosine values from a train-fitted weekday-number lookup; retained linear DayOfYear.
- Result: AUC rose from 0.6847 to 0.6850; evaluation took 28.1 s. New best.

## Synthesis after 30 non-baseline experiments

- **What helped:** tree complexity control remains useful: depth 3 improved over the starter's depth 6, while depth 4 is slightly better after adding annual features. Learning rate 0.05 with 200 trees and `colsample_bytree=0.8` remain part of the best model. The strongest new signal came from linear `DayOfYear`; replacing its two sine/cosine features with one index improved AUC, and removing separate Month/DayofMonth categories improved it again. Replacing categorical DayOfWeek with weekly sine/cosine gave another small gain.
- **What did not help:** raw route and carrier-hour categories; departure-hour features; adding Month or DayofMonth back to DayOfYear; cyclic daily departure-time encodings; row subsampling; deeper/shallow depth trials outside the local best; split and category regularization; DART; finer histograms; and more than 200 trees at 0.033.
- **Current theory:** the day-level calendar has stable, transferable seasonal and weekly signals. Representing these as compact numeric indices/cycles works better than redundant category copies. Scheduled departure time and airport/carrier identifiers remain useful, while sparse identity interactions and extra category machinery have not helped.
- **Current best:** Eval AUC 0.6850 at commit `28a9f98`: depth 4, 200 trees, learning rate 0.05, `colsample_bytree=0.8`, linear DayOfYear, and weekly sine/cosine.
- **Next direction:** research compact known-in-advance interactions, such as carrier with weekday, and continue checking that every derived feature is row-local.

## Experiment 31 — 667a6a2 — Eval AUC 0.6805 — discard

- Classification: exploration of a week-level seasonal feature.
- Hypothesis: a train-fitted category for the Monday-start week containing each flight could let trees group holiday or seasonal weeks.
- Rationale: a flight-arrival delay study includes week-of-year to capture holiday and seasonal trends ([MDPI study](https://www.mdpi.com/2079-9292/13/24/4910)).
- Change: added train-fitted categorical `WeekOfYear`, derived from row-local day-of-year and weekday alongside existing date features.
- Result: AUC fell to 0.6805; evaluation took 30.6 s. Reverted.
- Next: test week-of-year as an ordered numeric replacement for `DayOfYear`, rather than a separate category.

## Experiment 32 — 577f311 — Eval AUC 0.6840 — discard

- Classification: comparison of ordered seasonal resolutions.
- Hypothesis: a numeric week index could provide a coarser seasonal signal than day-of-year while keeping weekly wraparound features.
- Change: replaced numeric `DayOfYear` with a Monday-start `WeekOfYear` index derived per row from date and weekday; kept weekly sine/cosine.
- Result: AUC fell to 0.6840; evaluation took 27.8 s. Reverted to `DayOfYear`.
- Next: test depth 3 with the current annual index and weekly-cycle representation.

## Experiment 33 — 7961f29 — Eval AUC 0.6845 — discard

- Classification: follow-up to the compact calendar feature result.
- Hypothesis: the annual index and weekly cycles might allow a depth-3 model to match depth 4 with less complexity.
- Change: reduced `max_depth` from 4 to 3; kept the current feature set and other settings.
- Result: AUC was 0.6845, below the 0.6850 best; evaluation took 27.9 s. Reverted to depth 4.
- Next: test `colsample_bytree=0.9` to check whether retaining slightly more features per tree improves the current compact model.

## Experiment 34 — 4836fac — Eval AUC 0.6842 — discard

- Classification: follow-up to column subsampling.
- Hypothesis: 0.9 might preserve more useful signal than 0.8 while retaining some tree diversity.
- Change: raised `colsample_bytree` from 0.8 to 0.9.
- Result: AUC fell to 0.6842; run completed in 29.5 s. Reverted to 0.8.
- Plateau note: three recent experiments have been within 0.001 of the current best but did not improve it. Researching new interaction ideas before another trial.

## Experiment 35 — ef4a789 — Eval AUC 0.6832 — discard

- Classification: exploration of airline-by-weekday interaction.
- Hypothesis: weekday delay effects may vary with airlines' schedules; a carrier-weekday category could capture this heterogeneity.
- Rationale: a flight-delay causal analysis reports heterogeneous weekday effects and discusses travel demand and airline schedule variation as a possible source ([study](https://doi.org/10.1016/j.ijtst.2022.01.007)). The train set had 140 carrier-weekday combinations, median support 1,345, no singletons.
- Change: added a train-fitted `CarrierWeekday` category; unseen combinations map to missing.
- Result: AUC fell to 0.6832; evaluation took 33.2 s. Reverted.
- Next: test a denser month-by-weekday category for season-specific weekday effects.

## Experiment 36 — 715f602 — Eval AUC 0.6832 — discard

- Classification: exploration of seasonal weekday interaction.
- Hypothesis: the effect of weekdays could change with the season, so a train-fitted Month×DayOfWeek category may capture non-additive patterns.
- Change: added a row-local, train-fitted categorical MonthWeekday feature alongside the existing annual and weekly numeric features.
- Result: AUC fell to 0.6832; evaluation took 33.4 s. Reverted.
- Next: final trial tests modest L2 leaf regularization.

## Experiment 37 — 94cfa61 — Eval AUC 0.6850 — discard

- Classification: final regularization check.
- Hypothesis: modestly stronger L2 leaf regularization could improve year-to-year generalization.
- Rationale: XGBoost documents larger `reg_lambda` as more conservative ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: set `reg_lambda=2.0` on the current best model.
- Result: AUC matched 0.6850; runtime was 29.4 s versus 29.8 s for the best. This is too small to establish a speed-up, and the code is not simpler, so discarded.

## Final summary

- **Best Eval AUC:** 0.6850 at commit `28a9f98`.
- **What worked:** depth 4, 200 trees at learning rate 0.05, and `colsample_bytree=0.8`; a linear `DayOfYear` feature; replacing categorical DayOfWeek with weekly sine/cosine; removing separate Month and DayofMonth categories. Eval AUC improved from the 0.6743 baseline by 0.0107.
- **What did not:** raw Origin–Dest and carrier-time/day interactions, departure-hour encodings, week categories, month/day categories alongside DayOfYear, deeper/shallow depth alternatives, row subsampling, more trees with smaller updates, stronger category/split regularization, DART, and a higher histogram bin count.
- **Next:** evaluate kept models on the human-only holdout after the run. For future model research, explore airport-by-time effects using compact encodings and continue to avoid row-frequency features.
