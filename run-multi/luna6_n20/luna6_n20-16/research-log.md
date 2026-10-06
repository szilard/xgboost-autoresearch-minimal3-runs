# Research log

## Baseline — `b15ec66`

- **Result:** Eval AUC 0.6743 (`ok`).
- **Setup:** Unmodified starter model: native categorical XGBoost, 100 trees, depth 6, learning rate 0.1.
- **Observation:** This is the reference score for the run. Research and next hypothesis will be recorded before the first changed model.

## Research before Experiment 1

- The XGBoost tuning guide frames tree depth and related regularizers as bias/variance controls; the categorical tutorial describes one-hot and category-partition splits for categorical predictors ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- A flight-delay XGBoost study reports that departure time and carrier were influential among its flight factors ([study](https://www.sciencedirect.com/science/article/pii/S2772415822000050)). This supports retaining these known inputs, while the route-specific effect below is a hypothesis for this dataset.

## Experiment 1 hypothesis — direct directed-route category

- **Classification:** exploration (new feature representation).
- **Change:** add one categorical `Origin_Dest` feature, leaving all starter features and model settings intact.
- **Why:** separate origin and destination splits require the trees to reconstruct a route. A direct category can expose repeated directed-route effects in one feature. In `train.csv`, 200,000 rows contain 4,290 distinct directed routes, with 107 routes appearing once, so most route levels have repeat examples.
- **Prediction:** repeated routes carry stable operational risk that may improve Eval AUC; sparse categories or year-to-year drift could instead make it neutral or worse.
- **Comparison:** baseline `b15ec66`, Eval AUC 0.6743.

## Experiment 1 — `2d26e48` — discard

- **Result:** Eval AUC 0.6667 (`ok`), versus baseline 0.6743; row-by-row evaluation increased from about 30s to 48s.
- **Outcome:** Reverted to baseline. The direct route category did not generalize from 2005 to 2006 in this representation and added a large categorical lookup/model artifact. This weakens the hypothesis that a raw route ID is useful without stronger shrinkage or a more general route feature.

## Research before Experiment 2

- The scikit-learn time-feature example explains that sine/cosine pairs encode a periodic variable without a discontinuity between the end and start of the cycle ([time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)). The flight-delay study above also identifies departure time as influential.
- In `train.csv`, `CRSDepTime` ranges from 0005 to 2359, has 1,162 unique values, and every minute field is below 60. It is valid HHMM data, so it can be converted rowwise to minutes after midnight.

## Experiment 2 hypothesis — continuous and cyclic departure time

- **Classification:** exploration (new time representation).
- **Change:** retain raw `CRSDepTime`; add true minutes after midnight and sine/cosine encodings with a 1,440-minute period.
- **Why:** the raw integer is HHMM, whose numeric distance is not elapsed minutes and whose values jump at midnight. The added features provide true elapsed-minute thresholds and a periodic encoding of the day boundary. All are computed from the row alone.
- **Prediction:** time-of-day delay patterns may be easier to express; the trees may already recover the relevant boundaries from raw HHMM, so the extra features may add no value.
- **Comparison:** baseline `b15ec66`, Eval AUC 0.6743.

## Experiment 2 — `0445eb1` — discard

- **Result:** Eval AUC 0.6734 (`ok`), 0.0009 below baseline; evaluation took 37s versus about 30s at baseline.
- **Outcome:** Reverted to baseline. Correcting HHMM to minutes and adding a single smooth cycle did not help at this resolution. A per-hour category remains a distinct test because it allows arbitrary hourly effects rather than imposing a smooth cyclical shape.

## Experiment 3 hypothesis — departure hour as a category

- **Classification:** exploration (different time representation from Experiment 2).
- **Change:** add `DepHour`, derived from `CRSDepTime // 100`, as a categorical feature with levels fitted once on `train.csv`; keep raw `CRSDepTime` and baseline settings.
- **Why:** the scikit-learn time-feature example compares ordinal, one-hot hour and sine/cosine encodings, noting that hour categories allow arbitrary per-hour effects ([guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)). XGBoost's categorical handling supports direct categorical splits ([XGBoost categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)). The previous smooth cycle was slightly below baseline; this feature tests a less constrained hourly shape and can interact with carrier/airport splits.
- **Prediction:** hourly irregularity may explain delay risk beyond raw HHMM thresholds; it may also be redundant because trees can already threshold the raw time.
- **Comparison:** baseline `b15ec66`, Eval AUC 0.6743.

## Experiment 3 — `97a4c17` — keep

- **Result:** Eval AUC 0.6747 (`ok`), improving the previous kept score by 0.0004; evaluation took about 36s.
- **Outcome:** Kept. A modest per-hour category improved over baseline, while the higher-cardinality route category failed. This suggests coarse operational groupings may be more stable than raw route IDs.

## Experiment 4 hypothesis — carrier-by-hour interaction

- **Classification:** follow-up to the kept departure-hour category (`97a4c17`, 0.6747).
- **Change:** add a train-fitted categorical `CarrierHour` key while retaining `DepHour` and all other features.
- **Why:** the flight-delay study identifies both carrier and departure time as influential; their joint effect may differ by airline. In `train.csv`, the interaction has 401 levels, only 6 singletons, and a median of 360 rows per level, substantially denser than the failed 4,290-level route feature.
- **Prediction:** the interaction may let the model capture carrier-specific scheduling patterns; it may be redundant with sequential tree splits on `UniqueCarrier` and `DepHour`.
- **Comparison:** last kept `97a4c17`, Eval AUC 0.6747.

## Experiment 4 — `1aba3f1` — discard

- **Result:** Eval AUC 0.6721 (`ok`), below the kept 0.6747; evaluation took about 44s.
- **Outcome:** Reverted to `97a4c17`. The direct joint category underperformed the model's separate carrier and hour features. This supports avoiding extra categorical interactions without stronger evidence.

## Experiment 5 hypothesis — one-hot splits for low-cardinality categories

- **Classification:** follow-up to the kept departure-hour feature (`97a4c17`, 0.6747).
- **Change:** set `max_cat_to_onehot=25`; leave features and all other model settings unchanged. The installed XGBoost version is 3.4.1.
- **Why:** the official XGBoost categorical documentation says `max_cat_to_onehot` selects between equality (one-hot) splits and category-partition splits, and that categories below the threshold use one-hot splits ([categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). A threshold of 25 makes the 24-level `DepHour` and other smaller categories eligible for one-hot splits, allowing individual levels to be isolated instead of grouped.
- **Prediction:** individual hours or calendar levels may have distinct risk; the extra split flexibility may also overfit.
- **Comparison:** last kept `97a4c17`, Eval AUC 0.6747.

## Experiment 5 — `18b82c0` — discard

- **Result:** Eval AUC 0.6719 (`ok`), below the kept 0.6747; evaluation took about 36s.
- **Outcome:** Reverted to `97a4c17`. Forcing one-hot splits on low-cardinality categories reduced AUC, so the starter category-partition behavior remains preferable in the current feature set.

## Experiment 6 hypothesis — shallower trees

- **Classification:** exploration (model-capacity regularization).
- **Change:** lower `max_depth` from 6 to 4, keeping the best feature set and all other parameters fixed.
- **Why:** the XGBoost parameter guide states that increasing tree depth raises model complexity and overfitting risk ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Recent direct categorical additions and one-hot splits both underperformed on 2006; a shallower tree may generalize better across the year shift.
- **Prediction:** less capacity may improve cross-year AUC if the baseline is overfitting; it could lose useful carrier/airport interactions.
- **Comparison:** last kept `97a4c17`, Eval AUC 0.6747.

## Experiment 6 — `603aca8` — keep

- **Result:** Eval AUC 0.6789 (`ok`), improving the previous best 0.6747 by 0.0042; evaluation took about 36s.
- **Outcome:** Kept. Reducing depth from 6 to 4 substantially improved the 2006 score, supporting the cross-year overfitting hypothesis. Next, test whether depth 3 regularizes further or begins to underfit.

## Experiment 7 hypothesis — depth 3 versus depth 4

- **Classification:** follow-up to the promising depth-4 result (`603aca8`, 0.6789).
- **Change:** lower only `max_depth` from 4 to 3.
- **Why:** depth 4 improved Eval AUC by 0.0042 over depth 6. One further step tests whether the cross-year gain continues with simpler interactions, or whether depth 4 is needed to model carrier/airport structure.
- **Prediction:** depth 3 may reduce overfitting further, but could underfit useful feature interactions.
- **Comparison:** last kept `603aca8`, Eval AUC 0.6789.

## Experiment 7 — `3daef11` — keep

- **Result:** Eval AUC 0.6797 (`ok`), improving the previous best 0.6789 by 0.0008; evaluation took about 36s.
- **Outcome:** Kept. Depth 3 improved slightly over depth 4, continuing the regularization trend. A depth-2 step will test the lower-capacity boundary.

## Experiment 8 hypothesis — depth 2 versus depth 3

- **Classification:** follow-up to the improving depth-4/depth-3 sequence (`603aca8` and `3daef11`).
- **Change:** lower only `max_depth` from 3 to 2.
- **Why:** the last two depth reductions improved Eval AUC, so test one more step while preserving the best feature set and category handling.
- **Prediction:** depth 2 may continue to reduce cross-year overfitting, or underfit interactions among the airport, carrier, and schedule features.
- **Comparison:** last kept `3daef11`, Eval AUC 0.6797.

## Experiment 8 — `fa437a6` — discard

- **Result:** Eval AUC 0.6754 (`ok`), 0.0043 below the kept depth-3 model; evaluation took about 36s.
- **Outcome:** Reverted to `3daef11`. Depth 2 underfit relative to depth 3, placing the useful capacity range between 2 and 4 for this feature set.

## Experiment 9 hypothesis — increase `min_child_weight`

- **Classification:** follow-up to the kept depth-3 model (`3daef11`, 0.6797).
- **Change:** set `min_child_weight=5`, keeping depth 3 and every other feature/parameter unchanged.
- **Why:** the XGBoost parameter reference says a larger `min_child_weight` makes the model more conservative by requiring more instance weight before splitting ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). After finding the useful depth range, this tests whether weak leaves still overfit the 2005-to-2006 shift.
- **Prediction:** suppressing low-support splits may improve generalization; it may also discard useful airport/carrier distinctions.
- **Comparison:** last kept `3daef11`, Eval AUC 0.6797.

## Experiment 9 — `55221b3` — discard

- **Result:** Eval AUC 0.6797 (`ok`), equal to the kept depth-3 model; evaluation time was effectively unchanged.
- **Outcome:** Reverted to `3daef11`. The added regularization had no measured AUC benefit and was not a meaningful simplification or speedup.

## Experiment 10 hypothesis — row subsampling

- **Classification:** exploration (stochastic regularization).
- **Change:** set `subsample=0.8` with the depth-3 best model; keep all other settings fixed.
- **Why:** XGBoost's tuning guide describes row and column sampling as ways to add randomness and control overfitting ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). The depth reduction helped substantially, while higher `min_child_weight` did not; this tests an independent regularization mechanism.
- **Prediction:** sampling 80% of training rows per boosting iteration may improve year-shift generalization, or reduce useful signal.
- **Comparison:** last kept `3daef11`, Eval AUC 0.6797.

## Experiment 10 — `0c9a160` — discard

- **Result:** Eval AUC 0.6784 (`ok`), below the kept 0.6797; evaluation took about 36s.
- **Outcome:** Reverted to `3daef11`. Row subsampling at 0.8 did not improve this model.

## Synthesis after 10 experiments

- **What helped:** A 24-level departure-hour category made a small gain. Lowering `max_depth` from 6 to 4 and then 3 produced the strongest improvement, from 0.6743 to 0.6797. The large difference between depths 2, 3, and 4 suggests this dataset benefits from modest but nontrivial interactions.
- **What did not help:** Raw directed-route and carrier-hour categories, HHMM/minute/cyclic time additions, forcing one-hot splits for small categories, higher `min_child_weight`, and 0.8 row subsampling all failed to beat the current best. The depth-2 model underfit; depth 4 and 3 generalized better than depth 6.
- **Current theory:** Cross-year generalization is sensitive to model complexity. Coarse schedule features and shallow trees appear more stable than high-cardinality interactions or added split flexibility.
- **Next direction:** Research leakage-safe ways to summarize historical category effects (especially carrier and airport) using only `train.csv`. A smoothed target encoding may retain the signal behind categories without the raw-ID sparsity seen for routes, but training-time leakage must be controlled and eval preparation must use only train-fitted lookups.

### Research after the 10-experiment synthesis

- Scikit-learn's `TargetEncoder` maps categories to shrunk target means. Its `fit_transform` uses internal cross-fitting so each training fold is encoded from the other folds; `transform` uses the final train-fitted mappings for new rows. Unseen categories fall back to the global target mean ([API reference](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html), [cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)). The installed scikit-learn version is 1.9.1.
- This is a possible alternative to raw categorical route identity: it carries a smoothed historical delay rate rather than asking the tree to memorize route labels. It may still fail under the 2005-to-2006 shift.

## Experiment 11 hypothesis — cross-fitted category target means

- **Classification:** exploration (supervised categorical representation).
- **Change:** add cross-fitted target-mean encodings for `UniqueCarrier`, `Origin`, `Dest`, and directed `Route`, keeping all native categorical features and the best depth-3 model. Fit mappings only on `train.csv`; training rows use cross-fitted values, while eval/holdout rows use the full train-fitted mappings looked up one row at a time.
- **Why:** raw route categories underperformed, but smoothed category target means can pool sparse category effects. Scikit-learn's documented cross-fitting avoids using each training row's own target in its training-time encoding.
- **Prediction:** supervised category rates may improve ranking, especially for airports and routes; 2005 rates may drift and add no value for 2006.
- **Comparison:** last kept `3daef11`, Eval AUC 0.6797.

## Experiment 11 — `47f143a` — discard

- **Result:** Eval AUC 0.6792 (`ok`), below the kept 0.6797; evaluation took about 57s, up from about 36s.
- **Outcome:** Reverted to `3daef11`. Cross-fitted category target means did not improve this model and made row-by-row preparation slower. The raw category split and depth-3 model remain preferable.

## Experiment 12 hypothesis — coarser departure periods

- **Classification:** ablation/simplification of the kept 24-level `DepHour` feature.
- **Change:** replace `DepHour` with a categorical `DepPeriod` having four six-hour bins (00–05, 06–11, 12–17, 18–23); leave raw `CRSDepTime` and the depth-3 model unchanged.
- **Why:** the 24-level hour category gave a small gain, but broader groups may retain stable operational periods while pooling examples. The scikit-learn time-feature guide discusses binning fine-grained time features to limit the feature-level count while keeping non-monotonic time effects ([time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)).
- **Prediction:** broader periods may generalize better across years, or lose distinctions that made `DepHour` useful.
- **Comparison:** last kept `3daef11`, Eval AUC 0.6797.

## Experiment 12 — `7af828b` — keep

- **Result:** Eval AUC 0.6798 (`ok`), 0.0001 above the previous best; evaluation took about 36s.
- **Outcome:** Kept under the strict higher-AUC rule. Replacing 24 hourly categories with four broad periods slightly improved the score, consistent with the idea that coarser time structure is more stable across years.

## Experiment 13 hypothesis — smaller boosting steps

- **Classification:** exploration (boosting trajectory).
- **Change:** set `learning_rate=0.05` and `n_estimators=200`, keeping the depth-3, four-period feature set.
- **Why:** the XGBoost tuning guide says to reduce the step size for more conservative updates and increase the number of rounds to compensate ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). The depth-3 model is the current strong baseline; smaller steps may improve ranking without restoring deeper trees.
- **Prediction:** finer boosting updates may improve AUC; the additional rounds may also overfit the 2005 training sample.
- **Comparison:** last kept `7af828b`, Eval AUC 0.6798.

## Experiment 13 — `9aa4478` — keep

- **Result:** Eval AUC 0.6805 (`ok`), improving the previous best 0.6798 by 0.0007; evaluation took about 37s.
- **Outcome:** Kept. A smaller step size with twice the rounds improved AUC. Test one further step along the same documented learning-rate/rounds trade-off.

## Experiment 14 hypothesis — continue smaller-step boosting

- **Classification:** follow-up to the kept learning-rate result (`9aa4478`, 0.6805).
- **Change:** set `learning_rate=0.025` and `n_estimators=400`, keeping other settings fixed.
- **Why:** the `0.05`/200-tree model improved AUC. Another halving of the step size with twice the rounds tests whether more gradual fitting can further improve ranking.
- **Prediction:** it may continue the gain, or show diminishing returns/overfitting; training and evaluation should remain within their limits.
- **Comparison:** last kept `9aa4478`, Eval AUC 0.6805.

## Experiment 14 — `671d54b` — discard

- **Result:** Eval AUC 0.6804 (`ok`), 0.0001 below the kept `0.05`/200-tree model; evaluation took about 36s.
- **Outcome:** Reverted to `9aa4478`. One further learning-rate reduction did not improve the result.

## Research before Experiment 15

- A flight departure-delay study organizes delay patterns jointly by day of week and hour and reports temporal clusters ([study](https://onlinelibrary.wiley.com/doi/10.1155/2019/3525912)). Another airport-delay study identifies time period and weekday/weekend as relevant factors ([study](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)). These are evidence for testing, not proof the interaction will transfer to this U.S. dataset.
- `train.csv` has all 28 `DayOfWeek × DepPeriod` combinations represented; none are singletons, and the median is 8,321 rows per combination.

## Experiment 15 hypothesis — weekday-by-period category

- **Classification:** follow-up to the kept four-period timing feature (`7af828b`, now combined with the improved boosting settings in `9aa4478`).
- **Change:** add a categorical `WeekPeriod` key combining `DayOfWeek` with the four-level `DepPeriod`, retaining both original fields and all current settings.
- **Why:** time-of-day and weekday effects may interact. The 28-level interaction is much denser than the failed 401-level carrier-hour category, so it may capture weekday schedule patterns without the same sparsity.
- **Prediction:** a joint split may expose stable temporal patterns; the existing depth-3 model may already capture them through separate features.
- **Comparison:** last kept `9aa4478`, Eval AUC 0.6805.

## Experiment 15 — `16a0ad0` — keep

- **Result:** Eval AUC 0.6810 (`ok`), improving the previous best 0.6805 by 0.0005; evaluation took about 44s.
- **Outcome:** Kept. A dense weekday-by-period interaction improved ranking, supporting non-additive temporal effects. Test whether this feature set can use one additional tree level without losing cross-year generalization.

## Experiment 16 hypothesis — depth 4 with weekday-period interaction

- **Classification:** follow-up to the kept `WeekPeriod` interaction (`16a0ad0`, 0.6810).
- **Change:** raise only `max_depth` from 3 to 4, preserving the 200-tree, 0.05 learning-rate settings and current features.
- **Why:** the new joint category improved AUC and may support further interactions with carrier/airport. Depth 4 lost to depth 3 before `WeekPeriod` existed, so this isolates whether the expanded features change the best capacity setting.
- **Prediction:** an extra level may capture temporal-by-carrier/airport patterns, or revive the overfitting seen in the earlier depth-4 model.
- **Comparison:** last kept `16a0ad0`, Eval AUC 0.6810.

## Experiment 16 — `f6a3101` — keep

- **Result:** Eval AUC 0.6814 (`ok`), improving the previous best 0.6810 by 0.0004; evaluation took about 44s.
- **Outcome:** Kept. With `WeekPeriod`, depth 4 beat depth 3, unlike the earlier feature set. Test depth 5 once to see whether capacity continues to help.

## Experiment 17 hypothesis — depth 5 with weekday-period interaction

- **Classification:** follow-up to the kept depth-4/`WeekPeriod` model (`f6a3101`, 0.6814).
- **Change:** raise only `max_depth` from 4 to 5.
- **Why:** depth 4 improved by 0.0004 on the expanded temporal feature set. One additional level tests whether the interaction now supports useful extra conditioning or whether the earlier overfitting pattern returns.
- **Prediction:** deeper trees may gain from airline/airport interactions with `WeekPeriod`, or reduce 2006 generalization.
- **Comparison:** last kept `f6a3101`, Eval AUC 0.6814.

## Experiment 17 — `043e838` — discard

- **Result:** Eval AUC 0.6794 (`ok`), 0.0020 below the kept depth-4 model; evaluation took about 43s.
- **Outcome:** Reverted to `f6a3101`. Depth 5 lost the gain from depth 4, indicating that this feature set still benefits from bounded complexity.

## Research before Experiment 18

- A U.S. airline delay study models seasonal and time-of-day effects and reports that delay impacts differ by time of day ([Transportation Research Board record](https://trid.trb.org/View/777637)). I infer that scheduled time patterns may also vary by season; the cited result motivates that hypothesis but does not directly establish a month-by-hour interaction.
- The `Month × DepPeriod` combination has 48 levels in `train.csv`, no singletons, and a median of 5,024 rows per level.

## Experiment 18 hypothesis — month-by-period category

- **Classification:** follow-up to the kept weekday-period interaction (`16a0ad0`, 0.6810; depth-4 variant `f6a3101`, 0.6814).
- **Change:** add a categorical `MonthPeriod` key from `Month` and the four six-hour departure bins; retain `Month`, `DepPeriod`, and `WeekPeriod`.
- **Why:** month and time of day are both associated with delay in U.S. airline research. A 48-level joint feature can test the inferred seasonal schedule effect with dense train support.
- **Prediction:** month-specific departure periods may improve ranking; the tree may already capture this interaction or the relationship may not transfer to 2006.
- **Comparison:** last kept `f6a3101`, Eval AUC 0.6814.

## Experiment 18 — `7eb8114` — discard

- **Result:** Eval AUC 0.6811 (`ok`), below the kept 0.6814; evaluation took about 51s.
- **Outcome:** Reverted to `f6a3101`. Month-by-period did not add useful signal beyond weekday-by-period and increased scoring time.

## Experiment 19 hypothesis — limit categories considered per split

- **Classification:** exploration (categorical split regularization).
- **Change:** set `max_cat_threshold=32`, keeping the best features and other model settings unchanged.
- **Why:** XGBoost documents this parameter as limiting categories considered in each partition-based split to prevent overfitting ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). It may regularize the high-cardinality airport features without changing the one-hot threshold that underperformed.
- **Prediction:** limiting category candidates may improve 2006 generalization; it may also exclude useful airport partitions.
- **Comparison:** last kept `f6a3101`, Eval AUC 0.6814.

## Experiment 19 — `2e91f92` — keep

- **Result:** Eval AUC 0.6817 (`ok`), improving the previous best 0.6814 by 0.0003; evaluation took about 44s.
- **Outcome:** Kept. Limiting partition category candidates improved the 2006 score. Test a more restrictive threshold to check whether the gain continues.

## Experiment 20 hypothesis — stronger category partition limit

- **Classification:** follow-up to the promising `max_cat_threshold=32` result (`2e91f92`, 0.6817).
- **Change:** lower only `max_cat_threshold` from 32 to 16.
- **Why:** the limit of 32 improved the best score. A more restrictive candidate set tests whether further regularization helps or excludes useful category groupings.
- **Prediction:** AUC may improve if high-cardinality partitions still overfit; it may fall if the airports need more candidates.
- **Comparison:** last kept `2e91f92`, Eval AUC 0.6817.

## Experiment 20 — `f0b50db` — discard

- **Result:** Eval AUC 0.6758 (`ok`), 0.0059 below the kept threshold-32 model; evaluation took about 44s.
- **Outcome:** Reverted to `2e91f92`. A threshold of 16 was too restrictive; retain 32.

## Synthesis after 20 experiments

- **What helped:** The strongest gain came from lowering tree depth (6 to 3/4), using smaller boosting steps (`0.05` with 200 trees), replacing 24 hour levels with four six-hour periods, adding a dense `DayOfWeek × DepPeriod` category, and limiting categorical partition candidates to 32. Best Eval AUC is 0.6817 at `2e91f92`, up 0.0074 from the 0.6743 baseline.
- **What did not help:** Raw route identity, carrier-hour identity, target means, cyclic/minute time features, low-cardinality one-hot splits, month-by-period, row subsampling, and depth 5 all lost. Depth 2 underfit. `max_cat_threshold=16` was much too restrictive, while 32 modestly beat the unmodified setting.
- **Current theory:** The 2006 score benefits from modest model complexity and stable, dense temporal groups. Direct sparse IDs and additional flexible encodings overfit or cost inference time. There is still room to test compact calendar interactions or a different regularizer.
- **Next direction:** Research recurring holiday/calendar effects that can be derived only from the allowed date features, then test a compact, rowwise holiday-period indicator if the evidence supports it.

## Research after the 20-experiment synthesis

- The U.S. Bureau of Transportation Statistics publishes Thanksgiving flight-delay details by flight date and reports delays at the same 15-minute threshold used here ([BTS Thanksgiving delay detail](https://transtats.bts.gov/HolidayDelay_Detail.asp)). This supports testing a holiday-period signal, but not the specific effect of every holiday window below.
- Read-only inspection of `train.csv` (no other data) shows delay rates of 0.5466 for Nov 20–30, 0.6176 for Dec 20–31/Jan 1–3, 0.5761 for Jul 1–5, 0.4263 for May 25–31, and 0.3584 for Sep 1–7; all other dates are 0.4949. The windows are broad, have 25,105 rows combined, and are exploratory on this balanced sample. These train rates are not an evaluation metric.

## Experiment 21 hypothesis — broad holiday-window category

- **Classification:** exploration (calendar feature engineering).
- **Change:** add one categorical `HolidayWindow` with five predefined date windows—Thanksgiving (Nov 20–30), winter holidays (Dec 20–Jan 3), July 4 (Jul 1–5), Memorial vicinity (May 25–31), Labor vicinity (Sep 1–7)—and `none` otherwise. Compute it rowwise from the existing month/day fields; keep the current best model and all existing features.
- **Why:** BTS tracks Thanksgiving delays, and the allowed training split shows different label rates in these broad calendar windows. The 2006 Eval AUC will determine whether the signal generalizes.
- **Prediction:** recurring travel-period effects may improve ranking, or the 2005 rates may be sample noise and shift in 2006.
- **Comparison:** last kept `2e91f92`, Eval AUC 0.6817.

## Experiment 21 — `973b25f` — keep

- **Result:** Eval AUC 0.6819 (`ok`), improving the previous best 0.6817 by 0.0002; evaluation took about 60s.
- **Outcome:** Kept. The broad calendar windows added a small gain and remain within the 5-minute evaluation limit. Test whether a pooled holiday flag retains the signal with fewer levels.

## Experiment 22 hypothesis — pool holiday periods into one flag

- **Classification:** ablation/simplification of the kept six-level `HolidayWindow` feature.
- **Change:** replace the five event labels with `holiday` versus `none`, using the same predefined calendar windows.
- **Why:** the six-level holiday feature improved AUC only slightly, while train rates varied across event windows. Pooling tests whether a general holiday-period effect transfers better than the 2005 event-specific differences.
- **Prediction:** a pooled flag may be more stable and simpler; distinct event effects may be lost.
- **Comparison:** last kept `973b25f`, Eval AUC 0.6819.

## Experiment 22 — `3a643e3` — discard

- **Result:** Eval AUC 0.6807 (`ok`), 0.0012 below the kept six-level holiday category; evaluation took about 59s.
- **Outcome:** Reverted to `973b25f`. Pooling the event windows lost useful distinctions; retain the named windows.

## Experiment 23 hypothesis — depth 3 with holiday windows

- **Classification:** follow-up to the kept holiday-window feature (`973b25f`, 0.6819).
- **Change:** lower only `max_depth` from 4 to 3, retaining the named holiday categories, weekday-period interaction, threshold 32, and current boosting settings.
- **Why:** the holiday feature adds calendar signal; a shallower model may use it without fitting extra interactions. Earlier depth comparisons were made without this feature, so the preferred depth may shift.
- **Prediction:** depth 3 may improve cross-year generalization, or depth 4 may be needed to combine holiday windows with airline/airport effects.
- **Comparison:** last kept `973b25f`, Eval AUC 0.6819.

## Experiment 23 — `e29d16b` — discard

- **Result:** Eval AUC 0.6795 (`ok`), 0.0024 below the kept depth-4 holiday model; evaluation took about 60s.
- **Outcome:** Reverted to `973b25f`. The holiday features did not shift the preferred depth downward; retain depth 4.

## Experiment 24 hypothesis — column subsampling

- **Classification:** exploration (feature-sampling regularization).
- **Change:** set `colsample_bytree=0.8` on the current best holiday model; leave all other settings unchanged.
- **Why:** the XGBoost tuning guide lists column sampling as a way to add randomness and control overfitting ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). Row subsampling at 0.8 lost, but sampling features independently may reduce reliance on unstable predictors.
- **Prediction:** modest column sampling may improve cross-year robustness, or omit a useful calendar/category feature on too many trees.
- **Comparison:** last kept `973b25f`, Eval AUC 0.6819.

## Experiment 24 — `c2febf2` — keep

- **Result:** Eval AUC 0.6833 (`ok`), improving the previous best 0.6819 by 0.0014; evaluation took about 60s.
- **Outcome:** Kept. Column subsampling improved the holiday/weekday-period model, unlike row subsampling. Test a slightly milder column sample if the clock allows a full run.

## Experiment 25 hypothesis — milder column subsampling

- **Classification:** follow-up to the kept column-sampling result (`c2febf2`, 0.6833).
- **Change:** raise only `colsample_bytree` from 0.8 to 0.9.
- **Why:** 0.8 improved AUC by 0.0014. A fraction of 0.9 retains more candidate predictors per tree while preserving some sampling randomness, testing whether the best balance is milder.
- **Prediction:** AUC may improve if 0.8 omitted useful predictors too often, or fall if stronger sampling was important.
- **Comparison:** last kept `c2febf2`, Eval AUC 0.6833.

## Experiment 25 — `7067b18` — discard

- **Result:** Eval AUC 0.6830 (`ok`), below the kept 0.6833; evaluation took about 60s.
- **Outcome:** Reverted to `c2febf2`. The 0.8 column-sample rate remains the best tested value.

## Final summary

- **Best commit:** `c2febf2`, Eval AUC **0.6833**, versus baseline 0.6743.
- **Kept approach:** depth-4 XGBoost with 200 trees at learning rate 0.05; four six-hour departure periods; the `DayOfWeek × DepPeriod` feature; named broad holiday windows; `max_cat_threshold=32`; and `colsample_bytree=0.8`.
- **What helped most:** reducing depth and using smaller boosting steps improved generalization; dense temporal interactions and holiday windows added smaller gains; column subsampling produced the largest final increment.
- **What did not help:** sparse route and carrier-hour IDs, cross-fitted target means, cyclic/minute encodings, low-cardinality one-hot splits, row subsampling, excess depth, overly restrictive category threshold 16, pooled holiday flags, and column sampling at 0.9.
- **Next direction:** if continuing, test an intermediate `colsample_bytree` between 0.8 and 0.9, or refine holiday windows with a feature chosen from known calendar rules rather than train-label rates. The holdout remains untouched for human scoring.
