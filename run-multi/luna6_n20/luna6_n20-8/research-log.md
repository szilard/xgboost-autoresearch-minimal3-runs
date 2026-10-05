# Research log

## Baseline — commit `b15ec66`

Ran the starter `train.py` unchanged on the `oct5` branch. The harness completed successfully with Eval AUC **0.6743** (32.1 seconds total). This is the current best and comparison point. The starter uses native categorical features with 100 depth-6 trees, learning rate 0.1, and seed 42.

## Experiment 1 — commit `7cd821f` (keep)

**Hypothesis:** Reducing `max_depth` from 6 to 4 would reduce variance and transfer better from the 2005 training year to 2006 evaluation. This was motivated by XGBoost's [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), which identifies tree depth as a direct model-complexity control and notes that deeper models need enough data. Native categorical features remain unchanged, consistent with the [categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

**Result:** Eval AUC **0.6789**, up **0.0046** from baseline 0.6743. Run completed successfully in 32.0 seconds. Kept the change. This is evidence that the starter's depth-6 trees were too complex for year-to-year transfer; test one additional shallower setting before changing feature representation.

## Experiment 2 — commit `07f77a1` (keep)

**Hypothesis:** Since depth 4 improved substantially over depth 6, depth 3 might improve transfer further by reducing tree complexity another step. All parameters other than `max_depth` stayed fixed.

**Result:** Eval AUC **0.6798**, up **0.0009** over depth 4 and **0.0055** over baseline. Run completed successfully in 31.5 seconds. Kept the change. The local depth trend still favors shallower trees, though the incremental gain narrowed.

## Experiment 3 — commit `b6a334f` (discard)

**Hypothesis:** A directed `Origin_Dest` category could expose route-specific delay patterns directly, which a depth-3 tree might not recover from separate origin and destination fields. This followed the AIAA SciTech paper's observation that OD airport pairs can affect delays ([paper](https://junchen.sdsu.edu/proceedings/scitech_gnc19_Chen.pdf)). The feature used route levels fitted once from `train.csv`; unseen routes map to missing, so each row has the same encoding in training and row-wise evaluation. XGBoost supports native categorical partitioning ([guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).

**Result:** Eval AUC **0.6734**, down **0.0064** from the current best 0.6798. Evaluation also rose from about 30 seconds to 47.3 seconds, as per-row `prepare` now checks a 4,290-level route lookup. Discarded; the direct route category did not generalize here and adds scoring cost. Keep the shallower depth-3 model.

## Experiment 4 — commit `381d78b` (discard)

**Hypothesis:** Smoothed training-set delay rates for carrier, origin, and destination could supply compact group-risk signals that help shallow trees. Rates were shrunk toward the training prior with smoothing weight 200; training rows used leave-one-out sums and evaluation rows used full training lookups. No evaluation labels entered the rate features. This follows the shrinkage principle in [scikit-learn's TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html), which also stresses leakage control, and flight-delay research reports spatial/airport dependencies ([study](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)).

**Result:** Eval AUC **0.5819**, down **0.0979** from the current best 0.6798. The 42.0-second evaluation was also slower than the 30-second baseline. Discarded. The large drop indicates that these 2005 target-rate summaries do not transfer safely/usefully in this setup, despite smoothing and leave-one-out training rates.

## Experiment 5 — commit `346ee83` (discard)

**Hypothesis:** The gains from depth 6 to 4 and then 3 suggested another reduction to depth 2 might improve cross-year transfer. All other model settings were unchanged.

**Result:** Eval AUC **0.6751**, down **0.0047** from the depth-3 best. Run completed successfully in 31.9 seconds. Discarded. The tested depth sweep is non-monotonic: depth 3 is better than depths 2, 4, and 6.

## Experiment 6 — commit `b0680c4` (keep)

**Hypothesis:** Halving `learning_rate` to 0.05 and doubling estimators to 200 would let the model make smaller updates while preserving capacity, following XGBoost's [tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).

**Result:** Eval AUC **0.6807**, up **0.0009** over the depth-3 100-tree model. Run completed successfully in 32.9 seconds. Kept the paired setting. Current best is depth 3, 200 estimators, learning rate 0.05.

## Experiment 7 — commit `d4fd919` (discard)

**Hypothesis:** `subsample=0.8` might add useful randomness and improve robustness to the 2005-to-2006 shift, as suggested by XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html). All other settings stayed at the current best.

