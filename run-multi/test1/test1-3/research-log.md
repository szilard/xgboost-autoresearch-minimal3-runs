# Experiment log — oct4

## Baseline — b15ec66

The untouched starter scored 0.6743 Eval AUC (0.7 s model fit, 30.6 s row-by-row evaluation). Training data has 200,000 balanced flights, no missing fields, 20 carriers, and 283 origin and destination airports. The raw scheduled departure time is HHMM.

## Research before experiment 1

- [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html): learning rate shrinks tree updates, depth controls interaction complexity, and minimum child weight plus row subsampling can make trees more conservative. The current 100 depth-6 trees may use capacity inefficiently, so test a smaller learning rate with more trees first.
- [XGBoost categorical data documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): categorical partitioning is supported by the histogram method used here. Keep the baseline's native categorical handling while isolating model-capacity changes.
- [Flight-delay literature review](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057): scheduled departure time, date, carrier, and airports are standard predeparture signals. Its discussion supports later tests of an explicit time-of-day representation and route interactions, using only available columns.

Only `data/train.csv` was inspected for these observations. Evaluation remains exclusively through the harness.

## Experiment 1 — gradual boosting (follow-up)

Hypothesis: 100 trees may stop before the useful signal is learned. Use 300 trees with learning rate 0.05 while retaining depth 6 and all original features. This follows the XGBoost parameter guide cited above. Watch for either a gain from reduced update size or a loss from overfitting the 2005 sample.

Result: 0.6743, exactly equal to baseline at printed precision, with slower fit (1.7 s versus 0.7 s). Discard under the keep rule. Extra boosting at depth 6 yielded no useful generalization gain.

## Experiment 2 — shallower trees (ablation)

Hypothesis: depth 6 may overfit interactions specific to 2005, consistent with XGBoost's [depth guidance](https://xgboost.readthedocs.io/en/stable/parameter.html). Reduce only `max_depth` to 4, retaining 100 trees and learning rate 0.1.

Result: 0.6789 (+0.0046), with faster fit. Keep. The shift across years favors simpler trees; the previous extra-tree trial at depth 6 likely spent capacity on interactions that did not transfer.

## Experiment 3 — gradual boosting at depth 4 (follow-up)

