# Research log — oct6

## Baseline — 8d9c760
The unchanged starter model achieved Eval AUC 0.6743 in 32.0 seconds. It uses 100 depth-6 trees, learning rate 0.1, and native categorical features. This is the reference for keep or discard decisions.

## Initial research
- [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): complexity controls (depth, minimum child weight, regularization) and sampling are the main overfitting controls; smaller learning rates need more trees.
- [XGBoost categorical data tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html): native category support offers partition based splitting, and category encoding must stay consistent at prediction time.
- [Naul, Airline Departure Delay Prediction](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf): scheduled departure time and calendar features are relevant predictors; the paper notes strong variation across flights and overfitting risk.
- Installed XGBoost is 3.4.1. Training data has 200,000 balanced rows, 20 carriers, and 283 airports at each endpoint. Scheduled departure is HHMM from 0005 to 2359.

## Experiment 1 — departure clock decomposition (exploration)
Hypothesis: HHMM is not a linear time scale; adding minute of day and departure hour gives trees cleaner thresholds for time of day while retaining the original feature. Based on the scheduled-time signal in Naul and the XGBoost advice to understand input data. Change only these derived clock features.
Result: Eval AUC 0.6751 (+0.0008), kept. Evaluation took 34.7 s. The feature signal is positive but modest.

## Experiment 2 — more boosting at smaller step size (exploration)
Hypothesis: the baseline's 100 rounds at learning rate 0.1 may underfit smooth time and airport effects. Try 250 rounds at 0.05 with other parameters unchanged. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explicitly links smaller step size to more rounds.
Result: Eval AUC 0.6746 (-0.0005 against kept model), discarded. More boosting at this step size did not improve transfer to 2006.

## Experiment 3 — day of year (follow-up to calendar signal)
Hypothesis: a numeric calendar position can model seasonal changes and dates that cross month boundaries with simpler tree splits than separate categorical month/day fields. The [Naul flight-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) included day of year. Use fixed non-leap month offsets (both dataset years are non-leap); preserve the original categories.
First attempt (97d9d51) crashed before training: calendar strings are prefixed, e.g. `c-11`, rather than bare integers. Fix the parsing and rerun the same hypothesis.
Corrected run (4ca56ea): Eval AUC 0.6773 (+0.0022), kept. Numeric annual position helped more than the clock decomposition.

## Experiment 4 — larger minimum child weight (exploration)
Hypothesis: high-cardinality airport splits with small leaves could learn 2005-specific patterns. Raising `min_child_weight` from its default 1 to 10 should regularize those splits. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) names it as a complexity control; all features and other parameters stay fixed.
Result: Eval AUC 0.6774 (+0.0001), kept by the exact printed-AUC rule. The effect is small; it does not by itself establish that stronger regularization is beneficial.

## Experiment 5 — shallower trees (exploration)
Hypothesis: depth 6 may still fit too many year-specific interactions. Test depth 4 while retaining minimum child weight 10. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) identify higher depth as more complex and more prone to overfitting. A shallower model will also be cheaper if AUC is equal.
Result: Eval AUC 0.6828 (+0.0054), kept. Artifact size dropped from 2.6 MB to 0.7 MB. This is strong evidence that the earlier depth-6 model was fitting patterns that did not transfer well to 2006.

## Experiment 6 — depth 3 (follow-up)
Hypothesis: if the gain from depth 6 to 4 came from avoiding narrow interactions, depth 3 may help further. Keep all other features and parameters fixed to isolate depth.
Result: Eval AUC 0.6830 (+0.0002), kept. Artifact decreased to 0.4 MB; most gain from shallower trees came between depth 6 and 4.

## Experiment 7 — depth 2 (follow-up)
Hypothesis: depth 3 still learns unnecessary narrow interactions. Test depth 2 as a clear boundary on complexity; if equal, the smaller model is preferable. All other choices stay fixed.
Result: Eval AUC 0.6777 (-0.0053), discarded. Depth 2 appears too constrained; depth 3 is a useful middle ground.

## Experiment 8 — more rounds for depth 3 (follow-up)
Hypothesis: the shallower model may need more rounds to learn airport and calendar effects. Revisit 250 trees at learning rate 0.05 now that each tree is depth 3; this differs materially from the failed depth-6 experiment 2 because tree capacity is much lower. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) connect smaller step size with more rounds.
Result: Eval AUC 0.6838 (+0.0008), kept. The depth-3 model did benefit from gentler boosting, unlike depth 6.

