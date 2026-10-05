# Research log — oct5-2026

## Baseline
- Commit: `b15ec66`
- Result: Eval AUC 0.6743 (`ok`); starter `train.py` unchanged.
- The baseline uses native categorical columns for calendar fields, carrier, origin, and destination, with scheduled departure time and distance as numeric inputs.
- Initial research: XGBoost's tuning guide emphasizes that preprocessing can matter as much as model tuning and describes regularization through tree complexity and sampling. The categorical tutorial explains native category partitioning and one-hot splits. Sources: [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [XGBoost categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). A flight-delay feature-engineering project groups useful inputs around timing, airport/location, and carrier, which match the columns available here; its unavailable weather/aircraft details are outside this dataset. Source: [UC Berkeley flight-delay feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches).

## Experiment 1 — directed route category (exploration)
- Hypothesis: native categorical handling of `Origin->Dest` can expose route-specific delay patterns beyond separate origin and destination effects. The train-only inspection found 4,290 directed routes across 200,000 rows (median 32 rows per route). Levels are fitted once on train; `prepare(df)` derives the route from each row and maps unseen routes to missing.
- Research basis: XGBoost supports native category splits with category levels declared on the training data ([categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)); flight-delay feature work groups airport/location as a useful feature family ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)).
- Result: Eval AUC 0.6667 (`ok`), down from 0.6743; evaluation took 44.7s. Discarded. The high-cardinality directed route category did not transfer well to the 2006 evaluation split and also increased row-wise preparation cost. This is consistent with route-specific categories being too sparse or unstable across years, though the run does not distinguish those causes.

## Experiment 2 — scheduled departure hour category (exploration)
- Hypothesis: extracting the hour from HHMM as a low-cardinality categorical feature lets trees group nonadjacent hours with similar delay risk, while retaining raw `CRSDepTime` preserves fine timing. This differs from the prior route interaction by testing a compact temporal encoding instead of a high-cardinality geographic combination.
- Research basis: XGBoost's tuning guide notes that preprocessing can be as important as parameter tuning and calls out categorical handling; flight-delay feature work explicitly includes departure-hour bins ([XGBoost guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). Hour levels are fitted once on train and looked up row-wise in `prepare`.
- Result: Eval AUC 0.6747 (`ok`), up 0.0004 from the previous kept baseline; evaluation took 35.2s. Kept as a small improvement.

## Experiment 3 — reduce tree depth (follow-up)
- Hypothesis: keep the small `DepHour` gain but reduce `max_depth` from 6 to 4. Shallower trees may transfer better across the 2005-to-2006 split by limiting higher-order interactions and should also reduce training/inference cost.
- Research basis: XGBoost's tuning guide identifies `max_depth` as a direct model-complexity control and notes that more complex trees require more data ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: Eval AUC 0.6789 (`ok`), up 0.0042 from the previous kept version; training took 0.4s and evaluation 35.4s. Kept.

## Experiment 4 — test depth 3 (follow-up)
- Hypothesis: the large gain from depth 6 to 4 may continue with depth 3, or depth 3 may begin to underfit. Change only `max_depth` from the current best value 4 to 3 to map the complexity tradeoff.
- Research basis: XGBoost's tuning guide identifies `max_depth` as a direct complexity control ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: Eval AUC 0.6797 (`ok`), up 0.0008 from the previous kept version; training took 0.3s and evaluation 35.0s. Kept. The depth trend continues to improve from 6 to 4 to 3.

## Experiment 5 — test depth 2 (follow-up)
- Hypothesis: the kept results continue to improve as depth drops (6: 0.6747, 4: 0.6789, 3: 0.6797); depth 2 tests whether this regularization trend continues or crosses into underfitting. Change only `max_depth` from 3 to 2.
- Research basis: XGBoost's tuning guide recommends treating depth as a complexity/bias-variance control ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: Eval AUC 0.6754 (`ok`), down 0.0043 from depth 3; training took 0.3s and evaluation 34.7s. Discarded and restored depth 3. The current depth sweep peaks at 3; depth 2 likely underfits relative to 3.

