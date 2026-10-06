# Oct 5 XGBoost research run

## Baseline — 8d9c760
Unchanged starter model: 100 trees, depth 6, learning rate 0.1, native categorical splits. Eval AUC 0.6743; run time 31.9s. Training has 200,000 rows and eight predictors. The HHMM departure time and high-cardinality airports suggest feature work may help.

## Research before experiments
[XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends controlling tree complexity with depth and child weight, using sampling to limit overfitting, and reducing learning rate while increasing boosting rounds. [XGBoost categorical-data guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) documents category partitioning and `max_cat_to_onehot` for native categorical predictors. We'll test these as separate hypotheses.

## Experiment 1 — exploration: smaller trees and gentler boosting
Hypothesis: 100 depth-6 trees may overfit a 2005-to-2006 shift. Try 300 depth-4 trees at 0.05 learning rate with `min_child_weight=5`, per the tuning guide, to represent broad effects with less variance. Other features stay the same.
Result: 0.6793, +0.0050 vs baseline; keep. Shallower, gentler boosting helped despite the year shift.

## Experiment 2 — follow-up: more boosting rounds
Hypothesis: the first change gained AUC because the smaller trees regularize well, and 300 rounds may not have exhausted useful interactions. Raise only `n_estimators` to 600 at the same learning rate; XGBoost's tuning guide recommends pairing smaller steps with more rounds.
Result: 0.6775, -0.0018 vs last kept; discard. Additional rounds appear to overfit this year split.

## Experiment 3 — exploration: explicit route category
Hypothesis: 4-level trees may struggle to assign route-specific effects after learning a strong time-of-day effect. Add origin-destination as one train-fitted categorical feature. This follows the [XGBoost categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) on native categorical splits and [Naul's airline departure study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) on airport and route context. The training set has 4,290 routes, median 32 rows per route; unseen routes map to missing.
Result: 0.6694, -0.0099 vs last kept; discard. A 4,290-level route feature overfit and increased row-wise evaluation time to 42.7s. The [Stanford study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) also highlights the sample size needed to learn individual flight patterns; this result is consistent with that concern.

## Experiment 4 — exploration: departure hour as categorical
Hypothesis: a 24-level hour feature lets native categorical splitting group similar periods and share signal across nearby exact HHMM values, while keeping the original numeric time. On the training split, delayed share rises from roughly 0.20 at 06:00 to 0.65 at 20:00. The [Stanford airline study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) identifies scheduled departure time as a predictive input.
Result: 0.6801, +0.0008 vs last kept; keep. The coarse hour grouping adds a small stable gain at modest evaluation cost. Gain-based importance of the previous kept model ranked `CRSDepTime` first by a wide margin.

## Experiment 5 — follow-up: reduce rounds to 200
Hypothesis: 600 rounds overfit, so 300 may also be beyond the optimum. With the extra hour feature, 200 rounds may improve year-shift generalization. Change only `n_estimators`; keep tree depth, child weight and learning rate fixed.
Result: 0.6796, -0.0005 vs last kept; discard. The optimum appears closer to 300 than 200 rounds with the hour feature.

## Experiment 6 — follow-up: stronger leaf-size regularization
Hypothesis: `min_child_weight=10` rather than 5 may suppress high-variance airport/time splits while retaining 300 rounds. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists child weight as a direct complexity control.
Result: 0.6795, -0.0006 vs last kept; discard. Stronger leaf-size regularization did not help.

## Experiment 7 — ablation: remove day of month
Hypothesis: day-of-month patterns in one year can partly reflect transient weather and calendar alignment rather than a repeatable 2006 effect. Remove `DayofMonth` while retaining month and weekday, reducing potential date memorization and evaluation work. [Naul's study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) notes that weather drives many delays but cannot be forecast far ahead from these inputs.
Result: 0.6805, +0.0004 vs last kept, with ~4s faster evaluation; keep. The 31-level day category likely captured some noise across years.

## Experiment 8 — follow-up: numeric day of month
Hypothesis: day within month might still carry a broad operational pattern even though individual day categories hurt. Encode it as an ordinal number so the tree can share statistical strength across adjacent dates. [Scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses ordinal and categorical encodings for date parts and notes tree models can work directly with numeric time features.
Result: 0.6842, +0.0037 vs last kept; keep. Numeric day supplies a useful smooth calendar signal that the categorical version obscured.

## Experiment 9 — follow-up: ordinal day of year
Hypothesis: a single 1–365 scale can express smooth seasonal changes and narrow calendar windows that cross month boundaries. This is distinct from numeric day of month, which resets each month. [Naul's departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) included day of year and holiday proximity among predictors. Both years are non-leap years; fit no information from eval.
Result: 0.6837, -0.0005 vs last kept; discard. A broad day-of-year scale did not add to month plus numeric day, and may have encouraged transient 2005 date effects.

## Experiment 10 — exploration: one-hot splits for compact categories
Hypothesis: XGBoost's default category partitioning can group 7–24 distinct month/weekday/carrier/hour labels by their current gradient; with this year shift, simpler one-category-versus-rest splits may generalize better. Set `max_cat_to_onehot=32`, leaving 283-level airports partitioned. [XGBoost categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) and [parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) document the threshold and the two splitting methods.
Result: 0.6813, -0.0029 vs last kept; discard. Native category partitioning is materially better than one-hot splits here.

## Synthesis after 10 experiments
Best 0.6842 at ceda777, +0.0099 from baseline. Broad patterns: depth-4 trees with gentler boosting improved; 600 rounds overfit and 200 underfit relative to 300. A compact departure-hour category helped. Removing 31-level day-of-month category helped, then restoring day as a numeric ordinal feature gave the largest later gain. The 4,290-level route category, day of year, extra child-weight regularization, and one-hot categorical splitting hurt. Current theory: the 2005-to-2006 shift rewards smooth, repeatable schedule/calendar effects and penalizes fine categories tied to one year's noise. Next explore robust interactions and sampling/regularization, then simpler schedule-derived features.

## Research after 10 experiments
[XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends row and feature subsampling to reduce overfitting; its [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) also describes leaf-wise growth and category thresholds as different complexity controls. [Scikit-learn's TargetEncoder study](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) shows that target averages without cross fitting overfit high-cardinality identifiers, so raw route target rates are a poor next step here. A [flight-delay XGBoost study](https://www.sciencedirect.com/science/article/pii/S2772415822000050) highlights departure time and carrier as influential schedule fields, supporting tests of their stable interactions.

## Experiment 11 — exploration: row subsampling
Hypothesis: with 200K training rows, taking 80% per tree should preserve the broad schedule patterns and reduce fitting to year-specific noise. Set only `subsample=0.8` per the XGBoost tuning guide.
Result: 0.6844, +0.0002 vs last kept; keep. Row sampling provides a modest variance reduction.

## Experiment 12 — follow-up: column subsampling
Hypothesis: sampling 80% of input features per tree may force the ensemble to use weaker complementary signals rather than overdepend on departure time. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) names column subsampling as a second randomness-based overfitting control. Keep row sampling 0.8.
Result: 0.6838, -0.0006 vs last kept; discard. Omitting one or two predictors from each small tree appears to cost more information than it saves in variance.

## Experiment 13 — exploration: ordinal month instead of native category
Hypothesis: the gain from numeric day suggests ordinal calendar structure matters. Encoding month 1–12 as numeric may let XGBoost learn broad adjacent seasonal ranges with fewer splits, while avoiding noisy gradient-based partitions of months. Retain weekday as categorical and day of month as numeric. [Scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) compares ordinal and categorical date-part encodings.
Result: 0.6847, +0.0003 vs last kept; keep. A broad ordinal season scale appears slightly more transferable than month partitioning.

## Experiment 14 — follow-up: ordinal weekday
Hypothesis: weekday 1–7 has a natural workweek/weekend ordering; a numeric split can separate workdays from weekends with fewer decisions than a categorical partition and may reduce year-specific combinations. Replace the weekday category with `WeekdayNum` while preserving ordinal month/day. The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) presents both encodings as plausible for trees.
Result: 0.6831, -0.0016 vs last kept; discard. Weekday benefits from native categorical grouping unlike month/day.

## Experiment 15 — exploration: depth-3 trees
Hypothesis: many weak higher-order combinations of date, airport and carrier may be specific to 2005. Reducing depth from 4 to 3 should suppress those combinations and improve transfer while keeping 300 rounds. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies depth as a primary complexity control.
Result: 0.6850, +0.0003 vs last kept; keep. Shallower interactions modestly improve cross-year AUC and reduce artifact size from 2.1 MB to 1.1 MB.

## Experiment 16 — follow-up: 500 shallow boosting rounds
Hypothesis: depth-3 trees may need more rounds to represent stable interactions than depth-4 trees. Test 500 rounds at the same 0.05 step. This differs from the failed 600-round test at depth 4, which had greater per-tree capacity and no ordinal calendar features.
Result: 0.6850, equal to last kept but larger and slower; discard under the keep rule. Extra shallow rounds added no measured AUC.

## Experiment 17 — exploration: categorical partition threshold
Hypothesis: airport categories have 283 levels each and partition splits may fit noisy small groups. Reducing `max_cat_threshold` from its default to 16 should limit category search and lower variance. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) describes this parameter as a way to prevent overfitting with partition-based categorical splits.
Result: 0.6791, -0.0059 vs last kept; discard. Restricting airport category partitions loses too much signal.

## Research before ensemble category
[Scikit-learn's ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) explains soft voting by averaging predicted class probabilities and its use when comparably strong models have different errors. [XGBoost's random-forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes subsampling as a source of model diversity. Since the current model has row subsampling 0.8, different seeds can generate meaningfully different fits.

## Experiment 18 — exploration: average three sampling seeds
Hypothesis: averaging three otherwise identical depth-3 XGBoost models (seeds 42, 43, 44) may reduce variance due to sampled rows while preserving the same feature mapping. Training each on the same `train.csv` stays within the 60-second training limit; the saved model will average probabilities at evaluation.
Result: 0.6853, +0.0003 vs last kept; keep. Three-seed averaging reduces some sampling noise at only ~1.7s extra training time; evaluation remains ~31s.

## Experiment 19 — follow-up: one deeper ensemble member
Hypothesis: depth-4 trees can learn interactions missed by depth-3 trees, but their single-model AUC was slightly lower. An ensemble with two depth-3 members and one depth-4 member may retain low variance while gaining complementary interactions. Change only the depth of the seed-44 model.
Result: 0.6856, +0.0003 vs last kept; keep. One depth-4 member added complementary signal to the low-variance depth-3 ensemble.

## Experiment 20 — exploration: carrier × departure-hour category
Hypothesis: delay accumulation over the day may vary by airline operating patterns. A carrier-hour cross should expose this interaction directly to shallow trees. Its cardinality is at most 480, far below the failed 4,290-level route cross. [Google's feature-cross guide](https://developers.google.com/machine-learning/crash-course/categorical-data/feature-crosses) describes combining two categorical attributes; [the flight-delay XGBoost study](https://www.sciencedirect.com/science/article/pii/S2772415822000050) identifies carrier and departure time as influential inputs.
Result: 0.6833, -0.0023 vs last kept; discard. Even this moderate-cardinality cross overfit or distracted the small trees and increased eval to 39s.

## Synthesis after 20 experiments
Best 0.6856 at 4ddf980, +0.0113 from baseline. Smooth calendar encodings remain the largest gains: numeric day and month, but categorical weekday. Depth 3 with 300 rounds generalizes slightly better than depth 4; 500 rounds at depth 3 tied while slower. Row sampling helped slightly; column sampling and aggressive categorical threshold hurt. Averaging three seeds and blending one deeper model added two small gains. Direct route and carrier-hour categories hurt, reinforcing that forcing crosses is not the current path. Next test domain-driven dates and carefully constrained interactions, then revisit ensemble composition or schedule normalization if needed.

## Research after 20 experiments
A [US Bureau of Transportation Statistics holiday-travel study](https://rosap.ntl.bts.gov/view/dot/6311/dot_6311_DS1.pdf) defines the Thanksgiving travel window as Tuesday through Sunday around the fourth Thursday, and the Christmas/New Year window as Dec 21 through Jan 6. These are repeatable calendar rules, unlike a particular storm day. [XGBoost's interaction-constraint guide](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) notes that some multi-feature tree paths can fit spurious relations, supporting our preference for stable feature design.

## Experiment 21 — exploration: holiday travel windows
Hypothesis: two binary indicators for the BTS Thanksgiving and year-end windows will help depth-3 trees capture known travel demand changes without needing a month–day–weekday path. Compute Thanksgiving relative to each row's weekday so the window shifts correctly between 2005 and 2006. No year field or evaluation data is used.
Result: 0.6868, +0.0012 vs last kept; keep. Repeatable holiday travel windows improve cross-year ranking. Evaluation rose to 42.4s due to extra per-row calendar logic, still far below the 5-minute limit.

## Experiment 22 — ablation: remove year-end indicator
Hypothesis: the movable Thanksgiving window carries most of the gain, while fixed year-end dates may already be captured by numeric month/day. Remove `YearEndTravel` and see if we can keep the same AUC with faster, simpler per-row preparation.
Result: 0.6853, -0.0015 vs last kept; discard. The year-end window contributes essential signal beyond raw month/day and is likely the larger part of the combined gain.

## Experiment 23 — ablation: remove Thanksgiving indicator
Hypothesis: if the year-end window explains nearly all of the combined gain, removing Thanksgiving may keep or improve AUC and avoid weekday/date arithmetic on every evaluation row. Retain `YearEndTravel` only.
Result: 0.6871, +0.0003 vs last kept and ~7s faster eval; keep. The Thanksgiving flag was redundant or harmful, while year-end carries the useful signal.

## Experiment 24 — follow-up: separate Christmas and New Year windows
Hypothesis: the broad Dec 21–Jan 6 flag mixes distinct traffic regimes. The [BTS holiday travel study](https://rosap.ntl.bts.gov/view/dot/6311/dot_6311_DS1.pdf) notes different peaks before Christmas and after Christmas. Replace the single flag with Christmas window (Dec 21–28) and New Year window (Dec 29–Jan 6) so shallow trees can assign different effects.
Result: 0.6864, -0.0007 vs last kept; discard. One broad year-end window generalizes better than two narrow phases on these years.

## Experiment 25 — exploration: minute within scheduled hour
Hypothesis: flight schedules cluster at recurring minute marks across different hours; depth-3 trees using HHMM and hour may not easily share that pattern. Add numeric `CRSDepTime % 100` as a row-only feature. [Scikit-learn's time-feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses extracting finer-grained within-day periodic information.
Result: 0.6869, -0.0002 vs last kept; discard. Numeric minute gave a weak monotonic representation. In train-only descriptive checks, :00 and :30 show lower delayed shares (0.462 and 0.472) than nearby five-minute marks (~0.49–0.52), suggesting a non-monotonic schedule-slot pattern.

## Experiment 26 — follow-up: whole/half-hour departure slot
Hypothesis: a single flag for scheduled minutes 00 or 30 lets shallow trees share those two recurring slots, which numeric minute cannot group in one split. The pattern is based on train-only descriptives and requires just a row's scheduled time.
Result: 0.6871, equal to last kept but slower and more code; discard. The slot pattern does not add measured AUC.

## Research before train-fitted schedule lookup
The [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) treats origin airport and scheduled departure time as core, distinct operational factors. The [airport-delay study](https://journals.sagepub.com/doi/10.3141/2052-08) models airport flow in time-of-day segments. `program.md` explicitly permits train-fitted median schedule lookups used row by row at inference.

## Experiment 27 — exploration: departure time relative to origin median
Hypothesis: airports have different daily operating schedules. A departure at 15:00 may be late in one airport's day and near its peak in another. Compute the origin's median scheduled minute from train only, then subtract it from each row's scheduled minute. This continuous relative-time feature may transfer better than a large origin–hour categorical cross.
Result: 0.6870, -0.0001 vs last kept; discard. Airport-relative schedule time adds no measured value beyond origin and departure-time features.

## Experiment 28 — follow-up: five-member depth mix
Hypothesis: the three-member seed ensemble improved over its base, and a fourth/fifth independently sampled member may further smooth idiosyncratic trees. Use three depth-3 models and two depth-4 models, retaining all other settings. [Scikit-learn's soft-voting guide](https://scikit-learn.org/stable/modules/ensemble.html) motivates averaging comparably strong but imperfect classifiers.
Result: 0.6872, +0.0001 vs last kept; keep. Two extra ensemble members give a small AUC gain at ~2s more training; still well under the limit.

## Experiment 29 — exploration: finer histogram bins
Hypothesis: scheduled HHMM time has 1,162 distinct values, while XGBoost's default numeric histogram has 256 bins. `max_bin=512` may locate more useful thresholds for its strongest feature. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) states that increasing `max_bin` improves split optimality at extra computation cost.
Result: 0.6873, +0.0001 vs last kept; keep. Finer time thresholds add a small gain without material runtime cost.

## Experiment 30 — follow-up: near-full time histogram resolution
Hypothesis: increasing from 512 to 1,024 bins may recover nearly all of the 1,162 distinct scheduled times, improving split placement on this dominant predictor. If this instead fits irregular minute-level noise, discard. This completes the bin-resolution direction before the next synthesis.
Result: 0.6872, -0.0001 vs last kept; discard. The 512-bin setting is the best measured resolution; near-full time bins add noise or no useful split quality.

## Synthesis after 30 experiments
Best 0.6873 at 21f1021, +0.0130 from baseline. The last ten experiments showed the strongest post-baseline feature gain from a single year-end travel-window flag; splitting it or adding Thanksgiving hurt. Fine schedule-minute and airport-relative-time features did not help. Averaging five models and raising numeric histogram bins to 512 each gave small gains. Current theory: smooth calendar structure and broad holiday periods carry stable signal across years, while narrow or high-cardinality schedule crosses add variance. Next test alternative tree growth/regularization and other broad calendar indicators, then assess whether more ensemble diversity pays for its complexity.

## Research after 30 experiments
[XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes depthwise from loss-guided tree growth; `max_leaves` can cap leaf count, while `gamma` and L2 regularization make splits more conservative. [XGBoost's tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends controlling complexity explicitly when a model fits noise. These offer a different mechanism from the high-cardinality feature crosses that failed.

## Experiment 31 — exploration: loss-guided trees with leaf budget
Hypothesis: among the candidate splits within a 3/4-depth tree, choosing the highest-loss reduction first and capping at 12 leaves may retain useful interactions while pruning weak branches. Set `grow_policy=lossguide` and `max_leaves=12`; keep the existing per-model depth caps. The depth-3 members naturally cap at eight leaves, while depth-4 members gain a tighter budget than their default 16.
Result: 0.6873, equal to last kept but no simpler or faster; discard. The alternative growth order does not justify its added parameters.

## Experiment 32 — exploration: stronger L2 leaf regularization
Hypothesis: the ensemble still learns noisy year-specific leaf values, especially on airport categories. Raise `reg_lambda` from the default 1 to 5 while keeping the same structure and random seeds. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger L2 regularization makes leaf weights more conservative.
Result: 0.6871, -0.0002 vs last kept; discard. Stronger L2 leaf shrinkage slightly underfits or removes useful contrasts.

## Experiment 33 — follow-up: smaller minimum child weight
Hypothesis: after several conservative changes (depth 3/4, five-seed averaging, row sampling), `min_child_weight=5` may be too restrictive for holiday and airport interactions. Lower to 2, letting useful smaller leaves form while the ensemble limits variance. This is the opposite capacity direction from experiment 6 (`min_child_weight=10`), which hurt.
Result: 0.6871, -0.0002 vs last kept; discard. Smaller children likely fit too much year-specific noise; child weight 5 remains best.

## Experiment 34 — exploration: minimum split gain
Hypothesis: some late tree branches offer only tiny training-loss improvements and may be noise. Set `gamma=1`, which requires a minimum loss reduction to split but leaves leaf-size and shrinkage unchanged. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes gamma from L2 and child-weight regularization.
Result: 0.6873, equal to last kept without simplification or speed; discard. Penalizing low-gain splits at gamma 1 makes no measured difference.

## Experiment 35 — exploration: broader airport categorical partitions
Hypothesis: experiment 17's threshold of 16 removed too much airport detail. The default partition threshold may still restrict a few useful airport groups; increasing `max_cat_threshold` to 128 could learn stronger groupings from 200K rows. Only this categorical parameter changes. [XGBoost's categorical parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as the maximum categories considered per split.
Result: 0.6866, -0.0007 vs last kept; discard. Broader airport partitions add variance; the default categorical threshold is preferable to both 16 and 128.

## Research before additional holiday feature
The [BTS summer-travel report](https://www.bts.gov/statistical-products/surveys/national-household-travel-survey-summer-travel-quick-facts) describes a long seasonal leisure-travel period, and BTS [holiday/travel documentation](https://www.bts.gov/archive/subject-areas/economics_and_finance/deseasonalized_data/seasonally-adjusted-vehicle-miles-traveled/documentation/list_of_figures_and_tables/table2) treats holiday windows as repeatable date features. These motivate a cautious fixed-date test; the failed Thanksgiving flag shows we should retain only measured improvements.

## Experiment 36 — exploration: July Fourth travel window
Hypothesis: early July holiday travel has repeatable schedule and demand effects. Add a single July 1–7 flag, leaving the successful year-end flag untouched. Since July Fourth is a fixed date, the feature is computed from each row alone and transfers to 2006 without any year-specific lookup.
Result: 0.6870, -0.0003 vs last kept; discard. Another narrow holiday flag did not transfer; year-end remains the only useful holiday feature.

## Experiment 37 — exploration: smaller boosting steps at matched total shrinkage
Hypothesis: 500 rounds at learning rate 0.03 (total nominal shrinkage 15) may fit stable patterns more gradually than 300 at 0.05 (also 15), avoiding uneven early splits. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explicitly pairs lower step size with more rounds. This differs from the previous 500-round test, which kept the higher 0.05 rate.
Result: 0.6871, -0.0002 vs last kept; discard. Finer boosting steps with the same nominal total did not help and raised training time to 8.5s.

## Experiment 38 — follow-up: faster matched-strength boosting
Hypothesis: 200 rounds at learning rate 0.075 also have nominal shrinkage 15 and may reduce tree noise and model size. This is distinct from experiment 5's 200 rounds at 0.05 (nominal 10), which underfit before the later feature changes.
Result: 0.6870, -0.0003 vs last kept; discard. Fewer, stronger updates lose AUC despite a smaller model.

## Experiment 39 — follow-up: higher row sampling in ensemble
Hypothesis: with five models averaging away seed noise, sampling 90% rather than 80% of training rows per tree may reduce individual-model bias. This changes only `subsample`; it differs from the earlier single-model row-sampling test.
Result: 0.6868, -0.0005 vs last kept; discard. More data per tree reduced the beneficial diversity or raised variance in this ensemble.

## Experiment 40 — follow-up: shallower five-model mix
Hypothesis: the first depth-4 member improved the three-model ensemble, but the second may contribute less or increase noise. Use four depth-3 and one depth-4 member with the same five seeds, changing only seed 46's depth. This isolates ensemble composition rather than model count.
Result: 0.6873, equal to last kept but ~0.2s faster overall and a smaller 6.3 MB artifact; keep under the equal-AUC simplification/speed rule.

## Synthesis after 40 experiments
Best 0.6873 at ec130fa, +0.0130 from baseline. The last ten experiments mostly tied or fell below the best: loss-guided growth, stronger L2, smaller leaves, gamma, a larger category threshold, July Fourth flag, slower/faster matched-strength boosting and more row sampling gave no lift. The four-shallow/one-deep mix preserved AUC with a smaller, faster model. The cross-year signal still seems dominated by schedule time, broad year-end travel, and smooth month/day effects; small parameter changes now offer diminishing returns. Next try a genuinely different periodic encoding, then one alternative ensemble mechanism if time allows.

## Research after 40 experiments and plateau
[Scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains sine/cosine encoding for annual cycles, avoiding the artificial gap between December and January. [XGBoost's DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes tree dropout as a different overfitting control but notes slower training, making it a later small-scale option under our 60s training limit.

## Experiment 41 — exploration: circular season encoding
Hypothesis: the earlier raw day-of-year value hurt because it placed Dec 31 far from Jan 1 and allowed narrow date thresholds. Add only sine/cosine of day-of-year, which groups nearby winter dates on a circle while preserving gradual seasonality. Keep numeric month/day and the year-end flag for the known travel effect.
Result: 0.6848, -0.0025 vs last kept; discard. Circular annual encodings substantially degrade this tree ensemble; the numeric month/day plus year-end window remain better.

## Experiment 42 — exploration: one depth-2 ensemble member
Hypothesis: a very shallow learner can capture stable main effects and simple interactions with low variance, complementing the three depth-3 and one depth-4 members. Change seed 46 from depth 3 to depth 2; model count and feature mapping stay the same.
Result: 0.6872, -0.0001 vs last kept; discard. The extra shallow model loses a little information relative to the existing mix.

## Experiment 43 — exploration: one dropout-boosted member
Hypothesis: DART's stochastic tree dropout can produce different errors from standard gradient boosting and soften overfit. Replace only seed 46 with a 200-round DART depth-3 model using `rate_drop=0.05` and `skip_drop=0.5`, then average with four unchanged XGBoost members. [XGBoost's DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) documents this option and cautions that it can train more slowly; 200 rounds limits the risk under the 60s training cap.
Result: 0.6874, +0.0001 vs last kept; keep. One DART member adds slight diversity. Training took 16.7s, comfortably below 60s; evaluation stayed ~35s.

## Experiment 44 — follow-up: second DART member
Hypothesis: if one dropout-boosted model complements standard boosted trees, two may further reduce correlated errors. Convert seed 45 (depth 3) to the same 200-round DART settings, leaving three standard models and two DART models. Expected training time remains under 60s.
Result: 0.6875, +0.0001 vs last kept; keep. A second DART member again adds a small gain, at 28.7s training under the 60s cap.

## Experiment 45 — follow-up: third DART member
Hypothesis: the two successive DART additions each improved AUC by 0.0001. Converting seed 43 to DART tests whether the trend persists; leave seeds 42 and 44 standard, preserving the sole depth-4 member. Estimated training ~40s, within the cap.
Result: 0.6874, -0.0001 vs last kept; discard. Two DART members are the best balance; a third displaces too much of the standard ensemble signal.

## Experiment 46 — follow-up: stronger DART dropout
Hypothesis: the two-DART ensemble may benefit from more regularization within those members. Raise `rate_drop` from 0.05 to 0.10, keeping `skip_drop=0.5`, member count and other parameters fixed. [XGBoost's DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) identifies `rate_drop` as the dropout amount.
Result: 0.6877, +0.0002 vs last kept; keep. Stronger dropout in the two DART members improved ranking; training remains 28.1s under the cap.

## Experiment 47 — follow-up: test dropout limit
Hypothesis: the gain from raising `rate_drop` 0.05 to 0.10 suggests stronger DART regularization might help further. Test 0.20 with the same two DART members and unchanged standard members. This is the final feasible experiment before the one-hour budget ends.
Result: 0.6877, equal to last kept and 0.9s faster overall (62.9s vs 63.8s); keep under the equal-AUC speed rule.

## Final summary
Best Eval AUC: **0.6877** at **83775c5** (baseline 0.6743; gain 0.0134), on branch `oct5`. The winning model uses numeric day/month, categorical departure hour and weekday/airports/carrier, a broad Dec 21–Jan 6 year-end flag, 512-bin histograms, row sampling, and a five-model ensemble with three standard boosted-tree members and two DART members. Shallow trees, smooth calendar features, the year-end window and model averaging produced the main gains. Fine route/carrier-hour categories, cyclic season features, more boosting rounds, tighter or looser airport category partitions, extra holiday flags, and strong leaf regularization did not improve Eval AUC. A next run could test different weights for standard vs DART members or alternative broad, repeatable calendar windows. The human should check this saved artifact on the unseen holdout after the run.
