# Research log — oct5

## Baseline

- Commit `8d9c760`: unchanged starter, Eval AUC 0.6743, 31.8s total.
- Training data: 200,000 rows, no missing values. `CRSDepTime` is HHMM; date fields are categorical strings of the form `c-11`.
- Initial research: [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends complexity and subsampling controls; [categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains native categorical partitioning; [flight delay research](https://arxiv.org/abs/1911.01605) motivates time and airport context. I will test schedule, calendar, and airport features, then model complexity.

## Experiment 1 — exploration

- Hypothesis: converting HHMM to minutes since midnight will give XGBoost ordered thresholds that align with actual clock time, especially across hour boundaries. This is a per-row transformation and is safe for row-by-row evaluation.
- Result `f26673c`: 0.6743 (equal), discarded. On reflection, valid HHMM and minute-of-day have the same order, so a threshold tree already has the same possible partitions. The extra column only duplicates information; this was a weak hypothesis.

## Experiment 2 — exploration

- Hypothesis: calendar fields supplied as categorical strings lose useful order. Numeric month and day-of-month allow adjacent days to share tree thresholds, helping generalization to 2006. Day of week remains categorical because its ordering is cyclic.
- Result `bee3302`: 0.6774 (+0.0031), kept. Calendar order matters. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html) confirms numeric features use thresholds while categorical features use category sets. [UC Berkeley's flight-delay study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) supports month, weekday, and departure-time patterns.

## Experiment 3 — follow-up

- Hypothesis: 100 boosting rounds may underfit the time and airport effects. Increase to 300 trees at the same learning rate to test whether added capacity improves cross-year AUC. XGBoost's [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes the tradeoff between rounds and learning rate.
- Result `4861a20`: 0.6655 (-0.0119), discarded. More rounds strongly overfit cross-year evaluation. Training EDA shows large time-of-day and month effects but likely year-specific noise. Next, reduce individual tree complexity.

## Experiment 4 — follow-up

- Hypothesis: max depth 6 may capture brittle carrier-airport-date interactions. Reducing to depth 4 at 100 rounds should regularize those interactions while preserving main effects. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommend max_depth as a complexity control.
- Result `72f1958`: 0.6838 (+0.0064), kept. Strong evidence that less complex trees generalize better to 2006.

## Experiment 5 — follow-up

- Hypothesis: with depth 4 regularization, another 50 boosting rounds may learn stable weak effects without the depth 6 overfit seen at 300 rounds. Try 150 rounds, leaving other settings fixed.
- Result `e33a92d`: 0.6827 (-0.0011), discarded. Even at depth 4, more boosting is slightly worse across years.

## Experiment 6 — follow-up

- Hypothesis: depth 3 may further reduce brittle higher-order interactions. Keep 100 rounds to isolate the depth effect.
- Result `76e69bc`: 0.6848 (+0.0010), kept. Simpler trees continue to generalize better across years.

## Experiment 7 — follow-up

- Hypothesis: depth 2 may help further by emphasizing stable main effects and pairwise interactions. Hold 100 rounds fixed to finish the depth sweep.
- Result `4989c74`: 0.6811 (-0.0037), discarded. Depth 2 loses useful interactions; depth 3 is the best tested.

## Experiment 8 — follow-up

- Hypothesis: depth 3 trees have less per-tree capacity than depth 4, so 150 rounds might recover stable interactions without the overfit seen at depth 4. This differs from experiment 5 specifically in tree depth.
- Result `339b036`: 0.6851 (+0.0003), kept. A few more shallow trees help; improvement is modest.

## Experiment 9 — exploration

- Hypothesis: the native categorical partition strategy may group small categorical fields by aggregate effect, but some carriers and weekdays might merit their own branches. Test one-hot splitting for fields with at most 20 categories using `max_cat_to_onehot=21`; airports remain partitioned. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/release_3.2.0/tutorials/categorical.html) explains the two split strategies.
- Result `ca0de2b`: 0.6823 (-0.0028), discarded. Partitioning is preferable for the small categories here.

## Experiment 10 — exploration

- Hypothesis: a route category can expose origin-destination interaction to shallow trees, which otherwise need two splits before learning route-specific effects. Train contains 4,290 routes; unseen routes become missing. [A flight-delay study](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057) lists routes alongside origin, departure time, and carrier as predictors; the [CatBoost paper](https://papers.nips.cc/paper_files/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf) explains why combinations of categories can capture dependencies. Cardinality may overfit, so this is exploratory.
- Result `284dc56`: 0.6756 (-0.0095), discarded. The 4,290-category route feature appears too sparse to generalize across years; eval also slowed to 39.6s.

## Synthesis after 10 experiments

- Best: `339b036`, 0.6851. Numeric month/day, depth 3, and 150 rounds helped.
- More complex models and high-cardinality interactions hurt: 300 depth-6 rounds, route category, and one-hot carrier/weekday all lost AUC. Depth 2 underfit.
- Current theory: stable broad seasonal and airline/airport effects matter more than granular 2005-specific route patterns. Next, test regularization of small/noisy tree leaves and then simpler time/calendar features.
- New research: [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends `min_child_weight`, `gamma`, `max_cat_threshold`, and subsampling for overfit; [XGBoost parameter reference](https://xgboost.readthedocs.io/en/latest/parameter.html) defines their effects.

## Experiment 11 — follow-up

- Hypothesis: the remaining depth-3 trees may still create leaves on small, noisy airport subsets. Set `min_child_weight=5` to require more Hessian mass per leaf while keeping the successful tree depth and boosting rounds.
- Result `e0bc7ca`: 0.6851 (equal), discarded because it adds a parameter without improving AUC or speed.

## Experiment 12 — exploration

- Hypothesis: random sampling of 80% of training rows per tree will decorrelate trees and reduce reliance on idiosyncratic 2005 flights. Test `subsample=0.8`, as suggested by [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).
- Result `1f74115`: 0.6851 (equal), discarded; no AUC or speed gain.

## Experiment 13 — ablation/simplification

- Hypothesis: day-of-month can encode 2005-specific weather events whose dates will not repeat in 2006. Training day-specific delay rates vary widely, so dropping day-of-month could improve transfer and simplify `prepare`. Month remains to capture seasonality.
- Result `5a5b7c3`: 0.6811 (-0.0040), discarded. Day-of-month carries useful repeatable information despite event noise.

## Experiment 14 — follow-up

- Hypothesis: a numeric day-of-year will represent seasonal progression within and across months in one feature, improving shallow trees' ability to learn summer and winter patterns. Compute it from month and day per row with a fixed non-leap-year lookup; both 2005 and 2006 are non-leap years. [UC Berkeley's flight-delay study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes temporal patterns including month.
- Result `e1fdcfc`: 0.6857 (+0.0006), kept. Smooth seasonal position helps a little; eval time is 30.5s.

## Experiment 15 — follow-up

- Hypothesis: day-of-year has an artificial break between December 31 and January 1. Sine and cosine of annual position place neighboring dates near each other and may help shallow trees capture winter behavior. [Scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) demonstrates cyclic encodings, while noting tree models often need less preprocessing. Test two annual terms as a deliberately small extension.
- Result `2217929`: 0.6838 (-0.0019), discarded. Explicit trigonometric terms add noise or redundant splits for this tree model.

## Experiment 16 — exploration

- Hypothesis: scheduled departure time is by far the highest-gain feature, and a categorical hour may let XGBoost group nonadjacent late-night hours without extra thresholds. Fit hour category levels on train and add a per-row hour category, retaining raw HHMM for within-hour variation. [Scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses categorical time-step representations.
- Result `be9bf3c`: 0.6848 (-0.0009), discarded. Numeric HHMM appears sufficient; extra hour category costs 3s in eval.

## Experiment 17 — exploration

- Hypothesis: airport category splits may be fitting rare 2005-specific airport effects. Limit the candidate categories per partition split with `max_cat_threshold=16`; [XGBoost's parameter documentation](https://xgboost.readthedocs.io/en/latest/parameter.html) describes this as an overfit control for categorical features.
- Result `9d48eca`: 0.6778 (-0.0079), discarded. Richer airport partitions are essential; the route feature failure was about the much sparser joint category, not airports alone.

## Experiment 18 — follow-up

- Hypothesis: slower boosting at `learning_rate=0.05` with 300 rounds provides roughly the same total step size as 150 rounds at 0.1, but can learn smoother corrections and better generalize. [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) suggest reducing eta while increasing rounds.
- Result `ab3a784`: 0.6854 (-0.0003), discarded. Equivalent total boosting with smaller steps is slightly worse here.

## Experiment 19 — exploration

- Hypothesis: stronger L2 regularization on leaf weights may reduce overconfident corrections from 2005-specific signals without limiting category partitions. Test `reg_lambda=10` versus default 1. [XGBoost boosted-tree model documentation](https://xgboost.readthedocs.io/en/latest/tutorials/model.html) shows the leaf-weight penalty in its objective.
- Result `2ab779d`: 0.6850 (-0.0007), discarded. Stronger L2 does not help this model.

## Experiment 20 — exploration

- Hypothesis: a coarse joint weekday/time-block category will expose recurring weekly schedule interactions to shallow trees. Use 3-hour blocks, giving at most 56 combinations, far fewer than the route feature's 4,290. [Scikit-learn's time-feature study](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) highlights the importance of interactions between hour and working day.
- Result `f2f66d7`: 0.6862 (+0.0005), kept. Coarse weekday/time interactions help, unlike hour alone.

## Synthesis after 20 experiments

- Best: `f2f66d7`, 0.6862. Ordered calendar, day-of-year, shallow depth-3 trees, 150 rounds, and weekday/time-block interaction help.
- Sparse route categories and overly restrictive airport categorical splits hurt substantially. Hour by itself, cyclic year terms, strong L2, row subsampling, and slower boosting did not improve AUC.
- Current theory: transferable seasonality and low-cardinality schedule interactions help, whereas 2005-specific granular route effects do not. Next test the granularity of the successful weekday/time interaction, then try model growth and train-fitted schedule summaries.
- New research: [CatBoost's paper](https://papers.nips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf) warns that naive target-rate features can leak labels, so I will prefer unsupervised lookups. [XGBoost parameters](https://xgboost.readthedocs.io/en/latest/parameter.html) describe the alternative `lossguide` growth policy and leaf limits.

## Experiment 21 — follow-up

- Hypothesis: 2-hour rather than 3-hour blocks may distinguish early and late evening weekday risk while still keeping only about 84 joint categories. This tests resolution of the proven interaction, with all other settings fixed.
- Result `3f8f74d`: 0.6862 (equal), discarded; same code complexity and slightly slower evaluation.

## Experiment 22 — follow-up

- Hypothesis: 4-hour blocks may reduce variance in the weekday/time interaction by pooling more flights per group. The narrower 2-hour version did not improve the result, so test the other side of the granularity tradeoff before leaving this feature family.
- Result `607b367`: 0.6857 (-0.0005), discarded. Three-hour blocks remain the best resolution.

## Experiment 23 — exploration

- Hypothesis: an airport's typical departure time provides schedule context. A flight scheduled later than its origin's median may face a different delay regime from an equally timed flight at an airport with a later operating day. Fit median departure minute on train by origin, then map it per row. This is an unsupervised lookup that keeps train and eval semantics identical. [Airport situational-awareness research](https://arxiv.org/abs/1911.01605) motivates airport-level context; [XGBoost's data consistency guide](https://xgboost.readthedocs.io/en/release_3.0.0/python/examples/cat_pipeline.html) emphasizes using training-fitted transforms at inference.
- Result `e8f3876`: 0.6860 (-0.0002), discarded. Origin schedule context is close but does not improve the best; eval slowed to 39.1s.

## Experiment 24 — exploration

- Hypothesis: loss-guided growth with eight leaves allocates splits to the strongest effects instead of growing all depth levels uniformly. This can represent an uneven schedule effect while retaining roughly the best model's eight-leaf size. Set `grow_policy=lossguide`, `max_leaves=8`, and `max_depth=0` with `hist`. [XGBoost parameters](https://xgboost.readthedocs.io/en/latest/parameter.html) define these controls.
- Result `f7904b4`: 0.6859 (-0.0003), discarded. Alternative growth is close but not better.

## Experiment 25 — exploration

- Hypothesis: averaging the best depth-3 model with a depth-4 model may smooth idiosyncratic tree splits while retaining useful complementary interactions. Train both on the same features and average probabilities with 70% weight on the current best. [Scikit-learn's soft-voting documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) explains probability averaging; a custom wrapper preserves pandas categorical inputs for XGBoost.
- Result `41cc6b7`: 0.6864 (+0.0002), kept. Averaging offers a small gain at modest training cost.

## Experiment 26 — follow-up

- Hypothesis: the depth-4 component may contribute more complementary structure than the current 30% weight allows. Test equal probability weights while holding both fitted models fixed. This isolates blend balance rather than changing either model.
- Result `3407ccd`: 0.6864 (equal), discarded. The same two models and complexity gave no meaningful speed difference.

## Experiment 27 — ablation/simplification

- Hypothesis: with the newer calendar and weekday/time features, depth 4 alone may match the ensemble. Test the depth-4, 100-round component as a single model; equal AUC would simplify the final artifact and reduce training work.
- Result `1523996`: 0.6852 (-0.0012), discarded. The blend's gain comes from retaining the stronger depth-3 component.

## Experiment 28 — exploration

- Hypothesis: carrier operations differ across weekdays; a 140-level carrier/weekday category can expose this interaction to shallow trees without the sparsity of route categories. [CatBoost's categorical-feature paper](https://papers.nips.cc/paper_files/paper/2018/file/14491b756b3a51daac41c24863285549-Paper.pdf) motivates moderate-cardinality category combinations.
- Result `0465c6e`: 0.6844 (-0.0020), discarded. The successful interaction is specific to weekday and time; carrier/weekday appears noisy. Eval slowed to 40s.

## Experiment 29 — exploration

- Hypothesis: numeric month and day-of-year represent ordered seasons, but a categorical copy of month can group nonadjacent high-delay months such as January, July, and December in one split. Test the additional 12-level categorical month while retaining the ordered version.
- Result `e634807`: 0.6864 (equal), discarded. It added scoring time and code without AUC gain.

## Experiment 30 — exploration

- Hypothesis: scheduled departure time has 1,162 observed values, but histogram trees use 256 bins by default. Raising `max_bin` to 512 may yield more precise useful thresholds for the dominant time feature. [XGBoost parameter reference](https://xgboost.readthedocs.io/en/release_3.2.0/parameter.html) describes the accuracy/computation tradeoff.
- Result `fd45163`: 0.6863 (-0.0001), discarded. More precise histogram thresholds did not improve transfer.

## Synthesis after 30 experiments

- Best: `41cc6b7`, 0.6864. The 70/30 depth-3/depth-4 ensemble adds a small gain to the strongest engineered feature set.
- The useful feature additions remain ordered calendar, day-of-year, and a coarse weekday/time-block category. Carrier/weekday, route, hour alone, and a categorical month copy were neutral or harmful.
- Fine histogram bins and altered ensemble balance were close but did not improve. The current theory favors broad, repeatable schedules and modest model diversity over more granular fits.
- New research: [XGBoost parameters](https://xgboost.readthedocs.io/en/release_3.2.0/r_docs/R-package/docs/reference/xgb.params.html) identify `gamma` as a way to suppress low-gain splits; [scikit-learn's feature-importance discussion](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html) cautions that correlated features can have misleading individual importances. I will test direct ablation rather than infer usefulness from gain alone.

## Experiment 31 — ablation/simplification

- Hypothesis: distance has the lowest gain among original features and overlaps with origin/destination. Removing it may reduce overfit and speed preparation. Equal AUC would be a valid simplification.
- Result `acea629`: 0.6856 (-0.0008), discarded. Distance contributes useful information even alongside airport codes.

## Experiment 32 — exploration

- Hypothesis: suppressing low-gain splits with `gamma=1` may prune weak 2005-specific interactions in both ensemble members while retaining dominant schedule and airport effects. [XGBoost parameters](https://xgboost.readthedocs.io/en/release_3.2.0/r_docs/R-package/docs/reference/xgb.params.html) define gamma as the minimum loss reduction for a split.
- Result `b21afd8`: 0.6864 (equal), discarded because training and total run time increased.

## Experiment 33 — ablation/simplification

- Hypothesis: numeric month and day-of-year are correlated seasonal indicators. Removing month as a predictor while retaining it locally to compute day-of-year may reduce redundant splits and improve transfer. This is a direct ablation prompted by the [scikit-learn note](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html) that correlated features can obscure individual importance.
- Result `fa052d9`: 0.6865 (+0.0001), kept. Removing the redundant month feature slightly improved AUC and sped evaluation.

## Final summary

- Best Eval AUC: **0.6865** at commit `fa052d9` (baseline `8d9c760`: 0.6743). The branch ends at the best kept commit.
- Helpful changes: ordered day-of-month, day-of-year, three-hour weekday/time category, shallower depth-3 trees at 150 rounds, and a 70/30 probability blend with a depth-4 100-round model. Dropping redundant numeric month added a final small gain.
- Changes that did not help: high-cardinality route and carrier/weekday categories, extra hour category, cyclic year terms, stronger categorical restrictions, bigger histograms, altered ensemble weights, and most regularization changes. Distance remained useful on ablation.
- Next ideas: test whether the weekday/time interaction can be represented more simply, and test whether more diverse yet individually stable model components improve the ensemble. Validate the final artifact on the human-only holdout after this run; that score was never inspected during research.
