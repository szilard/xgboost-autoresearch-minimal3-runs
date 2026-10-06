# XGBoost experiment: oct6

Started 2026-10-06 UTC from baseline commit `b15ec66`. Objective: maximize the harness's four-decimal Eval AUC, keeping only improvements (or equal scores with simpler/faster code). The 2005 training sample has 200,000 rows, balanced labels, eight predictors, and no missing values. Evaluation is on 2006 and remains accessible only through the harness. All features must give identical values for a row processed alone or in a batch.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): control complexity and regularization; pair smaller learning rates with more boosting rounds. Initial parameter probes will compare capacity with conservative leaf fitting, rather than use an automated search or extra scoring procedure.
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, minimum Hessian per leaf, L2 penalties, row/column sampling, and categorical split limits offer distinct controls. Installed XGBoost is 3.4.1; use stable documentation, not development defaults.
- [XGBoost categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): native categorical partitioning groups categories by their fitted contribution. Train-fitted categories must remain consistent in row-at-a-time inference.
- [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): scheduled time blocks and calendar components motivate row-local time features. Adapt only features available before departure; no external datasets, actual-flight outcomes, or sample-frequency features.

## Baseline

- Commit: `b15ec66`.
- Unchanged starter: 100 trees, depth 6, learning rate 0.1, six native categorical columns plus scheduled HHMM departure and distance.
- Hypothesis: establish the required reference before editing code.
- Result: **0.6743**, keep. Training 1.6s including startup; evaluation 30.8s; total 32.4s.

## Experiment 1 — more gradual boosting

- Class: follow-up to baseline.
- Hypothesis: 400 trees at learning rate 0.05 (versus 100 at 0.1) will capture stable residual schedule interactions while taking smaller steps. Keep all features and tree depth unchanged to test boosting budget.
- Source: XGBoost tuning guide above.
- Commit: `48ac2f6`. Result: **0.6724**, discard (best 0.6743). Training 3.1s; evaluation 31.1s. More rounds worsened temporal generalization, suggesting overfitting rather than inadequate boosting.

## Experiment 2 — simpler categorical preparation

- Class: ablation/simplification of baseline.
- Hypothesis: pre-fit categorical dtypes and construct the output frame once; pandas categoricals already map unknown levels to missing, making the explicit membership filter unnecessary. Predictions should stay identical while row-at-a-time preparation gets faster.
- Validation: compare against the saved baseline prepare on training rows and synthetic unknown categories; check batch/single-row equality without evaluating a model.
- Commit: `e130f87`. Result: **0.6743**, keep at equal AUC with simpler/faster code. Total 11.7s; evaluation 10.2s. Exact preparation and batch/single-row checks passed, including unseen categories. Pandas emits a future-version warning for unknown levels; current behavior correctly produces missing values.

## Experiment 3 — remove day of month

- Class: ablation/simplification.
- Hypothesis: arbitrary day-of-month category splits encourage memorization of 2005 calendar/weather patterns. Removing this predictor may improve transfer to 2006 while retaining month, weekday, and scheduled time. Extra boosting already hurt in experiment 1.
- Commit: `a1068df`. Result: **0.6759**, keep (+0.0016). Total 10.5s; training 1.4s. Removing day of month supports the temporal-overfitting hypothesis.

## Experiment 4 — one-category categorical splits

- Class: exploration of categorical handling.
- Hypothesis: native partition splits can form flexible subsets of airports and calendar categories that fit noise. Force one-category-versus-rest splits with max_cat_to_onehot=512; all existing categorical cardinalities are below this threshold. Keep 100 trees and all other parameters fixed.
- Source: [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).
- Commit: `1c1f67f`. Result: **0.6771**, keep (+0.0012). Total 10.3s; training 1.2s. Less flexible categorical splits transfer better.

## Experiment 5 — more boosting with one-category splits

- Class: follow-up to experiment 4.
- Hypothesis: the simpler split family has lower capacity per tree and may now benefit from 400 trees at learning rate 0.05. This differs from experiment 1 by using one-category splits and excluding day of month, both successful regularization changes.
- Commit: `f6d76c6`. Result: **0.6796**, keep (+0.0025). Total 11.5s; training 2.3s. Additional rounds help once categorical split complexity is controlled, unlike experiment 1.

## Experiment 6 — shallower trees

