# Research log: oct6

## Setup — 2026-10-06

- Created branch `oct6` directly from current HEAD, `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist without opening evaluation data.
- Verified installed dependencies import successfully: pandas 3.0.6, NumPy 2.5.3, XGBoost 3.4.1, scikit-learn 1.9.1, cloudpickle 3.1.2. Python 3.14.4; 8 available CPUs.
- Initialized `output/results.tsv` with its four-column header. No experiments have run.
- Experiment clock has not started. On confirmation, the first action is `python3 harness.py start`, followed by a baseline run of the unchanged `train.py`.
- Web research is required before the first non-baseline experiment, at every ten-experiment synthesis, at a plateau, and before a new category of change.

## Baseline

Baseline completed; see the recorded result below.

Baseline `b15ec66`: Eval AUC **0.6743**, training 1.5s including startup, evaluation 30.9s, total 32.4s. Kept.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): balance capacity against variance; try smaller learning rates with more rounds and control depth, child weight, and subsampling.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): concrete regularization and categorical split controls. Installed version is 3.4.1; use stable 3.4 docs, not development defaults.
- [Categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): fixed integer codes plus explicit feature_types preserve categorical splitting without constructing pandas categorical arrays per row.
- [Time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): useful background for separating calendar and clock components; any transforms here must depend only on the row and training lookups.
- Training inspection: 200,000 rows, 9 columns, no missing values, balanced labels. Calendar values use c- prefixes. 283 origins/destinations and 20 carriers. No evaluation data was inspected.

## Experiment 1 — faster categorical preparation

Classification: ablation/simplification. Hypothesis: fixed codes with explicit categorical feature types preserve baseline partitions and AUC while reducing row-scoring overhead. Same feature order, category order, missing-category handling, and model parameters. Source: categorical documentation above.

Result: 8f52066, Eval AUC **0.6743**, **keep**. Run time: 5.7s (training 1.5s, eval 4.2s, ok)

## Experiment 2 — conservative extended boosting

Classification: exploration. Hypothesis: depth 4, 500 rounds at learning rate 0.05, child weight 30, lambda 10, and 0.85 row sampling should capture stable effects with less category-specific overfitting than the depth-6 baseline. This is a deliberate model-capacity regime change, motivated by the cross-year shift and the XGBoost tuning guide. No feature changes.

Result: 845b6e4, Eval AUC **0.6796**, **keep**. Run time: 7.0s (training 2.7s, eval 4.3s, ok)

## Experiment 3 — remove day-of-month categories

Classification: ablation/simplification of experiment 2. Hypothesis: a categorical day of month lets trees memorize 2005 date-specific disruptions that will not recur in 2006. Removing this weak calendar variable should improve transfer while simplifying the model. Month and weekday remain available. Motivated by the limited gain from regularization and the known year shift.

Result: 651c21f, Eval AUC **0.6799**, **keep**. Run time: 7.2s (training 3.0s, eval 4.2s, ok)

## Experiment 4 — departure hour and minute

Classification: exploration (feature engineering). Hypothesis: separate departure hour and minute expose time-of-day and timetable rounding effects to shallow trees more efficiently than HHMM alone. Add only these two numeric features to the best model. Source: scikit-learn time-related feature engineering example (initial research); row-local transforms preserve evaluation semantics. The Berkeley flight-feature page was found in search but its full page returned HTTP 403, so no details from the blocked content are assumed.

Result: 1d61618, Eval AUC **0.6799**, **discard**. Run time: 7.1s (training 2.8s, eval 4.3s, ok)

## Experiment 5 — route identity

Classification: exploration. Hypothesis: a native categorical origin-destination interaction exposes route-specific operating conditions without requiring repeated airport splits in shallow trees. Fit route codes on training pairs only; unseen routes become missing. Motivated by retained airport effects and the XGBoost categorical partitioning documentation. Experiment 4 tied without simplifying, so it was discarded.

Result: 1c397ba, Eval AUC **0.6703**, **discard**. Run time: 8.4s (training 3.9s, eval 4.5s, ok)

## Experiment 6 — one-category splits

Classification: exploration of categorical handling. Hypothesis: one-hot categorical splits will reduce unstable category groupings across years, especially for airports. Experiment 5 lost 0.0096 AUC with a high-cardinality route feature, suggesting that flexible grouping overfits. Set max_cat_to_onehot=512, above every remaining category cardinality; keep all other best-model settings. Source: XGBoost categorical documentation, initial research.

Result: 9027ae9, Eval AUC **0.6787**, **discard**. Run time: 6.3s (training 2.2s, eval 4.0s, ok)

## Experiment 7 — longer boosting horizon

Classification: follow-up to experiment 2. Hypothesis: 500 shallow trees may still underfit stable carrier-airport-time interactions; test 1500 rounds at the same learning rate to measure the direction of the boosting-horizon effect. This triples capacity without changing split rules or regularization. Experiment 6 shows that restricting every categorical split to one category is not sufficient by itself.

Result: 11896eb, Eval AUC **0.6756**, **discard**. Run time: 10.3s (training 6.0s, eval 4.3s, ok)

## Experiment 8 — shorter boosting horizon

Classification: ablation/simplification. Hypothesis: experiment 7 fell to 0.6756, so boosting is already fitting unstable residuals. Test 200 rounds versus the best 500 to bracket a more transferable horizon. No other settings change.

Additional research after unsuccessful feature/encoding trials: [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) explains how structural restrictions can suppress spurious interactions. This motivates a later separation of calendar effects from route operating effects. [Target encoding example](https://sklearn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) warns about target leakage; avoid naive rare-route target means.

Result: fb016af, Eval AUC **0.6807**, **keep**. Run time: 5.6s (training 1.5s, eval 4.0s, ok)

## Experiment 9 — cyclic season representation

Classification: exploration. Hypothesis: replacing arbitrary month partitions with sine/cosine of month will favor broad recurring seasonal structure over year-specific month groupings. Use the 200-round best model unchanged otherwise. Source: scikit-learn time feature example in initial research. Both features are deterministic row-local functions.

Result: 4910fa8, Eval AUC **0.6834**, **keep**. Run time: 5.7s (training 1.6s, eval 4.2s, ok)

## Experiment 10 — departure relative to route schedule

Classification: exploration. Hypothesis: a flight departing later than the typical departure on its route can capture schedule-position effects while pooling across routes, avoiding the unstable route-identity partitions in experiment 5. Fit median scheduled minutes per origin/destination on train only and look them up in prepare. No target or count features. The lookup pattern is explicitly supported in program.md; domain research on scheduled operations provides context ([study](https://doi.org/10.1016/J.JAIRTRAMAN.2019.101737)). Cyclic season improved AUC to 0.6834 and is retained.

Result: 6c3240d, Eval AUC **0.6836**, **keep**. Run time: 6.5s (training 1.7s, eval 4.8s, ok)

## Synthesis after experiments 1–10
Best: 6c3240d, Eval AUC 0.6836, versus baseline 0.6743 (+0.0093). Faster preparation preserved predictions and reduced scoring to roughly 4 seconds. Smaller boosting budgets and cyclic season representation helped; route identity, one-hot splits, and long boosting did not. Day-of-month was safely removed. Route-relative scheduled time adds a small gain and passes batch/single-row and label-independence checks.
Current theory: strong time-of-day effects plus transferable seasonal/airport effects dominate; fitting fine categorical interactions easily overfits the year shift. Next compare lower interaction order, calendar restrictions, and variance reduction.
New research: [soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) supports averaging independently fitted probability models; [XGBoost random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) documents forests within boosting. Both can reduce variance without extending the residual-fitting horizon. Fit only on train and retain harness AUC as the sole selection metric.

## Experiment 11 — shallower trees at comparable leaf budget
Classification: follow-up. Hypothesis: 400 depth-3 trees (about the same maximum leaf budget as 200 depth-4 trees) emphasize lower-order interactions and transfer better. This tests interaction order rather than simply adding more trees.

Result: 37590c8, Eval AUC **0.6843**, **keep**. Run time: 7.2s (training 2.1s, eval 5.1s, ok)

## Experiment 12 — limit categorical group search
Classification: follow-up to the regularization findings. Hypothesis: max_cat_threshold=16 restricts large airport-category partitions while retaining multi-category splits that one-hot encoding removed. This targets category grouping flexibility separately from depth and boosting horizon. Source: XGBoost parameter documentation. Best model now uses depth 3 and 400 rounds.

Result: 6b7c177, Eval AUC **0.6839**, **discard**. Run time: 6.7s (training 2.0s, eval 4.8s, ok)

## Experiment 13 — five-seed probability average
Classification: exploration (variance reduction). Hypothesis: averaging five independent stochastic fits of the best shallow model will reduce sampling-sensitive airport partitions without lengthening each fit's boosting horizon. Same features and hyperparameters; seeds 42, 137, 271, 509, 733. All fits use train.csv only. Source: scikit-learn VotingClassifier documentation from the ten-experiment research pause.

Result: 757bfe2, Eval AUC **0.6847**, **keep**. Run time: 12.9s (training 7.8s, eval 5.1s, ok)

## Experiment 14 — continuous position within the year
Classification: follow-up to experiment 9. Hypothesis: cyclic day-of-year features can represent seasonal transitions within months while retaining December–January continuity. Replace month sine/cosine with non-leap calendar day sine/cosine, derived from month and day only. The five-seed ensemble gained 0.0004 AUC and remains unchanged. Source: scikit-learn time feature engineering example.

Result: 5d2ba5c, Eval AUC **0.6847**, **discard**. Run time: 12.0s (training 6.7s, eval 5.3s, ok)

## Experiment 15 — additive seasonal effects
Classification: exploration (structural regularization). Hypothesis: seasonal main effects are transferable, but season-by-airport/carrier interactions partly memorize a single year's disruptions. Restrict MonthSin/MonthCos to their own interaction group and allow all operating features to interact together. This directly tests the cross-year interaction theory from the first synthesis. Source: official XGBoost interaction-constraint tutorial. The finer seasonal phase tied without simplifying and was discarded.

Result: 9575027, Eval AUC **0.6839**, **discard**. Run time: 11.7s (training 6.6s, eval 5.1s, ok)

## Experiment 16 — feature subsampling within trees
Classification: follow-up to successful five-model averaging. Hypothesis: colsample_bynode=0.8 will decorrelate trees and encourage the model to capture useful secondary predictors rather than repeatedly splitting the dominant departure-time feature. Keep row sampling at 0.85, the existing seeds, and boosting horizon unchanged. Source: XGBoost random forest and tuning documentation.

Result: 5614f89, Eval AUC **0.6852**, **keep**. Run time: 11.7s (training 6.7s, eval 5.0s, ok)

## Experiment 17 — average trees within each boosting step
Classification: follow-up to experiments 13 and 16. Hypothesis: four independently sampled trees per boosting round will further stabilize each residual update, complementing averaging completed models. Set num_parallel_tree=4 while preserving 400 rounds, depth 3, and all feature/seed choices. This tests the boosted-forest strategy described in the official XGBoost random-forest tutorial. Expected training remains below 60 seconds.

Result: e0715b6, Eval AUC **0.6852**, **discard**. Run time: 42.1s (training 35.6s, eval 6.5s, ok)

## Experiment 18 — coarser numeric split resolution
Classification: exploration (numeric regularization). Hypothesis: max_bin=64 reduces unstable fine thresholds in scheduled time, distance, and route-relative time. This pools nearby schedules without adding new features. Experiment 17 tied while increasing run time from 11.7s to 42.1s and was discarded. Source: XGBoost max_bin parameter documentation.

Result: e0a05e6, Eval AUC **0.6849**, **discard**. Run time: 12.0s (training 6.6s, eval 5.4s, ok)

## Experiment 19 — larger minimum leaf weight
Classification: follow-up to the successful low-complexity regime. Hypothesis: min_child_weight=200 (versus 30) suppresses small airport/calendar subgroups while preserving broad main effects. This changes minimum evidence per leaf without reducing boosting horizon or all interaction depth. Coarser numeric bins lost 0.0003 and were discarded.

Result: 5b11c7a, Eval AUC **0.6852**, **discard**. Run time: 12.2s (training 6.7s, eval 5.5s, ok)

## Plateau research and experiment 20 — distance-derived airport coordinates
Three consecutive small/equal discards triggered a research pause. [Classical MDS](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.ClassicalMDS.html) maps pairwise distances into numeric coordinates; [SciPy shortest paths](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html) can fill unobserved distances through the training flight graph. Training-only inspection confirms the graph connects all 284 airports.
Classification: exploration. Hypothesis: three geometric coordinates for origin and destination will allow regional pooling and seasonal interactions that arbitrary airport categories do not express. Fit a symmetric graph from median route distances, compute shortest paths, and classical MDS via centered squared-distance eigendecomposition. No labels, flight counts, external airport data, or evaluation data are used. Keep airport categories as well as the coordinates.

Result: f77dfc0, Eval AUC **0.6852**, **discard**. Run time: 14.1s (training 8.6s, eval 5.6s, ok)

## Synthesis after experiments 11–20
Best: 5614f89, Eval AUC 0.6852 (+0.0109 over baseline). Shallower trees, five-seed averaging, and per-node feature sampling helped. Finer season resolution, restricting seasonal interactions, four trees per boosting step, coarse bins, and larger leaves did not improve AUC. Distance-derived geographic coordinates tied and were removed. Row-wise preparation remains verified.
Theory: variance reduction helps, but remaining gains may require a different loss or targeted domain features rather than additional generic capacity. Preserve short boosting horizons and cyclic months.
New research: [XGBoost learning to rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) and ranking parameter docs describe RankNet pairwise loss with uniform pair sampling. [Monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) offers another way to regularize the dominant time feature.

## Experiment 21 — pairwise ranking objective
Classification: exploration (training objective). Hypothesis: binary AUC measures delayed/non-delayed pair ordering, so optimizing pairwise ranking may improve it over logistic probability fitting. Fit three seeded rankers on one query group containing all training rows, with two sampled pairs per row; average their margins and sigmoid only for the harness predict_proba interface. Same 400-round shallow regime. No new evaluation or validation split is introduced.

Result: 35f0e2e, Eval AUC **0.0000**, **crash**. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)

## Experiment 22 — feasible pairwise ranking pilot
Classification: follow-up (timeout fix). Experiment 21 exceeded the training limit and was logged as a crash, then reverted. Test one ranker with 150 rounds, eta 0.1, and one sampled pair per row to reduce pair-generation and sorting cost substantially. The question remains whether pairwise loss offers enough AUC gain to justify further work; no other metric is computed.

Result: a6d8613, Eval AUC **0.6813**, **discard**. Run time: 11.6s (training 6.8s, eval 4.7s, ok)

## Experiment 23 — holiday proximity
Classification: exploration (domain calendar features). Hypothesis: holiday travel patterns recur across years but move relative to weekday/month categories. Add signed proximity within narrow windows of Christmas, New Year, July 4, and Thanksgiving. Thanksgiving is computed as the fourth Thursday of November using each row's month/day/weekday. Fixed-date offsets use non-leap day-of-year; both relevant years are non-leap. No year guessing or external records. Source: [OPM holiday rules](https://www.opm.gov/faq/payleave/what-are-federal-holidays.ashx). Ranking pilot was discarded at 0.6813.

Result: 08a6d97, Eval AUC **0.6876**, **keep**. Run time: 14.1s (training 8.2s, eval 5.9s, ok)

## Experiment 24 — moving Monday holidays
Classification: follow-up to experiment 23 (+0.0024 AUC). Hypothesis: Memorial Day and Labor Day add recurring travel effects missed by the four existing holidays. Recover Jan 1 weekday from the row's known day-of-year and weekday, then compute May's last Monday and September's first Monday. This handles windows crossing month boundaries, without guessing a year or reading any other data. Source: OPM holiday rules already researched.

Result: fe53f49, Eval AUC **0.6874**, **discard**. Run time: 14.3s (training 8.2s, eval 6.1s, ok)

## Experiment 25 — monotone daytime delay accumulation
Classification: exploration (shape regularization). Hypothesis: between 05:00 and 21:00, delay risk for an otherwise identical schedule should generally rise as disruptions accumulate. Constrain CRSDepTime and RouteTimeOffset upward, adding an unconstrained night-phase feature below 05:00 and after 21:00 so red-eye and late-night patterns remain flexible. Source: official XGBoost monotonic-constraint tutorial. Monday-holiday additions were discarded; their calendar and row-invariance checks passed.

Result: b60969f, Eval AUC **0.6875**, **discard**. Run time: 14.5s (training 8.5s, eval 6.0s, ok)

## Experiment 26 — night-phase feature without shape constraints
Classification: ablation of a near miss. Experiment 25 lost only 0.0001, combining a new night-phase representation with monotonic constraints. Hypothesis: the representation may help while strict monotonicity removes genuine schedule effects. Keep only NightPhase and allow all effects to be learned freely; this isolates the two changes.

Result: 445f0b3, Eval AUC **0.6880**, **keep**. Run time: 14.6s (training 8.5s, eval 6.1s, ok)

## Experiment 27 — semiannual seasonal harmonics
Classification: follow-up to cyclic months. Hypothesis: winter and summer delay peaks can be represented more directly by a second annual harmonic, reducing the tree depth needed for two recurring seasonal peaks. Add sin(4*pi*month/12) and cos(4*pi*month/12) alongside the first harmonic. Source: [statsmodels Fourier examples](https://www.statsmodels.org/stable/examples/notebooks/generated/deterministics.html); implemented with NumPy only. NightPhase alone improved to 0.6880 and is retained.

Result: 730404b, Eval AUC **0.6840**, **discard**. Run time: 14.9s (training 8.8s, eval 6.1s, ok)

## Experiment 28 — share the holiday response
Classification: ablation/simplification of the successful holiday feature family. Hypothesis: pooling all four holiday offsets into one nearest-holiday feature will share statistical strength and reduce overfitting of individual holiday windows. Retain cyclic month and weekday so genuine seasonal differences remain expressible. Select the closest eligible holiday per row, with NaN outside every window. This reduces four model inputs to one; no aggregation across rows.

Result: 51c6e00, Eval AUC **0.6863**, **discard**. Run time: 14.9s (training 8.7s, eval 6.3s, ok)

## Experiment 29 — recency-weighted training
Classification: exploration (temporal transfer). Hypothesis: airport/carrier behavior later in 2005 may better represent 2006. Use an exponential six-month half-life on training sample weights, normalized to mean one to preserve regularization scale. Features and five models are unchanged. These weights affect fitting only, never row preparation or evaluation. Source: [Instance-Conditional Timescales of Decay](https://arxiv.org/abs/2212.05908), which motivates testing recency while retaining older observations. Local sklearn code confirms VotingClassifier forwards sample_weight.

Result: d293546, Eval AUC **0.6881**, **keep**. Run time: 14.7s (training 8.6s, eval 6.0s, ok)

## Experiment 30 — smaller boosting steps at the same total shrinkage
Classification: follow-up to the improved feature set. Hypothesis: 800 rounds at eta 0.025 will fit the useful holiday and nighttime effects more smoothly than 400 rounds at eta 0.05, without extending the nominal sum of step sizes. Keep recency weighting after its small gain to 0.6881. This differs from experiment 7, which tripled the total boosting horizon in a deeper model.

Result: d8e355c, Eval AUC **0.6879**, **discard**. Run time: 22.1s (training 15.7s, eval 6.4s, ok)

## Synthesis after experiments 21–30
Best: d293546, AUC 0.6881 (+0.0138 from baseline). A small pairwise ranker underperformed; a larger one timed out. Separate holiday offsets gave the main gain (+0.0024), and an unconstrained night-phase feature helped further. Monday holidays, strict daytime monotonicity, extra seasonal harmonics, pooling holiday effects, and smaller boosting steps did not help. Recency weighting improved by 0.0001.
Current theory: specific schedule/calendar structure matters more than generic additional smoothing. Retain distinct holiday effects and flexible daytime behavior. Next test carrier-station interactions and more distinct ensemble members.
Research search for the original Micci-Barreca paper returned no result. Further research on DART (dropout boosting) examines a way to reduce over-specialization of later trees; official XGBoost dropout parameters are available, but runtime will need care.

## Experiment 31 — carrier departure station
Classification: exploration. Hypothesis: a carrier-airport pair captures station-specific operations that shallow trees struggle to express through two separate high-cardinality predictors. This is substantially coarser than origin-destination route identity, which failed earlier. Fit category codes solely on training pairs; unseen stations become missing. Source: XGBoost categorical-data documentation.

Result: 60c77cc, Eval AUC **0.6821**, **discard**. Run time: 16.6s (training 9.8s, eval 6.9s, ok)

## Experiment 32 — blend a dropout-boosted model
Classification: exploration (ensemble diversity). Hypothesis: DART's repeated dropout of earlier trees produces a complementary fit to ordinary boosting. Keep the five best ordinary models and add a 150-round DART member (eta 0.15, drop rate 0.02, skip probability 0.5), assigning half the blend weight to each family. The shorter DART horizon controls its prediction-heavy training cost. Features and recency weights are shared.
Source: [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) and XGBoost dropout parameter documentation. Raw station categories were discarded at 0.6821; this reinforces the need for regularization if station statistics are revisited.

Result: 303f914, Eval AUC **0.6881**, **discard**. Run time: 23.1s (training 17.0s, eval 6.1s, ok)

## Experiment 33 — independently fitted historical delay priors
Classification: exploration (supervised training lookups). Hypothesis: smoothed carrier-station and route delay priors can pool evidence more reliably than raw joint categories. Fit priors on a fixed random 25% partition of train, train three encoded models only on the other 75%, and blend them equally with the best full-data ensemble. There is no cross-validation or new evaluation metric.
Sources: [TargetEncoder guidance](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) motivates separating the lookup-fitting labels from downstream training labels. Use a disjoint partition rather than cross-fitting. Priors shrink toward the encoding partition's mean with strength 100. Group counts are used only as denominators for probability estimation, never as features. All transforms and lookup application remain in prepare.
The full-data ensemble receives only its original columns, so encoding-partition labels cannot enter its features. Unknown groups get the encoding partition's prior.

Result: 3e5e55d, Eval AUC **0.6876**, **discard**. Run time: 20.4s (training 12.4s, eval 8.0s, ok)

## Experiment 34 — more data for prior estimation

Classification: follow-up to the supervised-lookup near miss. Experiment 33 lost only 0.0005 despite using a small prior-fitting partition. Hypothesis: doubling that partition to 50% improves noisy station/route estimates enough to compensate for reducing encoded-tree fitting to 50%. Retain the full-data base ensemble and equal blend. Reuse experiment 33's verified implementation; the two partitions remain disjoint and no extra metric is introduced.

Result: aa4b0ab, Eval AUC **0.6871**, **discard**. Run time: 18.6s (training 11.3s, eval 7.3s, ok)

## Experiment 35 — diversify interaction depth
Classification: exploration (heterogeneous ensemble). Hypothesis: depth-2, depth-4, and depth-5 models capture complementary broad and detailed effects, while the best depth-3 ensemble supplies a stable center. Add models with approximately matched maximum leaf budgets: 800x4, 200x16, and 100x32 leaves; all eta 0.05. Weight the original five models and the new three-model group equally.
Plateau research: [sklearn bias/variance example](https://scikit-learn.org/stable/auto_examples/ensemble/plot_bias_variance.html) explains how averaging can reduce variance while introducing a bias tradeoff. This experiment seeks diversity in model capacity after extra seeds/dropout/target priors were insufficient. Source results are on a regression example; application here is a hypothesis tested only through harness AUC.

Result: 18bd4af, Eval AUC **0.6886**, **keep**. Run time: 19.0s (training 12.8s, eval 6.2s, ok)

## Experiment 36 — carrier-station schedule position
Classification: follow-up to the useful route-relative schedule feature. Hypothesis: departure time relative to a carrier's typical origin-airport schedule pools station operating context numerically without the unstable joint categories tested in experiment 31. Fit station median scheduled minutes on train and subtract it per row. No target statistics or count features. Keep the newly improved mixed-depth ensemble.

Result: 2f230dd, Eval AUC **0.6889**, **keep**. Run time: 19.6s (training 12.9s, eval 6.7s, ok)

## Experiment 37 — isolate the broad-pattern ensemble
Classification: ablation/simplification of experiment 35. Hypothesis: with explicit holidays and two schedule-relative features, depth-2 trees may capture enough useful interactions and avoid the noise of deeper members. Use five depth-2 models with 800 rounds and remove the depth-3/4/5 mixture, preserving roughly the original per-model maximum leaf budget. This isolates whether the shallow member supplied the diversity gain.

Result: 47e03a3, Eval AUC **0.6870**, **discard**. Run time: 19.1s (training 12.5s, eval 6.6s, ok)

## Experiment 38 — isolate the more detailed ensemble
Classification: ablation/follow-up to the mixed-depth gain. Depth 2 alone fell to 0.6870, so the blend needs richer interactions. Hypothesis: five depth-4 models at 200 rounds may recover the useful carrier/calendar/schedule interactions more directly than the mixed-depth model. Preserve maximum leaf budget and all features/weights; remove the extra model families to isolate this direction.

Result: 0503ef6, Eval AUC **0.6886**, **discard**. Run time: 12.7s (training 6.3s, eval 6.4s, ok)

## Experiment 39 — stronger leaf-value shrinkage
Classification: follow-up to richer schedule/calendar features. The mixed-depth model beats either homogeneous depth-2 or depth-4 alternative. Hypothesis: increasing reg_lambda from 10 to 100 will retain its interaction diversity while shrinking unstable leaf values, especially around sparse holiday windows and small carrier-airport subsets. This tests weight shrinkage rather than the already-tried minimum leaf size or binning.

Result: 7b56660, Eval AUC **0.6893**, **keep**. Run time: 20.6s (training 14.0s, eval 6.7s, ok)

## Experiment 40 — reject weak split gains
Classification: follow-up to stronger L2 regularization. Hypothesis: gamma=5 removes weak residual splits while preserving the stronger station/holiday structure. L2 shrinkage improved AUC to 0.6893; a split-gain threshold targets tree structure rather than merely scaling retained leaf values. Keep all other best settings unchanged.

Result: ce514fd, Eval AUC **0.6893**, **discard**. Run time: 19.7s (training 13.1s, eval 6.6s, ok)

## Synthesis after experiments 31–40
Best: 7b56660, AUC 0.6893 (+0.0150). Raw carrier-station categories failed. DART tied. Independently fitted target priors passed integrity checks but lost AUC even with more lookup data. Mixed tree depths helped, a carrier-station schedule offset helped, and stronger L2 leaf shrinkage helped. Neither shallow-only nor deeper-only ensembles matched the mixture.
Gamma=5 tied. It reduced total nodes only from 46,712 to 46,200 and artifact size by 0.2%; the small timing difference was insufficient evidence of a useful simplification, so it was discarded.
Current theory: diverse interaction depths with strong regularization and explicit schedule context work best. Further gains should come from new residual emphasis or removal of redundant inputs.
Research: [sklearn scoring guidance](https://scikit-learn.org/stable/modules/calibration.html) discusses logistic and Brier losses as proper scoring rules; [Brier definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html) motivates squared-error conditional-mean fitting. We will still compute only harness AUC.

## Experiment 41 — squared-error probability ranking
Classification: exploration (training loss). Hypothesis: squared-error fits to binary outcomes emphasize residuals differently from logistic loss and may transfer better. Keep the same mixed-depth structure and recency weights. Scale child weight and lambda by four to roughly match row support and probability-scale shrinkage near p=0.5. Fit XGBRegressor with square error; a strictly monotone sigmoid maps the averaged regression score into valid predict_proba outputs without changing its AUC ordering.

Result: 5410d34, Eval AUC **0.6892**, **discard**. Run time: 20.4s (training 13.7s, eval 6.6s, ok)

## Experiment 42 — combine logistic and squared-error fits
Classification: follow-up to the squared-error near miss (0.6892 vs 0.6893). Hypothesis: the two losses produce complementary rankings even though neither dominates alone. Fit matched mixed-depth families for both losses, then average the logistic probability and raw squared-error conditional-mean estimate. A monotone sigmoid converts the combined score to valid probabilities, preserving its ranking. Same training data, recency weights, and features; no extra metric.

Result: 620792d, Eval AUC **0.6893**, **discard**. Run time: 33.1s (training 25.7s, eval 7.4s, ok)

## Plateau research and experiment 43 — sparse leaf-value updates
Three small/equal losses (40–42) prompted renewed research into XGBoost L1 penalties and gradient-based sampling. Official parameter docs describe alpha as leaf-weight L1 regularization and support gradient-based sampling with hist on the installed CPU-capable version.
Classification: follow-up to successful stronger L2 shrinkage. Hypothesis: reg_alpha=10 can zero weak leaf updates and retain stronger effects, complementing the best reg_lambda=100. Unlike gamma, it penalizes the update magnitude directly. The squared-error blend tied and was discarded.

Result: 24dc4a4, Eval AUC **0.6902**, **keep**. Run time: 19.8s (training 13.2s, eval 6.6s, ok)

## Experiment 44 — remove recency weighting
Classification: ablation/simplification. Hypothesis: the original 0.0001 gain from recency weighting may no longer be useful after mixed depths, station timing, and strong L1/L2 regularization. Uniform weights restore equal evidence across seasons and remove fitting-only date logic. Keep if AUC improves or ties, since the code becomes simpler.

Result: f57c2bd, Eval AUC **0.6895**, **discard**. Run time: 18.8s (training 12.2s, eval 6.6s, ok)

## Experiment 45 — remove flight distance
Classification: ablation/simplification. Hypothesis: distance contributes little independent information once carrier, airports, and relative schedule context are present; removing it may reduce weak residual splits and simplify preparation. Feature-gain inspection previously ranked distance last. Recency weighting remains necessary after losing 0.0007 when removed.

Result: 809d8a3, Eval AUC **0.6890**, **discard**. Run time: 18.9s (training 12.4s, eval 6.5s, ok)

## Experiment 46 — remove route-relative schedule time
Classification: ablation/simplification. Hypothesis: the more broadly pooled carrier-station median might make the original route median redundant, allowing a smaller lookup and fewer noisy route-specific estimates. Remove RouteTimeOffset and its fitted table while retaining StationTimeOffset and raw departure time. Distance ablation failed despite low gain importance, showing that gain is not a reliable selection metric by itself.

Result: bc2edb6, Eval AUC **0.6902**, **keep**. Run time: 18.3s (training 12.1s, eval 6.2s, ok)

## Experiment 47 — gradient-based row sampling
Classification: exploration (training-sample selection). Hypothesis: gradient-based sampling at fraction 0.5 may preserve informative updates while changing the ensemble's sensitivity to easy versus difficult rows. Set hist explicitly and use the CPU support documented in the stable 3.4 parameter reference (older API pages still describe GPU-only behavior). Keep all retained regularization and features.
Experiment 46 tied at 0.6902 while removing nine lines and the route lookup, and reduced total runtime from 19.8s to 18.3s, so it was kept as a clear simplification.

Result: 696e5b4, Eval AUC **0.6905**, **keep**. Run time: 29.3s (training 23.0s, eval 6.3s, ok)

## Experiment 48 — uniform half-sampling control
Classification: ablation/simplification of experiment 47. Gradient-based half-sampling improved AUC to 0.6905. Hypothesis: the gain may come from stronger stochasticity rather than gradient prioritization. Keep the sampling fraction at 0.5 and switch to ordinary uniform selection by removing sampling_method. This directly separates the two changes and can simplify/speed the model on a tie.

Result: a1e4ac7, Eval AUC **0.6905**, **keep**. Run time: 20.7s (training 14.4s, eval 6.3s, ok)

## Experiment 49 — fewer repeated depth-three members
Classification: ablation/simplification. Uniform half-sampling tied at 0.6905 and reduced runtime from 29.3s to 20.7s, so it was kept. Hypothesis: three rather than five depth-3 seeds may suffice alongside depth-2/4/5 diversity. Retain half the total ensemble weight for each family by using six equal-weight members. This removes two fits and explicit ensemble weights without changing feature preparation or model regimes.

Result: e4e1ada, Eval AUC **0.6904**, **discard**. Run time: 17.0s (training 10.8s, eval 6.2s, ok)

## Experiment 50 — distance relative to carrier network
Classification: follow-up to useful carrier-station schedule context. Hypothesis: a flight's distance relative to its carrier's usual route length distinguishes short versus long operations within different airline networks more directly than raw distance plus carrier. Fit median distance by carrier on train and subtract it per row. No target or frequency statistics. Retain eight members after the six-member ablation lost 0.0001.

Result: 7edd943, Eval AUC **0.6906**, **keep**. Run time: 21.2s (training 14.5s, eval 6.6s, ok)

## Synthesis after experiments 41–50
Best: 7edd943, AUC 0.6906 (+0.0163 from baseline). Squared-error fitting nearly matched logistic but blending losses did not improve. L1 plus L2 regularization helped substantially. Recency and distance remain useful. Route timing became redundant after station timing and was removed at equal AUC. Half-sampling helped; uniform sampling matched gradient-based sampling much faster. Fewer ensemble members lost slightly. Carrier-relative distance added 0.0001.
Current theory: retain stable calendar and carrier-context features, substantial random sampling, and regularized depth diversity. Avoid additional loss/encoding complexity without a measured benefit.
New research: [BTS field definitions](https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ) confirm distance is miles and scheduled flight elapsed time is measured in minutes. Only definitions were read, not source flight records. This motivates a deliberately crude time-distance interaction.

## Experiment 51 — approximate arrival clock
Classification: exploration (schedule interaction). Hypothesis: departure minutes plus distance/8 plus 30 minutes exposes an approximate destination operating window to shallow trees. Use modulo 1440 for daily continuity. The nominal 480 mph plus 30-minute overhead is a fixed heuristic, not an estimate fitted to unavailable elapsed/arrival data. The clock remains in origin-local units and ignores time zones; destination categories may partly account for this. All computation is row-local.

Result: 91cd7ee, Eval AUC **0.6906**, **discard**. Run time: 21.8s (training 14.9s, eval 6.9s, ok)

## Experiment 52 — selective one-hot categorical splits
Classification: exploration/follow-up to categorical handling. Hypothesis: low-cardinality carrier and weekday identities may benefit from individual-category splits while airports still require flexible pooling. Set max_cat_to_onehot=32, affecting 7 weekdays and 20 carriers but leaving 283-level airport features partitioned. This is different from experiment 6, which forced one-hot airport splits too. Keep all strong regularization and half-sampling. The arrival proxy tied and was discarded.

Result: e527f6b, Eval AUC **0.6882**, **discard**. Run time: 21.0s (training 14.4s, eval 6.6s, ok)

## Experiment 53 — stronger sparsity threshold
Classification: follow-up to experiment 43's 0.0009 gain. Hypothesis: alpha=30, three times the current 10, may suppress additional weak holiday/station updates under half-sampling. This tests a materially stronger sparsity threshold after the first L1 penalty helped; it could also underfit rare but real effects, which the harness will resolve. Other settings are fixed.

Result: f997e5d, Eval AUC **0.6887**, **discard**. Run time: 20.0s (training 13.4s, eval 6.6s, ok)

## Experiment 54 — stronger feature sampling
Classification: follow-up to the successful stochastic ensemble. Hypothesis: sampling half rather than 80% of columns at each split may further diversify the eight models. The station-time feature supplies a proxy when raw departure time is absent, so useful signal can remain while individual trees become less correlated. Keep alpha=10 after alpha=30 underfit and lost 0.0019. All other settings remain fixed.

Result: 26b8e1d, Eval AUC **0.6900**, **discard**. Run time: 20.8s (training 14.2s, eval 6.6s, ok)

## Experiment 55 — finer numeric split resolution
Classification: exploration/follow-up to numeric resolution. Coarse 64-bin splits failed earlier. Hypothesis: 1024 bins, versus the default 256, can resolve more precise scheduled-time, station-offset, and distance thresholds now that strong L1/L2 penalties control weak splits. This increases representation precision without changing features, tree depth, or boosting horizon.

Result: 3c64d9a, Eval AUC **0.6908**, **keep**. Run time: 21.7s (training 14.8s, eval 6.9s, ok)

## Experiment 56 — stronger recency preference
Classification: follow-up to the demonstrated value of recency weighting. Removing weights lost 0.0007 after strong regularization. Hypothesis: shortening the half-life from six months to three may further emphasize operating conditions closest to 2006, at the cost of less effective evidence from early 2005. Normalize weights as before, and retain the new 1024-bin gain to 0.6908.

Result: e68ab9e, Eval AUC **0.6900**, **discard**. Run time: 21.6s (training 15.0s, eval 6.6s, ok)

## Experiment 57 — remove the overlapping New Year feature
Classification: ablation/simplification. Hypothesis: the New Year window overlaps much of the Christmas window and may be redundant once month, weekday, and strong regularization are present. Remove only NewYearOffset; preserve Christmas, July 4, and Thanksgiving. The three-month recency half-life lost 0.0008, so six months remains the best tested balance.

Result: 2c6068e, Eval AUC **0.6911**, **keep**. Run time: 21.2s (training 14.7s, eval 6.6s, ok)

## Experiment 58 — consistent Thanksgiving window
Classification: follow-up/simplification of calendar semantics. Hypothesis: defining the Thanksgiving window by actual day distance, rather than additionally requiring November, avoids truncating the final day when Thanksgiving falls on November 24. Derive November 1 weekday from each row's non-leap day-of-year and known weekday; compute the fourth Thursday and apply the same +/-7-day window across month boundaries. No year or external data is required. Removing NewYearOffset improved AUC to 0.6911.

Result: e16bcaf, Eval AUC **0.6912**, **keep**. Run time: 21.2s (training 14.7s, eval 6.5s, ok)

## Experiment 59 — average model log-odds
Classification: exploration (ensemble aggregation). Hypothesis: averaging margins before the sigmoid may combine the differently confident depth families more effectively than averaging probabilities. Keep all fitted models, seeds, weights, features, and training choices unchanged. This corresponds to normalized geometric pooling of binary class probabilities.
Source: [Heskes, logarithmic opinion pools](https://papers.nips.cc/paper_files/paper/1997/hash/59f51fd6937412b7e56ded1ea2470c25-Abstract.html). We retain existing weights rather than fit them to evaluation predictions.
Experiment 58 improved to 0.6912. Its saved artifact passed synthetic calendar-boundary checks, batch/single-row equality, current-label independence, unseen-category handling, and finite normalized probabilities.

Result: 4e870c0, Eval AUC **0.6913**, **keep**. Run time: 21.3s (training 14.8s, eval 6.5s, ok)

## Experiment 60 — stronger row subsampling
Classification: follow-up to the half-sampling gain. Hypothesis: reducing uniform subsampling from 0.5 to 0.3 may improve temporal robustness through more diverse trees, with eight models averaging away some added variance. This is a substantial reduction in rows per tree; it also risks excessive regularization, since alpha and lambda remain fixed. All other best settings, including log-odds pooling at AUC 0.6913, remain unchanged.

Result: 6217391, Eval AUC **0.6908**, **discard**. Run time: 21.1s (training 14.5s, eval 6.6s, ok)

## Synthesis after experiments 51–60
Best: 4e870c0, AUC 0.6913 (+0.0170 over baseline). The approximate arrival clock tied; selective one-hot handling, alpha=30, stronger feature sampling, and a three-month recency half-life hurt. Finer 1024-bin resolution helped. Removing the overlapping New Year feature and making Thanksgiving's window consistent across months helped. Log-odds pooling added a small gain. Row subsampling at 0.3 lost; 0.5 remains best.
New research: [learning-rate scheduler callback](https://xgboost.readthedocs.io/en/release_1.7.0/python/python_api.html#xgboost.callback.LearningRateScheduler) supports per-round rates and suggests a future matched-budget annealing study. With the remaining clock, first test whether the much stronger regularization now permits a longer fixed-rate horizon.

## Experiment 61 — longer horizon under the final regularization regime
Classification: follow-up to strong L1/L2 and half-sampling. Hypothesis: the earlier long-horizon failure occurred with weaker regularization and fewer useful features; the current model may tolerate more residual fitting. Increase every depth family's rounds by 50% (depth 3: 600; depth 2: 1200; depth 4: 300; depth 5: 150), preserving learning rate and mixture weights. This is a controlled horizon test, not another change to step size.

Result: 4c0a951, Eval AUC **0.6917**, **keep**. Run time: 28.7s (training 21.6s, eval 7.1s, ok)

## Final summary

Stopped experimentation after the harness reported less than two minutes remaining, as required by program.md.

- Branch: oct6; best commit: 4c0a95116aefb1011e72251f576058b741f8bbdc.
- Baseline Eval AUC: 0.6743. Best Eval AUC: 0.6917. Absolute gain: 0.0174.
- Runs: 62 total, comprising the baseline and 61 experiments. Status counts including baseline: 26 keep, 35 discard, 1 crash.
- Final run: 28.7s total, including 21.6s training/startup and 7.1s evaluation. Within both harness limits.
- Best artifact: artifacts/4c0a95116aefb1011e72251f576058b741f8bbdc.pkl (14.3 MB).
- Final model: eight XGBoost members combining depths 2/3/4/5, weighted log-odds pooling, learning rate 0.05, L2=100, L1=10, uniform row sampling 0.5, per-node feature sampling 0.8, and 1024 numeric bins. Boosting rounds are 1200/600/300/150 for depths 2/3/4/5. Training weights have a six-month recency half-life.
- Inputs: fixed categorical codes; raw scheduled departure and distance; cyclic month; Christmas, July 4, and Thanksgiving proximity; night departure phase; departure offset from the carrier-origin median schedule; distance offset from the carrier median. All lookups are fitted on train, and all row transformations are inside prepare.

### What helped

Faster equivalent categorical preparation enabled more experiments. Reduced interaction depth and shorter early boosting horizons improved transfer; later, stronger L1/L2 regularization allowed a longer final horizon. Cyclic seasons, specific holiday features, flexible night phase, carrier-relative schedule/distance, mixed depths, recency weights, half-sampling, finer bins, and log-odds pooling each contributed retained gains. Removing redundant day-of-month categories, route timing, and New Year proximity simplified the model without sacrificing the kept score.

### What did not help

Raw route/station categories, broad one-hot splitting, geographic distance embeddings, extra seasonal harmonics, pooled holiday effects, Monday holiday features, strict monotonicity, additive seasonal constraints, target-prior blends, DART blending, squared-error blending, extra trees per boosting step, more extreme penalties/sampling/recency decay, and a smaller ensemble failed to improve the kept score. The large pairwise-ranking experiment timed out and was reverted; its smaller pilot also underperformed.

### Validation and remaining questions

Verified that HEAD is the best kept commit and the only tracked change from the starting commit is train.py. Every kept run has its saved artifact, all 62 runs are logged exactly once, and output files remain ignored/uncommitted. Verified the final saved artifact on training-derived and synthetic cases: batch/single-row feature equality, independence from the current row's target, unseen-category handling, Thanksgiving month-boundary behavior, and finite normalized predictions. save_and_evaluate(model, prepare) remains the final statement.

Evaluation scores were obtained only through the unchanged harness. Holdout and human-only tools/data were not accessed. Generalization beyond the evaluation set remains for the human's holdout check.

Next directions: matched-budget learning-rate annealing; independent-run replication of the small late gains; calendar/context features that do not require unavailable operational data. AUC-only improvements of 0.0001 remain small observations from this evaluation set, not guarantees of a holdout gain.

The experiment clock is stopped through harness.py stop as the final action after this summary.
