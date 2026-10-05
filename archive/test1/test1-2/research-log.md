# Research log — oct4

## Baseline — b15ec66

Unchanged starter: 100 depth-6 trees, learning rate 0.1, native categorical features. Eval AUC 0.6743; training 0.6 s, evaluation 30.2 s. The 200,000 training rows have no missing values; labels are balanced. Training is from 2005, evaluation from 2006.

Initial research: [XGBoost tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identify tree complexity, subsampling, and learning rate/tree count as key controls; [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes category partitioning. A [flight-delay feature-engineering study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) motivates temporal features. Experiments will test these ideas against the 2006 evaluation metric.

## Experiment 1 — exploration: departure hour

Hypothesis: a categorical scheduled departure hour lets the model group hours with similar delay risk, while retaining the raw HHMM value for within-hour splits. This follows the temporal-block idea from the flight-delay study above. The feature uses only the row's scheduled time, so row-by-row scoring remains consistent.

Result: 0.6747 (+0.0004); keep 9149f7e. The gain is small but positive. Hourly delay rates in train increase across the day, so raw time already represents much of this signal.

## Experiment 2 — follow-up: more boosting rounds

Hypothesis: 100 trees may leave time/airport/carrier interactions underfit. Increase to 300 trees at the same learning rate to test model capacity. The [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) notes the tradeoff between boosting rounds and step size; this tests rounds alone first.

Result: 0.6672 (-0.0075), discarded 0bb0fa7. More rounds at the same depth and step size overfit relative to the 2006 evaluation data.

## Experiment 3 — follow-up: fewer boosting rounds

Hypothesis: the steep loss with 300 trees suggests that 100 may already overfit the cross-year target. Try 50 trees, holding every other setting fixed. This is the reverse side of the capacity test, not a small step around 300.

Result: 0.6764 (+0.0017); keep 06ea12b. The 2006 evaluation favors fewer rounds at depth 6.

## Experiment 4 — follow-up: bracket the round count

Hypothesis: if 50 is better than 100, 25 may improve further by avoiding year-specific interactions. Test 25 rounds with all other settings held fixed; this brackets the capacity trend before changing tree shape.

Result: 0.6770 (+0.0006); keep b9608c0. Reduction continues to help, though by less than the previous step.

## Experiment 5 — follow-up: small ensemble

Hypothesis: the 2005-to-2006 drift still makes 25 depth-6 trees too specific. Try 10 trees to see whether the AUC peaks near a much smaller ensemble or falls from underfitting.

Result: 0.6732 (-0.0038); discard f562569. Ten rounds underfit; the useful range at depth 6 appears around 25–50 rounds.

## Experiment 6 — exploration: shallower trees with more rounds

Hypothesis: the sharp degradation from 100 to 300 depth-6 trees may be caused by high-order interactions, rather than boosting rounds alone. Test 100 depth-3 trees: fewer interactions per tree and more chances to fit broad, stable patterns. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends controlling tree complexity to limit overfitting.

Result: 0.6797 (+0.0027); keep cf3f678. Shallower trees generalize better across years than the best depth-6 ensemble tested.

## Experiment 7 — follow-up: more shallow trees

Hypothesis: depth-3 trees constrain interactions enough that additional rounds may keep learning useful main effects. Increase from 100 to 200 rounds, retaining depth 3 and all features.

Result: 0.6790 (-0.0007), discard ae80b47. Even at depth 3, extra rounds slightly hurt cross-year AUC.

## Experiment 8 — exploration: weak pairwise trees

Hypothesis: much of the transferable delay signal is in main effects and pairwise interactions. Try 200 depth-2 trees, giving roughly the same leaf budget as 100 depth-3 trees while limiting interaction order.

Result: 0.6771 (-0.0026); discard 118f064. Pairwise trees miss useful interactions despite a similar nominal leaf count.

## Experiment 9 — exploration: moderate tree depth

Hypothesis: depth 3 beat depth 2 and depth 6 in the tested configurations; depth 4 with 50 trees may retain useful three- or four-way interactions while limiting total leaf capacity. This tests the other side of the depth range around the current best.

Result: 0.6778 (-0.0019); discard b78557b. So far 100 depth-3 trees is the strongest configuration.

## Experiment 10 — exploration: categorical split strategy

Hypothesis: some month, weekday, hour, and carrier categories may warrant individual splits, while large airport categories should still be grouped by similar gradient signal. Set `max_cat_to_onehot=32`, switching the smaller categorical fields to one-hot splits. The [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) describes the two split methods and the threshold parameter.

Result: 0.6794 (-0.0003); discard 2f86dc7. Native partitioning of the smaller categorical features remains marginally better.

## Synthesis after 10 experiments

Best AUC: 0.6797 at cf3f678 (100 depth-3 trees plus categorical departure hour). Categorical hour helped slightly. More depth-6 rounds hurt sharply; 25 depth-6 trees helped, but shallower depth-3 trees were better still. Depth 2 lost useful interactions, depth 4 with fewer trees was worse, and one-hot splitting of small categorical fields gave no lift. The working theory is that transferable main effects and limited interactions matter most; high-order year-specific patterns overfit. Four consecutive discarded designs indicate a plateau, so the next phase will research and test new row-wise features or regularization instead of small round-count adjustments.

Plateau research: the [original mlcourse.ai flight-delay assignment](https://mlcourse.ai/book/topic10/assignment10_flight_delays_kaggle.html) on this feature schema created a `Flight` feature from origin and destination; the [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) also points to `min_child_weight`, `gamma`, subsampling and column sampling to control overfitting. These suggest a new route feature followed by regularization experiments.

## Experiment 11 — exploration: route category

Hypothesis: origin and destination have a joint effect that 100 depth-3 trees may not represent efficiently. Add the origin-destination pair as a native category, motivated by the original course assignment above. Train-fitted category levels make it stable under row-by-row scoring. High cardinality could overfit, so the evaluation decides whether to keep it.

Result: 0.6741 (-0.0056), discard d04fc95. The many route categories likely absorb sparse, year-specific detail; evaluation also slowed from about 34 to 46 s.

## Experiment 12 — exploration: continuous seasonal position

Hypothesis: a numeric day-of-year feature lets shallow trees split contiguous seasonal periods across month boundaries. The [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) uses temporal features for seasonality. Compute the value from each row's month and day using a fixed non-leap calendar, while retaining the original date categories.

Result: 0.6832 (+0.0035); keep 623c924. Numeric seasonal position is the largest single gain so far, suggesting smooth changes around month boundaries or holidays are useful.

## Experiment 13 — ablation: remove day-of-month category

Hypothesis: once day of year is present, the 31-way day-of-month category may encourage repeated, weak patterns that do not persist across years. Drop it from the model's categorical features while still using its value to compute day of year. This reduces complexity and may improve generalization.

Result: 0.6842 (+0.0010); keep 63c7ff8. Removing day-of-month also restored evaluation time to about 34 s.

## Experiment 14 — ablation: remove month category

Hypothesis: day of year might subsume month as well as day of month, and removing its redundant category could let the shallow ensemble focus on smooth seasonal effects. This test removes only Month from model inputs, retaining Month in the day-of-year calculation.

Result: 0.6850 (+0.0008); keep 6bae803. Numeric day of year appears to transfer better than either calendar category, and evaluation is faster (30.5 s).

## Experiment 15 — ablation: remove departure-hour category

Hypothesis: categorical departure hour provided only a small gain before day-of-year engineering and may now be redundant with raw scheduled time. Remove it to test whether simpler time representation preserves or improves AUC.

Result: 0.6843 (-0.0007); discard 3e13506 despite faster evaluation, per strict keep rule. Departure hour still contributes distinct signal.

## Experiment 16 — exploration: half-hour time blocks

Hypothesis: departure risk may change within an hour, while a 24-level category is coarse. Replace departure hour with 48 half-hour categories; a [GBM talk using this flight-delay schema](https://r-consortium.org/posts/gradient-boosting-machines-gbms-in-the-age-of-llms-and-chatgpt/szilard_GBM_LLM.pdf) specifically mentions half-hour slots. Retain raw scheduled time for exact ordering.

Result: 0.6845 (-0.0005); discard 894716b. The finer temporal categories add complexity without improving year-to-year AUC.

## Experiment 17 — exploration: row subsampling

Hypothesis: random 80% row subsamples for each tree may reduce sensitivity to year-specific training patterns while preserving the main effects captured by day of year and scheduled time. [XGBoost documentation](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) describes per-tree row sampling and recommends it as one route to reducing overfitting.

Result: 0.6835 (-0.0015); discard e237958. Full-sample splits were more effective at this ensemble size.

## Experiment 18 — exploration: limit categorical split breadth

Hypothesis: large airport categories can overfit by allowing many categories in one partition. Set `max_cat_threshold=16` to limit the categories considered per split while retaining partition-based categorical handling. [XGBoost parameters](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) describe this as a categorical overfitting control.

Result: 0.6758 (-0.0092); discard 8699218. Broad category partitions appear essential for airport signal.

Plateau research: [scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains cyclic trigonometric encodings and the year-boundary issue for day of year. The [original flight-delay assignment](https://mlcourse.ai/book/topic10/assignment10_flight_delays_kaggle.html) also blended logistic and boosted-tree predictions; this is a possible later direction if simpler features stop helping.

## Experiment 19 — exploration: cyclic winter feature

Hypothesis: numeric day of year separates Dec 31 from Jan 1 even though both are winter. Add a cosine of annual phase, giving a smooth high value near both year endpoints. Keep numeric day of year for precise seasonal position. This follows the scikit-learn cyclic-feature explanation above.

Result: 0.6852 (+0.0002); keep 0fc27c1. The winter wraparound contributes a small amount beyond day of year.

## Experiment 20 — follow-up: complete annual cyclic encoding

Hypothesis: the complementary sine term distinguishes spring from autumn at the same cosine value, allowing the shallow trees to model smooth phase effects over the full year. Add it while retaining day of year and cosine; source is the same scikit-learn cyclic-feature example.

Result: 0.6837 (-0.0015); discard b6193e3. The full cyclic pair does not help at this tree capacity.

## Synthesis after 20 experiments

Best AUC: 0.6852 at 0fc27c1. The strongest discovery is numeric day of year; removing Month and DayofMonth categories improved it further. Cosine helped marginally, while adding sine hurt. An exact route category, finer half-hour slots, row subsampling, and a stricter categorical split threshold all hurt. The best model has 100 depth-3 trees. The current theory is that simple seasonal effects transfer across years, while sparse categorical and overly flexible interactions do not.

New research: the [original mlcourse.ai assignment](https://mlcourse.ai/book/topic10/assignment10_flight_delays_kaggle.html) blends logistic regression with XGBoost for this feature schema. [scikit-learn's mixed-column example](https://scikit-learn.org/stable/auto_examples/compose/plot_column_transformer_mixed_types.html?highlight=standardscaler), [one-hot encoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html), and [soft-voting documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) show how to fit a compatible additive model and average probabilities. [Its target-encoder example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) warns that naive target encoding overfits without cross fitting; avoid it under this experiment's no-cross-validation constraint.

## Experiment 21 — exploration: blend additive and boosted models

Hypothesis: a one-hot logistic model estimates stable additive carrier, airport, day, and time effects that complement XGBoost's nonlinear effects. Fit both on train.csv and use a fixed 75% XGBoost / 25% logistic probability blend, following the original flight-delay assignment's model-combination idea. No extra validation or tuning metric is added.

Result: 0.6870 (+0.0018); keep ea82302. The additive model supplies complementary signal, with training still only 2.0 s and evaluation 33.0 s.

## Experiment 22 — follow-up: equal blend

Hypothesis: the additive model may deserve more than 25% weight because it captures stable main effects across years. Test an equal-probability blend, retaining identical submodels and features, to locate the useful weight range.

Result: 0.6862 (-0.0008); discard 27356fa. Logistic signal complements the tree but dominates too much at 50%.

## Experiment 23 — follow-up: lower logistic weight

Hypothesis: if 50% logistic is worse than 25%, a small 10% contribution may preserve most of the complement while reducing any linear-model bias. Test a 90/10 blend as the other side of a coarse weight bracket.

Result: 0.6862 (-0.0008); discard d867ae2. Among the broad weights tested, 25% logistic is best.

## Experiment 24 — follow-up: seasonal spline in logistic model

Hypothesis: the additive model currently sees an almost linear day-of-year effect, whereas flight delay risk varies nonlinearly through seasons. Give only the logistic branch a periodic spline of day of year, keeping XGBoost unchanged. [scikit-learn's time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) uses periodic splines to model annual patterns smoothly across New Year.

Result: 0.6846 (-0.0024); discard 3ace5d7. Extra seasonal flexibility in the logistic component appears to fit 2005 details that do not transfer.

## Experiment 25 — exploration: smaller boosting steps

Hypothesis: 200 shallower updates at learning rate 0.05 may preserve the broad pattern learned by 100 updates at 0.1 but reduce overshooting and improve cross-year ranking. Keep the logistic blend fixed. [XGBoost's tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends pairing a lower step size with more rounds.

Result: 0.6870 (equal); discard e4082b7 because it doubles the tree count, is slower, and does not simplify the code or improve rounded AUC.

## Experiment 26 — exploration: minimum leaf weight

Hypothesis: depth-3 trees can still isolate rare airport/date patterns when their child-weight threshold is 1. Raise `min_child_weight` to 50 to require substantially more training support per leaf. [XGBoost parameters](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) describe higher values as making trees more conservative.

Result: 0.6869 (-0.0001); discard f3ded52. More conservative leaves did not improve the rounded AUC.

Plateau research: the [original flight-delay assignment](https://mlcourse.ai/book/topic10/assignment10_flight_delays_kaggle.html) uses a route feature with one-hot logistic regression, while the earlier route-as-XGBoost-category test here hurt. [scikit-learn's pipeline](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline) and [function-transformer](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.FunctionTransformer.html) documentation support giving the two model branches different columns. This isolates the route effect to the regularized linear branch.

## Experiment 27 — exploration: route effect in logistic branch only

Hypothesis: route-specific effects may be stable enough for a regularized additive model even though native XGBoost overfit the large route category. Add an origin-destination string to `prepare`, one-hot it only for logistic regression, and exclude it from the unchanged tree branch.

Result: 0.6878 (+0.0008); keep 4d2dff3. The route effect is useful when regularized in the linear branch, and evaluation takes 35.6 s.

## Experiment 28 — follow-up: carrier-specific origin effect

Hypothesis: airlines differ in operations at their origin hubs, and this interaction may persist across years. Add a one-hot carrier-origin pair to the logistic branch only; retain the route feature and unchanged XGBoost branch. This extends the successful regularized interaction approach from experiment 27.

Result: 0.6883 (+0.0005); keep 348dae0. The regularized airline-origin effect adds a little transferable information.

## Experiment 29 — follow-up: carrier-specific departure hour

Hypothesis: carriers may differ in how delay risk accumulates through the day, an inference from the [flight-delay XGBoost study](https://www.sciencedirect.com/science/article/pii/S2772415822000050) finding that carrier and departure time matter individually. Add a carrier-hour one-hot interaction only to logistic regression, where L2 regularization can shrink weak cells.

Result: 0.6889 (+0.0006); keep d468113. Carrier-specific time-of-day effects improve ranking modestly.

## Experiment 30 — follow-up: carrier-specific destination

Hypothesis: destination airports may have carrier-specific scheduling patterns, complementary to carrier-origin and route effects. Add a carrier-destination one-hot interaction only to the logistic branch. Its sparsity is similar to carrier-origin, which helped in experiment 28.

Result: 0.6886 (-0.0003); discard 25eb20a. The added destination interaction is redundant or unstable at the current regularization strength.

## Synthesis after 30 experiments

Best AUC: 0.6889 at d468113. A 75% XGBoost / 25% logistic blend improved over XGBoost alone. Logistic-only one-hot interactions for route, carrier-origin, and carrier-hour each added small gains. Carrier-destination hurt. The earlier date feature discovery remains: numeric day of year plus a winter cosine and categorical departure hour give the tree useful transferable structure. A lower XGBoost learning rate matched but did not exceed the best; heavier minimum child weight gave no gain. Next, test whether regularization of rare logistic interactions or a clean category preparation speeds scoring without reducing AUC.

Research at 30: [scikit-learn's logistic documentation](https://scikit-learn.org/stable/modules/linear_model.html) explains that lower `C` means stronger coefficient shrinkage, potentially helpful for the growing set of sparse interactions. Its [OneHotEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html) describes grouping infrequent levels, but this experiment's rule bars count-derived features, so I will use coefficient regularization instead.

## Experiment 31 — exploration: stronger logistic shrinkage

Hypothesis: with route, carrier-origin, and carrier-hour indicators, `C=1` may let sparse coefficients fit 2005 noise. Set logistic `C=0.1` while retaining the same features and blend weight. This tests regularization of the promising interaction model directly.

Result: 0.6890 (+0.0001); keep d79a56c. Training also fell to 1.5 s, though eval remains around 40 s.

## Experiment 32 — follow-up: bracket logistic shrinkage

Hypothesis: if a tenfold decrease in `C` helps slightly, another tenfold decrease to 0.01 may further suppress sparse route and carrier-interaction noise. Hold features and blend weight fixed to test the regularization trend.

Result: 0.6883 (-0.0007); discard 7c0b013. Stronger shrinkage suppresses useful interaction effects; `C=0.1` remains best.

## Experiment 33 — ablation/simplification: direct categorical conversion

Hypothesis: passing the fixed train-fitted levels directly to `pd.Categorical` should treat unseen categories as missing just like the current `where(isin(...))` step, while avoiding a redundant per-row membership scan. Remove that scan; keep only if rounded AUC is equal or better and code is simpler or faster.

Result: 0.6890 (equal), eval 33.8 s versus 40.4 s; keep 36e0681 because it is simpler and materially faster.

## Experiment 34 — exploration: month effect in logistic branch only

Hypothesis: the regularized additive model may capture broad monthly delay shifts that its linear day-of-year and cosine terms miss. Add one-hot Month only for logistic regression, leaving the tree branch exactly as in the best model. The earlier month ablation concerned tree handling, so this tests a different estimator and representation.

Result: 0.6865 (-0.0025); discard bad1485. Broad monthly bins overfit or conflict with smoother seasonal representation even in logistic regression.

## Experiment 35 — follow-up: origin-specific departure hour

Hypothesis: departures later in the day may be especially delay-prone at particular airports because congestion varies by hub. Add an origin-hour one-hot interaction only for the regularized logistic model, following the carrier-hour success but testing a distinct spatial-time relationship. The [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) motivates both geographic and temporal predictors; the interaction is my inference.

Result: 0.6892 (+0.0002); keep 21993e0. Airport-specific time-of-day effects add a small signal, with evaluation time 37.0 s.

## Experiment 36 — exploration: column subsampling in XGBoost

Hypothesis: sampling 80% of input features for each tree may reduce dependence on noisy airport splits and help the tree component generalize, while the logistic branch retains all features. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) cites column subsampling as an overfitting control. This differs from row subsampling, which hurt earlier.

Result: 0.6887 (-0.0005); discard fbf17b7. Keeping all columns in each tree is better at this small feature count.

## Experiment 37 — exploration: stronger tree leaf regularization

Hypothesis: the logistic branch now represents several stable additive interactions, leaving XGBoost free to capture residual nonlinear signal. A stronger `reg_lambda=10` may smooth tree leaf outputs and reduce weak 2005-specific corrections while preserving its three-level structure. [XGBoost parameters](https://xgboost.readthedocs.io/en/release_3.3.0/parameter.html) define lambda as L2 leaf-weight regularization.