## Experiment 9 — 500 depth-3 rounds (follow-up)
Hypothesis: the gain at 250 rounds indicates residual underfitting. Double rounds to 500 at the same learning rate 0.05, isolating the amount of boosting and locating the point where extra trees stop transferring.
Result: Eval AUC 0.6836 (-0.0002), discarded. The 250-round model is better on printed AUC and half the size.

## Experiment 10 — row subsampling (exploration)
Hypothesis: sampling 80% of rows per tree may make the shallow model less sensitive to idiosyncrasies of the balanced 2005 sample. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend `subsample` as a source of randomness to control overfitting. Use 0.8, retaining other parameters.
Result: Eval AUC 0.6825 (-0.0013), discarded. Random row sampling did not help here.

## Synthesis after 10 experiments
Best: 0.6838 at ac21572. The main gains came from adding numeric day of year (+0.0022) and reducing tree depth from 6 to 4 (+0.0054). Depth 3 improved a further 0.0002. Depth 2 lost 0.0053, so useful interactions remain. At depth 3, 250 trees at learning rate 0.05 helped (+0.0008), while 500 trees and row sampling lost AUC. Minimum child weight 10 gave only +0.0001. Working theory: a few stable calendar and schedule effects transfer across years, while deep local airport interactions overfit. Next direction: improve representation of the available categorical and schedule fields, and inspect controlled feature interactions.

## Research after experiment 10
- [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains partition splits for categories and the `max_cat_to_onehot` choice. With 283 airports per endpoint, airport split handling is a plausible remaining source of overfit.
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) says `max_cat_threshold` limits the categories considered per partition split to prevent overfitting. This is a direct test of the current depth-3 model's airport splits.
- [Naul flight-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) also names holiday proximity as a useful schedule-time feature. Holiday effects can be tested later with row-local calendar calculations, without extra datasets.

## Experiment 11 — tighter categorical split threshold (exploration)
Hypothesis: partitioning over 283 airport codes can adapt to noise in the 2005 sample even with shallow trees. Limit `max_cat_threshold` to 16 to encourage broader airport effects that transfer to 2006. This changes categorical split search, a new category of experiment supported by the XGBoost references above.
Result: Eval AUC 0.6761 (-0.0077), discarded. Limiting partition candidates this strongly removed useful categorical signal.

