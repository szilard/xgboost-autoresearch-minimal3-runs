# oct5 research log

## Baseline — 8d9c760

Unchanged starter model: 0.6743 Eval AUC, 32.4 s total. The 200,000 training rows are balanced and have no missing values. The model uses XGBoost native categorical handling with 100 depth-6 trees.

## Experiment 1 — scheduled time components

Exploration. Hypothesis: scheduled departure hour and minute have patterns that are harder to capture from HHMM as a single number. Keep the original HHMM and add integer hour and minute features. The [Berkeley flight-delay feature engineering study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) highlights departure-hour effects. XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) also emphasizes preprocessing and controlling tree complexity. The features are computed from each row independently.

Result: 0.6752, up 0.0009. Kept. The time components provide a small gain.

## Experiment 2 — shallower, longer boosting

Follow-up to experiment 1. Hypothesis: depth-6 trees can fit 2005-specific interactions that do not transfer to 2006; depth 4 with more trees and lower learning rate may learn stable effects. Try 300 trees, depth 4, learning rate 0.05. This follows XGBoost's [parameter tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) on depth, learning rate, and compensating tree count.

Result: 0.6789, up 0.0037. Kept. Lower-complexity trees with more boosting transferred better.

## Experiment 3 — more rounds at the same tree complexity