## Experiment 6 — smaller boosting steps, more rounds (exploration)
- Hypothesis: with depth 3 retained, 200 trees at learning rate 0.05 may improve ranking through finer boosting updates compared with 100 trees at 0.1. This follows the guide's paired advice to reduce `eta` and increase the round count.
- Research basis: [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).
- Result: Eval AUC 0.6794 (`ok`), down 0.0003 from the previous kept version; evaluation took 35.3s. Discarded and restored `de63d03` (100 trees, learning rate 0.1).

## Experiment 7 — raise minimum child weight (exploration)
- Hypothesis: retain the best depth-3 model but raise `min_child_weight` from its default 1 to 5, requiring more Hessian weight in each child and potentially suppressing weak, noisy splits.
- Research basis: XGBoost's tuning guide lists `min_child_weight` among the direct model-complexity controls ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: Eval AUC 0.6797 (`ok`), equal to the previous kept version; training took 0.4s and evaluation 35.5s, so it was not simpler or faster. Discarded under the keep rule and restored `de63d03`.

## Experiment 8 — weekday-by-hour categorical interaction (exploration)
- Hypothesis: weekday-specific delay patterns may vary across departure hours. A train-fitted `DayOfWeek->DepHour` categorical lets native categorical splits group the joint combinations. Train-only inspection found 158 observed combinations (median 1,590 rows per combination; 10th percentile 20), denser overall than the route categories that hurt the prior run. The feature is computed per row in `prepare`; unseen combinations map to missing.
- Research basis: flight-delay feature work identifies day-of-week effects and time-of-day schedules as temporal patterns ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)); XGBoost documents how tree paths model feature interactions and notes that unconstrained interactions may fit spurious patterns ([interaction guide](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html)).
- Result: Eval AUC 0.6806 (`ok`), up 0.0009 from the previous kept version; evaluation took 42.4s. Kept.

## Experiment 9 — row subsampling (exploration)
- Hypothesis: `subsample=0.8` may make the depth-3 trees less dependent on training-specific patterns and improve transfer to 2006. Change only this regularization parameter from its default of 1.0.
- Research basis: XGBoost's tuning guide describes `subsample` as a way to add randomness and improve robustness ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: Eval AUC 0.6793 (`ok`), down 0.0013 from the previous kept version; evaluation took 42.1s. Discarded and restored `5e7ab12`.

## Experiment 10 — month-by-hour categorical interaction (follow-up)
- Hypothesis: the successful weekday-by-hour feature may benefit from a seasonal counterpart. Add train-fitted `Month->DepHour` to let native categorical splits group hours differently by month. Train-only inspection found 265 observed combinations (median 918 rows; 10th percentile 16), so sparse levels are a risk.
- Research basis: flight-delay feature research treats season and time of day as related temporal patterns ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)).
- Result: Eval AUC 0.6789 (`ok`), down 0.0017 from the previous kept version; evaluation took 49.9s. Discarded and restored `5e7ab12`.

## Synthesis after 10 experiments
- Best kept result: Eval AUC 0.6806, commit `5e7ab12` (`DepHour` and `DayOfWeek->DepHour`, `max_depth=3`).
- What helped: representing scheduled time as an hour category gave a small gain; reducing depth from 6 to 4 and then 3 gave the largest improvement; the weekday-by-hour category added another 0.0009.
- What did not help: the 4,290-level route key dropped AUC and slowed evaluation; depth 2 underfit; 200 trees at learning rate 0.05 and `subsample=0.8` were slightly worse; `min_child_weight=5` tied without making the code faster; the month-by-hour category reduced AUC and added substantial evaluation overhead.
- Current theory: generalization across years improves with shallower trees and compact temporal features that have enough training support. Very high-cardinality or sparse combinations appear less reliable. The weekday-by-hour effect is more useful than the month-by-hour feature in this setup.
- Next direction: revisit tree depth with the now-kept weekday-hour feature in place. A depth-4 tree may exploit that compact interaction differently from the earlier depth sweep; test it as a single-parameter change, then continue with other regularization or timing ideas.

