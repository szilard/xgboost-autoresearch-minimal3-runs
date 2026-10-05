# Research log — oct5

Setup complete on 2026-10-05. The baseline run is still pending; no experiments have been run.

## Baseline — b15ec66

Ran the unmodified starter model as required. Eval AUC was 0.6743. This is the first kept commit and the reference for all subsequent experiments.

## Research before experiment 1

- XGBoost's tuning notes frame depth, child weight, split loss, row sampling, and column sampling as bias/variance controls; they also emphasize that preprocessing can matter as much as parameter tuning. [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)
- A flight-delay prediction study lists time of day, weekday, month, and season among schedule features, and says it applies trigonometric encodings to time-related features. The starter already includes the raw fields, so the first exploration is to add periodic numeric views alongside them. [Probabilistic Flight Delay Predictions Using Machine Learning](https://www.mdpi.com/2226-4310/8/6/152)

## Experiment 1 hypothesis

**Exploration — cyclic calendar/time features.** Add departure minutes since midnight plus sine/cosine phases for scheduled departure time and month, retaining existing inputs. Trees split raw HHMM and month categories as ordered or grouped values; explicit phases may represent the adjacency of late-night/early-morning departures and December/January more directly. The paper above motivates trig encodings, but performance on this dataset is unknown. Compare Eval AUC with baseline 0.6743.

**Result — fbcea73:** Eval AUC 0.6734 (discard; baseline 0.6743). The added periodic time views did not help this model on the 2006 evaluation split. The effect was small but below the keep threshold.

## Experiment 2 hypothesis

**Exploration — reduce tree depth.** Starting from the kept baseline, change only `max_depth` from 6 to 4. XGBoost's tuning guide describes depth as a direct complexity control; shallower trees may capture robust carrier/airport/time interactions while reducing fit to 2005-specific noise. [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)

**Result — eb629b2:** Eval AUC 0.6789 (keep; +0.0046 over baseline). Reducing depth improved performance and cut artifact size from 2.6 MB to 0.7 MB. The current best uses the starter features with `max_depth=4`.

## Experiment 3 hypothesis

**Follow-up — leaf regularization.** Retain the best `max_depth=4` and change only `min_child_weight` from its default 1 to 5. If smaller trees helped by reducing unsupported interactions, requiring more Hessian support before splitting may improve robustness further. XGBoost documents larger child weight as more conservative. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)

**Result — a25238b:** Eval AUC 0.6793 (keep; +0.0004 over previous best). Raising `min_child_weight` from 1 to 5 gave a small additional gain; retain both depth 4 and child weight 5.

## Experiment 4 hypothesis

**Follow-up — continue the child-weight sweep.** On the kept model, raise `min_child_weight` from 5 to 10, changing no other parameter. This checks whether the small gain at 5 reflects a continuing benefit from conservative leaf support or a local optimum near 5.

**Result — bcf3b81:** Eval AUC 0.6800 (keep; +0.0007). Increasing child weight from 5 to 10 improved AUC again, so test one stronger value before moving to another regularization control.

## Experiment 5 hypothesis

**Follow-up — extend child-weight sweep.** Raise `min_child_weight` from 10 to 20 on the current best. The sequential gains at 5 and 10 suggest larger minimum leaf support may be reducing year-specific small-leaf patterns; 20 tests whether that trend continues or becomes too restrictive.

**Result — db5d363:** Eval AUC 0.6783 (discard; best 0.6800). Raising child weight to 20 overshot; the current best remains 10.

## Experiment 6 hypothesis

**Exploration — row subsampling.** Starting from the kept depth-4 / child-weight-10 model, set only `subsample=0.8`. XGBoost notes row subsampling as a way to reduce overfitting. Sampling 80% of 2005 rows per tree may make the model less dependent on quirks in the sampled training year. [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)

**Result — 7c6289a:** Eval AUC 0.6779 (discard; best 0.6800). Row subsampling to 0.8 reduced AUC on this split.

## Experiment 7 hypothesis

**Exploration — column subsampling.** From the kept depth-4 / child-weight-10 model, set only `colsample_bytree=0.8`. This is distinct from row sampling: each tree will see a random subset of the eight starter features, which may reduce reliance on any one feature family, though the small feature count makes over-regularization a risk. XGBoost documents column subsampling as another regularization control. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)

**Result — 3c0623a:** Eval AUC 0.6798 (discard; best 0.6800). Column subsampling across the eight original features was slightly worse.

## Research before experiment 8

