# Research log — oct6

## Baseline — 8d9c760

Untouched `train.py`: 100 trees, depth 6, learning rate 0.1, native categorical splits. Eval AUC 0.6743; 1.4 s training and 30.2 s evaluation. Data: 200,000 balanced training rows, no missing values. `CRSDepTime` is HHMM format; month, day and weekday arrive as `c-N` strings.

## Experiment 1 — smaller steps, more boosting rounds (follow-up)

Hypothesis: the baseline's 100 rounds may stop before useful carrier, airport and time interactions are learned. Use 300 trees at learning rate 0.05; hold other choices fixed. XGBoost's [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends reducing the learning rate while increasing the number of rounds to control fit complexity. The [categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) confirms that the current pandas categories and native categorical model are supported. Eval AUC 0.6743, equal to baseline but training increased to 2.4 s and artifact to 7.5 MB; discard.

## Experiment 2 — departure hour as a category (exploration)

Hypothesis: hour of day has non-monotonic effects that a single numerical HHMM feature learns inefficiently. Add the scheduled hour as a 24-level category. The [UC Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) reports different delay patterns by departure hour and carrier; this dataset has the scheduled time needed to test that idea without using post-departure information. Eval AUC 0.6747, +0.0004; keep.

## Experiment 3 — carrier by departure hour (follow-up)

Hypothesis: carriers have different schedule and delay propagation patterns across the day. A joint carrier-hour category gives XGBoost direct access to this interaction while keeping the feature derived only from scheduled information. The same [UC Berkeley analysis](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) describes carrier-specific hour patterns. Levels are fixed using training data and reused for single-row evaluation. Eval AUC 0.6721, a substantial drop; discard. This interaction likely fragments the training signal too much.

## Experiment 4 — shallower trees (exploration)

Hypothesis: depth-6 trees overfit the 2005 sample, especially with hundreds of airport levels, then transfer poorly to 2006. Try depth 4 with the kept hour feature. XGBoost's [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) names max depth as a direct complexity control. Eval AUC 0.6789, +0.0042; keep. Artifact shrank from 2.6 MB to 0.7 MB.

## Experiment 5 — depth three (follow-up)

Hypothesis: the large gain from depth 4 suggests complexity was limiting transfer across years. Test another step down to depth 3 at the same 100 rounds and learning rate, to find whether the trend continues or bias starts to dominate. Eval AUC 0.6797, +0.0008; keep.

## Experiment 6 — depth two (follow-up)

Hypothesis: with 2005-to-2006 shift, still simpler trees may transfer better. Test depth 2 while holding the hour feature and all other parameters fixed. Eval AUC 0.6754, -0.0043; discard. Depth 3 is the best of tested depths 2, 3, 4 and 6.

## Experiment 7 — more shallow boosting rounds (follow-up)

Hypothesis: depth-3 trees have less capacity per round and may gain from a longer, slower boosting path. Use 300 rounds at learning rate 0.05. This revisits Experiment 1 only after finding that lower tree depth materially improves cross-year AUC. Eval AUC 0.6796, -0.0001 and slower; discard. More rounds have not improved at either depth tested.

## Experiment 8 — larger minimum leaf weight (exploration)

Hypothesis: some airport categories have too few training examples for reliable splits. Set `min_child_weight=10` so the model rejects fragile leaves even with depth 3. XGBoost's [parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger values make partitioning more conservative. Eval AUC 0.6797, unchanged; discard because the extra parameter brings no simplification or speed gain.

## Experiment 9 — sample 80% of rows per tree (exploration)

Hypothesis: sampling rows on each boosting round will reduce sensitivity to noisy airport and date combinations in 2005. Set `subsample=0.8` at the kept depth-3 configuration. XGBoost's [parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies row subsampling as a way to control overfitting. Eval AUC 0.6784, -0.0013; discard. The smaller sample seems to lose useful signal.

## Experiment 10 — day of year (exploration)

Hypothesis: month and day categories make it hard for shallow trees to learn contiguous seasonal changes and holiday neighborhoods. Add a numeric day-of-year derived from each row's scheduled month and day. The [Stanford airline departure delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) uses day of year and holiday proximity among its advance-known predictors. The lookup is fixed and means the same for whole-frame training and single-row scoring. Eval AUC 0.6832, +0.0035; keep.

## Synthesis after 10 experiments

Best Eval AUC is 0.6832 at 2f1be6a, up from 0.6743 baseline. The largest gains came from shallower depth (6 → 4 → 3) and a numeric day-of-year feature. A categorical departure hour added a small gain. Depth 2 underfit. A carrier-hour cross feature overfit or fragmented the signal. More boosting rounds, higher minimum child weight, and row subsampling did not help the tested configurations. Current theory: compact trees that receive explicit calendar structure transfer better from 2005 to 2006 than a more flexible fit to sparse combinations. Next explore route information and, if needed, carefully cross-fitted encodings. Research: the [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partition splits for high-cardinality categories; [scikit-learn's target encoding example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) shows why target-derived encodings need cross-fitting. Both suggest ways to represent route effects without leaking a row's label.

## Experiment 11 — route category (exploration)

Hypothesis: some origin-destination pairs have different operational risk than the separate airports imply. Add their joint route as a native categorical feature, with levels fixed from training. This follows the route-specific patterns discussed in [flight-delay research](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12183) and XGBoost's [categorical partitioning guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). There are 4,290 training routes, median 32 sampled rows each, so overfitting is a real risk. Eval AUC 0.6759, -0.0073; discard. Training was still quick but row-wise evaluation rose to 50 s.

## Experiment 12 — cross-fitted smoothed route risk (exploration)

Hypothesis: a smoothed route-level delay signal captures useful structure without the thousands of raw categorical split candidates. Fit five lookup tables on `train`, each excluding one day-of-month fold. Every row selects its fold's lookup, so its own target never contributes to its feature and `prepare(row)` is identical to the same row within `prepare(train)`. Smooth each estimate with 50 balanced prior observations to limit sparse-route noise. [scikit-learn's target encoding example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) specifically uses cross-fitting to prevent overfitting when a target mean is used as a feature. Eval AUC 0.6825, -0.0007 and evaluation rose to 64 s; discard.

## Experiment 13 — ordered weekday (exploration)

Hypothesis: a numeric weekday lets depth-3 trees find weekday-versus-weekend and adjacent-day effects with fewer splits than the existing categorical weekday. Add a numeric representation while retaining the category. This follows the temporal features used in [flight-delay research](https://www.mdpi.com/2079-9292/13/24/4910). Eval AUC 0.6832, equal to best but slower; discard.

## Experiment 14 — fixed-holiday window (exploration)

Hypothesis: travel and operational conditions change immediately around New Year, Independence Day and Christmas in both years. Add a binary window for three days on either side of those fixed dates, including the year-end wrap. [Stanford's departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) includes holiday proximity as an advance-known predictor. Eval AUC 0.6832, unchanged and slower; discard.

## Plateau research after Experiments 12–14

Three discards moved AUC by less than 0.001. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) emphasizes understanding the data and feature selection, while the [scikit-learn gradient boosting guide](https://scikit-learn.org/stable/modules/ensemble.html) recommends native categoricals for nominal values. Our day-of-month appears twice: as a nominal category and within ordered day of year. I will test whether dropping the standalone category removes noise, then explore XGBoost's alternative tree growth and categorical-split controls if needed.

## Experiment 15 — remove day-of-month category (ablation)

Hypothesis: the standalone day-of-month category encourages 2005-specific date splits. Numeric day of year already preserves day information with useful seasonal order; removing the category may improve transfer or at least simplify single-row preparation. Eval AUC 0.6842, +0.0010; keep. This supports the redundant-date-noise hypothesis.

## Experiment 16 — remove month category (ablation)

Hypothesis: day of year also contains month information, so removing the standalone month category may simplify the model further and prevent arbitrary 2005-specific month groupings. Unlike day-of-month, however, month may encode climate seasons more cleanly, so this is a direct test of whether the ordered feature can replace it. Eval AUC 0.6850, +0.0008 and faster evaluation; keep.

## Experiment 17 — remove departure-hour category (ablation)

Hypothesis: now that the model is shallow and date categories are gone, the explicit hour feature may duplicate the scheduled HHMM value. Remove it to check whether the earlier small gain still survives in this configuration. Eval AUC 0.6843, -0.0007 despite faster evaluation; discard under the keep rule.

Inspection of the saved 8d16e61 model's average split gain ranks `CRSDepTime` highest (1688), followed by `DepHour` (448), `DayOfYear` (211), carrier (191), origin (162), weekday (158), destination (121) and distance (56). This suggests departure time is the strongest place to look for additional compact structure.

## Experiment 18 — minute within hour (exploration)

Hypothesis: scheduled flights cluster at certain minute marks within every hour, and a shallow tree cannot share this pattern across hours using raw HHMM alone. Add `CRSDepTime % 100` as an ordered numeric feature while retaining hour and HHMM. The [UC Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies scheduled time and time of day as operational signals. Eval AUC 0.6850, unchanged. Runtime happened to be lower, but the added feature itself does not offer a credible speed improvement; discard under the simplicity rule.

## Experiment 19 — one-hot splits for small categories (exploration)

Hypothesis: partition-based categorical splits may group several weekday, carrier and departure-hour levels according to noisy 2005 gradients. Set `max_cat_to_onehot=32` so those categories use one-hot splits while the 283-level airport categories still use partitions. The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains the split choice and parameter. Eval AUC 0.6818, -0.0032; discard. Partitioning appears better for these categories.

## Experiment 20 — smaller categorical partition search (exploration)

Hypothesis: airport categories are numerous and XGBoost may find training-specific category partitions. Set `max_cat_threshold=16` to reduce how many categories are considered at each partition split; retain partitioning of small categories after Experiment 19. XGBoost's [parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes this control as a way to prevent overfitting categorical splits. Eval AUC 0.6758, -0.0092; discard. This substantially impairs category handling.

## Synthesis after 20 experiments

Best Eval AUC is 0.6850 at 8d16e61. Removing day-of-month and month categories after introducing numeric day of year brought the second block's clearest gains. The remaining categorical hour is useful: ablating it lowered AUC. Route categories, smoothed route risk, fixed-holiday window, numeric weekday and minute of hour did not improve. For categorical handling, broad one-hot splits and a smaller partition search both hurt. A compact depth-3 tree with native categorical partitions and a single ordered seasonal date feature remains the strongest theory. New research: [scikit-learn's cyclical feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) suggests sine and cosine transforms to connect Dec 31 to Jan 1; [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes leaf regularization and alternative tree growth. I will test calendar periodicity, then model structure and ensembling.

## Experiment 21 — cyclical annual date (exploration)

Hypothesis: numeric day of year creates an artificial gap between late December and early January. Add sine and cosine of annual position so a depth-3 tree can group the year-end winter period with one or two splits. Retain numeric day of year for ordered seasonal breaks. The [scikit-learn time-feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) describes this exact periodic encoding. Eval AUC 0.6837, -0.0013; discard. The flexible periodic representation appears to add noise.

## Experiment 22 — fewer boosting rounds (exploration)

Hypothesis: the reduced feature set may still slightly overfit with 100 depth-3 rounds. Test 60 rounds at the same learning rate, which also lowers training and artifact cost. This is a direct early-stopping style test without an extra validation metric, consistent with the [XGBoost tuning guide's](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) advice to balance tree complexity and boosting steps. Eval AUC 0.6838, -0.0012; discard. The 60-round model appears underfit.

## Experiment 23 — 150 boosting rounds (follow-up)

Hypothesis: 60 rounds underfit; the current 100 rounds may also end before learning weaker time, carrier and airport effects. Test 150 rounds at the same learning rate to bracket the boosting optimum around the current feature set. Eval AUC 0.6846, -0.0004; discard. The 100-round setting remains best in this neighborhood.

## Experiment 24 — stronger L2 leaf regularization (exploration)

Hypothesis: with only 100 rounds and depth 3, shrinking leaf weights may control noisy airport and time interactions without removing useful splits. Raise `reg_lambda` from the default 1 to 10. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as L2 regularization of leaf weights. Eval AUC 0.6844, -0.0006; discard.

## Experiment 25 — depth four after calendar ablations (follow-up)

Hypothesis: the earlier depth-4 model (Experiment 4) had noisy month and day-of-month categories. With those removed, depth 4 may now exploit richer time-airport interactions without overfitting. Test 100 depth-4 rounds on the current feature set. This is a new configuration, directly motivated by the successful ablations. Eval AUC 0.6840, -0.0010; discard. Depth 3 still wins, but depth 4 remains close enough to consider blending.

## Experiment 26 — average depth-3 and depth-4 predictions (exploration)

Hypothesis: depth 3 and 4 capture partially different departure-time, airport and calendar effects. Average their predicted probabilities so each model's idiosyncratic errors may cancel. Both models fit only `train.csv` under the same preparation. The [scikit-learn ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) describes soft voting as useful for comparably performing models that have different weaknesses. Eval AUC 0.6853, +0.0003; keep.

## Experiment 27 — favor depth three in blend (follow-up)

Hypothesis: depth 3 performs 0.001 better than depth 4 alone, so equal averaging may give too much weight to the weaker component. Try a 2:1 probability blend favoring depth 3 while retaining depth 4's complementary signal. Eval AUC 0.6854, +0.0001; keep.

## Experiment 28 — stronger depth-three weight (follow-up)

Hypothesis: moving from 1:1 to 2:1 improved AUC, so a 3:1 blend may further reduce noise from the weaker depth-4 model while keeping some complementary signal. This brackets the blend between the current 2:1 result and the depth-3 standalone score. Eval AUC 0.6854, unchanged, with no simplification or speed gain; discard. The 2:1 blend remains the simpler tested winner.

## Experiment 29 — split penalty in both models (exploration)

Hypothesis: the ensemble retains noisy low-gain splits, especially in its depth-4 component. Set `gamma=1` in both models, requiring a minimum training-loss improvement before any split. The [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes gamma as a direct split penalty. Eval AUC 0.6854, unchanged; discard because it adds a parameter without simplifying or speeding the code.

## Experiment 30 — loss-guided second model (exploration)

Hypothesis: the equal-depth split policy spends nodes across branches even when most improvement is concentrated in a few time-airport pockets. Replace the depth-4 component of the 2:1 blend with an eight-leaf loss-guided tree model; keep the stronger depth-3 component. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says loss-guided growth selects the node with the highest loss reduction. Eval AUC 0.6853, -0.0001; discard.

## Synthesis after 30 experiments

Best Eval AUC is 0.6854 at 52040bb. Blending depth-3 and depth-4 trees added a small gain beyond either standalone model; weighting depth 3 twice was slightly better than equal weighting. More weight, a split penalty, and replacing the depth-4 component with eight-leaf loss-guided trees did not improve it. Earlier calendar simplifications remain the largest source of improvement. Research now points to two unexplored directions: the [XGBoost histogram bin parameter](https://xgboost.readthedocs.io/en/stable/parameter.html) may permit better thresholds for scheduled departure time, which had the largest split gain, and an ablation of weak distance could simplify the input. I will test those before further complexity.

## Experiment 31 — more histogram bins (exploration)

Hypothesis: scheduled departure time has 1,162 distinct values and dominates model split gain, but the default histogram allows only 256 bins per numeric feature. Set `max_bin=512` for both blend components so they can consider finer departure-time thresholds. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) says more bins can improve split optimality at the cost of training time. Eval AUC 0.6847, -0.0007; discard. The extra split resolution likely fits training noise.

## Experiment 32 — remove distance (ablation)

Hypothesis: the origin and destination categories may already convey the route distance, while raw distance had the lowest average split gain in the inspected model. Remove it to see whether the feature adds unique predictive information or only noise and row-wise preparation cost. Eval AUC 0.6845, -0.0009; discard. Even a weak feature contributes useful information.

## Plateau research after Experiments 30–32

Three consecutive discards each moved AUC by less than 0.001. The [XGBoost monotonic constraint guide](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) offers a way to encode a strong prior in one model rather than changing the input features. The [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) offers dropout across trees as a different regularizer. Research on [US delay propagation](https://arxiv.org/abs/1304.2528) emphasizes hour-by-hour evolution of accumulated delays. I will first constrain scheduled time in the depth-4 blend component, leaving the stronger depth-3 model free to handle exceptions.

## Experiment 33 — increasing departure-time constraint in secondary model (exploration)

Hypothesis: the secondary model's local time reversals mostly fit 2005 noise; an increasing constraint on scheduled departure time could improve 2006 transfer while the unconstrained depth-3 component captures exceptions. Apply `monotone_constraints={"CRSDepTime": 1}` only to depth 4. Eval AUC 0.6847, -0.0007; discard. Time effects likely require non-monotonic behavior, or the categorical hour weakens the intended constraint.

## Experiment 34 — DART secondary model (exploration)

Hypothesis: tree dropout may prevent depth-4 boosting from making narrowly corrective trees that fit 2005 noise. Replace only the secondary component with a DART model, using 5% tree dropout and skipping dropout half the rounds; retain the dominant depth-3 model. The [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes this regularization mechanism. Eval AUC 0.6856, +0.0002; keep. Training rose to 5.4 s but remains far below the 60 s limit.

## Experiment 35 — stronger DART dropout (follow-up)

Hypothesis: 5% dropout helped the secondary model, suggesting it still benefits from less reliance on earlier trees. Raise `rate_drop` to 10% while keeping `skip_drop=0.5` and all else fixed. Eval AUC 0.6855, -0.0001; discard. More dropout is not better here.

## Experiment 36 — DART in both blend components (follow-up)

Hypothesis: dropout's gain in the depth-4 component may extend to depth 3. Use the same 5% dropout and 50% skip probability for both, retaining the 2:1 blend and all features. This tests whether regularizing the stronger model adds a further gain or destroys its complementary unregularized signal. Eval AUC 0.6851, -0.0005; discard. The plain depth-3 component is useful.

## Experiment 37 — deeper DART secondary model (exploration)

Hypothesis: DART may regularize a depth-5 model enough to learn useful airport-time interactions that neither depth 3 nor 4 captures. Change only the secondary model from depth 4 to 5, retaining 5% tree dropout and the 2:1 blend. Eval AUC 0.6856, equal but larger (1.8 MB versus 1.1 MB) and slower; discard.

## Plateau research after Experiments 35–37

Three discards changed AUC by less than 0.001. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) suggests feature subsampling as a different form of randomness, and the [scikit-learn ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) explains that averaging models with distinct weaknesses can improve generalization. I will keep the best depth-3 model intact and introduce column sampling only to the secondary DART model. This tests diversity rather than further tuning dropout strength or tree depth.

## Experiment 38 — column sampling in DART component (exploration)

Hypothesis: sampling 80% of columns per tree in the secondary model may create more complementary predictions to the unchanged depth-3 model while reducing reliance on the dominant scheduled-time feature. Keep its DART parameters and blend weight fixed. Eval AUC 0.6855, -0.0001; discard.

## Experiment 39 — coarser histogram bins (exploration)

Hypothesis: increasing `max_bin` to 512 hurt (Experiment 31), perhaps because fine scheduled-time thresholds fit 2005 noise. Try 128 bins, half the default, in both components to encourage broader time regions while retaining all original features. Eval AUC 0.6855, -0.0001; discard. The default 256 bins remains best.

## Experiment 40 — four broad seasons (exploration)

Hypothesis: the numeric day-of-year feature makes December and January distant in feature space, but a four-level season feature can group winter across the year boundary without the extra flexibility of the failed sine/cosine features. This uses only known month and follows seasonal features in [flight-delay research](https://www.mdpi.com/2079-9292/13/24/4910). Eval AUC 0.6848, -0.0008 and slower; discard.

## Synthesis after 40 experiments

Best Eval AUC is 0.6856 at f781674, up from 0.6743 baseline. A 2:1 blend of depth-3 XGBoost and depth-4 DART gives a slight gain over the plain blend. Higher dropout, dropout in both components, depth 5, column sampling, alternate histogram bin counts, and a coarse seasonal feature did not improve. The strongest substantive insight remains that removing month and day-of-month categories after adding numeric day of year improves transfer from 2005 to 2006. New research: the [XGBoost DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) gives two tree-weight normalization schemes. The present secondary model uses the default `tree`; test `forest` as a different regularization form.

## Experiment 41 — forest-style DART normalization (exploration)

Hypothesis: forest normalization gives a dropped group of trees one shared weight and may reduce overcorrection in the secondary model. Change only its `normalize_type` from the default `tree` to `forest`, preserving 5% dropout and the 2:1 blend. Eval AUC 0.6858, +0.0002; keep.

## Experiment 42 — higher dropout with forest normalization (follow-up)

Hypothesis: unlike tree normalization, forest normalization may benefit from more dropout because it weights the dropped group collectively. Test 10% instead of 5% `rate_drop` in the secondary model while retaining forest normalization and the 2:1 blend. Eval AUC 0.6857, -0.0001; discard.

## Final summary

Best Eval AUC: **0.6858** at commit **b27ca12**, versus **0.6743** at baseline 8d9c760 (+0.0115). The best model uses numeric day of year instead of month and day-of-month categories, retains categorical departure hour, and blends depth-3 XGBoost with a depth-4 DART model at a 2:1 probability weight. The DART model uses 5% tree dropout, 50% dropout skips and forest normalization.

What worked: shallower trees, ordered seasonal date, removing redundant date categories, and a modest blend with a differently regularized secondary model. What did not: raw route categories, cross-fitted route risk, extra temporal features, one-hot categorical splits, constrained categorical partitions, altered histogram bins, monotone time constraint, dropping distance or hour, and stronger DART dropout. Several adjustments tied AUC but added complexity and were discarded.

Next: test whether a simpler model can match the ensemble on a truly independent holdout. If continuing experiments, investigate robust geographic airport metadata available at schedule time and alternative DART sampling or normalization only after measuring generalization. No holdout data or human-only tools were used during this run.