## Experiment 11 — depth 4 with weekday-hour feature (follow-up)
- Hypothesis: the new `DOWHour` feature may change how much tree depth is useful. Test `max_depth=4` while keeping the current best features and all other parameters fixed; this may capture an additional interaction or overfit.
- Research basis: XGBoost's tuning guide describes tree depth as a bias-variance / complexity control ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: Eval AUC 0.6791 (`ok`), down 0.0015 from the previous kept version; evaluation took 41.7s. Discarded and restored `5e7ab12`.

## Experiment 12 — raise one-hot threshold for categorical splits (exploration)
- Hypothesis: use `max_cat_to_onehot=25` so features with fewer than 25 categories (including the 24-hour `DepHour`) use category-equality splits, while the 158-level `DOWHour` and airport features retain partition-based splits. This may let the model isolate specific hour categories while preserving grouping for larger interactions.
- Research basis: the installed XGBoost is 3.4.1; official categorical docs describe one-hot equality splits versus category partitioning and explain that `max_cat_to_onehot` selects between them ([categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html), [parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Result: Eval AUC 0.6818 (`ok`), up 0.0012 from the previous kept version; training took 0.3s and evaluation 42.1s. Kept. The result supports further controlled testing of which low-cardinality features benefit from one-hot splits.

## Experiment 13 — include day-of-month in one-hot features (follow-up)
- Hypothesis: raising `max_cat_to_onehot` from 25 to 32 adds only the 31-level `DayofMonth` feature to the one-hot set; the 158-level `DOWHour` and 283-level airport features remain partitioned. This isolates whether independent day-of-month splits improve AUC.
- Research basis: XGBoost uses one-hot splits for features with fewer categories than `max_cat_to_onehot`, and partitions the rest ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Result: Eval AUC 0.6813 (`ok`), down 0.0005 from the previous kept version; evaluation took 41.8s. Discarded and restored `6328667`. The 31-level `DayofMonth` is better left partitioned in this configuration.

## Experiment 14 — isolate one-hot departure hour (follow-up)
- Hypothesis: `max_cat_to_onehot=21` keeps the 20-level carrier, month, and weekday categories one-hot but moves the 24-level `DepHour` back to partitioning. This tests whether the gain at threshold 25 came specifically from independent hour splits.
- Research basis: XGBoost's categorical parameter uses one-hot splits for categories below the threshold and partitioning otherwise ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Result: Eval AUC 0.6818 (`ok`), equal to the previous kept version; training took 0.3s and evaluation 42.2s. Not simpler or faster, so discarded and restored `6328667` (threshold 25).

## Experiment 15 — expand categorical partition budget (exploration)
- Hypothesis: raise `max_cat_threshold` to 256 while keeping `max_cat_to_onehot=25`. This lets partition search consider all 158 `DOWHour` categories, potentially improving a feature that helped AUC; airport features have 283 levels and remain above the limit.
- Research basis: XGBoost documents `max_cat_threshold` as a cap on categories considered for each partition split and a way to prevent overfitting ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Result: Eval AUC 0.6809 (`ok`), down 0.0009 from the previous kept version; evaluation took 42.0s. Discarded and restored `6328667`.

## Research after plateau
Three successive categorical-threshold/partition experiments failed to beat 0.6818 by at least 0.001. Fresh research suggests testing cyclic encodings: scikit-learn's time-feature guide uses sine/cosine transforms to represent periodic hours without a discontinuity at the period boundary ([guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)); an airline disruption study encodes scheduled flight times as periodic vectors on a 24-hour clock ([study](https://www.sciencedirect.com/science/article/pii/S2666827021000517)). These sources motivate an experiment, but do not establish that the transformation helps this XGBoost classifier.

## Experiment 16 — cyclic departure-time features (exploration)
- Hypothesis: sine/cosine features from scheduled minutes-of-day may represent smooth periodic timing and midnight adjacency better than a raw HHMM threshold, complementing the existing `DepHour` and `DOWHour` features.
- Research basis: scikit-learn's time-feature guide shows sine/cosine encodings for periodic hours ([guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)); an airline disruption study represents scheduled time on a 24-hour periodic clock ([study](https://www.sciencedirect.com/science/article/pii/S2666827021000517)).
- Implementation: `DepTimeSin` and `DepTimeCos` are derived per row in `prepare` using the row's scheduled time in minutes after midnight; no data-fitted statistic is needed.
- Result: Eval AUC 0.6812 (`ok`), down 0.0006 from the previous kept version; evaluation took 46.5s. Discarded and restored `6328667`.

## Experiment 17 — carrier-by-month categorical interaction (exploration)
- Hypothesis: carrier-specific operating differences may vary seasonally. Add a train-fitted `UniqueCarrier->Month` categorical. Inspection found 236 observed combinations (median 788 rows, minimum 55), so the interaction is less sparse than the failed month-hour feature. No row counts are used as model inputs; only the row's composite category is added.
- Research basis: flight-delay feature research identifies both temporal patterns (including month) and carrier as relevant feature families ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)).
- Result: Eval AUC 0.6751 (`ok`), down 0.0067 from the previous kept version; evaluation took 49.2s. Discarded and restored `6328667`.

