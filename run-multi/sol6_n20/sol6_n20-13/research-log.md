# Research log — oct6

## Baseline — 8d9c760

Unchanged starter model. Eval AUC 0.6743; training 0.6 s and evaluation 30.0 s. All further results are compared against the latest kept commit using the harness's rounded four-decimal AUC.

## Experiment 1 — more boosting rounds (exploration)

Hypothesis: the 100-tree baseline underfits. Try 300 trees at the same depth and learning rate to isolate ensemble length. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explains the tradeoff between step size, rounds, and model complexity. Training remains far below the one-minute limit at baseline.

Result f906baa: Eval AUC 0.6678, discard. Additional depth-6 rounds appear to overfit or amplify the 2005-to-2006 shift.

## Experiment 2 — shallower trees with more rounds (follow-up)

Hypothesis: reducing max_depth from 6 to 3 will smooth high-cardinality carrier/airport interactions, allowing 300 rounds to learn general patterns without the overfitting observed in experiment 1. This follows the complexity guidance in the [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result 647e659: Eval AUC 0.6805, keep. The large gain over baseline suggests shallow trees generalize better across years.

## Experiment 3 — 500 shallow rounds (follow-up)

Hypothesis: depth-3 trees may still benefit from more boosting rounds. Change only n_estimators from 300 to 500, checking whether the smoother tree structure delays overfitting.

Result 2c1e6b8: Eval AUC 0.6804, discard. Extra rounds do not help at this depth either.

## Experiment 4 — route categorical feature (exploration)

Hypothesis: the origin-destination pair has route-specific reliability that depth-3 trees may not efficiently derive from separate airport features. Add a train-fitted route category, preserving identical values in whole-frame training and single-row scoring. The dataset has 4,290 routes, so this is a meaningful cardinality test. Flight-delay research identifies route context as useful ([UC Berkeley study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)); [XGBoost categorical guidance](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes partition-based category splits.

Result 791f43e: Eval AUC 0.6694, discard. Route identity has too many categories for this sample and probably learns unstable route effects. Evaluation took 42.5 s versus about 30 s.

## Experiment 5 — scheduled minute within hour (exploration)

Hypothesis: departure minute within the hour captures scheduling conventions (e.g. flights leaving on the hour) across all times of day. The raw HHMM number can split by time of day but a shallow tree cannot easily reuse the same minute-of-hour pattern at every hour. The [UC Berkeley airline study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) finds scheduled time relevant; this specific transform tests a periodic schedule effect using only preflight information.

Result 63a3b3c: Eval AUC 0.6801, discard. The small loss means scheduled minute does not add useful generalizable information at this model capacity.

### Plateau research after experiments 3–5

[XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends controlling complexity with depth, child weight, gamma, or categorical thresholds when generalization suffers. The [categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) specifically limit category partitions. The [CatBoost paper](https://arxiv.org/abs/1706.09516) warns that target-derived categorical features can introduce prediction shift, so I will first try a lower-capacity model rather than in-sample target encoding.

## Experiment 6 — depth 2 with 500 rounds (exploration)

Hypothesis: this small, year-shifted dataset favors mostly additive effects over the depth-3 model's interactions. Reduce depth to 2 while using 500 rounds to compensate for lower per-tree capacity. This is a larger capacity change than the ineffective 300-to-500 adjustment at depth 3.

Result 6d346df: Eval AUC 0.6776, discard. Some depth-3 interactions are useful.

## Experiment 7 — limit category split search (exploration)

Hypothesis: 283-category airport features can lead the model to fit unstable partitions. Set `max_cat_threshold=16` to constrain the categories considered per partition, keeping the proven depth-3 and 300-round structure. This setting is specifically described as an overfitting control in the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result 65c5c6e: Eval AUC 0.6778, discard. The default categorical search appears to be useful; tighter limits underfit.

## Experiment 8 — remove day of month (ablation/simplification)

Hypothesis: the exact day number may encode events unique to 2005 and fail in 2006. Remove `DayofMonth` while preserving month and weekday, which represent more repeatable calendar effects. If AUC holds or improves, a simpler feature set also helps evaluation speed.

Result 518f710: Eval AUC 0.6799, discard despite a shorter evaluation. Day of month has weak but real signal under the required keep rule.

### Plateau research after experiments 6–8

No gain since experiment 2. [XGBoost guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) proposes row or column subsampling as a separate form of regularization from shallower trees. Airline studies also use seasonal features such as [day of year](https://www.mdpi.com/2226-4310/8/6/152). I will first test stochastic regularization and then calendar representation, rather than retrying route identity or extra rounds.

## Experiment 9 — 80% row subsampling (exploration)

Hypothesis: training each tree on a random 80% of flights reduces sensitivity to 2005-specific observations while keeping the depth-3 structure and 300 rounds that have worked best. Only `subsample` changes.

Result c350f7e: Eval AUC 0.6793, discard. Row subsampling loses information in this setting.

## Experiment 10 — continuous day of year (exploration)

Hypothesis: seasonal transitions and holiday periods are easier for a shallow tree to identify along one day-of-year axis than through separate month and day categories. Add day of year from the row's month and day; keep existing calendar features. Both years are non-leap years, and the [flight-delay modeling study](https://www.mdpi.com/2226-4310/8/6/152) lists day of year among schedule-derived predictors.

Result b769b26: Eval AUC 0.6817, keep. A smooth seasonal axis gave the first improvement since experiment 2.

### Synthesis after 10 experiments

Best: 0.6817 at b769b26. Depth-3 trees with 300 rounds improved on the starter's depth 6; day of year added another 0.0012. More rounds, route identity, departure minute, depth 2, tighter categorical partitions, removing day of month alone, and row subsampling all reduced AUC. The working theory is that a moderate interaction depth plus smooth seasonality captures stable cross-year structure, while highly specific route or calendar partitions are noisy. New research on [feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) suggests a possible way to prevent spurious depth-3 interactions; airline literature emphasizes seasonal and temporal context ([Li et al. 2021](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057)). Next I will test whether day of year makes raw calendar fields redundant, then consider constrained or selected interactions.

## Experiment 11 — remove day of month after day-of-year (ablation/simplification)

Hypothesis: day of year now carries the useful day-of-month signal in a form that generalizes across the calendar. Removing the original categorical day number may eliminate unstable split choices and speed row-by-row preparation.

Result b45afba: Eval AUC 0.6825, keep. Day of year replaces the original day category more effectively.

## Experiment 12 — remove month after day-of-year (ablation/simplification)

Hypothesis: day of year may also subsume month boundaries. Remove the month categorical input while retaining it only to compute day of year; this tests whether the continuous seasonal representation is sufficient.

Result 7d1cb76: Eval AUC 0.6826, keep. Slightly higher and faster, so the model can use day of year without month category.

## Experiment 13 — remove distance (ablation/simplification)

Hypothesis: origin and destination may already capture much of route length, and distance has the lowest total gain in the kept model (21 versus at least 66 for every other feature). Remove it to see whether the weak signal matters for cross-year AUC. Feature gain guides this ablation; harness Eval AUC remains the only keep criterion.

Result 8ce980b: Eval AUC 0.6813, discard. Distance contributes useful information despite low model gain.

## Experiment 14 — smaller learning rate with more rounds (follow-up)

Hypothesis: the current day-of-year model may benefit from smaller boosting steps. Halve learning rate to 0.05 and double the number of trees to 600, keeping approximate total boosting strength. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explicitly pairs lower step size with more rounds as a way to control overfitting.

Result 9d783e9: Eval AUC 0.6834, keep. Smaller steps improve the current model.

## Experiment 15 — still smaller boosting steps (follow-up)

Hypothesis: if smoother boosting is beneficial, 0.03 learning rate with 1,000 trees (same total 30 units) may further reduce path dependence and improve ranking. This isolates step size at approximately fixed total boosting weight.

Result 2a94ea7: Eval AUC 0.6829, discard. 0.05 appears closer to the useful step size.

## Experiment 16 — minimum child weight 10 (exploration)

Hypothesis: high-cardinality origin and destination features may create small, unstable leaves. Raising `min_child_weight` from its default 1 to 10 should suppress those leaves while retaining depth-3 structure. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) define it as the minimum child Hessian mass.

Result 5bad961: Eval AUC 0.6834, discard because identical rounded AUC with a more complex configuration and no meaningful speed gain.

## Experiment 17 — depth 4 on the seasonal model (exploration)

Hypothesis: the day-of-year feature and smaller learning rate may let one extra interaction level capture useful airport-by-season or carrier-by-time effects. Test depth 4 at 600 rounds and 0.05 learning rate; this probes between the earlier depth-2 and depth-6 extremes.

Result f218a9a: Eval AUC 0.6790, discard. The extra depth overfits despite seasonality and smaller steps.

### Plateau research after experiments 15–17

Three discards since the 0.6834 model. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes `lossguide`, which grows whichever node offers the most loss reduction, from `depthwise`, which grows by level. A leaf budget may permit selected higher-order interactions without widening every tree. [Feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) are another way to prevent spurious combinations, but I will first test adaptive tree shape because it uses fewer domain assumptions.

## Experiment 18 — loss-guided eight-leaf trees (exploration)

Hypothesis: a fixed budget of eight leaves per tree will spend complexity on only the strongest branches, potentially keeping helpful localized interactions while avoiding the broad overfitting of depth 4. Use `lossguide`, `max_leaves=8`, and cap path depth at 5.

Result c80c546: Eval AUC 0.6827, discard. Adaptive branch depth did not beat the regular depth-3 trees.

## Experiment 19 — one-hot splits for small categories (exploration)

Hypothesis: partition splits may group unrelated carriers or weekdays by 2005-specific gradients. Set `max_cat_to_onehot=32` so 20 carriers and seven weekdays use one-hot splits, while airports remain partitioned. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes the split mechanisms and threshold parameter.

Result 9cd3ea0: Eval AUC 0.6817, discard. Partitioning small categories works better here.

## Experiment 20 — coarser histogram bins (exploration)

Hypothesis: day-of-year and departure time may contain fine-scale noise from 2005. Lower `max_bin` from the default 256 to 64 so numerical splits use broader bins, while keeping the successful model structure. [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_bin` controls the resolution of histogram splits.

Result 43e4787: Eval AUC 0.6829, discard. Coarsening numeric splits lost useful detail.

### Synthesis after 20 experiments

Best: 0.6834 at 9d783e9. Since the prior pause, removing categorical day and month after adding continuous day of year improved performance and speed; reducing learning rate from 0.1 to 0.05 with proportionally more rounds improved AUC. Distance remains useful. Finer learning rate, more tree depth, eight-leaf loss-guided growth, one-hot carrier/weekday splits, and coarse histograms did not help. The strongest repeatable pattern is smooth time and season effects with restrained interactions. Research on [delay propagation across flight rotations](https://www.eurocontrol.int/publication/eurocontrol-data-snapshot-59-better-first-wave-performance) and [schedule position and buffers](https://doi.org/10.1016/j.tre.2021.102333) motivates a route-relative schedule feature: it may approximate whether a departure is early or late within a route's service day using only information known ahead of time.

## Experiment 21 — departure time relative to route median (exploration)

Hypothesis: relative schedule position on a route conveys rotation exposure beyond absolute departure time. Fit each route's median scheduled departure minute on `train.csv`, then map it in `prepare(df)` and subtract from the row's scheduled minute. This follows the train-fitted lookup pattern in `program.md`; unknown routes remain missing.

Result 6450a4b: Eval AUC 0.6827, discard. Route-level schedule medians are likely noisy or unstable; the median route has only 32 training rows.

## Experiment 22 — departure time relative to origin median (follow-up)

Hypothesis: an origin-level median is much better supported than a route median and may capture whether a flight is early or late relative to its airport's service day. Keep the same preflight, train-fitted design but aggregate only by origin.

Result b037f04: Eval AUC 0.6829, discard. Relative schedule time is still weaker than the absolute time and airport categories already available.

### Plateau research after experiments 20–22

The best remains 0.6834. Train-fitted route/origin schedule medians add overhead without improving ranking. I researched [scikit-learn soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html), which averages predicted probabilities from fitted classifiers, and [XGBoost's boosted random-forest options](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). An ensemble may reduce model-specific errors, but needs diversity. I will first measure a simpler depth-2 model with the improved calendar representation, then consider a blend if its signal is competitive.

## Experiment 23 — depth-2 seasonal model (exploration)

Hypothesis: day-of-year may give an additive model enough seasonal information to become a useful, different predictor. Use depth 2 and 1,000 rounds at learning rate 0.05, which gives more additive boosting capacity than the earlier depth-2 test (done before day-of-year was engineered).

Result 1f0a6db: Eval AUC 0.6834, discard under the keep rule. It matches the best score but changes parameter values without simplifying code and trains slightly slower. Its comparable AUC despite shallower trees makes it a reasonable candidate for blending.

## Experiment 24 — equal soft vote of depth-2 and depth-3 models (exploration)

Hypothesis: the two models reach the same Eval AUC with different tree depth, so their ranking errors may partly cancel. Fit both on `train.csv` and average predicted probabilities with [scikit-learn's soft voting classifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). This changes the model combination while preserving the kept preparation function.

Result 18c9d50: Eval AUC 0.6843, keep. The two depth settings contain complementary ranking information.

## Experiment 25 — favor depth-3 model in the vote (follow-up)

Hypothesis: the depth-3 model may be the more stable component, since its 600-tree version is faster and was kept first. Give it two thirds of the soft-vote weight and the depth-2 model one third; this probes whether the equal blend underweights interactions.

Result c1f1c54: Eval AUC 0.6842, discard. Favoring depth 3 hurt slightly.

## Experiment 26 — favor depth-2 model in the vote (follow-up)

Hypothesis: the loss from giving depth 3 more weight suggests the smoother depth-2 model may make the blend more robust. Test the opposite 1:2 weighting, a distinct direction from experiment 25, to determine whether the optimum lies on the additive side of equal weighting.

Result 118c441: Eval AUC 0.6842, discard. Equal weighting remains best, consistent with useful but differently biased components.

## Experiment 27 — monotone departure time (exploration)

Hypothesis: delay risk largely increases through the service day because upstream delays accumulate. In the 2005 training data it climbs from about 0.19 at 06:00 to 0.65 at 20:00, though it declines after 20:00. Test an increasing monotonic constraint on `CRSDepTime` for both vote components, accepting the known late-night limitation. [XGBoost's monotonicity guide](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) explains how this prior can reduce noisy oscillations.

Result e172c26: Eval AUC 0.6828, discard. The decline after 20:00 and airport-specific time profiles make the global monotonic prior too rigid.

### Plateau research after experiments 25–27

Neither asymmetric ensemble weight nor monotonic departure time improved 0.6843. [Scikit-learn's time-feature study](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses periodic hour representations; domain research likewise points to hour as a useful preflight predictor ([Berkeley airline study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). I will test an hour category that can represent the observed nonmonotonic late-night behavior without constraining all airports alike.

## Experiment 28 — categorical scheduled departure hour (exploration)

Hypothesis: hour category groups flights into operational waves while the existing HHMM value preserves within-hour ordering. This may let shallow trees share a broad time effect across airlines and airports without forcing monotonicity.

Result 93d3f79: Eval AUC 0.6840, discard. The raw HHMM feature already expresses the relevant hour pattern well enough.

## Experiment 29 — cyclic seasonal coordinates (exploration)

Hypothesis: day of year has an artificial boundary between December and January. Add sine and cosine coordinates for the annual cycle, retaining the continuous day-of-year feature. [Scikit-learn's periodic-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) describes why two trigonometric coordinates make adjacent dates across the year boundary close in representation.

Result 45bddf3: Eval AUC 0.6819, discard. The cyclic coordinates introduce misleading grouping or distract the trees; a simple ordinal day-of-year works better.

## Experiment 30 — wider categorical partitions (exploration)

Hypothesis: lowering `max_cat_threshold` to 16 in experiment 7 hurt, suggesting the default categorical search may be too restrictive for airport features. Raise the threshold to 128 for both vote components, allowing more airport categories to be considered at each partition. This probes the opposite direction of the earlier threshold test, as described in the [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result a9c2f88: Eval AUC 0.6838, discard. The default categorical setting remains preferable.

### Synthesis after 30 experiments

Best: 0.6843 at 18c9d50. The main gain since the previous pause is averaging depth-2 and depth-3 models; equal weights beat either 2:1 weighting. Route/origin relative schedule features, a global time monotonic constraint, extra hour category, cyclic year coordinates, and wider categorical partitions did not improve the blend. The best theory is that the two model capacities capture complementary smooth and interaction signals, while extra transformed features generally add noise. New [XGBoost documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies L2 leaf regularization as a way to make predictions more conservative without changing tree depth. I will test this before trying additional ensemble diversity.

## Experiment 31 — stronger L2 regularization (exploration)

Hypothesis: the models may still give overly large corrections on rare airport categories. Increase `reg_lambda` from the default 1 to 10 in both vote components, preserving all other choices. This shrinks leaf weights and may improve cross-year AUC.

Result 9539abe: Eval AUC 0.6842, discard. Stronger L2 slightly reduces ranking quality.

## Experiment 32 — remove L2 leaf shrinkage (follow-up)

Hypothesis: if increasing L2 is slightly harmful, the default may also be too conservative for the two shallow ensemble components. Test `reg_lambda=0`, the opposite direction, to determine whether leaf shrinkage is useful here.

Result cc7a8cf: Eval AUC 0.6842, discard. Both directions around default L2 give the same slight decline; default 1 is well placed.

## Experiment 33 — minimum split gain 5 (exploration)

Hypothesis: airport partitions with tiny training gain may be year-specific. Set `gamma=5` in both vote components, requiring larger gain for every split while leaving established trees otherwise unchanged. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines gamma as minimum split loss reduction.

Result dc2d6f4: Eval AUC 0.6852, keep. Pruning low-gain splits materially helps and shrinks the artifact from 3.8 to 2.8 MB.

## Experiment 34 — minimum split gain 10 (follow-up)

Hypothesis: if gamma 5 removed noise, gamma 10 may improve further. Double the split-gain threshold while retaining the successful ensemble to test the upper side of this regularization direction.

Result 55e57a0: Eval AUC 0.6850, discard. Some splits removed by gamma 10 are useful.

## Experiment 35 — minimum split gain 2 (follow-up)

Hypothesis: gamma 5 may be slightly too aggressive; compare a lower threshold of 2 against the known zero and ten endpoints. This tests whether the AUC peak occurs with gentler pruning rather than more aggressive pruning.

Result 5891582: Eval AUC 0.6845, discard. Gamma 5 is the best of 0, 2, 5, and 10, so I will keep it fixed while testing whether pruning changes the useful number of rounds.

## Experiment 36 — longer boosting with pruned trees (follow-up)

Hypothesis: gamma 5 makes each tree smaller and may leave stable residual structure after the original 600/1,000 rounds. Increase depth-3 rounds to 800 and depth-2 rounds to 1,300 (about one-third more) to see whether additional pruned trees improve AUC.

Result b9e711c: Eval AUC 0.6852, discard. More rounds match the score but take longer and enlarge the artifact.

## Experiment 37 — shorter boosting with pruned trees (ablation/simplification)

Hypothesis: if extra pruned rounds add no AUC, some existing rounds may be redundant. Reduce depth-3 rounds from 600 to 400 and depth-2 rounds from 1,000 to 700. An equal score would qualify as a faster, smaller model; a gain would indicate late overfitting.

Result 91594fb: Eval AUC 0.6852, keep. Training is faster (2.7 s versus 3.2 s) and the artifact is smaller (2.5 versus 2.8 MB) at the same rounded AUC.

## Experiment 38 — further shorten pruned ensemble (ablation/simplification)

Hypothesis: gamma 5 may make even more boosting rounds redundant. Test 300 depth-3 rounds and 500 depth-2 rounds, roughly half of the original gamma-5 ensemble, to locate the smallest model that preserves Eval AUC.

Result be41f0d: Eval AUC 0.6851, discard. A further reduction costs 0.0001 AUC; the 400/700 balance remains best.

## Experiment 39 — remove additive vote component (ablation/simplification)

Hypothesis: gamma pruning may have reduced the complementary errors that made blending useful. Train only the depth-3, 400-round component at gamma 5. If it matches or improves AUC, removing the voting wrapper yields a substantially simpler and faster model.

Result bc771d6: Eval AUC 0.6846, discard. The additive component still contributes useful diversity.

## Experiment 40 — remove interaction vote component (ablation/simplification)

Hypothesis: the depth-2, 700-round component may alone retain the blend's AUC after pruning. Test it by itself, completing the component ablation and showing whether the more complex depth-3 model is still needed.

Result 0487fde: Eval AUC 0.6843, discard. Both components are necessary for the 0.6852 result.

### Synthesis after 40 experiments

Best AUC: 0.6852 at 91594fb. Gamma 5 produced the only substantive gain in the last ten experiments. Gamma 2 and 10 were lower; default and zero L2 were effectively tied, while strong L2 slightly hurt. Pruned trees could be shortened to 400/700 rounds without losing AUC, but shortening further lost 0.0001. Removing either vote component lost 0.0006 or 0.0009. The current theory is that split pruning and structural diversity work together: shallow additive and depth-3 interaction models make different useful errors. Research on [ensemble diversity](https://proceedings.mlr.press/v108/durrant20a.html) and [scikit-learn voting](https://scikit-learn.org/stable/modules/ensemble.html) motivates one final source of tree-shape diversity, while keeping the two proven components dominant.

## Experiment 41 — add a small depth-4 vote component (exploration)

Hypothesis: gamma 5 may make a depth-4 model less prone to the overfitting seen without pruning. Add a 300-round depth-4 component at one-fifth of the total soft-vote weight, retaining the depth-3 and depth-2 components at two-fifths each. This tests whether selected higher-order interactions add complementary ranking signal.

Result a9c5589: Eval AUC 0.6855, keep. A small pruned depth-4 component adds complementary signal.

## Experiment 42 — equal three-way vote (follow-up)

Hypothesis: the third component improved AUC at 20% weight, so giving all three models equal weight may capture more of its higher-order signal. This changes only the vote balance, not the fitted component specifications.

Result 12712ae: Eval AUC 0.6855, discard because the rounded AUC and speed tie the kept model with no simpler code. Equal weighting may still allow removal of the explicit weights argument.

## Experiment 43 — implicit equal weights (ablation/simplification)

Hypothesis: `VotingClassifier` defaults to equal weights. Remove the explicit weights argument, which produces the same votes as experiment 42 with simpler code. If the harness repeats 0.6855, keep this clean-up under the tie rule.

Result 016b53e: Eval AUC 0.6855, keep. Equal weighting now needs one less argument at no AUC cost.

## Experiment 44 — mature depth-4 component (follow-up)

Hypothesis: the depth-4 component contributed at 300 rounds, and gamma 5 limits noisy splits. Increase only that component to 500 rounds to see whether more higher-order residual structure improves the equal three-way vote.

Result a2e8649: Eval AUC 0.6855, discard. More depth-4 rounds tie but enlarge and slow the model.

## Experiment 45 — shorten depth-4 component (ablation/simplification)

Hypothesis: the added depth-4 signal may be present early in boosting. Reduce just that component from 300 to 200 rounds, leaving the two proven models unchanged. An equal AUC would give a smaller, faster ensemble.

Result 77d7068: Eval AUC 0.6857, keep. The shorter depth-4 component is both better and smaller, suggesting later deep splits overfit.

## Experiment 46 — depth-4 component at 100 rounds (follow-up)

Hypothesis: the deeper component's best signal may be concentrated in early trees. Halve its rounds again from 200 to 100 to locate the boundary between useful higher-order signal and underfitting.

Result da23300: Eval AUC 0.6862, keep. The deeper model's early trees are substantially more useful to the blend than its later trees.

## Experiment 47 — depth-4 component at 50 rounds (follow-up)

Hypothesis: a very short depth-4 member may provide just the coarse interactions that complement the longer shallow models. Halve from 100 to 50 rounds to test whether the AUC improvement continues.

Result 0b710ae: Eval AUC 0.6867, keep. Shorter depth-4 contribution continues to improve the blend.

## Experiment 48 — depth-4 component at 25 rounds (follow-up)

Hypothesis: the ensemble may need only the earliest, broadest depth-4 interactions. Cut its 50 rounds to 25, while preserving the two mature shallow components.

Result 419aca2: Eval AUC 0.6869, keep. Early depth-4 structure still adds signal with fewer trees.

## Experiment 49 — depth-4 component at 10 rounds (follow-up)

Hypothesis: performance has improved with each reduction from 300 to 25 deeper rounds. Try 10 rounds to see whether the useful contribution is concentrated in the first few trees or whether this removes too much signal.

Result 733e48d: Eval AUC 0.6865, discard. Ten rounds underfit the higher-order component.

## Experiment 50 — depth-4 component at 18 rounds (follow-up)

Hypothesis: 25 rounds score 0.6869 and 10 rounds score 0.6865. Test 18 rounds between them to check whether a modestly shorter component preserves or improves the peak while reducing the artifact.

Result 5ed0a2f: Eval AUC 0.6869, keep. The 18-round artifact is 2,653,620 bytes versus 2,703,065 bytes at 25 rounds, with the same rounded AUC.

### Synthesis after 50 experiments and final summary

Best Eval AUC: **0.6869** at **5ed0a2f**, up from the 0.6743 baseline by 0.0126. The final model uses a train-fitted, row-consistent day-of-year feature and an equal soft vote of three XGBoost models: depth 3 with 400 rounds, depth 2 with 700 rounds, and depth 4 with 18 rounds; all use learning rate 0.05 and gamma 5. The run ended with the branch at this kept commit. Every run is recorded in `results.tsv` and the last artifact is saved for post-hoc holdout scoring.

What worked: shallower trees than the starter, continuous day of year, removing redundant month and day categories, smaller learning rate, averaging different depths, pruning low-gain splits with gamma, and making the depth-4 vote member very short. What did not: longer unpruned boosting, route category, schedule-relative group medians, departure-minute/hour features, cyclic year encoding, different categorical thresholds, monotonic departure time, row subsampling, or either ensemble member alone. The run never inspected holdout data.

Potential next directions from final research: [XGBoost's DART booster](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) can regularize by dropping trees, though training may exceed this setup's one-minute limit; [feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) may restrict spurious airport interactions. Another focused test is whether a separate early-stopped deep member can contribute at a lower vote weight without exceeding training time. These are ideas for a future run, not untested changes to this artifact.
