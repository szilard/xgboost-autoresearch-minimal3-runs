# Research log

## Experiment 1 hypothesis — scheduled departure hour category

- **Type:** exploration / feature engineering.
- **Hypothesis:** the numeric scheduled-departure field captures a global time ordering, while a coarse hour category may let the trees group hours with similar delay behavior. Keep raw `CRSDepTime` and add only a 0–23 hour category, fitted from `train.csv`, so the experiment isolates the added representation.
- **Data observation:** all 200,000 training times decode as valid HHMM; flights cluster during daytime (especially 15:00–19:00) and overnight hours are sparse.
- **Research:** XGBoost's categorical splits can group categories by learned leaf values ([categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)); its tuning guide emphasizes understanding the data and balancing tree complexity ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)). The scikit-learn time-feature guide says tree models can learn nonlinear effects from raw ordinal time ([time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)), so this tests an additional grouping rather than replacing the raw feature with a cyclic transform. Flight-delay research also finds airport and flight-context features useful, though its richer weather and traffic data are unavailable here ([Shao et al., 2019](https://arxiv.org/abs/1911.01605)).
- **Result:** commit `f685e45`, Eval AUC **0.6747** (`ok`, kept), up from 0.6743. The small improvement supports testing a row-local carrier/route interaction next; a route key may give the model direct access to pair identity beyond separate Origin and Dest features.

## Experiment 2 hypothesis — directional route category

- **Type:** exploration / feature engineering.
- **Hypothesis:** separate `Origin` and `Dest` categories may not efficiently expose route-specific delay patterns. Add one train-fitted `Origin→Dest` category while retaining both airports and the successful departure-hour feature. It has 4,290 levels in `train.csv`, so sparse-route overfitting is a material risk.
- **Research:** XGBoost's categorical handling partitions category values into groups during splits ([categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)). Flight-delay work studies spatial and flight-context signals, including airport traffic complexity combined with flight information ([Shao et al., 2019](https://arxiv.org/abs/1911.01605)); those extra operational measurements are absent here, so the route pair is a low-cost proxy to test.
- **Result:** commit `68e9e29`, Eval AUC **0.6660** (`ok`, discarded), versus 0.6747 kept. The route category increased artifact size to 17.5 MB and eval time to 52.5 s, while reducing AUC by 0.0087. The 4,290-level route identity is too sparse or unstable across the 2005→2006 split in this form; revert it and focus on lower-cardinality or regularized signals.

## Experiment 3 hypothesis — smoothed carrier and airport delay rates