## Experiment 18 — cross-fitted categorical delay rates (exploration)
- Hypothesis: smoothed delay-rate encodings may recover useful carrier, airport, route, and weekday-hour tendencies more directly than categorical splits, while regularizing sparse groups.
- Research basis: a flight-delay study target-encodes categorical features using their >15-minute delay rates ([study](https://www.mdpi.com/2226-4310/8/6/152)); scikit-learn explains that training rows must be cross-fitted so each row is encoded using other folds, preventing self-target leakage ([cross-fitting guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)).
- Implementation: five folds are assigned by hashing predictor columns only. Module-level lookup maps for `Carrier`, `Origin`, `Dest`, `Route`, and `DOWHour` use the other four folds with smoothing strength 50. `prepare` reproduces the row's fold and looks up only the train-fitted rate. No count is passed to the model and no evaluation labels enter a lookup.
- Result: Eval AUC 0.6805 (`ok`), down 0.0013 from the previous kept version; evaluation took 59.5s. Discarded and restored `6328667`. The full set of five rate features did not improve AUC and added about 18 seconds to row-wise evaluation.

## Experiment 19 — remove route delay-rate encoding (ablation)
- Hypothesis: the full five-feature target-encoding set fell 0.0013; remove only the smoothed route rate, retaining cross-fitted carrier, origin, destination, and weekday-hour rates. This tests whether sparse route estimates caused the decline.
- Implementation: same predictor-hash five-fold assignment, fold-excluded smoothed rates, and strength 50 as Experiment 18. `RouteDelayRate` is omitted; no counts are passed as features and no evaluation labels enter the lookups.
- Result: Eval AUC 0.6821 (`ok`), up 0.0003 from the previous best; evaluation took 57.1s. Kept. Omitting the route rate recovered the score and shaved about 2.4 seconds from evaluation compared with the full encoding set.

## Experiment 20 — ablate weekday-hour rate (follow-up)
- Hypothesis: test whether `DOWHourDelayRate` adds value beyond the retained native `DOWHour` category. Remove only that rate encoding; retain cross-fitted rates for carrier, origin, and destination.
- If AUC ties, the reduced lookup set is simpler and may shorten the row-wise evaluator.
- Result: Eval AUC 0.6809 (`ok`), down 0.0012 from the previous kept version; evaluation took 56.7s. Discarded and restored `f5ccb93`; the weekday-hour rate adds value alongside the native category.

## Experiment 21 — reduce target-rate smoothing (follow-up)
- Hypothesis: the retained carrier, origin, destination, and weekday-hour groups are denser than routes; reducing smoothing strength from 50 to 20 may preserve more category-specific signal. This changes only the shrinkage strength for the four retained target rates.
- Result: Eval AUC 0.6808 (`ok`), down 0.0013 from the previous kept version; evaluation took 57.0s. Discarded and restored `f5ccb93` (smoothing strength 50).

## Experiment 22 — increase target-rate smoothing (follow-up)
- Hypothesis: 20 was worse than 50, so test stronger shrinkage at 100 to see whether carrier/origin/destination/weekday-hour rates transfer better when pulled further toward the fold prior. Change only the smoothing strength.
- Result: Eval AUC 0.6815 (`ok`), down 0.0006 from the previous kept version; evaluation took 58.6s. Discarded and restored `f5ccb93` (smoothing strength 50).

## Experiment 23 — ablate carrier delay-rate encoding (follow-up)
- Hypothesis: carrier is already an explicit one-hot feature under `max_cat_to_onehot=25`; remove only `CarrierDelayRate` to test whether the target-rate feature adds useful signal or redundancy.
- Result: Eval AUC 0.6804 (`ok`), down 0.0017 from the previous kept version; evaluation took 56.2s. Discarded and restored `f5ccb93`; the carrier rate adds value despite the one-hot carrier column.

## Experiment 24 — ablate origin delay-rate encoding (follow-up)
- Hypothesis: test whether `OriginDelayRate` adds predictive signal beyond the native origin category. Remove only that encoding; retain carrier, destination, and weekday-hour rates.
- Result: Eval AUC 0.6821 (`ok`), equal to the previous best; evaluation took 56.4s (0.7s faster). Kept the simpler lookup set and commit `9a6deb9`.

## Experiment 25 — ablate destination delay-rate encoding (follow-up)
- Hypothesis: remove only `DestDelayRate` to test whether it adds value beyond the native destination category. Retain carrier and weekday-hour rates.
- Result: Eval AUC 0.6816 (`ok`), down 0.0005 from the previous best; evaluation took 54.3s. Discarded and restored `9a6deb9`.

## Experiment 26 — depth 2 with retained delay rates (follow-up)
- Hypothesis: target-rate inputs expose group-level propensities directly, so the current feature set may need less tree depth than the categorical-only model. Test `max_depth=2` with all retained features and other parameters unchanged.
- Result: Eval AUC 0.6798 (`ok`), down 0.0023 from the previous best; evaluation took 55.7s. Discarded and restored `9a6deb9`.

## Experiment 27 — depth 4 with retained delay rates (follow-up)
- Hypothesis: the additional carrier, destination, and weekday-hour rates may alter the useful tree capacity. Test depth 4 with the current best encoding set; prior depth-4 results predate these numeric features.
- Result: Eval AUC 0.6793 (`ok`), down 0.0028 from the previous best; evaluation took 56.4s. Discarded and restored `9a6deb9`.

## Experiment 28 — feature subsampling (exploration)
- Hypothesis: `colsample_bytree=0.8` may reduce reliance on a small set of features and improve transfer. This samples columns per tree, distinct from the earlier row-subsampling attempt.
- Research basis: XGBoost's tuning guide identifies `colsample_bytree` as a regularization option ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: Eval AUC 0.6816 (`ok`), down 0.0005 from the previous best; evaluation took 56.4s. Discarded and restored `9a6deb9`.

## Experiment 29 — small split penalty (exploration)
- Hypothesis: `gamma=0.1` may suppress weak splits and slightly improve cross-year generalization. All other model settings remain fixed.
- Research basis: XGBoost's tuning guide lists `gamma` as a direct control on tree complexity ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Result: Eval AUC 0.6821 (`ok`), tied the previous best; evaluation took 55.8s versus 56.4s for `9a6deb9`. Kept under the equal-AUC/faster rule.

## Final summary
- Best Eval AUC: 0.6821, commit `bd192f4` (baseline `b15ec66`: 0.6743; gain: 0.0078). The final kept model uses native `DepHour` and `DOWHour` categories, `max_cat_to_onehot=25`, depth 3, and cross-fitted smoothed delay rates for carrier, destination, and weekday-hour; the origin-rate ablation tied with a slightly faster evaluator, and `gamma=0.1` tied again with a small additional timing improvement.
- What helped: reducing depth from 6 to 3, one-hot splits for low-cardinality categories, the weekday-hour feature, and cross-fitted group delay rates (with route and origin rates omitted).
- What did not: directed route categories/rates, month-hour and carrier-month interactions, cyclic time features, deeper or shallower trees, lower learning rate with more rounds, row/column subsampling, and expanded categorical partition limits. Smoothing 20 or 100 was worse than 50.
- Next: the holdout evaluation can check whether the 2006 eval gains generalize. Further experiments could focus on leakage-safe, time-aware reliability features and cross-fitted rate calibration.
