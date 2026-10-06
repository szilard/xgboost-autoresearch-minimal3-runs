# Research log — oct6

## Baseline

- Commit: `8d9c760`
- Eval AUC: 0.6743. Training took 0.6 s; row-wise evaluation took 30.2 s.
- Starter uses raw scheduled departure time and distance, six native categorical features, and 100 depth-6 trees at learning rate 0.1.

## Experiment 1 — shallower, slower boosting

- Type: exploration. Hypothesis: depth 4 with 300 trees and learning rate 0.05 will reduce overfitting to 2005 while retaining enough capacity.
- Source: [XGBoost tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): deeper trees raise model complexity, and smaller learning rates make each update more conservative.
- Result: `8b8a252`, 0.6795 (+0.0052); keep. Training plus evaluation took 32.6 s. Lower complexity appears helpful across years.

## Experiment 2 — depth 3

- Type: follow-up to experiment 1. Hypothesis: reducing depth from 4 to 3 with boosting budget unchanged will further reduce year-specific interactions if depth 4 is still too flexible. All other settings stay fixed.
- Source: [XGBoost tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html), depth and overfitting guidance.
- Result: `93540c3`, 0.6812 (+0.0017); keep. Shallower trees continue to help.

## Experiment 3 — departure hour category

- Type: exploration of schedule features. Hypothesis: a categorical departure hour will let depth-3 trees group nonadjacent hours with similar delay risk, complementing raw HHMM time.
- Source: [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) describes scheduled departure time in hours and time-of-day as standard flight-delay predictors.
- Result: `4d61736`, 0.6796 (-0.0016); discard. Additional categorical flexibility appears to overfit; raw HHMM already captures useful time ordering.

## Experiment 4 — numeric day of month

