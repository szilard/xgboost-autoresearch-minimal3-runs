# Research log — oct5

## Baseline — 8d9c760

Starter `train.py` with native categorical features, 100 trees, depth 6, and learning rate 0.1. Eval AUC: **0.6743**. Training took 1.4 seconds and evaluation 30.4 seconds. This is the comparison point for subsequent experiments.

## Experiment 1 — more boosting rounds (exploration)

Hypothesis: 100 trees may underfit. Increase only `n_estimators` to 300, holding features and other parameters fixed. [XGBoost's tuning notes](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) identify boosting rounds as part of the capacity tradeoff. Compare with baseline 0.6743.

Result: `ee29d1e` scored **0.6678**, down 0.0065. Training rose to 2.4 seconds. Discard. More rounds at the same learning rate appear to overfit or amplify 2005-specific patterns.

## Experiment 2 — depth 4 (follow-up)

Hypothesis: the extra rounds hurt because depth-6 trees can fit complex interactions specific to 2005. Try depth 4 with the baseline 100 rounds. XGBoost's [tuning notes](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) name `max_depth` as a primary complexity control.

Result: `eb5671d` scored **0.6789**, up 0.0046. Keep. One first attempt was interrupted before an AUC was printed; the rerun finished normally.

## Experiment 3 — 200 rounds at depth 4 (follow-up)

Hypothesis: depth-4 trees generalize better but may need more rounds to build useful interactions. Change only `n_estimators` from 100 to 200 and compare with 0.6789. This follows the [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) on capacity and rounds.

Result: `0565c2b` scored **0.6777**, down 0.0012. Discard. More rounds still hurt, though less than at depth 6.

## Experiment 4 — depth 3 (follow-up)

Hypothesis: both higher tree count and depth 6 look too flexible for transfer to 2006. Try 100 rounds at depth 3, changing depth alone from the kept depth-4 model.

Result: `7f335e4` scored **0.6798**, up 0.0009. Keep. Shallower trees still help, but the gain is smaller than the depth-6 to depth-4 change.

## Experiment 5 — depth 2 (follow-up)

Hypothesis: if shallow trees transfer better between years, depth 2 could improve further. Keep 100 rounds and all features fixed so the effect of depth is clear.

Result: `51dbdd4` scored **0.6751**, down 0.0047. Discard. Depth 3 is the best tested tree depth at 100 rounds.

## Experiment 6 — categorical departure hour (exploration)

Hypothesis: at depth 3, hour-of-day groups may help XGBoost model accumulated delays and the overnight reset while keeping the exact scheduled departure time. [Stanford flight-delay work](https://cs229.stanford.edu/proj2016/report/DuperierSauvestreLeaf-ModelingFlightDelays-report.pdf) found departure hour relevant and encoded it as a discrete feature. Derive it rowwise from `CRSDepTime`, with fixed categories 0–23.

Result: `a88c85c` scored **0.6797**, down 0.0001 from the kept model. Discard under the strict keep rule. The raw time feature already captures most of the value.

## Experiment 7 — numeric day of year (exploration)

Hypothesis: a day-of-year feature makes adjacent calendar days across month boundaries close in one feature, which could be useful with depth-3 trees. [Naul's departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) included day of year. Compute the feature from each row's month and day, using a fixed non-leap-year calendar applicable to both 2005 and 2006.

First attempt `59c7f08` crashed in training because calendar strings carry a `c-` prefix (for example `c-22`). All 200K training rows use that prefix. Discard the broken commit and retry with explicit prefix removal.

## Experiment 8 — corrected numeric day of year (follow-up)

Hypothesis unchanged from experiment 7. Remove the `c-` prefix from month and day strings inside `prepare`, then compute ordinal day using the non-leap-year offsets. This preserves rowwise meaning.

Result: `7403a9e` scored **0.6830**, up 0.0032. Keep. Training took 1.2 seconds and rowwise evaluation 35.0 seconds. Calendar proximity mattered more than hour bucketing in this setup.

## Experiment 9 — larger minimum leaf weight (follow-up)

Hypothesis: with 200K rows and high-cardinality airports, default `min_child_weight=1` allows very small leaves and may fit 2005-specific noise. Raise it to 10 on the kept depth-3 day-of-year model. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) identify this as an overfitting control.

Result: `428ad21` scored **0.6830**, exactly equal at four decimals, but added a parameter without reducing run time. Discard under the equal-score rule.

## Experiment 10 — 80% row subsampling (exploration)

Hypothesis: stochastic row sampling may reduce sensitivity to 2005-only observations, especially in sparse airport/category combinations. Try only `subsample=0.8` on the kept model. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/release_1.3.0/tutorials/param_tuning.html) lists row subsampling as a way to control overfitting.

Result: `03a47f7` scored **0.6810**, down 0.0020. Discard.

## Synthesis after 10 experiments

Shallower trees helped: depth 6 baseline 0.6743, depth 4 0.6789, depth 3 0.6798, while depth 2 fell to 0.6751. More rounds at fixed learning rate worsened both depth-6 and depth-4 models. Row subsampling also hurt, and heavier minimum leaf weight tied without a speed or simplicity benefit. Explicit departure hour added little. Numeric day of year produced the strongest gain (+0.0032), suggesting that contiguous calendar position matters and can be hard for depth-3 trees to reconstruct from categorical month and day. The current best is `7403a9e` at **0.6830**. Next, investigate calendar effects and domain interactions while preserving per-row feature semantics.

## Experiment 11 — carrier by month category (exploration)

Hypothesis: weather, operating schedules, and fleet mix can make each carrier's seasonal delay pattern distinct. A [study of airline delay effects by month](https://gssrr.org/JournalOfBasicAndApplied/article/download/1230/1168/2409) observed a significant airline–month interaction. Expose that interaction directly as one categorical feature; 236 combinations occur in `train.csv`. Fit levels on training rows and use rowwise lookup in `prepare`.

Result: `2ea9f9a` scored **0.6745**, down 0.0085. Discard. This fine-grained interaction appears to fit noise across years despite being plausible in other flight data.

## Experiment 12 — holiday proximity (exploration)

Hypothesis: traffic and staffing patterns near major US holidays have effects beyond smooth day-of-year trends. [Naul's departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) included holiday proximity. Add distance to the nearest New Year, Memorial Day, July 4, Labor Day, Thanksgiving, or Christmas anchor, allowing a one-day shift for weekday holidays between 2005 and 2006.

Result: `9827e1c` scored **0.6823**, down 0.0007. Discard. Grouping all holidays into a single distance may blur different effects.

## Experiment 13 — 512 histogram bins (follow-up)

Hypothesis: scheduled departure time has the highest gain in the kept model and 1,162 distinct training values. The default 256 numeric bins may coarsen useful time thresholds. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/release_3.2.0/parameter.html) say larger `max_bin` improves split optimality at some compute cost. Try 512 bins, changing only this parameter.

Result: `f62717a` scored **0.6822**, down 0.0008. Discard. Extra split resolution did not help transfer to 2006.

## Experiment 14 — 128 histogram bins (follow-up)

Hypothesis: if 512 bins overfit time-specific cut points, reducing from the default 256 to 128 bins could smooth continuous feature thresholds and improve year-to-year generalization. This tests the opposite direction from experiment 13, holding all else fixed.

Result: `cd3b7fb` scored **0.6812**, down 0.0018. Discard. The original 256-bin setting is best among the tested resolutions.

## Experiment 15 — departure time relative to origin schedule (exploration)

Hypothesis: a given scheduled hour can represent different parts of the operating day at different airports. [Research on airport time profiles](https://www.nature.com/articles/s41598-024-68884-9) motivates representing airport-specific schedules. Fit each origin's median scheduled departure minute on training rows only, then subtract it from each row's scheduled minute in `prepare`. This is a continuous interaction between time and airport without target leakage or row-batch aggregation.

Result: `743aa52` scored **0.6822**, down 0.0008. Discard. The airport-adjusted clock did not add value beyond raw scheduled time and origin category.

## Experiment 16 — 50 boosting rounds (follow-up)

Hypothesis: 200 rounds at depth 4 and 300 rounds at depth 6 both worsened AUC. If 100 rounds is already past the optimum with depth 3, halving to 50 may improve the 2006 score and simplify the model. Keep features and learning rate fixed.

Result: `91cef22` scored **0.6789**, down 0.0041. Discard. Fifty rounds appear underfit; the good region lies nearer 100 trees.

## Experiment 17 — smaller learning rate, more rounds (follow-up)

Hypothesis: 100 trees at eta 0.1 work, while 50 at eta 0.1 underfit and longer runs at eta 0.1 overfit. [XGBoost guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends increasing rounds when reducing eta. Test 200 trees at eta 0.05 for a smoother fit with roughly similar total step size.

Result: `07f5782` scored **0.6831**, up 0.0001. Keep under the printed-AUC rule. The improvement is small, so avoid claiming a strong generalization effect; the smoother boosting path is still worth retaining.

## Experiment 18 — smaller categorical split threshold (exploration)

Hypothesis: origin and destination each have 283 levels, and unrestricted category partitions may fit year-specific airport quirks. The kept model's saved configuration has `max_cat_threshold=64`; [XGBoost documents this parameter](https://xgboost.readthedocs.io/en/stable/python/python_api.html) as a way to prevent overfitting in partition splits. Try 16 while keeping everything else fixed.

Result: `f562ebb` scored **0.6738**, down 0.0093. Discard. The model needs richer category partitions; this regularization is too severe.

## Experiment 19 — larger categorical split threshold (follow-up)

Hypothesis: 16 choices hurt badly compared with the default 64, indicating useful airport-category combinations were excluded. Try 128 to see whether more flexible partition splits improve AUC without changing model depth or features.

Result: `0d6ddf9` scored **0.6821**, down 0.0010. Discard. The default threshold of 64 is best among 16, 64, and 128.

## Experiment 20 — one-hot splits for small categories (exploration)

Hypothesis: month and day-of-week levels may have distinct spikes that one-hot splits capture more stably than learned category partitions across years. [XGBoost's categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes the two split strategies. Set `max_cat_to_onehot=16`, which switches 7-level day-of-week and 12-level month while leaving higher-cardinality features partitioned.

Result: `9b00a77` scored **0.6826**, down 0.0005. Discard. Learned partitions remain preferable for month and weekday.

## Synthesis after 20 experiments

The best model is `07f5782` at **0.6831**, only 0.0001 above the day-of-year model with 100 trees. A lower learning rate paired with more rounds helped slightly; 50 trees underfit. Day of year remains the clearest feature improvement. Carrier–month, holiday proximity, and airport-adjusted time failed to transfer. Both tighter and looser categorical partition thresholds hurt, and one-hot splitting for small categories was weaker than partitioning. The default categorical handling is strong; the next search should consider a different tree growth or regularization approach, or a simple calendar representation that uses fewer year-specific distinctions.

## Experiment 21 — leaf-guided trees (exploration)

Hypothesis: the best depth-3 tree has at most eight leaves, but depthwise growth may spend splits on weak branches. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) describe `lossguide` as splitting the leaf with greatest loss reduction. Try eight-leaf trees with no depth limit, keeping the same boosting schedule and features.

Result: `def8660` scored **0.6822**, down 0.0009. Discard. Giving leaves more flexible depth did not help.

## Experiment 22 — DART dropout (exploration)

Hypothesis: [XGBoost's DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) explains tree dropout as a way to reduce reliance on early trees and curb overfitting. Try a modest `rate_drop=0.05` with `skip_drop=0.5`, holding the 200-round depth-3 setup. Training may be slower, but the 60-second limit will determine feasibility.

Result: `351a341` scored **0.6810**, down 0.0021, and training rose to 13.7 seconds. Discard.

## Experiment 23 — week-of-year category (exploration)

Hypothesis: day of year helped, but a numeric tree must use separate thresholds for scattered high-delay seasonal weeks. A fixed 53-level week-of-year category could group those weeks in one partition while keeping daily position. [Flight-delay research](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) supports calendar proximity; this is a coarser representation of the successful day-of-year feature. Derive it rowwise with fixed categories.

Result: `2fc3906` scored **0.6814**, down 0.0017. Discard. The week categories likely capture year-specific variation that the continuous day-of-year feature avoids.

## Experiment 24 — 300 rounds at eta 0.03 (follow-up)

Hypothesis: 200 rounds at eta 0.05 beat 100 rounds at eta 0.1 by 0.0001, suggesting smoother boosting may help. Reduce eta to 0.03 with 300 rounds, giving a similar but slightly smaller total step magnitude. This tests whether the smoothing gain continues.

Result: `1332cd2` scored **0.6823**, down 0.0008. Discard. Smoothing past the 200/0.05 setup did not help.

## Experiment 25 — stronger L2 leaf regularization (exploration)

Hypothesis: airport-category partitions may be useful but produce leaf scores sensitive to the 2005 sample. [XGBoost parameter docs](https://xgboost.readthedocs.io/en/latest/parameter.html) describe `reg_lambda` as a way to make leaf weights more conservative. Increase it from the default 1 to 5, without changing tree depth or boosting rounds.

Result: `bb327b7` scored **0.6828**, down 0.0003. Discard. The small movement suggests the default leaf regularization is adequate.

## Experiment 26 — remove distance (ablation/simplification)

Hypothesis: distance had the lowest feature gain in the kept model, and [Naul's departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) used distance only for arrival delay prediction. Removing it may eliminate a weak route proxy and simplify inference. Keep if AUC improves, or ties with the simpler code.

Result: `19e1772` scored **0.6822**, down 0.0009. Discard. Even low-gain distance contributes useful route context.

## Plateau research before experiment 27

The last three discards (`1332cd2`, `bb327b7`, `19e1772`) all moved AUC by less than 0.001. [XGBoost's monotonic-constraints tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) describes encoding a strong trend prior, while [EUROCONTROL analysis](https://www.eurocontrol.int/publication/eurocontrol-data-snapshot-59-better-first-wave-performance) explains how delays accumulate through the operating day. Test this prior as a distinct approach rather than another small parameter tweak.

## Experiment 27 — increasing departure-time constraint (exploration)

Hypothesis: later scheduled departures generally inherit more disruptions. Constraining `CRSDepTime` to have a nondecreasing effect may prevent year-specific time wiggles in the highest-gain feature. Other features remain unconstrained, so interactions can still adjust predictions.

Result: `73bdc39` scored **0.6813**, down 0.0018. Discard. The departure-time effect needs local exceptions; a global monotonic prior is too rigid.

## Experiment 28 — intermediate boosting schedule (follow-up)

Hypothesis: 100 trees at eta 0.1 scored 0.6830, 200 at eta 0.05 scored 0.6831, and 300 at eta 0.03 fell to 0.6823. An intermediate 150 trees at eta 0.07 may balance smoothness and fit. It is a targeted interpolation between the two top schedules, not a broad hyperparameter sweep.

Result: `50d1635` scored **0.6829**, down 0.0002. Discard. The 200/0.05 schedule remains best under the printed-AUC rule.

## Final summary

Best Eval AUC: **0.6831** at kept commit `07f5782`, versus the baseline **0.6743** at `8d9c760` (+0.0088). The branch ends at the best commit. The run logged 28 experiments after baseline: four improved commits, 23 discards, and one corrected parsing crash.

What worked: depth 3 generalized better than depth 6 or 4; numeric day of year added a substantial gain; 200 trees at learning rate 0.05 edged out 100 trees at 0.1. The most convincing gain is the calendar feature, while the final boosting improvement is only 0.0001 at printed precision.

What did not: deeper or more numerous trees at eta 0.1, depth 2, categorical departure hour or week, carrier–month interaction, holiday-distance aggregation, origin-adjusted departure time, row subsampling, stronger leaf regularization, altered categorical thresholds/one-hot handling, changed histogram bins, leaf-guided growth, DART, a monotonic departure-time constraint, and removing distance.

Next research direction: test a small `gamma` penalty on the kept model, and explore date representations that target a specific holiday period rather than combining all holidays into one distance. Recheck any tiny eval gains on the human-only holdout after the run; the agent has not accessed it.