- Flight-delay work identifies airport and air-route context as useful predictors. A directional origin/destination pair can express a route-specific pattern that separate airport features do not expose as one field. [A Methodology for Predicting Aggregate Flight Departure Delays in Airports](https://www.mdpi.com/2071-1050/12/7/2749)
- XGBoost supports native categorical features and partitions category sets using their learned leaf scores. [XGBoost categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)
- Target means can be informative for categories, but fitting and transforming the same training rows leaks their labels. Cross-fitting encodes each training fold from the others; the scikit-learn example demonstrates the overfit caused by skipping it. I will first test route as a native category, leaving target encoding for a separate carefully cross-fitted experiment. [scikit-learn target encoder cross-fitting](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)
- A read-only summary of `train.csv` found 4,290 directed routes; median route count was 32 rows (10% of routes had at most 5 rows). This is enough to motivate a route category, while making rare-route overfit a risk.

## Experiment 8 hypothesis

**Exploration — add a directed route category.** Starting from the kept depth-4 / child-weight-10 model, add `Origin>Dest` as a single native categorical input, with levels fitted only from `train.csv`. The composite lets XGBoost learn directional route effects directly rather than requiring separate origin and destination splits to interact. Unseen routes map to missing; rare routes may be noisy, so the Eval AUC determines whether this survives.

**Result — 490fd48:** Eval AUC 0.6713 (discard; best 0.6800). The native route category was materially worse and raised row-by-row evaluation time to 47s. Route rarity appears to make this representation unhelpful in the current model.

## Experiment 9 hypothesis

**Exploration — cross-fitted carrier and airport target rates.** Add smoothed target means for `UniqueCarrier`, `Origin`, and `Dest` alongside their existing categorical inputs. These fields have enough records per level to summarize persistent risk; an airline delay study reports target encoding airline and airport features. Since using in-sample means can leak each row's label, fit five fold-specific lookup tables on train. Assign folds with a deterministic hash of that row's predictor fields, so `prepare` returns the same encoding whether it sees the row in the full training frame or by itself at scoring time. Each fold's rates exclude all training rows assigned to that fold; shrink small groups toward the train prior with strength 50. No raw counts become features. [Flight delay feature encodings](https://www.mdpi.com/2226-4310/8/6/152) · [scikit-learn cross-fitting guidance](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)

**Result — 553efd3:** Eval AUC 0.6781 (discard; best 0.6800). Cross-fitted smoothed carrier/origin/destination rates were valid row-wise features but did not improve ranking on 2006. Evaluation remained within limit at 43s.

## Experiment 10 hypothesis

**Follow-up — explicit time-of-day groups.** Starting from the best model, add departure hour as a categorical feature while retaining raw `CRSDepTime`. The earlier sine/cosine encoding did not help, but an hour category allows XGBoost to group specific hours directly and could capture sharp schedule-period effects with less interaction structure. Fit the hour levels on train. Related flight-delay work includes time of day among schedule predictors. [Probabilistic flight-delay prediction](https://www.mdpi.com/2226-4310/8/6/152)

**Result — 95b85d5:** Eval AUC 0.6789 (discard; best 0.6800). Explicit hour categories were better than cyclic time features on their own prior result, but did not beat the tuned baseline.

## Synthesis after 10 experiments

- **Best:** `bcf3b81`, Eval AUC 0.6800 (+0.0057 vs. baseline 0.6743), using starter features with `max_depth=4` and `min_child_weight=10`.
- **What helped:** reducing depth from 6 to 4 made the largest gain (+0.0046); increasing child weight to 5 and then 10 added small gains.
- **What did not help:** child weight 20 overshot; row and column subsampling reduced AUC. Cyclic date/time features, an explicit hour category, a native directed-route category, and cross-fitted carrier/airport rates all lost to the best. The route category also raised evaluation time to 47s.
- **Current theory:** this split benefits more from controlling tree complexity than from adding inputs or stochastic regularization. The original categorical and numeric fields already capture useful temporal, carrier, and airport signals; new encodings tested so far add noise or redundancy. This is based on Eval AUC only; holdout remains unseen.
- **Next direction:** research category split controls and split-gain regularization (`max_cat_threshold`, `gamma`) before continuing. Keep future changes isolated so an AUC gain can be attributed to a specific control.

## Research before experiment 11

- The installed XGBoost version is 3.4.1. Its categorical guide explains that native categories can be partitioned into sets at a split. The parameter reference describes `max_cat_threshold` as limiting the number of categories considered in partition-based splits to prevent overfitting. This specifically applies to the 283-level airport fields. [XGBoost categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) · [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)
- The same parameter guide says `gamma` is the minimum loss reduction required for a split and larger values are more conservative. It is a separate follow-up if categorical split control does not help. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)

## Experiment 11 hypothesis

**Exploration — constrain categorical split search.** On the current best, set only `max_cat_threshold=32`. Airports have 283 levels and the native route category was noisy; considering fewer category candidates per partition may remove brittle airport groupings while retaining stronger ones. XGBoost documents this as a categorical overfit control. The value 32 is a deliberate conservative step from the default-scale threshold; compare with best AUC 0.6800.

**Result — e49877e:** Eval AUC 0.6784 (discard; best 0.6800). Restricting categorical split candidates to 32 did not help.

## Experiment 12 hypothesis

**Exploration — minimum split gain.** Starting from the kept model, set only `gamma=1.0`. XGBoost requires a split to exceed this loss-reduction threshold; after gains from shallower trees and larger child weight, a modest split-gain threshold may prune marginal refinements without removing the robust coarse structure. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)

