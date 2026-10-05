# oct5 XGBoost research log

## Baseline — 8d9c760
Unchanged `train.py`: XGBClassifier with 100 trees, depth 6, learning rate 0.1, native categorical columns. Eval AUC 0.6743; training 1.4s and evaluation 30.1s. Future features must remain row-local or use lookups fitted on train, because evaluation prepares one row at a time.

## Experiment 1 — categorical partitioning (exploration)
Hypothesis: partition splits may share signal across airport and carrier levels better than one-hot splits. XGBoost's [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that `max_cat_to_onehot=1` forces partitioning. Change only that threshold and compare against baseline.
Result: Eval AUC 0.6743, equal to baseline; run time 32.2s versus 31.5s. No simplification or speed gain, so discard.

## Experiment 2 — departure hour category (exploration)
Hypothesis: an hour category can capture time-of-day risk patterns that a single numeric HHMM axis needs multiple splits to express. A [flight delay feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) explicitly extracts scheduled departure hour from HHMM. Keep raw `CRSDepTime` and add a row-local `DepHour` category.
Result: Eval AUC 0.6747 (+0.0004), keep. The gain is small but positive.

## Experiment 3 — more boosting rounds (follow-up)
Hypothesis: the baseline 100-tree model may stop before learning useful interactions among schedule, carrier, and airports. Increase to 300 trees at the same learning rate to test capacity. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies boosting rounds and step size as related controls.
Result: Eval AUC 0.6672, a marked drop; discard. At the original learning rate, 300 rounds likely overfit the cross-year task.

## Experiment 4 — shallower trees (exploration)
Hypothesis: shallower trees generalize better from 2005 to 2006 by avoiding narrow airport and calendar interactions. Test depth 4 at 100 trees; [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) identify larger depth as increasing complexity and overfitting risk.
Result: Eval AUC 0.6789 (+0.0042), keep. Lower tree complexity substantially improves cross-year evaluation.

## Experiment 5 — depth three trees (follow-up)
Hypothesis: if depth 4 helps, depth 3 may further reduce unstable interactions. Change depth only from 4 to 3 at 100 rounds.
Result: Eval AUC 0.6797 (+0.0008), keep. Depth 3 again helps, though less than the previous reduction.

## Experiment 6 — more rounds with shallow trees (follow-up)
Hypothesis: depth 3 may tolerate additional rounds better than depth 6; test 200 trees while holding depth 3 and learning rate 0.1.
Result: Eval AUC 0.6790, below best; discard. More rounds still hurt, even with shallow trees.

## Experiment 7 — depth two trees (follow-up)
Hypothesis: another depth reduction could improve year-to-year stability; test depth 2 at 100 rounds.
Result: Eval AUC 0.6754; discard. Depth 2 removes useful interactions, so depth 3 is the current balance.

## Experiment 8 — ordinal month (exploration)
Hypothesis: the model can share seasonal structure across adjacent months if month is also numeric. Add the month number while retaining the original categorical month. This is row-local and requires no fitted statistics.
Result: Eval AUC 0.6797, equal to best but slower and more code; discard. Numeric month adds no measured value.

## Experiment 9 — carrier-origin interaction (exploration)
Hypothesis: the departure delay propensity of a carrier at a specific airport can differ from the additive carrier and airport effects. A joint categorical feature could express that in one split, useful with depth-3 trees. There are 1,551 carrier-origin pairs in train; levels are fitted on train and then used unchanged per row. This is informed by the [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) and [flight delay factor literature](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057) identifying airlines and airports as influential.
Result: Eval AUC 0.6750; discard. The joint category likely encouraged narrow carrier-airport patterns that do not generalize across years.

## Experiment 10 — higher minimum child weight (exploration)
Hypothesis: minimum child weight 10 will reject small, unstable leaves while retaining depth-3 interactions. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe larger `min_child_weight` as a more conservative split criterion.
Result: Eval AUC 0.6797, equal to best. The 0.3s run-time difference is within noise and the code is more complex; discard.

## Synthesis after 10 experiments
Best AUC 0.6797 at 91b5adb: a departure-hour category and 100 depth-3 trees. Simplifying tree structure produced the clearest gain (+0.0050 versus baseline). More rounds, depth 2, and a high-cardinality carrier-origin interaction hurt. Pure month number, categorical split threshold, and child weight did not improve the displayed AUC. Current theory: broad schedule patterns transfer from 2005 to 2006, while narrow airport and calendar rules overfit. Next explore stochastic regularization and smoother time/date representations.

