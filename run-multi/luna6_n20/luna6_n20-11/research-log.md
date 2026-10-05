# Research log — oct5

## Baseline — `b15ec66`

Ran the starter `train.py` unchanged. The baseline uses native categorical features, `n_estimators=100`, `max_depth=6`, and `learning_rate=0.1`; training and row-by-row evaluation completed successfully in 31.8 seconds. Eval AUC: **0.6743**. This is the starting point for all keep/discard decisions.

## Experiment 1 proposal — cyclic departure-time representation (exploration)

**Hypothesis:** `CRSDepTime` is stored as HHMM (for example, 09:59 is 959 and 10:00 is 1000), so treating it as a plain integer distorts minute spacing and places midnight at an arbitrary edge. Replacing it with true minute-of-day and its sine/cosine phase should make the daily cycle easier to model and may improve transfer to 2006.

**Research:** The XGBoost tuning guide emphasizes that preprocessing can matter as much as parameter tuning and recommends managing model complexity to limit overfitting ([parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). A flight-delay prediction study uses temporal features including time of day and reports trigonometric encoding for time features ([flight-delay study](https://www.mdpi.com/2226-4310/8/6/152)). A time-series review explains sine/cosine encoding as a way to preserve periodic proximity ([cyclic-feature review](https://doi.org/10.1002/widm.1475)).

**Data observation:** In `train.csv`, `CRSDepTime` is an integer from 5 to 2359; sample values follow HHMM notation. The experiment will remove raw HHMM and add minute-of-day, sine, and cosine in `prepare(df)`. These features are computed independently for each row.

**Result — `b4ce117`:** Eval AUC **0.6734** (discard; baseline 0.6743). The row-local features trained and evaluated successfully, but this encoding did not transfer better to 2006. Keep the baseline as current best. Next, test a separate model-complexity direction suggested by XGBoost's tuning guide.

## Experiment 2 proposal — row and feature subsampling (exploration)

**Hypothesis:** Adding moderate randomness to the baseline's full-row, full-feature trees may reduce dependence on 2005-specific patterns and improve transfer to the 2006 evaluation set. Change only `subsample` and `colsample_bytree` to 0.8; keep all other baseline parameters fixed.

**Research:** XGBoost's [parameter-tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies `subsample` and `colsample_bytree` as ways to add randomness and make training more robust to noise. The [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes their fractions of sampled rows and columns and gives the supported range `(0, 1]`.

**Result — `c6adea4`:** Eval AUC **0.6777** (keep; +0.0034 versus baseline). The run completed successfully, with row and feature subsampling both set to 0.8. This supports the hypothesis that moderate sampling improves transfer. Next, ablate one sampling control to identify whether both are needed.

## Experiment 3 proposal — ablate column sampling (ablation)

**Hypothesis:** The gain in experiment 2 may come mainly from row sampling. Keep `subsample=0.8`, remove the explicit `colsample_bytree=0.8` setting (restoring its default of 1.0), and compare. Equal AUC would favor the simpler model; a drop would indicate feature sampling contributes.

**Result — `48ebd5e`:** Eval AUC **0.6759** (discard; kept combination is 0.6777). Row sampling alone retained some of the gain over baseline but did not match both controls together, so feature sampling may add useful regularization.

## Experiment 4 proposal — ablate row sampling (ablation)

**Hypothesis:** Since row sampling alone scored 0.6759, test whether feature sampling alone retains the gain. Keep `colsample_bytree=0.8` and remove `subsample=0.8` to restore full row sampling. This isolates the second control from experiment 2.

**Result — `0ea9a71`:** Eval AUC **0.6805** (keep; +0.0028 versus experiment 2 and +0.0062 versus baseline). Feature sampling alone outperformed the combination, while row sampling alone was lower. This points to feature subsampling as the main useful regularizer. Follow up by testing a slightly milder feature-sampling rate.

## Experiment 5 proposal — stronger feature sampling (follow-up)

**Hypothesis:** Since `colsample_bytree=0.8` was the strongest result and row sampling did not help, a stronger column-sampling rate of 0.6 may further limit reliance on 2005-specific splits. Change only this parameter; all other settings stay at the current best.

**Result — `26c7506`:** Eval AUC **0.6805** (discard; equal to current best without a simplification or speed gain). Stronger sampling tied the 0.8 setting at four-decimal reporting precision, so keep `colsample_bytree=0.8` as the simpler established choice.

## Experiment 6 proposal — shallower trees (exploration)

**Hypothesis:** The baseline depth of 6 may allow noisy interactions among the schedule and categorical features. At the current best's `colsample_bytree=0.8`, reduce `max_depth` to 4 to test whether simpler trees generalize better. XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frames depth as a bias-variance control; its [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) notes that deeper trees increase complexity and overfitting risk.

**Result — `e8c80dd`:** Eval AUC **0.6799** (discard; current best 0.6805). Reducing depth by two slightly hurt, suggesting the model benefits from retaining depth-6 interactions. Next, preserve depth and try limiting low-support splits with `min_child_weight`.

## Experiment 7 proposal — require more support per split (exploration)

**Hypothesis:** Depth 4 slightly underperformed, so retain depth-6 interactions but reduce low-support leaves. Raise `min_child_weight` from its default 1 to 5 while keeping the current best's feature sampling. The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger values make the algorithm more conservative by requiring more Hessian weight in child nodes.

**Result — `af0864d`:** Eval AUC **0.6782** (discard; current best 0.6805). Requiring more support at every split reduced AUC. Test a milder `min_child_weight=2` once to see whether the effect was specific to the stronger regularization.

## Experiment 8 proposal — milder child-weight constraint (follow-up)

**Hypothesis:** `min_child_weight=5` constrained the model too much. A smaller increase to 2 may retain useful depth-6 interactions while reducing only the least-supported splits. Change only `min_child_weight` from 1 to 2.

**Result — `f46bafb`:** Eval AUC **0.6783** (discard; current best 0.6805). The milder child-weight increase also hurt, so keep the default of 1. Move to learning dynamics: test a lower learning rate with proportionally more boosting rounds.

## Experiment 9 proposal — lower learning rate, more rounds (exploration)

**Hypothesis:** The baseline's 100 rounds at learning rate 0.1 may take steps that are too large. Try 300 rounds at 0.05, retaining depth 6 and the winning `colsample_bytree=0.8`. XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends reducing `eta` while increasing the number of rounds, since `eta` shrinks each boosting update.

**Result — `ae69a7d`:** Eval AUC **0.6780** (discard; current best 0.6805). Slower boosting with more rounds did not help in this setting. Experiment 10 will test native categorical split handling, a separate modeling direction.

## Experiment 10 proposal — one-hot splits for low-cardinality categories (exploration)

**Hypothesis:** Direct one-vs-rest splits may capture individual carrier and calendar-level effects better than grouping those categories. Set `max_cat_to_onehot=32` with native categorical handling and the current best's `colsample_bytree=0.8`. In train, Month (12), DayofMonth (31), DayOfWeek (7), and UniqueCarrier (20) have fewer than 32 levels and should use one-hot splits; Origin and Dest (283 each) should retain partition splits.

**Research:** The official XGBoost [categorical-data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains the difference between equality (one-hot) splits and category-group partition splits. Its [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_cat_to_onehot` selects between them based on the number of categories. The installed XGBoost version is 3.4.1.

**Result — `74c743d`:** Eval AUC **0.6789** (discard; current best 0.6805). Selective one-hot splits for the low-cardinality categories did not improve the score in this run.

## Synthesis after 10 non-baseline experiments

- **Best:** `0ea9a71`, AUC **0.6805**, with the starter model and `colsample_bytree=0.8` (up from the 0.6743 baseline).
- **What helped:** Feature sampling alone was the only clear improvement. Adding row sampling alongside it reduced AUC to 0.6777; row sampling alone scored 0.6759.
- **What did not help:** Re-encoding HHMM departure times, lowering tree depth, increasing `min_child_weight`, lowering the learning rate while tripling rounds, and raising the categorical one-hot threshold all scored below the best. `colsample_bytree=0.6` tied at four decimals but did not simplify or speed the code, so the 0.8 setting remains.
- **Current theory:** A little feature-level randomness improves transfer from 2005 to 2006. The existing inputs may need better interaction features; direct route identity is an attractive next direction because origin and destination are currently available only as separate categories.
- **Next:** Research route and airport interaction features in flight-delay prediction, then test a composite `Origin`–`Dest` categorical feature computed row by row in `prepare(df)`.

## Experiment 11 proposal — composite route category (exploration)

**Hypothesis:** Separate Origin and Dest splits require a tree path to express route-specific patterns. Adding their ordered pair as a categorical feature may expose route-level effects directly while preserving the airport features. This is row-local and uses only a category vocabulary fitted on train.

**Research:** Flight-delay work treats origin–destination links and airport connectivity as spatial structure ([FlightNet-ST study](https://link.springer.com/article/10.1007/s44196-025-00932-2)); a separate departure-delay study also describes route information among airports as contextual input ([Shao et al., 2021](https://arxiv.org/abs/2105.08969)). I am adapting that motivation to a single composite categorical feature; neither source evaluates this exact encoding.

**Data observation:** The training split contains 4,290 unique ordered Origin–Dest routes across 283 origin and 283 destination categories. The new `Route` feature will use those levels and map unseen routes to missing in `prepare(df)`.

**Result — `807b155`:** Eval AUC **0.6708** (discard; current best 0.6805). The 4,290-level composite route feature substantially hurt AUC. Evaluation also reported pandas warnings for routes absent from the train vocabulary; the harness run still completed. Do not keep this high-cardinality feature. Search for an alternative that uses stable aggregate airport/carrier behavior without route identity.

## Experiment 12 proposal — smoothed airport and carrier delay rates (exploration)

**Hypothesis:** Native categories let trees group airport/carrier levels, but a continuous estimate of each level's historical delay rate may expose a useful ordering directly. Fit smoothed target-rate lookups for UniqueCarrier, Origin, and Dest using train only, with prior weight 100 toward the training-set mean; map each row's category to its rate inside `prepare(df)`. Do not add group counts as features.

**Research:** The flight-delay paper [Probabilistic Flight Delay Predictions Using Machine Learning and Applications to the Flight-to-Gate Assignment Problem](https://www.researchgate.net/publication/351962528_Probabilistic_Flight_Delay_Predictions_Using_Machine_Learning_and_Applications_to_the_Flight-to-Gate_Assignment_Problem) target-encodes categorical features as the category's rate of crossing a 15-minute delay threshold. This experiment adapts the airport and airline rates to this setup and smooths them to reduce noise for smaller airport groups.

**Result — `ba0eb2d`:** Eval AUC **0.6766** (discard; current best 0.6805). Smoothed carrier/origin/destination delay rates did not add predictive value beyond the existing native categories under this setup. Shift to a low-cardinality interaction between carrier and departure-time block.

## Experiment 13 proposal — carrier by two-hour block (exploration)

**Hypothesis:** A carrier's delay behavior may vary through the day. Add one `CarrierDepBlock` categorical feature, combining carrier with a two-hour departure block (at most 20 × 12 = 240 categories), while retaining all original features and the current best parameters.

**Research:** A flight-delay study reports that airline-related delay factors differ across successive two-hour periods of the day ([Wu et al., 2018](https://onlinelibrary.wiley.com/doi/10.1155/2018/5236798)). A U.S. econometric study also finds time-of-day effects on average delay ([Hsiao & Hansen, 2006](https://doi.org/10.3141/1951-13)). My inference is that a compact carrier–time interaction could expose these differing patterns to the tree model. Each interaction level is learned from `train.csv`; the feature itself is computed from the row's carrier and scheduled time.

**Result — `74ca58a`:** Eval AUC **0.6758** (discard; current best 0.6805). The 240-level carrier/time interaction hurt, suggesting the existing features already capture enough of this structure or that the added category is noisy. A standalone hour category is a narrower test: it keeps the original HHMM signal but makes broad time-of-day groups available directly.

## Experiment 14 proposal — categorical departure hour (follow-up)

**Hypothesis:** Raw HHMM imposes a numeric ordering, while risk can vary non-monotonically over the day. Add the scheduled hour as a categorical feature alongside the untouched HHMM value, allowing XGBoost to group hours with similar learned effects in one split. The reviewed flight-delay studies report time-of-day differences, including airline-related effects across two-hour windows ([Wu et al., 2018](https://onlinelibrary.wiley.com/doi/10.1155/2018/5236798)).

**Implementation:** Derive `CRSDepTime // 100` per row. Fit the hour vocabulary on train and use it in `prepare(df)`; do not compute any statistics over the incoming frame.

**Result — `03bc882`:** Eval AUC **0.6769** (discard; current best 0.6805). Adding categorical hour alongside raw HHMM did not help; the native time representation already seems adequate for this model.

## Experiment 15 proposal — continuous day of year (exploration)

**Hypothesis:** Month and day-of-month categories may miss a smooth seasonal progression across month boundaries. Add a numeric day-of-year feature from the row's month and day while retaining both original categories. A flight-delay study includes day of year and season among candidate temporal predictors ([probabilistic delay-prediction study](https://www.researchgate.net/publication/351962528_Probabilistic_Flight_Delay_Predictions_Using_Machine_Learning_and_Applications_to_the_Flight-to-Gate_Assignment_Problem)).

**Implementation:** Convert the existing `c-N` month/day strings to integers and add the non-leap-year month offset. Train is from 2005 and eval from 2006, both non-leap years; no date is inferred from rows outside the current input.

**Result — `c2eb06b`:** Eval AUC **0.6783** (discard; current best 0.6805). A continuous day-of-year position did not improve the month/day categories on this year-ahead evaluation.

## Experiment 16 proposal — minimum split gain (exploration)

**Hypothesis:** Depth 4 and larger `min_child_weight` both underperformed. `gamma` applies a different constraint: require a minimum loss reduction for each split, potentially pruning weak splits while preserving high-value depth-6 interactions. Set `gamma=1` and keep the rest of the current best fixed. The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines it as the minimum loss reduction required for another partition; larger values are more conservative.

**Result — `bc1ecf7`:** Eval AUC **0.6790** (discard; current best 0.6805). A gain threshold of 1 was too restrictive or otherwise unhelpful. Test a smaller value of 0.1 once to distinguish a strong-threshold failure from the effect of any split-gain regularization.

## Experiment 17 proposal — mild split-gain threshold (follow-up)

**Hypothesis:** The `gamma=1` threshold may have removed useful splits. Try `gamma=0.1` to test whether only a small minimum gain is beneficial; all other settings remain at the current best.

**Result — `b003ed5`:** Eval AUC **0.6800** (discard; current best 0.6805). A small split-gain threshold came close but still scored lower. Restore gamma's default of 0 and test a depth-5 midpoint between the underperforming depth-4 model and the current depth-6 best.

## Experiment 18 proposal — depth-5 midpoint (follow-up)

**Hypothesis:** Depth 4 slightly underperformed depth 6. A depth of 5 may retain enough feature interactions with a modest complexity reduction. Change only `max_depth` to 5.

**Result — `c3b1dee`:** Eval AUC **0.6793** (discard; current best 0.6805). The depth-5 midpoint also underperformed. Next test a modest increase to depth 7 to see whether additional interactions help under column sampling.

## Experiment 19 proposal — depth-7 trees (follow-up)

**Hypothesis:** Depth 5 underperformed, but depth 7 may capture useful higher-order interactions while the 0.8 column sampling limits feature co-adaptation. Change only `max_depth` from 6 to 7.

**Result — `95e698c`:** Eval AUC **0.6759** (discard; current best 0.6805). Increasing depth to 7 substantially hurt. The depth-4/5/7 comparisons support retaining depth 6. Experiment 20 will constrain categorical partition search for high-cardinality airport features, then pause for synthesis and research.

## Experiment 20 proposal — limit categories in partition splits (exploration)

**Hypothesis:** Origin and Dest each have 283 levels, making their partition splits more prone to fitting rare airport patterns. Lower `max_cat_threshold` from the installed library's default to 32 to regularize those splits. The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as the maximum number of categories considered for a partition split and says it is intended to prevent overfitting. Keep every other setting at the current best.

**Result — `1493332`:** Eval AUC **0.6784** (discard; current best 0.6805). Limiting categorical partition candidates did not improve transfer.

## Synthesis after 20 non-baseline experiments

- **Best remains:** `0ea9a71`, AUC **0.6805**, using the starter inputs/structure with `colsample_bytree=0.8` (+0.0062 over baseline 0.6743).
- **Direction that helped:** Feature subsampling alone. Adding row subsampling reduced AUC.
- **Feature ideas that did not help:** HHMM/cyclic replacement, a high-cardinality route, smoothed carrier/airport rates, carrier-by-time blocks, a categorical hour, and day of year. These additions either duplicated information already accessible to the trees or were too sparse/noisy for this year-ahead split.
- **Model settings that did not help:** 0.6 feature sampling tied the best but was not simpler/faster; depth 4, 5, and 7 all underperformed depth 6; `min_child_weight`, `gamma`, and a lower `max_cat_threshold` also reduced AUC. AUC is therefore strongest with default depth and split regularization plus column sampling.
- **Current theory:** The generalization gain comes from randomizing which of the original features each tree sees. Hand-built interactions and stronger split constraints have not added signal. Research and test a substantially different tree-growing or ensemble-regularization strategy next.

## Experiment 21 proposal — DART tree dropout (exploration)

**Hypothesis:** Feature sampling helped, but ordinary boosting may still over-specialize to early tree contributions. Try DART's tree dropout with `rate_drop=0.1`, retaining depth 6 and `colsample_bytree=0.8`. The DART paper describes dropout as a response to over-specialization in additive tree ensembles ([Korlakai Vinayak & Gilad-Bachrach, 2015](https://proceedings.mlr.press/v38/korlakaivinayak15.html)); the XGBoost [DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) documents `rate_drop` and notes that training may be slower. The 60-second harness training timeout will reveal whether this configuration fits the budget.

**Result — `51f67b5`:** Eval AUC **0.6782** (discard; current best 0.6805). DART took 8.0 seconds total training time versus about 0.6 seconds for the baseline tree booster, scored lower, and XGBoost 3.4.1 emitted a deprecation warning for `booster="dart"`. Move on to a different tree-growing policy.

## Experiment 22 proposal — leaf-wise growth policy (exploration)

**Hypothesis:** Depthwise growth allocates splits by level. `lossguide` chooses the available node with the highest loss change and may spend a fixed tree budget on more useful interactions. Test it with histogram trees, `max_depth=0`, and `max_leaves=64` (close to the 64-leaf upper bound of depth 6), retaining `colsample_bytree=0.8`. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) limits `lossguide` to `hist` or `approx` and defines the leaf cap.

**Result — `427a9de`:** Eval AUC **0.6793** (discard; current best 0.6805). Leaf-wise growth with a 64-leaf cap did not beat depthwise growth at depth 6.

## Experiment 23 proposal — parallel-tree random forest

**Hypothesis:** The previous tests used sequential gradient boosting. A standalone forest averages randomized trees and could reduce variance under the year-ahead split. XGBoost's [Random Forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) documents using `n_estimators=1`, `num_parallel_tree` for forest size, and `learning_rate=1`; the [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) supports row and per-node column sampling. Try 100 parallel trees with depth 6, `subsample=0.8`, and `colsample_bynode=0.8`, retaining native categorical handling and the starter features. The settings differ from prior row-sampling ablation because sampling now diversifies a bagged forest rather than sequential boosting.

**Result — `b5a1173`:** Eval AUC **0.6681** (discard; current best 0.6805). The 100-tree standalone forest was substantially worse than boosted trees on this split, despite taking about the same evaluation time. Restore the best boosted model and continue exploring within the remaining clock.

## Experiment 24 proposal — positive-class weighting

**Hypothesis:** Delays are the minority class, and changing their gradient/Hessian weight may alter split selection to improve ranking. XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) specifically suggests balancing positive and negative weights with `scale_pos_weight` when optimizing AUC; its [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) gives the negative-to-positive count ratio as a typical value. Test `scale_pos_weight=4` as an approximate ratio while keeping the best model configuration (`colsample_bytree=0.8`) and all features unchanged.

**Result — `df56ff3`:** Eval AUC **0.6776** (discard; current best 0.6805). The approximate four-to-one positive weighting reduced AUC; test a milder weight to check whether the effect is sensitive to weighting strength.

## Experiment 25 proposal — moderate positive-class weighting

**Hypothesis:** Weight 4 may have shifted tree splits too strongly. Test `scale_pos_weight=2` as a milder cost adjustment while retaining the best feature-sampled model. If AUC remains lower, return to the unweighted objective.

**Result — `6a4444c`:** Eval AUC **0.6776** (discard; current best 0.6805). Weight 2 produced the same rounded AUC as weight 4, so class reweighting does not help this ranking objective here.

## Experiment 26 proposal — finer histogram bins

**Hypothesis:** The model has only two continuous inputs, and finer quantization may expose more useful thresholds in scheduled departure time and distance. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `max_bin` defaults to 256, controls the discrete bins for histogram trees, and that increasing it can improve split optimality at additional computation cost. Test `max_bin=512` with the current best model and feature sampling.

**Result — `6823a44`:** Eval AUC **0.6786** (discard; current best 0.6805). Finer continuous-feature quantization did not improve this validation split; test a coarser 128-bin grid for a regularization effect.

## Experiment 27 proposal — coarser histogram bins

**Hypothesis:** Increasing `max_bin` to 512 lost 0.0019 AUC. A coarser grid (`max_bin=128`) could smooth noisy thresholds in HHMM departure time and distance while retaining the original features and best column-sampling setting.

**Result — `747da31`:** Eval AUC **0.6776** (discard; current best 0.6805). Coarser histogram bins also reduced AUC, so retain the default 256 bins.

## Experiment 28 proposal — feature sampling by depth level

**Hypothesis:** Tree-level feature sampling (`colsample_bytree=0.8`) is the only tested change that helped. Adding a mild `colsample_bylevel=0.8` may decorrelate splits deeper in each tree. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines level sampling as selecting columns at each new tree depth and says the `colsample_by*` controls apply cumulatively. This leaves roughly 5 of 8 inputs available at each split on average; test it without other changes.

**Result — `dec0f5e`:** Eval AUC **0.6774** (discard; current best 0.6805). Additional depth-level feature sampling reduced AUC; retain tree-level sampling alone.

## Experiment 29 proposal — gradient-based row sampling

**Hypothesis:** Uniform row sampling at 0.8 underperformed, but it may discard hard delayed examples indiscriminately. XGBoost's [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `gradient_based` sampling as favoring examples with larger regularized gradients and supports it with CPU histogram training in recent releases. Test gradient-based sampling at `subsample=0.8` with explicit `tree_method="hist"`, keeping the best feature sampling. This isolates the sampling strategy while using the documented compatible tree method.

**Result — `552054b`:** Eval AUC **0.6789** (discard; current best 0.6805). Gradient-based sampling was better than uniform row sampling at the same 0.8 rate, but still did not beat training on all rows.

## Experiment 30 proposal — feature sampling at each split

**Hypothesis:** The failed depth-level sampling applies one feature subset to a whole level. `colsample_bynode` selects columns for each split independently, which may add useful variation while retaining most features. XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this split-level behavior and notes the column-sampling controls multiply; test `colsample_bynode=0.9` alongside the winning `colsample_bytree=0.8`.

**Result — `d4cdfb6`:** Eval AUC **0.6790** (discard; current best 0.6805). Split-level column sampling also underperformed tree-level sampling alone.

## Synthesis after 30 non-baseline experiments

- **Best remains:** `0ea9a71`, Eval AUC **0.6805** (baseline 0.6743), with original features and `colsample_bytree=0.8` only.
- **Experiments 23–30:** The parallel-tree random forest (0.6681), positive weights 2 and 4 (both 0.6776), histogram bins 128/512 (0.6776/0.6786), depth-level feature sampling (0.6774), gradient-based row sampling at 0.8 (0.6789), and split-level feature sampling (0.6790) all lost.
- **Updated view:** The useful randomness is specifically one-time feature sampling per tree. More randomization within a tree, row sampling, class weighting, finer/coarser numerical thresholds, and a standalone forest have not improved year-ahead ranking. Continue with a different categorical split setting, where categories currently receive native XGBoost handling.

## Experiment 31 proposal — partition every categorical feature

**Hypothesis:** One-hot splits for high-cardinality airports may be too specific. The earlier `max_cat_to_onehot=32` test partitioned only larger categoricals and lost; test the stronger alternative `max_cat_to_onehot=1`, which the [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents as enabling optimal partitioning for every categorical feature. Keep all other best settings.

**Result — `129964d`:** Eval AUC **0.6805** (discard; ties current best). Partitioning every category matched the score, but evaluation took 34.2 seconds versus about 30.5 seconds for the best, so it was neither simpler nor faster.

## Experiment 32 proposal — modestly more boosting rounds

**Hypothesis:** The 300-round, 0.05-learning-rate run changed two factors and lost. Test a smaller increase to 150 rounds at the best learning rate (0.1), keeping feature sampling and all else fixed, to see whether additional sequential trees refine the ranking without the slower, smaller-step regime.

**Result — `c4f3c05`:** Eval AUC **0.6783** (discard; current best 0.6805). Increasing to 150 rounds at the original learning rate reduced AUC.

## Experiment 33 proposal — milder tree-level feature sampling

**Hypothesis:** `colsample_bytree=0.8` helped, while 0.6 tied. Test `colsample_bytree=0.9` as a milder sampling rate that retains more features per tree while still adding randomness.

**Result — `ad5e9a9`:** Eval AUC **0.6766** (discard; current best 0.6805). Tree-level sampling at 0.9 was too mild to retain the gain from 0.8.

## Final session summary

- **Best checkpoint:** `0ea9a71`, Eval AUC **0.6805**; baseline `b15ec66` scored **0.6743**, a gain of **0.0062**.
- **Kept change:** `colsample_bytree=0.8` with the starter features and default boosted-tree setup.
- **Main findings:** Other feature sampling rates and levels/nodes, row samplers, class weights, standalone random forest, histogram resolution, categorical split strategies, depth/growth settings, regularization, and additional boosting rounds did not improve the best score. The 100-tree standalone forest was notably worse (0.6681); partitioning all categories tied but evaluated more slowly.
- **Final state:** Return branch `oct5` to the best checkpoint before stopping the experiment timer.
