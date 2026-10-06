# Research log — oct6

## Baseline — 8d9c760
Unchanged starter, Eval AUC 0.6743. Training 0.6 s, total run 31.7 s. The train table has 200,000 rows and no missing values. Calendar fields are strings prefixed `c-`; scheduled departure time is an integer HHMM value.

## Research before experiment 1
XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) recommend controlling complexity with depth, minimum child weight, and gamma, and reducing overfitting with row/column subsampling. Its [categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) documents partition-based category splits. A [flight-delay feature engineering study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies scheduled departure hour and carrier as informative; delay propagation often makes later departures riskier. These sources guide the first time-feature experiment and later regularization tests. Only schedule fields available at prediction time will be used.

## Experiment 1 — exploration
Hypothesis: HHMM as a plain number hides the actual spacing between times; converting it to minutes after midnight gives the tree a regular time scale. Add only that feature and retain the original for comparison.
Result: 0.6743, unchanged; discard because the extra feature adds complexity without improving AUC.

## Experiment 2 — exploration
Hypothesis: the default 100 trees at depth 6 may use capacity on unstable 2005-specific patterns. A longer, slower ensemble of depth-4 trees could generalize better to 2006. Based on XGBoost parameter tuning notes, reduce the step size to 0.05 and increase rounds to 400 while reducing tree depth to 4.
Result: 0.6789 (+0.0046); keep. Shallow, slower boosting is promising.

## Experiment 3 — follow-up
Hypothesis: at learning rate 0.05 the depth-4 model may still be undertrained after 400 trees. Extend to 600 trees, changing only the boosting duration.
Result: 0.6776; discard. More trees alone overfit the 2006 transfer or added unstable late-stage splits.

## Experiment 4 — follow-up
Hypothesis: reducing each tree to depth 3 will limit year-specific interactions while preserving the 400-round learning schedule that helped. This isolates tree depth relative to the last kept model.
Result: 0.6813 (+0.0024); keep. Reduced tree complexity is helping on 2006.

## Experiment 5 — follow-up
Hypothesis: the improved score at depth 3 suggests still simpler interactions may generalize better. Test depth 2 at the same boosting schedule to map the complexity boundary.
Result: 0.6768; discard. Depth 3 is better than both 2 and 4 in the present setup.

## Experiment 6 — exploration
Hypothesis: an ordinal day-of-year feature will let shallow trees capture smooth annual seasonality and holiday periods using fewer splits than separate month/day categories. Build it from per-row date fields and fixed non-leap offsets (both train and eval years are non-leap); leave existing categories in place.
Result: 0.6842 (+0.0029); keep. Explicit annual ordering helps the shallow model. The prior HHMM-to-minutes feature was a monotone transform of HHMM, which explains its lack of effect on tree splitting.

## Experiment 7 — exploration
Hypothesis: origin and destination jointly identify operational patterns that the depth-3 model may fail to learn through separate airport fields. Add a route category, with category levels fitted once on train, for all rows and row-by-row evaluation. The [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes its category-partitioning splits; high cardinality may overfit, so this is an empirical test.
Result: 0.6738; discard. The high-cardinality route interaction hurts 2006 AUC, likely because individual routes have sparse/unstable training evidence; it also slows row-wise evaluation.

## Experiment 8 — ablation/simplification
Hypothesis: after adding DayOfYear, separate Month and DayofMonth categories may encourage fragmented and year-specific splits. Remove those two model inputs while still using them in `prepare` to compute DayOfYear; retain DayOfWeek, which captures weekly cycles.
Result: 0.6846 (+0.0004); keep. This is both simpler and slightly better, and row-wise evaluation fell from 35.0 s to 27.4 s.

## Experiment 9 — exploration
Hypothesis: a larger minimum child weight will keep trees from fitting small, unstable subsets of 2005 flights, particularly airport/category splits. Test `min_child_weight=10` using the current simpler calendar representation. XGBoost tuning notes identify it as a primary complexity control.
Result: 0.6847 (+0.0001); keep. The gain is small at printed precision.

## Experiment 10 — follow-up
Hypothesis: because depth reduction and a weight of 10 both helped, a stronger `min_child_weight=30` may further suppress sparse leaves. This changes only the regularization strength.
Result: 0.6843; discard. Weight 10 is better than 30.

## Synthesis after 10 experiments
Best is 0.6847 at 0d2499f. Restricting tree depth from 6 to 3, replacing separate month/day categories with an ordinal day-of-year, and modest child-weight regularization helped. Depth 2 underfit; 600 trees at depth 4 and child weight 30 hurt. A 4,290-category route feature caused a large drop. Purely monotone recoding of departure time brought no gain. Current theory: simple, smooth calendar and time effects transfer better across years than detailed route interactions. Next I will try XGBoost's row/column sampling and categorical split controls, then revisit more structured interactions if needed.
## Research before experiment 11
Current [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend row and column subsampling as separate tools to reduce overfitting; the [parameter reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html) confirms `subsample` and `colsample_bytree` are available in `XGBClassifier`. An [airline feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes airport, carrier and departure-time effects, which fits the current modest-dimensional model. I will test row sampling first, then category splitting and selected feature interactions. The data is balanced, so there is no reason to change class weight.

## Experiment 11 — exploration
Hypothesis: sampling 80% of training rows for each tree will make individual trees less sensitive to 2005-specific noise and improve 2006 AUC. Keep all other settings fixed.
Result: 0.6852 (+0.0005); keep. Row sampling appears helpful.

## Experiment 12 — follow-up
Hypothesis: sampling 80% of features per tree may reduce reliance on a few possibly year-specific airport categories and complement row sampling. Test `colsample_bytree=0.8` while retaining the successful row sampling.
Result: 0.6856 (+0.0004); keep. Both sources of sampling help modestly.

## Experiment 13 — follow-up
Hypothesis: sampling adds noise to each boosting step, so the current 400 rounds may no longer be enough. Try 600 rounds at the same learning rate and sampled trees. This differs from experiment 3, which had no sampling and depth 4.
Result: 0.6856, tied but slower; discard under the keep rule. Extra rounds are not useful here.

## Experiment 14 — exploration
Hypothesis: XGBoost's default one-hot handling for very small categories may spend splits on isolated day-of-week or carrier labels. Force category partitioning with `max_cat_to_onehot=1`; [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes this option. The 3.4.1 installation predates the 3.5 default change, so this is a meaningful mode change.
Result: 0.6856, tied without a simplification; discard. Likely most active categories were already partitioned under the current default.

## Experiment 15 — exploration
Hypothesis: one-hot splits for airport categories will emphasize robust individual-airport effects instead of grouping sparse airports by potentially unstable fitted responses. Set `max_cat_to_onehot=300`, above the 283 origin/destination levels. This tests the opposite categorical split strategy from experiment 14.
Result: 0.6794; discard. Grouping airport categories is useful. The kept model's built-in feature importance ranks scheduled departure time far above all other features (~0.55 versus ~0.12 for day of year). This is a model diagnostic, not another metric.

## Experiment 16 — follow-up
Hypothesis: partitioning many airport categories is useful, but the default category split search may still fit fine-grained airport groups. Restrict `max_cat_threshold` to 16 to regularize those partitions; the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html) describes this as a category-split complexity control.
Result: 0.6800; discard. Airport grouping needs a wider partition search.

## Research before target-encoding experiment
The [scikit-learn TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) says fitting and then transforming the same training rows leaks targets, and recommends cross-fitting. The [CatBoost paper](https://arxiv.org/abs/1706.09516) explains the prediction shift from target statistics that include a row's own label. To satisfy the row-by-row `prepare` rule, I will deterministically assign each row to one of five folds from its schedule fields and use an origin-rate lookup fitted on the other four folds. Eval rows use the same fold rule and an out-of-fold lookup, so the feature has the same meaning in training and scoring. The lookup is smoothed toward the global train rate.

## Experiment 17 — exploration
Hypothesis: a smoothed historical delay rate for the origin airport can give shallow trees a useful continuous airport-risk signal without target leakage. Add only that feature, preserving the native airport category.
Result: 0.6854, below 0.6856; discard. The origin rate adds evaluation cost and little new information beyond native categorical splits.

## Experiment 18 — exploration
Hypothesis: additional L2 regularization of tree leaf weights will reduce year-specific probability extremes without restricting category split choices. Test `reg_lambda=10` against the default 1, keeping the sampled depth-3 model.
Result: 0.6857 (+0.0001); keep.

## Experiment 19 — follow-up
Hypothesis: stronger L2 shrinkage may further stabilize sparse categorical effects. Increase `reg_lambda` from 10 to 50, changing nothing else.
Result: 0.6861 (+0.0004); keep. Larger L2 regularization appears to help this year transfer.

## Experiment 20 — follow-up
Hypothesis: if the dominant time and airport effects still overfit, `reg_lambda=200` may improve transfer further; if not, it will reveal the regularization boundary. This is a fourfold increase from 50.
Result: 0.6863 (+0.0002); keep.

## Synthesis after 20 experiments
Best is 0.6863 at 7ad5c67. Row and column sampling each improved the sampled depth-3 model slightly. Large L2 penalties (10, 50, 200) improved step by step, indicating noisy/sparse leaf predictions across years. More boosting rounds tied but were slower at low L2. Changing native categorical partitioning in either direction was harmful or neutral. An explicitly cross-fitted origin target rate added no value. The next direction is to understand stronger shrinkage and test domain features that capture airport-time effects without sparse route categories.
## Research before experiment 21
The current [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) confirms L2 (`reg_lambda`) makes leaf scores more conservative, while `gamma` suppresses low-gain splits. The [monotonic-constraint tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) offers another way to encode a strong prior. The [flight feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies departure-time blocks and origin-specific congestion as useful. I will first finish the observed L2 trend, then test time structure and split penalties.

## Experiment 21 — follow-up
Hypothesis: L2 has helped through 200, so test a substantially stronger `reg_lambda=800` to identify whether conservative leaf scores still help. The stronger penalty may underfit with 400 trees, which would guide later round-count tests.
Result: 0.6857; discard. L2 200 is the best tested strength.

## Experiment 22 — exploration
Hypothesis: the stronger L2 penalty helps leaf values, but low-gain splits may still encode unstable detail. Add `gamma=1` to require each split to improve the training objective more substantially; leave `reg_lambda=200` in place.
Result: 0.6863, tied without simplification; discard. The small split penalty has no useful effect at printed precision. A read-only training summary shows delay rate climbing strongly from morning to about 20:00, then easing late at night; this motivates later time-shape experiments.

## Experiment 23 — follow-up
Hypothesis: `gamma=1` was too small to meaningfully suppress weak splits; try `gamma=5` to test a materially stronger split-gain threshold before abandoning that regularizer.
Result: 0.6865 (+0.0002); keep. A material split-gain threshold helps after L2 regularization.

## Experiment 24 — follow-up
Hypothesis: still stronger split pruning may help if most remaining fine splits are year-specific. Increase gamma from 5 to 15 while retaining all else.
Result: 0.6861; discard. Gamma 5 is better than 15.

## Experiment 25 — exploration
Hypothesis: depth 4 previously overfit, but row/column sampling, L2=200, and gamma=5 now regularize each split. Test depth 4 again in this meaningfully different regime to allow limited airport-time interactions without restoring the original overfit pattern.
Result: 0.6860; discard. Even with stronger penalties, depth 3 remains better.

## Experiment 26 — exploration
Hypothesis: departure delay risk mostly increases as the day progresses because delays propagate through rotations. The training hourly rates support this through about 20:00, with a late-night decline. Test an increasing monotonic constraint on `CRSDepTime`; the latter decline is a known risk to this experiment. [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) support feature-name constraints.
Result: 0.6857; discard. Strictly increasing time risk cannot represent the late-night decline, and/or it blocks useful interactions.

## Experiment 27 — exploration
Hypothesis: seasonality wraps between December and January, but ordinal DayOfYear places those days far apart. Add sine and cosine of DayOfYear to let shallow trees learn smooth cyclic seasonality while retaining DayOfYear for local date effects. Only the per-row calendar fields enter this transform.
Result: 0.6854; discard. The simple ordinal date feature remains better.

## Plateau research before experiment 28
The [XGBoost random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes boosting a small forest per round via `num_parallel_tree>1`, which averages randomly sampled trees at each stage and may reduce variance. The [feature-interaction constraint tutorial](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html) describes restricting unlikely interactions to reduce noise. The [scikit-learn ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) gives a related probability-averaging rationale. I will first test a small boosted forest, then structured interaction restrictions if needed.

## Experiment 28 — exploration
Hypothesis: averaging three independently sampled trees at each boosting round should lower sampling noise and give a more stable 2006 ranking. Set `num_parallel_tree=3` on the existing 400-round sampled model; training should remain below the one-minute limit.
Result: 0.6867 (+0.0002); keep. Three parallel trees per round improved AUC with training rising to 5.6 s, still well within the limit.

## Experiment 29 — follow-up
Hypothesis: a slightly larger forest per round may reduce tree-sampling variance further. Increase `num_parallel_tree` from 3 to 5 while keeping the same rounds and regularization.
Result: 0.6866; discard. Three trees per round is preferable.

## Experiment 30 — follow-up
Hypothesis: averaging three trees per round lowers per-round variance and, with L2=200, may need longer to fit stable patterns. Test 600 boosting rounds instead of 400; unlike experiment 13, this uses strong regularization and a forest each round.
Result: 0.6863; discard. The boosted forest does not need longer training.

## Synthesis after 30 experiments
Best is 0.6867 at 9bbcc68. A small forest of three sampled trees per boosting round broke the recent plateau. Five trees and 600 rounds were worse, so the gain is from modest averaging rather than raw model size. Tree depth 3, a day-of-year calendar feature, row/feature sampling, L2=200 and gamma=5 remain the strongest findings. Restricting time monotonically, adding cyclic seasonality, route categories, and cross-fitted origin target rates all failed. Next: test feature interaction priors and other ways to reduce noise while preserving the dominant scheduled-time effect.
## Research before experiment 31
A [R Consortium talk on this airline dataset](https://r-consortium.org/posts/gradient-boosting-machines-gbms-in-the-age-of-llms-and-chatgpt/szilard_GBM_LLM.pdf) reports feature engineering with half-hour departure slots. The [XGBoost interaction-constraint tutorial](https://xgboost.readthedocs.io/en/release_3.3.0/tutorials/feature_interaction_constraint.html) warns that unrestricted deeper trees can capture spurious interactions, and explains overlapping groups. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) identifies histogram bin count as another way to control numerical split granularity. I will test a categorical time-slot feature before interaction constraints and binning changes.

## Experiment 31 — exploration
Hypothesis: half-hour departure slots can model nonmonotone local peaks while sharing evidence among times in a slot. Add a 48-level categorical `DepSlot` derived from HHMM, retaining raw scheduled time for finer ordering. Only the row's schedule is used.
Result: 0.6869 (+0.0002); keep. Half-hour categories add a small gain, with row-wise evaluation about 5 seconds slower.

## Experiment 32 — ablation/simplification
Hypothesis: a coarser 24-level hourly category may preserve the time-block signal while requiring fewer category partitions and less row-wise work. Replace the 48 half-hour slots with 24 hourly slots.
Result: 0.6870 (+0.0001) and ~2 seconds faster; keep. Coarser blocks seem enough.

## Experiment 33 — follow-up/simplification
Hypothesis: the hourly category may still be too granular for the small per-hour early/late samples. Test 12 two-hour bins, halving categorical complexity again.
Result: 0.6869; discard. Hourly slots are the best tested time-block resolution.

## Experiment 34 — exploration
Hypothesis: the dominant raw departure-time feature has 1,162 distinct values, and the default 256 histogram bins may let trees chase narrow 2005-specific thresholds. Reduce `max_bin` to 64 to smooth numerical splits while retaining the hourly category. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) documents this bin control.
Result: 0.6870, tied and marginally slower; discard.

## Experiment 35 — exploration
Hypothesis: destination and distance contribute relatively weakly and their interactions with the dominant origin/time/calendar signal may be unstable across years. Use XGBoost interaction constraints to let `{Dest, Distance}` interact with each other, but keep them out of trees modeling time, origin, carrier and calendar. The [interaction-constraint tutorial](https://xgboost.readthedocs.io/en/release_3.3.0/tutorials/feature_interaction_constraint.html) documents the allowed-group semantics.
Result: 0.6861; discard. Destination/distance interactions with other fields matter more than expected.

## Plateau research before experiment 36
Recent three discards each moved less than 0.001 from the best. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) suggests L1 regularization (`reg_alpha`) as another conservative leaf penalty; it differs from the L2 and split-gain penalties tested so far. The [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes dropping prior trees to reduce overfitting but warns that training is slower, which is relevant to our 60-second limit. I will test L1 first, then consider DART only if there is room in the training budget.

## Experiment 36 — exploration
Hypothesis: a moderate L1 leaf penalty can set weak leaf contributions to zero, reducing unstable 2005 patterns that survive L2 and gamma. Add `reg_alpha=10` to the best model.
Result: 0.6875 (+0.0005); keep. Sparse leaf effects were still overfitting despite L2 and gamma.

## Experiment 37 — follow-up
Hypothesis: stronger L1 sparsity may suppress more unstable leaf values. Increase `reg_alpha` from 10 to 30 while retaining all else.
Result: 0.6857; discard. L1=10 is a useful moderate penalty, while 30 over-sparsifies.

## Experiment 38 — exploration
Hypothesis: level-wise depth-3 growth spends capacity evenly across branches. XGBoost's `lossguide` policy prioritizes the branches with the largest training gain, which may better capture a few strong airport/time subgroups without increasing maximum depth. Test this growth policy at the current depth and regularization. The [XGBoost Python reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html) documents both policies.
Result: 0.6875, tied but 0.8 s faster overall and 1.1 s faster training; keep under the speed exception. The gain is small enough that timing noise is possible.

## Experiment 39 — follow-up
Hypothesis: loss-guided growth could use the same eight-leaf budget more effectively if it can make deeper splits only on the most useful branches. Set `max_leaves=8`, remove the depth cap (`max_depth=0`), and retain `grow_policy="lossguide"`.
Result: 0.6882 (+0.0007); keep. Uneven tree depth is more useful than uniformly depth-3 trees with roughly the same leaf budget.

## Experiment 40 — follow-up
Hypothesis: useful airport/time branches may need more than eight leaves, while gamma and L1/L2 still constrain noisy splits. Increase the loss-guided leaf budget to 12, leaving other settings fixed.
Result: 0.6879; discard. Eight leaves is the stronger and faster configuration.

## Synthesis after 40 experiments
Best is 0.6882 at 5b71d1b. A moderate L1 penalty broke the prior plateau, and loss-guided eight-leaf trees then added another 0.0007. Stronger L1 and a 12-leaf budget reduced AUC. Hourly departure categories helped slightly; coarse numerical histograms and isolation of destination/distance interactions did not. The pattern remains that flexible but tightly regularized time and airport effects transfer best. Next I will research and test whether complementary models or alternative sampling can improve the ranking without loosening the successful structure.
## Research before experiment 41
The [scikit-learn ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) describes averaging diverse classifiers' probabilities as a way to balance their errors; that may be useful later. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says gradient-based row sampling is supported on CPU with histogram trees in recent versions, which applies to installed XGBoost 3.4.1. It prioritizes rows with larger regularized gradients instead of drawing all rows equally. I will test that sampling change before adding model-level complexity.

## Experiment 41 — exploration
Hypothesis: gradient-based sampling will focus boosted trees on flights the current model still predicts poorly while retaining the 80% row-sample regularization. Switch only `sampling_method` from uniform to gradient-based.
Result: 0.6878; discard. Gradient-prioritized rows seem to amplify year-specific hard cases and add training cost.

## Experiment 42 — follow-up
Hypothesis: stronger uniform row sampling could reduce dependence on particular 2005 flights in the loss-guided forest. Lower `subsample` from 0.8 to 0.6, retaining uniform sampling. The earlier 0.8 gain motivates this range test.
Result: 0.6876; discard. Subsample 0.8 remains the best tested value.

## Experiment 43 — exploration
Hypothesis: the current strongly regularized model may miss some useful rare interactions, while a second, less regularized loss-guided model may fit them but make different mistakes. Average their predicted probabilities with equal weight using scikit-learn's [soft VotingClassifier](https://scikit-learn.org/stable/modules/ensemble.html). The second model uses L2=50, no L1 or gamma, and a different seed; both train only on train.csv and share the same row-wise `prepare`.
Result: 0.6886 (+0.0004); keep. Complementary predictions outweighed the extra model cost (training 11.2 s, total 42.9 s).

## Experiment 44 — follow-up
Hypothesis: the heavily regularized component is individually strong, and the lighter model may be most useful as a correction. Increase its partner's weight by using a 2:1 blend (regularized:lighter) instead of 1:1, without changing either trained model.
Result: 0.6887 (+0.0001); keep. The lighter model helps, but the stronger model should dominate.

## Experiment 45 — follow-up
Hypothesis: if the lighter component mainly corrects a narrow subset, reducing its contribution further may help. Test a 3:1 regularized:lighter probability blend.
Result: 0.6886; discard. The 2:1 blend appears better than both 1:1 and 3:1 at printed precision.

## Experiment 46 — exploration
Hypothesis: `DayOfYear` models smooth seasonal changes, but a separate month category may give the blended models an efficient way to split by broad seasonal regimes. Reintroduce Month alone, leaving DayofMonth out. This isolates which calendar category caused the earlier two-column ablation gain.
Result: 0.6869; discard. The smooth ordinal day-of-year representation is preferable to a separate month category.

## Experiment 47 — ablation/simplification
Hypothesis: the two-model blend already averages predictions, so each component may need only two trees per boosting round rather than three. Reducing `num_parallel_tree` to 2 could preserve or improve AUC with smaller, faster artifacts.
Result: 0.6883; discard. Three trees per round remain useful even when blending two models.

## Experiment 48 — exploration
Hypothesis: the less regularized blend component is meant to supply complementary interactions. Increasing only its leaf budget from 8 to 12 may add useful cases while the stronger component limits overfit in the weighted average. The regularized component stays exactly as in the best commit.
Result: 0.6888 (+0.0001); keep. A somewhat more expressive secondary model adds complementary signal.

## Experiment 49 — follow-up
Hypothesis: the lighter component may benefit from further interaction capacity. Increase only its loss-guided leaf budget from 12 to 16; keep the regularized model and blend weights fixed.
Result: 0.6888, tied but slower; discard. Twelve leaves are enough for the secondary component.

## Experiment 50 — follow-up
Hypothesis: the 12-leaf lighter component might be too weakly regularized at L2=50. Test L2=100 for that component only, keeping its no-L1/no-gamma contrast with the primary model.
Result: 0.6888, tied but slower; discard.

## Synthesis after 50 experiments
Best is 0.6888 at eb00701. A 2:1 probability blend of strongly regularized eight-leaf and lighter twelve-leaf XGBoost models now improves over either simple forest configuration tested as the main model. The lighter model's larger leaf budget helped; further enlargement and higher L2 did not. Gradient-based row sampling and lower uniform row sampling reduced AUC. Reintroducing Month hurt. The next direction is to diversify split selection or model structure in a limited way, then leave the best kept commit and full experiment log when the hour expires.
## Research before experiment 51
The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) distinguishes sampling columns once per tree (`colsample_bytree`) from sampling at each split (`colsample_bynode`). The latter may diversify the current two-model ensemble by forcing some nodes to use secondary airport, carrier, and calendar signals instead of repeatedly selecting departure time. The [scikit-learn voting guide](https://scikit-learn.org/stable/modules/ensemble.html) supports averaging diverse model probabilities, while warning implicitly that complexity should be justified by a better result. I will test split-level feature sampling, then consider one additional complementary component if needed.

## Experiment 51 — exploration
Hypothesis: sampling 80% of features at each split will reduce the dominance of scheduled departure time and diversify both blended models. Add `colsample_bynode=0.8` while keeping the successful 2:1 blend and other parameters fixed.
Result: 0.6882; discard. Extra split-level feature sampling weakens the dominant signal too much.

## Experiment 52 — exploration
Hypothesis: depthwise and loss-guided trees make different structural errors. A third component using the prior depth-3 configuration could add diversity to the 2:1 blend of loss-guided models. Add a depthwise, strongly regularized XGBoost component with weight 1, yielding weights 2:1:1. The [scikit-learn soft-voting guide](https://scikit-learn.org/stable/modules/ensemble.html) supports probability averaging of differently structured classifiers.
Result: 0.6887; discard. A third depthwise component did not contribute enough to justify its cost.

## Experiment 53 — ablation/simplification
Hypothesis: distance is the least important input in the earlier tree importance diagnostic and may contribute noisy route proxies. Remove Distance from model inputs while preserving it in the source rows. This should simplify training and evaluation; keep only if AUC improves or ties with faster code.
Result: 0.6881; discard. Distance adds small but real ranking information.

## Experiment 54 — follow-up
Hypothesis: with L1/L2/gamma and an averaged forest, the current `min_child_weight=10` may suppress useful specific airport/time leaves. Lower it to 5 for both blend components, preserving other regularization.
Result: 0.6888, tied but slower; discard. A lower child-weight cutoff added no printed AUC.

## Plateau research before experiment 55
Three consecutive small or tied discards triggered another research pause. XGBoost's [current tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) and [parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) confirm that `min_child_weight` controls minimum Hessian mass in a leaf, complementary to L1/L2 and gamma. The lowered value did not help, so I will test a more conservative 20 before abandoning this branch. `max_delta_step` is mainly for extreme class imbalance, which this balanced dataset does not have.

## Experiment 55 — follow-up
Hypothesis: L2/L1 penalties regularize leaf scores, while a higher minimum child weight may suppress sparse airport/time partitions before they form. Increase `min_child_weight` from 10 to 20 in both blended models.
Result: 0.6888, tied but slightly slower; discard. The current cutoff of 10 is adequate.

## Experiment 56 — ablation/simplification
Hypothesis: 400 boosting rounds may include late corrections with little cross-year benefit; prior 600-round tests hurt. Try 300 rounds in both blended models. An equal AUC would justify keeping the faster, smaller artifact.
Result: 0.6886; discard. The shorter blend loses ranking quality.

## Experiment 57 — follow-up
Hypothesis: 300 rounds underfit while 400 works well; 500 may extract a little more stable signal in the blended models. This tests the opposite side of the 400-round setting. Earlier 600-round tests used different model configurations.
Result: 0.6889 (+0.0001); keep. More rounds helped the final blended model, despite added training and evaluation time.

## Final summary
Best Eval AUC: **0.6889** at **c4b427d** (baseline 0.6743, gain +0.0146). The final model averages two XGBoost forests 2:1: the primary uses eight loss-guided leaves, L1=10, L2=200, gamma=5; the secondary uses twelve leaves, no L1/gamma, and L2=50. Both use 500 rounds, row/column sampling, 3 parallel trees per round, an ordinal day-of-year, and an hourly departure category. The branch ends at the best kept commit.

What worked: shallower or leaf-limited trees, regularization, row/column sampling, an ordinal day of year, hourly departure blocks, modest boosted forests, and blending differently regularized models. What did not: sparse route categories, one-hot airport splits, separate month category, extra per-split sampling, cyclic seasonality, strict time monotonicity, cross-fitted origin target rates, and overly strong regularization or leaf budgets. Next, I would test whether other complementary feature representations add signal without sacrificing row-wise evaluation speed; the present run is complete.