- Class: ablation/simplification of experiment 5.
- Hypothesis: depth 4 instead of 6 restricts high-order interactions and may further improve temporal generalization. Hold the 400-round, 0.05-learning-rate schedule and features fixed to isolate depth.
- Commit: `f6a1a79`. Result: **0.6770**, discard (-0.0026). Total 11.5s. Removing interaction depth loses useful signal; retain depth 6 and test leaf support instead.

## Experiment 7 — require more support per leaf

- Class: follow-up to experiment 5.
- Hypothesis: min_child_weight=30 (instead of 1) limits noisy small-leaf estimates without removing depth-6 interactions that proved useful. This parameter bounds summed logistic Hessian, not raw sample count.
- Source: XGBoost parameter reference from initial research.
- Commit: `a5275d0`. Result: **0.6800**, keep (+0.0004). Total 11.4s. Stronger leaf support provides a small improvement while preserving useful depth.

## Experiment 8 — separate departure hour and minute

- Class: exploration of time feature engineering.
- Hypothesis: explicitly exposing hour and minute within the hour makes common departure-bank and schedule-rounding patterns accessible without many HHMM splits. Retain original HHMM time for its strong ordering signal.
- Research: [scikit-learn time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses ordinal, categorical and periodic time representations; the Berkeley study above motivates scheduled time blocks for flights. Use only row-local arithmetic, with no group counts.
- Commit: `cd56cb0`. Result: **0.6797**, discard (-0.0003). Total 11.8s. Explicit hour/minute features added no useful transfer signal at this configuration; batch/single-row equality passed.

## Experiment 9 — route identity

- Class: exploration of categorical interactions.
- Hypothesis: an origin-destination category gives each sufficiently supported route a direct split, representing pair-specific effects without spending two tree levels. Retain the successful one-category split strategy by raising its threshold to 20000 for the new high-cardinality feature.
- Research: [Cheng et al., Wide & Deep Learning](https://arxiv.org/abs/1606.07792) motivates cross-product features while noting weak generalization to unseen combinations. Here native missing handling, original airport columns, and min_child_weight=30 provide fallbacks and regularization.
- Commit: `366d017`. Result: **0.6801**, keep (+0.0001, a small increment rather than strong evidence). Total 13.0s; training 2.5s. 4290 train-fitted routes; row-invariance check passed.

## Experiment 10 — airline-airport interactions

- Class: follow-up to route identity.
- Hypothesis: carrier-origin and carrier-destination categories capture hub and station operations that differ by airline. This differs from route identity because it pools routes within each airline-airport pairing; retain original marginal categories and route fallback.
- Commit: `e08ff31`. Result: **0.6810**, keep (+0.0009). Total 15.2s; training 2.8s. Airline-airport combinations are more useful than route identity alone.

## Synthesis after 10 experiments

- Best: **0.6810** at `e08ff31`, compared with baseline 0.6743.
- Helpful: simplified preparation, removing arbitrary day-of-month categories, one-category splits, extra boosting after that regularization, minimum leaf support, and airline-airport interactions.
- Unhelpful: extra boosting with flexible categorical partitions, reducing depth from 6 to 4, and separate departure hour/minute fields.
- Working theory: scheduled time and stable operational combinations transfer across years, while flexible categorical partitions overfit year-specific patterns. Some interaction depth remains necessary.
- Next: test more depth with leaf support, then pooled categorical risk estimates and regularized ensembles if warranted.
- New research: [scikit-learn TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) and [CatBoost paper](https://arxiv.org/abs/1706.09516) explain the leakage risk of target means fitted on a row's own label. Standard fit_transform/transform behavior would violate this task's identical row preparation rule. A potential adaptation is fixed feature-derived encoding partitions with train-fitted maps excluding each partition, applied identically to every row. Encoding partitions would not be model cross-validation and would produce no additional evaluation metric.

## Experiment 11 — more supported interaction depth

- Class: follow-up to experiment 10.
- Hypothesis: depth 8 instead of 6 can model time-dependent airline-airport effects; min_child_weight=30 continues to prevent small leaves. This reverses the failed shallow-tree ablation in a deliberate direction, with newly useful interaction features.
- Commit: `8642581`. Result: **0.6815**, keep (+0.0005). Total 15.8s; training 3.4s. More interaction depth remains useful when leaves require support.

## Experiment 12 — smoothed categorical risk lookups

- Class: exploration of supervised categorical encoding.
- Hypothesis: smoothed numeric delay-rate estimates let trees pool airports/routes with similar risk without arbitrary categorical partitions at every node. Add estimates for origin, destination, route, carrier-origin, and carrier-destination while preserving original categories.
- Method: deterministic hashes of each row's predictor values assign one of five encoding partitions. For each partition, fit lookups using only other training partitions, with prior mean 0.5 and smoothing weight 100. Every training and future row uses the same hash rule and the same fitted tables. No row's own label contributes to its encoding; identical predictor rows stay in the same excluded partition. Partitions are solely for fitting preprocessing, not model cross-validation; the harness remains the sole metric.
- Sources: TargetEncoder documentation and CatBoost paper cited in the 10-experiment synthesis.
- Required checks: batch/single-row equality, predictor independence from supplied labels, and direct verification of an excluded-partition mean.
- Commit: `79421cd`. Result: **0.6798**, discard (-0.0017). Total 21.5s; training 3.9s. All three preprocessing checks passed. Numeric estimates did not improve transfer under the existing depth-8 model, potentially because this representation needs less capacity.

## Experiment 13 — risk lookups with conservative trees

- Class: exploration of the interaction between representation and model complexity.
- Hypothesis: unlike sparse one-category splits, numeric risk estimates already pool categories, so depth-4 trees can use them without expensive multi-level category selection. Test 600 trees at 0.03, depth 4, min_child_weight=100 and reg_lambda=10 with the risk features from experiment 12. This is a deliberate lower-variance configuration, not another smoothing tweak.
- Commit: `c052fa8`. Result: **0.6793**, discard (-0.0022). Total 20.8s; training 3.3s. Reducing capacity did not rescue target-risk encoding. Return to the best raw-category model.

## Experiment 14 — geography inferred from training distances

- Class: exploration of unsupervised geographic features.
- Hypothesis: airport location and route direction may share delay patterns across airports without fitting target statistics. Learn an approximate 3D airport map solely from median route distances in train.csv: symmetric distance graph, all-pairs shortest paths, then classical multidimensional scaling. Add three coordinates for each endpoint and three destination-minus-origin coordinates, retaining raw airports and distance.
- Research: [Isomap documentation](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html), [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html), and [Trosset & Buyukbas](https://arxiv.org/abs/2006.10858) describe graph distances followed by Euclidean embedding. Geographic features are also discussed in the Berkeley flight study. This is an adaptation, not an assertion that inferred axes are exact latitude/longitude.
- All geography is fitted on training predictors only; no external airport data, labels, counts, or data-dependent batch transformations are used.
- Commit: `27ee967`. Result: **0.6824**, keep (+0.0009). Total 17.0s; training 3.8s. The 284-airport graph is connected; batch/single-row equality passed. Unsupervised geography helps without label-derived features.

## Experiment 15 — stronger leaf-weight shrinkage

- Class: follow-up to the geographic representation.
- Hypothesis: reg_lambda=20, up from the default 1, shrinks estimates in the deeper model now using both categorical and geographic splits. Keep leaf support, depth, features, and boosting schedule fixed to isolate this regularizer.
- Source: XGBoost parameter reference from initial research.
- Commit: `e273acc`. Result: **0.6827**, keep (+0.0003). Total 17.0s; training 3.9s. L2 shrinkage gives a modest gain.

## Experiment 16 — longer boosting after regularization

- Class: follow-up to experiments 14 and 15.
- Hypothesis: geography supplies transferable structure and L2 shrinks leaf updates, so doubling rounds from 400 to 800 at the same learning rate may learn useful residual patterns. This is a capacity test under a substantially different representation/regularization regime from early experiments.
- Commit: `67e3f16`. Result: **0.6826**, discard (-0.0001). Total 19.1s; training 5.8s. Doubling rounds does not improve temporal generalization; retain 400.

## Experiment 17 — ordinal and cyclic season representation

- Class: exploration of seasonal feature representation.
- Hypothesis: numeric month plus sine/cosine of month permit broad seasonal splits, including winter across the December/January boundary, that can interact efficiently with inferred geography. Retain the original month category for irregular residual effects.
- Source: scikit-learn time feature engineering example, already read before experiment 8.
- Commit: `198c8c7`. Result: **0.6823**, discard (-0.0004). Total 17.5s. Broad season representations did not improve on the existing categorical month and geography combination.

## Experiment 18 — proximity to travel holidays

- Class: exploration of calendar semantics.
- Hypothesis: signed day offsets within a week of Thanksgiving, Christmas, New Year and July 4 capture transferable travel patterns while avoiding unrestricted day-of-month categories. Thanksgiving is reconstructed from the row's weekday and calendar position, so its date can move across years. Outside each window use missing values.
- Source: [OPM holiday reference](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay/) confirms fixed dates and Thanksgiving's fourth-Thursday rule. Holiday travel relevance is a modeling hypothesis.
- Validation: row invariance plus known Thanksgiving dates in both 2005 and 2006.
- Commit: `0c09316`. Result: **0.6858**, keep (+0.0031). Total 19.5s; training 5.1s. Calendar semantics give the largest feature gain so far. Thanksgiving date and row-invariance checks passed.

## Experiment 19 — summer travel holiday offsets

- Class: follow-up to experiment 18.
- Hypothesis: proximity to Memorial Day (last Monday in May) and Labor Day (first Monday in September) captures the beginning/end of summer travel. Compute signed offsets within one week, including adjacent-month days, using only each row's month/day/weekday.
- Source: OPM holiday reference cited in experiment 18.
- Commit: `940a0b7`. Result: **0.6858**, discard (equal AUC with more complex and slower code). Total 20.2s. Date checks passed; retain the four earlier holiday offsets.

## Experiment 20 — stochastic row and feature sampling

- Class: exploration of stochastic regularization.
- Hypothesis: subsample=0.8 and colsample_bytree=0.85 reduce sensitivity to particular 2005 observations and competing representations, averaging more diverse trees while keeping the same feature set and boosting schedule.
- Source: XGBoost tuning guide's randomness-based regularization discussion.
- Additional research considered: XGBoost monotonic-constraint documentation. Read-only training summaries show delay rates rising from morning to evening but falling late at night, so a global monotonic clock constraint is not justified and is not used.
- Commit: `e076935`. Result: **0.6863**, keep (+0.0005). Total 20.2s; training 5.3s. Stochastic regularization helps.

## Synthesis after 20 experiments

- Best: **0.6863** at `e076935`, +0.0120 over baseline.
- Strongest new findings: geography inferred from training distances adds signal; semantic holiday offsets add substantially more than arbitrary date features. L2 shrinkage and stochastic sampling produce smaller improvements.
- Unhelpful: target-risk lookups in both deep and conservative models, doubling boosting rounds, cyclic month features, and adding summer-holiday offsets (tie with more code).
- Working theory: useful calendar events move between dates across years, while geographic/operational structure persists. The model benefits from representing those relationships explicitly and regularizing residual interactions.
- Training feature importance puts scheduled time first and ranks New Year, Thanksgiving and July 4 offsets prominently. This is descriptive training-model evidence, not a second metric or held-out analysis.
- New research: [XGBoost boosted forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) and [scikit-learn probability averaging](https://github.com/scikit-learn/scikit-learn/blob/main/doc/modules/ensemble.rst) motivate reducing variance through multiple randomized trees or models. All constituent models will use only train.csv; ensemble scores will still come exclusively from the harness.

## Experiment 21 — boosted forest within each round

- Class: follow-up to successful stochastic sampling.
- Hypothesis: num_parallel_tree=3 averages three randomized trees at every boosting step, reducing noise before fitting the next residual. Hold the 400-round schedule and all other settings fixed.
- Source: XGBoost random-forest tutorial cited above.
- Commit: `b94dc2f`. Result: **0.6866**, keep (+0.0003). Total 30.1s; training 14.8s, below the 60s limit. Averaging within rounds helps slightly.

## Experiment 22 — average independently boosted models

- Class: exploration of ensemble structure, following experiment 21.
- Hypothesis: three independent 400-tree models with seeds 42, 137, and 2026 have different residual-fitting paths, potentially providing more useful diversity than three trees sharing residuals in each round. Use an equal average of class probabilities and one tree per round in each member, keeping the total tree count at 1200.
- Source: scikit-learn soft-voting documentation cited in the 20-experiment synthesis.
- All three members fit the same allowed training set; no extra scoring or model-selection folds.
- Commit: `c1cda88`. Result: **0.6866**, discard. Total 28.6s; training 13.6s versus 14.8s for the forest. Equal AUC with a more complex estimator wrapper; the modest single-run timing difference is not compelling evidence of a repeatable speed improvement, so prefer the simpler single estimator.

## Experiment 23 — departure relative to route schedule

- Class: exploration of predictor-only schedule lookups.
- Hypothesis: a flight departing late relative to its route's usual schedule may have different operational risk from a flight at the same absolute time on another route. Fit the median operational departure minute for each route on training predictors only; expose both that median and the row's deviation.
- Operational day starts at 04:00 to keep late-night departures near each other across midnight. All mapping is fitted once and applied unchanged per row. This follows the train-fitted route-median pattern explicitly described in program.md; no counts or target rates are features.
- Commit: `29377e1`. Result: **0.6866**, discard (equal AUC, more complexity and slower). Total 32.5s; training 16.0s. Row-invariance passed, but schedule context added no gain.

## Experiment 24 — global additive holiday effects

- Class: exploration of structural regularization.
- Hypothesis: specific holiday-by-airport interactions can memorize local 2005 weather rather than transferable travel patterns. Use two disjoint interaction groups: the four holiday offsets, and every operational/geographic feature. Each tree can model only one group, making holiday contributions additive to the operational model.
- Source: [XGBoost feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html). Disjoint groups are intentional: the documented behavior of overlapping groups would not enforce this separation.
- Commit: `ddb1b11`. Result: **0.6854**, discard (-0.0012). Total 29.4s; training 14.4s. Fully global holiday effects lose useful contextual interactions.

## Experiment 25 — restricted categorical partitions

- Class: exploration of categorical pooling under stronger regularization.
- Hypothesis: max_cat_to_onehot=4 with max_cat_threshold=8 can pool small groups of sparse route/station categories that cannot individually satisfy leaf support. This differs from the failed starter's flexible partitions by a much smaller split threshold, stronger leaf support/L2, stochastic sampling, and forest averaging.
- Research refresh after recent discards: [XGBoost categorical split parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) identifies max_cat_threshold as a partition-overfitting control. Test that mechanism rather than another round-count tweak.
- Commit: `6f70aaf`. Result: **0.6836**, discard (-0.0030). Total 37.7s; training 22.4s. Even heavily restricted partitions hurt temporal transfer; retain one-category splits.

## Experiment 26 — remove route category

- Class: ablation/simplification.
- Hypothesis: route identity's initial 0.0001 gain may be redundant after adding airport geometry, direction, holidays, and forest averaging. Remove the 4290-level category while preserving both airport identities and carrier-airport combinations; this also reduces categorical split work.
- Commit: `7090fd7`. Result: **0.6864**, discard (-0.0002). Total 28.4s. Route identity remains slightly useful even with geography and holidays.

## Experiment 27 — label-smoothed logistic objective

- Class: exploration of training objective regularization.
- Hypothesis: train with soft targets 0.05/0.95 using logistic gradients to reduce overconfident fits to unpredictable delay outcomes. Original binary labels are preserved for all harness evaluation; the training objective alone changes. At the population optimum symmetric smoothing preserves probability ordering, although finite-tree behavior may differ.
- Research: [Mueller et al., When Does Label Smoothing Help?](https://arxiv.org/abs/1906.02629) and [XGBoost custom objectives](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html). This is an adaptation from neural-network regularization, not an established guarantee for this dataset.
- Validation: finite-difference checks of gradients and Hessians before training.
- Commit: `9c795e7`. Result: **0.6866**, discard (equal AUC, more complex and slightly slower). Total 30.8s; training 15.4s. Finite-difference derivative checks passed, but the objective offered no scoring advantage.

## Experiment 28 — shallower forest after feature engineering

- Class: ablation/simplification of the best forest.
- Hypothesis: reduce max_depth from 8 to 6 now that geography and holiday semantics expose relationships directly. Earlier shallow-tree experiments used raw categories without these representations, so they do not settle the appropriate interaction depth of the current model.
- Commit: `c175384`. Result: **0.6856**, discard (-0.0010). Total 26.7s; training 11.9s. The richer representation still benefits from deeper interactions.

## Experiment 29 — loss-guided leaf allocation

- Class: exploration of tree growth policy.
- Hypothesis: one-category splits may need long, uneven paths to distinguish many airports/routes. Use lossguide, unrestricted depth, and max_leaves=64 to allocate a fixed leaf budget where residual loss warrants it, rather than expanding by depth. Preserve the best model's stochastic sampling and forest averaging.
- Research: XGBoost parameter reference, re-read before experiment 25, documents the distinction between depthwise and loss-guided growth.
- Commit: `8bb5af6`. Result: **0.6866**, discard (equal AUC, slower and more configuration). Total 42.0s; training 26.4s. Unbalanced paths do not improve ranking at this leaf budget.

## Experiment 30 — direct fitted category-code lookups

- Class: ablation/simplification of preprocessing overhead.
- Hypothesis: pre-fit dictionaries from category values to integer codes and use Categorical.from_codes. This preserves the exact categories and missing handling while avoiding per-row constructor inference and future-version warnings for unknown levels. The model, feature values, column order and parameters must remain identical.
- Validation: compare prepared rows against the saved best artifact, including synthetic unknown categories, and test batch/single-row equality. Keep only at equal AUC with a clear runtime benefit.
- Commit: `8af0d94`. Result: **0.6866**, keep at equal AUC with clear speed benefit. Total 23.9s; training 14.9s; evaluation 9.1s versus 15.2s for the previous best. Exact equivalence and row-invariance checks passed, including unknown categories. New runs no longer emit categorical deprecation warnings.

## Synthesis after 30 experiments

- Best AUC remains **0.6866**, now at `8af0d94` with faster preparation (original score-best was `b94dc2f`).
- Forest averaging gave a small gain. Independent model averaging, route schedule context, label smoothing and loss-guided growth all tied but added complexity or cost. Restricting holiday interactions, reintroducing categorical partitions, removing route identity and reducing depth lost accuracy.
- Working theory: both operational detail and contextual holiday effects matter. The best model is already robust to several proposed changes; further progress needs a different representation or treatment of the year shift, not cosmetic tuning.
- New research: [Time Series Prediction under Distribution Shift using Differentiable Forgetting](https://arxiv.org/abs/2207.11486) formulates observation weighting as a balance between recency and effective information. Adapt only the fixed-decay idea, with no learned weighting metric or access to evaluation observations. Other remaining directions are time-of-day wraparound and alternative geometry representations.

## Experiment 31 — modest recency weighting

- Class: exploration of temporal training weights.
- Hypothesis: later-2005 operations may better represent 2006 than early-2005 operations. Apply fixed exponential month weights with a 12-month half-life, normalized to mean one so the regularization scale stays comparable. Retain every training row and all seasonal features; evaluate only through the harness.
- The risk is downweighting useful early-year seasonal examples. This experiment tests that tradeoff rather than assuming recency helps.
- Commit: `94196b7`. Result: **0.6866**, discard (equal AUC with extra weighting logic). Total 23.9s; training 15.0s. This fixed recency preference does not improve over equal weighting.

## Experiment 32 — circular and operational departure clock

- Class: exploration of time representation.
- Hypothesis: sine/cosine of departure minutes and an operational-day clock starting at 04:00 expose continuity across midnight while preserving raw HHMM time. This differs from the failed hour/minute features, which did not connect late-night and early-morning departures.
- Source: scikit-learn cyclic time feature engineering, read before experiment 8. No monotonic constraint is imposed because training summaries show a late-evening decline in risk.
- Commit: `039ad87`. Result: **0.6868**, keep (+0.0002). Total 25.5s; training 16.3s. Midnight continuity gives a small improvement after the extended plateau.

## Experiment 33 — landmark distance geography

- Class: follow-up to successful train-distance geography.
- Hypothesis: the three-dimensional embedding discards some graph-distance information. Add each endpoint's shortest-path distance to ATL, ORD, DFW, LAX, and JFK, preserving nonlinear regional structure without relying on learned coordinate-axis orientation.
- Fit all distances on the existing training-only distance graph. The landmark airport codes are fixed; no external airport tables, sample frequencies, or targets enter these features.
- Source: graph-distance embedding research cited in experiment 14.
- Commit: `681e7db`. Result: **0.6873**, keep (+0.0005). Total 27.6s; training 18.1s. Landmark distance information complements the truncated coordinate embedding; lookup/row-invariance checks passed.

## Experiment 34 — stronger leaf support with richer geography

- Class: follow-up to the landmark features.
- Hypothesis: increasing min_child_weight from 30 to 100 counteracts the additional numeric split opportunities from landmark distances. Keep depth 8 and all other settings fixed, preserving high-order interactions but requiring more support for each estimate.
- Commit: `a808052`. Result: **0.6871**, discard (-0.0002). Total 26.5s; training 17.1s. Some smaller supported groups remain useful.

## Experiment 35 — sparse leaf-weight regularization

- Class: follow-up to the best landmark forest.
- Hypothesis: reg_alpha=5 suppresses small residual leaf updates without forbidding all leaves below the larger support threshold that just lost accuracy. L1 shrinkage tests a different mechanism from increasing min_child_weight; keep the latter at 30 and retain L2=20.
- Source: XGBoost parameter reference describes L1 leaf-weight regularization.
- Commit: `32a9642`. Result: **0.6874**, keep (+0.0001; small evidence). Total 29.0s; training 19.6s. L1 slightly improves ranking while retaining smaller leaves.

## Experiment 36 — departure-distance clock interaction

- Class: exploration of a schedule/flight-length interaction.
- Hypothesis: scheduled departure minutes plus a fixed travel-time proxy, 30 + Distance/8, can expose useful oblique boundaries in departure-time/distance space. Add the resulting modulo-day clock and its sine/cosine representation. This is explicitly a rough proxy, not observed arrival time or a claim of accurate flight duration; time-zone effects remain for the airport/geography features to distinguish.
- Motivation: flight timing/duration feature families in the Berkeley study and circular representations in the scikit-learn time-feature example, both researched earlier.
- Commit: `ca7cffd`. Result: **0.6875**, keep (+0.0001; small evidence). Total 28.8s; training 18.8s. The explicit departure-distance clock interaction adds a marginal gain.

## Experiment 37 — blend deep and shallower forests

- Class: exploration of complementary ensemble complexity.
- Hypothesis: average the best depth-8 forest with a depth-6 forest using fixed 3:1 weights. Keep the best model dominant and let the shallower member damp some interaction variance. Unlike experiment 22, members deliberately differ in depth as well as random seed.
- Both models use identical prepared features and the same full training set. The secondary seed is 137; no additional evaluation or weight-fitting procedure is used. Expected combined training remains below one minute.
- Source: probability averaging research cited after experiment 20.
- Commit: `583572a`. Result: **0.6875**, discard (equal AUC, more complex and slower). Total 42.2s; training 32.0s. Different model depth did not improve the best forest through this fixed blend.

## Experiment 38 — longer pre-Christmas lead-up

- Class: follow-up to the successful holiday representation.
- Hypothesis: extend only the Christmas window to 14 days before and seven days after, testing a longer holiday lead-up. Preserve the existing one-week windows around Thanksgiving, New Year and July 4 so this is not a broad reintroduction of day-of-month effects.
- Commit: `0d30a13`. Result: **0.6878**, keep (+0.0003). Total 28.5s; training 18.6s. A broader pre-Christmas window adds useful calendar detail without expanding the other windows.

## Experiment 39 — remove latent route-direction features

- Class: ablation/simplification.
- Hypothesis: the three destination-minus-origin embedding coordinates may be redundant after landmark distances and the departure-distance clock proxy. Remove only these direction columns, retaining all six endpoint coordinates and ten landmark distances.
- Commit: `58c4452`. Result: **0.6877**, discard (-0.0001). Total 28.6s. Direction columns retain a marginal contribution despite the richer endpoint representation.

## Experiment 40 — finer numeric histogram resolution

- Class: exploration of numeric split precision.
- Hypothesis: max_bin=512 instead of the default 256 provides finer cuts for continuous departure-distance clocks and graph distances. Preserve the existing regularization to test numerical split resolution rather than tree complexity.
- Research: [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) explains global histogram sketching and the accuracy/computation tradeoff of a larger bin budget.
- Commit: `6151ce6`. Result: **0.6876**, discard (-0.0002). Total 28.9s; training 19.0s. Finer numeric split resolution does not improve transfer.

## Synthesis after 40 experiments

- Best: **0.6878** at `0d30a13`, +0.0135 over baseline.
- This block broke the plateau with circular departure time, landmark graph distances, a departure-distance arrival-clock proxy, light L1 regularization, and a longer pre-Christmas lead-up. Several increments are only 0.0001-0.0003 and should not be treated as individually conclusive; selection follows the prescribed rounded-AUC rule.
- Unhelpful: fixed recency weighting, larger leaf support, blending deep/shallow forests, removing route-direction columns, and finer histogram bins.
- Working theory: explicit timing geometry and meaningful calendar alignment supply small additional signal, while aggressive simplification or extra ensemble layers do not consistently help.
- Research refresh: [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) suggests examining histogram resolution. Also searched [gradient-based sampling support](https://xgboost.readthedocs.io/en/release_3.2.0/parameter.html): CPU support is documented from 3.2 onward, with sampling probabilities based on gradient/Hessian magnitude. It is a distinct remaining alternative to uniform sampling if time permits.

## Experiment 41 — coarser numeric histogram regularization

- Class: follow-up to the split-resolution result.
- Hypothesis: after 512 bins slightly hurt, test 128 bins as an intentional regularizer relative to the 256-bin best. Coarser cuts may pool near-identical geography and schedule values more robustly while leaving categorical handling unchanged.
- Commit: `b6e2c21`. Result: **0.6872**, discard (-0.0006). Total 27.4s; training 17.6s. Both finer and coarser histograms lose to the default 256 bins.

## Plateau research and experiment 42 — gradient-based sampling

- Class: exploration of the sampling algorithm.
- Research pause after three small discards: [Ibragimov and Gusev, Minimal Variance Sampling in Stochastic Gradient Boosting](https://arxiv.org/abs/1910.13204) studies importance sampling to reduce gradient-estimation variance. XGBoost's documented gradient/Hessian-based sampling is a related available mechanism, not assumed identical to the paper's algorithm.
- Hypothesis: change only sampling_method from uniform to gradient_based, retaining subsample=0.8. This tests the allocation of the same approximate sampling budget rather than simply discarding more data. Installed XGBoost 3.4.1 is newer than the documented introduction of CPU support in 3.2.
- Commit: `fcb456a`. Result: **0.6872**, discard (-0.0006). Total 32.6s; training 22.5s. CPU support worked, but gradient-based sampling did not improve ranking and was slower.

## Experiment 43 — smaller steps at matched boosting exposure

- Class: follow-up to the best regularized forest.
- Hypothesis: use 600 rounds at learning_rate=1/30 instead of 400 at 0.05. Both schedules have round-count times learning-rate equal to 20, distinguishing this from experiment 16, which doubled total boosting exposure. More gradual residual fitting may improve ranking with the completed feature set.
- Source: XGBoost tuning guide's smaller-step/more-round guidance, researched initially.
- Commit: `e41ac1e`. Result: **0.6875**, discard (-0.0003). Total 37.5s; training 27.4s. Smaller steps at matched total exposure did not improve the final feature set.

## Experiment 44 — fewer averaged trees per round

- Class: ablation/simplification of the best forest.
- Hypothesis: two trees per round instead of three may retain rounded AUC with a substantial training-time reduction. Keep 400 rounds and all other best settings fixed. The pre-experiment clock check had 2m16s remaining, sufficient for this short final test and wrap-up.
- Commit: `292bb6a`. Result: **0.6875**, discard (-0.0003). Total 22.5s; training 12.9s. The third tree per round retains useful averaging despite its computational cost.

## Final summary

- Completed **44 experiments plus the unchanged baseline**: 19 experimental keeps, 25 discards, and zero crashes/timeouts. The baseline is an additional kept result.
- Baseline Eval AUC: **0.6743** (`b15ec66`). Best Eval AUC: **0.6878** (`0d30a13`), an absolute gain of **0.0135**. Branch `oct6` is restored to this best kept commit.
- Best model: 400 boosting rounds, three trees per round, depth 8, learning rate 0.05, minimum child weight 30, L2 20, L1 5, row sampling 0.8, column sampling 0.85, and one-category categorical splits. Its recorded run took 28.5s (18.6s training/startup, 9.9s evaluation).
- Best representation has 39 features: original schedule/distance and selected categories; route and carrier-airport combinations; circular/operational departure time; a rough departure-distance clock interaction; Thanksgiving, Christmas, New Year and July 4 offsets; airport coordinates, route direction and landmark distances fitted exclusively from training route distances.
- What worked: controlling categorical flexibility, retaining meaningful interaction depth, training-only geographic lookups, semantic holiday alignment, stochastic forest averaging, and lightweight shrinkage. Faster categorical preparation reduced evaluation from roughly 31s at baseline to roughly 10s with the much richer final feature set.
- What did not improve the best model: target-risk encoding, arbitrary date or month expansions, global additive holiday constraints, recency weighting, extra ensemble wrappers, alternate histogram resolutions, gradient-based sampling, lower depth, or smaller steps at matched boosting exposure. Several tied results were discarded because they added complexity or cost.
- What to try next: rotate the inferred geographic coordinate system to test axis-aligned tree sensitivity; test whether a carefully selected landmark subset can replace some coordinate features; explore complementary geometry representations in a compact ensemble. Avoid treating the tiny late-stage AUC gains as individually conclusive.
- Final verification: every logged commit has a saved artifact; the source worktree is clean and only train.py differs from the starting commit; the required final save_and_evaluate call is intact. The best saved prepare passes batch/single-row equivalence, supplied-label independence, and unseen-airport handling checks; saved-model probabilities are finite, bounded, and sum to one. No additional evaluation metric or holdout access was used.
- The last run finished with 1m28s on the experiment clock, triggering the prescribed wrap-up threshold. Clock stop follows final logging and verification.
