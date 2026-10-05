# Research log

Run setup initialized 2026-10-05. Baseline and experiment notes will be recorded after the run starts.

## Baseline — `b15ec66`

- Ran the untouched starter on the harness: Eval AUC `0.6743` (status `ok`); this is the current kept commit.
- Before the first non-baseline experiment, reviewed the [XGBoost parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), the [categorical data tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html), and a [flight-delay feature-engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches).
- Research suggests categorical split handling and tree complexity are meaningful tuning dimensions. The flight-delay project emphasizes carrier, route and scheduled-time information, while operational propagation features need information this task does not provide. I’ll first inspect the training feature distributions, then test a row-local transformation or training-fitted lookup that is available at inference time.

## Experiment 1 hypothesis — scheduled-time representation

- Classification: exploration (first feature-engineering change after baseline).
- Hypothesis: keep HHMM and add elapsed minutes after midnight plus a departure-hour categorical feature. HHMM numeric gaps do not match elapsed time across hour boundaries (for example, 09:55 to 10:00); the alternative view may let trees express time-of-day effects more directly. The flight-delay feature-engineering project reviewed above also treats scheduled time as useful.
- The added columns will be calculated per row in `prepare(df)` from that row's scheduled departure time; the hour categories will use a fixed 0–23 domain. No aggregation or evaluation data is involved.
- Success criterion: harness Eval AUC above the kept baseline `0.6743` at `b15ec66`; otherwise discard.

## Experiment 1 result — `62fa772`

- Eval AUC `0.6747` (`ok`), up `0.0004` from the kept baseline `0.6743`; kept.
- Adding elapsed minutes and a fixed-domain hour category alongside the raw HHMM field gave a small gain. The result supports the time representation hypothesis, but does not identify which added feature helped.

## Experiment 2 hypothesis — hour-category ablation

- Classification: ablation/simplification of the promising time-feature change.
- Change only the added features from the kept result by removing `DepHour`; retain both raw HHMM and `DepTimeMinutes`. This isolates whether the categorical hour contributes beyond elapsed minutes. If Eval AUC ties `0.6747`, the model input and per-row preparation are simpler; if it drops, restore the kept version.

## Experiment 2 result — `cb89f5f`

- Eval AUC `0.6743` (`ok`), down `0.0004` from kept `62fa772`; discarded and reset to `62fa772`.
- Removing `DepHour` while retaining elapsed minutes returned to the baseline score. The fixed-domain hour category contributes to the small time-feature gain and remains in the kept code.

## Experiment 3 hypothesis — low-cardinality categorical splits

- Classification: exploration of categorical split strategy, following the kept model with native categorical features.
- Based on the [XGBoost 3.4.1 Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html?highlight=XGBRegressor), set `max_cat_to_onehot=32`. The documented threshold uses one-hot splits when category count is below it and category partitioning otherwise. In this data this should switch the month, day, weekday, carrier, and departure-hour columns to one-hot splits while leaving the 283-category airport columns partitioned.
- Hypothesis: individual equality splits may better capture non-monotonic effects for these compact categories. Keep all features, tree parameters, and preprocessing fixed so this run isolates the split strategy.
- Success criterion: improve on kept Eval AUC `0.6747` at `62fa772`.

## Experiment 3 result — `b34386c`

- Eval AUC `0.6754` (`ok`), up `0.0007` from kept `62fa772`; kept as the new best.
- Setting `max_cat_to_onehot=32` improved the low-cardinality categories while the airport categories stayed partitioned. The gain supports testing the category split strategy further.

## Experiment 4 hypothesis — airport-specific one-hot splits

- Classification: follow-up to the categorical-split improvement.
- Set `max_cat_to_onehot=300`, with all other code fixed. The training data has 283 unique values each for `Origin` and `Dest`, so this threshold should change those two high-cardinality columns from partition-based to one-hot splits while preserving the one-hot strategy for compact categories.
- Hypothesis: individual airport effects may be useful because location-specific operating conditions differ, though airport one-hot splits can also overfit. The experiment isolates whether this finer representation improves next-year AUC.
- Success criterion: improve on kept Eval AUC `0.6754` at `b34386c`.

## Experiment 4 result — `65ce55a`