## Experiment 11 — row subsampling (exploration)
Hypothesis: `subsample=0.8` will reduce dependence on training-year quirks while retaining enough rows per tree. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends subsampling as a way to control overfitting.
Result: Eval AUC 0.6784; discard. Random row omission did not improve cross-year ranking.

## Experiment 12 — smaller steps, 150 rounds (exploration)
Hypothesis: a lower learning rate with moderately more rounds may avoid the overfitting seen at 200 and 300 rounds. Try 0.05 and 150 trees, an effective boosting budget somewhat lower than the current 0.1 × 100. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends pairing reduced step size with more rounds.
Result: Eval AUC 0.6786; discard. Smaller steps and 150 rounds slightly underperform.

## Experiment 13 — one-hot splits for low-cardinality categories (exploration)
Hypothesis: one-hot splits for month, weekday, departure hour, and carrier may select stable single levels while retaining partition splits for airports. Set `max_cat_to_onehot=32`; [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes this threshold and the two split modes.
Result: Eval AUC 0.6794; discard. More one-hot splitting did not surpass the native default.

## Experiment 14 — remove day of month (ablation/simplification)
Hypothesis: day of month may encode brittle date-specific effects, especially when training and evaluation are in different years. Removing it could improve cross-year generalization and simplify the model. The flight delay literature identifies broader temporal factors such as time of day and weekday; exact day of month may add less stable signal.
Result: Eval AUC 0.6800 (+0.0003), keep. The code and evaluation are also simpler/faster, consistent with day-specific patterns not transferring as well across years.

## Experiment 15 — scheduled departure minute (exploration)
Hypothesis: within-hour schedule placement may reflect operational patterns that raw HHMM splits do not isolate efficiently. Add a row-local minute feature; a [flight delay feature engineering study](https://www.mdpi.com/2079-9292/13/24/4910) separately extracts hour and minute from scheduled departure time.
Result: Eval AUC 0.6800, equal but slower and more code; discard. Raw HHMM plus hour category apparently already covers schedule placement sufficiently.

## Experiment 16 — remove destination (ablation/simplification)
Hypothesis: destination may encode route-specific effects that are unstable for departure delays across years. The fitted model's gain importance is lower for `Dest` than for scheduled time, hour, month, carrier, and origin. Test removing it.
Result: Eval AUC 0.6731; discard. Destination carries substantial independent signal despite modest gain importance.

## Experiment 17 — remove departure hour (ablation/simplification)
Hypothesis: after reducing tree depth and removing day of month, the hour category's original small gain may no longer hold. Test whether raw scheduled time alone suffices.
Result: Eval AUC 0.6800, equal to best; evaluation 27.8s versus 31.3s and one less feature. Keep this simplification. The hour category was helpful in the initial context but is redundant after subsequent changes.

## Experiment 18 — remove distance (ablation/simplification)
Hypothesis: with origin and destination retained, distance may be largely redundant and encourage route-specific noise. It had the lowest gain importance in the kept model. Remove it and compare.
Result: Eval AUC 0.6793; discard. Distance adds some route-generalizable signal.

## Experiment 19 — time relative to origin's typical schedule (exploration)
Hypothesis: delay risk rises with how late a departure is relative to its origin airport's normal schedule. A train-fitted median scheduled departure by origin provides a row-consistent reference; subtract it from each flight's scheduled time. [Flight delay research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes airport-specific operational patterns, while this lookup uses only schedule data known before departure.
Result: Eval AUC 0.6801 (+0.0001), keep. A weak positive signal despite slower per-row scoring.

## Experiment 20 — time relative to carrier-origin schedule (follow-up)
Hypothesis: carriers run different waves at the same airport, so a carrier-origin median schedule may be a more precise reference than the airport-only median. Add a second train-fitted lookup; each row's feature is computed from its own carrier, origin, and scheduled time.
Result: Eval AUC 0.6805 (+0.0004), keep. The finer carrier-origin timing reference contributes additional signal.

## Synthesis after 20 experiments
Best AUC 0.6805 at 6371e73. Shallow trees and removing exact day of month provided the largest, most reliable gains. Destination and distance are useful despite modest standalone importance. Redundant time features helped little or were later removed. Train-fitted schedule reference features gave two small successive improvements, suggesting relative operational timing helps. Categorical joint labels and longer boosting both overfit. Next test which schedule reference contributes independently, and explore features that express broad seasonal or time structure without high-cardinality labels.

## Experiment 21 — carrier-origin reference alone (ablation/simplification)
Hypothesis: the finer carrier-origin median may subsume the origin-only median. Remove the origin-only feature and its lookup; if AUC holds, prefer the simpler feature set. Research at the 20-experiment pause reinforced the value of compact, interpretable schedule features.
Result: Eval AUC 0.6810 (+0.0005), keep. The origin-only reference was redundant or mildly harmful; the more specific carrier-origin reference stands alone better.

## Experiment 22 — route schedule reference (exploration)
Hypothesis: some routes have distinctive schedule waves, and departure time relative to the route's median can reveal whether a flight falls late in that route's service day. Fit the median on train, use a row-local route key at inference, and let unseen routes map to missing. This follows the train-fitted lookup pattern prescribed in `program.md` and route relevance discussed in [flight-delay research](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057).
Result: Eval AUC 0.6810, equal but slower and more code; discard. The route reference adds no measurable value beyond the carrier-origin schedule.

## Experiment 23 — true-minute relative schedule (follow-up)
Hypothesis: HHMM subtraction does not represent elapsed minutes across hour boundaries. Convert the carrier-origin reference and flight time to minutes since midnight before subtraction, so a 60-minute shift has the same numerical meaning for every carrier-origin pair.
Result: Eval AUC 0.6812 (+0.0002), keep. Correct clock arithmetic matters for a cross-group relative-time feature.

## Experiment 24 — time since first station departure (follow-up)
Hypothesis: risk can reflect how far into a carrier's operating day a flight occurs. Fit the earliest scheduled departure minute for each carrier-origin pair from train and add elapsed minutes since that first schedule. This differs from the median reference by emphasizing the start of the station's flight day.
Result: Eval AUC 0.6806; discard. The first-flight reference is noisier or redundant relative to the median.

## Experiment 25 — stronger L2 leaf regularization (exploration)
Hypothesis: `reg_lambda=10` will shrink narrow category effects while preserving the useful depth-3 tree structure. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe larger lambda as more conservative.
Result: Eval AUC 0.6799; discard. Uniformly shrinking leaves costs ranking signal.

## Experiment 26 — minimum split gain (exploration)
Hypothesis: `gamma=1` can prune weak splits without shrinking all useful leaves, unlike the L2 test. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) define gamma as the minimum loss reduction needed to split.
Result: Eval AUC 0.6812, equal but slower and more code; discard.

## Experiment 27 — restrict categorical partitions (exploration)
Hypothesis: limiting partition candidates to `max_cat_threshold=16` can regularize high-cardinality airport splits specifically, preserving numeric schedule splits. [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) say this cap prevents overfitting in partition-based splits.
Result: Eval AUC 0.6723, a large drop; discard. Airport categoricals benefit from a wider partition search.

## Experiment 28 — expand categorical partitions (follow-up)
Hypothesis: since a threshold of 16 hurt sharply, raising the category partition cap to 128 may expose useful airport groupings that the default cap misses. This tests the opposite side of the same capacity question rather than another small cosmetic tweak.
Result: Eval AUC 0.6793; discard. Default categorical search capacity is better than either smaller or larger threshold tested.

## Experiment 29 — fewer rounds at best feature set (exploration)
Hypothesis: 100 rounds may still fit some year-specific residuals. The 200-round test was worse; try 70 rounds with all current best features and the same learning rate to locate the useful training range.
Result: Eval AUC 0.6800; discard. 70 rounds underfit compared with 100.

## Experiment 30 — bracket boosting length (follow-up)
Hypothesis: the useful range may lie between 100 and 200 rounds; 70 underfit and 200 previously overfit. Try 130 rounds on the current best feature set, holding all other settings fixed.
Result: Eval AUC 0.6820 (+0.0008), keep. The best boosting length is not simply the shortest; 130 rounds improves on 100, while 70 and 200 are worse in earlier contexts.

## Synthesis after 30 experiments
Best AUC 0.6820 at e7311df. The model now uses depth-3 trees, 130 rounds, carrier-origin relative schedule time in true minutes, and no exact day-of-month feature. Improvements came from controlling tree depth, removing brittle/redundant calendar and hour features, and representing schedule timing relative to carrier operations. Generic regularization (row subsampling, L2, split-gain cutoff, category cap changes) did not improve AUC. Next test model length near 130 and broader time/calendar signals; avoid the narrow categorical interactions that hurt.

## Experiment 31 — 160 rounds with refined features (follow-up)
Hypothesis: the refined feature set may sustain more rounds than the earlier models. Increase 130 to 160 to test whether the recent gain is still rising; the prior 200-round result used a different feature set and cannot settle this question.
Result: Eval AUC 0.6819, just below 130 rounds; discard. The best appears close to 130 for this feature set, so change direction.

## Experiment 32 — four-season grouping (exploration)
Hypothesis: a season feature can pool adjacent months into broader weather and travel regimes, potentially more stable across years than exact-month splits alone. The [flight-delay feature literature](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes seasonal patterns. Keep Month and add a four-level, row-local season category.
Result: Eval AUC 0.6820, equal but slower and more code; discard. Month already captured broad seasons when both were present.

## Experiment 33 — season instead of exact month (ablation/simplification)
Hypothesis: pooling months by season may generalize better across years and reduce categorical granularity. Replace Month with Season rather than adding a redundant feature.
Result: Eval AUC 0.6818; discard. Exact month has useful detail beyond broad season.

### Plateau research after experiments 31–33
Three consecutive changes moved less than 0.001 and were discarded. Pause to seek a different technique before the next run.
Plateau research: [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `grow_policy=lossguide`, which allocates splits to the nodes with highest loss change, and `max_leaves`, which caps tree size. This offers a genuinely different tree shape under a similar leaf budget. Flight-delay literature continues to emphasize time, carrier, and airport interactions, so asymmetric trees may allocate depth where those interactions are most useful.

## Experiment 34 — loss-guided eight-leaf trees (exploration)
Hypothesis: asymmetric trees with at most eight leaves can put extra depth into high-value schedule/airport branches without making every branch deep. Replace depthwise depth-3 growth with histogram-based loss-guided growth, eight leaves, no depth cap.
Result: Eval AUC 0.6805; discard. Unbalanced tree depth did not beat the fixed depth-3 structure.

## Experiment 35 — finer histogram bins (exploration)
Hypothesis: scheduled departure time has 1,162 distinct HHMM values, and the default 256 histogram bins may miss useful cut points. Increase `max_bin` to 512 so XGBoost can consider finer numeric thresholds while keeping the best tree structure. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) note that larger bins improve split optimality at computational cost.
Result: Eval AUC 0.6808; discard. More exact schedule thresholds overfit or distract.

## Experiment 36 — week within month (exploration)
Hypothesis: exact day-of-month categories were brittle, but early/middle/late month can capture broad travel and holiday scheduling patterns. Add a five-level week-of-month category from the row's `DayofMonth`; [flight-delay feature work](https://www.mdpi.com/2079-9292/13/24/4910) discusses day-of-month effects.
Result: Eval AUC 0.6834 (+0.0014), keep. Broad within-month timing recovers useful date signal without the full 31-level category.

## Experiment 37 — merge last partial week (follow-up)
Hypothesis: the fifth bin contains only days 29–31 and may be too sparse. Pool it with days 22–28 so each category has more support while keeping early/mid/late timing.
Result: Eval AUC 0.6857 (+0.0023), keep. The partial final week was indeed too narrow; a four-bin month phase is strongly useful.

## Experiment 38 — ordered month phase (follow-up)
Hypothesis: week-of-month is naturally ordered, so numeric split thresholds may generalize better than unrestricted categorical partitions. Keep the four bins but represent them as numbers.
Result: Eval AUC 0.6857, equal; simpler representation and 1.5s faster evaluation, keep.

## Experiment 39 — three broad month phases (follow-up)
Hypothesis: early (days 1–10), middle (11–20), and late (21–31) phases may be even more stable across years than four week-based bins. This coarsens the proven within-month signal rather than adjusting arbitrary cut points.
Result: Eval AUC 0.6848; discard. Four phases retain useful detail beyond early/middle/late.

## Experiment 40 — month-by-phase interaction (exploration)
Hypothesis: a month-phase category can represent recurring calendar windows such as early July or late November. At 48 possible levels this is much less sparse than the failed carrier-origin category, and the individual Month and WeekOfMonth features stay in place. This adapts the [categorical feature guidance](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) to a moderate-cardinality interaction.
Result: Eval AUC 0.6816; discard. The 48-level calendar interaction overfit or displaced more transferable splits.

## Synthesis after 40 experiments
Best AUC 0.6857 at c28639f. The strongest recent result was a four-bin, ordered week-of-month feature, replacing the earlier brittle 31-level day-of-month category with a broad within-month position. Merging sparse days 29–31 into the late-month bin mattered substantially. Three bins lost some signal; the 48-level month-phase category hurt. Loss-guided trees and finer histogram bins also hurt. Current theory: schedule and calendar effects need smooth, low-cardinality representations, while finely specified interactions overfit across years. Next investigate an ordinal day feature or node-level feature sampling and keep only clear improvements.

## Experiment 41 — ordinal day within month (exploration)
Hypothesis: the successful four-bin position feature may leave a smooth within-bin trend. Add day-of-month as a numeric, ordered variable while retaining the four bins. This differs from the 31-level categorical feature removed earlier; [scikit-learn preprocessing guidance](https://scikit-learn.org/stable/modules/preprocessing.html) notes that numeric codes impose ordering, which is appropriate for calendar day.
Result: Eval AUC 0.6853; discard. Exact numeric day adds noise beyond the four broad phases.

## Experiment 42 — sample features at each split (exploration)
Hypothesis: `colsample_bynode=0.8` may reduce dependence on scheduled time at every split and make the model use complementary airport/calendar signals. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguish this per-node sampling from the row subsampling that failed earlier.
Result: Eval AUC 0.6850; discard. Randomly omitting predictors at each split did not help this compact feature set.

## Experiment 43 — route distance relative to carrier station (exploration)
Hypothesis: a flight's distance relative to that carrier's typical routes from its origin may represent schedule and aircraft-operation differences more directly than absolute distance. Fit a median distance by carrier-origin on train and subtract it per row. [Flight-delay research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies distance and carrier operations as relevant flight features.
Result: Eval AUC 0.6855; discard. Relative distance added no transferable improvement.

### Plateau research after experiments 41–43
Three consecutive discards moved less than 0.001. Search for a different model strategy rather than another minor feature tweak.
Plateau research: [scikit-learn ensemble guidance](https://scikit-learn.org/stable/modules/ensemble.html) says soft voting averages predicted probabilities from complementary classifiers and can balance individual weaknesses. Its [VotingClassifier API](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) supports weighted probability averaging. A second XGBoost model can add deeper interactions while the current winner gets higher weight.

## Experiment 44 — weighted depth-3/depth-4 ensemble (exploration)
Hypothesis: depth-4 trees can capture a few useful carrier/airport/calendar interactions that depth-3 trees miss, even though a depth-4 model alone scored lower earlier. Soft-average a 130-tree depth-3 model with a 100-tree depth-4 model at 2:1 weights.
Result: Eval AUC 0.6860 (+0.0003), keep. The depth-4 component contributes complementary ranking signal despite lower solo performance in an earlier configuration.

## Experiment 45 — equal ensemble weights (follow-up)
Hypothesis: if the deeper model adds complementary signal, equal weights may improve further. Change only the 2:1 blend to 1:1 to measure the value of stronger deep-model influence.
Result: Eval AUC 0.6859; discard. Giving the depth-4 component half the weight is slightly worse.

## Experiment 46 — conservative deep-model weight (follow-up)
Hypothesis: equal weights worsened AUC, so the deeper model may be most useful as a small correction. Test a 3:1 ratio versus the kept 2:1 ratio.
Result: Eval AUC 0.6860, equal to 2:1 but slightly slower and no simplification; discard. A modest deep-model contribution seems sufficient.

## Experiment 47 — fixed-date holiday window (exploration)
Hypothesis: holiday-adjacent travel and staffing can affect departure delays at the same calendar dates in both years. Add a row-local flag for the day before, day of, or day after New Year's Day, Independence Day, and Christmas. [Flight-delay research](https://doi.org/10.1145/3786484.3786539) uses holiday calendars and nearby dates as features; fixed-date windows require no unavailable year field.
Result: Eval AUC 0.6860, equal but slower and more code; discard. Holiday dates added no measurable ranking signal beyond month and month phase.

## Experiment 48 — add categorical-split diversity to ensemble (follow-up)
Hypothesis: a third XGBoost model using one-hot splits for small/medium categorical features may make different errors from the two current models. Blend it at a modest weight with the retained depth-3 and depth-4 models; [XGBoost categorical guidance](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains the split mode, and [scikit-learn ensemble guidance](https://scikit-learn.org/stable/modules/ensemble.html) motivates complementary probability averaging.
Result: Eval AUC 0.6862 (+0.0002), keep. Categorical split diversity contributes a small additional gain.

## Experiment 49 — ablate depth-4 ensemble member (ablation/simplification)
Hypothesis: the categorical alternative may supply enough diversity that the depth-4 model is now redundant. Drop depth-4 and compare a 3:1 blend of the main and categorical-alternate models; equal or better AUC would reduce model size and training cost.
Result: Eval AUC 0.6859; discard. Depth-4 predictions remain complementary to the categorical alternative.

## Experiment 50 — more categorical-alternate weight (follow-up)
Hypothesis: the categorical alternative may help more at 25% of the blend than at 20%. Change main:deep:alternate weights from 3:1:1 to 2:1:1, holding all model fits fixed.
Result: Eval AUC 0.6862, equal; 0.1s run-time difference is noise and the code is not simpler, so discard.

## Synthesis after 50 experiments
Best AUC 0.6862 at 801fcdf: three XGBoost models blended at 3:1:1. The four-bin month-phase feature was the biggest recent step; numeric representation preserved AUC and sped scoring. A depth-4 model and an alternate categorical split strategy each added a small complementary signal when blended with the main depth-3 model. Removing the depth-4 model hurt, while increasing the alternate weight did not help. Holiday flags, finer date detail, and per-node feature sampling did not improve. Next focus on complementary model diversity rather than additional fragile features.
Research at 50: [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) confirms the one-hot threshold changes split structure; [scikit-learn](https://scikit-learn.org/stable/modules/ensemble.html) supports averaging complementary classifiers. A moderate threshold might diversify the ensemble without forcing one-hot splits for Month and Carrier.

## Experiment 51 — weekday-only one-hot alternate (exploration)
Hypothesis: the alternate model may benefit from one-hot splitting weekday while retaining partitioning for Month and Carrier. Reduce its `max_cat_to_onehot` from 32 to 8; keep the ensemble weights and other models fixed.
Result: Eval AUC 0.6859; discard. One-hot weekday alone does not provide the same complementary signal as threshold 32.

## Experiment 52 — month one-hot, carrier partition alternate (follow-up)
Hypothesis: month one-hot may be the useful source of diversity, while carrier one-hot may be unnecessary. Set the alternate model's threshold to 20, so weekday and month get one-hot splits but the 20-level carrier stays partition-based.
Result: Eval AUC 0.6864 (+0.0002), keep. One-hot month while retaining partitioned carrier appears more complementary than one-hot carrier.

## Experiment 53 — weight updated alternate more (follow-up)
Hypothesis: after improving the categorical alternate itself, a 2:1:1 main:deep:alternate blend may beat the current 3:1:1 ratio. This retests weights only after changing the alternate split strategy.
Result: Eval AUC 0.6864, equal and no simplification; discard. The categorical alternate has limited useful weight.

## Experiment 54 — longer deep ensemble member (follow-up)
Hypothesis: the depth-4 member's 100 rounds may underfit relative to the 130-round main model. Raise only the deep member to 130 rounds, keeping blend weights fixed.
Result: Eval AUC 0.6865 (+0.0001), keep. The deeper member benefited slightly from 30 more rounds.

## Experiment 55 — 160-round deep member (follow-up)
Hypothesis: the improvement from 100 to 130 rounds in the deep member may continue. Test 160 rounds without changing the other two models or their weights; stop this direction if it reverses.
Result: Eval AUC 0.6865, equal but slower and more trees; discard. Deep-member gains flattened by 130 rounds.

## Experiment 56 — longer categorical alternate (exploration)
Hypothesis: the categorical alternate may still underfit at 130 rounds, even though the deep member plateaued. Increase only the alternate model to 160 rounds and compare.
Result: Eval AUC 0.6866 (+0.0001), keep. The categorical alternate gained slightly from another 30 rounds.

## Experiment 57 — 190-round categorical alternate (follow-up)
Hypothesis: if the alternate gained from 130 to 160, another 30 rounds could improve the ensemble further. Change only its boosting length; this is the final capacity check within the remaining clock time.
Result: Eval AUC 0.6866, equal to 160 rounds. The shorter model trains slightly faster and uses fewer trees; discard 190 rounds.

## Final summary
Best Eval AUC: 0.6866 at commit eb1987a, versus 0.6743 baseline (+0.0123). The best model uses 130 depth-3 trees, 130 depth-4 trees, and a 160-tree depth-3 model with month/weekday one-hot splits, softly blended at 3:1:1. Useful features were a four-bin ordered week-of-month and scheduled departure time relative to the carrier-origin median, measured in true minutes. Lower tree depth and moderate boosting length improved cross-year AUC. Exact day-of-month categories, high-cardinality interactions, route schedule references, stronger generic regularization, and fixed holiday windows did not help. If continuing later, test alternate feature representations within one ensemble member or validate whether small eval gains persist on the human-only holdout after the run.