**Result:** Eval AUC **0.6787**, down **0.0020** from the 0.6807 best. Run completed successfully in 32.1 seconds. Discarded; training on all rows performed better here.

## Experiment 8 — commit `0c810e2` (discard)

**Hypothesis:** Halving the learning rate again to 0.025 and doubling rounds to 400 might continue the improvement from experiment 6. Other settings stayed fixed.

**Result:** Eval AUC **0.6803**, down **0.0004** from the current best 0.6807. Run completed successfully in 34.0 seconds. Discarded; the finer steps did not improve on 0.05.

## Experiment 9 — commit `c9b31b4` (discard)

**Hypothesis:** Setting `max_cat_threshold=32` would constrain high-cardinality native categorical partitions (especially origin and destination, each with 283 levels) and reduce overfitting. The [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this as a limit on categories considered per partition split and an overfitting control.

**Result:** Eval AUC **0.6776**, down **0.0031** from the current best 0.6807. Run completed successfully in 31.9 seconds. Discarded; this categorical regularization setting was too restrictive or otherwise unhelpful here.

## Experiment 10 — commit `a087aa0` (discard)

**Hypothesis:** Adding sine and cosine of scheduled minute-of-day would expose daily periodicity while retaining raw `CRSDepTime`, following a flight-delay study that used cyclical scheduled-time transforms ([study](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)).

**Result:** Eval AUC **0.6798**, below the current best 0.6807, with evaluation time increasing from 31.3 to 36.1 seconds. Discarded.

## Synthesis after 10 experiments

- **What helped:** Reducing `max_depth` from 6 to 4 and then 3 raised AUC; depth 2 fell back. The strongest model so far pairs depth 3 with 200 estimators and learning rate 0.05, reaching **0.6807** (commit `b0680c4`), +0.0064 over baseline.
- **What did not help:** A directed route category and smoothed target-rate lookups both hurt; the target-rate features caused a large drop. `subsample=0.8`, a tighter `max_cat_threshold`, 400 trees at learning rate 0.025, and cyclic departure-time features also failed to beat the best. The route and cyclic features increased evaluation time.
- **Current theory:** The 2005-to-2006 shift rewards restrained trees and a moderate learning rate. Additional learned group signals and feature transforms tested so far add variance or evaluation cost without improving AUC. Further work should focus on controlled regularization around the depth-3 model, one parameter at a time, before revisiting feature engineering.
- **Next direction:** Try `min_child_weight` above its default to regularize leaf splits while retaining the 200-tree, 0.05-learning-rate setup; then consider `gamma` or column sampling based on the result.

## Experiment 11 — commit `744ceef` (keep)

**Hypothesis:** Raising `min_child_weight` from its default 1 to 5 would suppress low-support leaves and improve cross-year transfer, following XGBoost's [parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

**Result:** Eval AUC remained **0.6807**. Run time was **31.8 seconds**, 1.1 seconds faster than the previous best's 32.9 seconds; training time was the same to the printed precision. Kept the setting under the equal-score/faster rule. Current best commit: `744ceef`.

## Experiment 12 — commit `4396a82` (discard)

**Hypothesis:** Adding `gamma=0.1` to the `min_child_weight=5` model would filter marginal splits and improve robustness; XGBoost defines gamma as the minimum loss reduction needed for a split ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

**Result:** Eval AUC tied at **0.6807**, but run time was 32.2 seconds versus 31.8 seconds for the current best. Discarded because it neither improved AUC nor speed/simplicity.

## Experiment 13 — commit `c71790f` (keep)

**Hypothesis:** Sampling 80% of columns per tree could reduce reliance on brittle features, a distinct regularization mechanism from row subsampling and one recommended for robustness in XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).

**Result:** Eval AUC **0.6809**, up **0.0002** over the prior best. Run completed successfully in 32.2 seconds. Kept the improvement. Current best: depth 3, learning rate 0.05, 200 trees, `min_child_weight=5`, `colsample_bytree=0.8`.

## Experiment 14 — commit `b1d6748` (discard)

**Hypothesis:** Milder column sampling at 0.9 might retain more useful predictors per tree while preserving the small gain at 0.8.

**Result:** Eval AUC **0.6800**, down **0.0009** from the current best 0.6809. Run completed successfully in 31.7 seconds. Discarded; 0.8 was better than 0.9.

## Experiment 15 — commit `9235693` (discard)

