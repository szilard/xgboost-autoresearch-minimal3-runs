# Experiment research log

## Setup and baseline

- Branch: `oct6`.
- Baseline commit `b15ec66`: unmodified starter model (`XGBClassifier`, 100 trees, depth 6, learning rate 0.1; native categorical support), Eval AUC 0.6743, status `keep`.
- Baseline establishes the comparison point. No training or evaluation changes were made.

## Experiment 1 — shallower trees (exploration)

- Hypothesis: reducing `max_depth` from 6 to 4 may improve transfer from the 2005 training sample to the 2006 evaluation sample by limiting interaction complexity, while preserving the baseline tree count and learning rate.
- Motivation: XGBoost's parameter tuning notes identify `max_depth` as a direct model-complexity control for the bias-variance tradeoff ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). The dataset has only 200K rows and several sparse categorical combinations (283 origins/destinations plus carrier), so deeper interactions may be noisy across years.
- Change: `max_depth=4`; all other model and feature settings stay at baseline.
- Result: Eval AUC 0.6789 (+0.0046 vs baseline), status keep; commit `2686e0b`.

## Experiment 2 — minimum child weight (follow-up)

- Hypothesis: build on the depth-4 gain by setting `min_child_weight=25`, which limits splits that isolate very small/noisy groups. With logistic loss, this is a Hessian threshold rather than a raw row count, but near-uncertain observations contribute about 0.25 each; 25 therefore discourages leaves supported by only a few dozen records.
- Motivation: the XGBoost tuning guide lists `min_child_weight` among the direct complexity controls and explains that raising it discourages splits on small subsets ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). This is a distinct regularizer from the successful depth cap.
- Change: on top of kept `max_depth=4`, set `min_child_weight=25`; all other settings stay fixed.
- Result: Eval AUC 0.6791 (+0.0002 vs prior, +0.0048 vs baseline), status keep; commit `194d5f4`.

## Experiment 3 — split gain threshold (follow-up)

- Hypothesis: require `gamma=1` for a split, on top of the kept depth and child-weight settings. The child-weight threshold limits small leaves; `gamma` separately rejects splits whose objective improvement is weak, which may reduce noisy branches further.
- Motivation: the XGBoost tuning notes identify `gamma` as another direct complexity control ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). The previous `min_child_weight=25` result improved AUC by 0.0002, so this tests a different regularization mechanism rather than repeating that setting.
- Change: add `gamma=1`; preserve `max_depth=4` and `min_child_weight=25`.
- Result: Eval AUC 0.6791 (equal to prior at four decimals), status discard; commit `f2a8b74` reset to `194d5f4`.

## Experiment 4 — row subsampling (exploration)

- Hypothesis: set `subsample=0.8` on the current best to add row-level randomness during tree construction, which may reduce sensitivity to year-specific patterns in the 2005 sample.
- Motivation: the XGBoost tuning notes recommend `subsample` as one way to add randomness and improve robustness ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). Experiment 3 showed `gamma=1` did not move the score, so this tests a different regularization mechanism.
- Change: set `subsample=0.8`; preserve all kept settings.
- Result: Eval AUC 0.6784 (below kept 0.6791), status discard; commit `558859f` reset to `194d5f4`.

## Experiment 5 — scheduled departure hour (exploration)

- Hypothesis: add a categorical `ScheduledDepHour` derived row-by-row from `CRSDepTime` while retaining the raw HHMM field. Hour-of-day effects may be non-monotonic (e.g. distinct operating waves); a native categorical split can group non-adjacent hours, whereas a threshold on raw HHMM only separates adjacent ranges.
- Research: an airline-delay project lists scheduled departure time among useful prediction features ([Stanford project](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)). Scikit-learn's time-feature guide discusses categorical hour steps and cyclical encodings ([guide](https://scikit-learn.org/1.5/auto_examples/applications/plot_cyclical_feature_engineering.html)); XGBoost supports partition-based categorical splits ([docs](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/categorical.html)).
- Data check: all training `CRSDepTime` values are valid HHMM (0005–2359), so integer division by 100 extracts the scheduled hour.
- Change: derive `ScheduledDepHour` inside `prepare(df)` and use fixed levels 0–23; this is row-local and uses no evaluation-frame aggregation.
- Result: Eval AUC 0.6784 (below kept 0.6791), status discard; commit `9e15f89` reset to `194d5f4`.

