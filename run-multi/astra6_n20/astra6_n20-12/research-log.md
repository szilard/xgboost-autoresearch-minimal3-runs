# Research log: oct6

## Setup — 2026-10-06

- Branch: `oct6`, created directly from starting commit `b15ec66`.
- Objective: maximize harness-reported Eval AUC for 15-minute flight departure delays.
- Read `program.md`, `train.py`, and `harness.py`.
- Verified `data/train.csv` and `data/eval.csv` exist.
- Training data: 200,000 rows, 9 expected columns, no missing values; 100,000 Y and 100,000 N labels.
- Environment: Python 3.14.4, pandas 3.0.6, NumPy 2.5.3, XGBoost 3.4.1, scikit-learn 1.9.1, cloudpickle 3.1.2; 8 available CPU cores.
- Git identity is configured and the starting working tree is clean.
- Initialized `results.tsv` with its header only; no baseline has been run.

## First run

After setup confirmation, the first action is `python3 harness.py start`, followed by the unmodified baseline via `python3 harness.py run`. The baseline uses 100 estimators, maximum depth 6, learning rate 0.1, native categorical features, and random seed 42.

The experiment budget is one hour, with a 60-second training limit and a 300-second evaluation limit per run. Research external sources before the first non-baseline experiment, every 10 experiments, at plateaus, and before a new category of change. Record hypotheses, sources, commits, results, and keep/discard decisions here throughout the run.

## Baseline — b15ec66

Eval AUC: **0.6743**. Training 1.6s including startup, evaluation 31.1s, total 32.6s. Keep as starting reference. Clock started after user confirmation.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): regularize tree complexity, add sampling, and pair smaller learning rates with more trees. Initial useful directions: depth 3–6, learning rate 0.03–0.1, min_child_weight 10–50, subsample 0.8–1.0; these are experiment choices, not universal optima.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): leaf-weight and category-split controls offer ways to reduce overfitting across years.
- [Categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): preserve training category identities and native categorical splits.
- [Time-related features](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): calendar components and periodic encodings motivate schedule features; assess on the harness's cross-year evaluation.
- [TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html): naive training target means can leak labels; avoid direct unsmoothed target encoding, and respect this task's prohibition on independent cross-validation/evaluation.
- [pandas Categorical](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html): specified category levels already map unseen labels to NaN.

## Experiment 1 — preprocessing simplification

Classification: ablation/simplification of the baseline.
Hypothesis: constructing the prepared frame once and letting Categorical handle unseen levels preserves predictions while reducing per-row overhead. Baseline spends 31s evaluating; faster preparation allows more meaningful experiments within the hour.
Change: remove redundant membership masks and repeated frame assignments; preserve column order, category levels, model settings, and row index.

Result: **0.6743**, commit 14af273, **keep**. The AUC is unchanged and redundant processing is removed.
Run time: 20.1s (training 1.4s, eval 18.6s, ok)

## Experiment 2 — 500 trees, depth 4, learning rate 0.05, minimum child weight 20, L2 10, row subsample 0.9

Classification: exploration.
Hypothesis: Shallower trees with more boosting steps and stronger leaf regularization may retain stable schedule effects while reducing cross-year overfitting. Test a deliberately regularized configuration against the starter.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html

Implementation note: experiment 1 exposed pandas deprecation warnings for unknown levels. Cached Index.get_indexer plus Categorical.from_codes now handles them explicitly as -1. Prepared features match the baseline, including a synthetic unknown airport, and match between batch and single-row calls.

Result: **0.6797**, commit b95c3da, **keep**. Tests whether reduced interaction complexity and stronger leaf regularization generalize across years.
Run time: 11.6s (training 2.6s, eval 9.0s, ok)

## Experiment 3 — remove categorical DayofMonth

Classification: ablation/simplification.
Hypothesis: Day-of-month has jagged training delay rates and enables month/day combinations that may memorize 2005-specific disruptions. Removing it may preserve recurring seasonality while improving cross-year generalization.

Result: **0.6797**, commit 0eb7523, **keep**. Ablates a calendar variable suspected of carrying year-specific disruption patterns.
Run time: 11.0s (training 2.5s, eval 8.5s, ok)

Keep-rule check: experiment 3 ties at four decimals while using one fewer feature and running faster, so it qualifies as a retained simplification.

## Experiment 4 — one-hot categorical splits via max_cat_to_onehot=512

Classification: exploration.
Hypothesis: Partition-based airport/category splits can fit unstable groups. One-hot splits isolate each category and may reduce cross-year variance, at the cost of requiring more trees for broad effects.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html

Result: **0.6780**, commit 70e1e86, **discard**. Contrasts independent category effects with partition-based category groups.
Run time: 10.6s (training 2.2s, eval 8.4s, ok)

## Experiment 5 — add departure hour, minute, and cyclical time features

Classification: exploration.
Hypothesis: Departure time dominates model gain. Exposing minute-of-hour, hour, and periodic time coordinates may capture airline departure banks and late-night behavior with fewer tree interactions.
Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html ; https://www.sciencedirect.com/science/article/pii/S0969699708000550

