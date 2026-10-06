# Research log — oct6

## Baseline — `b15ec66`

- Ran the starter `train.py` without changes through `harness.py`.
- Eval AUC: **0.6743**; status: **ok**; artifact saved.
- Baseline uses the raw scheduled departure time (`CRSDepTime`) as one numeric value alongside categorical month/day/carrier/airport features and numeric distance.

## Initial research

- The official [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend controlling tree complexity and adding row/column sampling when overfitting is a concern; the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explains the roles of depth, child weight, learning rate, and sampling.
- XGBoost's [categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) confirms that categorical DataFrame columns with `enable_categorical=True` use categorical splits, so an extracted scheduled hour can be represented as a categorical feature.
- A [UC Berkeley flight-delay feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports that delay patterns vary by scheduled hour, including worsening late at night, and discusses carrier and distance as useful schedule-level predictors. This supports testing a more explicit time-of-day representation while preserving the baseline inputs.

## Experiment 1 — `fdafcab` — keep

- **Class:** exploration.
- **Hypothesis:** a categorical scheduled hour can expose non-monotonic hour-of-day effects that a single numeric HHMM feature cannot express as directly, while retaining all baseline signals.
- **Change:** added `CRSDepHour`, derived per row inside `prepare()` and represented categorically using hour levels fitted from `train.csv`; kept all original columns and model parameters.
- **Result:** Eval AUC **0.6747** (up from 0.6743; status `ok`). Kept under the four-decimal AUC rule.
- **Observation:** the small gain supports testing a cleaner numeric encoding of scheduled time next. Training-only rates also rose from morning to evening, with very few observations in some late-night hours.

## Experiment 2 — `2f16df6` — discard

- **Class:** follow-up to the categorical-hour result.
- **Hypothesis:** converting packed HHMM to elapsed minutes would give the numeric time feature uniform spacing, while keeping the categorical hour signal.
- **Change:** replaced raw `CRSDepTime` with `(hour * 60 + minute)`; retained `CRSDepHour`, all other features, and parameters.
- **Result:** Eval AUC **0.6747**, equal to the best at four decimals; status `ok`.
- **Decision:** discarded because the score tied and the extra conversion did not simplify or speed up the code. This does not establish a benefit from the minute representation.

## Experiment 3 — `08ac293` — discard

- **Class:** exploration.
- **Hypothesis:** a directed `Origin→Dest` category could expose stable route-specific delay risk that separate airport categories miss. Flight-delay work studies route and spatial context (for example, [route/context features in a departure-delay model](https://www.sciencedirect.com/science/article/pii/S092523122101612X)).
- **Change:** added one categorical route feature using route levels fitted from `train.csv`; unseen routes map to missing.
- **Result:** Eval AUC **0.6660** (down from 0.6747); status `ok`. Artifact grew from about 2.6 MB to 17.5 MB, and evaluation took 50.8 seconds rather than about 35 seconds.
- **Decision:** discarded. The high-cardinality route category overfit or otherwise failed to transfer from 2005 to 2006 in this representation.

## Experiment 4 — `63a982b` — keep

- **Class:** exploration of tree capacity, prompted by the 2005-to-2006 shift and the XGBoost [parameter tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) on controlling complexity.
- **Hypothesis:** depth-6 trees may fit noisy feature combinations; depth 4 may generalize better to the next year.
- **Change:** reduced only `max_depth` from 6 to 4.
- **Result:** Eval AUC **0.6789** (up from 0.6747); status `ok`. Training fell to 0.4 seconds and the artifact to about 0.7 MB.
- **Observation:** shallower trees improved both ranking and size/time, supporting stronger regularization on this temporal split.

## Experiment 5 — `49874fc` — discard

- **Class:** follow-up to the shallower-tree improvement.
- **Hypothesis:** row subsampling could make each tree less sensitive to noisy 2005 examples and complement reduced depth, following XGBoost's [tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).
- **Change:** set `subsample=0.8`; kept depth 4 and all features.
- **Result:** Eval AUC **0.6781** (down from 0.6789); status `ok`.
- **Decision:** discarded. Row sampling did not improve the held-out year.

## Experiment 6 — `1ab8d45` — discard

- **Class:** follow-up regularization experiment.
- **Hypothesis:** increasing `min_child_weight` from its default could suppress small, noisy leaves while retaining depth 4.
- **Change:** set `min_child_weight=5` only; all features and other parameters matched the best run.
- **Result:** Eval AUC **0.6789**, tied with the best; status `ok`.
- **Decision:** discarded because there was no AUC improvement and no measurable speed or simplicity benefit.

## Experiment 7 — `17c0c0c` — discard

- **Class:** follow-up to the high-cardinality route result.
- **Hypothesis:** limiting category candidates in partition splits could regularize the existing airport categories; the XGBoost [categorical parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_threshold` is intended to help prevent overfitting.
- **Change:** set `max_cat_threshold=32` only.
- **Result:** Eval AUC **0.6784** (down from 0.6789); status `ok`.
- **Decision:** discarded. This is the third consecutive discard within 0.001 AUC of the best; pause for targeted research before the next experiment.

## Experiment 8 — `04aa02a` — discard

- **Class:** follow-up to departure-hour and minute-of-day experiments.
- **Hypothesis:** sine/cosine features with a 1,440-minute period would make the midnight wraparound explicit, as described in flight-delay feature literature (see the [TU Delft flight-delay study](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)).
- **Change:** replaced raw HHMM with per-row `DepTimeSin` and `DepTimeCos`, retaining categorical hour.
- **Result:** Eval AUC **0.6789**, tied with the best; status `ok`. Evaluation took 39.1 seconds versus 35.0 seconds for the best.
- **Decision:** discarded because the score tied and evaluation was slower. The cyclic representation did not beat the simpler raw time plus hour feature on this split.

## Experiment 9 — `044bc6e` — crash

- **Class:** exploration of annual calendar encoding.
- **Hypothesis:** day-of-year sine/cosine features may represent seasonal recurrence more smoothly than separate unordered month/day categories. Flight-delay literature describes encoding day-of-year on a 365-day cycle; see the [TU Delft review](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1).
- **Change:** derive a non-leap day number from month/day, then add sine and cosine values.
- **Result:** training crashed before evaluation (`Eval AUC` unavailable; recorded as 0.0000). The data encodes calendar categories as strings such as `c-11`, so the first implementation's numeric cast failed.
- **Next:** correct the per-row parsing and rerun the same idea.

## Experiment 10 — `f8a5db9` — keep

- **Class:** exploration of annual seasonality, informed by flight-delay literature describing day-of-year sine/cosine encoding (the [TU Delft review](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1) summarizes this for flight-delay models).
- **Hypothesis:** the model can use a smooth annual cycle to share signal across adjacent calendar days, especially across December/January, where separate month/day categories have no natural ordering.
- **Change:** parsed the `c-N` month/day labels per row, derived a non-leap day-of-year, and added sine/cosine features; retained the original calendar fields and depth-4 model. The first implementation crashed on the encoded labels and is logged separately above; this commit fixes that parsing.
- **Result:** Eval AUC **0.6820** (up from 0.6789); status `ok`. Kept.
- **Observation:** annual seasonality added useful ranking signal even though cyclic encoding of time-of-day did not.

## Synthesis after 10 experiment runs

- **What helped:** `max_depth=4` gave the largest single gain (+0.0042 AUC) and reduced model size/training time. Categorical scheduled hour added a small gain. The annual day-of-year sine/cosine pair then raised the best to **0.6820**.
- **What did not help:** replacing HHMM with minutes-since-midnight tied; cyclic time-of-day tied and slowed evaluation. Row subsampling, stronger child-weight regularization, and a lower categorical split threshold did not beat the best. The explicit directed route category sharply reduced AUC and greatly enlarged the artifact.
- **Current theory:** the year-to-year split rewards simpler trees and smooth calendar seasonality. High-cardinality identities or interactions can memorize 2005 patterns without carrying to 2006.
- **Next direction:** preserve the annual-cycle gain and test categorical split strategy on low-cardinality fields (month, weekday, carrier, and hour), then consider a modest carrier-by-hour interaction if low-cardinality encoding does not help. XGBoost documents one-hot versus partition splits in its [categorical-data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

## Experiment 11 — `b24a4ef` — discard

- **Class:** follow-up from the 10-run synthesis.
- **Hypothesis:** one-hot splits may let the model isolate specific month, weekday, carrier, or hour levels more directly, while keeping high-cardinality airport codes on partition splits.
- **Change:** set `max_cat_to_onehot=32`; the [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents the threshold between one-hot and partition splits.
- **Result:** Eval AUC **0.6809** (down from 0.6820); status `ok`.
- **Decision:** discarded. This split strategy did not help the low-cardinality calendar and carrier fields on the 2006 evaluation year.

## Experiment 12 — `cc18d90` — discard

- **Class:** interaction exploration proposed in the 10-run synthesis.
- **Hypothesis:** a carrier-by-hour category could capture airline-specific time-of-day behavior, which separate carrier and hour features may not express as directly. Flight-delay work discusses carrier-specific practices and hour-dependent delay accumulation (see the [UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). The training data contains 401 such combinations, with median support 360.
- **Change:** added a train-fitted categorical `CarrierDepHour` feature; unseen combinations map to missing.
- **Result:** Eval AUC **0.6787** (down from 0.6820); status `ok`. Evaluation increased to 52.9 seconds and the artifact to 1.0 MB.
- **Decision:** discarded. The direct interaction category did not generalize to 2006.

## Experiment 13 — `75b1438` — keep

- **Class:** ablation/simplification following the annual-cycle gain.
- **Hypothesis:** the day-of-year sine/cosine pair may represent seasonality more smoothly than separate Month and DayofMonth categories, which can overfit individual calendar levels.
- **Change:** removed Month and DayofMonth from the model input categories but still used them per row to compute day-of-year; retained all other inputs and settings.
- **Result:** Eval AUC **0.6832** (up from 0.6820); status `ok`. Evaluation fell from 44.9 to 37.3 seconds.
- **Observation:** the annual cycle appears to carry seasonal signal more efficiently than the two discrete calendar inputs on this temporal split.


## Experiment 14 — `df4ab78` — discard

- **Class:** ablation/simplification of the original categorical-hour gain.
- **Hypothesis:** raw HHMM plus annual seasonality may be sufficient without a separate categorical hour.
- **Change:** removed `CRSDepHour` and its train-fitted levels; retained raw `CRSDepTime`, annual cycle, and the reduced calendar feature set.
- **Result:** Eval AUC **0.6828** (down from 0.6832); status `ok`. Evaluation was faster at 32.2 seconds.
- **Decision:** discarded because AUC fell; the hour category still adds a small amount alongside the annual cycle.

## Experiment 15 — `6d078d9` — discard

- **Class:** follow-up to the annual-cycle feature.
- **Hypothesis:** a second Fourier harmonic could represent semiannual structure and distinguish the summer and winter peaks visible in training-only monthly rates. The [TU Delft flight-delay review](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1) describes annual cyclic encodings; Fourier-seasonality literature models more complex seasonal shape with additional harmonics.
- **Change:** added only `sin(2θ)` and `cos(2θ)` for the same 365-day cycle.
- **Result:** Eval AUC **0.6825** (down from 0.6832); status `ok`. Evaluation took 40.4 seconds.
- **Decision:** discarded. The fundamental annual cycle is useful; this extra harmonic did not improve transfer to 2006.

## Experiment 16 — `f11dbf2` — discard

- **Class:** follow-up hyperparameter exploration to the depth-4 result, following XGBoost's [tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) on pairing smaller steps with more rounds.
- **Hypothesis:** 200 trees at learning rate 0.05 could refine the depth-4 updates and improve generalization.
- **Change:** doubled `n_estimators` from 100 to 200 and halved `learning_rate` from 0.1 to 0.05.
- **Result:** Eval AUC **0.6829** (down from 0.6832); status `ok`. Training took 0.8 seconds and evaluation 37.6 seconds.
- **Decision:** discarded. The original 100-tree configuration remains better.

## Experiment 17 — `d5cd65a` — discard

- **Class:** follow-up seasonal feature exploration.
- **Hypothesis:** a four-level meteorological season feature could capture broad winter/summer peaks more directly than a single annual cycle. A flight-delay study includes season and holidays as periodic inputs ([Wang et al., 2022](https://doi.org/10.1049/itr2.12183)).
- **Change:** added a per-row winter/spring/summer/fall category from month while retaining annual sine/cosine features.
- **Result:** Eval AUC **0.6825** (down from 0.6832); status `ok`.
- **Decision:** discarded. The smoother annual encoding remains stronger than this coarse category.

## Experiment 18 — `3e408ff` — discard

- **Class:** feature exploration following the airport-schedule plateau research.
- **Hypothesis:** airports may have different departure-time banks; a flight's scheduled time relative to its origin's typical schedule could expose this context to a shallow tree. Prior delay-prediction work studies airport-level spatial-temporal dependencies and airport status ([Zhang et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)). This experiment used schedule times only, not target-derived statistics.
- **Change:** added the difference between each flight's scheduled departure minute and the training-set median scheduled minute for its origin.
- **Result:** Eval AUC **0.6827** (down from 0.6832); status `ok`. Evaluation took 41.5 seconds; artifact remained 0.7 MB.
- **Decision:** discarded. The single origin-wide schedule center did not improve transfer to 2006.

## Experiment 19 — `e452737` — discard

- **Class:** follow-up feature exploration to the origin schedule offset.
- **Hypothesis:** airport departure schedules may vary by weekday, so the flight's position relative to its origin's weekday-specific median schedule could be more informative than the all-week center. Airport-level delay work motivates spatial and temporal structure ([Zhang et al., 2021](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)). The lookup used only non-target scheduled times, with the origin-wide median as fallback.
- **Change:** added minutes from the train-fitted origin-and-weekday median scheduled departure.
- **Result:** Eval AUC **0.6824** (down from 0.6832); status `ok`. Evaluation took 47.1 seconds; artifact was 0.8 MB.
- **Decision:** discarded. Weekday-specific schedule centering did not improve transfer to 2006.

## Experiment 20 — `26166c6` — discard

- **Class:** follow-up feature exploration to airport-specific schedule centering.
- **Hypothesis:** an origin's scheduled departure banks may shift seasonally, so relative position against the origin-month median could capture a pattern beyond annual delay seasonality. Airport delay research describes temporal variation in airport profiles ([airport time-profile study](https://www.nature.com/articles/s41598-024-68884-9)). The lookup used only scheduled times from training data.
- **Change:** added the difference between each flight's scheduled departure minute and the train-fitted median for its origin and month, falling back to the origin-wide median.
- **Result:** Eval AUC **0.6823** (down from 0.6832); status `ok`. Evaluation took 46.9 seconds; artifact was 0.8 MB.
- **Decision:** discarded. Monthly schedule centering did not improve transfer to 2006.

## Plateau research after Experiment 20

Three consecutive schedule-offset variants stayed within 0.001 of the best without improving it. I reviewed other temporal representations before changing direction. Recent flight-delay feature engineering work represents daily periodicity with sine/cosine phases and retains fractional departure-hour precision ([FlightLLM feature description](https://www.sciencedirect.com/science/article/abs/pii/S0968090X26004274)); a flight-schedule operations study describes mapping departure times to periodic vectors ([Exploratory data analysis for airline disruption management](https://www.sciencedirect.com/science/article/pii/S2666827021000517)). The UC Berkeley flight-delay project also describes time-of-day operating blocks and rush-hour effects ([project feature engineering](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). I will test a coarse three-hour scheduled-departure block as a compact alternative to the existing exact-hour category.

## Experiment 21 — `9bf3bf3` — discard

- **Class:** feature exploration after temporal feature research.
- **Hypothesis:** a three-hour block may give a shallow tree a compact representation of broad airport operating periods, complementing the exact-hour category. Flight-delay feature work describes time-of-day blocks and distinct rush-hour effects ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)).
- **Change:** added a train-fitted categorical departure block `CRSDepHour // 3`.
- **Result:** Eval AUC **0.6832** (equal to the best); status `ok`. Evaluation took 41.9 seconds, slower than the best's 37.3 seconds.
- **Decision:** discarded because it matched the score but increased evaluation time.

## Experiment 22 — `075d2ee` — keep

- **Class:** model-capacity follow-up to the depth-4 result.
- **Hypothesis:** reducing tree depth could curb overfitting while retaining the stronger annual-cycle feature set. XGBoost's [parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes tree depth as a complexity control.
- **Change:** reduced `max_depth` from 4 to 3; retained the 100-tree, 0.1 learning-rate model and all features.
- **Result:** Eval AUC **0.6841** (up from 0.6832); status `ok`. Evaluation took 37.3 seconds and the artifact fell from 0.7 MB to 0.4 MB.
- **Decision:** kept as the new best.

## Experiment 23 — `4fcbf62` — discard

- **Class:** regularization follow-up to the depth-3 result.
- **Hypothesis:** sampling 80% of features per tree might reduce reliance on particular splits and improve generalization; XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discusses feature subsampling as a regularization setting.
- **Change:** set `colsample_bytree=0.8`; retained the depth-3 model.
- **Result:** Eval AUC **0.6832** (down from 0.6841); status `ok`. Evaluation took 37.2 seconds and artifact size fell to 0.3 MB.
- **Decision:** discarded because the AUC dropped.

## Experiment 24 — `97fe5b9` — discard

- **Class:** regularization follow-up to the depth-3 result.
- **Hypothesis:** a modest increase in `min_child_weight` could regularize leaf splits without the stronger constraint from the earlier value of 5; XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies it as a control on split support.
- **Change:** set `min_child_weight=2`.
- **Result:** Eval AUC **0.6841** (equal to the best); status `ok`. Evaluation time and artifact size were unchanged at 37.1 seconds and 0.4 MB.
- **Decision:** discarded because the equal score came with no measured simplicity or speed gain.

## Experiment 25 — `ec69646` — discard

- **Class:** model-size ablation of the kept depth-3 model.
- **Hypothesis:** reducing the tree count from 100 to 80 could retain AUC while reducing inference cost; XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) treats the number of boosting rounds as a capacity and training control.
- **Change:** reduced `n_estimators` from 100 to 80.
- **Result:** Eval AUC **0.6838** (down from 0.6841); status `ok`. Evaluation fell slightly to 36.9 seconds and artifact to 0.3 MB.
- **Decision:** discarded because the score decreased.

## Experiment 26 — `c6c871a` — discard

- **Class:** model-capacity ablation of the kept depth-3 model.
- **Hypothesis:** depth 2 might retain the learned structure with a smaller, more general model; XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends tuning tree depth to control complexity.
- **Change:** reduced `max_depth` from 3 to 2.
- **Result:** Eval AUC **0.6800** (down from 0.6841); status `ok`. Evaluation took 36.7 seconds; artifact fell to 0.2 MB.
- **Decision:** discarded due to a material AUC loss; depth 3 is the stronger compact setting.

## Plateau research after Experiment 26

Three recent depth-3 tuning ablations failed to improve the best, so I checked whether a simpler weekly regime could offer the shallow model a useful grouping. The UC Berkeley delay project reports elevated occurrence on Mondays and Sundays and treats day of week as a core temporal feature ([project findings](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). A separate flight-delay study found a weekend indicator weak for its arrival-delay target, which makes this a dataset-specific hypothesis to validate rather than assume ([MDPI study](https://www.mdpi.com/2079-9292/13/24/4910)). The training data encodes weekdays as `c-1` through `c-7`; I will test a Saturday/Sunday indicator alongside the existing categories.

## Experiment 27 — `0ff5ff4` — discard

- **Class:** feature exploration after weekday research.
- **Hypothesis:** an explicit Saturday/Sunday grouping could give depth-3 trees a direct weekly regime split alongside the full weekday category. Research reports weekday-specific delay patterns, though a separate study found a weekend flag weak for its arrival-delay target ([Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches), [MDPI study](https://www.mdpi.com/2079-9292/13/24/4910)).
- **Change:** added `IsWeekend` from the `c-6`/`c-7` training and evaluation row labels.
- **Result:** Eval AUC **0.6841** (equal to the best); status `ok`. Evaluation rose to 41.7 seconds and artifact size remained 0.4 MB.
- **Decision:** discarded because it matched AUC but increased evaluation time.

## Experiment 28 — `c657316` — discard

- **Class:** feature exploration following the annual-cycle gain.
- **Hypothesis:** the raw day-of-year position could give a depth-3 tree broad seasonal thresholds in addition to the smoother sine/cosine annual phase. Flight-delay feature work identifies day-of-year and seasonal variation as useful temporal representations ([TU Delft review](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)).
- **Change:** added numeric `DayOfYear` while retaining the existing annual sine and cosine.
- **Result:** Eval AUC **0.6837** (down from 0.6841); status `ok`. Evaluation took 38.4 seconds; artifact was 0.4 MB.
- **Decision:** discarded because the extra linear seasonal coordinate reduced AUC.

## Experiment 29 — `aa7fdd2` — discard

- **Class:** regularization follow-up to the depth-3 result.
- **Hypothesis:** slightly stronger L2 regularization could smooth leaf scores and improve generalization; XGBoost's [parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes regularization as a model-complexity control.
- **Change:** set `reg_lambda=2.0` from the default of 1.0.
- **Result:** Eval AUC **0.6835** (down from 0.6841); status `ok`. Evaluation took 36.9 seconds; artifact was 0.4 MB.
- **Decision:** discarded because AUC fell.

## Experiment 30 — `2edce46` — discard

- **Class:** feature exploration after weekday research.
- **Hypothesis:** weekly sine/cosine features could encode Sunday-to-Monday adjacency more directly than the existing weekday category. Flight-delay work explores trigonometric time encodings ([TU Delft review](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)); a recent temporal-feature study describes weekly phase encodings ([FlightLLM feature description](https://www.sciencedirect.com/science/article/abs/pii/S0968090X26004274)).
- **Change:** added sine and cosine of weekday number on a 7-day cycle.
- **Result:** Eval AUC **0.6841** (equal to the best); status `ok`. Evaluation rose to 43.0 seconds and artifact remained 0.4 MB.
- **Decision:** discarded because it matched AUC but increased evaluation time.

## Plateau research after Experiment 30

Four consecutive depth-3 ablations after the previous plateau review matched or narrowly missed the best. I reviewed XGBoost's official parameter reference for a final model-complexity hypothesis: `gamma` is the minimum loss reduction required to make another split, and larger values make splitting more conservative ([XGBoost parameters](https://xgboost.readthedocs.io/en/latest/parameter.html)). I will test a small nonzero value while keeping the depth-3 features and estimator count fixed.

## Experiment 31 — `5c7c7bd` — discard

- **Class:** split-regularization follow-up to the depth-3 model.
- **Hypothesis:** a small split penalty may remove marginal splits while preserving the useful depth-3 structure. XGBoost defines `gamma` as the minimum loss reduction for another split ([parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html)).
- **Change:** set `gamma=0.1`; all features, depth, and tree count stayed fixed.
- **Result:** Eval AUC **0.6841** (equal to the best); status `ok`. Evaluation took 37.4 seconds versus 37.3 seconds for the best; artifact remained 0.4 MB.
- **Decision:** discarded because it matched AUC without improving speed or size.

## Experiment wrap-up

The one-hour run began from baseline AUC **0.6743**. The best kept configuration is commit `075d2ee` at Eval AUC **0.6841**: 100 trees, depth 3, learning rate 0.1, with the train-fitted categorical departure hour and annual day-of-year sine/cosine features. Experiments and their keep/discard/crash outcomes are listed in `output/results.tsv`; the working branch is returned to the best checkpoint.
