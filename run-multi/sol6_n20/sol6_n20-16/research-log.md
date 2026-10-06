# Run oct6

Baseline: commit `8d9c760`, Eval AUC `0.6743`, 31.7 seconds. The starter uses 100 depth-6 trees, learning rate 0.1, and native categorical features. No changes to `train.py` yet.

## Experiment 1 — exploration: shallower, longer boosting

Hypothesis: 100 depth-6 trees may fit narrow category/time interactions in one year's sample. Use depth 4 with 400 trees and a 0.05 learning rate to build smoother effects in more steps. The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe depth as a complexity control and reducing the step size with more rounds as an overfitting control. Compare the row-scored 2006 AUC to baseline.

Result: `6adffa4` scored `0.6789` (+0.0046); keep.

## Experiment 2 — follow-up: route category

Hypothesis: the pair of airports carries route-specific effects that depth-4 trees may only capture through several splits. Add a categorical route fitted from the training set. The [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies route as a flight characteristic; [XGBoost's categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains grouped category splits. There are 4,290 training routes, so sparsity is a risk.

Result: `2a1c0b0` scored `0.6680` (−0.0109); discard. Sparse route categories transferred poorly to 2006 and added about 12 seconds to row scoring.

## Experiment 3 — exploration: scheduled departure hour

Hypothesis: a 24-level hour category can group similar departure periods and avoid spending depth-4 tree splits on repeated time thresholds. The [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports worse delays late in the day. Unlike route, hour is dense and should generalize across years.

Result: `4a164fb` scored `0.6786` (−0.0003); discard. The raw scheduled-time variable already exposes most of this signal.

## Experiment 4 — follow-up: stochastic regularization

Hypothesis: the shallower model still fits noise in the 2005 sample; requiring larger leaves and sampling rows and columns may improve transfer to 2006. The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend `min_child_weight`, `subsample`, and `colsample_bytree` for overfitting control. Try 10, 0.8, and 0.8 respectively while holding depth, rounds, and features fixed.

Result: `1ca8048` scored `0.6805` (+0.0016); keep. Regularization helped the 2005-to-2006 transfer.

## Experiment 5 — follow-up: shallower trees with more rounds

Hypothesis: the benefit from depth 4 and stronger regularization suggests further reduced tree interaction complexity may help. Change depth to 3 and rounds to 600, holding the step size and regularizers fixed. This extends the complexity-versus-rounds tradeoff described in the [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).

Result: `215cf01` scored `0.6803` (−0.0002); discard. Depth 4 may preserve useful interactions.

## Experiment 6 — exploration: numeric calendar position

Hypothesis: month and day-of-month have ordered relationships that the original categorical representation cannot express with a single threshold. Add numeric versions alongside the categories. The [flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) motivates temporal patterns, while the year shift makes simple, stable features preferable to date-specific memorization.

Result: `89451e6` scored `0.6802` (−0.0003); discard. Extra temporal thresholds did not improve the row-scored year shift.

## Experiment 7 — exploration: one-category splits for small categoricals

Hypothesis: ordered partitioning of small calendar and carrier categories may group unrelated values according to 2005 noise. Set `max_cat_to_onehot=32`, giving individual-category splits for 7–31-level columns while keeping airport partitioning. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains this threshold and the two split styles.

Result: `d158b12` scored `0.6807` (+0.0002); keep. The small-category split style gave a slight improvement.

## Experiment 8 — follow-up: cap airport partition size

Hypothesis: origin and destination each have 283 categories; limiting how many category values can drive one partition split should reduce sparse-airport fitting across years. Keep the one-category treatment for small fields and set `max_cat_threshold=16` for airport partitioning. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this threshold as an overfitting control.

Result: `7f85091` scored `0.6775` (−0.0032); discard. The 16-category limit removed useful airport grouping.

## Experiment 9 — follow-up: more airport partition candidates

Hypothesis: the sharp loss at 16 suggests the default cap of 64 may also be restrictive. Raise `max_cat_threshold` to 128 on the kept model to allow broader airport partitions, while preserving all other settings. The [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) define this cap specifically for partition splits.

Result: `d472ddc` scored `0.6804` (−0.0003); discard. The default threshold appears adequate.

## Experiment 10 — exploration: stronger leaf-weight shrinkage

Hypothesis: airport/category effects fitted to 2005 may be too extreme even with larger leaves. Increase `reg_lambda` from the default 1 to 10, keeping tree structure and sampling fixed. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L2 leaf regularization as making updates more conservative.

Result: `519d0ef` scored `0.6817` (+0.0010); keep.

## Synthesis after 10 experiments

Best is `0.6817` at `519d0ef`, up `0.0074` from baseline. Shallower/longer boosting, row and column sampling with larger leaves, one-category splits for smaller categorical variables, and stronger L2 all helped. A 4,290-level route feature hurt sharply; hour and ordinal calendar additions failed to beat the raw inputs. Depth 3 was slightly worse than depth 4, and both lower and higher airport partition caps lost to the default. Current theory: the source-year shift rewards controlled tree complexity and stable low-cardinality effects. Next, research alternative ways to reduce boosting variance and refine shrinkage.

The [XGBoost random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes combining multiple parallel trees with boosting. The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) emphasize variance reduction through sampling and shrinkage. This suggests testing small forests within each boosting round, then tuning sampling or model length if needed.

## Experiment 11 — exploration: boosted forest of three trees

Hypothesis: averaging three sampled trees per boosting round may stabilize the category and airport effects across years. Set `num_parallel_tree=3`, retaining the kept model's subsampling, column sampling, learning rate, and rounds. This directly uses the boosted-forest option in the [XGBoost random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html).

Result: `7ca38f8` scored `0.6816` (−0.0001); discard. Triple model size and longer training did not improve ranking.

## Experiment 12 — exploration: departure time relative to origin schedule

Hypothesis: a flight's place within the origin airport's daily departure schedule may matter more than clock time alone, and depth-4 trees may need several splits to learn that interaction. Fit each origin's median scheduled departure minute on training rows and add the row's offset. This uses only preflight schedule fields, consistent with the temporal and airport effects described in the [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches).

Result: `8ba276d` scored `0.6806` (−0.0011); discard. The extra airport-relative time feature did not transfer well.

## Experiment 13 — follow-up: larger minimum leaves

Hypothesis: after L2 shrinkage helped, imposing a larger minimum child Hessian may further suppress small, noisy airport/date interactions. Change `min_child_weight` from 10 to 30 on the kept model. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies this as a conservative complexity control.

Result: `667c7ec` scored `0.6816` (−0.0001); discard. Larger leaves produced no gain.

Three candidates since the last keep failed, so I reviewed [work on ensembles of gradient boosted models](https://arxiv.org/abs/2006.10562) and [XGBoost's categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html). The former motivates averaging independently seeded fits to reduce training randomness; this differs from the within-round parallel trees of Experiment 11.

## Experiment 14 — exploration: average three seeded models

Hypothesis: separate boosting trajectories from different row/column samples may yield complementary errors, whereas three trees in each round share the same evolving residuals. Average the probabilities from three otherwise identical fits with seeds 42, 87, and 134. This adapts the independent-model ensemble design examined in the [gradient boosting ensemble paper](https://arxiv.org/abs/2006.10562).

Result: `013c760` tied at `0.6817` but was larger and slower; discard under the keep rule. Research on [target encoding](https://arxiv.org/abs/1706.09516) and [scikit-learn's cross-fitting explanation](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) highlights leakage from naive full-train target means, so I am avoiding that feature direction.

## Experiment 15 — follow-up: higher L2 regularization

Hypothesis: moving L2 from 1 to 10 helped by 0.0010, so 30 may improve stability further. Change only `reg_lambda` from 10 to 30 to test this curve. The [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe L2 as shrinking leaf weights.

Result: `aebae40` scored `0.6815` (−0.0002); discard. The useful L2 range appears closer to 10.

## Experiment 16 — ablation: remove column sampling

Hypothesis: only eight original fields are available, and selecting 80% per tree can exclude time or origin from many trees. With `min_child_weight=10` and L2=10 now constraining overfitting, using all columns may improve fit without losing year-to-year stability. Remove `colsample_bytree=0.8`, leaving row sampling. The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frame sampling as one optional overfitting control.

Result: `78458b6` scored `0.6801` (−0.0016); discard. Column sampling is beneficial even with eight fields.

## Experiment 17 — follow-up: stronger row sampling

Hypothesis: the benefit of stochastic regularization may come from greater diversity across trees. Lower row `subsample` from 0.8 to 0.6 while keeping column sampling and the other settings. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes subsampling per boosting round as an overfitting control.

Result: `b6b60be` scored `0.6806` (−0.0011); discard. The existing row sampling level is better.

Training artifact gain scores were highest for scheduled departure time (about 246, versus 15–54 for other fields). This measures average gain when selected, rather than an independent predictive effect, but suggests that useful time interactions might benefit from asymmetric trees. The [XGBoost grow-policy documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) describes loss-guided splitting at the node with the largest expected loss reduction.

## Experiment 18 — exploration: loss-guided trees

Hypothesis: with a 16-leaf budget, allowing loss-guided trees to spend depth on high-value time and airport branches could capture interactions more efficiently than uniformly depth-4 trees. Set histogram growth to `lossguide`, unlimited depth with `max_leaves=16`, and keep the current regularization. This follows the [XGBoost grow-policy documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: `07a9743` scored `0.6814` (−0.0003); discard. Flexible branch depth did not beat the symmetric depth limit.

## Experiment 19 — exploration: tree dropout

Hypothesis: the base model may over-rely on early time splits. DART drops a fraction of earlier trees while training later ones, which could spread importance across trees and help 2006 ranking. Keep 400 rounds and the existing tree settings; use `booster="dart"`, `rate_drop=0.1`, and `skip_drop=0.5`. The [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and [original DART paper](https://arxiv.org/abs/1505.01866) motivate this over-specialization control. Training runtime is a risk.

Result: `715893c` timed out before evaluation at 60 seconds; crash and discard. DART training cost is incompatible with 400 rounds here.

## Experiment 20 — exploration: carrier at the origin airport

Hypothesis: a carrier's departure reliability may vary by origin airport; an explicit `Origin`–`UniqueCarrier` category could expose this interaction to depth-4 trees. It has 1,551 training levels, fewer than the 4,290-route category that failed. The [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) discusses both carrier practices and airport conditions; the interaction is my inference from those factors. Fit levels on train and use a stable rowwise lookup.

Result: `c733449` scored `0.6782` (−0.0035); discard. Explicit high-cardinality combinations are still too sparse.

## Synthesis after 20 experiments

Best remains `0.6817` at `519d0ef`. Since the first synthesis, larger leaves, more L2, stronger row sampling, a loss-guided tree policy, and both ensemble forms failed to improve. DART exceeded the training limit. Airport-relative time and carrier-origin combinations also lost. The best model is a moderately regularized XGBoost tree ensemble on the eight starter fields, with one-category splits for low-cardinality fields. The largest average split gain belongs to scheduled departure time. Next, examine split resolution and ablate weak features, then consider depth/round choices.

The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) states that increasing `max_bin` can improve numeric split optimality at a computation cost. Scheduled departure time has 1,162 training values, above the default 256-bin limit. This offers a targeted new hypothesis without adding fragile row features.

## Experiment 21 — exploration: finer numeric split bins

Hypothesis: 512 histogram bins may distinguish more useful scheduled-departure thresholds than the default 256. Change only `max_bin` on the kept model and compare the row-scored AUC. Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: `ffb5347` scored `0.6814` (−0.0003); discard. Extra time split resolution gave no gain.

## Experiment 22 — follow-up: coarser numeric split bins

Hypothesis: since finer bins lost slightly, coarser 128-bin quantization may regularize scheduled-time splits and improve 2006 transfer. Change only `max_bin` from the default 256 to 128. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as the number of histogram buckets for numeric features.

Result: `40f38d8` scored `0.6810` (−0.0007); discard. The default 256 bins performs better than either 128 or 512.

## Experiment 23 — exploration: require split gain

Hypothesis: requiring a minimum loss reduction may cut weak airport/date splits that generalize poorly. Add `gamma=1` to the kept settings. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines gamma as the minimum loss reduction needed to split a leaf.

Result: `397a148` scored `0.6815` (−0.0002); discard. Three small declines in a row prompted more research. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes L1 leaf regularization from the L2 and split penalties tried so far. The [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) also recommend step-size and round-count tradeoffs.

## Experiment 24 — exploration: sparse leaf weights

Hypothesis: L1 shrinkage may suppress weak leaf adjustments differently from L2 and gamma, reducing fit to year-specific noise. Add `reg_alpha=1` to the kept model. This follows the [XGBoost L1 parameter definition](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: `24119de` scored `0.6815` (−0.0002); discard. L1 did not add value at this setting.

## Experiment 25 — follow-up: smaller steps over more rounds

Hypothesis: the current 400 rounds at learning rate 0.05 may reach the right model size with coarse updates. Use 700 rounds at 0.03, preserving a similar total shrinkage budget while smoothing the trajectory. The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend increasing rounds when reducing the step size.

Result: `9e88338` scored `0.6810` (−0.0007); discard. An earlier evaluation process disappeared before reporting AUC or writing timing, so I reran the unchanged committed candidate and used the completed result.

## Experiment 26 — follow-up: deeper trees with fewer rounds

Hypothesis: depth 3 lost slightly to 4; depth 5 with fewer rounds may capture useful time-by-airport interactions while the existing leaf, sampling, and L2 controls limit overfitting. Try 300 depth-5 trees at the same 0.05 rate. The [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frame depth as the interaction-capacity control.

Result: `c8d133a` scored `0.6815` (−0.0002); discard. Depth 4 remains best.

## Experiment 27 — ablation: individual splits only for calendar fields

Hypothesis: the slight benefit from `max_cat_to_onehot=32` may be due to month and day-of-week, while forcing individual splits for carrier and day-of-month may be wasteful. Set the threshold to 13, which one-hot splits month and weekday but uses partitioning for carrier, day-of-month, and airports. This tests the [XGBoost categorical split threshold](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) more selectively.

Result: `65ac930` scored `0.6816` (−0.0001); discard. It is close enough to motivate isolating the carrier effect.

## Experiment 28 — follow-up: individual splits for carrier too

Hypothesis: threshold 21 will one-hot split the 20-level carrier along with month and weekday, while leaving the 31-level day-of-month partitioned. It differs from Experiment 27 only in the carrier treatment and from the kept model only in day-of-month treatment. The [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) defines the threshold.

Result: `a8130de` scored `0.6796` (−0.0021); discard. This suggests the treatment of day-of-month and carrier interacts; the global threshold of 32 remains best.

## Experiment 29 — ablation: fewer boosting rounds

Hypothesis: 400 depth-4 trees may include late weak corrections; 300 at the same learning rate may generalize better or tie while simplifying the model. This directly tests the round-count side of the [XGBoost shrinkage tradeoff](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), without changing depth as Experiment 26 did.

Result: `80ff81f` scored `0.6814` (−0.0003); discard. Training is slightly faster but rowwise evaluation dominates total time.

## Experiment 30 — follow-up: more boosting rounds

Hypothesis: 300 rounds was weaker than the kept 400, so 500 at the same depth and rate may continue improving ranking before overfit takes hold. This differs from Experiment 25, which reduced the step size while increasing rounds. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe the round-count/step-size tradeoff.

Result: `b3dbe20` scored `0.6813` (−0.0004); discard. The 400-round setting is best among 300, 400, and 500 at depth 4.

## Synthesis after 30 experiments and final summary

Best Eval AUC: **0.6817** at commit **`519d0ef`**, an increase of **0.0074** from the 0.6743 baseline. The kept model uses 400 depth-4 trees at learning rate 0.05, min child weight 10, row and column sampling 0.8, a 32-category one-hot threshold, and L2 regularization 10. This was the best of 30 candidates. Its saved artifact is available for the human's holdout scoring.

What worked: shallower, longer boosting; moderate row and column sampling with larger leaves; one-category splits for the smaller categorical fields; L2 leaf shrinkage. What did not: explicit route or carrier-airport categories, added calendar or relative-time features, depth 3/5, longer or shorter boosting schedules, alternative histogram bins and tree growth, more aggressive penalties/sampling, and ensembles. DART timed out in training. The 300/400/500-round comparison supports keeping 400.

Next ideas: test a leak-safe way to encode high-cardinality airport effects that still gives exactly the same features for one-row scoring and training, or investigate whether a carefully designed schedule-only airport interaction transfers between years. The current results do not justify adding those untested ideas to the kept model.