## Experiment 6 — cyclic scheduled-time encoding (exploration)

- Hypothesis: add sine and cosine of minutes since midnight while retaining raw HHMM. Unlike the rejected hourly category, this directly makes 23:59 adjacent to 00:05 and gives the model a smooth circular representation at the midnight boundary.
- Research: scikit-learn's time-feature guide describes sine/cosine transforms with the period as a compact encoding that removes the discontinuity between the first and last time step, and notes that tree models can model non-monotonic effects from raw ordinal time ([guide](https://scikit-learn.org/1.5/auto_examples/applications/plot_cyclical_feature_engineering.html)). Scheduled departure time is used as a predictor in the Stanford airline-delay project ([paper](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)).
- Data check: the training sample includes valid HHMM rows just after midnight and late at night; use a 1440-minute daily period.
- Change: add `DepTimeSin` and `DepTimeCos` inside `prepare(df)`; preserve raw HHMM and the kept model settings.
- Result: Eval AUC 0.6798 (+0.0007 vs prior, +0.0055 vs baseline), status keep; commit `3d95ef4`.

## Experiment 7 — second daily harmonic (follow-up)

- Hypothesis: add sine and cosine at twice the daily frequency to the winning first-harmonic features. This gives the trees a representation for two within-day peaks (such as morning and evening waves) that one full-day cycle may smooth together.
- Motivation: the first cyclic encoding improved Eval AUC by 0.0007. Scikit-learn's time-feature guide specifically notes that higher harmonics or additional trigonometric terms can represent more detailed variation within the natural period ([guide](https://scikit-learn.org/1.5/auto_examples/applications/plot_cyclical_feature_engineering.html)).
- Change: add `DepTimeSin2` and `DepTimeCos2` with period 720 minutes, retaining raw HHMM and the first harmonic.
- Result: Eval AUC 0.6800 (+0.0002 vs prior, +0.0057 vs baseline), status keep; commit `a4199d9`.

## Experiment 8 — cyclic month features (follow-up)

- Hypothesis: extend the improving daily cyclic representation to annual seasonality by adding sine and cosine of month-of-year. This makes December and January neighbors while retaining the existing month category.
- Motivation: the daily cyclic family produced sequential improvements (0.6798, then 0.6800). Scikit-learn's time-feature guide demonstrates monthly sine/cosine features with a 12-month period ([guide](https://scikit-learn.org/1.5/auto_examples/applications/plot_cyclical_feature_engineering.html)); the Stanford airline-delay project includes month of year among predictive features ([paper](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)).
- Change: add `MonthSin` and `MonthCos` computed from each row's `Month`, retaining the native month category and daily time features.
- Result: Eval AUC 0.6800 (equal to prior at four decimals; no simplification), status discard; commit `1647db8` reset to `a4199d9`.

## Experiment 9 — cyclic weekday features (exploration)

- Hypothesis: encode weekday as sine/cosine over a 7-day period, retaining the native category. This lets the model represent the week boundary directly (weekend-to-Monday adjacency) without forcing a linear ordering.
- Motivation: weekday effects matter in flight delays, and scikit-learn's time-feature guide demonstrates sine/cosine transforms for a 7-step weekday period ([guide](https://scikit-learn.org/1.5/auto_examples/applications/plot_cyclical_feature_engineering.html)). This differs from the daily clock features because it represents weekly calendar structure.
- Change: add `DayOfWeekSin` and `DayOfWeekCos` inside `prepare(df)`; preserve all kept daily features.
- Result: Eval AUC 0.6800 (equal to prior at four decimals; no simplification), status discard; commit `816c82d` reset to `a4199d9`.