- Eval AUC `0.6777` (`ok`), up `0.0023` from kept `b34386c`; kept as the new best.
- Extending one-hot splits from compact categories to the 283 origin and destination levels produced a larger gain. Airport-specific signals appear useful under the 2005-to-2006 split, though this result does not establish how much each airport column contributes.

## Experiment 5 hypothesis — carrier-specific route category

- Classification: exploration of a row-local categorical interaction, following the airport one-hot gain.
- The [flight-delay feature-engineering study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies route-related features among useful feature families. This dataset has 6,588 observed carrier–origin–destination combinations (versus 4,290 origin–destination pairs). Add a combined `CarrierRoute` category whose valid levels are fitted from `train.csv`; compute each row's key from its carrier, origin, and destination. Do not add row counts or target statistics.
- Hypothesis: a direct carrier–route identity will expose an interaction that otherwise takes several tree splits to represent. With 6,588 levels and `max_cat_to_onehot=300`, XGBoost will use partition-based categorical splits, allowing related routes to share splits. Sparse/unseen routes may limit the gain.
- Success criterion: improve on kept Eval AUC `0.6777` at `65ce55a`.

## Experiment 5 result — `b46a05b`

- Eval AUC `0.6629` (`ok`), down `0.0148` from kept `65ce55a`; discarded and reset to `65ce55a`.
- The 6,588-level carrier–route category reduced next-year AUC sharply. The direct interaction appears too sparse/noisy for this split and model; do not repeat this encoding.

## Experiment 6 hypothesis — regularize airport one-hot splits

- Classification: follow-up to the airport one-hot improvement.
- Based on the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) and [parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html), increase `min_child_weight` from its default of 1 to 5. The parameter sets the minimum summed Hessian weight for a child; larger values make the tree more conservative.
- Hypothesis: airport one-hot splits improved AUC, but low-support leaves may overfit the 2005 sample. A moderate increase may preserve common airport patterns while suppressing weak splits that do not carry to 2006. Keep other features and parameters fixed.
- Success criterion: improve on kept Eval AUC `0.6777` at `65ce55a`.

## Experiment 6 result — `f46e457`

- Eval AUC `0.6766` (`ok`), down `0.0011` from kept `65ce55a`; discarded and reset to `65ce55a`.
- `min_child_weight=5` was too conservative for this model and reduced AUC.

## Experiment 7 hypothesis — mild child-weight regularization

- Classification: follow-up hyperparameter tuning after the `min_child_weight=5` result.
- Change only `min_child_weight`, from 1 to 2. Since 5 lowered AUC, test a smaller increase that may reduce weak airport-specific leaves while preserving more useful splits. The XGBoost docs describe this parameter as a complexity control based on the child Hessian weight.
- Success criterion: improve on kept Eval AUC `0.6777` at `65ce55a`.

## Experiment 7 result — `a770227`

- Eval AUC `0.6774` (`ok`), down `0.0003` from kept `65ce55a`; discarded and reset to `65ce55a`.
- `min_child_weight=2` was slightly better than 5 but still below the default-1 model. Keep the default for now.

## Experiment 8 hypothesis — carrier-by-month category

- Classification: exploration of a denser categorical interaction.
- The flight-delay study reviewed earlier treats month as a temporal feature and carrier as a flight feature. This training split has 236 observed carrier–month combinations, far fewer than the 6,588 carrier–route combinations that hurt AUC. Add a `CarrierMonth` category with levels fitted once on `train.csv` and construct its key from each row's carrier and month.
- Hypothesis: airline-specific seasonal patterns may help, and the denser interaction should be less noisy than carrier–route. Under the kept `max_cat_to_onehot=300`, its 236 levels will use one-hot splits, consistent with the earlier low-cardinality gain. No group counts or target aggregates are added.
- Success criterion: improve on kept Eval AUC `0.6777` at `65ce55a`.

## Experiment 8 result — `a360420`

- Eval AUC `0.6758` (`ok`), down `0.0019` from kept `65ce55a`; discarded and reset to `65ce55a`.
- The 236-level carrier–month one-hot interaction did not improve on the independent carrier and month features. Further categorical interactions need a stronger reason than shared fields alone.

## Experiment 9 hypothesis — row subsampling

