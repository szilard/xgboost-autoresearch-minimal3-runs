# Research log — oct6

## Baseline — 8d9c760

The unchanged starter model scored 0.6743 Eval AUC (31.5 seconds total; 0.6 seconds inside `model.fit`). Training has 200,000 rows, no missing values, and nine columns including the target. The feature columns are scheduled departure HHMM, distance, month, day of month, day of week, carrier, origin, and destination.

Initial reading: [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) recommends smaller trees and shrinkage to manage overfitting; the [parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) explains depth, learning rate, child weight and sampling. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains one-hot versus partitioned categorical splits. A [Berkeley airline-delay feature engineering study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) points to schedule, carrier, route, and time-of-day information; this dataset has only a subset of those fields.

## Experiment 1 — conservative boosting (exploration)

Hypothesis: the 100 depth-6 trees may fit 2005-specific patterns. Reducing depth to 4 and learning rate to 0.05, while increasing to 300 trees, may improve 2006 generalization. This follows the XGBoost tuning guidance above. Keep all features unchanged to isolate the model change.

Result: 0.6795 Eval AUC (32.4 seconds total), a +0.0052 improvement. Keep. This supports trying still shallower trees; the contribution of each changed setting remains unresolved.

## Experiment 2 — depth 3 (follow-up)

Hypothesis: if the gain came from reducing tree complexity, depth 3 may generalize even better across years. Hold 300 trees and learning rate 0.05 fixed so only depth changes.

Result: 0.6812 (+0.0017), keep. Shallower trees have helped twice, so test one more step before adding features.

## Experiment 3 — depth 2 (follow-up)

Hypothesis: broad calendar, airport and schedule effects may dominate. Depth-2 trees are more regularized and may further reduce 2005-specific interactions. Keep 300 trees and learning rate 0.05 fixed.

Result: 0.6760 (-0.0052), discard. Depth 2 loses important interactions; depth 3 remains the best.

## Experiment 4 — 500 depth-3 trees (follow-up)

Hypothesis: depth 3 is a good complexity level but 300 small steps may still underfit. Raise the number of trees to 500 while keeping depth and learning rate fixed. More boosting may model interactions without making each tree more complex.

Result: 0.6810 (-0.0002), discard. Extra rounds were slightly worse, so test fewer rounds before changing regularization.

## Experiment 5 — 200 depth-3 trees (ablation/simplification)

Hypothesis: if 500 rounds are worse than 300, the optimum may be below 300. Try 200 at the same depth and learning rate; if AUC ties, the smaller and faster model is preferable.

Result: 0.6807 (-0.0005), discard. Among 200, 300 and 500 rounds, 300 is best at depth 3 and learning rate 0.05.

## Experiment 6 — larger child weight (exploration)

Hypothesis: rare airport/carrier categories can create leaves that encode 2005-specific noise. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says a larger `min_child_weight` makes child formation more conservative. Try 10 instead of 1 with the kept 300-tree model; all other settings stay fixed.

Result: 0.6810 (-0.0002), discard. Three consecutive small declines (500 trees, 200 trees, child weight 10) form a plateau, so pause for targeted research before another change.

