# XGBoost experiment research log

## Setup — 2026-10-07

- Run branch: `oct7`, created directly from the current HEAD.
- Starting commit: `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py`.
- Verified that `data/train.csv` and `data/eval.csv` exist without reading their contents.
- Verified installed dependencies: Python 3.14.4, NumPy 2.5.3, pandas 3.0.6, XGBoost 3.4.1, scikit-learn 1.9.1, and cloudpickle 3.1.2. The environment reports 8 CPUs.
- Initialized `output/results.tsv` with the required four-column header; outputs remain ignored by git.
- Baseline: run the unchanged `train.py` through `python3 harness.py run` after the user confirms starting the one-hour clock.
- No experiments have run. Research sources, hypotheses, results, and keep/discard decisions will be recorded here during the experiment.

## Baseline — b15ec66

Unchanged starter model: Eval AUC **0.6743**, training 1.5 s including startup and preparation, evaluation 30.8 s. Kept as the reference.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): control tree complexity and randomness; smaller learning rates need more boosting rounds.
- [XGBoost categorical guide](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/categorical.html): native categorical partitioning can combine categories with similar leaf values; consistent category mappings are essential.
- [AWS XGBoost tuning ranges](https://docs.aws.amazon.com/sagemaker/latest/dg/xgboost-tuning.html): supports exploring child weights, learning rates, regularization, sampling, and boosting rounds over broad ranges.
- [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): search summary identifies schedule/timing, airport/location, and carrier feature groups; full page was inaccessible (403). No weather or operational outcome data are available here, so any domain features must use the supplied schedule columns.

Training-only inspection: 200,000 rows, no missing values, 283 origins/destinations, 20 carriers; calendar columns use c-N strings. Departure times use HHMM. No evaluation rows were inspected.

## Experiment 1 — exploration: regularized shallow boosting

Hypothesis: depth-4 trees with larger leaves and more shrinkage steps will learn stable schedule/airport effects while reducing year-specific interactions. Starting from the baseline, use 600 trees, learning rate 0.05, min_child_weight 30, reg_lambda 10, subsample 0.9, and max_cat_threshold 32. Sources: initial XGBoost/AWS research above. Only harness Eval AUC determines retention.

Result: **0.6800**, +0.0057 over baseline; kept `2c36c9d`. Training 2.8 s, evaluation 31.4 s.

## Experiment 2 — ablation: remove day of month

Hypothesis: calendar-date fluctuations seen in 2005 may be weather/event noise that does not repeat in 2006. Removing DayofMonth reduces opportunities to fit those interactions while retaining month and weekday seasonality. Keep experiment 1 hyperparameters fixed.

Result: **0.6809**, keep `6ba2fb2`; change +0.0009 versus kept `2c36c9d` (0.6800). Run time: 29.8s (training 2.7s, eval 27.1s, ok)

## Experiment 3 — simplification: faster categorical preparation

Hypothesis: construct the feature frame once with cached categorical dtypes, removing redundant membership checks and repeated column assignments. [pandas.Categorical](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) handles values outside explicit categories as missing. This should preserve features and AUC exactly while reducing row-by-row evaluation time. Check equality against the kept preparation on training rows, single-row behavior, and unseen categories before running the harness.

Result: **0.6809**, keep `d950e9a`; change +0.0000 versus kept `6ba2fb2` (0.6809). Run time: 12.0s (training 3.7s, eval 8.3s, ok)

Preparation checks passed on the full training set, sampled individual rows, and an unseen airport. Evaluation fell from 27.1 s to 8.3 s. However, pandas 3 emitted repeated deprecation warnings for unseen categories; these must be handled explicitly.

## Experiment 4 — follow-up/simplification: explicit unknown-category codes

Hypothesis: using the cached category index to encode values, with -1 for unseen categories, then Categorical.from_codes preserves the feature schema while avoiding pandas deprecated construction behavior and further reducing overhead. This is a functional follow-up to experiment 3, with unchanged model parameters.

Result: **0.6809**, keep `94fd4f8`; change +0.0000 versus kept `d950e9a` (0.6809). Run time: 9.7s (training 2.6s, eval 7.1s, ok)

## Experiment 5 — exploration: one-hot categorical splits

Hypothesis: unrestricted category partitions may group unrelated airports using year-specific residuals. Set max_cat_to_onehot=100000 so each categorical split isolates a single category, retaining the same tree budget and regularization. [XGBoost categorical guide](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/categorical.html) explains this alternative splitting mechanism. Remove max_cat_threshold, which only applies to partition splits.

Result: **0.6793**, discard `83d88f6`; change -0.0016 versus kept `94fd4f8` (0.6809). Run time: 9.3s (training 2.5s, eval 6.9s, ok)

## Experiment 6 — exploration: route and carrier-airport interactions

Hypothesis: explicit route, carrier-origin, and carrier-destination categories let shallow trees model stable operational combinations directly. Derive category vocabularies only from train and map unseen combinations to missing. No frequency/count features are used. This adapts the schedule/location/carrier feature groups found in initial flight-delay research, using native categorical handling from the XGBoost guide. Retain all kept model parameters.

Result: **0.6731**, discard `911a18b`; change -0.0078 versus kept `94fd4f8` (0.6809). Run time: 15.1s (training 5.1s, eval 10.1s, ok)

The interaction experiment passed single-row invariance and unseen-combination checks, but its 4,290 route categories and roughly 1,550 categories per carrier-airport feature hurt transfer substantially. Avoid unrestricted high-cardinality partition features without further regularization.

## Experiment 7 — ablation: remove month

Hypothesis: part of the apparent month signal is weather variation in 2005 rather than recurring seasonality. Following the successful day-of-month ablation, remove Month alone to test whether the remaining schedule, weekday, carrier, airport, and distance features transfer more reliably.

Result: **0.6832**, keep `ecd40a7`; change +0.0023 versus kept `94fd4f8` (0.6809). Run time: 8.8s (training 2.6s, eval 6.2s, ok)

## Experiment 8 — follow-up: additive month effect

Hypothesis: removing Month helped because detailed month-airport/carrier interactions memorized 2005 conditions, but a global seasonal effect may still transfer. Reintroduce Month and isolate it into its own interaction-constraint group; retain unrestricted interactions among all other kept features. [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) provides the mechanism.

Result: **0.6816**, discard `f30000b`; change -0.0016 versus kept `ecd40a7` (0.6832). Run time: 9.4s (training 2.6s, eval 6.8s, ok)

## Experiment 9 — exploration: departure-time decomposition

Hypothesis: separate departure hour/minute and sine/cosine of time since midnight expose coarse schedule banks and midnight continuity to shallow trees. Keep raw HHMM and all kept features. [scikit-learn time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses these representations; trees already handle raw nonlinear time, so this is a test of a useful inductive bias rather than a required transformation.

Result: **0.6833**, keep `077c0f5`; change +0.0001 versus kept `ecd40a7` (0.6832). Run time: 10.7s (training 3.1s, eval 7.6s, ok)

## Experiment 10 — follow-up: increase interaction depth

Hypothesis: after removing fragile calendar inputs, depth-6 trees may capture useful schedule/carrier/airport interactions missed at depth 4. Change only max_depth, keeping 600 rounds, shrinkage, minimum child weight, and L2 regularization fixed. This tests capacity independently of the original bundled regularization change.

Result: **0.6792**, discard `463f97a`; change -0.0041 versus kept `077c0f5` (0.6833). Run time: 10.8s (training 3.8s, eval 7.0s, ok)

## Synthesis after 10 experiments

Best: **0.6833** at `077c0f5`, +0.0090 over baseline. Shallower regularized boosting and removing raw calendar dates help. Route/carrier-airport category partitions, deeper trees, and reintroducing an additive month effect do not. One-hot categorical splits with the current tree budget also underperform. Time decomposition has only a 0.0001 gain, so its necessity remains uncertain. Preparation changes cut row-by-row evaluation from about 31 s to 7 s without changing its values.

Current theory: stable departure-time, airport, and carrier patterns matter, while fine interactions and 2005 calendar effects are fragile. Explore representations that pool related airports without using labels or sample frequencies, then test stronger variance controls.

New research: [Isomap](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html) and [SciPy shortest paths](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html) motivate a low-dimensional embedding of an airport graph weighted by scheduled route distance. Graphs use each observed airport pair's distance, never traffic counts. [Target-encoder leakage example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) warns against naive reuse of training labels; postpone target encodings while exploring unsupervised representations.

## Experiment 11 — exploration: distance-derived airport geometry

Hypothesis: low-dimensional airport coordinates inferred solely from training route distances let trees share geographic patterns between airports, with less variance than arbitrary categorical combinations. Build an undirected distance graph, infer missing pair distances via shortest paths, and take three classical MDS coordinates. Add origin/destination coordinates alongside existing features. These are approximate latent coordinates, not externally supplied latitude/longitude. Unknown airports map to missing. All fitted graph/embedding work stays at module level and prepare only performs row-specific lookup.

Result: **0.6834**, keep `33bf4ba`; change +0.0001 versus kept `077c0f5` (0.6833). Run time: 11.1s (training 3.3s, eval 7.8s, ok)

Graph preparation passed connectedness, single-row invariance, and unknown-airport checks. The gain is only 0.0001; retain per the keep rule, but revisit its complexity during later ablations.

## Experiment 12 — follow-up: shallower depth 3

Hypothesis: depth 6 reduced AUC by 0.0041, suggesting that residual interaction capacity is harmful. Test depth 3 versus the kept depth 4, changing no other parameter, to locate the bias/variance balance with the current time and geometry features.

Result: **0.6841**, keep `e6feb97`; change +0.0007 versus kept `33bf4ba` (0.6834). Run time: 10.4s (training 2.8s, eval 7.7s, ok)

## Experiment 13 — exploration: recency-weighted training

Hypothesis: carrier schedules and operational relationships later in 2005 better approximate the 2006 evaluation year. Keep all training rows, but weight them exponentially with a six-month half-life, normalized to mean one so regularization stays comparable. Month remains absent from the predictive feature set. This adapts temporal weighting discussed in [Handling Concept Drift in Global Time Series](https://arxiv.org/abs/2304.01512); it is an unproven transfer to this task. Only the harness score decides retention.

Result: **0.6845**, keep `588b04e`; change +0.0004 versus kept `e6feb97` (0.6841). Run time: 10.6s (training 2.9s, eval 7.7s, ok)

## Experiment 14 — exploration: boosted randomized forests

Hypothesis: average four randomized shallow trees in each boosting round to reduce split variance while keeping the accumulated boosting shrinkage fixed. Use num_parallel_tree=4, subsample=0.65, and colsample_bynode=0.8, keeping the 600 rounds and other best settings. Source: [XGBoost random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). Training remains one harness run with one XGBoost model.

Result: **0.6837**, discard `476d9a0`; change -0.0008 versus kept `588b04e` (0.6845). Run time: 20.2s (training 12.2s, eval 8.0s, ok)

## Experiment 15 — ablation/simplification: remove airport geometry

Hypothesis: the geometry's initial 0.0001 gain may not persist after changing depth and training weights. Remove the graph construction and all six coordinate features while retaining every other kept setting. Prefer the shorter implementation if AUC is equal or better; do not accept any score decrease.

Result: **0.6846**, keep `a9db66e`; change +0.0001 versus kept `588b04e` (0.6845). Run time: 9.2s (training 2.5s, eval 6.7s, ok)

## Experiment 16 — exploration: schedule-relative departure features

Hypothesis: departure time relative to a route's or carrier-origin pair's typical schedule can identify unusually early/late service within an operation. Fit median departure minutes on train for each pair, then subtract these fixed medians inside prepare. This follows the train-fitted lookup pattern explicitly described in program.md; it uses no target labels or count/frequency features. Keep raw departure-time features and all current model settings.

Result: **0.6848**, keep `f5ee1ae`; change +0.0002 versus kept `a9db66e` (0.6846). Run time: 10.3s (training 2.6s, eval 7.7s, ok)

## Experiment 17 — ablation/simplification: fewer boosting rounds

Hypothesis: the consistent benefit of lower interaction complexity suggests that late boosting iterations may also overfit 2005 residuals. Halve n_estimators from 600 to 300 while holding depth, shrinkage, features, and recency weights fixed. Equal AUC is acceptable only because this model is smaller and faster.

Result: **0.6848**, keep `41c1f04`; change +0.0000 versus kept `f5ee1ae` (0.6848). Run time: 9.9s (training 1.9s, eval 8.0s, ok)

## Experiment 18 — exploration: independently fitted target lookups

Hypothesis: smoothed airport and route delay-rate priors can express stable category relationships without flexible residual category partitions. Reserve a fixed random quarter of train for fitting five smoothed mean tables (origin, destination, route, carrier-origin, carrier-destination), then fit the booster on the other three quarters. Use smoothing strength 40 and the encoding subset's global mean as fallback. The subsets are disjoint, so no booster-training label enters its own target features. This is a single split for independent feature fitting, with no cross-validation or extra evaluation metric. Every prepare call uses the same frozen maps; eval labels are used only to return y. Group sizes are used solely as denominators for fitted smoothed means, never as count/frequency features.

Sources: [scikit-learn target-encoding guide](https://scikit-learn.org/stable/modules/preprocessing.html#target-encoder) and its [leakage demonstration](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html). Since the experiment rules disallow cross-validation, use independent lookup/booster subsets rather than the documentation's internal cross-fitting procedure. The potential cost is fewer rows for each learning stage.

Result: **0.6824**, discard `9190f5b`; change -0.0024 versus kept `41c1f04` (0.6848). Run time: 11.0s (training 1.9s, eval 9.1s, ok)

## Experiment 19 — follow-up: more conservative categorical partitions

Hypothesis: max_cat_threshold=8, down from 32, will reduce arbitrary airport groupings while retaining useful pooling that the one-hot experiment removed. This specifically regularizes categorical partition search, unlike tree depth or the independent target-prior experiment. Source: the categorical parameter definition in [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature).

Result: **0.6781**, discard `70b62cd`; change -0.0067 versus kept `41c1f04` (0.6848). Run time: 9.4s (training 1.8s, eval 7.6s, ok)

## Experiment 20 — follow-up: stronger recency weighting

Hypothesis: the six-month half-life improved AUC, so test a three-month half-life to give late-2005 operating relationships more influence. This is a deliberate strength comparison for the same drift hypothesis, keeping all rows and normalizing weights to mean one. Excessive seasonal emphasis could hurt, which the harness will measure.

Result: **0.6833**, discard `48d8fc9`; change -0.0015 versus kept `41c1f04` (0.6848). Run time: 9.5s (training 1.9s, eval 7.6s, ok)

## Synthesis after 20 experiments

Best: **0.6848** at `41c1f04`, +0.0105 over baseline. Depth 3, moderate recency weighting, and schedule-relative departure times help; halving boosting rounds preserves AUC and shrinks the model. Airport geometry was removable after subsequent changes. Randomized boosted forests and independently fitted target priors hurt. A three-month recency half-life also hurts relative to six months.

Updated theory: prefer shallow models with stable operational inputs, but do not confuse low tree depth with a need for very restrictive category pooling. Both one-hot splitting and max_cat_threshold=8 underperform; airport groups need flexibility. Fine route categories were still too variable. Explore broader pooling within shallow trees, loss reweighting by training month, and regularization mechanisms other than more sampling.

Research refresh: [XGBoost DART](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) supplies dropout over trees; [monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) allow directional constraints on numeric effects; [balanced class-weight documentation](https://scikit-learn.org/1.9/modules/generated/sklearn.utils.class_weight.compute_class_weight.html) gives class-weight formulas that could be adapted within training months. These are hypotheses for this dataset, not evidence they will improve its AUC.

## Experiment 21 — follow-up: broader category pooling

Hypothesis: max_cat_threshold=8's large loss suggests insufficient pooling of airport effects, so test 128 versus the kept 32. Keep depth 3 and 300 rounds to limit interaction complexity. This changes the category-group search capacity in the opposite direction for a specific evidence-based reason; other settings remain fixed.

Result: **0.6841**, discard `a1794e5`; change -0.0007 versus kept `41c1f04` (0.6848). Run time: 9.6s (training 2.0s, eval 7.6s, ok)

## Experiment 22 — exploration: balance class weight within each month

Hypothesis: even with Month removed as a feature, differing 2005 monthly delay rates can induce unstable associations through seasonal schedule mixes. Multiply the kept recency weights by class-balancing factors within each training month, then normalize to mean one. Monthly label rates affect only supervised training-loss weights, never prepare or inference features. This adapts the balanced-weight formula from [scikit-learn class-weight documentation](https://scikit-learn.org/1.9/modules/generated/sklearn.utils.class_weight.compute_class_weight.html) to month-defined training environments.

Result: **0.6850**, keep `996d7b8`; change +0.0002 versus kept `41c1f04` (0.6848). Run time: 9.5s (training 1.9s, eval 7.6s, ok)

## Experiment 23 — exploration: dropout boosting

Hypothesis: modest random dropout of existing trees can reduce reliance on small residual corrections while preserving the useful shallow-tree representation. Use booster=dart, rate_drop=0.03, skip_drop=0.5 with the same 300 rounds, features, and weights. [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes the mechanism and its potentially slower training; the harness's normal 60-second limit remains in force.

Result: **0.6844**, discard `3deb8c3`; change -0.0006 versus kept `996d7b8` (0.6850). Run time: 34.9s (training 27.3s, eval 7.6s, ok)

## Experiment 24 — exploration: monotonic direct schedule effects

Hypothesis: directional constraints on raw departure time, departure hour, and both schedule offsets suppress implausible local reversals in the daily accumulation of delays. Keep sine/cosine and minute features unconstrained to permit overnight exceptions. These are partial feature constraints, not a guarantee that the entire prediction is monotonic in clock time because the derived features change together. Source: [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html). All other settings stay at the kept model.

Result: **0.6841**, discard `e0f7fbb`; change -0.0009 versus kept `996d7b8` (0.6850). Run time: 9.5s (training 1.9s, eval 7.7s, ok)

## Experiment 25 — exploration: three-seed probability ensemble

Hypothesis: averaging independently trained shallow boosters can reduce variance without the aggressive row/column sampling that changed the failed boosted-forest experiment. Use fixed seeds 42, 43, and 44, identical kept hyperparameters, identical full training data and weights, and equal probability averaging through [VotingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). No seed search, cross-validation, or separate evaluation is performed; the saved ensemble is scored once by the harness.

Result: **0.6851**, keep `5f77763`; change +0.0001 versus kept `996d7b8` (0.6850). Run time: 11.7s (training 3.7s, eval 7.9s, ok)

## Experiment 26 — exploration: time-distance arrival proxy

Hypothesis: adding travel duration to scheduled departure time supplies an oblique time-distance interaction that shallow trees otherwise approximate with many splits. Define a rough duration as Distance/8 + 30 minutes, add it to departure minutes, and expose the wrapped proxy plus sine/cosine. This is not actual arrival time and lacks destination timezone adjustment. [FAA ground-delay explanation](https://www.fly.faa.gov/ais/Help/ais_message_help.html) motivates why expected destination conditions can influence departure holds. Only given schedule/distance inputs are used.

Result: **0.6850**, discard `20f898c`; change -0.0001 versus kept `5f77763` (0.6851). Run time: 11.8s (training 3.9s, eval 7.9s, ok)

## Experiment 27 — follow-up: month under balanced monthly loss

Hypothesis: the earlier raw Month feature failed under unbalanced monthly class rates and a deeper single model. The kept objective now gives delayed and on-time rows equal total weight within each month, potentially allowing conditional seasonal effects while suppressing the old monthly base-rate shortcut. Reintroduce Month as a categorical input under the current shallow ensemble and weighted objective; other features/settings remain fixed. This revisit is motivated by the changed loss weighting, not a duplicate of the earlier calendar experiments.

Result: **0.6862**, keep `c9deb51`; change +0.0011 versus kept `5f77763` (0.6851). Run time: 12.0s (training 3.9s, eval 8.1s, ok)

## Experiment 28 — exploration: holiday proximity

Hypothesis: calendar rules shared across years provide a more transferable date signal than raw day-of-month categories. Derive day-of-year and the weekday of January 1 from each row's month/day/weekday, then compute New Year, Memorial Day, Independence Day, Labor Day, Thanksgiving, and Christmas positions. Add pooled days-before/days-after-nearest-holiday features only within a seven-day window; all other dates use sentinel 8. Both years in this task are non-leap years. No raw day/year feature is retained. This adapts holiday indicators studied in [Calibrated and Explainable Flight Delay Prediction](https://doi.org/10.1145/3786484.3786539); benefits here remain empirical.

Result: **0.6874**, keep `5c272d4`; change +0.0012 versus kept `c9deb51` (0.6862). Run time: 14.0s (training 3.9s, eval 10.1s, ok)

Holiday features passed checks for Thanksgiving, Memorial Day, and Labor Day in both 2005 and 2006, plus single-row invariance. Their +0.0012 gain is larger than most recent feature changes.

## Experiment 29 — follow-up: shallower trees at similar total leaf capacity

Hypothesis: 600 depth-2 trees can learn additive/pairwise effects over more steps while avoiding three-way interactions, compared with 300 depth-3 trees. Both have approximately 2,400 maximum leaves per ensemble member. This differs from the earlier depth-only trial by compensating for reduced per-tree capacity. Retain learning rate, ensemble seeds, feature set, and training weights.

Result: **0.6845**, discard `cca2c6f`; change -0.0029 versus kept `5c272d4` (0.6874). Run time: 15.5s (training 5.3s, eval 10.2s, ok)

## Experiment 30 — follow-up: larger minimum leaves

Hypothesis: the model needs depth-3 interactions, but some leaves may still rely on too little evidence. Increase min_child_weight from 30 to 100, leaving tree count, depth, L2, features, and weighting unchanged. This tests leaf support rather than globally reducing interaction order. Source: initial XGBoost parameter research.

Result: **0.6880**, keep `4631964`; change +0.0006 versus kept `5c272d4` (0.6874). Run time: 14.3s (training 4.0s, eval 10.3s, ok)

## Synthesis after 30 experiments

Best: **0.6880** at `4631964`, +0.0137 over baseline. The last ten trials changed the interpretation of calendar features: after balancing class loss within months, reintroducing Month helps (+0.0011); transferable holiday proximity helps further (+0.0012). Larger minimum leaves help (+0.0006), while depth 2 loses important interactions. A fixed three-seed ensemble gives a small gain. DART, monotonic schedule constraints, and a crude arrival-time proxy do not improve this model.

Current theory: the model needs meaningful schedule/calendar interactions, controlled through larger leaves and weights that reduce training-year monthly base-rate shortcuts. Calendar information is useful when represented and weighted carefully, so the early blanket month-ablation result was conditional on the earlier training setup. Next explore dense time-band interactions and coarse numerical histograms, then ablate marginal features.

Research refresh: [XGBoost tree methods](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html) explains weighted histogram sketching and max_bin; [a recent flight-delay study](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0335141) discusses departure-hour bins and calendar components. Only advance-known inputs from our dataset will be used; operational outcomes and traffic-count features remain excluded.

## Experiment 31 — exploration: dense time-band interactions

Hypothesis: weekday-by-three-hour-band and carrier-by-three-hour-band categories capture recurring weekly schedules and rotation patterns directly. These interactions have at most 56 and 160 categories, far fewer than the failed route/airport pair features. Fit vocabularies on train, map unknown combinations to missing, and retain all current numeric time features and hyperparameters.

Result: **0.6861**, discard `7be51cc`; change -0.0019 versus kept `4631964` (0.6880). Run time: 16.2s (training 4.3s, eval 11.9s, ok)

## Experiment 32 — ablation/simplification: remove hour/minute duplicates

Read-only inspection of the kept ensemble's training split gains found no DepHour splits and negligible DepMinute gain. Most time signal is carried by raw departure time and DepSin; neither will be removed. Hypothesis: drop just DepHour and DepMinute to simplify the feature frame without losing Eval AUC. Training importance is only a diagnostic; the official harness result remains the sole keep metric.

Result: **0.6881**, keep `cd86fe8`; change +0.0001 versus kept `4631964` (0.6880). Run time: 13.8s (training 3.9s, eval 9.9s, ok)

## Experiment 33 — exploration: coarser numeric histograms

Hypothesis: reducing max_bin from its default 256 to 64 smooths continuous time, distance, and schedule-offset splits, reducing sensitivity to fine schedule variation. Categorical partition settings stay fixed. Source: [XGBoost tree-method documentation](https://xgboost.readthedocs.io/en/release_3.3.0/treemethod.html), which describes histogram sketching and its split-resolution control.

Result: **0.6876**, discard `599a3ee`; change -0.0005 versus kept `cd86fe8` (0.6881). Run time: 14.0s (training 3.8s, eval 10.2s, ok)

## Experiment 34 — follow-up: distinguish holiday types

Hypothesis: the useful pooled holiday-window effect may differ between Thanksgiving, winter holidays, and summer holidays. Add a seven-level categorical feature: no nearby holiday, or one of the six already-computed holidays within seven days. Retain pooled before/after distances. This adds holiday identity without introducing arbitrary calendar-date categories.

Result: **0.6891**, keep `adf82c7`; change +0.0010 versus kept `cd86fe8` (0.6881). Run time: 15.2s (training 4.0s, eval 11.2s, ok)

## Experiment 35 — exploration: deterministic categorical masking

Hypothesis: the original training data has no missing values, while unknown categories are mapped to missing during inference. Exposing the model to about 2% masked carrier/origin/destination values may improve its learned missing branches. Compute masks deterministically from each row's calendar date, scheduled departure, and distance using fixed integer mixing; apply the identical mapping in train and inference. This deliberately also masks some known inference categories, an accuracy cost to be assessed by the harness. Masks never depend on labels, batch contents, row index, or mutable randomness.

Source: [XGBoost missing-value FAQ](https://xgboost.readthedocs.io/en/release_2.0.0/faq.html) explains that missing branch directions are learned during training; the [TabPFN robustness appendix](https://openreview.net/pdf?id=WH5blx5tZ1) discusses feature-dropout training for XGBoost. Only native categorical inputs are masked; fixed schedule lookups remain unchanged.

Result: **0.6873**, discard `478ea90`; change -0.0018 versus kept `adf82c7` (0.6891). Run time: 16.5s (training 4.9s, eval 11.6s, ok)

## Experiment 36 — follow-up: geographic pooling with seasonal features

Hypothesis: the earlier distance-derived airport geometry was unhelpful in the month-free model, but may now enable spatially coherent seasonal/holiday interactions after Month became useful under balanced loss. Reintroduce the same three coordinates per endpoint with current stronger leaf regularization. This tests the changed seasonal context, not a new coordinate fit or arbitrary variation. Geometry still uses only train route distances and no labels/counts/external airport metadata.

Result: **0.6891**, discard `cba049c`; change +0.0000 versus kept `adf82c7` (0.6891). Run time: 16.7s (training 4.4s, eval 12.4s, ok)

## Experiment 37 — follow-up: stronger leaf-value shrinkage

Hypothesis: larger minimum leaves improved transfer, but moderately sized leaves may still have unstable prediction magnitudes. Increase reg_lambda from 10 to 50 to shrink those values smoothly without forbidding additional splits. Keep min_child_weight=100 and the full kept feature/weighting setup fixed.

Result: **0.6898**, keep `17da597`; change +0.0007 versus kept `adf82c7` (0.6891). Run time: 15.2s (training 4.0s, eval 11.1s, ok)

## Experiment 38 — follow-up: require meaningful split gain

Hypothesis: the improvement from leaf-value shrinkage suggests small residual corrections are still noisy. Set gamma=5 to reject low-gain splits while retaining depth 3 and the successful larger leaves/L2 regularization. This penalizes creating a split, a different control from leaf size or magnitude. All feature and weighting choices remain fixed.

Result: **0.6898**, discard `6f692c0`; change +0.0000 versus kept `17da597` (0.6898). Run time: 15.4s (training 4.0s, eval 11.4s, ok)

## Experiment 39 — follow-up: depth 4 under stronger regularization

Hypothesis: the current calendar features need interactions, and the successful min_child_weight=100/reg_lambda=50 controls may permit depth 4 without the overfitting seen earlier. Increase depth alone from 3 to 4, keeping 300 rounds and the weighted three-seed ensemble. Compared with the old deeper trial, leaf support, shrinkage, calendar representation, and loss weighting have all materially changed.

Result: **0.6906**, keep `33b5ba6`; change +0.0008 versus kept `17da597` (0.6898). Run time: 15.8s (training 4.7s, eval 11.1s, ok)

## Experiment 40 — follow-up: narrower holiday windows

Hypothesis: the holiday gains may come primarily from the immediate travel period. Reduce the active proximity/type window from seven days to three, retaining sentinel 8 outside the window. This removes more distant dates that may have contributed year-specific weather effects. Calendar calculations, features, and model settings otherwise stay fixed.

Result: **0.6896**, discard `575b074`; change -0.0010 versus kept `33b5ba6` (0.6906). Run time: 16.2s (training 4.7s, eval 11.4s, ok)

## Synthesis after 40 experiments

Best: **0.6906** at `33b5ba6`, +0.0163 over baseline. Useful recent changes: remove redundant hour/minute inputs, distinguish holiday identity, increase L2 regularization to 50, then permit depth 4 under the stronger regularization. Seven-day holiday windows beat three-day windows. Geometry adds no AUC in the seasonal model, categorical masking hurts, and coarse histogram bins hurt. Gamma=5 ties but offers no demonstrated simplicity/speed benefit.

Current theory: maintain the stable calendar/schedule representation and use stronger leaf-level regularization to support a modest increase in interaction depth. Remaining checks should test optimization smoothness, objective choice, and simplifications rather than arbitrary feature proliferation.

Research refresh: [XGBoost ranking tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) describes pairwise ranking objectives and query grouping; [XGBoost shrinkage parameter documentation](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) motivates smaller steps with more rounds. Any ranking trial will preserve the existing harness AUC evaluation and use only training labels to fit its objective.

## Experiment 41 — follow-up: smaller boosting steps

Hypothesis: reduce learning_rate from 0.05 to 0.025 and double n_estimators from 300 to 600 to preserve approximate total boosting path length while making split decisions more gradually. Keep the best depth, regularization, ensemble seeds, features, and sample weights.

Result: **0.6905**, discard `3ae1caf`; change -0.0001 versus kept `33b5ba6` (0.6906). Run time: 19.6s (training 7.9s, eval 11.6s, ok)

## Experiment 42 — exploration: pairwise ranking within training months

Hypothesis: directly learning positive-negative ordering within each month may target discrimination while reducing sensitivity to month-level delay prevalence. Fit one XGBRanker with rank:pairwise, mean pair sampling (4 per row), and training months as 12 query groups. Apply the same six-month recency decay as query weights; row-level class balancing is replaced by within-month pair comparisons because ranking weights are per query. Use 300 depth-4 trees, learning rate 0.05, min_child_weight=100, reg_lambda=50. Keep feature preparation unchanged. A wrapper converts each independent ranking score through a sigmoid for the harness predict_proba interface; this is a monotone score mapping, not probability calibration. Cross-month score alignment is a potential weakness.

Sources: [XGBoost ranking tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) and [ranking API](https://xgboost.readthedocs.io/en/stable/python/python_api.html). There is no additional scoring/CV, and all rows and query labels come from train.csv.

Result: **0.6888**, discard `7047069`; change -0.0018 versus kept `33b5ba6` (0.6906). Run time: 16.0s (training 4.9s, eval 11.0s, ok)

## Experiment 43 — exploration: mixed-depth ensemble

Hypothesis: averaging models with different interaction capacities can reduce a shared structural bias more effectively than changing seeds alone. Replace the three depth-4 members with depths 3, 4, and 5, keeping their fixed seeds 42, 43, and 44, all other hyperparameters, and equal probability averaging. All three are fitted on the same full training set and weights, with one harness evaluation of the saved ensemble.

Result: **0.6906**, discard `94fb42f`; change +0.0000 versus kept `33b5ba6` (0.6906). Run time: 16.7s (training 5.6s, eval 11.1s, ok)

## Experiment 44 — exploration: partial daily class balancing

Hypothesis: some remaining 2005-specific delay prevalence comes from transient daily shocks. Blend the per-month label rate equally with each date's label rate, and use that blended rate for the class-loss weights. This partially removes daily prevalence variation while retaining some recurring weekday/holiday signal, unlike full daily balancing. All rates are learned only from training labels and affect loss weights, never inference features. The [group-shift regularization paper](https://arxiv.org/abs/1911.08731) provides conceptual motivation for examining environments and regularization, but this blend is our own heuristic, not an implementation of group DRO.

Result: **0.6868**, discard `df1cd4a`; change -0.0038 versus kept `33b5ba6` (0.6906). Run time: 16.2s (training 4.7s, eval 11.4s, ok)

## Experiment 45 — ablation/simplification: one full-sampling model

Hypothesis: after adding strong leaf regularization and stable calendar features, sampling variance may be small enough to remove the ensemble. Fit one depth-4 XGBoost classifier with subsample=1.0, retaining all other best hyperparameters, features, and training weights. Compare this deterministic full-row booster against the three stochastic members. Equal AUC would justify retaining the smaller/faster model.

Result: **0.6902**, discard `f3348c7`; change -0.0004 versus kept `33b5ba6` (0.6906). Run time: 13.2s (training 2.2s, eval 11.0s, ok)

## Experiment 46 — larger minimum leaf weight

Classification: follow-up. The prior move from min_child_weight=30 to 100 helped, as did depth four under stronger L2. Test min_child_weight=300 to require broader support for those deeper seasonal splits. This extends the documented minimum Hessian support control: https://xgboost.readthedocs.io/en/stable/parameter.html . All other settings remain at the best kept commit.

Result: **0.6910**, keep `cbf5e51`; change +0.0004 versus kept `33b5ba6` (0.6906). Run time: 15.9s (training 4.8s, eval 11.2s, ok)

## Experiment 47 — remove schedule offsets

Classification: ablation/simplification. Route and carrier-origin departure offsets originally added only 0.0002 before the successful seasonal features and stronger regularization. Remove both lookups and features to test whether they still justify their complexity and per-row preparation cost. Retain the change only at equal or higher printed AUC. This follows the established feature-ablation reasoning and the XGBoost tuning documentation already reviewed.

Verification: Artifact cbf5e51 passed training-only checks: batch/single-row equality, row-order independence, label-independent features, unseen-category handling, and finite normalized probabilities. No additional evaluation metric was computed.

Result: **0.6905**, discard `c8724c9`; change -0.0005 versus kept `cbf5e51` (0.6910). Run time: 14.3s (training 4.4s, eval 10.0s, ok)

## Experiment 48 — fewer boosting rounds with the final feature set

Classification: ablation/simplification. Earlier, reducing 600 rounds to 300 retained the printed AUC, but that result preceded the seasonal features and stronger minimum leaf support. Test 200 rounds under the final features and regularization to see whether later trees add transferable information or mostly complexity. The XGBoost parameter-tuning documentation describes this bias/variance and learning-rate/round-count tradeoff: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html .

Result: **0.6907**, discard `a47f9f9`; change -0.0003 versus kept `cbf5e51` (0.6910). Run time: 15.5s (training 4.3s, eval 11.1s, ok)

## Final summary

The clock reported 58m02s elapsed and 1m58s remaining, so the experiment loop ended at the prescribed wrap-up threshold. Completed 48 experiments after the baseline: 22 kept, 26 discarded, and 0 crashes. The branch is `oct7` at best commit `cbf5e51c96081e6f7e047ae0dab1557c7cfdbeaa`. Baseline Eval AUC was 0.6743; best Eval AUC is **0.6910**, an absolute gain of **0.0167**. The best artifact is `/home/ubuntu/xgboost-autoresearch-minimal3/artifacts/cbf5e51c96081e6f7e047ae0dab1557c7cfdbeaa.pkl`. Its harness run took 15.9 seconds (4.8 seconds training/startup and 11.2 seconds evaluation, rounded), comfortably within the limits.

What worked:
- Cached categorical dtypes, explicit category codes, and building the prepared DataFrame once greatly reduced row-by-row evaluation overhead.
- Restrained tree depth, stronger minimum leaf support and L2 regularization, plus a small fixed-seed ensemble improved the score.
- Six-month recency weighting combined with class balancing within each training month let the model use month information more effectively across years.
- Row-derived holiday identity and before/after distances added useful calendar context; the seven-day window beat the narrower version.
- Cyclical departure-time features and fixed training route/carrier-origin schedule medians survived ablation. Removing schedule offsets in the final model reduced AUC to 0.6905.

What did not work:
- High-cardinality route categories, one-hot splitting, deeper unregularized trees, compact distance-derived geometry, categorical masking, and standalone split-fitted target encoding did not improve the retained model.
- DART, random-forest-style boosting, monotonic constraints, pairwise ranking, and a mixed-depth ensemble did not beat the best configuration.
- Stronger recency weighting, daily class balancing, a narrower holiday window, and an arrival-time proxy hurt the result.
- A single full-sampling model and fewer final boosting rounds were faster or simpler but lost AUC; the keep rule required discarding them.

Validation and handoff:
- The best saved artifact passed training-only checks on 128 rows: batch versus single-row feature equality, row-order independence, label-independent features, unseen-category handling, and finite normalized prediction probabilities. No separate scoring metric was computed.
- Every successful logged trial has its saved artifact. All 49 result rows (baseline plus experiments) have unique commits; the working tree is clean and the branch points to the last kept commit.
- Only train.py changed relative to the baseline commit, and save_and_evaluate(model, prepare) remains its final line. The experiment logs remain uncommitted in output/.
- The final two simplifications were discarded: removing schedule offsets scored 0.6905 and reducing rounds to 200 scored 0.6907, versus 0.6910 for the retained model.

Next ideas: test additional movable holidays and holiday-specific windows, then investigate robust schedule-spread lookups fitted only on training rows. The fitted trees still put most importance on scheduled departure time and its cyclical transforms. Small score differences remain specific to this evaluation split; the saved artifact is ready for the human's separate holdout check.