- Classification: exploration of training randomness on the kept airport one-hot model.
- Based on the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), set `subsample=0.8` while leaving the other parameters fixed. The guide lists row subsampling as a way to add randomness and improve robustness to noise.
- Hypothesis: the airport one-hot gain may still include variance from individual 2005 examples. Sampling 80% of rows per boosting iteration could make the model less dependent on weak individual patterns while leaving substantial data for each tree.
- Success criterion: improve on kept Eval AUC `0.6777` at `65ce55a`.

## Experiment 9 result — `195f5a2`

- Eval AUC `0.6769` (`ok`), down `0.0008` from kept `65ce55a`; discarded and reset to `65ce55a`.
- Row subsampling at 0.8 did not help the airport one-hot model. Preserve the full-row default while considering other feature directions.

## Experiment 10 hypothesis — cyclic departure-time coordinates

- Classification: exploration of a periodic time representation.
- The [scikit-learn time-feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains that sine/cosine features represent a periodic clock without a jump between its first and last values. A [flight-delay prediction study](https://www.mdpi.com/2226-4310/8/6/152) also uses trigonometric encodings for time variables.
- Add `sin(2πt/1440)` and `cos(2πt/1440)` for each row's elapsed departure minute `t`. Keep the existing HHMM, elapsed-minute, and hour-category features; this tests whether the cyclic view adds useful signal to the current best without replacing what already helped. The transform is row-local and has a fixed 1,440-minute period.
- Trees already model nonlinear effects, so the gain is uncertain; the specific opportunity is treating departures near midnight as neighbors. Success criterion: improve on kept Eval AUC `0.6777` at `65ce55a`.

## Experiment 10 result — `b8c1d75`

- Eval AUC `0.6772` (`ok`), down `0.0005` from kept `65ce55a`; discarded and reset to `65ce55a`.
- The cyclic coordinates did not add to the current tree model's HHMM, elapsed-minute, and hour features.

## Synthesis after 10 experiments

- **What helped:** elapsed departure minutes plus a categorical hour gave a small gain (`0.6743` → `0.6747`); removing the hour category removed that gain. The large improvement came from setting `max_cat_to_onehot=32` and then `300`, with the airport categories included: AUC reached `0.6777` at `65ce55a`.
- **What did not help:** carrier–route (`0.6629`) and carrier–month (`0.6758`) interaction categories, cyclic time coordinates (`0.6772`), row subsampling at `0.8` (`0.6769`), and `min_child_weight` values 2 or 5 (`0.6774`, `0.6766`) all fell below the kept model.
- **Current theory:** individual category splits for airports carry useful, stable signal across the year boundary. Sparse combined categories and added regularization have not transferred as well. The time representation adds a small independent benefit; its cyclic form did not.
- **Next direction:** explore a denser schedule interaction, then continue with controlled model-capacity and category-threshold changes. Keep every feature row-local and fit any category levels only on `train.csv`.

## Experiment 11 hypothesis — smaller boosting steps

- Classification: exploration of the boosting schedule on the kept feature and category setup.
- The [XGBoost parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends reducing `eta` while increasing the number of rounds; the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `eta` as shrinkage that makes each update more conservative.
- Change `learning_rate` from `0.1` to `0.05` and double `n_estimators` from `100` to `200` to allow more, smaller updates. Keep the model depth, categories, and features fixed. Hypothesis: the longer, gentler sequence may rank flights more robustly across the year split.
- Success criterion: improve on kept Eval AUC `0.6777` at `65ce55a`.

## Experiment 11 result — `2edbcc6`

- Eval AUC `0.6775` (`ok`), down `0.0002` from kept `65ce55a`; discarded and reset to `65ce55a`.
- Doubling rounds while halving the learning rate nearly matched the best but did not improve it.

## Experiment 12 hypothesis — more rounds at the current step size

- Classification: follow-up to the learning-rate/round-count experiment.
- Set `n_estimators=200` while retaining `learning_rate=0.1`. This isolates whether more boosting rounds help, since the previous run changed both values. If it scores higher than `0.6777`, additional stages carry useful signal; if lower, the 100-round model remains preferable.

## Experiment 12 result — `e87c3fe`

- Eval AUC `0.6808` (`ok`), up `0.0031` from kept `65ce55a`; kept as the new best.
- Doubling the number of rounds at the original learning rate materially improved AUC. This suggests the 100-tree model had not exhausted useful boosting signal.

## Experiment 13 hypothesis — continue the round-count curve

- Classification: follow-up to the strong 200-tree improvement.
- Increase only `n_estimators` from 200 to 300, retaining `learning_rate=0.1` and the winning feature/category setup. Hypothesis: additional rounds may continue to improve ranking, though overfitting could begin as the trees accumulate.
- Success criterion: improve on kept Eval AUC `0.6808` at `e87c3fe`.

## Experiment 13 result — `1daea67`

- Eval AUC `0.6814` (`ok`), up `0.0006` from kept `e87c3fe`; kept as the new best.
- Increasing rounds from 200 to 300 continued to help, with a smaller gain than the prior step.

## Experiment 14 hypothesis — test 400 rounds

- Classification: follow-up to the improving round-count curve.
- Increase only `n_estimators` from 300 to 400 at `learning_rate=0.1`. The 200→300 increment still improved the time-split AUC, so test one further step while watching for diminishing returns or overfit.
- Success criterion: improve on kept Eval AUC `0.6814` at `1daea67`.

## Experiment 14 result — `aea1b55`

- Eval AUC `0.6815` (`ok`), up `0.0001` from kept `1daea67`; kept under the strict higher-AUC rule.
- A further 100 rounds added a very small gain, so continue cautiously.

## Experiment 15 hypothesis — test 500 rounds

- Classification: follow-up to the still-increasing round-count curve.
- Increase only `n_estimators` from 400 to 500 at `learning_rate=0.1`. The last increment improved AUC by `0.0001`; test whether another 100 rounds adds measurable ranking signal or begins to overfit.
- Success criterion: improve on kept Eval AUC `0.6815` at `aea1b55`.

## Experiment 15 result — `704fcbd`

- Eval AUC `0.6812` (`ok`), down `0.0003` from kept `aea1b55`; discarded and reset to `aea1b55`.
- The improvement plateaued around 400 rounds; 500 trees began to lose AUC.

## Experiment 16 hypothesis — deeper trees at the 400-round optimum

- Classification: exploration of model capacity after identifying a useful round count.
- Set `max_depth=7` while keeping 400 trees, learning rate 0.1, and all features fixed. XGBoost docs say depth allows more complex interactions but can overfit; the extra level may help combine carrier, airport, schedule, and time signals, with the 200K training rows providing support.
- Success criterion: improve on kept Eval AUC `0.6815` at `aea1b55`.

## Experiment 16 result — `621716c`

- Eval AUC `0.6796` (`ok`), down `0.0019` from kept `aea1b55`; discarded and reset to `aea1b55`.
- Depth 7 overfit relative to the depth-6 model at 400 rounds.

## Experiment 17 hypothesis — shallower trees

- Classification: ablation of tree capacity following the depth-7 loss.
- Set `max_depth=5` at 400 trees and `learning_rate=0.1`, keeping all other settings fixed. This tests whether a slightly simpler tree transfers better across the year split. If it ties `0.6815`, keep it only if the shallower model is faster.
- Success criterion: higher AUC than kept `aea1b55`, or an exact tie with faster execution.

## Experiment 17 result — `ce40419`

- Eval AUC `0.6810` (`ok`), down `0.0005` from kept `aea1b55`; discarded and reset to `aea1b55`.
- Depth 5 also underperformed the depth-6 model. Together with depth 7, this supports retaining the default depth for now.

## Experiment 18 hypothesis — finer numeric histogram bins

- Classification: exploration of numerical split resolution on the kept model.
- The [XGBoost 3.4.2 parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says the default `max_bin=256` buckets continuous features for `hist`/`approx` and that increasing it can improve split optimality at extra computation cost. The same reference says `tree_method=auto` uses `hist`. In `train.csv`, `CRSDepTime` and `Distance` each have more than 1,100 distinct values.
- Set `max_bin=512`, keeping features, depth, learning rate, and 400 rounds fixed. Hypothesis: more numeric cut candidates may better resolve schedule-time and distance effects that the current 256-bin histogram approximates coarsely.
- Success criterion: improve on kept Eval AUC `0.6815` at `aea1b55`.

## Experiment 18 result — `92b2507`

- Eval AUC `0.6816` (`ok`), up `0.0001` from kept `aea1b55`; kept as the new best.
- Doubling numeric histogram resolution from 256 to 512 gave a small improvement without a material runtime increase.

## Experiment 19 hypothesis — 1,024 numeric bins

- Classification: follow-up to the positive `max_bin=512` result.
- Increase only `max_bin` from 512 to 1,024. The source numeric features have over 1,100 distinct values, so this tests whether further split resolution improves their contribution. The XGBoost docs note the tradeoff: more accurate split candidates at higher computation cost.
- Success criterion: improve on kept Eval AUC `0.6816` at `92b2507`.

## Experiment 19 result — `4d5d233`

- Eval AUC `0.6809` (`ok`), down `0.0007` from kept `92b2507`; discarded and reset to `92b2507`.
- Increasing numeric resolution to 1,024 bins hurt slightly; 512 remains the best setting.

## Experiment 20 hypothesis — slower boosting at matched exposure

- Classification: follow-up to the promising 400-round model and the smaller-step tuning result.
- Set `learning_rate=0.05` and `n_estimators=800`, keeping features, depth, and `max_bin=512` fixed. This doubles rounds as the step size is halved, matching the nominal `learning_rate × rounds` of the kept 400-round, 0.1 model. The XGBoost tuning guide recommends increasing rounds when lowering the step size; the earlier 200-round test may simply have stopped too soon.
- Hypothesis: smaller updates across enough rounds may improve generalization; the larger ensemble may also begin to overfit or be slower. Success criterion: improve on kept Eval AUC `0.6816` at `92b2507`.

## Experiment 20 result — `c129fc3`

- Eval AUC `0.6813` (`ok`), down `0.0003` from kept `92b2507`; discarded and reset to `92b2507`.
- At 800 rounds, learning rate 0.05 still did not beat 400 rounds at 0.1.

## Synthesis after 20 experiments

- **What helped:** native categorical one-hot splits up through 283 origin/destination levels raised AUC to `0.6777`. Increasing rounds at learning rate 0.1 then improved the model through 400 trees (`0.6815`); 512 numeric bins added a small gain to `0.6816` (`92b2507`). Clock minutes and hour category remain a small useful addition over baseline (`0.6747` vs `0.6743`).
- **What did not help:** high-card carrier–route and carrier–month interaction categories, cyclic time features, row subsampling, stronger child-weight regularization, depths 5 or 7, 500 rounds, max-bin 1,024, and lower-rate schedules all scored below the current best.
- **Current theory:** the strongest transferable signal is in the individual categorical effects, especially airports, followed by allowing enough boosting rounds to use them. Very sparse interactions and added model complexity beyond depth 6/400 rounds have not generalized to the following year. Finer numeric bins help only slightly.
- **Next direction:** research whether smoothed, train-fitted airport delay-rate lookups can pool similar origin/destination effects more efficiently than one-hot splits. Any lookup will be fitted only on `train.csv`; no counts will be added as features, and all lookups will be applied row by row in `prepare(df)`.

## Experiment 21 hypothesis — cross-fitted smoothed airport rates

- Classification: exploration of train-fitted airport statistics, following the strong airport one-hot gain and the weak raw carrier–route category.
- The [scikit-learn target-encoding docs](https://scikit-learn.org/stable/modules/preprocessing#target-encoder) describe encoding categories with a smoothed conditional target mean and recommend cross-fitting so each training row is encoded without its own fold's target information. A [flight-delay feature study](https://pmc.ncbi.nlm.nih.gov/articles/PMC10897135/) includes an origin delay-rate feature; another [airport-delay feature analysis](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) documents airport-specific average-delay variation.
- Add `OriginDelayRate` and `DestDelayRate`: binary target means smoothed toward the global prior with strength 100, fitted in five deterministic folds from `train.csv`. The fold is a stable hash of each row's non-target input features. Each fold's mapping excludes that fold; `prepare(df)` selects a mapping from the current row's hash, so the feature is unchanged when scored one row at a time and the evaluation label is not used. Counts are only used internally to compute smoothed rates and are not included as features; no AUC is computed outside the harness.
- Hypothesis: smooth rates can pool airports with similar delay tendencies, complementing the individually one-hot airport categories while avoiding raw high-cardinality route memorization.
- Success criterion: improve on kept Eval AUC `0.6816` at `92b2507`.

## Experiment 21 result — `8365ed8`

- Eval AUC `0.6800` (`ok`), down `0.0016` from kept `92b2507`; discarded and reset to `92b2507`.
- Cross-fitted smoothed origin/destination rates did not improve on the airport one-hot categories. Their added per-row hashing increased evaluation time from about 34s to 45s, so do not retain this preparation overhead.

## Experiment 22 hypothesis — mild column sampling

- Classification: exploration of feature sampling on the kept model.
- Based on the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), set `colsample_bytree=0.9`, leaving all other settings fixed. Each tree will sample 90% of feature columns.
- Hypothesis: omitting one of the correlated time encodings or one airport column in some trees may reduce feature co-adaptation and create useful ensemble diversity. This is a milder change than the unsuccessful 0.8 row-sampling experiment.
- Success criterion: improve on kept Eval AUC `0.6816` at `92b2507`.

## Experiment 22 result — `9c18804`

- Eval AUC `0.6818` (`ok`), up `0.0002` from kept `92b2507`; kept as the new best.
- Mild feature-column sampling gave a small improvement without changing runtime materially.

## Experiment 23 hypothesis — stronger column sampling

- Classification: follow-up to the positive `colsample_bytree=0.9` result.
- Lower only `colsample_bytree` from 0.9 to 0.8. This tests whether stronger tree-to-tree feature diversity helps further, while retaining all features across the ensemble. It may also omit useful airport columns too often, so the direction is uncertain.
- Success criterion: improve on kept Eval AUC `0.6818` at `9c18804`.

## Experiment 23 result — `d8092e4`

- Eval AUC `0.6813` (`ok`), down `0.0005` from kept `9c18804`; discarded and reset to `9c18804`.
- Stronger column sampling at 0.8 removed too many useful feature columns; retain 0.9.

## Experiment 24 hypothesis — ablate finer numeric bins

- Classification: ablation of the small `max_bin=512` gain in the new best model.
- Set `max_bin=256` while retaining `colsample_bytree=0.9` and all other settings. The 512-bin setting previously improved AUC by only `0.0001`; test whether that gain persists with column sampling, and whether the default bin count ties with faster training.
- Keep 256 only if it improves AUC or ties at four decimals with a measurable runtime reduction.

## Experiment 24 result — `19cf2f2`

- Eval AUC `0.6810` (`ok`), down `0.0008` from kept `9c18804`; discarded and reset to `9c18804`.
- With 0.9 column sampling, 256 bins did not match the 512-bin result. Retain the finer histogram.

## Experiment 25 hypothesis — 450 rounds with column sampling

- Classification: follow-up to the new best using mild column sampling.
- Test `n_estimators=450` at `learning_rate=0.1`, `max_bin=512`, and `colsample_bytree=0.9`, changing only the round count from the kept 400. Column sampling may delay the overfit observed at 500 rounds without it.
- Success criterion: improve on kept Eval AUC `0.6818` at `9c18804`.

## Experiment 25 result — `b22e89a`

- Eval AUC `0.6819` (`ok`), up `0.0001` from kept `9c18804`; kept as the new best.
- At `colsample_bytree=0.9`, 450 rounds edged out 400. Runtime remained about 37 seconds.

## Final summary — 2026-10-05

- Best Eval AUC: `0.6819` at commit `b22e89a` on branch `oct5`.
- What worked: adding elapsed minutes and a categorical departure hour gave a small initial gain. Setting `max_cat_to_onehot=300` so the airport categories received individual splits was the largest feature/model improvement. Increasing the tree count to 400 and then 450 at learning rate 0.1 improved AUC; `max_bin=512` and `colsample_bytree=0.9` each contributed small gains.
- What did not: sparse carrier–route and carrier–month categories, airport target-rate lookups, cyclic time features, stronger child-weight regularization, row sampling, depths 5/7, 500 rounds without column sampling, 800 rounds at 0.05, and max-bin settings of 256 (with column sampling) or 1,024 all scored lower.
- Current best settings: 450 trees, depth 6, learning rate 0.1, `max_bin=512`, `max_cat_to_onehot=300`, `colsample_bytree=0.9`, with the retained minute and hour features.
- Next direction for a future run: tune round count in the 400–500 range around 450 with `colsample_bytree=0.9`, or investigate airport hierarchy features if a reliable train-only mapping is available.
