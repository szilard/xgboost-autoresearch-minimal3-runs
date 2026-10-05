# Research log — oct5

Baseline `8d9c760`: unchanged starter, Eval AUC 0.6743. Training 1.4 s, evaluation 30.7 s. The data has 200,000 rows and eight permitted predictors; categorical fields have 12 months, 31 day numbers, 7 weekdays, 20 carriers, and 283 origin and destination airports.

Research before tuning: [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends controlling tree complexity and using a smaller learning rate with more rounds; [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explains `max_depth`, `min_child_weight`, and sampling. [Categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes one-hot versus partitioned splits. [Berkeley flight delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) motivates airport, carrier, and schedule features. Available version is XGBoost 3.4.1.

## Experiment 1 — follow-up: conservative, longer boosting

Hypothesis: the baseline 100 depth-6 trees fit spurious details of the sampled 2005 data, which generalize poorly to 2006. Try 300 depth-4 trees at learning rate 0.05 with `min_child_weight=5`; shallower trees and larger leaves should reduce that variance while extra rounds restore useful capacity. Based on XGBoost's parameter tuning guide above.

Result `7cbcf53`: Eval AUC 0.6793, keep. The conservative longer boosting improved by 0.0050.

## Experiment 2 — exploration: ordinal day of year

Hypothesis: Month and day of month as separate categorical predictors make it hard for shallow trees to represent seasonal transitions and localized calendar effects. Add a numeric day-of-year feature from the row's month and day; the model can then split on date intervals. A [flight delay study](https://onlinelibrary.wiley.com/doi/10.1155/2024/3385463) explicitly constructs day of year, and [this flight prediction study](https://www.mdpi.com/2226-4310/8/6/152) includes it among schedule-derived features. This is available before departure and is stable for row-by-row scoring.

Result `d19cef7`: Eval AUC 0.6829, keep. Ordered date added 0.0036 AUC, suggesting that temporal continuity helps beyond separate month and day categories.

## Experiment 3 — follow-up: categorical scheduled hour

Hypothesis: departure risk has distinct peaks by time of day. The raw HHMM number gives the model an ordering, while a categorical hour lets a shallow tree group nonadjacent peak hours in one split. [UC Berkeley's flight delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) uses departure time blocks and describes their operational rationale. Add only the hour category, retaining the raw scheduled time.

Result `4a69ee1`: Eval AUC 0.6813, discard. The categorical hour lost 0.0016 versus the best. The numeric HHMM and shallow trees may already represent useful daily timing; an extra categorical version may add noise.

## Experiment 4 — exploration: route identity

Hypothesis: the same origin can serve routes with different delay profiles, and four-level trees may spend useful capacity discovering origin–destination interactions. Add an explicit categorical route based only on origin and destination. The 2005 train set contains 4,290 distinct routes. [This flight delay modeling paper](https://www.nature.com/articles/s41598-024-55217-z) treats route as an operational indicator. New routes become missing, which XGBoost supports.

Result `8be9a98`: Eval AUC 0.6733, discard. High-cardinality route identity lost 0.0096. It may overfit idiosyncratic 2005 routes and showed pandas warnings for unseen 2006 combinations.

## Experiment 5 — follow-up: more boosting rounds

Hypothesis: experiment 1's smaller steps and depth-4 trees may still be underfit at 300 rounds. Increase to 600 rounds with all other features and parameters fixed. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) advises increasing the number of rounds when reducing the step size. If extra rounds help, we can then explore stronger regularization around the longer model.

Result `7522d7e`: Eval AUC 0.6782, discard. More rounds lost 0.0047, suggesting the model overfits before 600 rounds.

Research pause after three discards: the [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) notes that trees can learn nonlinear effects from ordinal time variables without a categorical hour. This matches our failed hour category. The next test removes a redundant calendar category from the successful day-of-year model.

## Experiment 6 — ablation: remove categorical day of month

Hypothesis: day-of-month categorical splits may memorize 2005-specific date effects that shift in 2006. The retained ordinal day-of-year feature provides smoother date representation. Remove only the original day-of-month category; this also makes row-wise preparation a little faster. Motivated by the temporal encoding discussion in scikit-learn's example above.

Result `9b34686`: Eval AUC 0.6828, discard. It was nearly tied but lower than 0.6829; the strict keep rule applies. The day category provides a small benefit.

## Experiment 7 — exploration: row subsampling

Hypothesis: the model still overfits 2005-specific patterns, as 600 rounds and route identity both hurt. Set `subsample=0.8` while keeping all other model choices fixed. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes row sampling as a way to improve robustness to noise. The 200,000-row train set should still give ample cases per tree.

Result `80b31a4`: Eval AUC 0.6828, discard. Random row subsampling lost 0.0001.

## Experiment 8 — exploration: regularize categorical partitioning

Hypothesis: origin and destination each have 283 levels, and the model's fitted `max_cat_threshold` default is 64. More limited category partitions could reduce noisy airport splits across years. Set `max_cat_threshold=16`, keeping all other settings fixed. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says this parameter caps categories considered per partitioned split to prevent overfitting.

Result `9ea449b`: Eval AUC 0.6793, discard. Strongly restricting airport partitions lost 0.0036, suggesting the model needs to compare more airport groups.

## Experiment 9 — follow-up: broader categorical partitions

Hypothesis: since 16 was too restrictive, the default cap of 64 may also limit useful airport grouping. Try `max_cat_threshold=128` and compare against 0.6829. This is the opposite direction from experiment 8, based on the same [XGBoost parameter definition](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result `fc72ea6`: Eval AUC 0.6804, discard. The default cap of 64 outperformed both narrower and broader partition searches.

## Experiment 10 — follow-up: earlier stopping point

Hypothesis: 600 rounds substantially hurt versus 300, implying later trees fit year-specific noise. The optimum number of rounds may be below 300. Test 200 rounds at the same learning rate, depth, and features. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) discusses the balance between boosting rounds and overfitting.

Result `edc5de6`: Eval AUC 0.6835, keep. Fewer rounds gained 0.0006 and also made the artifact smaller and training faster.

## Synthesis after 10 experiments

Best Eval AUC is 0.6835 at `edc5de6`, versus baseline 0.6743. A smaller, shallower boosted model and an ordinal day-of-year feature helped. More rounds hurt, suggesting 2005-specific detail is a problem. A raw categorical route was markedly harmful; categorical departure hour was also harmful. The default airport partition cap of 64 beat both 16 and 128. The day-of-month category still contributes slightly alongside day of year. My current theory is that stable calendar structure and conservative model capacity matter more here than high-cardinality interactions. Next I will test categorical encoding and then alternative regularization or a smooth calendar feature.

Research at the 10-experiment pause: [the original mlcourse.ai flight-delay assignment](https://mlcourse.ai/book/topic10/assignment10_flight_delays_kaggle.html) and [a worked discussion of that task](https://blog.gitcode.com/dfc80702b1d0d7912ba963928d9ed172.html) identify one-hot encoding of date, carrier, and route as a useful approach, sometimes blended with a linear model. Our native XGBoost category support already uses partitioning for all six categorical fields because the fitted one-hot threshold is 4. [XGBoost's categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains the split-rule difference. I will test one-hot splits on the lower-cardinality fields without changing the high-cardinality airports first.

## Experiment 11 — exploration: one-hot splits for calendar and carrier

Hypothesis: one-hot splits for month, day, weekday, and carrier isolate robust individual categories; partitioning these small fields may group noisy categories together. Set `max_cat_to_onehot=32`, which leaves the 283-level airports partitioned. This directly tests the split strategy from the XGBoost categorical guide above.

Result `d3998ca`: Eval AUC 0.6820, discard. Partitioning the small categories is better here than individual-category splits.

## Experiment 12 — exploration: shallower trees

Hypothesis: the move from depth 6 to 4 was part of the successful first experiment, and 200 rounds now outperform 300. Try depth 3 at 200 rounds to test further complexity reduction while holding everything else fixed. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends depth as a primary overfitting control.

Result `4e23f67`: Eval AUC 0.6831, discard. Depth 3 was close but below depth 4, so reducing interaction capacity further did not help.

## Experiment 13 — follow-up: moderate depth increase

Hypothesis: the depth-3 loss may mean useful interactions need at least four splits, while the smaller 200-round model may tolerate depth 5. Test depth 5 with all else fixed. This brackets the retained depth 4 from the other side and isolates tree depth, following the same XGBoost tuning guidance.

Result `1f4f704`: Eval AUC 0.6812, discard. Depth 4 beat both depth 3 and 5 at 200 rounds.

## Experiment 14 — exploration: larger minimum leaves

Hypothesis: even depth-4 trees can create noisy small airport/category leaves, especially given the year shift. Raise `min_child_weight` from 5 to 10 to require more Hessian mass for every leaf. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as a direct complexity control. All other settings stay fixed.

Result `88c11bc`: Eval AUC 0.6835, discard. It tied the kept model at printed precision but added no simplification or reliable speed improvement.

## Experiment 15 — exploration: holiday travel window

Hypothesis: day-of-year cannot naturally align moving holidays such as Thanksgiving between 2005 and 2006. Add one binary feature for travel windows around Thanksgiving, Christmas/New Year, and July 4. Thanksgiving is computed from each row's month/day/weekday by finding the fourth Thursday of November; no test data or year-specific lookup is needed. The [U.S. Bureau of Transportation Statistics holiday-delay analysis](https://www.transtats.bts.gov/holidayDelay.asp?pn=1) explains why the travel season covers nearby days that vary by year. Check that `c-4` corresponds to Thursday using only the train data (Nov 24, 2005).

Result `d664ae0`: Eval AUC 0.6835, discard. The feature tied printed AUC but added code and ~11 seconds of evaluation time, so the keep rule rejects it.

## Experiment 16 — exploration: stronger L2 leaf regularization

Hypothesis: explicit calendar and airport categories create leaves with unstable 2005-specific scores. Try `reg_lambda=10` (default 1) to shrink those scores without changing tree depth or feature preparation. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes larger lambda as more conservative.

Result `ff6434b`: Eval AUC 0.6822, discard. Stronger L2 shrinkage hurt.

## Experiment 17 — ablation: default minimum child weight

Hypothesis: `min_child_weight=5` from experiment 1 may be unnecessary in the now smaller 200-round model and could suppress useful airport-specific leaves. Remove the explicit setting to restore XGBoost's default 1. This is a simplification and tests the other side of experiment 14's value 10. See the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result `b157ab7`: Eval AUC 0.6833, discard. A minimum child weight of 5 remains slightly better than both 1 and 10.

## Experiment 18 — follow-up: 150 boosting rounds

Hypothesis: 200 rounds beat 300 and 600; the generalization optimum might be still earlier. Test 150 rounds, only 50 fewer than the current best, to locate the early side of the optimum. This is a targeted follow-up to experiments 5 and 10, not a random parameter change. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explains the relationship between boosting rounds and overfitting.

Result `c2853dd`: Eval AUC 0.6827, discard. Of 150, 200, 300, and 600 rounds tested at 0.05, 200 is best.

## Experiment 19 — exploration: finer numerical histograms

Hypothesis: `CRSDepTime` and distance have many distinct values, and 256 histogram bins may merge nearby but operationally different departure times. Raise `max_bin` to 512, leaving model complexity otherwise fixed. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says more bins improve split precision at added computation cost.

Result `a1ec0f8`: Eval AUC 0.6833, discard. Finer bins did not improve the score.

## Experiment 20 — exploration: average depth-3 and depth-4 XGBoost models

Hypothesis: the depth-3 model from experiment 12 scored close to the best and may make different errors from depth 4. Average their predicted probabilities equally to reduce model variance while preserving the same row-wise features. [The original mlcourse.ai flight-delay assignment](https://mlcourse.ai/book/topic10/assignment10_flight_delays_kaggle.html) describes a probability mixture of complementary models for this task. Our test uses two XGBoost depths so that inference preparation stays exactly the same.

Result `cb906fc`: Eval AUC 0.6840, keep. The equal-probability mixture gained 0.0005 over the single depth-4 model. Training 3.0 s and evaluation 34.4 s remain within limits.

## Synthesis after 20 experiments

Best Eval AUC is 0.6840 at `cb906fc`, baseline 0.6743. The main improvements remain a moderate 200-round depth-4 XGBoost, ordered day-of-year, and now blending a close but distinct depth-3 model. The gain from averaging suggests model variance matters. Parameter sweeps around depth, child weight, categorical partition cap, and histogram bins show a narrow optimum near the retained choices; stronger L2 and holiday windows did not help. Next I will tune the new blend deliberately, then explore smooth seasonal encoding or a more diverse model.

Research at this pause: [scikit-learn's ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) describes weighted averages of predicted probabilities; [XGBoost's random-forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) offers boosted random forests as a more structural averaging option. [XGBoost's DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes tree dropout for overfitting control, but it may raise training cost.

## Experiment 21 — follow-up: favor stronger depth-4 model in blend

Hypothesis: depth 4 alone (0.6835) outperformed depth 3 alone (0.6831). Giving the stronger model 75% and the shallow model 25% of the probability mixture may retain diversity with less bias from the weaker component. [scikit-learn's ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) supports weighted soft voting. Only the blend weight changes.

Result `60c6e99`: Eval AUC 0.6839, discard. More weight on depth 4 lost 0.0001; the shallow model's distinct predictions may deserve more weight than its standalone AUC suggests.

## Experiment 22 — follow-up: favor shallow model in blend

Hypothesis: the 75% depth-4 blend was worse than the equal blend, so test the opposite direction: 25% depth 4 and 75% depth 3. This brackets the useful mixture and tests whether a more conservative main model generalizes better despite its lower standalone score. The weighted probability average follows [scikit-learn's ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html).

Result `ebbf483`: Eval AUC 0.6838, discard. The equal blend beat both 75/25 alternatives; stop tuning this weight.

## Experiment 23 — exploration: smooth seasonal cycle

Hypothesis: ordered day-of-year helped but has an artificial break at New Year. Add sine and cosine of day of year, retaining the raw ordinal date, so shallow trees can group winter dates across that boundary and capture broad annual seasons. [scikit-learn's time-feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains cyclical transformations. Both features depend only on the current row.

Result `774b066`: Eval AUC 0.6833, discard. Cyclical date features did not add to ordinal day-of-year and categories.

## Experiment 24 — exploration: add a stochastic third XGBoost model

Hypothesis: the depth-3/depth-4 average improved AUC because the models make partly distinct errors. A third depth-4 model trained with 80% row and column sampling may add further diversity, even though subsampling the single model in experiment 7 did not win. Average all three equally. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes both sampling controls, and [scikit-learn's ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) motivates averaging diverse predictions. Same feature preparation and row-wise semantics.

Result `ec24960`: Eval AUC 0.6841, keep. The sampled third model improved by 0.0001; training and evaluation remain quick.

## Experiment 25 — follow-up: sample a fourth shallow model

Hypothesis: one stochastic member helped slightly, and the depth-3 model contributed useful errors to the earlier two-model average. Add a depth-3 model with 80% row and column sampling and a distinct seed, then average all four. This tests whether the combined structural and sampling diversity helps more than the added weaker model hurts. [XGBoost's random-forest guide](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes sampling to diversify tree ensembles.

Result `ad29f42`: Eval AUC 0.6839, discard. A fourth sampled shallow member reduced the score; three models is better so far.

## Experiment 26 — exploration: carrier–origin identity

Hypothesis: carrier-specific hub operations can have distinct departure-delay risk at the same airport. [Research on U.S. airline delays](https://www.nber.org/papers/w9744) reports differences for hub carriers at their origin airports. An explicit carrier–origin category lets shallow trees use that interaction. The train set has 1,551 distinct carrier–origin pairs, substantially fewer than the 4,290 routes whose identity hurt in experiment 4. Add the pair as a categorical feature to the retained three-model blend; unknown pairs map to missing.

Result `ff97b80`: Eval AUC 0.6780, discard. Like the route category, a high-cardinality pair hurt cross-year generalization and inflated the artifact.

## Experiment 27 — exploration: prune weak tree splits

Hypothesis: although the current ensemble avoids explicit high-cardinality pairs, its component trees may still make weak splits tied to 2005 noise. Set `gamma=1` in all three models to require a minimum loss reduction for each split, keeping the feature preparation and ensemble weights fixed. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines gamma as the minimum split gain.

Result `52baa38`: Eval AUC 0.6841, discard. It tied printed AUC without simplification or speed improvement.

## Experiment 28 — exploration: alternative tree split algorithm in third model

Hypothesis: the sampled third ensemble member can contribute different, useful errors if built using XGBoost's `approx` tree method, which recalculates Hessian-weighted quantile sketches for each tree rather than relying on `hist`'s one global sketch. The logistic objective has nonconstant Hessian, so the [XGBoost tree-method guide](https://xgboost.readthedocs.io/en/stable/treemethod.html) says `approx` can sometimes improve accuracy. Change only the third model's tree method; categorical data is supported.

Result `88637c6`: Eval AUC 0.6839, discard. The approximate splitter was slower and slightly worse in the three-model ensemble.

## Experiment 29 — exploration: dropout in third XGBoost model

Hypothesis: the third model currently contributes through row/column sampling. DART tree dropout may produce a more distinct predictor and reduce overfitting, which could improve the average despite the usual training-cost penalty. Change only the third member to DART with `rate_drop=0.1` and `skip_drop=0.5`, as described in [XGBoost's DART guide](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html). The two existing depth models and feature preparation remain fixed.

Result `a4e732a`: Eval AUC 0.6836, discard. DART was slower and lower scoring.

## Experiment 30 — exploration: L1 leaf regularization

Hypothesis: the three-model blend still includes unstable small leaf effects, and L1 regularization may suppress these while preserving stronger categorical/calendar signals. Set `reg_alpha=1` in all three component models. Unlike experiment 16's L2 shrinkage, L1 can drive weak leaves to zero. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this penalty.

Result `bc6f8e6`: Eval AUC 0.6843, keep. L1 regularization improved the three-model blend by 0.0002.

## Synthesis after 30 experiments

Best Eval AUC is 0.6843 at `bc6f8e6`, baseline 0.6743. Depth-4 boosting with 200 rounds and min-child weight 5 was the strongest single component. Ordered day of year helped. Averaging depth-4, depth-3, and one sampled depth-4 model added another 0.0008 over the best single model, and L1 regularization added 0.0002. High-cardinality route and carrier–origin identities failed sharply. Holiday and cyclical calendar features, DART, approximate splits, and stronger L2 did not help. The current theory is that modest capacity and low-variance predictions transfer best from 2005 to 2006.

Research at this pause: [XGBoost's interaction-constraint documentation](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) suggests constraining implausible feature combinations to cut noise. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) also covers alternative leaf-growth policies. Time remaining favors a targeted follow-up to the successful L1 result before a code simplification.

## Experiment 31 — follow-up: stronger L1 regularization

Hypothesis: L1 at 1 improved the ensemble. Test `reg_alpha=3` in all three models to see whether more aggressive removal of small leaf scores improves transfer across years. This changes one parameter and directly follows experiment 30. Source: [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result `e4ed85d`: Eval AUC 0.6852, keep. Raising L1 from 1 to 3 improved by 0.0009, a larger move than recent ensemble tweaks.

## Experiment 32 — follow-up: test upper side of L1 optimum

Hypothesis: L1 at 3 has not yet exhausted the benefit of pruning weak 2005-specific leaves. Test `reg_alpha=6` in all three models to locate whether the optimum lies higher. This is a direct extension of the successful experiment 31, with one changed parameter; [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes the penalty's effect.

Result `b602c3f`: Eval AUC 0.6858, keep. Raising L1 from 3 to 6 improved by 0.0006.

## Experiment 33 — follow-up: L1 at 10

Hypothesis: the consistent gains at L1 values 1, 3, and 6 suggest further shrinkage may help. Test `reg_alpha=10` in all three ensemble members with everything else fixed. [XGBoost's parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explains this as stronger L1 regularization; this is the last targeted test before the time limit.

Result `cd7df53`: Eval AUC 0.6853, discard. L1 at 10 was worse than 6; the optimum among tested values is 6.

## Final summary

Best Eval AUC: **0.6858** at kept commit `b602c3f` on branch `oct5`, versus unchanged baseline 0.6743 (gain 0.0115). The best artifact is the saved model for that commit. The model uses a row-wise ordinal day-of-year feature and averages three XGBoost classifiers: depth 4, depth 3, and a sampled depth-4 member. All use 200 rounds, learning rate 0.05, minimum child weight 5, and L1 penalty 6.

What worked: conservative tree capacity, day-of-year, a small diverse ensemble, and L1 regularization. What did not: explicit high-cardinality route or carrier–origin identities, extra rounds, categorical departure hour, cyclical date or holiday features, stronger L2, and DART/approximate third models. The tested L1 values 0, 1, 3, 6, and 10 gave the clearest late-run trend; 6 was best.

Next: if running another experiment, refine L1 near 6 and consider interaction constraints to suppress implausible feature combinations. The human-only holdout check can assess whether the Eval AUC gain transfers to unseen rows; it was not used in this run.