## Experiment 12 — one-hot splits for smaller categories (exploration)
Hypothesis: month, day, weekday, and carrier have only 7-31 levels, so individual-category splits may capture stable effects more directly than partition splits, while airports still use partitioning. Set `max_cat_to_onehot=32`; the [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes this switch. This differs from experiment 11, which constrained large airport partitions.
Result: Eval AUC 0.6822 (-0.0016), discarded. The default partition strategy works better than one-hot splits for these categorical fields.

## Experiment 13 — minute within hour (exploration)
Hypothesis: scheduled flights cluster at particular minutes, and different slots within an hour may reflect airline scheduling practices. A row-local `CRSDepTime % 100` feature exposes this repeated pattern across hours; the existing numeric HHMM and minute-of-day fields require interactions to recover it. The [Naul study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) supports scheduled time as a delay predictor.
Result: Eval AUC 0.6838 (equal) but the extra column and ~1.5 seconds of evaluation are not a simplification, so discarded.

## Plateau research
The [Naul departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) explicitly considered holiday proximity. The [XGBoost interaction-constraints tutorial](https://xgboost.readthedocs.io/en/release_1.2.0/tutorials/feature_interaction_constraint.html) notes that spurious feature interactions can hurt generalization; this may be useful if a later depth-4 model with hand-picked interaction groups is tested. For now, test a simple row-local calendar transformation instead of another small parameter tweak.

## Experiment 14 — proximity to fixed holidays (exploration)
Hypothesis: major travel days around New Year's Day, July 4, and Christmas may have distinctive delay patterns. A minimum absolute day-of-year distance to these fixed dates lets depth-3 trees capture several narrow calendar windows with one split. It uses only the flight's own month and day and no outside data.
Result: Eval AUC 0.6839 (+0.0001), kept by the printed-AUC rule. The gain is tiny, so the holiday interpretation remains tentative.

## Experiment 15 — Thanksgiving proximity (follow-up)
Hypothesis: Thanksgiving travel is important, but its November date shifts between 2005 and 2006. Derive the year's first weekday from each row's day-of-year and day-of-week, then the fourth Thursday of November; add absolute days to Thanksgiving as one row-local feature. This follows the holiday-proximity idea in the [Naul study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) while using no outside data or year column.
Result: Eval AUC 0.6842 (+0.0003), kept. Holiday timing continues to help slightly, and the per-row weekday calculation works across the year shift.

## Experiment 16 — spring and autumn travel weekends (follow-up)
Hypothesis: Memorial Day and Labor Day create travel patterns that differ from ordinary Mondays. Compute proximity to the last Monday of May and first Monday of September using the row-derived January 1 weekday; expose the minimum distance as one feature. This extends the successful moving-holiday approach to two more US travel dates.
Result: Eval AUC 0.6842 (equal) but extra code and slower evaluation, so discarded.

## Research before route features
The [PLOS One air traffic delay study](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0249754) uses origin, destination, and scheduled departure timing as schedule inputs. The [Berkeley flight delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) describes airport-specific delay patterns and scheduling effects. These support testing a route-conditioned timing feature, but this experiment must avoid any label-derived or row-count statistics. `program.md` explicitly permits a median scheduled departure time fitted on `train.csv` and looked up during per-row preparation.

## Experiment 17 — departure time relative to route median (exploration)
Hypothesis: depth-3 trees may struggle to learn how unusual a flight's departure time is for its origin-destination route. Fit a route median minute-of-day on train once, then subtract it from each row's departure minute. Unknown routes map to missing, which XGBoost handles.
Result: Eval AUC 0.6846 (+0.0004), kept. Evaluation increased to 50.5 s from string lookup work, still well under the 5-minute limit.

## Experiment 18 — departure time relative to origin median (follow-up)
Hypothesis: a flight scheduled unusually late for its origin may face different congestion or aircraft-rotation risk. An origin median uses a broader, more stable group than a route median, so it tests a distinct airport-level timing relationship. Fit the median on train once and look it up row by row.
Result: Eval AUC 0.6843 (-0.0003), discarded. The route-relative timing feature is more useful than an additional origin-relative time feature.

## Experiment 19 — carrier-origin interaction (exploration)
Hypothesis: a carrier's operations at one airport have distinct, stable delay risk (hub banks, staffing, schedules) that depth-3 trees cannot always isolate from separate `UniqueCarrier` and `Origin` categories. Add their composite as one categorical feature with levels fitted on train. The [XGBoost interaction tutorial](https://xgboost.readthedocs.io/en/release_1.2.0/tutorials/feature_interaction_constraint.html) explains why tree paths encode interactions, while the [PLOS One air traffic paper](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0249754) uses schedule and airport characteristics in delay prediction. There are 1,551 observed carrier-origin pairs in train.
Result: Eval AUC 0.6796 (-0.0050), discarded. A 1,551-level composite category likely encourages local patterns that fail across years; it also slowed row-wise preparation.

## Experiment 20 — remove minimum child weight 10 (ablation)
Hypothesis: `min_child_weight=10` was selected when trees were depth 6, where it barely helped. With depth 3, it may suppress useful schedule and route effects. Remove it to restore the default 1 while keeping the rest of the best model. If AUC ties, the simpler code wins.
Result: Eval AUC 0.6845 (-0.0001), discarded. Even with depth 3, the child-weight constraint adds a little value.

## Synthesis after 20 experiments
Best: 0.6846 at 4fc539b. Since experiment 10, modest gains came from proximity to fixed holidays, Thanksgiving, and route-relative scheduled departure. Strong categorical split changes (`max_cat_threshold=16`, one-hot threshold 32, carrier-origin composite) hurt, sometimes substantially. A broader origin-relative time feature and two more holiday dates did not help. The current theory is that broad regularized trees plus a few purposeful, continuous schedule features work better than high-cardinality interactions. Next: revisit tree depth/regularization on the enriched feature set and test alternative time-of-day representations.

## Research after experiment 20
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `gamma` as the minimum split gain and `reg_lambda` as L2 leaf regularization. These offer different ways to control complexity while permitting deeper trees.
- [XGBoost feature interaction constraints](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html) explains that deeper trees may pick up spurious interactions and that domain-based interaction groups can limit them.
- A [flight-delay feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) explicitly constructs a night-flight indicator from scheduled departure time. This suggests a row-local time block feature as a later experiment.

## Experiment 21 — depth 4 with enriched features (follow-up)
Hypothesis: depth 4 previously helped substantially versus depth 6, while depth 3 was only marginally better with 100 trees. With 250 rounds and new holiday/route features, depth 4 may capture useful interactions those features enable. Test `max_depth=4` with everything else fixed.
Result: Eval AUC 0.6844 (-0.0002), discarded. At 250 rounds the extra depth no longer helps.

## Experiment 22 — minimum split gain (exploration)
Hypothesis: rather than limiting every tree to depth 3 alone, requiring positive gain from a split may prune fragile branches. Set `gamma=5` on the best depth-3 model; the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines it as the minimum loss reduction for a split.
Result: Eval AUC 0.6846 (equal), but no evident speed or complexity improvement, so discarded.

## Experiment 23 — night-flight indicator (exploration)
Hypothesis: late-day delay propagation and the midnight wrap make one night-flight flag useful to depth-3 trees. Add a binary indicator for 21:00 through 04:59 based only on scheduled hour. A [flight-delay feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) used a similar scheduled-time indicator.
Result: Eval AUC 0.6846 (equal), but added code and slower evaluation, so discarded. This is the third consecutive discard without improving the best AUC.

## Plateau research
The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes depthwise growth from `lossguide`, which splits the leaf with the largest loss reduction, and describes `max_leaves` as a size cap. This offers a meaningfully different tree shape while holding leaf budget near the current depth-3 model. An uneven tree may spend capacity on the strongest schedule effects instead of splitting every branch at each depth.

## Experiment 24 — loss-guided eight-leaf trees (exploration)
Hypothesis: an eight-leaf budget with loss-guided growth and depth capped at 5 can devote splits to high-signal parts of the data without the full complexity of depth-4 trees. Set `tree_method=hist`, `grow_policy=lossguide`, `max_leaves=8`, and `max_depth=5` together as one tree-shape experiment.
Result: Eval AUC 0.6836 (-0.0010), discarded. Uneven eight-leaf trees did not improve this dataset; depthwise three-level trees remain best.

## Experiment 25 — stronger L2 leaf shrinkage (exploration)
Hypothesis: modest depth still permits noisy airport and route effects in leaf values. Increase `reg_lambda` from the default 1 to 10 to shrink those values without changing tree depth or feature set. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes L2 regularization as making a model more conservative.
Result: Eval AUC 0.6842 (-0.0004), discarded. Stronger L2 shrinkage did not help.

## Research on periodic time features
The [scikit-learn time-related feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows sine/cosine encodings that join the beginning and end of a periodic range. For this flight model, January and December are adjacent in seasonal conditions but far apart numerically in day-of-year. This could matter to shallow trees.

## Experiment 26 — cyclical day of year (exploration)
Hypothesis: year sine and cosine make winter and other repeating seasons easier to isolate without multiple numeric day-of-year thresholds. Add both on the non-leap 365-day cycle while retaining the original DayOfYear feature.
Result: Eval AUC 0.6837 (-0.0009), discarded. A periodic seasonal representation did not improve the tree model.

## Research before averaging models
The [scikit-learn VotingClassifier reference](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) documents weighted averaging of classifier probabilities with `voting=soft`. Both candidate estimators remain XGBoost models, and the harness still trains and evaluates only through its prescribed path.

## Experiment 27 — depth-3/depth-4 soft vote (exploration)
Hypothesis: depth 4 scored 0.6844 alone, close to depth 3's 0.6846, but may rank some flights differently. A 3:1 probability average may keep the stronger depth-3 signal while correcting some errors with depth 4. Train both on the same `train.csv` and evaluate only through the harness.
Result: Eval AUC 0.6851 (+0.0005), kept. The blend beat both depth-3 and depth-4 individual models, suggesting useful ranking diversity.

## Experiment 28 — equal blend weights (follow-up)
Hypothesis: the 3:1 blend improved over depth 3, so the depth-4 model may deserve more influence. Test 1:1 probabilities with the same two fitted model designs, isolating only the blend weight.
Result: Eval AUC 0.6853 (+0.0002), kept. Increasing depth-4 influence from 25% to 50% helped slightly.

## Experiment 29 — depth-4 majority blend (follow-up)
Hypothesis: the rise from 25% to 50% depth-4 weight may continue, despite depth 4 being weaker alone. Test 1:2 weights as a meaningful shift to two-thirds depth-4 influence and identify whether the blend optimum lies above 50%.
Result: Eval AUC 0.6851 (-0.0002), discarded. The best tested blend is balanced 1:1.

## Experiment 30 — add a depth-2 smoothing model (follow-up)
Hypothesis: a depth-2 model can contribute broad schedule trends to the successful depth-3/depth-4 blend, even though 100 depth-2 trees alone underfit. Train 250 depth-2 trees at the same learning rate, add them at one-seventh weight (`[1,3,3]`) so their bias does not dominate, and test through the harness.
Result: Eval AUC 0.6851 (-0.0002), discarded. Adding a shallow third model did not help and increased artifact size.

## Synthesis after 30 experiments
Best: 0.6853 at 94f446b. The key later improvement was a balanced soft vote of depth-3 and depth-4 XGBoost models. Raising depth-4 weight to two-thirds or adding depth 2 worsened AUC. Recent regularization, alternate tree-growth, night-flight, and cyclical-year experiments also failed. The current best model uses both depths equally and retains the stable calendar and route-relative schedule features. The next useful checks are ablations of potentially redundant time features, since the model now has HHMM, minute-of-day, and hour.

## Research after experiment 30
The [scikit-learn correlated-feature example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html) warns that importances can be misleading when features overlap. I inspected only the saved best models' split-gain summaries (no extra scoring). Neither depth-3 nor depth-4 model uses `DepMinuteOfDay` as a split, while HHMM dominates. This motivates a direct harness ablation rather than trusting importance alone.

## Experiment 31 — remove unused minute-of-day model column (ablation)
Hypothesis: minute-of-day is useful as an intermediate for route-relative time, but adding it as a separate model input is redundant with HHMM. Keep computing it inside `prepare` for the route feature while omitting it from X; if printed AUC ties, the smaller input is simpler.
Result: Eval AUC 0.6853 (equal), kept as a simplification. The model receives one fewer feature while route-relative timing is unchanged.

## Experiment 32 — remove low-use departure hour (ablation)
Hypothesis: raw HHMM supplies nearly all departure-time split gain, and the extra hour column was used little by either ensemble member. Omit `DepHour`; if AUC ties, reduce the input further. This direct harness ablation checks the importance-based clue.
Result: Eval AUC 0.6851 (-0.0002), discarded despite faster evaluation. Departure hour still contributes useful ranking information.

## Experiment 33 — remove route-median lookup (ablation)
Hypothesis: route-relative time helped the single model by +0.0004 but adds string mapping and roughly 8 seconds per evaluation. The depth-3/depth-4 blend may achieve equal AUC without it. Remove the lookup, its feature, and now-unused minute-of-day computation; equal AUC would be a valuable simplification and speed gain.
Result: Eval AUC 0.6852 (-0.0001), discarded despite evaluation falling to 40.7 s. The route feature remains valuable under the strict AUC keep rule.

## Final summary
Best Eval AUC: **0.6853**, commit **6321ab4** on branch `oct6` (baseline 0.6743; gain +0.0110). The final model is an equal soft vote of depth-3 and depth-4 XGBoost classifiers, each with 250 trees, learning rate 0.05, and minimum child weight 10. Kept features include numeric day of year, departure hour, distance to fixed holidays and Thanksgiving, and departure time relative to the train-fitted route median. A separate minute-of-day model input was removed with no loss of printed AUC.

The largest gains came from shallower trees, numeric annual position, and the two-model blend. Holiday and route-timing features each added small gains. More boosting beyond 250 trees, row subsampling, tighter categorical split thresholds, composite carrier-origin categories, cyclical annual features, and stronger L2 regularization did not help. Removing departure hour or the route median made scoring faster but reduced printed AUC, so neither ablation was kept.

Next: the human can score the saved artifacts on the unseen holdout set after the run. If experimenting again, consider alternate diverse shallow XGBoost members or a more deliberate feature-interaction design, and compare any eval gains against holdout before trusting them.