Follow-up to experiment 2. Hypothesis: at learning rate 0.05 and depth 4, 300 trees may not capture all stable effects; increasing only `n_estimators` to 600 tests whether the model is still underfitting. The XGBoost [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes the step-size effect of learning rate.

Result: 0.6771, down 0.0018. Discarded. More rounds appear to fit year-specific noise; 300 trees remains the best setting.

## Experiment 4 — larger minimum leaf weight

Follow-up to experiment 3's overfitting signal. Hypothesis: raising `min_child_weight` from 1 to 5 will discourage splits on small groups while preserving 300 rounds of depth-4 interactions. The [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies this as a complexity control.

Result: 0.6784, down 0.0005. Discarded. The stronger leaf constraint removed some useful structure.

## Experiment 5 — day of year

Exploration of calendar representation. Hypothesis: an ordinal day-of-year feature gives the trees contiguous seasonal windows that may generalize from 2005 to 2006 better than separate categorical month and day values. Retain the original fields and add a single deterministic row-level feature. The [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies seasonal patterns, and the [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that categorical splits group levels by their learned response rather than calendar order.

Result: 0.6822, up 0.0033. Kept. Ordinal seasonal windows are useful across years.

## Experiment 6 — carrier at origin

Exploration of a categorical interaction. Hypothesis: a carrier's operations at a particular origin airport have stable delay risk that is hard to learn through separate splits in depth-4 trees. Add a categorical carrier-origin key with levels learned from `train.csv`. The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partition-based grouping for category values; the [Berkeley flight-delay study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies carrier and origin as relevant schedule-time features. There are 1,551 carrier-origin pairs in training.

Result: 0.6763, down 0.0059. Discarded. The explicit high-cardinality interaction overfits or distracts the model. Unseen pairs also generated repeated pandas warnings, increasing eval time to 45.1 s.

## Experiment 7 — depth-three trees

Follow-up to the calendar gain. Hypothesis: after adding day of year, depth-3 trees may be enough to capture stable seasonal and schedule effects and may generalize better across years. Change only `max_depth` from 4 to 3 at 300 trees and 0.05 learning rate. This probes the depth versus generalization tradeoff in the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).

Result: 0.6843, up 0.0021. Kept. Shallower interactions transfer better.

## Experiment 8 — more depth-three rounds

Follow-up to experiment 7. Hypothesis: the simpler depth-3 trees can benefit from more rounds before overfitting. Increase only `n_estimators` from 300 to 500 at learning rate 0.05; compare with experiment 3, where more depth-4 rounds hurt.

Result: 0.6831, down 0.0012. Discarded. Additional rounds again hurt transfer.

## Experiment 9 — fewer depth-three rounds

Follow-up to experiment 8. Hypothesis: 300 rounds may already be past the best point; try 200 rounds at the same depth and learning rate. This changes only boosting duration and tests the other side of the learning curve.

Result: 0.6832, down 0.0011. Discarded. The local best is 300 depth-3 rounds.

## Experiment 10 — row subsampling

Exploration of training randomness. Hypothesis: sampling 80% of rows for each tree will reduce sensitivity to idiosyncratic 2005 observations without losing too much signal from 200,000 rows. Change only `subsample` to 0.8 on the kept 300-tree model. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends subsampling as a way to control overfitting.

Result: 0.6828, down 0.0015. Discarded. Row sampling sacrificed signal here.

## Synthesis after 10 experiments

Best AUC is 0.6843 at a2c056e, up 0.0100 from baseline. Adding day of year and reducing tree depth helped most; scheduled hour and minute were a smaller gain. At depth 3, both 200 and 500 trees underperformed 300. More depth-4 rounds, larger minimum leaf weight, row subsampling, and carrier-origin categories also hurt. Current theory: broad, stable schedule and seasonal effects matter more than sparse interactions. The next direction is categorical split control, followed by other temporal representations and model diversity. New research: [XGBoost categorical parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html), [XGBoost DART docs](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html), and a [flight-delay study](https://www.mdpi.com/2079-9292/13/24/4910) describing week-of-year features.

## Experiment 11 — limit category partition size

Exploration of categorical handling. Hypothesis: reducing `max_cat_threshold` from its actual default of 64 to 32 may constrain origin and destination category partitions and improve transfer to 2006 without affecting most lower-cardinality fields. The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe this parameter as an overfitting control. Keep all other settings at a2c056e.

Result: 0.6814, down 0.0029. Discarded. Airport category partitions need more than 32 candidates here.

## Experiment 12 — finer numeric histograms

Exploration of split resolution. Hypothesis: `DayOfYear` has 365 distinct values but the histogram method defaults to 256 bins, so `max_bin=512` may give more precise seasonal split points. All other settings remain at a2c056e. The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) state that more bins can improve split optimality at a computation cost.

Result: 0.6840, down 0.0003. Discarded by the strict keep rule. Finer bins did not add useful generalization.

## Experiment 13 — depth-two trees

Follow-up to experiment 7's depth gain. Hypothesis: main effects dominate and depth-2 trees may further improve cross-year transfer. Change only `max_depth` from 3 to 2 at 300 trees. This is a meaningful lower-capacity setting, following the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).

Result: 0.6797, down 0.0046. Discarded. Depth 2 loses important interactions; depth 3 is the best depth tested.

## Experiment 14 — blend depths three and four

Exploration of model diversity. Hypothesis: depth-3 and depth-4 models capture overlapping but different effects, and averaging their probabilities may reduce prediction variance. Train both on the same `train.csv` and use scikit-learn's soft-voting classifier, with equal weights. This follows the [scikit-learn VotingClassifier documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) on averaging class probabilities. The depth-4 model alone scored 0.6822, so it contributes only if its errors are complementary.

Result: 0.6840, down 0.0003. Discarded. Model diversity from tree depth alone was insufficient.

## Experiment 15 — categorical week of year

Exploration of a coarser calendar feature. Hypothesis: categorizing fixed seven-day blocks of the year may expose recurring travel peaks while pooling more rows than individual days. Keep numeric day of year and add a 53-level week category computed from each row. A [flight-delay feature study](https://www.mdpi.com/2079-9292/13/24/4910) discusses week-of-year seasonality; XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partition-based grouping of weeks with similar response.

Result: 0.6822, down 0.0021. Discarded. The categorical week partitions likely emphasize 2005-specific peaks.

## Experiment 16 — major holiday travel windows

Exploration of calendar events. Hypothesis: the Thanksgiving date shifts from year to year, so numeric day of year alone may miss its travel window; fixed-date Christmas/New Year and July Fourth periods may also differ from adjacent days. Add a compact `HolidayPeriod` category based only on month, day, and weekday for each row. The [Schösser and Schönberger flight-delay study](https://traffic2.fpz.hr/index.php/PROMTT/article/download/144/28/400) includes holidays among schedule-time features and reports their influence. No outcome or evaluation data is used to construct it.

Result: 0.6840, down 0.0003; eval time rose to 50.6 s. Discarded. The existing calendar features already capture most holiday signal.

## Experiment 17 — time relative to route median

Exploration of a train-fitted schedule lookup. Hypothesis: a departure time unusual for an origin-destination route may indicate a different operational schedule and delay risk. Fit each route's median scheduled departure minute using only `train.csv`; within `prepare`, subtract that median from the row's scheduled minute. This follows the allowed lookup pattern in `program.md` and the [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) on route and schedule characteristics. No row counts or target outcomes enter the lookup.

Result: 0.6842, down 0.0001; eval time rose to 43.2 s. Discarded by the strict keep rule.

## Experiment 18 — remove unused departure minute

Ablation/simplification. The kept depth-3 model's booster reports zero splits on `DepMinute`. Hypothesis: removing it leaves the same AUC and slightly reduces row-by-row preparation time. The added hour and original HHMM remain. This directly tests whether the original experiment 1 gain required minute-of-hour.

Result: 0.6843, equal AUC; eval time fell from 38.1 s to 36.3 s. Kept as a simplification.

## Experiment 19 — loss-guided trees with eight leaves

Exploration of growth strategy. Hypothesis: depthwise trees can spend capacity on less useful branches; `grow_policy="lossguide"` with at most eight leaves may allocate the same approximate capacity to the strongest schedule and seasonal interactions. Set `max_depth=0` and `max_leaves=8`, keeping 300 rounds at learning rate 0.05. The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe loss-guided growth and leaf limits.

Result: 0.6833, down 0.0010. Discarded. Depthwise growth remains stronger.

## Experiment 20 — month and weekday interaction

Exploration of a low-cardinality categorical interaction. Hypothesis: weekly travel patterns vary by season, and a month-weekday combination lets depth-3 trees capture that with one split. There are only 84 possible levels, unlike the 1,551-level carrier-origin feature that hurt earlier. This is motivated by the [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) on seasonal and weekday patterns and the [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

Result: 0.6823, down 0.0020. Discarded. Explicit calendar interactions have not transferred well.

## Synthesis after 20 experiments

Best AUC remains 0.6843 at 59226f3, up 0.0100 from baseline. The second set found an equal-AUC simplification: `DepMinute` had zero splits and removing it shortened evaluation. More histogram bins nearly tied but did not beat the best; categorical partition tightening, depth-2 trees, loss-guided trees, blending depths, explicit month-weekday, week-of-year, holiday periods, and route-relative time did not help. The current theory is that 300 depth-3 trees on raw schedule fields plus numeric day of year capture the transferable signal; extra interaction freedom or calendar detail often follows 2005 noise. New research for the next direction: [XGBoost DART](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html), [XGBoost split regularization](https://xgboost.readthedocs.io/en/stable/parameter.html), and [scikit-learn's cyclical time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).

## Experiment 21 — smaller boosting steps

Follow-up to experiments 8 and 9. Hypothesis: 500 trees at learning rate 0.03 may give a smoother fit than 300 at 0.05, while keeping the same approximate total step budget (15). This distinguishes additional model complexity from the learning-rate effect that caused 500 trees at 0.05 to overfit. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends lowering the step size while increasing rounds.

Result: 0.6835, down 0.0008. Discarded. Smaller steps did not improve the transfer score at similar total shrinkage.

## Experiment 22 — DART tree dropout

Exploration of booster regularization. Hypothesis: dropout across trees may reduce dependence on year-specific corrective trees while retaining depth-3 effects. Use XGBoost `booster="dart"`, `rate_drop=0.05`, `skip_drop=0.5` at 300 rounds. This follows the [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html); training may take longer, but the 60-second training limit remains the gate.

Result: 0.6828, down 0.0015; training took 27.4 s rather than under a second for `gbtree`. Discarded. DART also emitted a deprecation warning for `booster="dart"` in the installed XGBoost.

## Experiment 23 — minimum split gain

Exploration of split regularization. Hypothesis: weak splits follow 2005-specific noise; `gamma=0.5` may suppress those while retaining splits on large schedule effects. The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define gamma as the minimum loss reduction to split, and a [flight-delay study](https://traffic2.fpz.hr/index.php/PROMTT/article/download/144/28/400) reported a tuned value near 0.59 in a different setting. Change only gamma from 0.

Result: 0.6843, equal AUC but no simplification or speed gain. Discarded under the keep rule.

## Experiment 24 — one-hot splits for smaller categories

Exploration of categorical split strategy. Hypothesis: allowing one-hot splits for month, weekday, carrier, and day-of-month may isolate distinct category effects more reliably than response-ordered partitions, while the 283-level airports remain partitioned. Set `max_cat_to_onehot=32` (default 4). The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains the switch between one-hot and partition-based splits.

Result: 0.6819, down 0.0024. Discarded. Partition-based splits are more effective for these calendar and carrier categories.

## Experiment 25 — cyclical day of year

Exploration of cyclic calendar representation. Hypothesis: numeric day of year places December and January at opposite ends despite similar winter conditions, while sine and cosine features join the ends of the cycle. Retain the ordinal day feature and add both periodic components. The [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) motivates these encodings; their value for this tree model is an empirical question.

Result: 0.6832, down 0.0011; eval time rose to 39.9 s. Discarded. The existing month category and ordinal day of year are sufficient for these seasonal effects.

## Experiment 26 — remove categorical day of month

Ablation/simplification. Hypothesis: categorical day of month may fit irregular 2005-specific date effects, while `DayOfYear` already provides fixed calendar position. Remove only `DayofMonth` from the model's categorical input; it remains available to `prepare` for computing day of year. If AUC ties, the simpler and faster model wins under the keep rule.

Result: 0.6842, down 0.0001, despite eval time improving from 36.3 s to 32.7 s. Discarded under the strict keep rule.

## Experiment 27 — ordinal day of month

Follow-up to experiment 26. Hypothesis: day-of-month is useful, but a numeric representation may provide more stable contiguous windows than categorical partitions and score faster row by row. Replace the categorical `DayofMonth` with a numeric `DayNumber`, retaining `DayOfYear`. This tests representation rather than simply removing the information.

Result: 0.6856, up 0.0013. Kept. Contiguous day-of-month windows appear to transfer better than response-grouped day categories.

## Experiment 28 — combine numeric and categorical day of month

Follow-up to experiment 27. Hypothesis: numeric `DayNumber` gives the broad within-month trend, while the categorical day can represent repeatable special dates. Add the original categorical `DayofMonth` back without removing `DayNumber`; assess whether the extra freedom improves or overfits.

Result: 0.6843, down 0.0013. Discarded. The categorical representation appears to draw trees toward less transferable day-specific patterns.

## Experiment 29 — depth four with ordinal day

Follow-up to experiment 27. Hypothesis: the new ordinal day feature may help depth-4 trees learn useful interactions without spending splits on categorical day partitions. Change only `max_depth` from 3 to 4 to re-check the previously losing capacity level with the improved feature set.

Result: 0.6841, down 0.0015. Discarded. Shallow depth still transfers best.

## Experiment 30 — 400 depth-three rounds with ordinal day

Follow-up to experiment 27. Hypothesis: the better date representation may let more depth-3 rounds add transferable signal before overfitting. Test 400 rounds, midway between the prior 300-round best and 500-round overfit result on the old representation. Change only `n_estimators`.

Result: 0.6855, down 0.0001. Discarded. The strict best remains 300 rounds.

## Synthesis after 30 experiments

Best Eval AUC is 0.6856 at bf7afb4, up 0.0113 from baseline. The strongest gains came from day of year, lower tree depth, and treating day of month as an ordinal number instead of a category. Categorical day added back hurt, as did depth 4 and 400 rounds with the new representation. Dropout, one-hot categorical splits, cyclic encoding, and smaller learning-rate steps did not break the earlier plateau. The model may be near the limit of these schedule-only fields; remaining experiments will focus on shrinkage, category partition limits, and ablation. New research: [scikit-learn's encoding comparison](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_categorical.html) supports native categories for high-cardinality fields and explains the cost of one-hot splits, while [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L2 regularization and column sampling. I also reviewed [target-encoding leakage guidance](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) and will avoid in-sample target statistics.

## Experiment 31 — stronger L2 leaf regularization

Exploration of shrinkage. Hypothesis: `reg_lambda=5` may smooth leaf scores without excluding splits, improving cross-year transfer compared with the default of 1. This differs from `min_child_weight`, which removed candidate splits and hurt earlier. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as an L2 penalty on leaf weights.

Result: 0.6849, down 0.0007. Discarded. Stronger L2 shrinkage did not help.

## Experiment 32 — wider airport category partitions

Follow-up to experiment 11. Hypothesis: the 283-level origin and destination fields may benefit from considering more than the default 64 category candidates per partition. A smaller threshold of 32 hurt; test `max_cat_threshold=128` with the stronger ordinal-day feature set. The [XGBoost categorical parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe this limit.

Result: 0.6843, down 0.0013. Discarded. The default category threshold remains best.

## Experiment 33 — remove scheduled hour

Ablation/simplification. Hypothesis: original HHMM already orders departure times, so the derived `DepHour` may be redundant after the calendar improvements. Remove it and keep `CRSDepTime`; retain only if AUC improves or ties with simpler, faster code.

Result: 0.6857, up 0.0001; eval time fell from 35.0 s to 33.6 s. Kept. HHMM is sufficient for the time-of-day effect.

## Experiment 34 — remove distance

Ablation/simplification. Hypothesis: distance may contribute little once origin and destination are known, and its learned splits may reflect 2005-specific route mix. Remove `Distance` from the numeric inputs. Keep only if AUC improves or ties with simpler, faster code.

Result: 0.6848, down 0.0009. Discarded. Distance contributes transferable information.

## Final summary

Best Eval AUC: **0.6857** at commit **72d7e0a**, versus 0.6743 at baseline, an increase of 0.0114. The best model uses 300 depth-3 XGBoost trees at learning rate 0.05, native categories for month, weekday, carrier, origin, and destination; numeric HHMM departure time, distance, day of year, and ordinal day of month. It is trained only on `data/train.csv` and retains the required `save_and_evaluate(model, prepare)` call.

What worked: numeric day of year, shallower trees, ordinal day of month in place of its categorical representation, and removal of unused departure minute and hour features. What did not: more or fewer rounds, deeper or shallower trees, stronger regularization, dropout, alternative categorical split settings, explicit categorical interactions, holiday/week features, cyclic day encoding, route-relative departure time, and removing distance. These are Eval AUC results only; holdout generalization remains for the human-only post-run check.

Next directions: test train-only unsupervised airport schedule summaries such as departure time relative to the origin median; explore calendar representations that preserve broad seasonal effects without date-specific overfitting; and, if a larger data window becomes available, validate whether the current small AUC gains remain stable across years. Avoid in-sample target encoding without cross fitting because it can leak each training row's label.
