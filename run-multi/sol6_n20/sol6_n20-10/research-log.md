# Research log: oct6

## Baseline 8d9c760
Unchanged starter: Eval AUC 0.6743, training 1.4s, evaluation 30.1s. The sample has 200,000 balanced 2005 flights; 2006 evaluation is a temporal shift. Scheduled departure is stored as HHMM, while Month/DayofMonth/DayOfWeek are strings. Each evaluation row is prepared alone.

Initial research: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) recommends controlling complexity with depth, child weight and gamma, randomness with subsample/column sampling, and more rounds when reducing learning rate. [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes partition based categorical splits via max_cat_to_onehot. [Berkeley airline delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) highlights time of day and calendar patterns; only scheduled features are usable here. Test these as separate hypotheses.

## Experiment 1: scheduled time in minutes
Exploration, informed by the Berkeley time-of-day feature discussion. Hypothesis: HHMM has artificial gaps at each hour; minutes after midnight gives trees a meaningful continuous time scale. Replace the raw field without changing model capacity.
Result: 0.6743, equal to baseline; evaluation 32.5s vs 29.9s. Discard because no simplification or speed gain. A monotone recoding alone did not alter useful tree splits enough.

## Experiment 2: ordered calendar fields
Exploration based on Berkeley's calendar-seasonality discussion. Hypothesis: ordered numeric month and day-of-month permit adjacent calendar values to share statistical strength, whereas categorical splitting can fit arbitrary 2005-specific partitions. Keep day-of-week categorical because it is cyclic and has only seven values.
Result: 0.6774 (+0.0031), evaluation 27.8s. Kept. Adjacent calendar values appear to carry transferable structure.

## Experiment 3: slower boosting with more trees
Follow-up to 0.6774: the first model uses just 100 trees. XGBoost's tuning guide recommends lowering eta while increasing boosting rounds. Hypothesis: 400 trees at 0.05 learn a smoother useful score with less single-tree dependence. Keep depth six for isolation of learning schedule.
Result: 0.6723, a 0.0051 decline from the current best. Deeper ensemble appears to overfit 2005 patterns or lose cross-year calibration. Discard.

## Experiment 4: shallower longer ensemble
Follow-up to experiment 3 and current best. XGBoost's tuning guide identifies max_depth as the main complexity control. Hypothesis: depth three with 400 trees at eta 0.05 can capture stable additive patterns while limiting the 2005-only interactions seen with depth six.
Result: 0.6850 (+0.0076 over prior best), training 1.7s, evaluation 28.0s. Kept. The contrast with experiment 3 supports a strong cross-year regularization need: gradual boosting works when interactions are shallow.

## Experiment 5: depth two
Ablation of the promising shallow model. Hypothesis: if cross-year generalization benefits from fewer interactions, depth two at the same 400 rounds may improve AUC further. This changes only depth.
Result: 0.6836, 0.0014 below depth three. Discard. Some pairwise or three-way interactions are useful.

## Experiment 6: route category
Exploration of a new feature family. The [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains category partitioning for native categorical features. Hypothesis: a route label gives depth-three trees access to origin-destination interactions without spending two split levels. 4,290 routes occur in training. Unknown eval routes become missing categories.
Result: 0.6739, down 0.0111, with evaluation time 40.1s. Discard. Sparse route identities overfit the 2005 sample or shift poorly to 2006; avoid similar high-cardinality combinations for now.

## Experiment 7: day of year
Exploration of calendar interaction after route category failed. Hypothesis: a single ordinal day-of-year feature lets shallow trees isolate seasonal and holiday windows with one split rather than separate month and day splits. It is computed solely from each row's month/day and nonleap month offsets shared by 2005 and 2006.
Result: 0.6849, 0.0001 below best, with ~3 seconds slower evaluation. Discard under the strict keep rule. The shallow model already gets most usable seasonality from numeric month and day.

## Experiment 8: row subsampling
Follow-up to depth-three model. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) describes subsample as a way to reduce overfitting. Hypothesis: using 80% of training rows per tree weakens dependence on peculiarities of the 2005 sample while preserving the helpful shallow interactions. Only subsample changes.
Result: 0.6852 (+0.0002), training 1.9s, eval 28.1s. Kept despite the small gain, because the reported four-decimal AUC is higher.

## Experiment 9: larger minimum child weight
Follow-up to the small subsampling gain. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) define min_child_weight as a minimum Hessian mass for a split. Hypothesis: 10 (vs default 1) suppresses splits on sparse airport/carrier patterns that fail across years.
Result: 0.6852, equal to best but with an extra parameter and negligible time difference. Discard by the keep rule.