Result: **0.6801**, commit 26fd5a1, **keep**. Checks whether explicit intraday structure adds transferable information beyond ordered scheduled departure time.
Run time: 12.4s (training 2.6s, eval 9.7s, ok)

## Experiment 6 — add route and carrier-airport categorical interactions

Classification: exploration.
Hypothesis: Airline operation and airport-pair effects may be hard for shallow trees to discover from separate categories. Explicit route and carrier-airport categories let splits represent those interactions directly.
Source: https://www.sciencedirect.com/science/article/pii/S0969699708000550 ; https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html

Result: **0.6703**, commit 37c5371, **discard**. Tests explicit network interactions; row features passed batch/singleton, target-independence, and unknown-airport checks.
Run time: 21.5s (training 4.5s, eval 17.0s, ok)

## Experiment 7 — limit categorical split search with max_cat_threshold=8

Classification: follow-up.
Hypothesis: The high-cardinality interaction experiment lost 0.0098 AUC. The retained model also partitions airport categories; limiting the number of categories considered per split may reduce unstable grouping without forcing every category into a separate split.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature

Result: **0.6800**, commit 0ae9070, **discard**. Tests whether simpler category groupings reduce variance after the failed high-cardinality interaction experiment.
Run time: 12.1s (training 2.4s, eval 9.7s, ok)

## Experiment 8 — add airport distance-graph embedding

Classification: exploration.
Hypothesis: Route categories overfit, but geography could pool related airports. Fit three unsupervised coordinates from shortest-path route distances and expose origin/destination coordinates as continuous features. This may share regional patterns while avoiding target-derived encodings and row-frequency features.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html ; https://arxiv.org/abs/2207.06959

Result: **0.6800**, commit 16c3e31, **discard**. Unsupervised geographic lookups use only training route distances; row consistency and unknown-airport handling passed.
Run time: 13.9s (training 3.2s, eval 10.6s, ok)

## Experiment 9 — reduce tree depth to 3

Classification: follow-up.
Hypothesis: Additional detailed representations have not improved the cross-year metric. Halving the maximum leaves per tree by reducing depth from 4 to 3 tests whether low-order, more additive effects transfer better; all other retained settings stay fixed.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html

Result: **0.6809**, commit 90b46c6, **keep**. Tests a more additive hypothesis after detailed route and geographic representations failed to improve generalization.
Run time: 12.0s (training 2.2s, eval 9.7s, ok)

## Experiment 10 — 1500 depth-three trees at learning rate 0.03

Classification: follow-up.
Hypothesis: Depth-three trees improved AUC, suggesting low-order effects are useful. Increase boosting rounds from 500 to 1500 while lowering the step size from 0.05 to 0.03 to test whether this simple tree structure benefits from a more detailed additive fit.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html

Result: **0.6800**, commit c446bcb, **discard**. Tests whether more boosting improves the promising shallow model.
Run time: 14.8s (training 5.0s, eval 9.9s, ok)

## Synthesis after 10 experiments

Best: **0.6809**, commit `90b46c6`, versus baseline 0.6743 (+0.0066).

What helped: fast category lookup reduced evaluation from 31s to about 10s; conservative depth-four boosting improved discrimination; removing day-of-month preserved AUC with fewer features; explicit time components helped slightly; depth three improved further.

What did not: full one-hot category splits, high-cardinality route/carrier-airport interactions (large loss), tighter category partition limits, airport distance-graph coordinates, and more boosting rounds. None has been retained.

Current theory: the 2005-to-2006 shift rewards stable low-order schedule effects. Detailed categorical interactions and prolonged fitting can learn year-specific behavior. Investigate constrained seasonality, holiday-relative calendar features, and low-variance encodings rather than more arbitrary category combinations.