**Hypothesis:** A categorical departure hour could capture daily delay patterns that shallow trees cannot express with contiguous `HHMM` thresholds. The feature uses a fixed hour-level lookup from training data; prior flight-delay studies commonly include hour of day alongside scheduled departure time ([literature review](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1)).

**Result:** Eval AUC **0.6791**, down **0.0018** from the current best. Evaluation increased to 35.2 seconds. Discarded; raw scheduled time performed better and faster.

## Experiment 16 — commit `107c880` (discard)

**Hypothesis:** Setting `max_cat_to_onehot=21` would use one-hot splits for the 7-level weekday, 12-level month, and 20-level carrier fields while retaining partition splits for day-of-month and airports. XGBoost's [3.4.1 API documentation](https://xgboost.readthedocs.io/en/stable/python/python_api.html) defines this category-count threshold.

**Result:** Eval AUC **0.6786**, down **0.0023** from the current best. Run completed successfully in 32.0 seconds. Discarded; this low-cardinality one-hot strategy was too aggressive.

## Experiment 17 — commit `7a1cbf0` (keep)

**Hypothesis:** Increasing `min_child_weight` from 5 to 10 might further suppress low-support leaves without losing useful signal.

**Result:** Eval AUC tied at **0.6809**. Run time was 31.8 seconds versus 32.2 seconds for the previous best, so the setting meets the faster tie rule. Kept. Current best: depth 3, 200 estimators, learning rate 0.05, `min_child_weight=10`, `colsample_bytree=0.8`.

## Experiment 18 — commit `5486160` (discard)

**Hypothesis:** Increasing `min_child_weight` from 10 to 20 might continue the equal-score/faster pattern by further limiting weak leaves.

**Result:** Eval AUC **0.6805**, down **0.0004** from the current best 0.6809. Run completed successfully in 32.2 seconds. Discarded; `min_child_weight=10` is a better regularization point.

## Experiment 19 — commit `0d83c44` (discard)

**Hypothesis:** Raising `reg_lambda` from 1 to 2 might regularize leaf weights enough to improve transfer. XGBoost documents lambda as L2 weight regularization and says larger values make the model more conservative ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

**Result:** Eval AUC tied at **0.6809**, but the 32.1-second run was 0.3 seconds slower than the current best. Discarded under the equal-score rule.

## Experiment 20 — commit `cfa6046` (discard)

**Hypothesis:** Reducing `max_bin` from 256 to 128 would coarsen histogram cut candidates for scheduled time and distance, potentially suppressing fragile splits. XGBoost documents `max_bin` as the number of bins for continuous features ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

**Result:** Eval AUC **0.6802**, down **0.0007** from the current best. Run completed successfully in 32.1 seconds. Discarded.

## Synthesis after 20 experiments

- **Best result:** Eval AUC **0.6809**. Commit `7a1cbf0` (`min_child_weight=10`) ties `c71790f` (`colsample_bytree=0.8`) and ran 0.4 seconds faster, so `7a1cbf0` is the current best. This is +0.0066 over the 0.6743 baseline.
- **What helped:** Shallower depth was the largest gain: depth 4 and then 3 improved markedly over depth 6, while depth 2 underfit. Lowering learning rate to 0.05 and doubling trees to 200 added another 0.0009. Column sampling at 0.8 added 0.0002; 0.9 was worse. `min_child_weight=10` preserved the best AUC at slightly faster measured runtime.
- **What did not help:** Route categories, smoothed target-rate features, cyclic/time-hour features, low-cardinality one-hot splitting, and categorical split caps all lost AUC or made evaluation slower. Row subsampling, a second learning-rate reduction, stronger gamma/L2, stronger child-weight 20, and fewer histogram bins also failed to beat the best.
- **Current theory:** The year-to-year shift benefits most from controlled tree capacity with moderately slow boosting. Adding group summaries or derived time/route representations appears less stable than the original features. Mild column sampling helps; more aggressive feature or leaf constraints begin to underfit.
- **Next direction:** Research ensemble and alternative-booster options, then test one distinct model averaging or boosting strategy while keeping the current best as the comparison point.

## Experiment 21 — commit `33d9cc5` (discard)

**Hypothesis:** Averaging three depth-3, 200-tree models with different random seeds might reduce variance from `colsample_bytree=0.8`. XGBoost uses the seed to control its random generator, and scikit-learn describes soft voting as averaging class probabilities ([XGBoost RF guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html), [VotingClassifier docs](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html)).