- **Type:** exploration / supervised feature engineering.
- **Hypothesis:** carrier-, origin-, and destination-level historical delay propensities may add a compact numeric signal beyond native categorical splits. Fit smoothed train-only lookups, with 5-fold out-of-fold encodings for training rows and full-train lookups at scoring time. Use `alpha=100` to shrink sparse groups toward the balanced train prior; the 2005→2006 year shift may limit transfer.
- **Research:** scikit-learn recommends cross-fitting target encodings to avoid leakage and describes smoothing toward the global target mean ([TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). The CatBoost paper explains both target-statistic smoothing and the train/test shift caused by naive target encodings ([Prokhorenkova et al., 2018](https://papers.nips.cc/paper_files/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf)). Flight-delay studies also use airline, origin, and destination information ([PLOS One study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0335141)).
- **Result:** commit `be1b246`, Eval AUC **0.6756** (`ok`, kept), up 0.0009 from the hour-category model and 0.0013 from baseline. Cross-fit carrier/airport rates add a small positive signal without a large artifact; next, test whether stronger smoothing helps the 2005→2006 transfer by reducing noisy airport-rate estimates.

## Experiment 4 hypothesis — stronger target-rate smoothing

- **Type:** follow-up to the positive target-rate result.
- **Hypothesis:** increasing the prior weight from 100 to 300 should reduce noise in smaller origin/destination groups and may transfer better across the year boundary. Keep the encoding columns and cross-fitting scheme fixed so only the smoothing strength changes.
- **Research:** scikit-learn's `TargetEncoder` documentation states that a larger smoothing value puts more weight on the global target mean ([documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)).
- **Result:** commit `abf9720`, Eval AUC **0.6753** (`ok`, discarded), down 0.0003 from the `alpha=100` result. Stronger shrinkage did not help; retain `alpha=100`.

## Experiment 5 hypothesis — row and feature subsampling

- **Type:** exploration / model regularization.
- **Hypothesis:** the feature set now exposes additional interactions, and stochastic sampling may reduce sensitivity to the 2005 training sample and transfer better to 2006. Set `subsample=0.8` and `colsample_bytree=0.8`, holding the current features and all other model parameters fixed.
- **Research:** XGBoost's tuning notes recommend subsampling rows and columns as a way to add randomness and make training more robust ([parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `2d42846`, Eval AUC **0.6771** (`ok`, kept), up 0.0015 from the best feature-only model. AUC improved while artifact size fell to 2.2 MB; next, ablate column sampling while retaining row sampling to identify whether both sources of randomness are needed.

## Experiment 6 hypothesis — remove column sampling

- **Type:** ablation/simplification of the promising sampling result.
- **Hypothesis:** test whether `subsample=0.8` alone preserves the 0.6771 score. Remove `colsample_bytree=0.8` (return to its default of 1.0) and leave all other settings fixed. If the AUC is equal or higher, keep the simpler parameter set.
- **Research:** XGBoost documents `subsample` and `colsample_bytree` as separate randomness controls for tree construction ([parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `7ff549e`, Eval AUC **0.6759** (`ok`, discarded), down 0.0012 from the combined setting. Row sampling alone lost the gain, so keep both sampling controls.

## Experiment 7 hypothesis — shallower trees

- **Type:** follow-up model-complexity tuning.
- **Hypothesis:** reducing `max_depth` from 6 to 4 may lower overfitting on the sampled 2005 data while retaining the established gains from hour categories, smoothed rates, and both sampling controls. Keep every other setting fixed.
- **Research:** XGBoost's parameter reference says increasing `max_depth` makes trees more complex and more likely to overfit ([tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Result:** commit `643da81`, Eval AUC **0.6804** (`ok`, kept), up 0.0033 from the depth-6 model. The artifact also fell to 0.6 MB. The strong depth response motivates trying depth 3 next to see whether the gain continues as interactions are constrained.

## Experiment 8 hypothesis — depth 3 follow-up

- **Type:** follow-up to the strong depth-4 result.
- **Hypothesis:** test whether another reduction in interaction depth improves transfer to 2006. Change only `max_depth` from 4 to 3; keep target rates, hour category, and both sampling controls.
- **Research:** the XGBoost parameter reference describes `max_depth` as a direct model-complexity control and warns that deeper trees can overfit ([tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Result:** commit `adb69f9`, Eval AUC **0.6779** (`ok`, discarded), down 0.0025 from depth 4. The improvement peaked at depth 4 rather than continuing with shallower trees.

## Experiment 9 hypothesis — depth 5 bracket

- **Type:** follow-up parameter search around the depth-4 improvement.
- **Hypothesis:** depth 5 may preserve more useful interactions than depth 4 while avoiding some of the overfit seen at depth 6. Change only `max_depth`; compare against the measured depth-4, depth-3, and depth-6 results.
- **Research:** XGBoost's parameter guide identifies depth as a complexity/overfitting control ([tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Result:** commit `8f52a9e`, Eval AUC **0.6790** (`ok`, discarded), below depth 4 by 0.0014 but above depth 6. Depth 4 remains the best tested point.

## Experiment 10 hypothesis — slower boosting with more trees

- **Type:** follow-up model tuning on the depth-4 configuration.
- **Hypothesis:** 200 trees at `learning_rate=0.05` may provide smoother updates than 100 trees at 0.1 while keeping the same approximate total learning-rate budget. Keep depth 4, both sampling settings, and all features fixed.
- **Research:** XGBoost's tuning notes recommend reducing `eta`/learning rate while increasing the number of boosting rounds ([parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `17c36c9`, Eval AUC **0.6810** (`ok`, kept), up 0.0006 from depth 4 with 100 trees. Lower learning rate and more rounds gave a modest further gain.

## Synthesis after 10 experiments (baseline excluded)

- **What helped:** a categorical departure hour (+0.0004), cross-fit smoothed carrier/airport rates (+0.0009 over the hour model), both row and column sampling (+0.0015 over feature engineering alone), depth 4 (+0.0033), and 200 trees at learning rate 0.05 (+0.0006). Best Eval AUC is **0.6810** at `17c36c9`.
- **What did not:** the 4,290-level route category hurt AUC by 0.0087 and enlarged/slowed the artifact; alpha 300 was worse than alpha 100; row sampling alone lost the combined sampling gain; depths 3 and 5 both trailed depth 4.
- **Current theory:** transfer to the later year benefits from moderate regularization plus stable, smoothed low-cardinality delay propensities. Sparse route identity overfits. More trees at a smaller step size help slightly after depth and sampling are controlled.
- **Next direction:** research categorical split controls and time/day interaction features, then test one new direction at a time.

## Experiment 11 hypothesis — carrier-by-hour interaction

- **Type:** exploration / feature engineering.
- **Hypothesis:** delay patterns by departure hour may differ across carriers, so a direct `UniqueCarrier × DepHour` category could expose an interaction that depth-4 trees otherwise need multiple splits to represent. Add only this row-local, train-vocabulary category; keep the best model settings and all existing features fixed.
- **Research:** a Berkeley flight-delay feature study reports that late-night delay patterns vary by carrier and describes departure-hour blocks as operationally meaningful ([project report](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). XGBoost's native categorical handling supports grouped splits ([categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html)).
- **Result:** commit `f784cec`, Eval AUC **0.6791** (`ok`, discarded), down 0.0019 from the best model. The carrier-hour interaction category was slower to score and did not transfer well; retain the standalone departure-hour category.

## Experiment 12 hypothesis — smoothed route delay rate

- **Type:** follow-up to the failed raw route category and the positive low-cardinality target-rate features.
- **Hypothesis:** a smoothed numeric route propensity may preserve signal from frequent origin-destination pairs while shrinking sparse routes toward the balanced train prior. Add one route target-rate lookup with `alpha=100`, using the existing five-fold out-of-fold encodings for training rows; do not expose route counts as features.
- **Research:** target statistics can represent high-cardinality categories numerically, but naive encodings leak labels; smoothing and cross-fitting address these risks ([CatBoost paper](https://papers.nips.cc/paper_files/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf), [scikit-learn TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). The previously kept carrier/airport rates at this smoothing value provide the task-specific reason to test it.
- **Result:** commit `86b0e19`, Eval AUC **0.6804** (`ok`, discarded), 0.0006 below the current best. Smoothing reduced route-category cost, but the route rate added no predictive value beyond the existing carrier/airport rates; revert it.

## Experiment 13 hypothesis — categorical split cap

- **Type:** exploration / categorical regularization.
- **Hypothesis:** reducing the maximum categories considered in partition-based splits to 32 may constrain overfitting in the 283-level origin/destination features. Keep all features and other model settings fixed.
- **Research:** XGBoost documents `max_cat_threshold` as the maximum number of categories considered per split and says it is used to prevent overfitting in categorical partitioning ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Result:** commit `aeb53e2`, Eval AUC **0.6798** (`ok`, discarded), down 0.0012 from the best. Restricting categorical splits to 32 did not improve transfer; keep the library default.

## Experiment 14 hypothesis — minimum child weight

- **Type:** exploration / node-level regularization.
- **Hypothesis:** increasing `min_child_weight` from 1 to 5 may suppress splits based on small, unstable subsets while retaining useful airport and schedule effects. Keep the best depth, learning rate, tree count, and sampling settings.
- **Research:** XGBoost defines `min_child_weight` as the minimum Hessian sum needed in a child and says larger values make the model more conservative ([tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Result:** commit `9fd5bca`, Eval AUC **0.6810** (`ok`, discarded). It tied the best to four decimals but added a parameter and did not run faster, so the keep rule favors the simpler depth-4 configuration.

## Experiment 15 hypothesis — minimum split gain

- **Type:** exploration / tree regularization.
- **Hypothesis:** requiring `gamma=1` loss reduction before a split may suppress weak patterns that do not transfer to 2006. Keep the best feature set, depth, learning rate, tree count, and sampling settings fixed.
- **Research:** XGBoost defines `gamma` as the minimum loss reduction required for a further partition; larger values make the model more conservative ([tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- **Result:** commit `180276f`, Eval AUC **0.6810** (`ok`, discarded). It tied the best to four decimals and did not improve runtime, so the added parameter does not satisfy the keep rule.

## Experiment 16 hypothesis — 400 trees at 0.025

- **Type:** follow-up to the positive 200-tree / 0.05 learning-rate result.
- **Hypothesis:** another halving of the learning rate with twice as many trees may smooth boosting updates while preserving the approximate cumulative learning-rate budget. Change only those paired schedule values.
- **Research:** XGBoost recommends decreasing learning rate while increasing boosting rounds as a tuning direction ([parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- **Result:** commit `465336c`, Eval AUC **0.6808** (`ok`, discarded), 0.0002 below 200 trees at 0.05. The extra rounds did not continue the small prior gain; retain 200 / 0.05.

## Experiment 17 hypothesis — remove the derived departure hour

- **Type:** ablation/simplification of the early hour-category improvement.
- **Hypothesis:** `DepHour` raised the starter AUC by only 0.0004, while raw `CRSDepTime` remains available and the model now uses shallower trees plus historical rates. Remove the derived category to test whether it is redundant in the best configuration; keep it only if removing it lowers AUC.
- **Research:** scikit-learn's time-feature guide notes that tree models can learn nonlinear time patterns from raw ordinal features ([time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)).
- **Result:** commit `d2b3ebc`, Eval AUC **0.6805** (`ok`, discarded), 0.0005 below the best. Eval was 4.6 s faster, but the AUC drop violates the keep rule; restore `DepHour`.

## Experiment 18 hypothesis — five time-of-day bands

- **Type:** exploration / alternative schedule encoding.
- **Hypothesis:** the 24-level `DepHour` category helps, but a five-band feature may capture broad operational differences with less granularity. Replace `DepHour` with early/late night (00–05), morning (06–11), afternoon (12–16), evening (17–19), and night (20–23), retaining raw `CRSDepTime`.
- **Research:** a flight-delay study created these five time bands and reports different delay-rate patterns by part of day and weekday ([thesis, feature-engineering section](https://arno.uvt.nl/show.cgi?fid=187024)). Its 2019 setting differs from this 2005→2006 task, so this is a testable encoding hypothesis rather than direct evidence of transfer.
- **Result:** commit `9f1f40d`, Eval AUC **0.6806** (`ok`, discarded), 0.0004 below the best. The broad bands did not match the value of the 24-level hour category; restore `DepHour`.

## Experiment 19 hypothesis — weaker target-rate smoothing

- **Type:** follow-up to the positive `alpha=100` target-rate features.
- **Hypothesis:** reducing the prior weight to 50 may preserve more carrier/airport-specific signal. `alpha=300` was slightly worse than 100 in the earlier configuration; keep the current model and feature set fixed while testing 50.
- **Research:** target-encoding documentation describes the tradeoff between category-specific means and the global prior ([scikit-learn TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)).
- **Result:** commit `708de79`, Eval AUC **0.6804** (`ok`, discarded), 0.0006 below `alpha=100`. More category-specific rates did not improve transfer; retain `alpha=100`.

## Experiment 20 hypothesis — day of year

- **Type:** exploration / temporal feature engineering.
- **Hypothesis:** a numeric seasonal position derived from `Month` and `DayofMonth` may let shallow trees represent smooth seasonal effects and interactions more directly than the two separate categories. Add one row-local `DayOfYear` feature; do not read external calendar data.
- **Research:** a flight-delay study lists day of year among its engineered temporal features ([PLOS One study](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0335141)). This supports testing the representation, not assuming it transfers to this dataset.
- **Result:** commit `c0309ed`, Eval AUC **0.6831** (`ok`, kept), up 0.0021 from the previous best. The first run crashed because calendar fields are stored as `c-*` strings; parsing those suffixes as integers fixed the feature. The corrected run completed in 49.6 s.

## Synthesis after 20 experiments (baseline excluded)

- **Best result:** Eval AUC **0.6831** at `c0309ed`.
- **What helped:** the departure-hour category gave a small early gain; cross-fit smoothed carrier/airport delay rates added signal; row and column sampling together helped; depth 4 clearly outperformed depths 3, 5, and 6; 200 trees at 0.05 improved slightly over 100 at 0.1; and `DayOfYear` added the strongest recent gain (+0.0021).
- **What did not:** raw route categories, route target rates, and carrier-hour categories failed to transfer; five broad time bands and removal of `DepHour` were worse; stronger/weaker target-rate smoothing than 100 was worse; categorical split cap and extra tree constraints did not help; 400 trees at 0.025 slightly trailed.
- **Current theory:** smooth calendar position and moderate tree regularization help the 2005→2006 transfer, while sparse operational identity interactions are unstable. Carrier/origin/destination target rates remain useful when smoothed and cross-fit.
- **Next:** test whether `Month` still adds signal once `DayOfYear` is present; then consider a periodic encoding of the annual position if time remains.

## Experiment 21 hypothesis — ablate Month after DayOfYear

- **Type:** ablation/simplification of the day-of-year improvement.
- **Hypothesis:** `DayOfYear` carries both month and day ordering, so `Month` may be redundant. Remove only `Month` while keeping `DayOfYear`, `DayofMonth`, and all model settings; if AUC is equal or higher, keep the simpler representation.
- **Result:** commit `9c59de7`, Eval AUC **0.6842** (`ok`, kept), up 0.0011. `DayOfYear` carries useful season order, and the separate `Month` category was redundant or noisy in this configuration.

## Experiment 22 hypothesis — ablate DayofMonth after DayOfYear

- **Type:** ablation/simplification of the calendar representation.
- **Hypothesis:** `DayOfYear` also contains day-of-month information. Remove only the `DayofMonth` category and retain `DayOfYear`; if AUC is equal or higher, keep the simpler calendar features.
- **Result:** commit `794421a`, Eval AUC **0.6859** (`ok`, kept), up 0.0017. With `DayOfYear` present, both separate month and day-of-month categories were redundant; keep weekday as a distinct signal.

## Experiment 23 hypothesis — cyclic annual position

- **Type:** follow-up feature engineering on the strong `DayOfYear` result.
- **Hypothesis:** sine/cosine terms may encode the December-to-January wrap without an artificial numeric edge. Add both periodic terms while retaining raw `DayOfYear` and all other features.
- **Research:** scikit-learn's time-feature guide describes sine/cosine transforms as a way to encode periodic features without a jump between the range endpoints ([guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)).

## Baseline — `b15ec66`

- Ran the unmodified starter model on the prescribed train/eval split.
- Eval AUC: **0.6743** (`ok`, 33.1 s total).
- This is the comparison point for subsequent experiments.

- **Result:** commit `42af8ba`, Eval AUC **0.6843** (`ok`, discarded), 0.0016 below the best. The annual sine/cosine terms did not improve this model when added alongside raw `DayOfYear`.

## Session closeout

- **Best result:** Eval AUC **0.6859** at `794421a` (remove `DayofMonth` while retaining `DayOfYear`).
- **Kept improvements:** departure hour, cross-fit smoothed carrier/origin/destination delay rates, row and column subsampling, depth 4, 200 trees at learning rate 0.05, and `DayOfYear` with separate `Month` and `DayofMonth` categories removed.
- **Latest rejected change:** annual sine/cosine features alongside raw `DayOfYear` reduced AUC to 0.6843.
- **Restore:** reset the working branch to the best commit `794421a`.