## Experiment 10 — lower learning rate with more rounds (follow-up)

- Hypothesis: use `learning_rate=0.05` and `n_estimators=200` instead of 0.1/100, keeping the nominal total step size similar while letting the ensemble build more gradually. This may improve generalization of the current best without changing features or tree complexity.
- Motivation: XGBoost's tuning notes recommend reducing `eta` while increasing the number of boosting rounds ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). The weekly and monthly cyclic ablations tied, so this returns to an independent model-training axis.
- Change: set `learning_rate=0.05`, `n_estimators=200`; preserve the best feature set, `max_depth=4`, and `min_child_weight=25`.
- Result: Eval AUC 0.6802 (+0.0002 vs prior, +0.0059 vs baseline), status keep; commit `32beb38`.

## Synthesis after 10 experiments

- Best so far: Eval AUC 0.6802 at commit `32beb38` (`max_depth=4`, `min_child_weight=25`, daily departure-time sine/cosine through the second harmonic, `learning_rate=0.05`, `n_estimators=200`). This is +0.0059 over the baseline.
- Helped: reducing depth from 6 to 4 gave the largest gain (+0.0046); `min_child_weight=25` added +0.0002; cyclic departure time added +0.0007 and its second harmonic another +0.0002; halving learning rate with twice the rounds added +0.0002.
- Did not help: `gamma=1` tied without simplification; row subsampling, a standalone hour category, month cycles, and weekday cycles all scored lower or tied without a simplification.
- Current theory: keeping tree complexity moderate helps across the year shift, and smooth daily timing features add signal the raw HHMM representation misses. Further work should explore useful row-level interactions among carrier, route, and schedule, plus categorical-split settings, rather than adding calendar cycles indiscriminately.
- Next direction: research high-cardinality route interactions and XGBoost categorical split controls before testing one targeted feature or setting.

### Research refresh after experiment 10