Research refresh: [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) permit separating feature groups to avoid spurious interactions. [BTS seasonal adjustment methodology](https://www.bts.gov/archive/subject-areas/economics_and_finance/deseasonalized_data_meaning) explains that moving holidays shift activity across calendar dates. This motivates holiday-relative features computed from the row's date and weekday. [Periodic time encodings](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) provide a smoother alternative to arbitrary month categories.

## Experiment 11 — isolate Month with interaction constraints

Classification: follow-up.
Hypothesis: Depth reduction helped and more fitting hurt. Isolating month as an additive component should prevent learning year-specific month-airport/carrier combinations while retaining overall seasonality.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html

Result: **0.6815**, commit 85855ee, **keep**. Isolates global seasonal effects from airport, carrier, and schedule interactions.
Run time: 11.9s (training 2.3s, eval 9.7s, ok)

## Experiment 12 — add holiday-relative offset and holiday identity

Classification: exploration.
Hypothesis: Moving holidays shift calendar dates between years. Pooling signed days to six major travel holidays may capture repeatable travel timing more robustly than arbitrary day-of-month. Dates are derived from each row's month/day/weekday, using the non-leap calendar shared by the supplied years.
Source: https://www.bts.gov/archive/subject-areas/economics_and_finance/deseasonalized_data_meaning

Result: **0.6840**, commit 99b5a33, **keep**. Calendar arithmetic checked on moving and fixed holidays in both supplied non-leap years, and batch/single-row features match.
Run time: 14.9s (training 2.9s, eval 11.9s, ok)

## Experiment 13 — ablate HolidayType while retaining HolidayOffset

Classification: ablation/simplification.
Hypothesis: Holiday features improved AUC by 0.0025. Remove holiday identity while retaining the pooled signed offset to test whether shared travel timing alone explains the gain, with fewer opportunities to memorize event-specific disruptions.

Result: **0.6823**, commit 1f2aac9, **discard**. Retain at equal AUC only because one categorical feature and its construction disappear.
Run time: 13.6s (training 2.9s, eval 10.7s, ok)

## Experiment 14 — add Martin Luther King Jr. Day and Presidents Day

Classification: follow-up.
Hypothesis: Removing holiday identity lost 0.0017 AUC, so distinct holiday effects matter. Add the two winter Monday holidays, whose travel dates also move between years, while preserving the existing six holiday identities.
Source: https://www.transtats.bts.gov/holidaydelay.asp

Result: **0.6842**, commit fd0abe0, **keep**. Extends the successful holiday-relative representation to two moving winter travel dates.
Run time: 15.0s (training 3.0s, eval 12.0s, ok)

## Experiment 15 — training-only reference target statistics

Classification: exploration.
Hypothesis: Raw interaction categories overfit. Smoothed category delay rates estimated on a separate 50,000-row reference subset may provide lower-variance route and schedule summaries. Fit XGBoost only on the other 150,000 rows so their labels cannot leak into the encodings. This is one reference/model split, with no cross-validation or additional metric; only the harness scores performance.
Source: https://papers.neurips.cc/paper_files/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf section 3.2

Result: **0.6823**, commit 8c9f9d0, **discard**. Reference rows supply risk tables; distinct rows fit the booster. No evaluation subset or cross-validation metric was introduced.
Run time: 16.2s (training 3.0s, eval 13.2s, ok)

## Experiment 16 — boosted forests with four parallel trees and sampling

Classification: exploration.
Hypothesis: Single-tree boosting appears sensitive to categorical noise. Average four independently sampled trees per boosting round, with row and node-level feature sampling, to stabilize fitted effects while preserving the successful low-depth and holiday representation.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html

Result: **0.6848**, commit 66224b1, **keep**. Tests variance reduction by averaging trees within the boosting process.
Run time: 24.3s (training 12.3s, eval 12.0s, ok)

## Experiment 17 — isolate DayOfWeek as well as Month

Classification: follow-up.
Hypothesis: Averaging sampled trees improved AUC to 0.6848, reinforcing the variance-reduction hypothesis. Separating weekday as its own effect tests whether location-specific weekday patterns also overfit, analogous to the successful month constraint.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html

Result: **0.6832**, commit 242d13a, **discard**. Checks whether the successful month separation also applies to weekday effects.
Run time: 23.6s (training 11.6s, eval 12.0s, ok)

## Experiment 18 — reduce boosted-forest rounds from 500 to 250

Classification: ablation/simplification.
Hypothesis: The earlier longer boosting horizon hurt AUC. With four-tree averaging now reducing noise, test half as many boosting rounds to see whether remaining late-stage fits still capture year-specific noise.

Result: **0.6837**, commit 2479704, **discard**. A shorter horizon qualifies as a simplification if it ties, and tests late-stage overfitting.
Run time: 19.1s (training 7.2s, eval 11.8s, ok)

## Experiment 19 — remove Month predictor and its interaction constraint

Classification: ablation/simplification.
Hypothesis: The month interaction constraint helped, but its global 2005 seasonal effect could still shift in 2006. Remove the month predictor entirely while preserving holiday calculations to measure whether broad month effects are useful at all.

Result: **0.6868**, commit 9752185, **keep**. Tests whether retaining only holiday-derived calendar detail is more transferable than the global month effect.
Run time: 24.6s (training 13.2s, eval 11.4s, ok)

## Experiment 20 — add coarse meteorological season as an additive feature

Classification: follow-up.
Hypothesis: Removing month improved AUC by 0.0020 while holiday features remain useful. A four-season additive effect pools neighboring months and could retain stable winter/summer structure with less year-specific detail than twelve independent month categories.
Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html

Result: **0.6852**, commit 175e802, **discard**. Tests whether pooled seasonal effects transfer better than twelve month categories.
Run time: 25.4s (training 13.0s, eval 12.4s, ok)

## Synthesis after 20 experiments

Best: **0.6868**, commit `9752185`; +0.0125 over the baseline.

Experiments 11–20 established that holiday-relative timing transfers better than broad seasonal effects. Removing holiday identity lost AUC, adding winter Monday holidays helped slightly, and removing the Month predictor helped substantially. Four-tree boosted forests also improved the result. Weekday interactions are useful: forcing weekday to be additive hurt. Coarse seasons and halving the boosting rounds both lost AUC. Separate-reference target statistics did not justify sacrificing booster-training rows.

Current theory: recurring calendar events and schedule patterns are more reliable than broad month-specific 2005 delay rates. Average weak models to stabilize noisy categorical effects while preserving weekday/schedule interactions.

Research refresh: [Friedman, Stochastic gradient boosting](https://www.sciencedirect.com/science/article/pii/S0167947301000652) and [DART](https://proceedings.mlr.press/v38/korlakaivinayak15.html) suggest sampling and dropout as distinct variance-control mechanisms. [XGBoost ranking](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) offers a pairwise loss that could align training with ranking quality; it is a future experiment, not a change to the harness metric. Crucially, [BTS reporting metadata](https://www.bts.gov/browse-statistical-products-and-data/statistical-products/airline-time-statistics) confirms that HP and US began reporting jointly as US in 2006. This motivates a concrete carrier-code harmonization rather than a guessed category grouping.

## Experiment 21 — normalize carrier HP to US

Classification: exploration.
Hypothesis: BTS documents a 2006 reporting shift from separate America West (HP) and US Airways (US) to joint US reporting. Pool those labels in training and preparation so the learned US category reflects both operations when scoring 2006 flights.
Source: https://www.bts.gov/browse-statistical-products-and-data/statistical-products/airline-time-statistics

Result: **0.6871**, commit f02dba3, **keep**. Uses documented reporting metadata to align carrier identity across the train/eval years; preserves row-local preparation.
Run time: 24.4s (training 12.3s, eval 12.1s, ok)

## Experiment 22 — increase min_child_weight from 20 to 100

Classification: follow-up.
Hypothesis: The retained forest still uses the original minimum child weight of 20. Raising it fivefold to 100 tests whether small leaves capture transient airport/schedule effects that averaging alone does not remove.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html

Result: **0.6872**, commit 0aa8978, **keep**. Tests substantially larger leaf support after earlier evidence favored variance control.
Run time: 24.4s (training 12.2s, eval 12.1s, ok)

## Experiment 23 — reduce retained forest to depth 2

Classification: ablation/simplification.
Hypothesis: The leaf-support increase gave only a small gain. Test whether pairwise interactions suffice by reducing tree depth from 3 to 2, now that holidays and carrier harmonization explicitly represent important structure.

Result: **0.6848**, commit 86273f1, **discard**. Tests whether explicit holiday and carrier features make third-order tree interactions unnecessary.
Run time: 21.9s (training 10.1s, eval 11.8s, ok)

## Experiment 24 — pairwise ranking objective

Classification: exploration.
Hypothesis: AUC measures pair ordering. Test XGBoost's pairwise logistic ranking loss with one global query and uniformly sampled pairs, retaining the current features and tree regularization. A monotonic sigmoid adapter exposes predict_proba to the unchanged harness.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html

Result: **0.6841**, commit bac3d4e, **discard**. Completed within the training limit, but did not beat the retained binary-logistic model.
Run time: 42.4s (training 30.2s, eval 12.2s, ok)

## Experiment 25 — relative departure time versus training schedule medians

Classification: exploration.
Hypothesis: Absolute time is strong, but a flight's position relative to a route or airport's typical schedule may capture operational context without fitting target-derived route categories. Fit departure-minute medians on train and expose row-local deviations.
Source: https://www.sciencedirect.com/science/article/pii/S0969699708000550 ; program.md feature engineering example

Result: **0.6874**, commit 08f1415, **keep**. Fits only unlabeled schedule statistics on train; batch/single-row preparation and target independence checked.
Run time: 25.4s (training 12.5s, eval 12.9s, ok)

## Experiment 26 — deterministic carrier masking for unseen-category robustness

Classification: exploration.
Hypothesis: Carrier reporting changes expose categories absent from train. Teach a fallback by deterministically masking carrier and its carrier-specific schedule lookup on about 5% of rows. The mask depends only on predictor values and is identical in batch and single-row calls; targets and row indexes do not affect it.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html

Result: **0.6862**, commit 6a316f6, **discard**. Fallback training did not offset the loss of carrier information and added preprocessing cost.
Run time: 34.2s (training 12.6s, eval 21.6s, ok)

## Experiment 27 — depth 4 with current robust features and forest averaging

Classification: follow-up.
Hypothesis: Depth two underfit the current representation. The earlier depth-four comparison preceded holiday features, removal of month, forest averaging, and stronger leaf support. Re-test depth four in this substantially regularized model to recover useful higher-order schedule interactions.

Result: **0.6868**, commit 2ca86f9, **discard**. Revisits model capacity after removing broad seasonality and adding strong leaf support, forest averaging, and schedule-relative features.
Run time: 28.3s (training 15.1s, eval 13.2s, ok)

## Experiment 28 — retain only origin-relative departure time

Classification: ablation/simplification.
Hypothesis: Among the schedule deviations, origin-relative departure time has much higher training gain than route or carrier-origin deviations. Remove the two detailed lookups to see whether the simpler airport-level context preserves or improves the small gain.

Result: **0.6872**, commit 51e99a6, **discard**. Ablates the two more detailed schedule lookups; ties qualify as a simpler model.
Run time: 24.4s (training 12.1s, eval 12.3s, ok)

## Experiment 29 — DART dropout boosting

Classification: exploration.
Hypothesis: Plateau research points to DART as a different way to control late-tree specialization. Test low-frequency tree dropout, using 250 rounds at eta 0.1 and one tree per round to keep recomputation within the 60-second training limit.
Source: https://proceedings.mlr.press/v38/korlakaivinayak15.html ; https://xgboost.readthedocs.io/en/stable/tutorials/dart.html

Result: **0.6868**, commit 1498076, **discard**. Dropout completed within the training limit but did not improve the retained forest.
Run time: 39.0s (training 26.5s, eval 12.5s, ok)

## Experiment 30 — smoothed binary-logistic training loss

Classification: exploration.
Hypothesis: Try 10% label smoothing toward the balanced prior to discourage overconfident fits to flight-specific outcomes. The source studies neural networks, so transfer to boosted trees is an exploratory hypothesis. Implement only the training gradient; the prepared binary labels and harness AUC remain standard.
Source: https://arxiv.org/abs/1906.02629 ; https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html

Result: **0.6875**, commit 33dad0a, **keep**. Custom derivatives passed finite-difference checks; the classifier retains the binary-logistic prediction link.
Run time: 26.0s (training 13.1s, eval 13.0s, ok)

## Synthesis after 30 experiments

Best: **0.6875**, commit `33dad0a`; +0.0132 over baseline. About 24 minutes remain.

What helped in this block: documented HP-to-US reporting harmonization, larger minimum leaf support, route/airport-relative departure times, and a small gain from label smoothing. All are retained strictly under the harness's four-decimal keep rule.

What did not: depth two, depth four with the newer feature set, pairwise ranking loss, deterministic carrier masking, removing detailed schedule medians, or low-frequency tree dropout. The forest at depth three remains the best capacity/variance balance. The schedule median bundle's small gain survived an ablation: removing the detailed lookups lost 0.0002.

The plateau after experiments 26–28 prompted research into DART and label smoothing. [DART](https://proceedings.mlr.press/v38/korlakaivinayak15.html) completed within its runtime budget but lost AUC. [Label smoothing](https://arxiv.org/abs/1906.02629) was adapted as a training-only logistic objective; its derivatives were checked numerically, and installed XGBoost source confirms that the classifier keeps the logistic prediction link.

Next directions: separate low-cardinality one-hot handling from airport partitions; assess heavily regularized low-cardinality risk encodings without sacrificing training rows; test whether balancing training outcomes within months removes residual 2005-specific seasonal effects. Research refresh includes [regularized target encoding](https://arxiv.org/abs/2104.00629) and the [categorical parameter guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

## Experiment 31 — one-hot only low-cardinality categories with threshold 32

Classification: exploration.
Hypothesis: The early one-hot test also changed the large airport categories. Now isolate the low-cardinality case: use one-hot splits for weekday, carrier and holiday identity, while leaving airports partition-based. This may stabilize category-specific effects without losing pooled airport information.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html

Result: **0.6856**, commit fb39512, **discard**. Separates the low-cardinality encoding question from the earlier all-categories one-hot trial.
Run time: 25.7s (training 12.9s, eval 12.8s, ok)

## Experiment 32 — replace airport partitions with strongly smoothed numeric risks

Classification: exploration.
Hypothesis: Replace native airport categories with fixed smoothed delay-rate encodings. Unlike experiment 15, retain all booster-training rows and encode only the two airport fields, with prior strength 500 to limit low-support noise. In-sample target statistics can overfit; limiting cardinality and imposing strong shrinkage is the explicit regularization hypothesis, judged only by the harness.
Source: https://arxiv.org/abs/2104.00629 ; https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html

Result: **0.6850**, commit 645137e, **discard**. Uses only training-derived risk lookups, with strong shrinkage and identical row-wise preparation. Assesses the fixed-ordering tradeoff against native partitions.
Run time: 23.1s (training 11.5s, eval 11.6s, ok)

## Experiment 33 — approximate arrival phase from scheduled time and distance

Classification: exploration.
Hypothesis: Destination arrival constraints can induce departure holds. Approximate travel duration as 30 minutes plus distance at 480 mph, then expose origin-clock arrival phase. It is a rough schedule interaction, not actual arrival time and not timezone-corrected; airport categories may absorb persistent route differences.
Source: https://www.faa.gov/air_traffic/publications/atpubs/foa_html/chap18_section_10.html

Result: **0.6878**, commit af8cfd2, **keep**. Adds a physical time-distance interaction; does not use actual arrival information or external airport data.
Run time: 27.1s (training 13.4s, eval 13.7s, ok)

## Experiment 34 — balance training outcomes within months

Classification: exploration.
Hypothesis: Month removal helped, but seasonal label prevalence can still influence the remaining fitted effects. Reweight delayed/on-time training rows to equal total weight within each month. This is a static robustness hypothesis inspired by group-shift work, not an implementation of group DRO.
Source: https://arxiv.org/abs/1911.08731 ; https://scikit-learn.org/1.6/modules/generated/sklearn.utils.class_weight.compute_sample_weight.html

Result: **0.6883**, commit 5dc2911, **keep**. Weighted custom-objective derivatives passed finite-difference checks; weights affect training only.
Run time: 27.5s (training 14.4s, eval 13.1s, ok)

## Experiment 35 — add Easter relative timing for the supplied calendars

Classification: follow-up.
Hypothesis: Holiday-relative features have been useful. Add Easter's documented travel window, which moves by twenty days between the supplied years. In this explicitly 2005/2006, non-leap setup, January 1's weekday derived from the row identifies which calendar applies; this is known-in-advance calendar information, not a learned year predictor.
Source: https://www.transtats.bts.gov/holidaydelay.asp

Result: **0.6863**, commit 04d4089, **discard**. Adds public holiday calendar information for the two supplied non-leap years; arithmetic and row consistency passed.
Run time: 26.7s (training 13.4s, eval 13.2s, ok)

## Experiment 36 — coarsen numeric histograms to 64 bins

Classification: exploration.
Hypothesis: The model now contains several continuous time and schedule-relative features. Reducing numeric histogram resolution from 256 to 64 bins may pool small timetable differences and reduce split noise across years, without changing categorical identities.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html

Result: **0.6883**, commit d4bd0fc, **keep**. Pools nearby continuous values to test sensitivity to year-to-year timetable detail.
Run time: 26.4s (training 13.3s, eval 13.1s, ok)

Tie decision: retained 64-bin histograms for equal printed AUC and faster observed training (13.3s including preparation versus 14.4s); total runtime 26.4s versus 27.5s. This is a single timing measurement.

## Experiment 37 — average two fixed-seed boosted forests

Classification: exploration.
Hypothesis: Average predicted probabilities from two identically configured boosted forests trained on the full training set with fixed seeds 42 and 137. Independent subsampling can reduce variance without selecting a favorable individual seed. Expected training is about 26 seconds, within the 60-second limit.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html

Result: **0.6883**, commit c9b84a1, **discard**. The average ties the single model but adds complexity and time, so retain the single model.
Run time: 39.5s (training 25.7s, eval 13.8s, ok)

## Experiment 38 — remove label smoothing after month balancing

Classification: ablation/simplification.
Hypothesis: Label smoothing added only 0.0001 before month outcome balancing. Test whether the new training weights make smoothing redundant by restoring ordinary binary logistic loss while keeping every feature, weight and model parameter.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html

Result: **0.6884**, commit bdfa039, **keep**. Ordinary logistic loss improves AUC by 0.0001, removes the custom objective, and trains slightly faster. Month balancing appears sufficient for this regularization role.
Run time: 26.0s (training 12.6s, eval 13.4s, ok)

## Experiment 39 — approximate rotation exposure from time and distance

Classification: exploration.
Hypothesis: Aircraft rotations propagate delays through successive flights and turnarounds. Expose elapsed daytime divided by approximate leg duration plus turnaround as a nonlinear time-distance interaction. With no tail numbers this is only a proxy, not an observed count of flights, and contains no row frequencies.
Source: https://www.sciencedirect.com/science/article/pii/S0305054821003221 ; https://www.tandfonline.com/doi/abs/10.1080/03081060310001635878

Result: **0.6883**, commit 725359f, **discard**. Tests a physical interaction without tail numbers or row-count features; coefficients are rough advance-known assumptions, not fitted flight trajectories.
Run time: 26.3s (training 12.8s, eval 13.4s, ok)

## Experiment 40 — remove minute-within-hour feature

Classification: ablation/simplification.
Hypothesis: The minute-within-hour feature has weak gain in the fitted model and scheduled minute patterns can change across years. Remove this redundant feature while retaining scheduled HHMM, departure hour and cyclical time.
Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html

Result: **0.6883**, commit eba2076, **discard**. A weak individual feature still provides marginal benefit in combination; removal costs 0.0001 and is discarded.
Run time: 26.7s (training 13.4s, eval 13.3s, ok)

## Synthesis after 40 experiments

Best: bdfa039, Eval AUC 0.6884. The last ten trials favored rough arrival-phase features, balancing outcomes within training months, and coarser numeric bins. Once weights were added, removing label smoothing improved both simplicity and AUC. Soft-voting two fixed-seed forests tied the single model at additional cost. Additional raw airport risk encodings, Easter alignment, and the rotation proxy did not help. Removing the low-gain departure-minute feature also lost a small amount.

Working theory: preserving stable operational relationships while suppressing year-specific calendar prevalence matters more than extra model capacity. Tiny changes around 0.0001 should be treated cautiously; the harness keep rule still determines selection. Fresh research examined XGBoost's minimum split-loss penalty and feature sampling weights. Next test whether loss-based pruning removes weak residual splits; then test column-sampling structure or travel-window alignment if time permits.

Sources: https://xgboost.readthedocs.io/en/stable/parameter.html ; https://xgboost.readthedocs.io/en/stable/python/python_api.html?highlight=XGBRegressor ; https://arxiv.org/abs/1603.02754

## Experiment 41 — prune weak residual splits with gamma 2

Classification: exploration.
Hypothesis: A minimum split-loss penalty rejects weak residual splits even when leaves satisfy the existing sample-mass threshold. Test gamma=2 to prune noisy interactions while retaining the 500-round fitting horizon.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html ; https://arxiv.org/abs/1603.02754

Result: **0.6884**, commit c35166c, **discard**. Matches the best AUC but adds a parameter and is not faster; discard. Three consecutive small discards trigger a research pause.
Run time: 26.2s (training 12.7s, eval 13.5s, ok)

## Experiment 42 — align four holiday windows with BTS travel seasons

Classification: follow-up.
Hypothesis: Research after three small discards highlighted BTS travel-season windows rather than symmetric calendar proximity. Keep the same eight holidays but use documented asymmetric offsets for Presidents Day (-4,+1), Memorial Day (-7,+2), Labor Day (-5,+2), and Thanksgiving (-6,+5). Other holiday windows remain unchanged.
Source: https://www.transtats.bts.gov/holidaydelay.asp

Result: **0.6891**, commit c3ed334, **keep**. Improves AUC by 0.0007 with the same holiday identities. Calendar-window alignment is more productive than the recent capacity adjustments.
Run time: 25.8s (training 12.6s, eval 13.3s, ok)

## Experiment 43 — align Independence Day with its weekend travel window

Classification: follow-up.
Hypothesis: The asymmetric travel windows improved AUC by 0.0007. Extend that idea to Independence Day using the Friday strictly before the observed holiday through the following Sunday, as in the BTS calendar. Keep the original actual July 4 offset so only the active window changes.
Source: https://www.transtats.bts.gov/holidaydelay.asp

Result: **0.6885**, commit 7b59ca0, **discard**. Uses calendar arithmetic for the observed holiday and its surrounding weekends, without flight-performance metadata.
Run time: 26.1s (training 12.5s, eval 13.6s, ok)

## Experiment 44 — broaden pre-Christmas and shorten post-New-Year windows

Classification: follow-up.
Hypothesis: BTS winter travel seasons start in mid-December and end in early January, whereas the current symmetric Christmas window starts December 18 and the New Year window extends to January 8. Approximate the broad documented season by extending Christmas's lower bound to -11 days and ending New Year's window at +3 days. This uses a common calendar envelope rather than year-specific dates.
Source: https://www.transtats.bts.gov/holidaydelay.asp

Result: **0.6900**, commit a0dbe02, **keep**. Improves AUC by 0.0009. A broad winter travel envelope appears more transferable than symmetric distance to each holiday.
Run time: 26.6s (training 13.4s, eval 13.2s, ok)

## Experiment 45 — isolate holiday interactions from operational features

Classification: follow-up.
Hypothesis: Holiday alignment now drives the latest gains, but holiday-by-airport interactions can absorb idiosyncratic weather from a single year. Restrict the two holiday features to their own interaction group, analogous to the earlier successful Month isolation test, while leaving operational features free to interact.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html

Result: **0.6894**, commit 3091b2c, **discard**. Restricting holiday interactions costs 0.0006, suggesting some interaction with operational context remains useful.
Run time: 26.7s (training 13.4s, eval 13.3s, ok)

## Experiment 46 — halve the parallel trees per boosting round

Classification: ablation/simplification.
Hypothesis: Four parallel trees per boosting round helped earlier, before month balancing and calendar refinements. Halve the parallel trees to two while retaining 500 rounds; this tests whether the stronger feature design now permits a smaller and faster model without losing printed AUC.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html

Result: **0.6903**, commit d48e406, **keep**. Tests a smaller boosted forest after the calendar and weighting improvements.
Run time: 20.1s (training 7.1s, eval 13.0s, ok)

## Experiment 47 — sample features once per tree instead of per split

Classification: exploration.
Hypothesis: Per-node column sampling can reintroduce dominant time or airport features later in every tree. Draw one 80-percent feature subset per whole tree instead, giving each parallel tree a more distinct view while preserving the expected number of candidate columns.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html

Result: **0.6904**, commit 860b28d, **keep**. AUC improves another 0.0001; retain tree-level sampling despite slightly longer training.
Run time: 20.9s (training 7.9s, eval 13.1s, ok)

## Experiment 48 — remove parallel-tree averaging

Classification: ablation/simplification.
Hypothesis: Reducing four parallel trees to two improved both AUC and speed. Test whether parallel averaging is still necessary by using one tree per boosting round, keeping the newly useful per-tree feature sampling.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html

Result: **0.6901**, commit d290bb3, **discard**. Removing parallel averaging is faster but loses 0.0003 AUC; retain two trees per round.
Run time: 16.5s (training 3.5s, eval 13.0s, ok)

## Experiment 49 — increase L2 leaf shrinkage to 50

Classification: exploration.
Hypothesis: The current leaf penalty of 10 is small compared with the minimum leaf Hessian mass of 100. Raise L2 to 50 to shrink noisy leaf effects more strongly, especially after reducing parallel averaging. This changes leaf values rather than the split-loss pruning tested earlier.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html

Result: **0.6909**, commit 8052d06, **keep**. Stronger leaf shrinkage improves AUC by 0.0005 and remains fast; retain it.
Run time: 20.3s (training 7.1s, eval 13.2s, ok)

## Experiment 50 — remove feature subsampling after stronger leaf shrinkage

Classification: ablation/simplification.
Hypothesis: Stronger L2 regularization improved AUC. Test whether it now makes feature subsampling unnecessary by exposing every feature to every tree, while retaining row subsampling and two parallel trees. This removes a model setting if AUC is preserved.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html

Result: **0.6895**, commit bbcaa90, **discard**. Removing feature subsampling loses 0.0014 AUC. Explicit leaf shrinkage and feature sampling remain complementary; restore the best commit.
Run time: 20.4s (training 7.2s, eval 13.2s, ok)

## Synthesis after 50 experiments

Best: 8052d06, Eval AUC 0.6909. Calendar travel windows delivered the largest late gains: asymmetric windows for four holidays, then a broad winter travel envelope. Independence Day narrowing hurt, and isolating holidays from operational interactions also hurt. Reducing four parallel trees to two improved both AUC and runtime; reducing to one lost AUC. Sampling columns once per tree improved over per-node sampling, and raising L2 from 10 to 50 added 0.0005. Removing feature subsampling after stronger L2 lost 0.0014, so those two regularizers are complementary in this configuration.

The current theory remains that year-specific calendar prevalence and brittle operational effects are major failure modes. Fresh research: Zhou et al. (2021) show that robust optimization depends on whether group definitions capture spurious correlations, and that simple group-level objectives can miss within-group variation. Their experiments are in image/language tasks, so a month-by-operational-group adaptation here would be a new hypothesis, not established evidence for this dataset. A future run could compare carefully regularized training-only group weighting against our static within-month label balance, without reading any held-out features or labels.

Source: https://proceedings.mlr.press/v139/zhou21g.html

## Final summary

- Branch: `oct6`; best commit: `8052d06d9fdaa6a6852cd7ed93e17d16d58c5132`.
- Best Eval AUC: **0.6909**, versus baseline **0.6743**; absolute improvement **0.0166**.
- Completed 50 experiments plus the unchanged baseline: 23 experiments kept, 27 discarded, no crashes or timeouts. All 51 harness runs completed successfully.
- Best artifact: `artifacts/8052d06d9fdaa6a6852cd7ed93e17d16d58c5132.pkl` (about 3.5 MB).
- Best run time: 20.3 seconds, including 7.1 seconds for startup/preparation/training and 13.2 seconds for evaluation.

What worked: a shallow regularized boosted forest; removing raw day-of-month and month predictors; holiday-relative features with travel-season windows; departure-time decomposition and training-fitted schedule medians; public HP-to-US reporting harmonization; approximate arrival phase; and training-only outcome balancing within months. Late improvements came from a broader Christmas/shorter New Year window, two parallel trees rather than four, per-tree feature sampling, and stronger L2 leaf shrinkage.

What did not work: explicit high-cardinality route categories, the distance-graph embedding, tested target-risk encodings, deeper trees, pairwise ranking, DART, extra seed averaging, Easter alignment, the rotation proxy, Independence Day window narrowing, and isolating holiday interactions. Label smoothing initially helped slightly but was removed after month balancing improved the simpler logistic model. One parallel tree or removing feature subsampling lost AUC.

Final model: 18 prepared features; binary logistic XGBoost; 500 rounds, depth 3, learning rate 0.05, minimum child weight 100, L2 50, row and per-tree column sampling 0.8, two parallel trees, and 64 numeric histogram bins. Only `train.py` differs from the starting code; the harness is unchanged. Every experiment was committed before evaluation and logged. The branch is clean and points to the highest retained printed AUC.

Verification: the saved artifact loads independently; its preparation produces identical features for whole-frame and individual-row calls; changing labels leaves X unchanged; predicted probabilities are finite and normalized. The required final evaluation call remains the last line. Final checks used training rows only and did not compute an additional performance metric.

Scope and next steps: these are results on the provided 2006 evaluation split; unseen holdout performance remains for the human to assess. Calendar arithmetic is scoped to the supplied non-leap years. In a future run, separate the two successful winter-window changes to identify their contributions, and investigate cautiously regularized training-only group weighting informed by the final research pause. Keep the simple month-balanced model as the comparison. No holdout or archived-run outputs were accessed.