Plateau research: the [UC Berkeley airline-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports operational patterns by scheduled departure hour and uses categorical hour blocks. The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes grouped category splits. This dataset's raw HHMM field is ordered but makes the same hour span many distinct values. An explicit hour block could make recurring daily timing easier to share across flights.

## Experiment 7 — scheduled hour block (exploration)

Hypothesis: a categorical departure hour alongside HHMM helps the shallow model learn recurring within-day congestion patterns, especially when interacting with origin and carrier. Compute it from each row's `CRSDepTime` only, so training and row-by-row evaluation agree.

Result: 0.6796 (-0.0016), discard. Hour block is redundant with HHMM or distracts the shallow model. Keep the original time representation.

Research on categorical combinations: [CatBoost's original paper](https://arxiv.org/abs/1706.09516) describes useful categorical feature combinations while warning that target statistics can leak labels. This trial will use a simple raw feature cross, with no target encoding. Training contains 1,551 distinct carrier-origin pairs, far fewer than 4,290 routes, so the carrier-origin cross seems the more stable first test. The [Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) discusses airport-specific and carrier-specific operating patterns.

## Experiment 8 — carrier-origin category (exploration)

Hypothesis: delay propensity for an airline at a particular origin can differ from the airline and airport effects separately. A precomputed category for that pair may let depth-3 trees use this interaction without spending two splits. Unknown pairs map to missing.

Result: 0.6741 (-0.0071), discard. The high-cardinality cross overfits or distracts XGBoost, and row-by-row eval slowed to 37.5 seconds. Pandas also warns about unseen pairs; reverting avoids that warning.

## Experiment 9 — one-hot splits for small categories (exploration)

Hypothesis: [XGBoost's categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) says `max_cat_to_onehot` selects one-hot versus partitioned splits. At the default threshold, all six categorical features use partitioning. One-hot splits may be more stable for month (12), weekday (7), and carrier (20) across years, while airport codes (283) stay partitioned. Set threshold 24, with no feature changes.

Result: 0.6782 (-0.0030), discard. The default partitioned splitting is substantially better for these small categories.

## Experiment 10 — restrict categorical partition size (follow-up)

Hypothesis: the one-hot result favors partitioning, but the airport features have 283 levels and could form overly detailed partitions. [XGBoost's categorical parameters](https://xgboost.readthedocs.io/en/latest/parameter.html) describe `max_cat_threshold` as a limit on categories considered per split to prevent overfitting. Reduce it from 64 to 16 while keeping all other settings fixed.

Result: 0.6737 (-0.0075), discard. The default category threshold is important; smaller partitions discard useful category structure.

## Synthesis after 10 experiments

Best: 0.6812 at `6509d5a`, +0.0069 over baseline. Shallower depth improved twice, with depth 3 better than 2 or 4 at 300 rounds and learning rate 0.05. Both 200 and 500 rounds declined slightly; increased child weight also declined slightly. A new departure-hour category and a carrier-origin cross harmed generalization, as did one-hot splitting for small categories and a lower category partition threshold. Current theory: the existing schedule and category features carry signal, but the model needs modest interaction depth and the default partitioning behavior. Next direction: try encoding calendar features in their natural order and other carefully chosen schedule features; avoid high-cardinality crosses.

Next-cycle research: [Stanford's Airline Departure Delay Prediction study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) used day of year and holiday proximity alongside schedule and airport features; its reported high variance is consistent with our poor high-cardinality cross. It also used actual departure time, which is unavailable and would leak for this task, so we ignore that part. [scikit-learn's time feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows that ordinal time can give trees usable ordering and that trees capture nonlinear patterns; this suggests a compact calendar axis rather than more categorical levels.

## Experiment 11 — day of year (exploration)

Hypothesis: the combined calendar position offers a seasonal split across month boundaries that depth-3 trees struggle to express using separate categorical month and day fields. Add a numeric non-leap day-of-year feature, computed independently for each row; keep the original calendar fields.

Result: 0.6840 (+0.0028), keep. The continuous calendar position carries new predictive information. Row-by-row eval took 34.3 seconds, still safely within limit.

## Experiment 12 — remove day-of-month category (ablation/simplification)

Hypothesis: numeric day of year may capture the useful part of day-of-month, while the standalone day number adds 2005-specific noise. Remove the `DayofMonth` model feature but still use it to derive day of year. A tie would justify the simpler representation.

Result: 0.6844 (+0.0004), keep. Day-of-month was redundant or harmful once day of year was present; eval time also returned near the starter level.

## Experiment 13 — remove month category (ablation/simplification)

Hypothesis: day of year also determines month, and direct month partitions may add abrupt, year-specific boundaries. Remove Month from model features while retaining it only for day-of-year derivation. A tie or gain would simplify the calendar representation.

Result: 0.6850 (+0.0006), keep. The single numeric calendar axis works better than separate month and day categories, and eval time fell to 26.6 seconds.

## Experiment 14 — depth 4 with day-of-year representation (follow-up)

Hypothesis: the calendar representation changed substantially since the earlier depth comparison. Day of year may free tree splits that were previously needed to combine month and day, allowing depth 4 to learn useful airport/time interactions. Test depth 4 with all else fixed at the new best.

Result: 0.6838 (-0.0012), discard. Depth 3 remains better even with the new calendar representation.

## Experiment 15 — ordinal weekday (follow-up)

Hypothesis: replacing the seven-level weekday category with its natural 1–7 order may smooth weekday versus weekend effects and reduce arbitrary partitioning across 2005 and 2006. This follows [scikit-learn's example on ordinal time features for trees](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). Keep day of year and all other features fixed.

Result: 0.6836 (-0.0014), discard. The categorical weekday split remains useful; the date-axis gain was specific to month/day combined.

Introspection of the kept artifact: XGBoost gain importance is dominated by `CRSDepTime` (803 versus 145 for day of year, 158 for carrier, 121 for origin, 94 for destination, 133 for weekday, 34 for distance). This motivates schedule-position features. The [Berkeley airline-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes scheduled rotation and departure timing. I infer that time relative to a route's typical departure could proxy schedule position, though it is much weaker than actual aircraft rotation data, which this dataset lacks. The [Stanford study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) also discusses repeated routes as an historical reference.

## Experiment 16 — departure time versus route median (exploration)

Hypothesis: the same route can have early and late departures with different delay propagation risk. A numeric difference between each flight's scheduled minutes after midnight and the training-set median for its origin-destination route may expose this pattern to shallow trees. The median is fitted once on `train.csv`, outside `prepare`; each row only looks it up.

Result: 0.6846 (-0.0004), discard. The route-relative schedule feature adds little beyond raw departure time and the existing airport fields. It also increased row scoring to 31.6 seconds.

## Experiment 17 — 80% row subsampling (exploration)

Hypothesis: stochastic row sampling per boosting round may reduce sensitivity to idiosyncratic 2005 flights without weakening splits as much as a larger child weight. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says subsampling can prevent overfitting. Try `subsample=0.8` on the kept day-of-year model.

Result: 0.6851 (+0.0001), keep. The gain is small at four-decimal precision but clears the keep rule.

## Experiment 18 — 60% row subsampling (follow-up)

Hypothesis: if 80% sampling helps by reducing variance, 60% may help more. Hold all other settings fixed to isolate the effect of stronger stochastic sampling.

Result: 0.6841 (-0.0010), discard. Moderate 80% subsampling appears preferable to aggressive 60% sampling.

## Experiment 19 — sample features by tree (exploration)

Hypothesis: scheduled departure time dominates split gain, perhaps crowding out calendar, carrier and airport effects. With seven features, `colsample_bytree=0.8` forces some trees to explore other predictors, potentially improving robustness. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) describes this sampling as another overfitting control. Keep 80% row sampling.

Result: 0.6852 (+0.0001), keep. Modest feature sampling helps at printed precision.

## Experiment 20 — stronger L2 regularization (exploration)

Hypothesis: with stochastic sampling, leaf estimates from rare airport subsets may still be unstable. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says larger `reg_lambda` makes leaf weights more conservative. Increase from 1 to 5; keep feature set and sampling fixed.

Result: 0.6854 (+0.0002), keep. Stronger L2 regularization helps slightly.

## Synthesis after 20 experiments

Best: 0.6854 at `6649883`, +0.0111 over baseline. The largest gain in this block was the numeric day-of-year feature, especially after removing both month and day-of-month categorical inputs. With this feature set, depth 3 remains better than depth 4; weekday should remain categorical. Route-relative scheduled time did not help. Moderate 80% row sampling, 80% feature sampling and stronger L2 leaf regularization each improved printed AUC by a small amount. Next: research other ways to capture calendar disruptions and tune regularization without high-cardinality categorical crosses.

Next-cycle research: the [Bureau of Transportation Statistics holiday-delay page](https://www.transtats.bts.gov/holidayDelay.asp?pn=1) defines travel seasons around Presidents' Day, Memorial Day, Independence Day, Labor Day, Thanksgiving and the winter holidays; their windows shift slightly between 2005 and 2006. [Stanford's flight-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) included holiday proximity as a predictor. We can approximate common day-of-year windows that cover both years using only the scheduled date in the row, with no external file read at training or evaluation.

## Experiment 21 — holiday travel window (exploration)

Hypothesis: a seven-level feature (outside a major holiday period, or one of six travel windows) may let a depth-3 tree share holiday-period behavior across separated dates. The date windows are fixed public calendar ranges; they use each row's day-of-year only. Keep the rest of the best model unchanged.

Result: 0.6867 (+0.0013), keep. Explicit holiday-season identity helps beyond day of year. Evaluation took 31.8 seconds, well within limit.

## Experiment 22 — binary holiday-window flag (ablation/simplification)

Hypothesis: the gain may come from distinguishing holiday periods as a group rather than distinguishing six holidays. Replace the seven-level category with one binary flag. If AUC ties or improves, use the simpler representation.

Result: 0.6858 (-0.0009), discard. Different holiday periods carry distinct signals; preserve the seven-level feature.

Introspection of the kept artifact: HolidayWindow appears in 68 splits with gain importance 151, even higher than day of year (121). The broad windows are likely useful, but may include ordinary days whose behavior dilutes the signal.

## Experiment 23 — narrower holiday windows (follow-up)

Hypothesis: the [BTS holiday travel seasons](https://www.transtats.bts.gov/holidayDelay.asp?pn=1) cover long stretches, including days distant from the holiday. Narrowing each category to the immediate travel days may sharpen its effect and reduce noise, while retaining separate holiday identities. Hold all other model settings fixed.

Result: 0.6861 (-0.0006), discard. Broad holiday travel periods generalize better than immediate days alone.

## Experiment 24 — larger L2 penalty (follow-up)

Hypothesis: moving `reg_lambda` from 1 to 5 improved AUC, so a stronger value of 20 might better shrink rare-category leaf estimates. Test it with the kept holiday-window feature and all other settings fixed.

Result: 0.6870 (+0.0003), keep. The benefit of a larger L2 penalty continued.

## Experiment 25 — L2 penalty 50 (follow-up)

Hypothesis: the rising AUC from L2 values 1 to 5 to 20 suggests the optimum may be higher. Test 50 with no other change, while watching for underfitting.

Result: 0.6879 (+0.0009), keep. Strong leaf shrinkage is particularly useful with the holiday feature and categorical airport splits.

## Experiment 26 — L2 penalty 100 (follow-up)

Hypothesis: AUC improved monotonically through L2=50. Doubling to 100 tests whether the optimum is still further toward conservative leaves, or whether stronger shrinkage begins to underfit.

Result: 0.6879 (tie), discard under the keep rule because the code is not simpler or faster. L2=50 remains best.

## Experiment 27 — 500 trees with strong L2 (follow-up)

Hypothesis: the much larger L2 penalty reduces each tree's contribution, so the previous 300-round optimum (found near default L2) may now underfit. Try 500 rounds at the kept `reg_lambda=50`, learning rate 0.05 and holiday features.

Result: 0.6880 (+0.0001), keep. Additional rounds narrowly help under strong L2.

## Experiment 28 — 800 trees with strong L2 (follow-up)

Hypothesis: the upward change from 300 to 500 rounds under L2=50 suggests further boosting may help. Try 800 as a wider step to locate the point where extra rounds stop helping.

Result: 0.6874 (-0.0006), discard. At learning rate 0.05, extra rounds beyond 500 overfit.

## Experiment 29 — finer learning rate at similar total boosting (exploration)

Hypothesis: the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends reducing `eta` with more rounds for conservative boosting. Try 800 trees at 0.03 (roughly 24 total learning-rate units) versus the kept 500 at 0.05 (25 units). This tests finer steps at similar overall boosting strength, distinct from 800 trees at 0.05.

Result: 0.6878 (-0.0002), discard. Finer boosting steps did not outperform 500 at 0.05.

## Experiment 30 — minimum split gain (exploration)

Hypothesis: with many categories and 500 trees, some late splits may chase small 2005-specific gains. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says `gamma` requires a minimum loss reduction for a split. Try `gamma=5` at the kept settings to prune weak splits without reducing all leaf weights.

Result: 0.6879 (-0.0001), discard. L2 shrinkage helped more than a split-gain threshold.

## Synthesis after 30 experiments

Best: 0.6880 at `46d159f`, +0.0137 over baseline. In the third block, a separate categorical identity for six broad holiday travel windows was the largest gain (+0.0013). A binary holiday flag and narrower windows were worse. L2 regularization improved at 20 and 50, then tied at 100; 500 trees slightly beat 300 with L2=50, while 800 trees overfit. Smaller learning rate with more trees and gamma=5 did not help. Current theory: calendar disruptions and schedule timing matter, while airport/category details need substantial shrinkage. Next: test underused schedule-time details and ablate low-value predictors.

Next-cycle research: a [pre-tactical flight-delay study](https://link.springer.com/article/10.1007/s13272-026-00941-7) uses both hour and minute of scheduled departure, available well before flight time. [scikit-learn's time feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses periodic components and how shallow representations can miss recurring patterns. In our training sample, scheduled minute `00` has a lower delay share than `55`, though this is confounded by carrier and route. A minute-of-hour feature would let the model share that pattern across all hours; raw HHMM alone requires many separate splits.

## Experiment 31 — scheduled minute within hour (exploration)

Hypothesis: scheduled departure at certain minute slots may proxy airline scheduling or airport flight waves. Add `CRSDepTime % 100` as a numeric feature alongside raw HHMM. This is computed from each row alone and does not use outcomes or external data.

Result: 0.6872 (-0.0008), discard. Fine schedule minute does not add useful information beyond raw HHMM, and it slowed eval slightly.

## Experiment 32 — remove distance (ablation/simplification)

Hypothesis: distance has much lower split gain than scheduled time, calendar, carrier and airport features. Its route-specific values may add noise already implicit in origin and destination. Remove it and see whether AUC holds or improves; the feature set and row preparation become smaller.

Result: 0.6873 (-0.0007), discard. Even with low aggregate gain, distance adds information that origin/destination splits do not fully capture.

## Experiment 33 — remove destination (ablation/simplification)

Hypothesis: destination airport may mostly proxy route-specific noise after origin, distance and schedule are known. Its gain importance is lower than origin's. Remove destination to test whether its 283-category splits contribute to 2006 generalization.

Result: 0.6805 (-0.0075), discard. Destination is essential despite moderate average gain.

## Experiment 34 — 512 histogram bins (exploration)

Hypothesis: the current [XGBoost parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says a larger `max_bin` improves split resolution at extra training cost. With 365 day-of-year values and 1,162 scheduled HHMM values, the default 256 bins may merge useful thresholds. Try 512 while keeping the model otherwise identical.

Result: 0.6879 (-0.0001), discard. Finer resolution did not improve AUC, suggesting the default bins are adequate or act as useful smoothing.

## Experiment 35 — 128 histogram bins (follow-up)

Hypothesis: since 512 bins were slightly worse, coarser 128-bin thresholds may smooth noisy 2005-specific calendar and schedule details. This tests the opposite side of the default 256-bin setting and may improve year-to-year generalization.

Result: 0.6877 (-0.0003), discard. The default 256-bin resolution is better than either 128 or 512 on the current model.

## Experiment 36 — loss-guided growth, eight leaves (exploration)

Hypothesis: [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says loss-guided tree growth splits whichever node has the highest loss change. The current depth-3 model can have up to eight leaves, but allocates depth level by level. An eight-leaf loss-guided tree can use unbalanced depth to capture strong patterns without adding total leaves. Test `grow_policy='lossguide'`, `max_leaves=8`, `max_depth=0`.

Result: 0.6877 (-0.0003), discard. The depthwise shape remains better. Three consecutive small declines from max-bin and grow-policy changes form a plateau, so research a new direction before continuing.

Plateau research: [XGBoost's DART documentation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes dropping previously fitted trees to reduce overfitting; it notes that training can be slower because the prediction buffer cannot be reused. This is distinct from the row/feature sampling and L2 shrinkage already tried. The [original DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) motivates dropout of early dominant trees. The timing limit may be a risk, so choose modest dropout and skip half the dropout rounds.

## Experiment 37 — DART tree dropout (exploration)

Hypothesis: early schedule-time trees may dominate the ensemble. Modest tree dropout may make later trees learn complementary airport/calendar effects and improve 2006 generalization. Try `booster='dart'`, `rate_drop=0.05`, `skip_drop=0.5` at the kept feature and parameter settings. This is a materially different regularization mechanism.

Result: training hit the 60-second harness limit before evaluation, logged as crash and discarded. XGBoost warns that `booster=dart` is deprecated in favor of dropout parameters on the tree booster. Try fewer rounds once; if still too slow or inaccurate, leave dropout behind.

## Experiment 38 — 300 dropout trees (follow-up)

Hypothesis: reducing from 500 to 300 trees should bring DART's training cost below the limit, while retaining enough depth-3 trees to test whether dropout changes generalization. Keep all other settings fixed.

Result: 0.6865 (-0.0015), discard. Training took 27.4 seconds and total run about 60 seconds, much slower than the kept model. Dropout did not help enough to justify further trials.

## Experiment 39 — cyclic season features (exploration)

Hypothesis: numeric day of year has a discontinuity between December 31 and January 1. [scikit-learn's time feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains that sine/cosine features represent periodic adjacency. Add both calendar sine and cosine alongside day of year and holiday window, so shallow trees can group winter conditions across the year boundary.

Result: 0.6867 (-0.0013), discard. The cyclic features were redundant or distracting given day of year plus winter holiday window, and row scoring slowed to 35.2 seconds.

## Experiment 40 — L1 leaf regularization (exploration)

Hypothesis: [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) describes `reg_alpha` as an L1 penalty that can set small leaf outputs to zero. With many weak airport/calendar leaves, L1=10 might prune residual noise beyond the L2=50 shrinkage already in place. Test it without changing the features or tree count.

Result: 0.6889 (+0.0009), keep. L1 sparsity complements the high L2 penalty.

## Synthesis after 40 experiments

Best: 0.6889 at `9ea1df0`, +0.0146 over baseline. Removing distance or destination hurt, so both stay despite low or moderate gain importance. More or fewer histogram bins and loss-guided trees all declined slightly. DART was too slow at 500 trees and underperformed at 300. Cyclic calendar coordinates added no value over day of year plus holiday periods. The only gain in this block was adding L1=10, suggesting residual weak splits remain. Next: tune L1 strength and look at other category regularization options.

Next-cycle research: the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) distinguishes L1 (`reg_alpha`) sparsity from L2 shrinkage. The [tree methods guide](https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html) also says `approx` uses Hessian-weighted sketches per tree and can sometimes improve accuracy for objectives with nonconstant Hessians, whereas the current `hist` method is faster. These are two concrete directions to test with the same features.

## Experiment 41 — L1 penalty 30 (follow-up)

Hypothesis: the +0.0009 gain at L1=10 suggests further pruning of weak leaf outputs may help. Increase `reg_alpha` to 30 at the kept settings to test for a continued trend versus underfitting.

Result: 0.6864 (-0.0025), discard. L1=30 is too strong and suppresses useful leaves.

## Experiment 42 — L1 penalty 5 (follow-up)

Hypothesis: L1=10 helped, but 30 overpruned. A smaller value of 5 may preserve weak but useful airport/calendar signals and outperform 10. All other settings remain fixed.

Result: 0.6888 (-0.0001), discard. The L1 optimum appears close to 10 among values 0, 5, 10 and 30.

## Experiment 43 — Hessian-weighted approximate splits (exploration)

Hypothesis: the [XGBoost tree methods guide](https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html) says `approx` recomputes Hessian-weighted sketches for each tree and sometimes improves accuracy for objectives with nonconstant Hessians. Binary logistic loss has a nonconstant Hessian. Try `tree_method='approx'` with the kept features and parameters, accepting slower training if it remains under the 60-second limit.

Result: 0.6888 (-0.0001), discard. Training increased from about 2 to 10 seconds with no AUC gain.

## Experiment 44 — categorical partition limit 128 (exploration)

Hypothesis: the [XGBoost categorical parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says `max_cat_threshold` limits categories considered per partitioned split. Reducing it to 16 was harmful on the earlier model. With stronger L1/L2 penalties now limiting overfit, allowing 128 categories (versus default 64) may capture more airport-level structure.

Result: 0.6887 (-0.0002), discard. The default threshold of 64 remains preferable.

## Experiment 45 — stronger feature sampling (follow-up)

Hypothesis: feature sampling at 0.8 helped earlier by making some trees use less dominant predictors. Now that holiday and L1/L2 features are in place, 0.6 may further diversify trees and reduce year-specific splits. This is a wider step than fine-tuning 0.8 to 0.9; keep row sampling at 0.8.

Result: 0.6892 (+0.0003), keep. More feature diversity helps the heavily regularized model.

## Experiment 46 — 40% feature sampling (follow-up)

Hypothesis: the rise from 0.8 to 0.6 suggests further diversity may help, but with only eight features 0.4 leaves just a few choices per tree. Test it to identify whether the gain continues or the model loses essential interactions.

Result: 0.6889 (-0.0003), discard. 0.6 is better; sampling only a few features per tree loses useful interactions.

## Experiment 47 — 90% row sampling with 60% columns (follow-up)

Hypothesis: with more feature sampling, the model may need slightly more rows per tree for stable estimates of rare airport categories. Increase row sampling from 0.8 to 0.9 while keeping the 0.6 feature rate fixed.

Result: 0.6881 (-0.0011), discard. More rows per tree likely reduce the useful stochastic regularization.

## Experiment 48 — 70% row sampling (follow-up)

Hypothesis: with L1/L2 shrinkage and 60% column sampling, 70% row sampling may improve robustness further. The earlier 60% row trial was on a different, much less regularized model. Test 0.7 with current best settings.

Result: 0.6893 (+0.0001), keep. Slightly more row stochasticity helps with the current regularized model.

## Experiment 49 — 60% row sampling with current model (follow-up)

Hypothesis: the current model improved from 90% to 80% to 70% row sampling. Test 60% to see whether the trend continues; this differs materially from the earlier 60% trial because holiday, L1/L2 and feature sampling are now in place.

Result: 0.6886 (-0.0007), discard. The 70% setting is best among 60–90% with the present feature set.

## Experiment 50 — depth 4 under strong regularization (follow-up)

Hypothesis: the earlier depth-4 test was done before adding holiday windows, L1/L2 penalties, and row/feature sampling. These changes may let a deeper tree use airport-calendar-schedule interactions without overfitting. Retest depth 4 with all current best settings fixed.

Result: 0.6888 (-0.0005), discard. Depth 3 is still the better complexity level.

## Synthesis after 50 experiments

Best: 0.6893 at `cd0df4b`, +0.0150 over baseline. L1=10 was useful; 5 was marginally worse and 30 strongly worse. `approx` training was slower and less accurate than `hist`, and a larger categorical partition limit was worse. Reducing column sampling from 0.8 to 0.6 helped, but 0.4 hurt. With the stronger regularization, 70% row sampling narrowly beat 80%, while 60% and 90% were worse. Depth 4 still overfits. Current theory: a depth-3 model with diverse trees and moderate row sampling extracts the available schedule/airport/calendar signal without overfitting. Remaining trials should focus on one small but meaningful change at a time.

Final-block research: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/latest/parameter.html) distinguishes `colsample_bytree` from `colsample_bynode`: the former chooses a feature set once per tree, the latter samples again for each split, and their fractions multiply. [XGBoost's random forest guide](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/rf.html) uses per-node column sampling to diversify splits. This suggests testing a modest node-level reduction while preserving the six-tenths set chosen per tree.

## Experiment 51 — per-node feature sampling (exploration)

Hypothesis: 0.4 feature sampling per tree was too restrictive, but 0.8 per node on top of 0.6 per tree may provide similar diversity without excluding the same features for the whole tree. Test `colsample_bynode=0.8` with all other settings fixed.

Result: 0.6884 (-0.0009), discard. Additional node-level sampling removes useful split candidates.

## Experiment 52 — lower child-weight threshold (exploration)

Hypothesis: L1=10 and L2=50 strongly shrink leaf weights, potentially allowing useful small airport groups that default `min_child_weight=1` prevents. Try 0.1 to permit these splits; [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) defines this threshold on child Hessian mass.

Result: 0.6893 (tie), discard because the extra setting does not simplify or speed up the model.

## Experiment 53 — moderate L2 with L1 and sampling (follow-up)

Hypothesis: L2=50 was selected before L1=10 and stronger feature/row sampling. Those later additions also regularize the model, so lowering L2 to 30 may restore useful leaf signal while retaining overfit control. Test this single parameter change.

Result: 0.6891 (-0.0002), discard. The higher L2 value is still preferable.

## Experiment 54 — L2 penalty 70 (follow-up)

Hypothesis: lowering L2 from 50 to 30 was slightly worse. Test 70 to bracket the current value under the final L1/sampling settings; if it does not improve printed AUC, return to 50.

Result: 0.6891 (-0.0002), discard. L2=50 remains best among 30, 50 and 70 under the final settings.

## Final summary

Best Eval AUC: **0.6893** at commit `cd0df4b`, versus baseline 0.6743 at `8d9c760` (+0.0150). The best model uses 500 depth-3 trees, learning rate 0.05, 70% row sampling, 60% feature sampling, L1=10 and L2=50. It retains scheduled departure time, distance, weekday, carrier, origin and destination; derives numeric day of year and a seven-level major holiday travel window from the scheduled date.

What worked: shallower trees versus the starter; a numeric day-of-year feature replacing month/day categories; broad, separate holiday-window categories; moderate row/feature sampling; stronger L1 and L2 penalties; and 500 trees once regularization was strong. What did not: deeper or extremely shallow trees, additional minute/hour and route/airport-cross features, alternative categorical split limits, DART, finer or coarser histograms, approximate/loss-guided tree building, cyclic season features, and removing distance or destination. Several late parameter changes moved AUC by only 0.0001–0.0003, so the precise optimum may be sensitive to the eval sample.

Next ideas: investigate generalizable airport geography or timezone metadata if it can be embedded without new runtime data reads; test a carefully designed calendar feature for moving holidays such as Easter; and compare holdout AUC of the kept artifacts after the human runs the holdout check. No holdout data or human-only tools were used during this run.