**Result — 13f15b3:** Eval AUC 0.6800 (discard; equal at four decimals to best, with no simplification or speed gain). Gamma 1.0 had no measurable effect at the harness precision.

## Experiment 13 hypothesis

**Follow-up — stronger split-gain threshold.** Raise `gamma` from 1 to 10 on the kept model. A threshold of 1 left AUC unchanged to four decimals; 10 should prune more low-gain splits and reveal whether split pruning helps beyond `min_child_weight=10`.

**Result — 2e39a08:** Eval AUC 0.6795 (discard; best 0.6800). Gamma 10 was more restrictive than the data favored.

## Experiment 14 hypothesis

**Exploration — L2 leaf-weight regularization.** From the kept model, change only `reg_lambda` from its default 1 to 5. Gamma 1 was ineffective and gamma 10 hurt; L2 instead shrinks leaf scores after splits are chosen, so moderate shrinkage may stabilize predictions without suppressing useful partitions. XGBoost documents larger L2 as more conservative. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)

**Result — 9baf5f8:** Eval AUC 0.6799 (discard; best 0.6800). Moderate L2 shrinkage was a near miss but did not meet the keep rule.

## Experiment 15 hypothesis

**Exploration — finer boosting steps.** Starting from the kept model, lower `learning_rate` from 0.1 to 0.03 and raise `n_estimators` from 100 to 300 as a paired boosting schedule. Smaller steps may rank borderline flights more smoothly; additional rounds compensate for the slower learning. XGBoost's tuning notes recommend increasing the number of rounds when reducing the step size. [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)

**Result — b2aef8c:** Eval AUC 0.6802 (keep; +0.0002 over previous best). The slower schedule produced a small improvement and remains well under the 60s training limit (1.9s).

## Experiment 16 hypothesis

**Follow-up — finer boosting schedule.** On the new best, lower `learning_rate` from 0.03 to 0.02 and raise `n_estimators` from 300 to 500. The initial finer-step run gained 0.0002; this tests whether that trend continues with smaller updates and enough rounds.

**Result — a584316:** Eval AUC 0.6797 (discard; best 0.6802). The finer 500-round schedule trained in 2.7s but scored lower.

## Experiment 17 hypothesis

**Follow-up — intermediate schedule and compactness.** Try `learning_rate=0.05` with `n_estimators=200`. This uses fewer trees than the best 300-at-0.03 schedule while keeping a similar total step-size budget; if AUC ties at four decimals, its smaller artifact and faster inference are useful wins.

**Result — 835ed1d:** Eval AUC 0.6798 (discard; best 0.6802). The 200-round model was smaller, but the AUC drop exceeded the equality allowance.

## Experiment 18 hypothesis

**Exploration — one-hot splits for low-cardinality categories.** On the best model, set only `max_cat_to_onehot=16`. With the installed XGBoost 3.4.1 default threshold of 4, Month (12 levels) and DayOfWeek (7) use partition splits; threshold 16 switches those fields to one-category-vs-rest splits. This may let the model express individual seasonal and weekday effects more directly. [XGBoost categorical features](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)

**Result — 1ed6e81:** Eval AUC 0.6799 (discard; best 0.6802). Switching both Month and DayOfWeek to one-hot splits did not help.

## Experiment 19 hypothesis

