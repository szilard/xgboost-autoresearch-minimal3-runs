# Research log — oct5

## Baseline — 8d9c760

Unchanged starter model: 100 XGBoost trees, depth 6, learning rate 0.1, native categorical features. Eval AUC: 0.6743. Training and evaluation completed within the limits. Subsequent experiments use this as the initial kept result.

## Research before experiment 1

The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/release_3.0.0/tutorials/param_tuning.html) recommends balancing tree complexity against overfitting through depth, child weight, sampling, and learning rate. Its [parameter guide](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) explains categorical partitions and the main tree controls. [Berkeley's flight delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes scheduled time, carrier, and airport patterns. This dataset contains only predeparture schedule fields, so no realized delay or weather feature will be used.

## Experiment 1 — decoded scheduled departure time

Exploration. Hypothesis: HHMM as an integer distorts time spacing at hour boundaries, whereas minute of day and scheduled hour make temporal effects easier for trees to learn. Keep the original time and add both derived features. Compare against 0.6743.

Result: 9a2b5ef, Eval AUC 0.6751 (+0.0008), kept. Evaluation time rose to 35.0 s.

## Experiment 2 — partition categorical values

Follow-up to the documented categorical handling. [XGBoost's categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) says `max_cat_to_onehot=1` forces partition-based splits. Hypothesis: grouping airports or carriers with similar delay tendencies in a split should use sparse categories more efficiently than singleton tests. Change only that threshold.

Result: b6727d3, Eval AUC 0.6751, discarded because it tied without simplifying or speeding up. Reset to 9a2b5ef.

## Experiment 3 — more boosting rounds

Exploration. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_3.0.0/tutorials/param_tuning.html) notes the interaction of learning rate and boosting rounds. Hypothesis: 100 rounds at 0.1 may leave useful signal uncaptured; test 300 rounds with all else held fixed. Watch for worse 2005-to-2006 transfer from overfitting.

Result: 5833849, Eval AUC 0.6674, discarded. The large drop suggests the current trees overfit the year shift as rounds accumulate.

## Experiment 4 — fewer boosting rounds

Follow-up to experiment 3. Hypothesis: 50 rounds should reduce overfitting relative to 100 while retaining the dominant schedule signal. Test 50 trees with depth 6 and learning rate 0.1 unchanged.

Result: 7df6ee8, Eval AUC 0.6766 (+0.0015), kept. Stronger generalization with half as many trees.

## Experiment 5 — 25 boosting rounds

Follow-up to experiments 3 and 4. Hypothesis: the AUC improvement at 50 rounds and deterioration at 300 imply an early optimum, possibly before 50; halve to 25 to locate the useful range. This differs materially from the previous tests by probing the underfitting boundary.

Result: a607d99, Eval AUC 0.6770 (+0.0004), kept. The gain is smaller than the 100-to-50 change, but the direction is consistent.

## Experiment 6 — shallower trees

Exploration of a different complexity control. [XGBoost parameters](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) describe depth as controlling interaction complexity and overfitting. Hypothesis: depth 4 will retain major schedule, airport, and carrier patterns while reducing idiosyncratic category interactions from 2005. Hold 25 rounds fixed.

Result: 99b4b41, Eval AUC 0.6747, discarded. Simpler trees lost useful interactions even with only 25 rounds.

## Experiment 7 — route category

Exploration of schedule-based interaction features. [Flight delay research](https://link.springer.com/article/10.1007/s44196-025-00932-2) uses origin-destination pairs, and [XGBoost categorical guidance](https://xgboost.readthedocs.io/en/release_3.0.0/tutorials/categorical.html) supports consistent categorical encoding. Hypothesis: a route identity captures directional, airport-pair-specific patterns that separate origin and destination splits may miss in 25 trees. Fit 4290 route levels on train only, then map each row to this fixed category set.

Result: 770f0dc, Eval AUC 0.6710, discarded. Route identity appears too sparse or costly for this small boosted model; evaluation increased to 47.4 s.

## Experiment 8 — ordinal day of year

Exploration of calendar representation. The [Berkeley flight delay study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) highlights seasonal timing as a predictive factor. Hypothesis: a continuous day-of-year feature lets the trees express adjacent seasonal periods more efficiently than separate categorical month and day-of-month splits. Month/day strings are mapped by fixed calendar constants, identically for training and single-row evaluation.

Result: 146bc7e, Eval AUC 0.6784 (+0.0014), kept. This is the largest gain since changing the number of trees.

## Experiment 9 — cyclic season encoding

Follow-up to the useful day-of-year feature. [Scikit-learn's time feature engineering guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses sine/cosine and periodic season encodings, while noting that trees can already learn nonmonotonic patterns from ordinal inputs. Hypothesis: sine and cosine make late December and early January adjacent, possibly helping the model group winter periods. Add the pair while retaining day of year.

Result: bcdcd08, Eval AUC 0.6784, discarded: no AUC gain and slower row evaluation.

## Experiment 10 — weekend indicator

Exploration of an interpretable calendar grouping. The [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) includes working-day and holiday indicators. Hypothesis: a weekend indicator allows a shallow split to capture different travel patterns without spending multiple splits on the seven day-of-week categories. Add an indicator based only on the scheduled day of week.

Result: d3465e5, Eval AUC 0.6784, discarded: tied and added work.

## Synthesis after 10 experiments

Best: 146bc7e at 0.6784. Decoding HHMM (+0.0008), reducing the number of depth-6 trees from 100 to 25 (+0.0019 across two tests), and continuous day of year (+0.0014) helped. Increasing rounds to 300, reducing depth to 4, and adding a high-cardinality route category hurt. Forced categorical partitioning, cyclic season encoding, and a weekend indicator did not add AUC. Current theory: compact calendar structure and strong but early-stopped tree interactions transfer better from 2005 to 2006 than sparse route memorization. Next examine stable airport/carrier signal and ways to regularize categorical effects.

## Research after experiment 10

The [CatBoost paper](https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html) warns that target statistics computed from the same row's label create prediction shift. We will avoid naive target-rate features. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) names `min_child_weight`, `gamma`, and `max_cat_threshold` as controls for overfitting. The next experiment tests leaf support while keeping the useful feature representation fixed.

## Experiment 11 — larger minimum child weight

Exploration. Hypothesis: depth 6 was useful, but leaves supported by only a few 2005 flights may encode noise that fails in 2006. Set `min_child_weight=10`, which requires substantially more support per child than the default 1, retaining depth 6 and 25 rounds.

Result: 039dc20, Eval AUC 0.6779, discarded. This level of leaf regularization removed useful signal.

## Experiment 12 — row subsampling

Exploration of a different regularizer. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) states that per-tree row subsampling can curb overfitting. Hypothesis: sampling 80% of the 2005 rows for each tree will reduce sensitivity to year-specific observations while keeping useful depth-6 splits. Keep 25 rounds and other settings fixed.

Result: ed6e6d6, Eval AUC 0.6786 (+0.0002), kept. The gain is small but supports some variance reduction.

## Experiment 13 — feature subsampling

Follow-up to experiment 12. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) describes `colsample_bytree` as selecting a subset of features per tree. Hypothesis: the raw HHMM, minute-of-day, and hour features are redundant; sampling 80% of columns may diversify splits and prevent a single time representation from dominating. Keep row subsampling at 0.8.

Result: 57623fb, Eval AUC 0.6770, discarded. Feature sampling appears to withhold important splits when only 25 trees are available.

## Experiment 14 — remove raw HHMM

Ablation/simplification. Hypothesis: after minute-of-day and scheduled hour were added, the raw HHMM integer may be redundant or encourage arbitrary splits at hour boundaries. Remove only the raw time feature, retaining decoded time and all other settings. Equal AUC with simpler/faster code is acceptable.

Result: e9521f1, Eval AUC 0.6786, kept because the model has one fewer redundant input at no AUC cost.

## Experiment 15 — remove separate departure hour

Ablation/simplification. Hypothesis: minute-of-day already identifies the hour exactly, so a separate hour split may be unnecessary. Remove `DepHour`, leaving one continuous physical time input rather than three versions of the same schedule. Equal AUC with a simpler representation is valuable.

Result: b4afa74, Eval AUC 0.6783, discarded. The explicit hour helps the 25-tree model despite being derivable from minute-of-day.

## Experiment 16 — carrier and origin interaction

Exploration. [Airline delay research from NBER](https://www.nber.org/papers/w9744.pdf) reports hub carrier delay effects, suggesting that a carrier's operations at a specific airport matter. Hypothesis: a carrier-origin category (1551 observed combinations, much less than the 4290 routes that failed) captures stable hub operations while letting the model use only one split for this interaction. Fit category levels on train, and apply the fixed levels row by row.

Result: 4967577, Eval AUC 0.6728, discarded. Combined categories again overfit and increased evaluation cost. The saved best model uses `max_cat_to_onehot=4` and `max_cat_threshold=64` by default.

## Experiment 17 — tighter category partitions

Exploration of categorical regularization. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) says `max_cat_threshold` caps categories considered in partition splits to prevent overfitting. Hypothesis: the default 64 is too generous for 283-airport features under a year shift; try 16 while preserving all features and 25 rounds.

Result: 3f22e3d, Eval AUC 0.6720, discarded. The tighter cap lost substantial airport signal.

## Experiment 18 — broader category partitions

Follow-up to experiment 17. Hypothesis: because a cap of 16 lost 0.0066 AUC, the airport features benefit from considering more categories together. Raise the cap from default 64 to 128, an opposite directional probe motivated by that result, while holding the model and features fixed.

Result: 1630432, Eval AUC 0.6781, discarded. The default cap of 64 remains best among those tried.

## Experiment 19 — airport geography from scheduled routes

Exploration of spatial features. [Cai et al.](https://www.sciopen.com/article/10.1016/j.cja.2022.10.004) find geographic relationships between airports useful for delay prediction. Hypothesis: approximate airport position can help generalize spatially and seasonally beyond memorized airport IDs. Build a train-only undirected graph weighted by median scheduled route distance, compute shortest-path distances to LAX, JFK, and DFW, then map origin and destination to those fixed lookup values. No labels, evaluation rows, or per-frame aggregation are used.

Result: f74ef1a, Eval AUC 0.6786, discarded. A tie with substantially slower evaluation (55.8 s) and more code.

## Experiment 20 — time relative to route schedule

Exploration of a train-fitted schedule statistic. The [Berkeley flight-delay study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes flight schedules, and `program.md` explicitly gives train-fitted route median time as a valid lookup. Hypothesis: deviation from the usual departure time for a route distinguishes early and late service patterns beyond absolute clock time. Fit a median minute-of-day by route on train and look it up per row; unseen routes become missing.

Result: e874389, Eval AUC 0.6780, discarded. Route-relative schedule was less transferable than absolute time.

## Synthesis after 20 experiments

Best remains e9521f1 at 0.6786. Row subsampling brought a small gain; feature subsampling and strong minimum-child regularization hurt. Removing raw HHMM tied while reducing model inputs, but removing the separately decoded hour hurt. Carrier-origin identities, train-derived airport geometry, and route-median departure time did not improve AUC. Changing the categorical partition limit in either direction hurt. Gain-based importance of the current model is overwhelmingly led by scheduled minute of day, followed by month, carrier, weekday, airport, and day of year. The model needs expressive but well-placed time and category interactions; sparse route-level features are not paying off. Next test an alternative tree growth policy and compact holiday timing.

## Research after experiment 20 and plateau

The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) describes `grow_policy=lossguide` as splitting nodes with the largest loss reduction, with `max_leaves` to bound size. [Scikit-learn's histogram boosting guide](https://scikit-learn.org/1.5/auto_examples/ensemble/plot_hgbt_regression.html) notes that feature interactions and tree complexity affect variance. Flight-delay research finds a strong scheduled-time pattern, and [holiday travel analysis](https://flyerintel.com/holidays/) points to date-specific effects worth testing with fixed-date, row-local features. None of these sources implies an AUC gain here; the next runs will test that.

## Experiment 21 — loss-guided tree growth

Exploration. Hypothesis: depth-wise trees spend leaves across all branches, while loss-guided growth can concentrate a 31-leaf budget on the most useful schedule and airport interactions. Use `grow_policy=lossguide` and `max_leaves=31` while retaining depth 6, 25 rounds, and the current features.

Result: 2fdc62b, Eval AUC 0.6790 (+0.0004), kept. The smaller, loss-guided trees slightly outperform the previous model.

## Experiment 22 — 15 loss-guided leaves

Follow-up to experiment 21. Hypothesis: if concentrating splits helped, a tighter 15-leaf budget may improve regularization further while retaining depth-6 interactions on the highest-gain branches. This tests the low-capacity side of the new growth policy.

Result: b91f59a, Eval AUC 0.6771, discarded. Fifteen leaves underfit compared with 31.

## Experiment 23 — 47 loss-guided leaves

Follow-up to experiments 21–22. Hypothesis: 31 leaves may be near the low side of the useful capacity range; 47 leaves lets loss-guided growth allocate more branches without forcing full depth-wise expansion. Test a materially larger leaf budget while preserving the winning growth policy.

Result: cb80a30, Eval AUC 0.6772, discarded. Thirty-one leaves is best of 15, 31, and 47 under loss-guided growth.

## Experiment 24 — holiday periods

Exploration of specific calendar effects. [Holiday flight-delay analysis](https://flyerintel.com/holidays/) separates Thanksgiving, July 4, and year-end travel periods. Hypothesis: a single small categorical feature for these windows will let the 25-tree model dedicate splits to them more efficiently than learning each window from day of year. Use fixed date ranges only; the feature depends on each row's month/day and applies identically in 2005 and 2006.

Result: e09605c, Eval AUC 0.6791 (+0.0001), kept. `HolidayPeriod` appears in the fitted tree splits, so the model uses it despite the small aggregate gain.

## Experiment 25 — separate Christmas and New Year

Follow-up to experiment 24. Hypothesis: the current year-end bucket combines travel around Christmas with travel around New Year, which may have different flight schedules and delay patterns. Split it into December 21–28 and December 29–January 3 while leaving July 4 and Thanksgiving buckets unchanged.

Result: c8d4ea1, Eval AUC 0.6791, discarded. No gain and greater code complexity.

## Experiment 26 — more rounds for loss-guided trees

Follow-up to the gain in experiment 21. Hypothesis: 31-leaf loss-guided trees overfit less than the earlier 64-leaf depth-wise model, so they may benefit from more boosting rounds. Increase from 25 to 40 while keeping learning rate 0.1 and features fixed. This probes a different capacity regime from the failed 50/100/300 depth-wise settings.

Result: 2f3dd9e, Eval AUC 0.6798 (+0.0007), kept. Reduced leaves allowed a longer boosting sequence to help.

## Experiment 27 — 60 loss-guided rounds

Follow-up to experiment 26. Hypothesis: the improvement from 25 to 40 may continue as the smaller trees learn additional schedule and airport patterns. Test 60 rounds to locate the point where the year shift begins to dominate.

Result: 2f9ff89, Eval AUC 0.6801 (+0.0003), kept. The benefit is diminishing but still positive.

## Experiment 28 — 90 loss-guided rounds

Follow-up to experiments 26–27. Hypothesis: modest additional rounds may still improve the 31-leaf model, but the shrinking gains suggest a nearby maximum. Test 90 rounds, a 50% increase, to probe the overfitting boundary clearly.

Result: 33a4ccd, Eval AUC 0.6800, discarded. The optimum in tested rounds is near 60.

## Experiment 29 — deeper loss-guided branches

Exploration of interaction shape. Hypothesis: the 31-leaf cap protects total tree size, so raising `max_depth` from 6 to 8 can model useful time-by-airport interactions along selected branches without expanding every branch. Keep 60 rounds and all other settings fixed.

Result: 2797a98, Eval AUC 0.6803 (+0.0002), kept. More depth helps a little under a fixed leaf budget.

## Experiment 30 — depth ten with a fixed leaf budget

Follow-up to experiment 29. Hypothesis: the gain at depth 8 could reflect useful narrow airport/time interaction chains; depth 10 tests whether allowing longer chains helps further while the 31-leaf limit controls total size.

Result: a9586ee, Eval AUC 0.6808 (+0.0005), kept.

## Synthesis after 30 experiments

Best: a9586ee at 0.6808, up 0.0065 from baseline. The recent gains came from switching to loss-guided growth with 31 leaves, increasing rounds to 60, and permitting depth 10 while retaining the leaf cap. Fifteen and 47 leaves were both worse than 31; 90 rounds was slightly worse than 60. A compact holiday-period feature also helped a little. The current theory is that sparse, deep, targeted interactions capture useful flight schedule patterns, provided the total leaf budget is constrained. The next experiments will test the depth boundary and regularization of those deeper leaves.

## Research after experiment 30

The [XGBoost 3.4 parameter reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html) confirms that loss-guided growth favors the highest loss reduction, `max_leaves` caps size, and `max_depth` caps paths. Its [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends `gamma` and L2 regularization to curb overfitting. These controls may matter more now that selected branches reach depth 10. Research also suggests scheduled time is dominant in flight delay models; the trained model's gain importance confirms it in this dataset.

## Experiment 31 — depth twelve with a fixed leaf budget

Follow-up to experiments 29–30. Hypothesis: deeper paths under the 31-leaf cap may continue to expose useful airport and time combinations; depth 12 tests whether the gain saturates. Keep 60 rounds and all other settings fixed.

Result: 73d108c, Eval AUC 0.6799, discarded. Depth 10 is best of 6, 8, 10, and 12 with 31 leaves.

## Experiment 32 — penalize weak splits

Exploration of an orthogonal regularizer. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) says `gamma` is the minimum loss reduction required to make a split. Hypothesis: some depth-10 splits follow 2005-only noise, so `gamma=5` will prune weaker branches while preserving the 31-leaf cap and more useful deep interactions.

Result: 9c85fb9, Eval AUC 0.6808, discarded. It tied while adding a parameter; the small runtime difference is not enough evidence of a speed improvement.

## Experiment 33 — stronger L2 leaf regularization

Exploration of leaf-value shrinkage. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) says larger `reg_lambda` makes the model more conservative. Hypothesis: depth-10 branches identify useful interactions but their leaf probabilities may be too extreme for 2006; raise `reg_lambda` from default 1 to 5 while keeping tree structure controls fixed.

Result: 7461a4f, Eval AUC 0.6805, discarded. This stronger L2 penalty reduced useful signal.

## Experiment 34 — smaller learning rate, longer run

Exploration of boosting path. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) suggests reducing `eta` and increasing boosting rounds to control overfitting. Hypothesis: 120 rounds at 0.05 may follow a smoother path than 60 rounds at 0.1 while achieving a similar cumulative step size. Preserve tree shape and feature design.

Result: 1a5836d, Eval AUC 0.6812 (+0.0004), kept. Smoother boosting helped despite doubling trees.

## Experiment 35 — half-sized boosting steps again

Follow-up to experiment 34. Hypothesis: the benefit of smaller steps may continue; use 240 rounds at learning rate 0.025, maintaining roughly the same cumulative step size as the previous two settings. The result will show whether the smoothness gain has saturated.

Result: 77588ba, Eval AUC 0.6810, discarded. Learning rate 0.05 with 120 rounds is better and trains faster.

## Experiment 36 — ablate holiday category at the new optimum

Ablation/simplification. Hypothesis: the holiday category yielded only +0.0001 at 25 rounds; with 120 rounds and deeper loss-guided trees, the model may learn these date effects from day of year itself. Remove the holiday feature and its NumPy import. A tie with simpler, faster preparation is worth keeping.

Result: 44473d1, Eval AUC 0.6818 (+0.0006), kept. Evaluation dropped from 46.2 to 40.1 s, and ten lines of feature code were removed. The prior holiday feature was not useful in the longer model.

## Experiment 37 — ablate departure hour again

Ablation/simplification in a different model regime. Experiment 15 found `DepHour` useful with 25 depth-wise trees, but the current model has 120 deeper loss-guided trees and may learn the same thresholds from minute-of-day. Remove the separate hour column. An equal AUC with simpler preparation is worth keeping.

Result: 70418af, Eval AUC 0.6812, discarded. The hour feature remains useful.

## Experiment 38 — ablate distance

Ablation/simplification. The best model's gain ranking put `Distance` well below scheduled time and calendar/airport features. Hypothesis: it may consume scarce split capacity while adding little to departure delay prediction. Remove the distance input while keeping all other features and settings. A tie with a simpler feature set is worth keeping.

Result: 849b17a, Eval AUC 0.6814, discarded. Distance still contributes.

## Experiment 39 — finer histogram bins

Exploration of continuous split resolution. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/release_3.0.0/parameter.html) says increasing `max_bin` offers more candidate thresholds at extra compute cost. The current model relies heavily on minute-of-day (over 1100 observed departure times) but uses the default 256 histogram bins. Hypothesis: 512 bins will better resolve time-of-day transitions and improve AUC without changing model size.

Result: 301a055, Eval AUC 0.6811, discarded. More detailed thresholds were worse.

## Experiment 40 — coarser histogram bins

Follow-up to experiment 39. Hypothesis: the default 256 bins may already fit some time noise; if 512 bins worsened transfer, 128 bins might regularize time thresholds and generalize better. This tests the opposite direction with a 2x change and may also speed training.

Result: 29c381a, Eval AUC 0.6805, discarded. Default histogram resolution remains best.

## Synthesis after 40 experiments

Best: 44473d1 at 0.6818, up 0.0075 from baseline. The latest clear gain was changing to 120 rounds at learning rate 0.05, then removing a holiday feature that had helped only in the shorter model. At this setting, hour and distance remain useful even though they had modest individual gain importance. Depth 10 with 31 leaves remains best; depth 12, additional L2 regularization, and either direction of histogram-bin change hurt. The leading theory is that local time structure plus targeted airport/calendar interactions matter most; more detailed partitioning or redundant seasonal flags add noise.

## Research after experiment 40

[Airline scheduling research](https://recherche.enac.fr/~steve.lawford/airline_papers/tu_etal05.pdf) reports spiky delay patterns by scheduled departure time that can arise from scheduling and airspace queues. The [scikit-learn time feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) reinforces that useful time components can be exposed explicitly. The next experiment isolates the minute within the scheduled hour, a signal the tree could derive from minute-of-day only through many disjoint splits.

## Experiment 41 — minute within scheduled hour

Exploration. Hypothesis: banked flights at :00/:30 and less common departure minutes may have different delay patterns even within the same clock hour. Add `CRSDepTime % 100` as a row-local numeric feature, retaining minute-of-day and hour. This is a distinct schedule-cycle signal rather than another absolute time scale.

Result: 864eec2, Eval AUC 0.6818, discarded. No gain and evaluation was slower.

## Experiment 42 — less row subsampling

Follow-up to the small gain from `subsample=0.8` earlier. Hypothesis: the current 120-round, lower-learning-rate model may benefit from more rows per tree than the earlier 25-round model. Raise subsample to 0.9 while holding other settings fixed. This tests whether less sampling noise improves the smoother model.

Result: a157264, Eval AUC 0.6817, discarded. Retained 0.8 subsampling.

## Final summary

Best Eval AUC: **0.6818**, commit **44473d1** on branch `oct5`; baseline was 0.6743, a gain of 0.0075. The best model decodes scheduled departure into minute of day and hour, adds ordinal day of year, uses 120 XGBoost rounds at learning rate 0.05 with 80% row subsampling, and grows depth-10 loss-guided trees capped at 31 leaves. Calendar and time features, targeted tree growth, and smaller boosting steps helped. High-cardinality route/carrier-origin categories, geographic and route-median lookups, extra holiday and minute-within-hour features, stronger L2 or split penalties, and altered histogram bins did not improve the final model. The most useful next work would be a deliberate check of the 2005-to-2006 distribution shift and controlled tests of alternate time/airport interactions; holdout evaluation belongs to the human-only post-run process.