## Experiment 10: column subsampling
Exploration of a distinct regularization mechanism from row subsampling. XGBoost's tuning guide recommends column sampling to reduce overfit. Hypothesis: colsample_bytree=0.8 forces alternative useful predictors into the ensemble and prevents dependence on a few 2005-specific splits.
Result: 0.6852, equal to current best with extra complexity and no credible speed gain. Discard.

## Synthesis after 10 experiments
Best is 0.6852 at 02c24fa. Ordered month and day fields contributed +0.0031, and shallow depth-three boosting with 400 rounds contributed +0.0076. Row subsampling gave a small +0.0002. More deep trees, depth two, route identity, and day of year did not help. Child weight and column sampling tied without simplification. Current theory: broad calendar and time patterns transfer across years, while sparse route details do not. Next test categorical split strategy and loss-guided growth rather than adding more route identity.

New research: [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) identify max_cat_to_onehot as the one-hot versus partition switch and grow_policy as depthwise versus loss-guided growth. Installed XGBoost is 3.4.1, whose default threshold is four; day-of-week has seven levels. One-hot splitting day-of-week is a meaningful untried alternative. max_cat_threshold can regularize partition splits in high-cardinality airports, and max_leaves can bound loss-guided trees. These will be tested deliberately.

## Experiment 11: one-hot day of week
Exploration based on the XGBoost categorical parameter docs. max_cat_to_onehot=16 changes seven-level day-of-week from partition splits to one-hot splits while leaving 20-level carrier and 283-level airport fields partitioned. Hypothesis: individual weekday effects are more stable across years than dynamically grouped weekdays.
Result: 0.6850, down 0.0002. Discard. Grouping weekdays seems slightly preferable or the effect is negligible.

## Experiment 12: restrict airport category partitions
Exploration of categorical regularization. XGBoost documents max_cat_threshold as the maximum categories considered for a partition-based split to prevent overfitting. Hypothesis: lowering it to 16 reduces fitting of unstable rare airport categories while retaining broad airport effects. Leave weekday partitioning as in the best model.
Result: 0.6801, a substantial decline. Discard. Rich partition choices for airport/carrier categories seem important; this regularizer was too strong.

## Experiment 13: loss-guided eight-leaf trees
Exploration from XGBoost's grow_policy and max_leaves documentation. Hypothesis: letting each tree put its eight leaves where gain is highest may capture a few useful deeper interactions, while retaining about the same leaf budget as depth-three depthwise trees. Set max_depth=0, max_leaves=8, grow_policy=lossguide.
Result: 0.6849, down 0.0003. Discard. Allowing deeper paths within the same leaf budget did not improve cross-year AUC.

## Experiment 14: fewer boosting rounds
Ablation of the 400-round model. Hypothesis: the current model may still fit late-stage 2005 noise, so 250 rounds with the same depth, eta and subsample could improve the 2006 ranking. This isolates boosting duration.
Result: 0.6848, down 0.0004. Discard despite faster training; strict AUC rule takes precedence.

## Experiment 15: more shallow boosting rounds
Follow-up to experiment 14. Since 250 rounds were slightly worse than 400, test 700 rounds at the same learning rate and depth. Hypothesis: depth-three trees may still be underfitting transferable patterns; the deeper model's failure did not answer this.
Result: 0.6847, down 0.0005. Discard. Three consecutive experiments (loss-guided leaves, 250 rounds, 700 rounds) have moved by less than 0.001; pause for targeted research before changing the model again.