**Ablation — isolate weekday one-hot splitting.** Set `max_cat_to_onehot=8`. This keeps DayOfWeek (7 levels) on one-hot splits but leaves Month (12 levels) on category partitions. The prior threshold changed both; this ablation tests whether Month's individual one-hot effects caused the small AUC loss.

**Result — fb31ba4:** Eval AUC 0.6786 (discard; best 0.6802). One-hot splitting for DayOfWeek alone did not recover the performance lost at threshold 16.

## Experiment 20 hypothesis

**Follow-up — slightly deeper interactions.** On the current best (depth 4, child weight 10, 300 rounds at 0.03), increase only `max_depth` to 5. Depth 4 was a large win over the starter's depth 6 in the initial comparison; the stronger leaf constraint may now make depth 5's extra interaction level safe. Compare against 0.6802.

**Result — a4f6b63:** Eval AUC 0.6785 (discard; best 0.6802). Depth 5 with child weight 10 lost 0.0017, confirming the tuned model prefers depth 4.

## Synthesis after 20 experiments

- **Best:** `b2aef8c`, Eval AUC 0.6802 (+0.0059 vs. baseline 0.6743), with `max_depth=4`, `min_child_weight=10`, `learning_rate=0.03`, and 300 estimators.
- **What helped:** the depth-4 / child-weight-10 structure remains the strongest result. Lowering the learning rate to 0.03 with 300 rounds added 0.0002; moving to 500 rounds at 0.02 lost 0.0005. Depth 5 also lost 0.0017.
- **What did not help:** increasing child weight to 20, subsampling rows or columns, categorical split/one-hot threshold changes, gamma, L2, engineered time features, route, and cross-fitted airport/carrier rates did not beat the current best. Most candidates were close, but the keep rule is strict at four decimals.
- **Current theory:** shallow trees with moderate leaf support are the main source of gains; a slower but not excessively long boosting schedule provides a small additional improvement. Added features and extra categorical flexibility have not helped the 2005-to-2006 ranking task.
- **Next direction:** research leaf-wise tree growth (`lossguide`) as a meaningfully different structure; keep its leaf budget comparable to the depth-4 model and evaluate on the same harness metric.

## Research before experiment 21

- XGBoost supports `grow_policy="lossguide"` with `hist` or `approx`; it expands nodes with the highest loss change instead of nodes closest to the root. `max_leaves` bounds the number of leaves and is supported by `hist`. With `max_depth=0`, the leaf cap controls size while allowing an asymmetric tree. The installed 3.4.1 API supports these parameters. [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) · [XGBoost 3.4.1 Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)

## Experiment 21 hypothesis

**Exploration — loss-guided tree growth.** Replace depth-wise growth with `grow_policy="lossguide"`, `tree_method="hist"`, `max_depth=0`, and `max_leaves=16`, holding depth-4 model's other parameters fixed. A 16-leaf cap roughly matches a full depth-4 tree, but loss-guided growth can spend those leaves on the strongest interactions instead of distributing them level by level. The unconstrained path depth is a risk; `min_child_weight=10` remains in place.

**Result — 4a9d997:** Eval AUC 0.6789 (discard; best 0.6802). Loss-guided growth with 16 leaves underperformed depth-wise depth 4; spending leaves by immediate gain did not improve ranking.

## Experiment 22 hypothesis

**Exploration — L1 leaf-weight regularization.** On the best model, set only `reg_alpha=1.0` (default 0). L2 shrinkage did not help; L1 can instead push weak leaf weights exactly to zero, potentially removing small noisy effects while preserving the selected partitions. XGBoost documents larger alpha as more conservative. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)

**Result — 0b50c10:** Eval AUC 0.6805 (keep; +0.0003). L1 regularization improved the best score, which now combines depth 4, child weight 10, 300 rounds at 0.03, and alpha 1.

## Experiment 23 hypothesis

**Follow-up — stronger L1 sparsity.** Raise `reg_alpha` from 1 to 5 on the kept model. Since alpha 1 improved AUC, a stronger penalty may remove additional weak leaf updates; the risk is overshrinking useful effects.

**Result — e1420fc:** Eval AUC 0.6812 (keep; +0.0007). Raising alpha from 1 to 5 improved the score again and reduced artifact size from 2.1 MB to 1.8 MB.

## Experiment 24 hypothesis

**Follow-up — extend the L1 sweep.** Raise `reg_alpha` from 5 to 10 on the current best. Two consecutive gains suggest stronger leaf sparsity may still help, though the next step may begin to suppress useful signal.

