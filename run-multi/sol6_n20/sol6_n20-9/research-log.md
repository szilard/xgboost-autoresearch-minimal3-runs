# Research log — oct6

## Baseline — 8d9c760
Untouched starter: 100 trees, depth 6, learning rate 0.1, native categorical features. Eval AUC 0.6743; training 0.6s, evaluation 30.1s. The data has 200,000 balanced 2005 rows and eight predictors; month and weekday are stored as c-N strings. Eval and holdout are from 2006, so changes must survive year drift.

## Sources and initial reasoning
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): tree depth controls complexity; min_child_weight, subsampling and column sampling can regularize it; max_cat_to_onehot and max_cat_threshold control native categorical splits.
- [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): pandas categorical dtype is accepted by the histogram tree method; category mappings must be consistent at inference.
- [Berkeley flight delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): scheduled departure hour, carrier and airports are useful predeparture signals. Their target and data differ, so this motivates a test rather than an expected gain.

## Experiment 1 — clock parts (exploration)
Hypothesis: HHMM as one number hides minute-of-hour schedule patterns, while explicit hour and minute parts could capture them efficiently. Add both as numeric row features; keep other settings fixed.
Result: Eval AUC 0.6752 (+0.0009), 35.1s total. Keep. Minute-of-hour schedule patterns may add information beyond the HHMM number.

## Experiment 2 — 300 trees (follow-up)
Hypothesis: with learning rate 0.1, 100 trees may stop before the model captures carrier and airport interactions. The XGBoost parameter guide describes boosting rounds as incremental fitting; test 300 at fixed depth and features. More trees may instead overfit 2005 patterns that do not transfer to 2006.
Result: Eval AUC 0.6682 (-0.0070 against last keep). Discard. Longer fitting at depth 6 appears to overfit 2005 patterns that do not carry into 2006.