**Result:** Eval AUC **0.6805**, down **0.0004** from the single-model best. Run completed successfully in 33.1 seconds. Discarded; the extra seeds did not improve ranking.

## Experiment 22 — commit `d26b538` (discard)

**Hypothesis:** A standalone bagged forest might transfer more robustly than sequential boosting. Used one boosting round with 200 parallel depth-3 trees, `subsample=0.8`, and `colsample_bynode=0.8`, following XGBoost's [random forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html).

**Result:** Eval AUC **0.6538**, down **0.0271** from the 0.6809 best. Run completed successfully in 32.7 seconds. Discarded; this dataset needs sequential boosting rather than a standalone shallow forest.

## Experiment 23 — commit `c4cd1ea` (discard; follow-up)

**Hypothesis:** Setting `reg_alpha=0.1` may shrink small leaf weights and improve year-to-year transfer. This tests L1 regularization, distinct from the `reg_lambda=2` L2 trial, which tied at 0.6809 but was slower. XGBoost documents alpha as L1 regularization on weights and says larger values make the model more conservative ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

**Result:** Eval AUC **0.6800**, down **0.0009** from the 0.6809 best. Run completed successfully in 32.5 seconds. Discarded.

## Experiment 24 — commit `13b22a4` (discard; follow-up)

**Hypothesis:** Setting `subsample=0.95` may add mild row-sampling regularization to the current `min_child_weight=10`, `colsample_bytree=0.8` model while retaining more training rows than the earlier `subsample=0.8` trial, which scored 0.6787. XGBoost samples rows once per boosting iteration; this tests whether the stronger current leaf and column constraints make a milder rate useful ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

**Result:** Eval AUC **0.6796**, down **0.0013** from the 0.6809 best. Run completed successfully in 32.0 seconds. Discarded.

## Experiment 25 — commit `7dda356` (discard; exploration)

**Hypothesis:** A histogram tree grown with `grow_policy="lossguide"`, `max_depth=0`, and `max_leaves=8` may allocate the same maximum eight leaves as a depth-3 binary tree more efficiently across uneven flight patterns. XGBoost documents `lossguide` as prioritizing nodes with the highest loss change; the eight-leaf cap keeps the complexity budget bounded ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

**Result:** Eval AUC **0.6802**, down **0.0007** from the 0.6809 best. Run completed successfully in 31.7 seconds. Discarded.

## Experiment 26 — commit `0e0474f` (discard; follow-up)

**Hypothesis:** Setting `max_cat_threshold=128` may restore useful airport-category partitions lost when `max_cat_threshold=32` scored 0.6776, with `min_child_weight=10` constraining weak leaves. XGBoost describes this as the category cap considered for each partition-based split ([parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html)).

**Result:** Eval AUC **0.6800**, down **0.0009** from the 0.6809 best. Run completed successfully in 32.3 seconds. Discarded.

## Experiment 27 — commit `6014594` (discard; exploration)

**Hypothesis:** Adding a numeric day-of-year feature from each row's month and day may expose smooth annual seasonality that the separate categorical month and day fields do not. A 2024 flight-delay study derives Gregorian day-of-year and reports it among its most influential features, though its data and airline context differ from this task ([study](https://onlinelibrary.wiley.com/doi/full/10.1155/2024/3385463)). The feature is computed only from the row's date fields.

**Result:** The first attempt produced a string-typed feature and crashed before scoring; converting month and day to numeric fixed the issue. The corrected run completed in 37.0 seconds and scored **0.6803**, down **0.0006** from the best. Discarded.

## Final summary

- **Best:** Eval AUC **0.6809** at commit `7a1cbf0`, an improvement of **0.0066** over the 0.6743 baseline. It ties `c71790f` and ran 0.4 seconds faster.
- **What helped:** Reducing tree depth to 3, using 200 trees at learning rate 0.05, and sampling 80% of columns. Raising `min_child_weight` to 10 retained the best score while reducing run time.
- **What did not help:** Route and target-rate features, alternate time representations, stronger regularization, row subsampling, a parallel-tree forest, leaf-wise growth, a wider categorical split cap, and numeric day-of-year all scored below the best.
- **Next:** Explore carefully chosen interactions between scheduled departure time and carrier or calendar fields, while keeping all per-row features self-contained and comparing against the current best.