**Result — ba8598f:** Eval AUC 0.6816 (keep; +0.0004). Increasing alpha from 5 to 10 continued the gain and reduced the artifact to 1.5 MB.

## Experiment 25 hypothesis

**Follow-up — higher L1 penalty.** Raise `reg_alpha` from 10 to 20. The 1, 5, and 10 sweep points improved monotonically; test whether a still stronger threshold continues to remove weak leaf updates or begins to overshrink.

**Result — 7c01b57:** Eval AUC 0.6802 (discard; best 0.6816). Alpha 20 overshot and erased the L1 gains.

## Experiment 26 hypothesis

**Follow-up — bracket the L1 optimum.** Set `reg_alpha=15`, midway between the best value 10 and the overshooting value 20. This can tell whether stronger shrinkage is still beneficial in the interval or whether 10 is the better operating point.

**Result — c81160e:** Eval AUC 0.6813 (discard; best 0.6816). Alpha 15 is worse than the best value 10, confirming the stronger penalty overshoots somewhere between 10 and 15.

## Experiment 27 hypothesis

**Follow-up — retune leaf support under L1.** On the alpha-10 model, lower `min_child_weight` from 10 to 5. L1 now suppresses weak leaf scores, so a smaller minimum child support may permit useful extra partitions while the L1 penalty keeps their effects conservative. This tests an interaction between the two regularizers.

**Result — 74ef2e4:** Eval AUC 0.6813 (discard; best 0.6816). Lower child weight did not complement alpha 10; the original child weight 10 remains best.

## Research before experiment 28