## Experiment 3 — shallower trees (exploration)
Hypothesis: reducing depth 6 to 3 constrains interactions and should improve year-to-year generalization. This follows the 300-tree overfit signal and [XGBoost's tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) on complexity control. Hold 100 trees and the kept clock features fixed.
Result: Eval AUC 0.6803 (+0.0051), artifact 0.3 MB, 34.8s. Keep. Strong gain supports limiting interaction complexity across the year boundary. Training-only inspection showed delay fraction rises sharply from early morning to evening; departure time is the dominant feature in the kept model's feature importance.

## Experiment 4 — 200 shallow trees (follow-up)
Hypothesis: depth 3 captures more stable patterns than depth 6, so 200 trees may add useful additive effects without the overfit of 300 depth-6 trees. Hold the learning rate and features fixed.
Result: Eval AUC 0.6810 (+0.0007), 34.6s. Keep. Shallow trees still benefit modestly from more rounds.

## Experiment 5 — 300 shallow trees (follow-up)
Hypothesis: another 100 depth-3 rounds could continue the gain from 100 to 200. This brackets the useful boosting duration before moving to different features or regularization. Hold all other choices fixed.
Result: Eval AUC 0.6803 (-0.0007). Discard. Useful boosting duration at depth 3 appears near 200 rounds, with longer fitting starting to lose year-to-year performance.

## Experiment 6 — day of year (exploration)
Hypothesis: month and day-of-month are separate categoricals, so a shallow tree may have trouble modeling smooth changes and holiday-adjacent weeks within the year. Add numeric day-of-year computed from the row's month and date, with fixed non-leap month offsets (both 2005 and 2006 are non-leap). [This flight-delay study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/) describes day-of-year and departure-hour features. Keep 200 depth-3 trees.
Result: Eval AUC 0.6832 (+0.0022), 38.8s. Keep. A smooth within-year coordinate adds useful information beyond separate month and day labels. The per-row map uses fixed offsets, so it has the same semantics at training and scoring.

## Experiment 7 — weekday by departure hour (exploration)
Hypothesis: at depth 3, splits on separate weekday and hour can use too much tree depth; a 168-level categorical interaction may represent recurring weekly schedule patterns directly. [XGBoost's categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes category partition splits; test that mechanism on a bounded, well-supported interaction.
Result: Eval AUC 0.6832 (equal), but evaluation rose to 42.2s and code grew. Discard under the equal-score simplification rule.

## Experiment 8 — departure relative to route schedule (exploration)
Hypothesis: a depth-3 tree cannot easily form origin-destination-specific schedule baselines. Fit the median scheduled departure minute for each directional route on train, then add each row's deviation from its route median. This uses no labels and applies unchanged to one-row scoring. [Berkeley's flight-delay feature work](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) motivates scheduled timing and airport context; the specific relative-time construction is our inference.
Result: Eval AUC 0.6832 (equal), eval 41.5s versus 37.3s for the best. Discard. Route-relative schedule signal did not add value beyond existing hour, origin, destination and distance features.

## Experiment 9 — minimum child weight 10 (exploration)
Hypothesis: the depth-3 model can still split rare airport or date categories into small leaves. Raising min_child_weight from 1 to 10 may regularize those leaves for transfer to 2006. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define it as the minimum child Hessian and say larger values are more conservative. Hold features, depth and rounds fixed.
Result: Eval AUC 0.6837 (+0.0005), eval 37.2s. Keep. Conservative leaves seem mildly helpful.

## Experiment 10 — minimum child weight 30 (follow-up)
Hypothesis: if suppressing small leaves helped at weight 10, weight 30 may further improve 2006 generalization. This tests the same regularization direction at a meaningfully stronger level; over-regularization is possible.
Result: Eval AUC 0.6836 (-0.0001). Discard. Weight 10 is the better point at printed precision.

## Synthesis after 10 experiments
Best is 0.6837 at ec501be, up from 0.6743 baseline. Shallower trees (depth 3) gave the largest single gain; 200 rounds worked better than 100 and 300 at this depth. Explicit clock parts, day of year and moderate child-weight regularization also helped. Weekday-hour and route-relative departure features tied the score while slowing per-row evaluation. Depth-6 300-tree fitting overfit badly. Current theory: stable, low-complexity time and schedule effects matter most across the 2005-to-2006 shift; fine-grained interactions can chase one-year noise.

Research pause: [XGBoost categorical docs](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) distinguish one-hot and partition splits; [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe max_cat_to_onehot and max_cat_threshold. [NVIDIA's categorical XGBoost article](https://developer.nvidia.com/blog/categorical-features-in-xgboost-without-manual-encoding/) notes the threshold's role in controlling categorical overfit. Next direction: compare categorical split strategies, then test smoother boosting and row/column subsampling. Target statistics warrant leakage-safe cross-fitting per [scikit-learn's TargetEncoder docs](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html), but that would conflict with this run's no-cross-validation rule, so they are not planned.
## Experiment 11 — one-hot splits for low-cardinality categories (exploration)
Hypothesis: the default max_cat_to_onehot=4 partitions month, weekday, day-of-month and carrier into data-driven groups. That flexibility may overfit a single year. Raising it to 32 makes these categories use one-vs-rest splits while origins and destinations still use partitioning, testing a simpler categorical structure. Installed XGBoost config confirms the default is 4.
Result: Eval AUC 0.6819 (-0.0018). Discard. Partition splits for month, weekday and carrier work better than one-vs-rest splits at the same tree budget.

## Experiment 12 — cap category split search at 16 (follow-up)
Hypothesis: keep beneficial partitioning but limit high-cardinality origin/destination split candidates. Reducing max_cat_threshold from 64 to 16 may suppress unstable rare-airport partitions across years. All other model settings stay at the kept values.
Result: Eval AUC 0.6798 (-0.0039). Discard. The tighter cap discards useful airport-category structure.

## Experiment 13 — expand categorical split cap to 128 (follow-up)
Hypothesis: the failure at 16 suggests the default 64 may still omit useful airport groups. Raise max_cat_threshold to 128 while retaining native partitioning and current regularization; this tests the opposite side of the default.
Result: Eval AUC 0.6826 (-0.0011). Discard. Both 16 and 128 underperformed the default cap of 64; categorical partitioning at the default is adequate.

## Experiment 14 — smaller boosting steps (exploration)
Hypothesis: 400 rounds at learning rate 0.05 might generalize better than 200 rounds at 0.1 despite a similar overall update budget. [XGBoost's tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend pairing a smaller eta with more rounds for robustness. Hold tree structure and features fixed.
Result: Eval AUC 0.6839 (+0.0002), 39.3s. Keep. Smaller steps yield a marginal ranking gain at similar total update budget.

## Experiment 15 — still smaller steps (follow-up)
Hypothesis: 800 rounds at learning rate 0.025 may further smooth the fitted function while keeping approximately the same aggregate shrinkage as 400 at 0.05. This probes whether the gain from experiment 14 continues or saturates.
Result: Eval AUC 0.6836 (-0.0003), 41.2s. Discard. The gain from smaller steps did not continue at 800 rounds.

## Experiment 16 — remove unused minute feature (ablation/simplification)
Hypothesis: DepMinute has zero importance in the kept 400-tree model, so deleting it may preserve AUC while reducing the row-by-row preparation work and model inputs. Keep only if the printed AUC is equal or higher.
Result: Eval AUC 0.6839 (equal), eval time 35.9s versus 37.3s, one less feature. Keep as a simplification.

## Experiment 17 — carrier by origin category (exploration)
Hypothesis: a carrier's reliability at a particular departure airport can differ from its national average; a direct categorical interaction may help the shallow model learn station-level effects. The training data has 1,551 carrier-origin combinations, so this is more supported than a full carrier-route key. The [Berkeley flight delay work](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies carrier and airport as separate predeparture signals; the interaction is our test.
Result: Eval AUC 0.6779 (-0.0060), eval 43.3s. Discard. High-cardinality station interaction overfit or distracted the shallow model. Pandas also warned on unseen category values at eval, though the run completed.

## Experiment 18 — month by departure hour (exploration)
Hypothesis: seasonal weather and travel patterns can alter how delay risk rises through the day. A 288-level month-hour category is far denser than carrier-origin and may let shallow trees capture that interaction. [Berkeley's feature work](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports seasonal and hourly timing as useful predictors; this interaction is our inference.
Result: Eval AUC 0.6810 (-0.0029), eval 41.3s. Discard. Month-hour category did not improve on separate month, departure time and day-of-year features.

## Experiment 19 — row subsampling at 0.8 (exploration)
Hypothesis: drawing 80% of rows per tree may average away noisy 2005-specific patterns while retaining the stable schedule signal. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) list subsample as a way to control overfitting by adding randomness. Keep features and other settings fixed.
Result: Eval AUC 0.6831 (-0.0008), eval 35.9s. Discard. Row sampling did not improve transfer.

## Experiment 20 — column subsampling at 0.8 (exploration)
Hypothesis: CRSDepTime dominates feature importance, so selecting 80% of features per tree could force some trees to learn complementary airport, carrier and calendar effects, helping ensemble ranking. This is distinct from row subsampling and follows the [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) on randomness.
Result: Eval AUC 0.6839 (equal) and essentially equal eval time, with added code. Discard.

## Synthesis after 20 experiments
Best is 0.6839 at 2d2332c (+0.0096 over baseline). The depth-3 model with 400 rounds at rate 0.05, child weight 10, day of year and departure hour has held up best. Removing an unused minute feature preserved score and sped evaluation. Both tighter and looser categorical thresholds, one-hot categories, row sampling and column sampling failed to improve. Manually constructed category interactions (weekday-hour, month-hour, carrier-origin) added cost and usually reduced AUC. Current theory: simple, stable calendar and schedule signals transfer across years; high-cardinality interactions add noise.

Research pause: [BTS holiday flight delays](https://www.transtats.bts.gov/holidayDelay.asp?pn=1) gives travel-season windows for 2005 and 2006, offering broad calendar features without flight outcomes. [XGBoost interaction constraints](https://github.com/dmlc/xgboost/blob/master/doc/tutorials/feature_interaction_constraint.rst) offers another way to limit unstable cross-feature patterns. [XGBoost random forest docs](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describe boosted forests as a later diversification option. Next test broad holiday windows, then structural model regularization and an ensemble if gains plateau.

## Experiment 21 — major holiday travel windows (exploration)
Hypothesis: unusually dense holiday travel can change departure delay risk within months, and depth-3 trees may not isolate these short periods easily. Add binary windows for winter holidays, Thanksgiving and Independence Day using day of year. Windows cover both 2005 and 2006 industry travel seasons from BTS and depend only on each row's date.
Result: Eval AUC 0.6839 (equal), but eval 42.4s versus 35.9s and more code. Discard. Holiday windows appear redundant with month/day-of-year in this setup.

## Experiment 22 — depth 2 with smooth boosting (exploration)
Hypothesis: depth 3 was much stronger than depth 6 across the year boundary, so depth 2 might further remove noisy interactions. Test it at the kept 400 rounds and rate 0.05. If it is close, it may be a diverse ensemble component later.
Result: Eval AUC 0.6812 (-0.0027). Discard. Depth 2 loses useful interactions; depth 3 is the better complexity level.

## Experiment 23 — average two tied XGBoost variants (exploration)
Hypothesis: the kept full-column model and the 0.8-column model each scored 0.6839 but may rank different rows incorrectly. Train both on the same train.csv and average their predicted probabilities, following [scikit-learn's soft voting definition](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). No extra data or evaluation is used. Keep only if the blended AUC rises despite model complexity.
Result: Eval AUC 0.6842 (+0.0003), 39.2s. Keep. The two tied individual models had complementary predictions enough to improve ranking when averaged.

## Experiment 24 — add row-sampled model to ensemble (follow-up)
Hypothesis: row subsampling alone lost only 0.0008 AUC but may make different errors. Add it as a third equally weighted model to the successful two-model blend. The training set and features stay identical for all members.
Result: Eval AUC 0.6843 (+0.0001), 40.4s. Keep. The third variant adds a tiny ranking gain; further ensemble changes should require a clear reason.

## Experiment 25 — histogram bin cap 128 (exploration)
Hypothesis: default max_bin=256 may permit excessively fine split positions on CRSDepTime and day of year. The [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) say max_bin controls continuous-feature quantization. Halving it may smooth splits and improve year-to-year transfer. Apply to all three ensemble members.
Result: Eval AUC 0.6844 (+0.0001), 41.0s. Keep. Coarser continuous split candidates help slightly.

## Experiment 26 — histogram bin cap 64 (follow-up)
Hypothesis: if 128 bins helps by smoothing time and calendar splits, 64 bins may help further. This deliberately brackets the useful time resolution; too few bins may erase schedule structure.
Result: Eval AUC 0.6840 (-0.0004). Discard. 128 bins retained useful resolution while smoothing relative to the default 256.

## Experiment 27 — categorical departure hour (exploration)
Hypothesis: the existing numeric DepHour enforces adjacent-hour split groups, while some risk patterns may be nonmonotone (early morning, evening peaks). XGBoost's categorical partitions can group similar hours directly. Replace only DepHour with a fixed 24-level category; retain the raw HHMM numeric feature for continuous ordering.
Result: Eval AUC 0.6837 (-0.0007), eval 37.7s. Discard. Numeric hour plus raw HHMM serves this dataset better and scores faster.

## Experiment 28 — stronger L2 leaf regularization (exploration)
Hypothesis: shrinking leaf scores can reduce sensitivity to noisy 2005 airport/date patterns. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) define reg_lambda as the L2 leaf-weight penalty. Raise it from default 1 to 10 across ensemble members, holding structure fixed.
Result: Eval AUC 0.6844 (equal) with unchanged speed and extra parameter. Discard.

## Experiment 29 — remove day-of-month category (ablation/simplification)
Hypothesis: DayofMonth can fit date-specific 2005 noise, while DayOfYear and Month retain seasonal position. The holiday-window test tied at extra cost, suggesting precise date effects may add little beyond existing calendar features. Remove only the categorical DayofMonth input; keep using it to compute DayOfYear.
Result: Eval AUC 0.6842 (-0.0002), eval 32.5s. Discard under the strict keep rule despite the speed gain. Day-of-month adds a small but measurable ranking signal.

## Experiment 30 — split gain threshold 2 (exploration)
Hypothesis: the ensemble still fits marginal 2005-specific splits. Set gamma=2 to require a minimum objective improvement before each split, following the [XGBoost parameter definition](https://xgboost.readthedocs.io/en/stable/parameter.html). This regularizes tree structure differently from the L2 setting that tied.
Result: Eval AUC 0.6846 (+0.0002), 40.4s. Keep. Pruning low-gain splits helped slightly, whereas stronger L2 leaf shrinkage only tied.

## Synthesis after 30 experiments
Best is 0.6846 at 348d81c (+0.0103 over baseline). The most important gains came from depth 3, day of year, and a smooth 400-round learning schedule. Averaging full-feature, column-sampled and row-sampled models gave small additional gains, followed by 128 histogram bins and gamma=2. Engineered high-cardinality interactions and categorical hour hurt. The day-of-month ablation lost a little AUC despite faster scoring. Current theory: stable schedule and geography effects are useful, but direct fine-grained categories overfit the 2005 sample; regularized numeric spatial features may offer a better route to new information.

Research pause: [Berkeley's flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) includes origin/destination coordinates as spatial predictors. [Classical MDS research](https://arxiv.org/abs/2303.05682) explains reconstructing low-dimensional coordinates from a pairwise distance matrix. We can infer an approximate airport embedding from the route distances already in train.csv, with no external flight outcomes or new files. This is an inference from those sources; the embedding may be distorted by missing direct routes. Next experiment tests it.

## Experiment 31 — airport coordinates inferred from routes (exploration)
Hypothesis: origin and destination category codes may not let a depth-3 tree share geographic information across airports. Fit a two-dimensional airport embedding from training route distances using shortest paths to fill missing pairs and classical MDS, then look up coordinates for each row. All lookups are fitted on train.csv and reused row by row; the label is not used.
Result: Eval AUC 0.6845 (-0.0001), eval 45.8s. Discard. All four inferred coordinates had zero importance in the first ensemble member; the category codes already conveyed what this embedding could offer.

## Experiment 32 — gamma 5 (follow-up)
Hypothesis: gamma=2 improved the three-model ensemble, so requiring still larger split gains may further prune year-specific noise. Raise gamma to 5 with all else fixed. If it loses AUC, retain gamma=2.
Result: Eval AUC 0.6845 (-0.0001). Discard. Gamma=2 gives a better balance than gamma=5 at printed precision.

## Experiment 33 — grouped feature interactions (exploration)
Hypothesis: the model may overfit interactions among 2005-specific locations, calendar dates and departure times. Constrain trees to three interpretable groups: intraday schedule and weekday; annual calendar; airline/airport/distance. [XGBoost's official interaction constraint tutorial](https://github.com/dmlc/xgboost/blob/master/doc/tutorials/feature_interaction_constraint.rst) supports named feature groups. This tests a more additive function across groups while retaining interactions within each group.
Result: Eval AUC 0.6798 (-0.0048). Discard. Cross-group interactions are important; an additive separation is too restrictive despite the gain from shallower trees.

## Experiment 34 — loss-guided eight-leaf trees (exploration)
Hypothesis: depthwise growth spends leaves evenly, while the dominant departure-time effect may benefit from allocating more splits to high-gain branches. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe grow_policy=lossguide and max_leaves. Allow no fixed depth limit but cap each tree at eight leaves, matching the maximum leaf count of a depth-3 tree with a different shape.
Result: Eval AUC 0.6836 (-0.0010). Discard. Balanced depthwise trees perform better than eight-leaf loss-guided trees for this feature set.

## Experiment 35 — L1 leaf-weight penalty (exploration)
Hypothesis: L1 regularization can zero small leaf effects that vary between 2005 and 2006. Unlike L2=10, which tied, reg_alpha=1 may produce sparse corrections in the three-model ensemble. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) identify reg_alpha as the L1 penalty on leaf weights.
Result: Eval AUC 0.6843 (-0.0003). Discard. L1 leaf shrinkage does not help beyond gamma pruning and child-weight regularization.

## Experiment 36 — remove flight distance (ablation/simplification)
Hypothesis: Distance has roughly 1–2% gain importance in the kept trees and may be redundant with origin/destination categories. Removing it may preserve AUC while reducing preparation work and simplifying the model. Apply to all ensemble members.
Result: Eval AUC 0.6838 (-0.0008). Discard. Distance contributes despite low global importance.

## Experiment 37 — average raw margins (exploration)
Hypothesis: averaging XGBoost raw margins (log odds) rather than their sigmoid-transformed probabilities may preserve complementary ranking signals better. [XGBoost prediction docs](https://xgboost.readthedocs.io/en/stable/prediction.html) define output_margin; logit averaging is a logarithmic opinion pool rather than the current linear probability pool. Keep the same three fitted members and change only the combine rule.
Result: Eval AUC 0.6846 (equal) and unchanged timing, with more code. Discard.

## Experiment 38 — cyclic annual date (exploration)
Hypothesis: numeric DayOfYear puts December and January at opposite ends of a line, although their weather and travel patterns can be similar. Add sine and cosine of the annual phase while keeping raw DayOfYear. [This flight-delay study](https://www.mdpi.com/2226-4310/8/6/152) uses trigonometric time features, and [scikit-learn's time feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains the continuous year boundary. Test whether shallow trees use this geometry.
Result: Eval AUC 0.6829 (-0.0017), eval 39.4s. Discard. Calendar category and DayOfYear already represent the useful annual structure for these trees.

## Experiment 39 — gamma 1 between tested values (follow-up)
Hypothesis: gamma=0 scored 0.6844, gamma=2 scored 0.6846, and gamma=5 scored 0.6845 with the same ensemble. Gamma=1 may prune enough low-gain splits while preserving ones that gamma=2 removes. Test this midpoint once to bracket the local setting.
Result: Eval AUC 0.6844 (-0.0002). Discard. Gamma=2 is better than both 1 and 5 with this ensemble.

## Experiment 40 — add a regularized depth-4 ensemble member (exploration)
Hypothesis: depth-3 members may miss stable higher-order effects. A depth-4 model with child weight 20 can capture some while limiting small leaves; averaging its predictions with the three kept depth-3 members may reduce its variance. [scikit-learn soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) formalizes probability averaging. This tests a diverse tree structure without changing data or scoring.
Result: Eval AUC 0.6846 (equal), larger artifact and more training, with no model simplification. Discard.

## Synthesis after 40 experiments
Best remains 0.6846 at 348d81c (+0.0103 over baseline). Over the last ten experiments, only gamma=2 improved AUC. Inferred airport geography had zero importance; interaction constraints hurt, showing cross-feature effects matter. Loss-guided growth, L1 penalty, cyclic annual date, margin averaging and adding a deeper member all failed. Distinct sample variants still help a little as a three-model average. Current theory: most available information is already captured, so further gains may come from how the ensemble samples and combines stable trees rather than more raw features.

Research pause: [NVIDIA's Kaggle modeling article](https://developer.nvidia.com/blog/the-kaggle-grandmasters-playbook-7-battle-tested-modeling-techniques-for-tabular-data) discusses seed ensembling and probability averaging; [XGBoost's boosted forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) documents num_parallel_tree with boosting. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) also suggests min_child_weight and regularization for additional variance control. Next test adds a differently seeded stochastic member, then explores boosted trees with multiple parallel trees.

## Experiment 41 — fourth stochastic seed (follow-up)
Hypothesis: the three kept models differ by row or column sampling, but all use seed 42. A fourth model with both row and column sampling at 0.8 and a different seed may reduce sample-path variance. Average it equally with the three kept members. Keep only if AUC rises.
Result: Eval AUC 0.6845 (-0.0001). Discard. Another stochastic seed did not improve the three-model average.

## Experiment 42 — boosted forest as fourth member (exploration)
Hypothesis: several parallel, sampled trees per boosting round may capture more stable alternate splits than a single sampled tree. [XGBoost's random forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) explicitly describes combining num_parallel_tree with multiple rounds. Add one 200-round, three-parallel-tree member with 0.8 row and split-level column sampling to the kept ensemble.
Result: Eval AUC 0.6845 (-0.0001), 42.9s. Discard. The boosted forest did not diversify the average enough to help.

## Experiment 43 — child weight 20 (follow-up)
Hypothesis: child weight 10 helped the earlier single model, while 30 slightly lost AUC. With gamma=2, 128 bins and the three-member average, the best weight could shift. Test 20 as a single deliberate midpoint across all members.
Result: Eval AUC 0.6844 (-0.0002). Discard. Child weight 10 remains better in the current ensemble.

Plateau research: several added ensemble members and nearby regularization choices have tied or slipped by <0.001. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes CPU histogram gradient-based row sampling in newer versions, selecting cases based on gradient magnitude rather than uniformly. Installed XGBoost is 3.4.1, so this method is available. It is a meaningfully different way to choose training rows, though harder cases may be noisier across years.

## Experiment 44 — gradient-based row sampler (exploration)
Hypothesis: the current uniform row-sampled ensemble member may waste its 80% draw on easy flights. Replace only that member with 50% gradient-based sampling under hist trees; keep the full-data and column-sampled members unchanged. This asks whether emphasizing difficult cases adds complementary ranking information.
Result: Eval AUC 0.6840 (-0.0006), training 4.3s. Discard. Emphasizing hard examples did not transfer well to 2006.

Further plateau research: [XGBoost's DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and the [original DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) describe dropping earlier trees during training to prevent later-tree overspecialization. The guide warns that training can be slower. A small DART member may offer a different error profile while keeping the main ensemble intact.

## Experiment 45 — DART dropout ensemble member (exploration)
Hypothesis: a dropout-trained depth-3 model may make complementary errors to ordinary boosted trees on 2005-specific patterns. Add one 200-round DART model with rate_drop 0.05 and skip_drop 0.5 to the three kept members, then average probabilities. Training remains on train.csv only.
Result: Eval AUC 0.6846 (equal), training 15.4s versus about 3.2s and more code. Discard. DART did not repay its cost here.

## Experiment 46 — column sampling at each node (exploration)
Hypothesis: the ensemble's second member currently samples 80% of columns once per tree. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes colsample_bynode, which resamples at every split. This may maintain more flexible trees while still diversifying split selection. Replace only that member's bytree sampling with bynode=0.8.
Result: Eval AUC 0.6844 (-0.0002). Discard. Per-tree column sampling is the better diversity mechanism for the second member.

## Experiment 47 — child weight 5 (follow-up)
Hypothesis: child weight 10 beat default 1 in the earlier single model, while 20 and 30 lost under tested setups. A weight of 5 may retain useful category detail while still regularizing rare leaves, especially with gamma=2 and the three-member average. This tests the untried lower side once.
Result: Eval AUC 0.6843 (-0.0003). Discard. Lighter child-weight regularization underperforms.

## Experiment 48 — 500 boosting rounds (follow-up)
Hypothesis: the best gamma=2 three-member ensemble may gain useful later small corrections beyond 400 rounds. Test 500 with all other settings fixed.
Result: Eval AUC 0.6846 (equal), training 3.8s vs about 3.2s with a larger model. Discard.

Plateau research: [scikit-learn TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) explains smoothed category means and warns of leakage without cross-fitting. I will test high-support, strongly smoothed airport/carrier means as fixed train-derived lookups; sparse categories fall back to the global prior, limiting self-inclusion. The feature is row invariant at evaluation.

## Experiment 49 — smoothed airport and carrier delay priors (exploration)
Hypothesis: tree splits on categories may not efficiently capture a stable ranking of airports and carriers by delay risk. Add fixed, train-derived delay rates for Origin, Dest, and UniqueCarrier, with 100 prior observations of shrinkage and global-prior fallback below 100 real observations. This follows the categorical encoding source above while limiting leakage from rare groups.
Result: Eval AUC 0.6843 (-0.0003), and evaluation 42.2s versus about 36s. Discard. The fixed historical priors add cost without enough generalization.

## Experiment 50 — 300 rounds in the gamma-regularized ensemble (ablation)
Hypothesis: gamma=2 prunes marginal splits, and the ensemble may reach its best ranking by 300 rounds. The 500-round trial tied at higher cost; 300 might preserve AUC with smaller and faster models.
Result: Eval AUC 0.6844 (-0.0002); training fell to 2.4s and artifact to 3.0 MB, but the keep rule requires an equal or better AUC. Discard.

## Synthesis after 50 experiments
The gains came from shallower depth-3 trees, 200 to 400 boosting rounds, DayOfYear and DepHour, min_child_weight=10, a three-member average using column and row sampling, max_bin=128, and gamma=2. The 400-round ensemble at 0.6846 remains best. Longer and shorter boosting runs, extra tree members, stronger or weaker child weights, categorical interactions, calendar embellishments, geographic inference, and smoothed delay priors did not improve the reported AUC. Recent [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) and [airport time-profile research](https://www.nature.com/articles/s41598-024-68884-9) point to operational schedule and capacity features as possible future directions, but the available balanced sample is insufficient for a reliable traffic-count feature.

## Final summary
Best Eval AUC: 0.6846 at commit 348d81c on branch oct6, versus starter baseline 0.6743 (+0.0103). Fifty non-baseline experiments were run and recorded in results.tsv. The kept model uses train-only row-invariant DayOfYear and DepHour features and averages three gamma-regularized XGBoost classifiers; its evaluation artifact was saved by the harness. Further work could use externally supplied historical schedules, weather, and congestion data if available, or test a clearly new model family on the same permitted inputs. No holdout result was inspected.