Hypothesis: shallower trees can use more boosting rounds without overfitting as quickly. Test 250 trees at learning rate 0.05, with depth 4 fixed. Compared with experiment 1, tree depth is the key changed condition. Based on the same [XGBoost shrinkage guidance](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 0.6798 (+0.0009). Keep. Gradual boosting adds a small gain once individual trees are shallower.

## Experiment 4 — categorical departure hour (exploration)

Hypothesis: flight delay grows with time of day but bends down at the late-night edge (seen in train-only hourly rates). A categorical hour lets XGBoost group nonadjacent hours in one partition, potentially reducing the number of splits needed. This is motivated by [Li et al.'s flight-delay literature review](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057), which describes scheduled hour as a commonly used categorical predictor. Hour is computed independently from each row's HHMM time.

Result: 0.6795 (-0.0003), with slower row-by-row preparation. Discard. Raw HHMM already seems sufficient for hour effects; a new category may add a little noise.

## Experiment 5 — origin–destination route (exploration)

Hypothesis: with depth 4, a single categorical route feature can express route-specific delay risk more efficiently than splitting separately on origin and destination. The train set has 4,290 observed routes (median 32 rows per route), so there is repeat data for many routes, though sparse routes can overfit. Motivated by the use of origin–destination pairs in [flight-delay research summarized by Li et al.](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12057) and XGBoost's [categorical partitioning](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). Levels are fitted only on train and applied row by row.

Result: 0.6709 (-0.0089), slower evaluation. Discard. The route category appears too granular or unstable from 2005 to 2006 for this model. Favor broader structure or stronger regularization.

## Experiment 6 — stronger minimum leaf weight (follow-up)

Hypothesis: shallow trees help cross-year transfer, while splits on rare airport patterns may still be fragile. Raise `min_child_weight` from 1 to 10 as described in the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html), changing no feature or other parameter.

Result: 0.6794 (-0.0004). Discard. Stronger minimum leaf weight slightly underfits or removes useful local effects; it does not rescue the broad idea of route categories.

## Experiment 7 — row subsampling (follow-up)

Hypothesis: depth reduction helped and the added route overfit, so stochastic row sampling may improve year-to-year stability while retaining all feature types. Set only `subsample=0.8`, as described in the [XGBoost parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: 0.6797 (-0.0001). Discard. This form of randomness does not materially help on this data.

## Experiment 8 — day of year (exploration)

Hypothesis: month and day-of-month as separate categories require interaction splits for a contiguous seasonal period. A numeric day-of-year gives such periods a simple threshold, and seasonal delay risk is noted in [flight-delay research](https://onlinelibrary.wiley.com/doi/full/10.1155/2024/3385463). Compute it from each row's existing date fields using non-leap month lengths (both years are non-leap), while retaining original fields.

Result: 0.6832 (+0.0034). Keep. Continuous seasonal position is useful beyond independent month and day categories.

## Experiment 9 — remove day-of-month category (ablation)

Hypothesis: once `DayOfYear` expresses the calendar position, the standalone day-of-month category may mainly add noisy, repeat-by-month effects. Remove it from predictors while still using it to compute day-of-year. This is a direct simplification of experiment 8.

Result: 0.6834 (+0.0002), also slightly faster. Keep. Day-of-year captures useful date information with less noise than a separate day-of-month category.

## Experiment 10 — remove month category (ablation)

Hypothesis: `DayOfYear` may already encode the broad seasonal month effect. Remove Month as a separate categorical predictor, while retaining its use in computing `DayOfYear`, to test whether the simpler representation transfers better to 2006.

Result: 0.6846 (+0.0012), with faster evaluation. Keep. A single ordered calendar position transfers better than separate month and day categories here.

## Synthesis after 10 experiments

Best so far: 0.6846 at b42f7a5, +0.0103 over baseline. Shallower depth-4 trees and a slower 250-round schedule helped. An ordered day-of-year feature gave a larger gain, and removing redundant month/day categories improved it further. Categorical departure hour, high-cardinality route, stronger minimum leaf weight, and row subsampling did not improve. The best theory is that stable, low-dimensional temporal structure matters more than fine-grained 2005-specific category patterns. Next test simpler tree capacity and alternative calendar/weekday representations, then revisit categorical handling if needed.

## Research before experiment 11

- [XGBoost parameter-tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) emphasize balancing model complexity against overfitting, especially with `max_depth`, and that preprocessing can matter more than extensive parameter tuning. This supports a depth-3 test now that seasonal position is simpler.
- [Flight-delay feature-engineering study](https://onlinelibrary.wiley.com/doi/full/10.1155/2024/3385463) uses day of year and explicit holiday indicators. A calendar-event feature is a later candidate because it could transfer recurring travel patterns from 2005 to 2006 using known dates. We cannot use its flight-count or historical-delay features under this experiment's rules.
- [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partition splits and the one-hot threshold; trying one-hot handling for the remaining low-cardinality weekday may be worthwhile if depth changes plateau.

## Experiment 11 — depth 3 with ordered calendar (follow-up)

Hypothesis: with the compact day-of-year representation, depth-3 trees may preserve useful broad effects while reducing year-specific interactions. Reduce only `max_depth` from 4 to 3, guided by XGBoost's tuning notes above.

Result: 0.6849 (+0.0003), faster. Keep. Further simplification of tree interactions helps slightly.

## Experiment 12 — depth 2 (follow-up)

Hypothesis: the positive depth trend from 6 to 4 to 3 may continue. Reduce only `max_depth` to 2, still allowing pairwise interactions, and compare with 0.6849. This follows the [XGBoost complexity guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).

Result: 0.6823 (-0.0026). Discard. Pairwise interactions are insufficient; depth 3 appears to balance capacity and transfer better.

## Experiment 13 — twice-yearly seasonal harmonic (exploration)

Hypothesis: train-only month summaries show elevated delay rates near January/July/December and lower rates around April/May and September/October. One cosine feature with two cycles per year can group these periods and bridge the December–January boundary. [Scikit-learn's cyclical-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains sine/cosine encodings and notes that higher harmonics can represent more complex periodicity; test the second cosine harmonic here while retaining `DayOfYear`.

Result: 0.6838 (-0.0011), slower evaluation. Discard. The extra periodic split signal is redundant or too coarse for the actual seasonal pattern; ordered day-of-year is stronger here.

## Experiment 14 — narrower categorical partitions (exploration)

Hypothesis: origin and destination each have 283 levels, and large categorical partitions may learn year-specific airport combinations. [XGBoost docs](https://xgboost.readthedocs.io/en/stable/parameter.html) say `max_cat_threshold` limits categories considered at each partition split to prevent overfitting. Reduce it from the default 64 to 32 while keeping depth 3 and existing features.

Result: 0.6833 (-0.0016). Discard. Restricting category candidates loses useful carrier/airport splits; test the opposite direction next to determine whether the default cap is binding.

## Experiment 15 — broader categorical partitions (follow-up)

Hypothesis: the loss at threshold 32 suggests useful categories were excluded from split search. Increase `max_cat_threshold` to 128 (from default 64), keeping everything else fixed. [XGBoost's categorical parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe this limit.

Result: 0.6843 (-0.0006). Discard. The default 64 sits between two worse settings; leave categorical split threshold alone.

## Experiment 16 — longer depth-3 boosting (follow-up)

Hypothesis: depth 3 is the best tested complexity, but 250 rounds may still stop early because the trees are small. Increase only `n_estimators` to 500 at learning rate 0.05; [XGBoost's tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe more rounds with small update size.

Result: 0.6839 (-0.0010), with longer fit. Discard. More rounds overfit or add unhelpful fine effects; test fewer rounds to bracket the useful range.

## Experiment 17 — shorter depth-3 boosting (follow-up)

Hypothesis: 500 rounds hurt relative to 250, so the optimal boosting length may be below 250. Test 150 rounds at learning rate 0.05, changing nothing else. The distinction from experiment 16 is an explicit search in the opposite direction around the 250-round best.

Result: 0.6842 (-0.0007), though faster. Discard under the keep rule. 250 rounds beat both 150 and 500, so further tiny changes in round count are unlikely to be productive now.

## Experiment 18 — average depth-3 and depth-4 models (exploration)

Hypothesis: the depth-3 and depth-4 models with the compact date representation scored 0.6849 and 0.6846. They may make partly different ranking errors; simple probability averaging can reduce variance. [Model-averaging research](https://jmlr.csail.mit.edu/papers/v23/20-874.html) provides a theoretical motivation, though its results are broad rather than specific to XGBoost. Fit both on train and average their predictions in one picklable model; no extra evaluation is introduced.

Result: 0.6855 (+0.0006), with both members fitted in 1.4 s. Keep. Complementary tree depths add a small ranking gain at low training cost.

## Experiment 19 — Thanksgiving week (exploration)

Hypothesis: an annual travel holiday moves by one calendar day between 2005 and 2006, while raw day-of-year anchors it to 2005. A flag for the week containing the fourth Thursday in November could transfer this recurring effect. The [flight-delay feature-engineering study](https://onlinelibrary.wiley.com/doi/full/10.1155/2024/3385463) includes holiday indicators, and the [U.S. Office of Personnel Management](https://www.opm.gov/frequently-asked-questions/pay-and-leave-faq/pay-administration/what-are-federal-holidays/?os=v) defines Thanksgiving as the fourth Thursday. Derive it from each row's month, day, and weekday; no lookup is fitted to labels or evaluation rows.

Result: 0.6855, exactly equal to the previous best but with more code and slower row preparation. Discard under the keep rule. This week-level holiday signal adds no ranking power at printed precision.

## Experiment 20 — favor depth 3 in ensemble (follow-up)

Hypothesis: the depth-3 member scored 0.6849 by itself, slightly above depth 4's 0.6846. The 50/50 average improved to 0.6855, showing complementary errors. A 70/30 depth-3/depth-4 probability average may retain complementarity while favoring the stronger member. The model-averaging rationale was researched for experiment 18.

Result: 0.6855, no gain at printed precision, and no meaningful speed or code simplification over equal weighting. Discard; equal weights remain easier to explain.

## Synthesis after 20 experiments

Best so far: 0.6855 at 95c61df, +0.0112 from baseline. Depth 3 is better than depths 2 and 4 in isolation with the compact date feature, but averaging depth 3 and 4 is better than either. Round count 250 outperformed 150 and 500; the default categorical split threshold 64 outperformed 32 and 128. A twice-yearly cosine and Thanksgiving-week flag added no value. The evidence points to broad temporal and airport/carrier signals, with moderate interaction capacity and averaging across tree structures. Next explore simple feature ablations, weekday/calendar effects, and a different model shape or encoding to diversify the ensemble.

## Research before experiment 21

- [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) emphasize understanding data and preprocessing. The retained model gives Distance only about 2.5% of split importance, making a feature ablation worthwhile.
- [XGBoost tree methods](https://xgboost.readthedocs.io/en/release_1.7.0/treemethod.html) contrasts histogram and approximate tree building and says both support categorical data. If feature ablations do not help, a different split-search method is a meaningful model-shape test.
- [XGBoost DART documentation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes tree dropout as another overfitting control, but warns that training can be slower. This is an option to test within the 60-second training limit.
- [Scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows that boosting trees handle ordinal temporal features well and that simpler smooth models can make different errors. A regularized linear model may be useful as a diverse ensemble member later.

## Experiment 21 — remove Distance (ablation)

Hypothesis: Distance contributes little to the retained ensemble and may be an unstable proxy for specific routes. Remove it while keeping airport and carrier identities; if AUC is equal or higher, this is also a simpler and faster `prepare`.

Result: 0.6847 (-0.0008). Discard. Distance's modest feature importance still represents useful information beyond the airport categories.

## Plateau research before experiment 22

Three consecutive discards moved the printed AUC by less than 0.001. [XGBoost's tree-method guide](https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html) says the histogram method sketches numeric split candidates once and that increasing `max_bin` can approach or exceed the accuracy of `approx` in some cases. This directly suggests testing resolution for the 1,162 unique departure times and 365 calendar positions. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) confirm the default is 256 and larger values trade computation for finer splits. [Scikit-learn's target-encoding guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) warns that category target means need cross-fitting to avoid leakage; because that complicates this row-wise setup and the program rules prohibit cross-validation, defer that avenue.

## Experiment 22 — finer histogram bins (exploration)

Hypothesis: 256 bins may merge scheduled departure times or day-of-year positions that have distinct delay rates. Increase `max_bin` to 512 for both ensemble members, leaving all else fixed, and monitor training time against the 60-second limit.

Result: 0.6851 (-0.0004), similar fit time. Discard. Finer histogram resolution does not improve year-to-year ranking; the default bin count remains best.

## Experiment 23 — approximate tree method (exploration)

Hypothesis: XGBoost's [`approx` method](https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html) uses a different sketch of numeric splits and supports categorical data. Try it for both ensemble members, retaining the default 256 bins and all other settings. Watch training time because it sketches more often than `hist`.

Result: 0.6853 (-0.0002), with fit time 9.0 s versus 1.4 s for `hist`. Discard as a standalone replacement. Since its AUC remains close to the best and split choices differ, test it as a diverse addition to the current ensemble.

## Experiment 24 — mix histogram and approximate ensembles (follow-up)

Hypothesis: although `approx` alone scored 0.0002 below `hist`, its different split search may yield complementary errors. Average the two retained histogram depth-3/4 models with two matching `approx` models (four equal weights). This is a direct diversity test, with an expected ~10-second fit under the 60-second limit.

Result: 0.6855, equal to the two-model histogram ensemble, but fit time rose from 1.4 s to 10.0 s and the artifact doubled. Discard under the keep rule; the added models bring no observed ranking gain.

## Plateau research before experiment 25

Four consecutive discards moved the printed AUC by less than 0.001. Revisited [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): `max_cat_to_onehot` switches low-cardinality columns from partition splits to one-hot splits. The [scikit-learn categorical comparison](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_categorical.html) underscores that encoding choices can materially change gradient boosting. Our categorical features have 7 weekdays, 20 carriers, and 283 airports on each side, so a threshold of 32 isolates the first two without expanding the airport features. [DART's official guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) presents tree dropout as a separate option if categorical encoding does not help.

## Experiment 25 — one-hot splits for carrier and weekday (exploration)

Hypothesis: partitioning the seven weekdays and 20 carriers can group categories by 2005-specific gradients. Force one-hot splits for those columns using `max_cat_to_onehot=32`; origin and destination remain partitioned. This differs from previous category-threshold tests, which limited the number of candidate levels within a partition.

Result: 0.6826 (-0.0029). Discard. Partition grouping is substantially more useful for carrier and/or weekday than one-hot splits. Isolate weekday alone next; carrier partitions are especially likely to benefit from grouping 20 levels.

## Experiment 26 — one-hot weekday only (follow-up)

Hypothesis: the large loss with threshold 32 may come from carrier's 20 levels. Set `max_cat_to_onehot=8`, so only seven-level weekday switches to one-hot splits; carrier and both airports retain partition splits. This isolates which low-cardinality column benefits from the default strategy.

Result: 0.6838 (-0.0017). Discard. Weekday partitioning itself is useful; the default categorical treatment should remain.

## Experiment 27 — loss-guided tree growth (exploration)

Hypothesis: the depthwise models may spend splits in low-signal branches while time/airport interactions are concentrated in a few branches. [XGBoost's parameter guide](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `grow_policy=lossguide` as choosing the node with the highest gain. Fit two loss-guided members with 8 and 16 leaf budgets, roughly matching the existing depth-3 and depth-4 tree sizes, and bound path depth at 6.

Result: 0.6847 (-0.0008), with slightly longer fit. Discard as a replacement; it might still diversify the retained depthwise ensemble because tree shapes differ.

## Experiment 28 — blend depthwise and loss-guided trees (follow-up)

Hypothesis: loss-guided models score slightly worse individually but can focus more leaves on specific interactions. Their errors may complement the retained depthwise pair. Average all four equally; compare with the simpler 0.6855 two-model ensemble.

Result: 0.6854 (-0.0001) and more training/serving work. Discard. Alternative tree growth adds no useful diversity at this precision.

## Experiment 29 — smooth additive model in XGBoost ensemble (exploration)

Hypothesis: the XGBoost members handle interactions well but their learned piecewise calendar/time functions can be noisy across years. A regularized logistic model with one-hot identities and smooth spline effects for scheduled time, day of year, and distance could supply a stable additive component. [Scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) uses splines for temporal effects, and its [mixed-type pipeline example](https://scikit-learn.org/stable/auto_examples/compose/plot_column_transformer_mixed_types.html) combines one-hot features with logistic regression. Fit only on train, using the same row-wise `prepare`, then average at weights 40%/40%/20%. This is a different model family within the retained XGBoost ensemble.

Result: 0.6860 (+0.0005), with 2.2 s fit. Keep. A small smooth additive contribution complements the tree models.

## Experiment 30 — larger additive-model weight (follow-up)

Hypothesis: the 20% logistic contribution helped, so the smooth additive model may merit a larger share. Test 40% logistic and 30% for each tree, with the component models and features unchanged. This tests whether the gain extends beyond a small correction.

Result: 0.6855 (-0.0005). Discard. The additive member helps as a small correction, while the trees retain most predictive power.

## Synthesis after 30 experiments

Best so far: 0.6860 at ac20606, +0.0117 from baseline. A 20% smooth logistic contribution improved the depth-3/4 XGBoost ensemble, but 40% lowered AUC. Other recent alternatives—finer histograms, approximate splits, one-hot low-cardinality categories, and loss-guided growth—did not improve. This suggests the best remaining gains may come from better complementary model structure or feature representation, rather than more capacity in the existing trees. Next test a smaller logistic weight and then dropout or a different treatment of seasonal/time effects.

## Research before experiment 31

- [Scikit-learn soft-voting documentation](https://scikit-learn.org/stable/modules/ensemble.html) describes probability averaging among classifiers. The successful heterogeneous blend makes the contribution weight a focused follow-up, not a new search over data features.
- [PMLR DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) argues tree dropout can reduce late-tree over-specialization. This gives a distinct way to regularize XGBoost if blend weights plateau, though XGBoost's [DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) warns it can be slower.
- [Scikit-learn spline documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.SplineTransformer.html) describes knot choices and periodic extrapolation. The retained logistic model uses quantile knots, so a later ablation can examine whether the calendar spline is helping or overfitting.

## Experiment 31 — smaller additive-model weight (follow-up)

Hypothesis: the 20% logistic component helped but 40% hurt. Test 10% logistic and 45% per tree to bracket the useful blend fraction, leaving fitted components unchanged.

Result: 0.6859 (-0.0001). Discard. The 20% blend beats both lower and higher tested weights at printed precision; stop adjusting probability weights.

## Experiment 32 — blend log odds instead of probabilities (exploration)

Hypothesis: XGBoost and logistic outputs can have different confidence scales. A weighted average of their log odds may rank rows better than an arithmetic probability average without retraining. [Recent ensemble-aggregation research](https://proceedings.mlr.press/v337/razafindralambo26a.html) identifies linear probability and geometric/logit pooling as distinct standard choices. Test 40%/40%/20% logit pooling, with clipping for numerical stability and unchanged component fits.

Result: 0.6860, equal to probability pooling at printed precision but with more code and marginally slower evaluation. Discard under the keep rule.

## Plateau research before experiment 33

Three consecutive blend changes moved AUC by less than 0.001. The [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) describes late boosting trees becoming specialized to a few instances and proposes tree dropout to regularize that. [XGBoost's DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) provides `rate_drop` and `skip_drop` and warns about slower training. This is a distinct training mechanism from the unsuccessful split-method and weight tests. The [XGBoost random-forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) gives another possible direction using randomized parallel trees if dropout does not help.

## Experiment 33 — DART depth-4 member (exploration)

Hypothesis: replacing only the depth-4 member with DART (10% tree dropout, skipped half the iterations) may reduce its year-specific late-tree effects while retaining diversity with the depth-3 and smooth models. Use all 250 rounds explicitly at prediction time for stable test scoring, and monitor the 60-second training limit.

Result: 0.6857 (-0.0003), with fit time 25.0 s rather than 2.2 s. Discard. The dropout schedule is feasible but does not improve this ensemble enough to justify its cost.

## Research before experiment 34

[Research on the geography of U.S. air traffic delays](https://www.sciencedirect.com/science/article/pii/S0966692321003136) reports different delay propagation at airports dominated by a carrier, which suggests carrier and origin can interact. [Airline hub delay research](https://www.sciencedirect.com/science/article/pii/S0191261509001313) discusses carrier-specific hub effects. The train-only pair has 1,551 observed levels (median 43 sampled flights per level), much less granular than the 4,290-route category that failed earlier. This is a domain-motivated interaction rather than another tree-parameter tweak.

## Experiment 34 — carrier-at-origin category (exploration)

Hypothesis: a carrier's operation at a given airport changes departure reliability beyond separate carrier and origin effects. Add a train-fitted CarrierOrigin category to both tree and regularized logistic members. Each row's key is computed from its own carrier and origin; unseen pairs map to missing for XGBoost and unknown for one-hot logistic encoding.

Result: 0.6825 (-0.0035), evaluation also slower. Discard. Like the route category, this high-cardinality interaction appears too specific to the 2005 sample, even with logistic regularization. Favor broad additive effects.

## Experiment 35 — stronger logistic regularization (follow-up)

Hypothesis: the successful additive member uses many one-hot airport levels, some sparse and unstable across years. [Scikit-learn's LogisticRegression documentation](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) defines smaller `C` as stronger regularization. Reduce C from 0.2 to 0.05 in that member only, retaining its 20% blend weight and all tree settings.

Result: 0.6859 (-0.0001). Discard. Stronger shrinkage loses a little useful airport/carrier contrast; test weaker regularization in the opposite direction.

## Experiment 36 — weaker logistic regularization (follow-up)

Hypothesis: the loss at C=0.05 suggests the original additive model may be too constrained. Increase only its C to 1.0 and compare with the 0.6860 best at C=0.2.

Result: 0.6861 (+0.0001), though fit is slightly slower. Keep under the strict AUC rule. The additive model benefits from less shrinkage at this blend weight.

## Experiment 37 — much weaker logistic regularization (follow-up)

Hypothesis: C=1.0 improved over 0.2 while 0.05 hurt. Increase to C=5.0 to learn whether the trend continues or overfitting of sparse airport indicators begins. Retain the same features and blend weights.

Result: 0.6861, equal at printed precision, without code or speed simplification. Discard. C=1.0 is adequate; avoid further C tuning.

## Experiment 38 — scheduled time in minutes (exploration)

Hypothesis: HHMM is ordered correctly for trees, but its numeric gaps misrepresent elapsed minutes for the logistic spline (for example 09:59 to 10:00 jumps by 41 units). Convert to minutes since midnight inside `prepare` for every row. [Flight-delay modeling research](https://onlinelibrary.wiley.com/doi/full/10.1155/2024/3385463) represents scheduled departure in minutes; [scikit-learn's spline example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) assumes a meaningful numeric time scale. The transformation is monotone, so tree order should be preserved.

Result: 0.6861, equal at printed precision, but row-wise preparation slows evaluation by about 3 s. Discard under the keep rule.

## Experiment 39 — remove distance from smooth member (ablation)

Hypothesis: distance helped the tree ensemble in experiment 21, but its contribution to the 20%-weighted smooth logistic member is unknown. Remove only that member's distance spline; if AUC is maintained, the smaller pipeline is simpler and may generalize better.

Result: 0.6860 (-0.0001). Discard despite simpler pipeline, per the strict keep rule. Distance is useful in both model families.

## Plateau research before experiment 40

Three consecutive discards changed printed AUC by less than 0.001. [Scikit-learn's time-feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows smooth spline features as a way to capture temporal patterns in linear models, while [SplineTransformer's documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.SplineTransformer.html) specifies that knot count controls the number of basis functions. Since the current logistic member is useful only at 20% weight, its time and seasonal fits may be too detailed. Test a smaller basis rather than another probability-weight tweak.

## Experiment 40 — smoother logistic time and season (follow-up)

Hypothesis: fewer spline knots can suppress 2005-specific daily/seasonal wiggles while preserving broad delay trends. Reduce time knots from 10 to 6 and day-of-year knots from 8 to 5 in the logistic member only. This is one coherent reduction in the additive model's temporal complexity.

Result: 0.6860 (-0.0001). Discard. Coarser time and seasonal splines remove a little useful structure; test a larger basis next to bracket the original.

## Synthesis after 40 experiments

Best so far: 0.6861 at 28ed4b1, +0.0118 over baseline. The 20%-weighted logistic spline member still helps, and relaxing its regularization to C=1.0 added a small gain. Further C relaxation tied rather than improved; removing its distance spline or reducing its time/season knots hurt. HHMM-to-minutes retained AUC but slowed per-row preparation. Domain-specific carrier-origin interactions hurt substantially. The current model benefits from a compact day-of-year representation, moderate-depth XGBoost ensemble, and a small smooth additive correction. The remaining time is best spent on a few targeted tests of smooth-model shape, keeping the strict AUC rule.

## Research before experiment 41

[Scikit-learn's spline interpolation example](https://scikit-learn.org/dev/auto_examples/linear_model/plot_polynomial_interpolation.html) explains how a larger spline basis can represent more local variation, while its [cyclical feature guide](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) illustrates periodic splines for calendar features. Experiment 40's smaller basis lost a little AUC, so bracket the current setting with more knots; periodic seasonality is a separate follow-up.

## Experiment 41 — richer logistic temporal splines

Hypothesis: the 10-knot time and 8-knot season splines may be slightly underfit. Increase only these two basis sizes to 16 and 12, respectively, retaining tree members, blend weights, and logistic regularization.

Result: 0.6861, equal at printed precision. Discard because the extra spline features add complexity without measurable gain.

## Experiment 42 — periodic seasonal spline

Hypothesis: daily delay behavior may vary smoothly over the year boundary. Make the logistic member's day-of-year spline periodic, as in [scikit-learn's cyclical feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), retaining eight quantile knots and every other setting.

Result: 0.6857 (-0.0004). Discard. Enforcing continuity at the year boundary worsens this dataset's ranking.

## Experiment 43 — uniformly spaced departure-time knots

Hypothesis: quantile knots may cluster in common daytime departure hours and leave coarse resolution elsewhere. Use uniformly spaced knots for the logistic member's departure-time spline, retaining the knot count and all other settings. [Scikit-learn's SplineTransformer reference](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.SplineTransformer.html) defines uniform and quantile knot placement.

Result: 0.6861, equal at printed precision. Discard because the new knot placement brings no gain and is marginally slower to fit.

## Final summary

The best Eval AUC is **0.6861** at commit **28ed4b1**, up **0.0118** from the 0.6743 baseline. This run completed 43 non-baseline experiments. The retained model uses a day-of-year feature, an average of depth-3 and depth-4 XGBoost models, and a 20%-weighted logistic model with one-hot categorical features and smooth time, season, and distance effects. Shallower trees, a slower boosting schedule, the compact calendar representation, model averaging, and the lightly regularized smooth member produced the meaningful gains.

High-cardinality route/carrier-origin categories, one-hot tree splits, more tree rounds, subsampling, alternative tree growth, and dropout did not improve the best score. The final spline tests showed no benefit from more knots or uniform time knots, while periodic seasonality lowered AUC. A next run could test a different low-capacity complementary model or carefully regularized interactions between departure time and broad airport groups, with the same strict Eval AUC keep rule.
