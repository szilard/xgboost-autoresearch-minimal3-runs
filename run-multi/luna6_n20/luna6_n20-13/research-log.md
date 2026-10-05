# Research log

## Baseline — `b15ec66`

- Ran the starter `train.py` unchanged through `python3 harness.py run`.
- Eval AUC: **0.6743**; status: `ok`; training 1.5 s and row-wise evaluation 30.7 s.
- This establishes the comparison point. The starter uses native XGBoost categorical splits on six categorical columns and two raw numeric columns, with 100 trees, depth 6, and learning rate 0.1.
- Before the first experiment, research XGBoost tuning guidance and domain-relevant flight delay features. The evaluation is from 2006 while training is from 2005, so features should be stable and computed from each row plus train-fitted lookups only.

## Experiment 1 — add a route category

- **Class:** exploration.
- **Hypothesis:** a train-fitted categorical `Origin-Dest` key gives the model a direct signal for repeated corridor-specific delay patterns. The train split has 4,290 distinct routes, a median of 32 rows per route, and only 107 singleton routes. The route should therefore often recur without requiring the tree to form a deep conjunction of origin and destination splits.
- **Research:** the XGBoost tuning guide recommends understanding the data and notes that preprocessing can matter as much as parameter tuning ([XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). XGBoost's categorical tutorial describes partition splits that group categories by similar leaf responses ([categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)). A flight-delay study reports value in airport traffic and flight-information features, though its extra weather and air-traffic data are unavailable here ([Shao et al., 2019](https://arxiv.org/abs/1911.01605)).
- **Change:** add only the route categorical feature. Its categories are fitted from `train`; `prepare(df)` derives the route from that row's origin and destination, so its meaning does not depend on the batch size.
- **Result:** Eval AUC **0.6667** (baseline 0.6743), so discard. Training remained fast, but artifact size grew from 2.6 MB to 17.4 MB and row-wise evaluation increased from 30.7 s to 47.7 s. The route identity added noise or overly complex categorical splits on this year-shifted evaluation; its repeated train support alone was not enough to generalize.

## Experiment 2 — one-hot splits for low-cardinality categoricals

- **Class:** exploration.
- **Prior result:** the route interaction was worse than baseline, so this experiment keeps the original features and tests a model-side categorical split choice.
- **Hypothesis:** allowing direct category-equality splits for month, day, weekday, and carrier may capture non-contiguous category effects and interactions more flexibly than partitioning those categories by ordered gradient statistics. Origin and destination stay partition-based because they have 283 levels each.
- **Research:** XGBoost documents `max_cat_to_onehot` as the threshold choosing equality-based one-hot splits for low-cardinality features versus partition splits for higher-cardinality features ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)); the categorical tutorial explains how partitioning can group categories by similar leaf responses ([categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- **Change:** set `max_cat_to_onehot=32`; leave data preparation and all other model parameters unchanged.
- **Result:** Eval AUC **0.6760** versus baseline 0.6743 (+0.0017), so keep `294ecb7` as the new best. Runtime and artifact size were essentially unchanged from baseline (2.6 MB; 30.8 s evaluation).

## Experiment 3 — add row subsampling

- **Class:** follow-up to the improved categorical split setting in `294ecb7`.
- **Hypothesis:** low-cardinality one-hot splits improved AUC modestly; sampling 80% of rows per tree may reduce sensitivity to training-sample noise and help the 2005-to-2006 shift.
- **Research:** the XGBoost tuning guide identifies `subsample` as a way to add randomness and improve robustness ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `subsample=0.8`; keep `max_cat_to_onehot=32` and all other parameters as in the current best.
- **Result:** Eval AUC **0.6753**, below the kept 0.6760, so discard. Runtime was unchanged and the artifact slightly smaller (2.5 MB). This single-seed row-subsampling setting did not improve cross-year ranking.

## Experiment 4 — lower learning rate with more rounds

- **Class:** follow-up to the current best `294ecb7`.
- **Hypothesis:** the original 100 rounds at 0.1 may make overly large boosting updates; 200 rounds at 0.05 preserves roughly the same aggregate step size while allowing a smoother fit that may generalize better across years.
- **Research:** XGBoost's tuning guide explicitly recommends reducing `eta` and increasing the number of boosting rounds when seeking more conservative updates ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `n_estimators=200` and `learning_rate=0.05`; keep all other settings from the current best.
- **Result:** Eval AUC **0.6766** versus 0.6760 (+0.0006), so keep `bb14388`. Runtime stayed under 33 s; artifact size increased to 5.2 MB.

## Experiment 5 — add scheduled departure hour

- **Class:** follow-up to the low-cardinality one-hot improvement in `294ecb7`, combined with the better learning-rate setting in `bb14388`.
- **Hypothesis:** a 24-level hour category can express non-monotonic hour groups and direct hour-by-airline or hour-by-airport interactions. The raw HHMM numeric feature gives ordered thresholds but does not directly mark each hour as a category. With `max_cat_to_onehot=32`, XGBoost can use equality splits for this new feature.
- **Research:** flight-delay literature reports time-of-day effects ([Hsiao & Hansen, 2006](https://journals.sagepub.com/doi/10.1177/0361198106195100113)) and lists scheduled time-of-day among common flight-level predictors ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057)). XGBoost's categorical docs describe equality-based splits for low-cardinality features ([categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- **Change:** derive `DepHour` from `CRSDepTime // 100` inside `prepare`, using levels fitted once from `train`; keep all other features and parameters unchanged.
- **Result:** Eval AUC **0.6762**, below the kept 0.6766, so discard. The hour category did not improve on raw scheduled time plus other features; evaluation also took 35.8 s versus about 30.7 s, likely from the extra per-row transformation.

## Experiment 6 — add a carrier-origin interaction

- **Class:** exploration.
- **Hypothesis:** airline-specific operating patterns at an airport may be useful as a direct interaction. Unlike the route category in experiment 1, this pair is denser in train: 1,551 combinations, median support 43, and 31 singleton groups. The route feature's lower result and higher sparsity motivate trying this smaller pairing.
- **Research:** prior flight-delay models include airline and airport alongside timing and route factors ([Li et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057)); XGBoost can apply categorical splits to a fitted joint key ([categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)). The benefit of a direct carrier-airport interaction here is an inference to test.
- **Change:** add a train-fitted `CarrierOrigin` category computed per row from carrier and origin; keep the current best model parameters.
- **Result:** Eval AUC **0.6718**, below 0.6766, so discard. The artifact grew to 12.2 MB and evaluation to 41.9 s. The denser pair still appears to overfit or add noisy categorical splits; do not prioritize similar joint identity keys.

## Experiment 7 — limit categories considered in partitions

- **Class:** exploration.
- **Prior results:** the route and carrier-origin joint keys both reduced AUC and inflated artifacts. This experiment leaves the feature set unchanged and regularizes the existing high-cardinality airport categoricals.
- **Hypothesis:** origin and destination each have 283 levels and remain partition-based under `max_cat_to_onehot=32`; capping categories considered per partition at 32 may reduce overly specific splits and improve year-to-year generalization.
- **Research:** XGBoost describes `max_cat_threshold` as a maximum number of categories considered for partition splits, specifically to help prevent overfitting ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)); its tuning guide lists this parameter among complexity controls ([tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `max_cat_threshold=32`; keep the current best features and remaining parameters.
- **Result:** Eval AUC **0.6790** versus 0.6766 (+0.0024), so keep `3d31b78` as the new best. Runtime remained about 31 s for evaluation; artifact size decreased slightly to 4.9 MB.

## Experiment 8 — tighten the partition category cap

- **Class:** follow-up to the promising `max_cat_threshold=32` result in `3d31b78`.
- **Hypothesis:** if restricting candidate categories reduced overfitting at 32, a tighter cap of 16 may improve cross-year generalization further; it may also remove useful splits, so compare directly.
- **Research:** the XGBoost parameter documentation says `max_cat_threshold` controls the number of categories considered in partition splits to help prevent overfitting ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Change:** lower `max_cat_threshold` from 32 to 16; leave other settings unchanged.
- **Result:** Eval AUC **0.6779**, below the kept 0.6790, so discard. The artifact shrank to 4.4 MB with no meaningful speed change; the tighter cap appears too restrictive.

## Experiment 9 — test an intermediate partition cap

- **Class:** follow-up to the `max_cat_threshold=32` improvement.
- **Hypothesis:** 16 was too restrictive and 32 performed best so far; an intermediate cap of 48 tests whether there is a broader useful range before the unbounded setting.
- **Research:** XGBoost documents this as a cap on categories considered by partition splits for overfit control ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Change:** set `max_cat_threshold=48`; keep all other settings unchanged.
- **Result:** Eval AUC **0.6782**, below the kept 0.6790, so discard. The artifact increased to 5.1 MB with unchanged evaluation time. The 48 cap is also less effective than 32.

## Experiment 10 — relax the partition cap to 64

- **Class:** follow-up to the `max_cat_threshold=32` improvement.
- **Hypothesis:** caps of 16 and 48 both underperformed 32. Testing 64 probes a looser cap that admits more categories into partition search and completes a small bracket around the promising value.
- **Research:** XGBoost documents this parameter as the candidate category limit for partition-based categorical splits ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Change:** set `max_cat_threshold=64`; keep all other settings unchanged.
- **Result:** Eval AUC **0.6766**, below the kept 0.6790, so discard. The 64 cap was less effective than 32 and 48, supporting the intermediate cap as the current best setting.

## Synthesis after 10 non-baseline experiments

- **Best:** `3d31b78`, Eval AUC **0.6790**, improving the unchanged baseline (0.6743) by 0.0047.
- **What helped:** one-hot splits for categories with at most 31 levels (`max_cat_to_onehot=32`) raised AUC to 0.6760; lowering the learning rate to 0.05 while doubling trees to 200 raised it to 0.6766; limiting partition candidates to 32 produced the strongest gain, to 0.6790. The tested partition caps 16, 48, and 64 were all worse than 32.
- **What did not help:** route and carrier-origin identity categories, scheduled departure hour, and 0.8 row subsampling all underperformed. The composite identity features also enlarged artifacts and slowed row-wise scoring, suggesting they add sparse/noisy splits here. The day-hour category did not add signal beyond raw scheduled time.
- **Current theory:** the compact original feature set already supports useful interactions. The main improvement so far comes from categorical split regularization, especially on the high-cardinality airport features; a smaller learning rate gives a modest additional gain.
- **New research:** flight-delay studies examine weekday versus weekend departure behavior ([Effect of airline choice and temporality](https://www.sciencedirect.com/science/article/pii/S096969971930537X)) and organize departure-delay patterns jointly by weekday and hour ([Cheng et al., 2019](https://onlinelibrary.wiley.com/doi/10.1155/2019/3525912)). These findings come from other time periods and settings, so they motivate a test rather than establish a pattern in this split. The training data confirms `DayOfWeek` uses Monday=1 through Sunday=7 for all 200,000 rows.
- **Next direction:** add a simple, row-local weekend indicator that groups Saturday and Sunday into one feature; if that does not help, move to tree-complexity tuning such as depth or minimum child weight.

## Experiment 11 — add a weekend indicator

- **Class:** exploration.
- **Hypothesis:** directly grouping Saturday and Sunday may let shallow trees represent a weekend-versus-weekday effect and its interactions with airline or airport in one split, while the existing seven-level `DayOfWeek` stays available.
- **Research:** U.S. flight-delay work explicitly models weekday-versus-weekend departures ([Effect of airline choice and temporality](https://www.sciencedirect.com/science/article/pii/S096969971930537X)); a departure-delay spatial study analyzes patterns by weekday and hour ([Cheng et al., 2019](https://onlinelibrary.wiley.com/doi/10.1155/2019/3525912)).
- **Change:** add `Weekend` from the row's `DayOfWeek` value (`c-6` or `c-7`), with no batch-level aggregation.
- **Result:** Eval AUC **0.6789**, just below 0.6790, so discard under the keep rule. Evaluation also slowed to 32.9 s. Day-of-week as an existing categorical feature appears sufficient for this representation.

## Experiment 12 — reduce tree depth to five

- **Class:** exploration.
- **Hypothesis:** the current best uses depth-6 trees; reducing depth by one may constrain interactions that fit 2005-specific noise while retaining the gains from categorical regularization.
- **Research:** XGBoost's tuning guide identifies `max_depth` as a direct model-complexity control for managing the bias-variance tradeoff ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `max_depth=5`; retain `max_cat_threshold=32`, 200 trees at 0.05, and the current categorical strategy.
- **Result:** Eval AUC **0.6805** versus 0.6790 (+0.0015), so keep `9ebaf7c` as the new best. The artifact size fell from 4.9 MB to 2.7 MB and evaluation was slightly faster (30.3 s).

## Experiment 13 — reduce tree depth to four

- **Class:** follow-up to the depth-5 improvement in `9ebaf7c`.
- **Hypothesis:** depth 5 improved cross-year AUC and cut artifact size; one further reduction tests whether simpler interactions continue to generalize better or lose needed capacity.
- **Research:** XGBoost's tuning guidance frames `max_depth` as a complexity control in the bias-variance tradeoff ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `max_depth=4`; keep all other settings from the current best.
- **Result:** Eval AUC **0.6800**, below the kept 0.6805, so discard despite the smaller artifact (1.3 MB). Depth 4 appears slightly too restrictive.

## Experiment 14 — increase minimum child weight

- **Class:** exploration.
- **Hypothesis:** depth 5 is better than 4, but individual leaves may still fit small sample-specific groups. Requiring more Hessian weight per child may reduce those splits while retaining depth-5 interactions.
- **Research:** the XGBoost parameter-tuning guide lists `min_child_weight` among the controls for tree complexity and overfitting ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `min_child_weight=5`; keep the current best depth and categorical settings.
- **Result:** Eval AUC **0.6800**, below the kept 0.6805, so discard. The artifact stayed at 2.7 MB with runtime essentially unchanged; `min_child_weight=5` did not add useful regularization.

## Experiment 15 — use a milder minimum child weight

- **Class:** follow-up to `min_child_weight=5`.
- **Hypothesis:** five may have removed useful small leaves; a value of two tests mild regularization against the default one while preserving depth-5 interactions.
- **Research:** XGBoost's tuning guide identifies `min_child_weight` as a tree-complexity control ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `min_child_weight=2`; keep all other settings at the current best.
- **Result:** Eval AUC **0.6805**, exactly tying the best. The code is not simpler and evaluation was slightly slower (30.9 s vs 30.3 s), so discard under the tie rule.

## Plateau research after experiment 15

- The earlier 24-level `DepHour` feature did not help. A feature-engineering study describes extracting the HHMM hour and grouping scheduled departures into 12 two-hour intervals, as well as a night-flight flag ([study](https://www.mdpi.com/2079-9292/13/24/4910)). That study focuses on arrival delay and a different dataset, so the time-band idea is an informed hypothesis rather than direct evidence for this target.
- Next test a 12-level two-hour block as a categorical feature, retaining raw `CRSDepTime`. Coarser bands may capture broad rush-hour patterns more smoothly than one category per hour.

## Experiment 16 — add a two-hour departure block

- **Class:** exploration after the plateau.
- **Hypothesis:** grouping adjacent hours into 12 two-hour blocks may capture broad operational periods while reducing the sparsity of the 24-level hour feature that failed in experiment 5.
- **Research:** the feature-engineering study defines 12 HHMM intervals across the day ([study](https://www.mdpi.com/2079-9292/13/24/4910)); XGBoost's categorical support can use one-hot splits for this 12-level feature under the current threshold ([categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- **Change:** derive `DepTimeBlock` from the row's scheduled HHMM time as `hour // 2`, with categories fitted once from train; retain raw time and all current best parameters.
- **Result:** Eval AUC **0.6804**, below the kept 0.6805, so discard. The artifact size stayed similar (2.6 MB), but row-wise evaluation increased to 36.1 s. The 12-level representation did not beat raw scheduled time in this setup.

## Experiment 17 — add a cross-midnight night-flight flag

- **Class:** exploration after the weak two-hour-block result.
- **Hypothesis:** the late-evening and early-morning schedule periods are separated numerically by midnight; a single flag can group 21:00–04:00 and expose a direct night-versus-day split without replacing raw time.
- **Research:** a flight feature-engineering study defines a night-flight indicator for scheduled departures from 21:00 through 04:00 ([study](https://www.mdpi.com/2079-9292/13/24/4910)). It studies arrival delay on another dataset, so this is a hypothesis for the current departure target.
- **Change:** add a row-local numeric `NightFlight` flag; keep raw `CRSDepTime` and all other features.
- **Result:** Eval AUC **0.6800**, below the kept 0.6805, so discard. The artifact remained 2.6 MB but evaluation took 33.2 s; the night grouping did not provide a useful additional split.

## Experiment 18 — partition day-of-month values

- **Class:** follow-up to the low-cardinality one-hot improvement in experiment 2.
- **Hypothesis:** the 31 distinct day-of-month values may be too specific for separate equality splits across a year shift. Partitioning that field may group similar dates, while month, weekday, and carrier remain one-hot.
- **Research:** XGBoost's categorical documentation explains the choice between equality-based one-hot splits and category partitions ([categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- **Change:** reduce `max_cat_to_onehot` to 25. With current cardinalities, this changes only day-of-month from one-hot to partition-based; keep `max_cat_threshold=32`.
- **Result:** Eval AUC **0.6769**, well below 0.6805, so discard. This supports keeping day-of-month one-hot under the 32 threshold; partitioning it loses useful date-specific signal.

## Experiment 19 — increase boosting rounds to 300

- **Class:** follow-up to the 200-tree, 0.05-learning-rate improvement.
- **Hypothesis:** the shallower depth-5 model may benefit from additional low-rate boosting rounds; test 300 trees while holding learning rate and all other settings fixed.
- **Research:** XGBoost's tuning guide notes that a smaller `eta` should generally be paired with more boosting rounds ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `n_estimators=300`; retain `learning_rate=0.05`, depth 5, and the best categorical settings.
- **Result:** Eval AUC **0.6798**, below the kept 0.6805, so discard. The artifact grew to 4.0 MB with no runtime gain; 300 rounds appear to overfit compared with 200.

## Experiment 20 — subsample features per tree

- **Class:** exploration.
- **Hypothesis:** row subsampling alone did not help, but sampling 80% of columns per tree may reduce reliance on particular feature splits without removing examples. The current input has eight features, so each tree should still see most of the signal.
- **Research:** XGBoost's tuning guide lists `colsample_bytree` among the randomness controls that can improve robustness to noise ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Change:** set `colsample_bytree=0.8`; keep all other parameters at the current best.
- **Result:** Eval AUC **0.6815** versus 0.6805 (+0.0010), so keep `ad1d860` as the new best. The artifact shrank from 2.7 MB to 2.4 MB; evaluation was about 0.7 s slower.

## Synthesis after 20 non-baseline experiments

- **Best:** `ad1d860`, Eval AUC **0.6815**, up 0.0072 from the 0.6743 baseline. The best model keeps the original eight features and uses 200 trees, learning rate 0.05, depth 5, `max_cat_to_onehot=32`, `max_cat_threshold=32`, and `colsample_bytree=0.8`.
- **What helped:** one-hot splits for low-cardinality categories, capping high-cardinality partition candidates at 32, reducing depth from 6 to 5, and column subsampling. Increasing the tree count to 300 reduced AUC; 16/48/64 category caps were all worse than 32.
- **What did not help:** explicit route and carrier-origin keys, hour/time-block/night features, a weekend flag, row subsampling, minimum child weight, and partitioning day-of-month all underperformed. Composite categories were especially costly in artifact size and evaluation time.
- **Current theory:** the individual calendar, airport, and carrier columns are enough to represent useful effects; their categorical split strategy and tree complexity matter more than adding sparse identity interactions. Feature subsampling appears to help where row subsampling did not.
- **New research:** a past departure-delay project explicitly includes holiday proximity among its calendar features ([Naul, 2008](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)). BTS describes holiday travel periods as extending to surrounding weekends because holidays fall on different weekdays ([BTS holiday delay notes](https://www.transtats.bts.gov/holidayDelay.asp?pn=1)), and MITRE documents operational delays and traffic changes around Thanksgiving Tuesday and Wednesday ([MITRE Thanksgiving 2008 report](https://www.mitre.org/sites/default/files/pdf/09_3693.pdf)). These references motivate a calendar-derived Thanksgiving window, not a claim that those dates are consistently worse in this split.
- **Next direction:** add a row-local Tuesday-through-Sunday Thanksgiving window derived from November's fourth Thursday using the row's month, day, and weekday. Do not use any flight counts or holiday outcome data.

## Experiment 21 — add Thanksgiving travel proximity

- **Class:** exploration after the 20-experiment synthesis.
- **Hypothesis:** departures from Tuesday through Sunday around Thanksgiving may have a distinct travel-demand and traffic-management regime that is not captured efficiently by separate month/day/weekday categories.
- **Research:** an earlier departure-delay project includes holiday proximity among its calendar features ([Naul, 2008](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf)). BTS notes that industry holiday windows include surrounding weekends because the holiday can fall on different weekdays ([BTS holiday delay notes](https://www.transtats.bts.gov/holidayDelay.asp?pn=1)); MITRE describes operational traffic and delay management around Thanksgiving Tuesday and Wednesday ([Thanksgiving 2008 report](https://www.mitre.org/sites/default/files/pdf/09_3693.pdf)).
- **Change:** derive a `ThanksgivingWindow` flag per row from month, day-of-month, and weekday: Tuesday through Sunday around November's fourth Thursday. Use no aggregates or external outcome data.
- **Result:** Eval AUC **0.6816** versus 0.6815 (+0.0001), so keep `c2de381` as the new best. The artifact is 2.3 MB, though row-wise evaluation increased to 41.7 s.

## Experiment 22 — optimize the Thanksgiving window lookup

- **Class:** ablation/simplification of the promising Thanksgiving feature.
- **Hypothesis:** parsing three categorical date fields into nullable integers inside every `prepare` call adds per-row overhead. A compact set of valid November `(day, weekday)` string pairs expresses the same fourth-Thursday window and should reduce evaluation time without changing feature values.
- **Change:** replace pandas string slicing and nullable-integer arithmetic with a module-level pair lookup and direct row-local membership checks. No model parameters or other features changed.
- **Result:** Eval AUC **0.6816**, equal to the best. Keep `2c75a29`: evaluation fell from **41.7 s to 32.0 s** (9.7 s faster) with the same 2.3 MB artifact.

## Experiment 23 — add cyclical departure-time features

- **Class:** exploration.
- **Hypothesis:** raw HHMM values place late-night and just-after-midnight schedules far apart numerically. Sine and cosine of minutes after midnight could expose the 24-hour cycle while retaining the original scheduled time. Flight-delay research has used trigonometric encodings for periodic time variables ([probabilistic flight delay study](https://www.mdpi.com/2226-4310/8/6/152)); this tests that representation with the current XGBoost model.
- **Change:** add row-local `DepTimeSin` and `DepTimeCos` from `CRSDepTime`, alongside the unchanged raw field and all existing features.
- **Result:** Eval AUC **0.6806**, below 0.6816, so discard `9f9b867` and return to `2c75a29`. The 2.3 MB artifact evaluated in 36.7 s. The cyclic representation did not improve this setup.

## Experiment 24 — increase L2 regularization

- **Class:** exploration.
- **Hypothesis:** the cross-year gain from `colsample_bytree=0.8` suggests less reliance on individual predictors may help generalization; modestly increasing L2 penalty could further shrink leaf weights. XGBoost's [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies `reg_lambda` as the L2 regularization control.
- **Change:** set `reg_lambda=2` from its default 1.0; leave all features and other parameters unchanged.
- **Result:** Eval AUC **0.6802**, below 0.6816, so discard `1c9a425` and return to `2c75a29`. Evaluation took 32.2 s; the stronger L2 penalty did not help.

## Experiment 25 — add a Presidents' Day travel window

- **Class:** follow-up to the Thanksgiving calendar feature.
- **Hypothesis:** a second holiday-specific window may expose travel-season effects not represented by independent month/day/weekday splits. BTS defines a Thursday-through-Tuesday period around Presidents' Day, with dates shifting by year ([BTS holiday periods](https://www.transtats.bts.gov/holidayDelay.asp?pn=1)).
- **Change:** add a row-local `PresidentsDayWindow` flag for the six days from Thursday before through Tuesday after the third Monday in February. Build the lookup across the 400-year Gregorian cycle; leave Thanksgiving and model settings unchanged.
- **Result:** Eval AUC **0.6813**, below 0.6816, so discard `1a381b4` and return to `2c75a29`. Evaluation took 33.6 s; the second holiday flag did not improve the model.

## Experiment 26 — increase feature subsampling

- **Class:** follow-up to the promising `colsample_bytree=0.8` result.
- **Hypothesis:** sampling about six of nine features per tree may add useful tree diversity beyond the roughly seven-of-nine setting at 0.8; XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes column subsampling as a regularization control.
- **Change:** set `colsample_bytree=0.7`; keep the data preparation and all other model parameters unchanged.
- **Result:** Eval AUC **0.6812**, below 0.6816, so discard `85b113e` and return to `2c75a29`. Evaluation took 32.1 s; stronger feature subsampling did not help.

## Experiment 27 — try milder feature subsampling

- **Class:** follow-up parameter search around the best `colsample_bytree=0.8` setting.
- **Hypothesis:** after 0.7 performed worse, a milder reduction from all features at 0.9 could retain the regularization benefit seen at 0.8.
- **Change:** set `colsample_bytree=0.9`; keep all other settings fixed.
- **Result:** Eval AUC **0.6809**, below 0.6816, so discard `807704d` and return to `2c75a29`. Evaluation took 31.9 s. The current best remains 0.8.

## Experiment 28 — reduce boosting rounds to 150

- **Class:** follow-up to the 300-round result, which fell below the best.
- **Hypothesis:** the 300-tree model may continue fitting cross-year noise after the useful boosting rounds; 150 trees at the same 0.05 learning rate tests whether less boosting improves generalization.
- **Change:** set `n_estimators=150`; keep learning rate, features, and all other parameters fixed.
- **Result:** Eval AUC **0.6811**, below 0.6816, so discard `e14d4fe` and return to `2c75a29`. Evaluation took 31.9 s; 200 rounds remains preferable.

## Experiment 29 — prune low-gain tree splits

- **Class:** exploration after plateau research.
- **Hypothesis:** recent experiments suggest limited gains from further feature and boosting-round changes. XGBoost defines `gamma` as the minimum loss reduction required for an additional split ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)); a small positive value may suppress weak splits and improve cross-year generalization.
- **Change:** set `gamma=0.1`; leave features and other parameters fixed.
- **Result:** Eval AUC **0.6816**, tying the best. Discard `cad6c87` because it adds a parameter without simplifying the code or improving evaluation speed (32.2 s vs 32.0 s for the best); return to `2c75a29`.

## Final summary

- **Best:** commit `2c75a29`, Eval AUC **0.6816**. The run began at **0.6743**.
- **What helped:** low-cardinality categorical handling, the tuned depth/category settings, `colsample_bytree=0.8`, and the row-local Thanksgiving window. Replacing its repeated pandas conversions with a pair lookup kept AUC tied and reduced evaluation from 41.7 s to 32.0 s.
- **What did not help:** cyclical departure-time features, stronger L2 regularization, a Presidents' Day window, stronger or milder feature subsampling, 150 trees, and a small split-loss threshold. The split-loss experiment tied but was neither simpler nor faster.
- **Next:** explore other row-local calendar interactions or tune a different XGBoost parameter while preserving the 0.8 column-sampling setting.