- FAA documentation describes delay propagation into and out of airports, connecting flight stages operationally. Carrier and origin are available schedule features here, so a carrier-at-origin interaction is plausible, though actual aircraft-chain data is unavailable to this model. [FAA delay propagation](https://www.aspm.gov/aspmhelp/index/Delay_Propagation.html)
- Read-only train-only counts show 1,551 carrier-origin pairs (median 43 rows) versus 4,290 directed routes (median 32). The pair may retain a station-specific airline signal with less sparsity than a full route category.

## Experiment 28 hypothesis

**Exploration — carrier-at-origin category.** Starting from best commit `ba8598f`, add `UniqueCarrier>Origin` as a native categorical feature with levels fitted on train only. This lets the model split carrier-specific airport operation patterns directly; unknown pairs map to missing. The earlier full route category hurt, so this smaller interaction is a targeted test of station-level effects.

**Result — 58343d1:** Eval AUC 0.6821 (keep; +0.0005 over prior best). The carrier-origin pair improved ranking; artifact size is 2.6 MB and evaluation remains within limit (41s).

## Experiment 29 hypothesis

**Follow-up — add carrier-at-destination context.** Keep the successful carrier-origin feature and add `UniqueCarrier>Dest` as another native category. FAA documentation describes delays propagating into and out of airports; a carrier-specific destination pattern may complement the origin feature by representing downstream station effects. Unknown pairs map to missing, with levels fitted on train only.

**Result — 4c6342f:** Eval AUC 0.6813 (discard; best 0.6821). Adding both carrier-origin and carrier-destination interactions was worse and raised evaluation time to 50s. The added destination feature may be redundant or noisy.

## Experiment 30 hypothesis

**Ablation — destination versus origin interaction.** Replace `CarrierOrigin` with `CarrierDest`, keeping one composite categorical feature. Since adding both together hurt, test whether the destination pair is useful alone or whether its value is redundant/noisy next to the origin pair. FAA describes propagation both into and out of airports, making this a directional comparison. [FAA delay propagation](https://www.aspm.gov/aspmhelp/index/Delay_Propagation.html)

**Result — c8eef16:** Eval AUC 0.6807 (discard; best 0.6821). Carrier-destination alone was substantially weaker than carrier-origin.

## Synthesis after 30 experiments

- **Best:** `58343d1`, Eval AUC 0.6821 (+0.0078 vs. baseline 0.6743). It uses depth 4, child weight 10, 300 rounds at learning rate 0.03, L1 alpha 10, and a train-fitted `CarrierOrigin` category.
- **What helped:** depth/child regularization and moderate L1 gave the largest gains; alpha 1, 5, then 10 improved monotonically, while 15 and 20 overshot. A carrier-at-origin feature added another 0.0005.
- **What did not help:** route, carrier-destination, or both carrier-airport interactions together underperformed the carrier-origin feature. The earlier cyclic/hour features, target rates, subsampling, gamma and categorical-threshold changes also failed to beat the then-current model.
- **Current theory:** station-specific carrier operations are a useful interaction, while full route and destination interactions are too sparse or redundant. L1 at 10 helps keep the added categorical signal from overfitting.
- **Next direction:** revisit categorical partition capacity specifically with `CarrierOrigin` present; test a larger `max_cat_threshold` than the default-scale setting to see whether this high-cardinality interaction needs more split candidates. Continue to compare against `58343d1`.

## Experiment 31 hypothesis

**Follow-up — expand category partition capacity.** On the current best, set only `max_cat_threshold=128`. `CarrierOrigin` has 1,551 levels, so a larger category cap may allow more useful station-specific groupings than the smaller cap tested earlier. L1 alpha 10 stays in place to control overfit. XGBoost documents this parameter as controlling categories considered for partition splits. [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)

**Result — eb4c5ab:** Eval AUC 0.6818 (discard; best 0.6821). Raising the category threshold to 128 did not improve the carrier-origin model.

## Experiment 32 hypothesis

**Follow-up — shallower carrier interaction model.** Reduce `max_depth` from 4 to 3 while holding alpha 10, child weight 10, and the successful carrier-origin feature fixed. Depth 5 lost in the earlier sweep; depth 3 tests whether the added interaction can generalize with still less tree capacity.

**Result — f278f1c:** Eval AUC 0.6807 (discard; best 0.6821). Depth 3 underfit relative to depth 4 after adding the carrier-origin interaction.

## Experiment 33 hypothesis

**Follow-up — retune L1 with the interaction present.** Increase `reg_alpha` from 10 to 15 while keeping `CarrierOrigin`. Alpha 15 lost before this category was added; the new high-cardinality input may benefit from stronger shrinkage. This checks the regularizer-feature interaction directly.

**Result — 6656238:** Eval AUC 0.6818 (discard; best 0.6821). Alpha 15 did not improve with CarrierOrigin present; alpha 10 remains best.

## Experiment 34 hypothesis

**Follow-up — add boosting rounds for the new feature.** Change the current `300 @ 0.03` schedule to `400 @ 0.025`, holding CarrierOrigin and all regularization fixed. More, smaller updates may refine the useful carrier-origin splits without reverting to the 500-round schedule that underperformed earlier.

**Result — 6774b19:** Eval AUC 0.6818 (discard; best 0.6821). More rounds at a smaller step did not improve the carrier-origin model.

## Experiment 35 hypothesis

**Follow-up — constrain carrier-origin partitioning.** Set `max_cat_threshold=32` on the current best. Threshold 128 was slightly worse; the 1,551-level carrier-origin field may benefit from a smaller candidate cap when paired with alpha 10. This tests stronger category-split regularization on the feature that improved AUC.

**Result — d72b8ff:** Eval AUC 0.6824 (keep; +0.0003). Restricting category partitions to 32 helped the carrier-origin model; artifact is 2.9 MB, with 40s evaluation.

## Experiment 36 hypothesis

**Follow-up — reduce overlapping regularization.** With `max_cat_threshold=32` now constraining carrier-category splits, lower `reg_alpha` from 10 to 5. This may retain useful category signal while keeping the split cap in place; it tests whether the two controls can be balanced more effectively.

**Result — 3197b95:** Eval AUC 0.6813 (discard; best 0.6824). Lowering alpha to 5 under the category cap did not help.

## Final summary

- **Best kept model:** commit `d72b8ff`, Eval AUC **0.6824**. Baseline `b15ec66` scored 0.6743, for a gain of 0.0081 on `eval.csv`.
- **Winning changes:** `max_depth=4`, `min_child_weight=10`, 300 estimators at learning rate 0.03, L1 `reg_alpha=10`, the train-fitted native `CarrierOrigin` category, and `max_cat_threshold=32`.
- **What helped:** reducing depth and raising child weight improved the starter; L1 regularization improved AUC through alpha 10; the carrier-origin interaction added signal; limiting categorical partition candidates to 32 gave the final gain.
- **What did not help:** cyclic/hour encodings, the full route category, target-rate encodings, carrier-destination interactions, row/column subsampling, loss-guided growth, gamma/L2, higher category caps, and the more extreme learning-rate/round schedules tested.
- **Next:** the human should score kept artifacts on the untouched holdout. Further experiments could test nearby `max_cat_threshold` and `reg_alpha` values with `CarrierOrigin`; no holdout data was accessed during this run.
