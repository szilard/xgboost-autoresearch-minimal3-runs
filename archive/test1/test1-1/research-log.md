# oct4 experiment log

## Baseline — b15ec66

The unchanged starter achieved Eval AUC 0.6743 (training 1.5 s; evaluation 30.4 s). Training has 200,000 rows and no missing values. `CRSDepTime` is encoded as HHMM; the categorical fields include 20 carriers and 283 origin and destination airports.

## Initial research

- [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) recommends controlling complexity through depth, child weight, gamma, sampling, and tree count.
- [XGBoost categorical data documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes one-hot and optimal-partition splits and `max_cat_to_onehot`.
- [UC Berkeley air travel delay feature engineering](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) motivates departure-hour, carrier, airport and calendar effects. Only features available before departure can be used here.

## Experiment 1 — 62b31ae (exploration; discard)

Hypothesis: 300 trees at 0.05 learning rate would resolve finer patterns than the 100-tree baseline. Eval AUC remained 0.6743, while training grew from 1.5 s to 2.5 s and the artifact from 2.6 MB to 7.5 MB. It does not meet the equal-score keep rule.

## Experiment 2 — b656b2d (exploration; keep)

Hypothesis: hour of departure has a nonmonotonic relationship with delay risk, beyond the ordered HHMM field. Added a categorical `DepHour`, using only each row's scheduled departure time. Eval AUC improved to 0.6747. Evaluation took 34.3 s, about 4 s longer than baseline.

## Experiment 3 — 58dccee (follow-up; keep)

Hypothesis: shallower trees reduce overfitting to 2005-specific interactions. Changing depth from 6 to 4 improved Eval AUC to 0.6789 and reduced artifact size from 2.6 MB to 0.7 MB. This is the largest gain so far.

## Experiment 4 — 9aba6ad (follow-up; keep)

Hypothesis: depth 3 will transfer even better than depth 4. Eval AUC rose to 0.6797; artifact shrank to 0.3 MB. So far reduced complexity consistently helps.

## Experiment 5 — 4431599 (follow-up; discard)

Hypothesis: depth 2 might further improve transfer. Eval AUC fell to 0.6754. At 100 trees the model appears too simple; depth 3 is better.

## Experiment 6 — 74712b4 (follow-up; discard)

Hypothesis: depth 3 might benefit from 300 smaller boosting steps even though depth 6 did not. Eval AUC was 0.6796, just below the kept 0.6797, and training took longer. The score does not support this schedule.

## Experiment 7 — 3813c84 (exploration; discard)

Hypothesis: a native categorical route feature would capture stable origin–destination interaction. The 4,290-level route category instead lowered AUC to 0.6741 and lengthened evaluation to 50 s. Sparse route effects appear to overfit the training year in this formulation.

## Experiment 8 — 999b1cf (exploration; discard)

Hypothesis: one-hot splits for small categories could avoid overfitting from arbitrary category groupings. `max_cat_to_onehot=25` reduced AUC to 0.6789, so the default split handling was better.

## Experiment 9 — day of year (exploration)

Hypothesis: ordered day of year can capture seasonal changes across month boundaries. Initial commit 1a0fa55 crashed because calendar values are strings like `c-11`; fixed parsing by removing the `c-` prefix. The failed run is recorded in results.tsv.

Corrected commit 97717bc achieved Eval AUC 0.6832, an improvement of 0.0035 over the previous best. Evaluation rose to 39.3 s due to the row-wise string conversion. The seasonal ordering appears valuable.

## Experiment 10 — a4d724a (follow-up; keep)

Hypothesis: the new seasonal feature may benefit from more boosting steps at the same depth. Raising tree count from 100 to 150 improved AUC to 0.6841, with similar evaluation time.

## Synthesis after 10 experiments

The strongest gains came from reducing depth from 6 to 3 and adding ordered day of year. Departure hour helped slightly. A high-cardinality route category harmed both AUC and speed; one-hot categorical splits also fell short. Longer boosting with the old feature set did not help, but 150 trees did once day of year was added. Current theory: stable, ordered calendar patterns plus moderate model complexity transfer better from 2005 to 2006 than sparse route memorization. Next I will investigate time-by-carrier or time-by-airport effects, and regularization of categorical splits.

## Research after experiment 10

- [XGBoost's current tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) names `min_child_weight`, `gamma` and `max_cat_threshold` as complexity controls and row/column sampling as ways to reduce noise.
- The [UC Berkeley flight delay study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports carrier-specific late-night effects. A carrier-by-hour feature is available at prediction time and has far fewer levels than route.
- [XGBoost categorical handling](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) uses partition-based splits to group category values; a precomputed carrier-hour category may express an interaction in one split.

## Experiment 11 — 5f63ce7 (exploration; discard)

Hypothesis: carrier-by-hour category would capture carrier-specific late-night delay patterns. Eval AUC fell to 0.6818, and row-wise evaluation took 46.1 s. A category warning also appeared for unseen carrier-hour pairs. Reverted.

## Experiment 12 — d560601 (exploration; discard)

Hypothesis: requiring larger child Hessian would prevent noisy small-category splits. `min_child_weight=10` yielded the same 0.6841 AUC, with no simplification or speed gain. It may rarely bind in the depth-3 trees.

## Experiment 13 — f555a81 (exploration; discard)

Hypothesis: 80% row sampling might reduce sensitivity to 2005-specific noise. Eval AUC dropped to 0.6831, so full-row training remains best.

## Experiment 14 — 65cfc3c (exploration; discard)

Hypothesis: sine and cosine of day of year would connect late December to early January, following [scikit-learn's cyclical time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). Eval AUC fell to 0.6828, and evaluation grew to 42.1 s. Ordered day of year alone worked better here.

## Experiment 15 — c9471c1 (exploration; discard)

Hypothesis: origin distances to JFK, LAX and ATL, derived from the training route-distance graph, would let the model share broad geographic effects. AUC tied at 0.6841 while evaluation slowed from 38.9 s to 44.3 s. Reverted under the equal-score rule.

## Experiment 16 — 3fe7dcb (follow-up; discard)

Hypothesis: improvement from 100 to 150 trees might continue to 200. Eval AUC fell to 0.6834; 150 trees is better with this feature set.

## Experiment 17 — 5464efa (exploration; discard)

Hypothesis: minute-of-hour might expose repeated scheduling patterns across different hours. A 60-level `DepMinute` category lowered AUC to 0.6828 and added evaluation cost. Fine-grained minute effects look noisy.

## Experiment 18 — 0d861bd (follow-up; discard)

Hypothesis: 12 five-minute positions would generalize better than 60 exact minutes. Eval AUC was 0.6840, just below the kept model, with slower evaluation. The coarser time-position feature still did not help.

## Plateau research

[scikit-learn's Target Encoder guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) warns that category target means without cross-fitting can leak labels and overfit, especially with rare categories. I will avoid high-cardinality airport or route target rates. A broad, 21-day smoothed historical seasonal rate may be safer: each lookup value averages many flights and is fitted once on 2005 training data, then applied identically row by row in 2006.

## Experiment 19 — 3ec537b (exploration; discard)

Hypothesis: a broad historical seasonal rate could capture smooth nonmonotonic calendar risk. The 21-day smoothed lookup from 2005 reduced AUC to 0.6818. This suggests the year-specific risk curve does not transfer well to 2006, despite smoothing.

## Experiment 20 — fb356a2 (exploration; discard)

Hypothesis: 512 histogram bins would let the model make finer departure-time splits. AUC dropped to 0.6830; the default 256 bins remain better.

## Synthesis after 20 experiments

The best remains 0.6841 at a4d724a. Since experiment 10, extra engineered features have not improved it. High-cardinality interactions, finer scheduled-minute encoding, geographic proxies, and a train-year seasonal risk curve all hurt or only tied while slowing evaluation. More trees and finer histogram bins also hurt. The current working theory is that this dataset rewards a small set of stable features and restrained model complexity; train-year-specific patterns transfer poorly. Next I will test categorical partition regularization and a small ensemble of complementary tree depths.

## Research after experiment 20

- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` caps categories considered for each partition-based split to help prevent overfitting. This directly addresses high-cardinality origin and destination splits without adding feature-processing cost.
- The [DART booster guide](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/dart.html) describes tree dropout as another overfitting control, though it can slow training. I will reserve it for a later distinct model experiment.
- [A study of random tree depth](https://link.springer.com/article/10.1007/s00180-025-01697-0) suggests depth diversity can reduce correlation among trees. A simple blend of XGBoost models at depths 3 and 4 can test a related idea within the training limit.

## Experiment 21 — f0b5644 (exploration; discard)

Hypothesis: limiting categories in partition-based splits to 16 would curb airport-specific overfitting. AUC dropped sharply to 0.6769. The categorical partition search appears to need more flexibility, motivating a test in the opposite direction.

## Experiment 22 — 813b2e9 (follow-up; discard)

Hypothesis: allowing 128 rather than the kept model's default 64 categories per split might capture more useful airport groups. AUC was 0.6829, so both directions away from 64 lost accuracy.

## Experiment 23 — 2e7843e (exploration; keep)

Hypothesis: averaging depth-3 and depth-4 XGBoost probabilities could reduce model-specific ranking errors. A 75/25 blend of the kept 150-tree depth-3 model and a 100-tree depth-4 model improved AUC to 0.6843. Training rose to 1.8 s and the artifact to 1.2 MB, while evaluation stayed near 39 s.

## Experiment 24 — b491b55 (follow-up; discard)

Hypothesis: equal weighting might gain more from the depth-4 model. AUC fell to 0.6840. The deeper model helps only as a smaller contribution so far.

## Experiment 25 — 102f771 (follow-up; discard)

Hypothesis: reducing depth-4 weight to 10% might improve over the 75/25 blend. AUC was 0.6842, between the single model and 75/25 blend. This completes the small weight comparison; 75/25 remains best.

## Experiment 26 — 610eb42 (exploration; discard)

Hypothesis: sampling 80% of features for the depth-4 blend member would make its errors less correlated with the depth-3 member. AUC was 0.6842, slightly below 0.6843. The added randomness did not help.

## Plateau research after experiment 26

[scikit-learn's correlated-feature example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html) shows that removing redundant correlated features can preserve performance. Scheduled HHMM and departure hour encode much of the same time information, so I will ablate hour first and look for a simpler equal-scoring model. The [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) also offers tree dropout as a separate approach if feature simplification does not help.

## Experiment 27 — 13c66e9 (ablation; discard)

Removing `DepHour` sped evaluation from about 39 to 36 seconds, but AUC dropped to 0.6841. Under the keep rule, the speed gain cannot justify a lower score. The hour category retains some predictive value even alongside HHMM.

## Experiment 28 — d5a21e6 (ablation; discard)

Removing `Distance`, the lowest-importance feature in the kept model, cut AUC to 0.6830. It carries useful information despite the small importance value. This reinforces the caution from correlated-feature research that fitted importance is not a direct measure of out-of-year value.

## Experiment 29 — 4b82d2b (exploration; discard)

Hypothesis: DART dropout on the depth-4 member would improve blend diversity and transfer. AUC tied at 0.6843, but training increased from about 1.8 s to 6.0 s, so it does not meet the equal-score keep rule.

## Experiment 30 — bbe2370 (exploration; discard)

Hypothesis: best-first growth with eight leaves and depth up to 5 would add a complementary asymmetric model. AUC was 0.6842, just below the kept blend.

## Synthesis after 30 experiments

The best is 0.6843 at 2e7843e. Blending depths 3 and 4 gave a small gain after a long plateau, but higher depth-4 weight, column sampling, DART dropout, and best-first growth did not improve it. Removing hour or distance lowered AUC, so even low-importance and correlated-looking inputs matter. The useful model is still compact and evaluation time is stable around 39 s. Next I will focus on regularizing leaf outputs and on a small number of targeted time or calendar features.

## Research after experiment 30

- [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `reg_lambda` as L2 regularization on leaf weights. The default is 1; stronger shrinkage may reduce year-specific fitted effects.
- [XGBoost feature interaction constraints](https://xgboost.readthedocs.io/en/release_1.2.0/tutorials/feature_interaction_constraint.html) can block spurious combinations. This is a later option if simpler leaf regularization fails.
- [Flight-delay feature research](https://www.mdpi.com/2079-9292/13/24/4910) highlights week of year and quarter as coarse calendar features, which could offer a lower-variance complement to exact day of year.

## Experiment 31 — 1c531a3 (exploration; discard)

Hypothesis: stronger L2 shrinkage on the dominant depth-3 member would reduce overfitting. `reg_lambda=100` lowered AUC to 0.6835. This strength appears excessive; I will test a moderate value before leaving this direction.

## Experiment 32 — 2983c97 (follow-up; discard)

Reducing `reg_lambda` from 100 to 10 still yielded 0.6835, below the default-leaf-regularization blend. This direction did not help, so I am shifting to a coarse calendar feature.

## Experiment 33 — db77365 (exploration; discard)

Hypothesis: seven-day calendar blocks would capture stable weekly seasonal changes. AUC fell to 0.6825 and evaluation slowed to 42.7 s. Coarse categorical weeks appear to add noise beyond the ordered day-of-year feature.

## Experiment 34 — c0c96a0 (exploration; keep)

Hypothesis: day of month has a natural order, so numeric splits may capture stable within-month trends better than arbitrary category partitions. Converting it to a numeric field improved AUC to 0.6851 and sped evaluation to 36.4 s. This is a substantial win late in the run.

## Experiment 35 — d6b6410 (follow-up; keep)

Hypothesis: month ordering may also be better modeled numerically when day of year is available. Numeric month nudged AUC up to 0.6852 and reduced evaluation to 33.1 s. Ordered calendar encodings are promising.

## Experiment 36 — 69502d0 (follow-up; discard)

Numeric weekday lowered AUC to 0.6835 despite speeding evaluation. The weekly effect appears nonmonotonic; keep it categorical.

## Experiment 37 — c9a3a97 (ablation; discard)

Removing the depth-4 model simplified training and shrank the artifact, but AUC dropped to 0.6848. The blend still contributes after the numeric calendar changes.

## Experiment 38 — 8619c6e (ablation; keep)

With numeric month and day of month, removing the now-redundant `DayOfYear` improved AUC to 0.6856 and cut evaluation to 31.1 s. The combined date feature helped when components were categorical, but no longer helps once both are ordered.

## Experiment 39 — 629fd07 (ablation; discard)

Removing `DepHour` again reduced AUC to 0.6853. It sped evaluation to 27.4 s, but the lower AUC requires reverting it.

## Final summary

Best Eval AUC: **0.6856** at **8619c6e**, up from the 0.6743 baseline. The kept model blends 150 depth-3 trees and 100 depth-4 trees at 75/25 weights. Treating month and day of month as ordered numbers improved AUC and evaluation speed; removing the now-redundant day-of-year feature improved both again. A separate categorical departure-hour feature remained useful.

High-cardinality route and carrier-hour interactions, historical seasonal target rates, cyclic date encoding, weekly categories, stronger regularization, DART dropout, and alternative categorical partition limits did not improve the best score. Distance and departure hour ablations lost AUC despite low feature importance or faster scoring. A next run could test alternative blend members or targeted pre-departure holiday features. The human holdout set was not accessed.