## Plateau research and experiment 16: monotone departure time
The [XGBoost monotonic constraints tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) explains how a strong directional prior can reduce noise; [feature interaction constraints](https://xgboost.readthedocs.io/en/release_0.90/tutorials/feature_interaction_constraint.html) offer another way to suppress spurious interactions. The [scikit-learn target-encoder example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) shows severe leakage without cross fitting, so avoid naive target encodings under this row-wise prepare interface. In train.csv, delay rate rises from ~0.19 at 6am to ~0.65 at 8pm, then softens in sparse late hours. A monotone constraint on scheduled departure is a test of whether that broad trend is more transferable than unconstrained splits. This is an exploration of a new regularization category.
Result: 0.6849, down 0.0003. Discard. The monotone prior is slightly too rigid for the sparse late-night decrease or conditional effects.

## Experiment 17: numeric day of week
Exploration of calendar representation motivated by numeric month/day success. Hypothesis: ordered weekday values let trees share weekday versus weekend structure more efficiently than categorical partitioning. It changes only one existing feature's type.
Result: 0.6836, down 0.0016. Discard. Weekday category partitions are better than the simple ordinal representation.

## Experiment 18: departure relative to route schedule
Exploration of train-fitted, label-free group statistics, matching the allowed example in program.md. [scikit-learn's preprocessing guidance](https://scikit-learn.org/1.0/common_pitfalls.html) emphasizes fitting transforms on train and applying them consistently later. Hypothesis: offset from a route's typical scheduled departure lets depth-three trees recognize unusually early or late flights on that route with one split. Fit route median departure minutes on train; apply per row with lookup. This uses no target or row counts.
Result: 0.6855 (+0.0003), evaluation 32.7s. Kept. A route-relative schedule signal may be useful, despite the route identity feature failing.

## Experiment 19: origin median schedule instead of route median
Ablation/simplification of experiment 18. Hypothesis: a departure offset from the origin airport's typical flight time retains schedule context while using a more stable 283-level lookup and speeding row-wise evaluation. Replace route median with origin median; do not add both.
Result: 0.6855, equal to route median, with evaluation 31.8s versus 32.7s and a much smaller lookup. Kept as a simplification at equal AUC.

## Synthesis after 20 experiments
Best is 0.6855 at 59fd87c. The largest advances remain numeric month/day and shallow boosted trees; origin-relative departure time adds a small gain and is as effective as a route median with less cost. Native categorical airport groups are useful (restricting partitions hurt), but explicit route identity was harmful. Weekday should stay categorical. Booster duration around 400 appears well placed: 250 and 700 were both slightly worse. Next explore feature representation or model objectives that make better use of stable airport and time effects, with care around target leakage.

Research after 20 experiments: [XGBoost's current tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists gamma and L2 regularization as untried complexity controls; [the DART tutorial](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/dart.html) suggests tree dropout can reduce overfitting but warns of slower training. I will first test other schedule representations, then consider these regularizers if features plateau.

## Experiment 21: destination median schedule instead of origin
Ablation of the 283-level origin lookup. Hypothesis: departures headed to a destination may have a characteristic schedule, and deviation from that schedule may transfer across years. Keep the same feature type and cost, replacing origin lookup with destination lookup.
Result: 0.6855, equal to origin version with effectively identical time and complexity. Discard by keep rule. The group-relative feature seems weak and robust to origin versus destination choice.

## Experiment 22: stronger L2 leaf regularization
Exploration prompted by the current [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html). Hypothesis: reg_lambda=10 (default 1) shrinks tree leaf scores, especially sparse airport partitions, improving generalization across 2005 to 2006 without discarding useful category choices as max_cat_threshold=16 did.
Result: 0.6858 (+0.0003) with no meaningful runtime change. Kept. Shrinking leaf outputs helps modestly.

## Experiment 23: stronger L2 at 30
Follow-up to experiment 22. Hypothesis: further shrinkage of leaf scores could reduce cross-year overfit more; testing 30 rather than changing multiple controls at once.
Result: 0.6861 (+0.0003). Kept. The trend from lambda 1 -> 10 -> 30 is positive.

## Experiment 24: L2 at 100
Follow-up to the positive regularization trend. Hypothesis: substantially stronger leaf shrinkage helps this noisy cross-year task further. Isolate reg_lambda=100, accepting that training may become more biased.
Result: 0.6855, down 0.0006, with training unusually slow at 21.2s. Discard. The optimum appears below 100.

## Experiment 25: L2 at 50
Follow-up to the bracket formed by lambda 30 (best) and 100 (worse). Hypothesis: a moderate increase from 30 may preserve the generalization benefit without the bias at 100. This is a targeted interpolation, not a random parameter change.
Result: 0.6854, down 0.0007. Discard. Lambda 30 is the best tested; the gain is not monotone past 30.

## Experiment 26: split-gain threshold
Exploration of a different regularizer after bracketing L2. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) say gamma requires a minimum loss reduction for each split. Hypothesis: gamma=1 prunes low-value interactions on sparse airport categories while preserving the broad patterns.
Result: 0.6861, tied, and artifact byte size was essentially identical (1,475,660 vs 1,475,659), so no real simplification. Discard. This is the third consecutive <0.001 discard; research before next change.

## Plateau research and experiment 27: winter wrap feature
The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses periodic calendar representations that remove year-boundary discontinuities, while noting trees often handle raw time features well. Here numeric month has a December-January split that a depth-three tree needs multiple branches to bridge. Hypothesis: a simple winter indicator (Dec-Feb) exposes a stable weather season with one split and fewer features than sine/cosine. Exploration of seasonal representation; no train-fitted statistics.
Result: 0.6855, down 0.0006, slower evaluation. Discard. A simple winter flag did not improve the seasonal representation.

I inspected total gain in the kept trained artifact: scheduled departure ~119k, origin ~71k, destination ~54k, month ~31k, carrier ~21k, weekday ~9k, day-of-month ~5k, origin-relative time ~5k, distance ~1k. Gain is only a training diagnostic, not a validation metric, but motivates a feature ablation.

## Experiment 28: remove distance
Ablation/simplification based on the low observed split gain. Hypothesis: distance is mostly redundant once origin and destination are represented; removing it may reduce noise and simplify the model. If AUC ties, smaller/faster code and model qualify under the keep rule.
Result: 0.6854, down 0.0007. Discard. Distance has modest training gain but still carries useful 2006 ranking information.

## Experiment 29: ablate origin schedule lookup under L2
Ablation/simplification of the only train-fitted group statistic. Its initial gain was just 0.0003 before L2 tuning; stronger regularization may make it redundant. Hypothesis: removing it at lambda 30 can preserve or improve AUC and cut per-row evaluation cost by several seconds.
Result: 0.6858, down 0.0003 despite reducing evaluation to 28.2s. Discard under strict AUC rule. Three consecutive small discards (winter, no distance, no schedule lookup) trigger a research pause.

## Plateau research and experiment 30: DART tree dropout
The [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) argues that later boosted trees can over-specialize and reports improved generalization with tree dropout; [XGBoost's DART tutorial](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/dart.html) documents rate_drop and skip_drop and warns training is slower. Hypothesis: modest dropout (rate_drop=0.1, skip_drop=0.5) reduces dependence on early 2005-specific trees and improves 2006 AUC. Try 400 depth-three rounds with the current features. This explores a different booster, rather than another near-duplicate parameter value.
Result: 0.6856, down 0.0005. Training rose to 44.6s and XGBoost warned that `booster=dart` is deprecated in 3.4.1. Discard; dropout did not pay off on this task.

## Synthesis after 30 experiments
Best remains 0.6861 at 9b694c7. L2 leaf shrinkage to 30 yielded two small but consistent gains; 50 and 100 reversed them. The origin schedule offset remains worthwhile after L2 and distance remains useful despite low training gain. Winter wrapping, DART, and the tested ablations failed. The feature set is fairly stable. Next prioritize averaging independent shallow models, because the remaining effects look smaller than individual-tree stochastic variation. If that fails, try interaction constraints and narrower feature transformations.

Research after 30: [scikit-learn's VotingClassifier documentation](https://scikit-learn.org/1.5/modules/generated/sklearn.ensemble.VotingClassifier.html) defines soft voting as averaging class probabilities, and its [ensemble guide](https://scikit-learn.org/1.1/modules/ensemble.html) describes averaging independent estimators for robustness. [XGBoost's random forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) also combines row/feature sampling with boosted forests. I will first test a transparent average of two independently seeded shallow XGBoost models.

## Experiment 31: two-seed soft vote
Exploration of an ensemble category. Hypothesis: independent 80% row samples yield different shallow trees; averaging their probabilities reduces stochastic variance without requiring new features or labels. Both models have the current best configuration, differing only in seed. Fit both on train and evaluate via a single soft-voting model saved by the harness.
Result: 0.6864 (+0.0003), training 3.1s, evaluation 31.8s. Kept. Seed averaging reduces small stochastic ranking errors.

## Experiment 32: third independent seed
Follow-up to successful two-seed vote. Hypothesis: adding a third independent 80%-row sequence further reduces variance. This changes only ensemble size, retaining equal votes and all per-model hyperparameters.
Result: 0.6866 (+0.0002), training 4.3s, evaluation 31.8s. Kept. Variance reduction continues but with a smaller increment.

## Experiment 33: five-seed vote
Follow-up to the two- and three-seed gains. Hypothesis: two additional independent models may capture remaining seed variance. Jump to five to test whether returns persist; if not, revert to three rather than random-walk seed choices.
Result: 0.6865, down 0.0001 and slower training (6.5s). Discard. Three seeds are the best tested ensemble size.

## Experiment 34: heterogeneous depth-two third vote
Follow-up to three-seed voting, based on the [scikit-learn ensemble guide](https://scikit-learn.org/1.1/modules/ensemble.html), which emphasizes diversity among averaged learners. Hypothesis: replacing one of the three depth-three members with a depth-two member reduces overfitted interactions while the other two retain detail. This is a structural ensemble change, not merely another seed.
Result: 0.6864, down 0.0002. Discard. The shallower third member added bias without compensating diversity.

## Experiment 35: heterogeneous depth-four third vote
Follow-up exploring the other direction of depth diversity. Hypothesis: two depth-three models preserve stable main effects while a depth-four member contributes selective interactions that averaging tempers. Replace only the third member's depth with four.
Result: 0.6863, down 0.0003. Discard. Heterogeneous depth in either direction did not beat three equal shallow voters. Three consecutive small discards (five seeds, depth two, depth four) trigger a research pause.

## Plateau research and experiment 36: prohibit direct route interactions
The [XGBoost interaction-constraint tutorial](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html) shows that feature groups can prevent spurious joint paths; the [scikit-learn ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) also describes limiting interaction structures. Route identity badly hurt AUC in experiment 6. Hypothesis: explicitly forbidding Origin and Dest on the same tree path improves cross-year generalization while retaining each airport's interactions with time, carrier, calendar and distance. Apply the same constraint to all three voters.
Result: 0.6857, down 0.0009. Discard. Some Origin-Dest paths apparently remain useful despite the explicit route category overfitting.

## Experiment 37: finer histogram bins
Exploration of split resolution. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) state that max_bin sets numeric split candidate resolution. Scheduled departure has 1,162 distinct HHMM values and dominates training gain. Hypothesis: 512 bins (versus default 256) allow better time thresholds while retaining the shallow, regularized structure. Keep all three voters consistent.
Result: 0.6862, down 0.0004. Discard. Finer time thresholds did not improve 2006 AUC.

## Experiment 38: coarser histogram bins
Follow-up in the opposite direction. Hypothesis: 128 bins smooth small scheduled-time variations and reduce sensitivity to the 2005 sample, while 512 made it worse. This isolates histogram resolution as a regularizer.
Result: 0.6862, down 0.0004. Discard. Both finer and coarser numeric histograms underperformed the default. Three consecutive small discards (route interaction constraint, 512 bins, 128 bins) trigger another research pause.

## Plateau research and experiment 39: Thanksgiving travel window
The [BTS holiday-delay report](https://transtats.bts.gov/HolidayDelay_Detail.asp) tracks flight delays around Thanksgiving, and [BTS holiday travel research](https://rosap.ntl.bts.gov/view/dot/6311/dot_6311_DS1.pdf) documents a large travel-volume change. On train.csv only, the Tuesday-to-Sunday Thanksgiving window has late rate 0.517 versus 0.455 in other November dates (in this balanced sample). Hypothesis: explicitly marking this moving holiday window lets shallow trees transfer it across 2005 and 2006 without memorizing exact dates. Compute fourth Thursday from each row's month/day/weekday; no year or external file lookup is needed.
Result: 0.6860, down 0.0006 and evaluation +7s. Discard. The 2005 Thanksgiving rate contrast did not translate into useful 2006 ranking.

## Experiment 40: Independence Day travel window
Exploration of a different holiday effect identified in train.csv: July 2-5 late rate is 0.510 versus 0.599 on other July dates. Hypothesis: a stable fixed-date summer holiday window may transfer better than the moving Thanksgiving window. One simple row-wise binary feature; this is distinct from experiment 39's moving-weekday feature.
Result: 0.6865, down 0.0001 with +3s evaluation. Discard. The strong 2005 July rate contrast was not enough for 2006 AUC.

## Synthesis after 40 experiments
Best remains 0.6866 at 28f8c07: three depth-three XGBoost voters, numeric month/day, origin schedule offset, and lambda 30. The three-seed vote helped more than adding untested holiday flags. Five seeds and mixed tree depths were worse. Direct Origin-Dest interaction restriction and changed histogram resolution were also worse. Seasonal event features visible in train may not transfer across years; next look for broader schedule representations, then test remaining model regularizers if time permits.

Research after 40 experiments: [UC Berkeley's flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies hourly scheduled-departure blocks as useful temporal features. [scikit-learn's time-feature example](https://scikit-learn.org/1.1/auto_examples/applications/plot_cyclical_feature_engineering.html) explains treating hour as a category to capture non-monotone daily patterns; trees often handle raw times, so this may still be redundant.

## Experiment 41: categorical departure hour
Exploration of a broader schedule representation. Hypothesis: adding the 24-level scheduled departure hour as a category lets a shallow tree group nonadjacent late-night and morning hours, while retaining precise HHMM for the strong daytime trend. All values come from the row's scheduled departure time; fixed 0-23 levels are shared by train and eval.
Result: 0.6862, down 0.0004 and slower evaluation. Discard. Raw scheduled time already captures enough hour structure.

## Experiment 42: boosted three-tree forest instead of soft vote
Exploration of the [XGBoost boosted-forest mechanism](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). Hypothesis: num_parallel_tree=3 averages three differently sampled trees at each boosting round, potentially delivering variance reduction like the three-model soft vote with a simpler single estimator. Keep subsample=0.8 so the parallel trees differ. If AUC ties, one XGBClassifier is a simplification.
Result: 0.6860, down 0.0006 despite simpler code. Discard. Averaging independently trained full ensembles is better than parallel-tree averaging here.

## Experiment 43: L1 leaf regularization within three-vote model
Exploration of a distinct leaf penalty after L2 was helpful. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) define reg_alpha as an L1 penalty, which can zero out weak leaf effects rather than merely shrinking all leaves. Hypothesis: reg_alpha=1 may suppress unstable sparse airport adjustments while retaining strong time and month effects. Apply to all three voters.
Plateau research before experiment 43: [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/latest/parameter.html) confirms L1 penalizes leaf weights and makes the model more conservative. This differs from the ineffective histogram and route-interaction changes; proceed with L1 before further tuning.
Result: 0.6869 (+0.0003), training 4.3s, eval 31.5s. Kept. Sparse leaf shrinkage helps beyond lambda 30.

## Experiment 44: stronger L1 at five
Follow-up to the L1 gain. Hypothesis: stronger sparsification may suppress more unstable local adjustments. Test reg_alpha=5 while retaining lambda 30 and all other settings.
Result: 0.6884 (+0.0015), a substantial gain. Kept. L1 leaf penalty clearly cuts harmful weak effects.

## Experiment 45: L1 at fifteen
Follow-up to the strong alpha-five gain. Hypothesis: further sparse-leaf suppression might continue helping this shifted dataset; test 15 before refining the range.
Result: 0.6874, down 0.0010. Discard. Alpha five is best; the optimum appears between one and fifteen.

## Experiment 46: L1 at eight
Targeted interpolation between alpha five (best) and fifteen (worse). Hypothesis: a moderate additional penalty may improve 2006 AUC without over-sparsifying as fifteen does.
Result: 0.6881, down 0.0003. Discard. Alpha five is the best tested in the upper bracket.

## Experiment 47: stronger row sampling under L1
Exploration of an interaction between successful L1 and row sampling. The current three-model vote already benefits from independent 80% samples. Hypothesis: 60% per tree creates more diverse voters and may improve averaged AUC while L1 protects against noisy small-sample splits. Change subsample only.
Result: 0.6882, down 0.0002. Discard. More aggressive row sampling weakens the ensemble slightly.

## Experiment 48: less aggressive row sampling
Follow-up in the opposite direction. Hypothesis: subsample=0.9 preserves more signal in each L1-regularized voter while still producing independent ensembles across seeds. This brackets 0.8 against the 0.6 decline.
Result: 0.6882, down 0.0002. Discard. Both 0.6 and 0.9 underperform 0.8 under L1; three small discards since alpha five warrant research before another change.

## Plateau research and experiment 49: minimum child Hessian under L1
[XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies min_child_weight as a separate control on tree complexity, and the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explains it limits low-Hessian child splits. Experiment 9 found weight 10 tied before L1 was introduced. Hypothesis: a moderate value of 5 in the current L1-regularized three-vote model may curb rare-airport splits while retaining enough detail. This is a new interaction with the successful penalty, not a repeat of experiment 9.
Result: 0.6885 (+0.0001), training 4.3s, evaluation 31.8s. Kept. Child-Hessian threshold helps slightly in combination with L1.

## Experiment 50: child weight ten under L1
Follow-up to experiment 49's small gain. Hypothesis: a higher threshold further suppresses rare-category leaves; weight ten tied in an earlier pre-L1 model but may be useful with today's configuration.
Result: 0.6882, down 0.0003. Discard. Moderate weight five beats ten.

## Synthesis after 50 experiments
Best is 0.6885 at c3b3a92. The main gains were numeric calendar values, depth-three slow boosting, L1/L2 regularization, and averaging three independently seeded models. The origin schedule offset and moderate child weight brought smaller gains. Exact holiday flags, route identity, alternative categorical and histogram settings, DART, and larger ensembles did not help. The best theory is that this small set of scheduled features supports broad, regularized patterns; extra local detail tends to fit 2005 noise. If time remains, test a different conservative split-randomization mechanism, then leave the best branch for holdout scoring.

Research after 50: [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguish column sampling at each node from the earlier per-tree sampling experiment; [XGBoost's random-forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) uses node-level sampling to diversify trees.

## Experiment 51: node-level column sampling
Exploration of split-level randomness in the three-vote model. Hypothesis: colsample_bynode=0.8 encourages different features at nearby tree nodes and complements 80% row sampling plus moderate child-weight and leaf penalties. Unlike experiment 10's colsample_bytree, this resamples for every split.
Result: 0.6876, down 0.0009. Discard. Per-node feature randomness hides too much of the strong time and airport signal, even with three voters.

## Final summary
Best Eval AUC: **0.6885** at commit **c3b3a92** (baseline 0.6743, gain +0.0142 across 51 post-baseline experiments). Kept model: numeric Month and DayofMonth; row-stable origin-relative scheduled departure offset fitted on train; soft vote of three independently seeded XGBoost classifiers, each with 400 depth-three trees, learning rate 0.05, subsample 0.8, L2 penalty 30, L1 penalty 5, and minimum child weight 5.

What worked: ordered calendar fields, shallower slower boosting, modest row sampling, label-free origin schedule context, L1/L2 leaf penalties, three-seed probability averaging, and a moderate child-Hessian threshold. What did not: high-cardinality route identity, categorical departure hour, holiday flags, DART dropout, stronger/weaker row sampling, altered histogram bins, direct route interaction constraints, and larger/mixed-depth voting ensembles. Several weak feature ablations also lost AUC under the strict keep rule.

Next: investigate new row-stable, label-free schedule summaries that capture airport and carrier operations without using row counts, or a more distinct secondary learner for blending. Treat gains below 0.001 cautiously when judging likely holdout transfer. The human-only holdout check remains untouched.