- XGBoost documents `max_cat_to_onehot` as the threshold between one-hot and partition-based categorical splits; the prior default was 4, while the 3.5 development docs note a later default change ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html), [categorical docs](https://xgboost.readthedocs.io/en/latest/parameter.html)). This environment has XGBoost 3.4.1.
- The current low-cardinality categorical features have 7–31 levels (weekday, month, carrier, day of month), while origin and destination each have 283. A threshold of 32 cleanly tests one-hot splits for the former while retaining partition splits for airports.
- Scikit-learn's TargetEncoder uses cross-fitting in `fit_transform` because using each row's own label in its encoded value leaks target information ([docs](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). Given this harness's row-wise `prepare` contract, target encodings would require careful train/eval handling, so they are not the next experiment.

## Experiment 11 — one-hot splits for low-cardinality categories (exploration)

- Hypothesis: set `max_cat_to_onehot=32`. The existing month, day-of-month, weekday, and carrier features then use one-hot splits, allowing direct level-specific effects; origin and destination retain partition-based splits because they each have 283 levels.
- Motivation: this isolates the categorical split strategy, a new direction identified in the 10-experiment research refresh. XGBoost documents the threshold's effect on categorical splits ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Change: add `max_cat_to_onehot=32`; preserve the current best features and tree parameters.
- Result: Eval AUC 0.6798 (below kept 0.6802), status discard; commit `d6c3bdc` reset to `32beb38`.

## Experiment 12 — cap airport category split candidates (follow-up)

- Hypothesis: add `max_cat_threshold=32` while retaining the partition-based splits that scored better in experiment 11. This parameter limits the categories considered per partition split and may regularize the two 283-level airport features.
- Motivation: the official XGBoost parameter docs say `max_cat_threshold` applies to partition-based categorical splits and is intended to help prevent overfitting ([source](https://xgboost.readthedocs.io/en/stable/parameter.html)). Experiment 11 found that one-hot splits for lower-cardinality features were not helpful; this tests regularization of the high-cardinality airport features instead.
- Change: set `max_cat_threshold=32`; keep the default partition strategy and best model settings.
- Result: Eval AUC 0.6799 (below kept 0.6802), status discard; commit `a429e6b` reset to `32beb38`.

## Experiment 13 — depth 3 (follow-up)

- Hypothesis: lower `max_depth` from the kept value 4 to 3, keeping `min_child_weight=25` and the slower learning schedule. Experiment 1's depth reduction produced the largest gain; another step down tests whether the year-shift benefit continues or begins to underfit.
- Motivation: XGBoost's tuning guide describes `max_depth` as a direct bias-variance/model-complexity control ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). The two categorical split setting trials did not improve the score, so return to the strongest observed axis.
- Change: `max_depth=3`; all other kept settings unchanged.
- Result: Eval AUC 0.6802 (equal to prior at four decimals; shallower trees kept as simpler), status keep; commit `fc4aaca`.

## Experiment 14 — smaller boosting steps (follow-up)

- Hypothesis: reduce `learning_rate` from 0.05 to 0.025 and double `n_estimators` from 200 to 400 on the current depth-3 best. The previous paired reduction improved AUC; a second, smaller step may improve transfer further.
- Motivation: XGBoost's tuning guide recommends reducing the step size while increasing boosting rounds ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: `learning_rate=0.025`, `n_estimators=400`; preserve all other current-best settings.
- Result: Eval AUC 0.6806 (+0.0004 vs prior, +0.0063 vs baseline), status keep; commit `2512b87`.

## Experiment 15 — smaller boosting steps, second follow-up

- Hypothesis: reduce `learning_rate` from 0.025 to 0.0125 and increase `n_estimators` from 400 to 800 on the current best. Both prior paired halvings improved Eval AUC, suggesting smaller updates may continue to help cross-year generalization.
- Motivation: follow-up to experiment 14's +0.0004 improvement and XGBoost's recommendation to pair lower step sizes with more rounds ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: `learning_rate=0.0125`, `n_estimators=800`; preserve the rest of the best configuration.
- Result: Eval AUC 0.6807 (+0.0001 vs prior, +0.0064 vs baseline), status keep; commit `895f60c`.

## Experiment 16 — smaller boosting steps, third follow-up

- Hypothesis: halve `learning_rate` again to 0.00625 and double to 1600 trees. The previous two reductions improved AUC, though by a smaller amount on the latest step; this tests whether that trend continues before moving on.
- Motivation: continuing the successful shrinkage/round-count sequence recommended in XGBoost tuning notes ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Change: `learning_rate=0.00625`, `n_estimators=1600`; preserve all other current-best settings.
- Result: Eval AUC 0.6806 (below kept 0.6807), status discard; commit `b233f1f` reset to `895f60c`.

## Experiment 17 — stronger minimum child weight (follow-up)

- Hypothesis: increase `min_child_weight` from 25 to 50 on the current 800-round ensemble. Larger thresholds can reduce small/noisy leaves and may help year-to-year transfer.
- Motivation: the XGBoost tuning guide lists `min_child_weight` as a direct complexity control and explains that raising it discourages splits on small subsets ([source](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). This changes leaf support while preserving the current depth, feature set, and learning schedule.
- Change: `min_child_weight=50` instead of 25.
- Result: Eval AUC 0.6807 (equal to prior at four decimals; no simplification), status discard; commit `275677a` reset to `895f60c`.

### Research note: carrier target-rate lookup

- The training-only carrier summary ranges from 0.138 to 0.626 delay rate; support per carrier ranges from 916 to 31,373 rows (median 9,621). These counts are for data understanding only and are not model features.
- Airline identity is a known predictor in the Stanford airline-delay project ([paper](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)). Scikit-learn describes target encoding as a shrunk category-conditioned target mean and recommends cross-fitting to prevent leakage ([docs](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). This experiment uses only a static carrier lookup fitted on `train`, so each row receives the same value from the same lookup in training and evaluation. It does include each training row in its carrier mean; with at least 916 rows per carrier, an individual label can move the mean by at most about 0.0011. The harness's held-out-year AUC will determine whether the lookup generalizes.

## Experiment 18 — carrier delay-rate lookup (exploration)

- Hypothesis: add the train-fitted mean delay label for each carrier as a numeric feature. This compactly orders carriers by their observed delay propensity and may complement native categorical carrier splits in shallow trees.
- Change: fit `carrier_delay_rate` once from `train` above `prepare`; map it onto each row inside `prepare(df)`. No count feature is added, and the lookup is independent of the input frame size.
- Result: Eval AUC 0.6807 (equal to prior at four decimals; no simplification), status discard; commit `b04f4fe` reset to `895f60c`.

### Plateau research refresh after experiments 16–18

- A flight-delay study describes route as a useful flight identifier and compares predictions with historical route averages ([Stanford project](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)). XGBoost's interaction-constraint guide explains that unrestricted tree paths can capture spurious interactions and that domain-grounded interactions can improve generalization ([docs](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html)).
- The training sample contains 4,290 directed origin-destination pairs (median 32 rows per route). This supports trying route identity as an explicit categorical interaction while avoiding route counts or target-derived route rates.
- Current direction: expose the origin-destination pair as a train-fitted categorical level. A shallow tree can then make one route split instead of spending separate levels on origin and destination.

## Experiment 19 — explicit route category (exploration)

- Hypothesis: add `Route = Origin + "-" + Dest` as a native categorical feature while retaining `Origin` and `Dest`. This makes route-level interactions available in one split, which is useful with the currently successful depth-3 trees.
- Research: flight-delay work identifies route as a meaningful unit for historical reliability ([Stanford project](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)); XGBoost supports partition-based categorical splits ([categorical docs](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/categorical.html)).
- Change: fit route levels and a code lookup from `train`; in `prepare(df)`, derive each row's route and use those fixed levels, with unseen routes mapped to missing. No route frequency or target statistic is used.
- Result: Eval AUC 0.6747 (below kept 0.6807), status discard; commit `e5bb78e` reset to `895f60c`.

### Plateau research refresh: probability averaging

- Dietterich's ensemble survey describes combining classifiers by weighted votes and explains when ensembles can improve performance ([paper](https://doi.org/10.1007/3-540-45014-9_1)). Scikit-learn's `VotingClassifier` supports soft voting by averaging predicted probabilities and recommends it when member probabilities are useful ([docs](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html)).
- The current depth-3 model is the best individual model (0.6807); earlier depth-3 and depth-4 models both scored 0.6802. Test whether averaging the best depth-3 model with a same-feature depth-4 model adds complementary rankings.

## Experiment 20 — soft average of depth-3 and depth-4 models (exploration)

- Hypothesis: average probabilities from two XGBoost models with identical features and learning schedule, varying only depth (3 vs 4). The deeper member may recover useful interactions while the shallow member preserves the stronger cross-year generalization; averaging may reduce model-specific errors.
- Research: ensembles combine predictions from multiple classifiers ([Dietterich](https://doi.org/10.1007/3-540-45014-9_1)); scikit-learn provides soft probability voting ([docs](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html)).
- Change: replace the single estimator with `VotingClassifier(voting="soft")` containing depth-3 and depth-4 XGBClassifier instances, each using 800 trees, learning rate 0.0125, and `min_child_weight=25`.
- Result: Eval AUC 0.6810 (+0.0003 vs prior, +0.0067 vs baseline), status keep; commit `17f5fd8`.

## Synthesis after 20 experiments

- Best so far: Eval AUC 0.6810 at commit `17f5fd8`, a soft average of depth-3 and depth-4 XGBoost models (each 800 trees, learning rate 0.0125, minimum child weight 25), using raw HHMM plus daily cyclic features through the second harmonic. This is +0.0067 over baseline.
- Helped: depth 4 over the starter's depth 6 (+0.0046); `min_child_weight=25` (+0.0002); daily cyclic features (+0.0007) and their second harmonic (+0.0002); smaller learning rates with more rounds raised AUC through 0.0125/800; depth 3 tied the earlier score with a simpler tree; soft averaging depth 3 and 4 added +0.0003.
- Did not help: gamma, row subsampling, discrete hour category, monthly/weekday cycles, categorical split changes, stronger child-weight regularization, carrier target-rate lookup, and explicit route category.
- Current theory: modest tree depth, smoother boosting, and daily timing shape transfer best across years. The ensemble adds a small gain. Broad categorical and route encodings have been noisy; next try a compact calendar feature with a clear operational rationale.
- Next direction: major U.S. holiday proximity, after checking the weekday encoding used by this dataset.

### Research refresh after experiment 20: holiday calendar

- The Stanford airline-delay project includes holiday proximity as a predictor ([paper](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)); Microsoft Learn's flight-delay tutorial also derives a holiday indicator from the flight date ([tutorial](https://learn.microsoft.com/en-us/fabric/data-science/r-flight-delay)). BTS publishes holiday-specific on-time delay details, including the 2005–2008 period ([BTS Thanksgiving delays](https://transtats.bts.gov/HolidayDelay_Detail.asp)).
- The BTS reporting directive confirms `DayOfWeek` uses Monday=1 through Sunday=7 ([directive](https://www.bts.gov/explore-topics-and-geography/modes/aviation/number-39-technical-directive-reporting-time)); convert this to weekday offsets when identifying moving holidays.

## Experiment 21 — major U.S. holiday travel window (exploration)

- Hypothesis: add a row-local binary flag for flights near New Year's, Memorial Day, Independence Day, Labor Day, Thanksgiving, or Christmas. Holiday travel can change demand and airport congestion in ways not captured by month or weekday alone.
- Change: derive `USHolidayWindow` only from each row's month, day of month, and weekday; identify moving holidays from calendar rules. No external calendar file, data aggregation, or label lookup is used.
- Result: Eval AUC 0.6810 (equal to prior at four decimals; no simplification), status discard; commit `9aae12a` reset to `17f5fd8`.

## Experiment 22 — favor the depth-3 ensemble member (follow-up)

- Hypothesis: change soft-voting weights from equal to `[2, 1]` for depth 3 and depth 4. The depth-3 member is the best individual model (0.6807), so it may deserve more influence while retaining depth 4's complementary splits.
- Motivation: equal-probability averaging improved AUC by 0.0003. Scikit-learn's `VotingClassifier` supports explicit weights for probability averaging ([docs](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html)).
- Change: set `weights=[2, 1]`; keep both fitted models and all their settings unchanged.
- Result: Eval AUC 0.6810 (equal to prior at four decimals; no simplification), status discard; commit `47d58a9` reset to `17f5fd8`.

## Experiment 23 — depth-4-only ablation (ablation/simplification)

- Hypothesis: keep only the depth-4 member of the winning soft ensemble, using its same 800-tree, 0.0125 schedule. The earlier depth-3 and depth-4 single-model settings tied at 0.6802; the depth-4 member may now be strong enough alone to match the ensemble.
- Motivation: the winning equal-weight ensemble scored 0.6810, while changing weights did not help. This tests whether the second model is needed; an equal score would allow a simpler and faster artifact.
- Change: replace the depth-3/depth-4 `VotingClassifier` with one depth-4 `XGBClassifier`; retain all features and model parameters otherwise.
- Result: Eval AUC 0.6799 (below kept 0.6810), status discard; commit `7525671` reset to `17f5fd8`.

## Experiment 24 — add a depth-2 ensemble member (follow-up)

- Hypothesis: add a depth-2 XGBoost model with a 20% vote share to the current depth-3/depth-4 ensemble (`weights=[1, 2, 2]`). Its simpler decision shapes may provide complementary rankings while the depth-3 and depth-4 models retain most of the weight.
- Motivation: soft averaging improved AUC by 0.0003 and depth-4 alone was worse than the ensemble. Ensemble methods benefit from combining accurate, diverse classifiers ([Dietterich](https://doi.org/10.1007/3-540-45014-9_1)); this adds a new tree depth with deliberately limited influence.
- Change: train 800-tree models at depths 2, 3, and 4 with the same remaining parameters; soft-vote with weights `[1, 2, 2]`.
- Result: Eval AUC 0.6806 (below kept 0.6810), status discard; commit `3d17dc0` reset to `17f5fd8`.

### Research refresh after experiment 24: dropout regularization

- XGBoost's DART booster drops selected existing trees during boosting rounds to address over-specialization; it uses the same tree parameters as `gbtree` and adds `rate_drop` and `skip_drop` controls ([official DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html)).
- The original DART paper motivates dropout as a way to limit later trees from becoming overly specialized to a small subset of examples ([PMLR paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html)). This is a meaningfully different regularization direction after several ensemble and feature tweaks tied or regressed.

## Experiment 25 — replace gbtree with DART (exploration)

- Hypothesis: DART's stochastic tree dropout may reduce over-specialization and improve held-out ranking relative to the plateaued gbtree ensemble.
- Change: keep the depth-3/depth-4 soft-voting ensemble, features, tree counts, learning rate, and child weight fixed. Change both boosters to DART with `rate_drop=0.1`, `skip_drop=0.5`, and the existing fixed random seed.
- Result: training timed out at the harness's 60-second limit; no Eval AUC. Status crash; commit `ffc8d70` reset to `17f5fd8`. The installed XGBoost warns that `booster=dart` is deprecated, and the two-member DART fit exceeded the budget.

## Experiment 26 — annual day-of-year harmonic (follow-up)

- Hypothesis: a smooth annual phase may represent seasonal progression within months and across month boundaries, complementing the existing categorical month and day features. The prior month-only sine/cosine cycle tied, so this tests a finer calendar phase.
- Change: derive a non-leap day-of-year from each row's `Month` and `DayofMonth`, then add its first sine/cosine harmonic with a 365-day period. No fitted statistics or external calendar lookup.
- Implementation note: the dataset encodes month/day as strings like `c-11`; the row-local preparation parses the numeric suffix before computing day-of-year.
- Result: Eval AUC 0.6826, improved from 0.6810; status keep; commit `03bbc84`.

## Experiment 27 — second annual harmonic (follow-up)

- Hypothesis: after the first annual cycle improved AUC by 0.0016, a second harmonic may represent two broad seasonal peaks while preserving the annual phase.
- Change: add sine/cosine terms at twice the annual frequency to the existing day-of-year features; leave the base model and other features unchanged.
- Result: Eval AUC 0.6822 (below the first-harmonic 0.6826); status discard; commit `7d831ef` reset to `03bbc84`.

## Final summary

- Best: Eval AUC 0.6826 at commit `03bbc84`, up from the 0.6743 baseline. The kept model is the equal-weight depth-3/depth-4 soft-voting ensemble with daily departure-time harmonics and a first annual day-of-year harmonic.
- What helped: moderate depth, a slower learning-rate schedule, soft voting, and the continuous annual calendar phase. The annual first harmonic added the largest final gain, from 0.6810 to 0.6826.
- What did not help: gamma, row subsampling, a discrete departure-hour category, cyclic month/weekday features, categorical split settings, stronger child-weight regularization, carrier target-rate lookup, route category, holiday window, vote reweighting, depth-4-only and depth-2 ensemble variants, and the second annual harmonic. The DART trial timed out during training.
- Next direction: consider a low-cardinality carrier-by-coarse-departure-time interaction. A standalone hour feature and a route category were not useful, but a compact schedule interaction may capture airline-specific operating patterns.
- A 366-day phase was considered but not run: the training data has no February 29 examples, and the experiment clock was below two minutes.