- Type: exploration of categorical handling. Hypothesis: numeric day-of-month splits will group neighboring dates and reduce year-specific noise from arbitrary categorical partitions.
- Source: [XGBoost categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains numerical threshold splits versus category partitioning.
- First attempt: `fbf65e3` crashed because dates use strings such as `c-22`, rather than bare integers. Fixing the conversion and rerunning the same hypothesis.
- Fixed run: `1fefbc3`, 0.6856 (+0.0044); keep. Ordered day splits transfer better than categorical day partitions.

## Experiment 5 — numeric month

- Type: follow-up to experiment 4. Hypothesis: numeric month splits will capture contiguous seasonal patterns with fewer arbitrary category groupings, improving transfer from 2005 to 2006.
- Source: [XGBoost categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) on numeric threshold splits versus categorical partitions; [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) discusses seasonal effects in flight delay.
- Result: `0b43513`, 0.6854 (-0.0002); discard. Month seems to benefit slightly from category partitioning, unlike day of month.

## Experiment 6 — day of year

- Type: exploration of seasonal representation. Hypothesis: a single continuous day-of-year feature allows shallow splits across month boundaries while retaining Month as categorical.
- Source: [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) reviews seasonal and calendar factors for departure-delay prediction.
- Result: `7a47967`, 0.6857 (+0.0001); keep under the printed-score rule. Small gain; seasonal encoding may be redundant with month and day.

## Experiment 7 — tighter categorical splits

- Type: exploration of categorical regularization. Hypothesis: lowering `max_cat_threshold` to 16 will curb overfitting in carrier and airport category partitions, prompted by the numeric day-of-month gain and categorical hour loss.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` limits categories considered per partition split to prevent overfitting.
- Result: `66ed609`, 0.6786 (-0.0071); discard. Reducing airport/carrier partition choices sharply hurts, so this capacity is useful.

## Experiment 8 — richer categorical splits

- Type: follow-up to experiment 7. Hypothesis: since a 16-category split limit hurt badly, raising `max_cat_threshold` to 128 may better model heterogeneous airport risks than the default.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) on `max_cat_threshold`.
- Result: `9f6d0f8`, 0.6842 (-0.0015); discard. The default is better than either 16 or 128, suggesting a useful middle level of airport partition capacity.

## Experiment 9 — more boosting rounds

- Type: follow-up to successful depth reduction. Hypothesis: 500 rather than 300 small steps at depth 3 will add useful patterns without restoring the depth-6 overfit.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes learning-rate shrinkage and tree-depth complexity.
- Result: `5e360b3`, 0.6850 (-0.0007); discard. Extending boosting at the same learning rate likely fits more 2005-specific structure.

## Synthesis after 10 run attempts

- Best: 0.6857 at `7a47967`, up 0.0114 from baseline.
- Helpful: shallower trees with smaller steps, numeric day-of-month, and a small gain from day of year.
- Unhelpful: categorical hour, numeric month, narrower or wider category split limits, and 500 boosting rounds.
- Current theory: broad schedule/calendar structure transfers across years; highly flexible category partitions and extra boosting can overfit, though airport partitions need some capacity. Researching new feature directions before the next experiment.

## Experiment 10 — origin-destination route category

- Type: exploration of a new interaction feature after the plateau. Hypothesis: an explicit route lets depth-3 trees use stable origin-destination patterns with one split, without deriving statistics from evaluation rows. Levels are fitted once on `train`.
- Source: [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) discusses origin-destination pairs in flight-delay prediction; [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes categorical partitioning.
- Result: `d8aa74b`, 0.6762 (-0.0095); discard. A 4,290-level route category sharply overfits this cross-year task and raises row-wise evaluation time to 44.8 s.

## Experiment 11 — depth 2

- Type: follow-up to experiments 1 and 2. Hypothesis: the large loss from route complexity, combined with gains from depth 6 to 4 to 3, suggests depth 2 may transfer even better across years.
- Source: [XGBoost tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) notes the complexity and overfitting cost of deeper trees.
- Result: `760ae82`, 0.6815 (-0.0042); discard. Depth 2 loses useful interactions; depth 3 appears to balance capacity and year-to-year transfer.

## Experiment 12 — departure time relative to route median

- Type: exploration following the failed route category. Hypothesis: a numeric deviation from each route's typical scheduled departure time can express schedule context without fitting 4,290 arbitrary route effects. The median is fitted once on `train` and looked up per row.
- Source: the [route-median example in `program.md`](../program.md) specifies this train-only lookup pattern; [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) motivates origin-destination and schedule interactions.
- Result: `4ecadd4`, 0.6853 (-0.0004); discard. A route's typical schedule adds little beyond the raw time, origin, destination and distance.

## Experiment 13 — row subsampling

- Type: exploration of stochastic regularization after the feature plateau. Hypothesis: `subsample=0.8` will make the depth-3 model less sensitive to 2005-specific examples while preserving categorical capacity.
- Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends `subsample` as a way to improve robustness to noise.
- Result: `edbffec`, 0.6849 (-0.0008); discard. Row subsampling at 0.8 removes useful signal more than it reduces overfit here.

## Experiment 14 — numeric day of week

- Type: follow-up to successful numeric day-of-month encoding. Hypothesis: ordered weekday splits may group adjacent workdays and weekends more robustly than categorical partitions across years.
- Source: [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains the split difference; [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) includes day of week as a predictor.
- Result: `0189d66`, 0.6835 (-0.0022); discard. Categorical weekday groups transfer better than ordered thresholds.

## Experiment 15 — minimum child weight

- Type: exploration of split-level regularization. Hypothesis: `min_child_weight=10` will suppress fragile leaves formed from rare airport/calendar groups without losing the depth-3 interactions.
- Source: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists `min_child_weight` as a complexity control; the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines its minimum child Hessian.
- Result: `9667470`, 0.6858 (+0.0001); keep under the printed-score rule. Weak but positive evidence that suppressing rare leaves helps.

## Experiment 16 — stronger minimum child weight

- Type: follow-up to experiment 15. Hypothesis: raising `min_child_weight` from 10 to 30 may further suppress unstable rare-category leaves; the larger step distinguishes a real regularization trend from a one-point fluctuation.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) on the conservatism of higher minimum child weight.
- Result: `439485a`, 0.6858 (equal); discard. Same code complexity and effectively same run time, so the keep rule favors the earlier setting.

## Experiment 17 — ablate day of year

- Type: ablation of experiment 6. Hypothesis: day of year contributed only +0.0001 before the child-weight change and may now be redundant with month and numeric day of month; removal could simplify at equal or higher AUC.
- Source: experiment 6 and `7a47967` in this log; [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) motivates seasonal features generally, but not this specific representation.
- Result: `aac1325`, 0.6857 (-0.0001); discard per strict keep rule. Day of year contributes a small but persistent amount even with higher minimum child weight.

## Experiment 18 — one-hot calendar splits

- Type: exploration of categorical split strategy. Hypothesis: one-hot splits for Month and DayOfWeek (but not carrier or airports) will avoid fragile grouped calendar categories across years. Best-model feature importance ranks Month second after scheduled departure time.
- Source: [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains one-hot versus partition-based splits and `max_cat_to_onehot`.
- Result: `23760b9`, 0.6841 (-0.0017); discard. Grouped calendar partitions outperform isolated category splits with shallow trees.

## Experiment 19 — cyclic departure time

- Type: exploration of a new time representation after the plateau. Hypothesis: sine and cosine of minutes since midnight may let shallow trees connect nearby late-night and early-morning departures while raw HHMM retains the daytime trend.
- Source: [scikit-learn time-related feature engineering](https://scikit-learn.org/1.8/auto_examples/applications/plot_cyclical_feature_engineering.html) explains sine/cosine encoding for periodic times; [UC Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) discusses time-of-day effects.
- Result: `ac85c11`, 0.6860 (+0.0002); keep. Cyclic time adds a small amount beyond raw HHMM, at roughly 5 s more row-wise evaluation.

## Synthesis after 20 run attempts

- Best: 0.6860 at `ac85c11`, up 0.0117 from baseline.
- Robust gains: depth 3 with slower boosting, numeric day of month, `min_child_weight=10`, and cyclic departure time. Day of year provides a small gain confirmed by ablation.
- Poor transfers: 4,290-level route category, extra boosting rounds, depth 2, and several changes that forced less flexible calendar or airport splits.
- Current theory: this task needs a modest amount of interaction capacity and smooth treatment of ordered/cyclic time, but fine-grained memorization of airports or routes hurts 2006 performance. Researching additional ways to model seasonal timing and regularize the useful shallow interactions.

## Experiment 20 — cyclic day of year

- Type: follow-up to cyclic departure time and day-of-year gains. Hypothesis: annual sine/cosine will connect late December and early January seasonal effects without requiring two separate tree branches.
- Source: [TU Delft review](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1) describes sine/cosine of day of year for flight-delay models; [scikit-learn time-feature guide](https://scikit-learn.org/1.8/auto_examples/applications/plot_cyclical_feature_engineering.html) explains periodic encoding.
- Result: `a48965b`, 0.6844 (-0.0016); discard. The annual circle adds noise or redundant seasonal splits, unlike the daily circle.

## Experiment 21 — stronger L2 leaf regularization

- Type: exploration of another regularization mechanism. Hypothesis: `reg_lambda=10` will shrink leaf outputs tied to 2005-specific patterns while preserving the effective depth-3 and categorical split structure.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) states that increasing L2 leaf regularization makes the model more conservative.
- Result: `ee4ecef`, 0.6850 (-0.0010); discard. Stronger L2 shrinkage underfits or reshapes the useful risk ordering.

## Experiment 22 — loss-guided eight-leaf trees

- Type: exploration of tree shape. Hypothesis: loss-guided growth with at most eight leaves will spend a depth-3-sized leaf budget on high-value schedule branches rather than splitting level by level.
- Source: [XGBoost tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `lossguide` as splitting the node with greatest loss change and `max_leaves` as the size limit.
- Result: `2df8037`, 0.6853 (-0.0007); discard. Uneven growth with the same nominal leaf budget does not beat balanced depth-3 trees.

## Experiment 23 — minimum split gain

- Type: exploration of selective branch pruning after three discards. Hypothesis: `gamma=5` will remove low-gain splits that capture year-specific noise while leaving large time/calendar splits in place.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as minimum split loss reduction. [scikit-learn's target-encoder study](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) and the [CatBoost paper](https://arxiv.org/abs/1706.09516) warn against naive target lookups, so this experiment avoids that leakage risk.
- Result: `0ffcd6b`, 0.6860 (equal), 38.9 s versus 38.8 s for the best; discard because it neither simplifies nor speeds up the model.

## Experiment 24 — carrier-origin interaction

- Type: exploration of operational interaction. Hypothesis: a carrier's operation at a particular origin airport has a more stable effect than a 4,290-level route; an explicit category makes it available to shallow trees in one split. The 1,551 levels are fixed from `train`.
- Source: [Li et al. (2021)](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057) identifies carrier and origin airport as delay predictors; the carrier-origin interaction is my inference from those factors.
- Result: `a85d65b`, 0.6802 (-0.0058); discard. Even this smaller high-cardinality interaction overfits across years; row-wise evaluation rose to 44.3 s.

## Experiment 25 — finer histogram bins

- Type: exploration of split precision. Hypothesis: `max_bin=512` will better locate time-of-day thresholds; scheduled departure time accounts for about 45% of the best model's feature importance, and it has 1,162 distinct training values.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) notes that raising `max_bin` improves split optimality at computation cost.
- Result: `9c49e76`, 0.6856 (-0.0004); discard. Finer departure-time thresholds do not transfer better, suggesting some quantization is useful.

## Experiment 26 — coarser histogram bins

- Type: follow-up to experiment 25. Hypothesis: reducing `max_bin` to 128 may regularize time thresholds that otherwise fit 2005 too specifically; 512 bins just lowered AUC.
- Source: [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) on histogram binning.
- Result: `a72ccbb`, 0.6854 (-0.0006); discard. Both coarser and finer bins lose against the default 256.

## Experiment 27 — half-day harmonic

- Type: exploration of a different time feature after the plateau. Hypothesis: a second daily harmonic will expose distinct morning/evening peaks to shallow trees beyond the first daily sine/cosine pair.
- Source: [scikit-learn's time-feature guide](https://scikit-learn.org/1.1/auto_examples/applications/plot_cyclical_feature_engineering.html) suggests higher harmonics for sharper within-day variation.
- Result: `96cdf9b`, 0.6858 (-0.0002); discard. The extra half-day wave adds complexity without improving 2006 AUC.

## Experiment 28 — ablate daily sine

- Type: ablation of the successful cyclic departure time feature. Hypothesis: raw HHMM plus daily cosine may retain the midnight connection and the 0.6860 AUC without the sine feature's cost.
- Source: experiment 19 (`ac85c11`) and the [scikit-learn time-feature guide](https://scikit-learn.org/1.8/auto_examples/applications/plot_cyclical_feature_engineering.html).
- Result: `8cd9a08`, 0.6857 (-0.0003); discard. The sine term contributes useful information despite the raw time and cosine feature.

## Final summary

- Best Eval AUC: **0.6860** at `ac85c11`, up 0.0117 from the 0.6743 baseline `8d9c760`.
- What worked: depth 3 with 300 trees and learning rate 0.05; numeric day of month; day of year; minimum child weight 10; daily sine and cosine of scheduled departure time. The latter gains were small under the printed four-decimal AUC.
- What did not: high-cardinality route and carrier-origin categories; categorical departure hour; numeric month or weekday; wider or narrower category and histogram thresholds; extra boosting; depth 2; stronger L2 or loss-guided growth; annual and half-day harmonics. Ablations confirmed the day-of-year and daily sine features helped slightly.
- Next: test carefully smoothed airport-history features with a training encoding that avoids own-label leakage, or explore a different training-year split design if the human permits. Do not use the held-out human data for this tuning.
