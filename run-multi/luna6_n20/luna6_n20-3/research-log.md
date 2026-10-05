# Research log — oct5

## Baseline

- Commit: `b15ec66`
- Eval AUC: `0.6743`
- Status: keep (baseline)
- Model: starter `XGBClassifier` with 100 trees, depth 6, learning rate 0.1; the existing features are month, day of month, day of week, scheduled departure time, carrier, origin, destination, and distance.
- Run completed successfully in 32.1s. The evaluation harness prepares each evaluation row independently.
- Next: review XGBoost tuning guidance and flight-delay feature research before the first non-baseline experiment.

## Experiment 1 — add directed route category (exploration)

**Hypothesis.** Explicitly represent the directed `(Origin, Dest)` pair as a native categorical feature. The starter gives the learner separate origin and destination features, but a route category lets it group pairs with similar delay behavior directly. `train.csv` has 4,290 distinct directed routes across 283 origins/destinations, so this is a moderate-cardinality feature. Keep all baseline model settings fixed to isolate the feature change.

**Research.** XGBoost's [categorical data guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes category-set partition splits and documents pandas `category` input with `enable_categorical=True`. Its [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) emphasize balancing tree complexity and that preprocessing can be as important as hyperparameter changes. A 2022 flight-delay study reports departure time and carrier as influential predictors ([paper](https://doi.org/10.1016/j.jcmds.2022.100030)); both are already present, motivating a test of origin-destination context. No extra external data is introduced.

**Implementation constraints.** Fit the route category levels from `train` once at module scope; inside `prepare(df)`, derive only the row's route key and map unseen routes to missing. The route itself does not aggregate over `df` or use labels.

**Result.** Eval AUC `0.6667` (commit `fce6a43`, run status `ok`), down from `0.6743`. The 4,290-level route category hurt on the 2006 evaluation data, consistent with route-specific effects being noisy or unstable across years at this sample size. Discarded and reset to the baseline commit. Keep geographic interactions in mind, but next test a more regularized model rather than stacking more sparse categories.

## Experiment 2 — shallower trees (exploration)

**Hypothesis.** Reduce `max_depth` from 6 to 4 while keeping the baseline's 100 estimators, learning rate, and other settings. A shallower tree may reduce variance and improve transfer from 2005 to 2006 after the sparse route category failed. This isolates tree depth rather than changing several regularization knobs at once.

**Research basis.** XGBoost's [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describe depth as a direct model-complexity control and explain that higher complexity can overfit when data support is limited. The same guide identifies sampling and learning rate as other controls; those remain unchanged in this experiment.

**Result.** Eval AUC `0.6789` (commit `8b2207d`, status `ok`), improving over the baseline `0.6743`. Keep. Shallower trees appear to transfer better across years; current best is depth 4 with all original features and other baseline settings.

## Experiment 3 — test intermediate depth 5 (follow-up)

**Hypothesis.** The depth-4 improvement over depth 6 suggests the baseline may be too complex, but depth 4 could have removed useful interactions. Test `max_depth=5` between the two measured settings, keeping every other parameter fixed. This is a targeted capacity bracket motivated by the current best, not a random parameter change.

**Research basis.** The XGBoost [parameter tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frame tree depth as a bias/variance and complexity tradeoff; the observed `0.6789` at depth 4 versus `0.6743` at depth 6 motivates locating a better point on that axis.

**Result.** Eval AUC `0.6777` (commit `3a22022`, status `ok`), below depth 4's `0.6789`; discard and reset. The current depth bracket favors 4 over 5 and 6.

## Experiment 4 — lower learning rate with more trees (follow-up)

**Hypothesis.** Preserve the best depth-4 structure, but lower `learning_rate` from 0.1 to 0.05 and double `n_estimators` from 100 to 200. Smaller steps may produce a smoother additive fit; doubling rounds gives the model more steps to reach comparable training capacity. This follows the XGBoost [tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), which recommends lowering eta while increasing boosting rounds.

**Result.** Eval AUC `0.6800` (commit `4405026`, status `ok`), a new best over `0.6789`. Keep. The lower learning rate with more rounds improved the depth-4 model; current best is depth 4, learning rate 0.05, 200 trees.

## Experiment 5 — row subsampling (follow-up)

**Hypothesis.** Keep the current best model settings and set `subsample=0.8`, sampling 80% of training rows for each tree. This may add useful variance reduction across 200 trees without changing feature availability. Leave column sampling at its default so the row-sampling effect is isolated.

**Research basis.** The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says `subsample` is the training-instance ratio, uses the range `(0, 1]`, and that subsampling can prevent overfitting. The tuning guide also identifies `subsample` as a randomness control.

**Result.** Eval AUC `0.6793` (commit `a063c5e`, status `ok`), 0.0007 below the current best; discard and restore `4405026`. Row sampling at 0.8 did not help this setup.

## Experiment 6 — require more support per child (exploration)

**Hypothesis.** On the best model, raise `min_child_weight` from its default 1 to 5. This makes split growth more conservative by requiring more Hessian weight in each child, which may suppress small leaves that fit noisy 2005-specific patterns. This is a different regularization mechanism from row subsampling, which slightly hurt.

**Research basis.** The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `min_child_weight` as the minimum Hessian sum needed in a child and says larger values make the model more conservative.

**Result.** Eval AUC `0.6799` (commit `4ad189f`, status `ok`), below `0.6800`; discard and restore `4405026`. Stronger child support was effectively neutral but did not improve the printed metric. This is the second consecutive close discard; if the next experiment also misses by less than 0.001, pause for additional research as required.

## Experiment 7 — require loss gain for splits (exploration)

**Hypothesis.** On the kept low-rate/depth-4 model, set `gamma=1` while keeping the remaining parameters fixed. Requiring a nontrivial loss reduction for each split may prune weak, year-specific structure. This tests split-gain regularization, separate from row sampling and child support.

**Research basis.** The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines `gamma` as the minimum loss reduction required for another leaf split and says larger values make the algorithm more conservative. The two preceding regularization experiments were close misses, so this tests a distinct control rather than repeating them.

**Result.** Eval AUC `0.6800` (commit `57ded51`, status `ok`), equal to the best but with an extra parameter and no simplification or speed gain; discard by the keep rule and restore `4405026`. This is the third consecutive close miss, so research a fresh feature direction before continuing.

## Plateau synthesis and fresh research

Depth 4 plus a lower learning rate improved AUC to `0.6800`. A route category hurt; depth 5, row subsampling, child-weight regularization, and split-gain regularization did not improve the current best. This suggests the useful gain so far came from reducing model capacity and shrinkage, while added sparse route signal and simple regularizers have not helped. To move beyond that plateau, research points to a new temporal representation: the scikit-learn [time-related feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains sine/cosine encoding for periodic time features so end and start of the period have no artificial jump. A flight-delay XGBoost study also finds scheduled departure time highly influential ([thesis, feature importance section](https://www.theseus.fi/bitstream/10024/889008/4/Sumay_Valkama_Ana.pdf)). The available training `CRSDepTime` values are valid HHMM times (5 through 2359; no invalid minute fields).

## Experiment 8 — cyclical scheduled departure time (exploration)

**Hypothesis.** Keep raw `CRSDepTime` and add sine/cosine of its parsed minute-of-day angle (period 1,440 minutes). Trees can already split raw time, but the cyclic pair offers a compact representation for smooth within-day effects and proximity across midnight. The test is row-local and uses no fitted statistics or outside data.

**Result.** Eval AUC `0.6803` (commit `d60e858`, status `ok`), improving by 0.0003 over the prior best. Keep. The cyclic time representation gives a small gain; current best retains raw scheduled time plus sine/cosine of minute-of-day.

## Experiment 9 — cyclical day of week (follow-up)

**Hypothesis.** Extend the small win from cyclic departure time to the separate weekly cycle. Add sine/cosine of the `DayOfWeek` code (period 7), preserving its original categorical feature. This may encode proximity around the week boundary and regular weekday traffic patterns. The raw values are strings `c-1` through `c-7`; parse only the row value in `prepare`.

**Research basis.** The scikit-learn [time-related feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) demonstrates sine/cosine transforms with period 7 for weekday and period 24 for hour, noting that the representation removes the artificial gap between cycle endpoints. The current experiment tests only the weekly pair.

**Result.** Eval AUC `0.6803` (commit `36d30c8`, status `ok`), tied with the current best but increased feature work and evaluation time; discard by the keep rule and restore `d60e858`. Weekly cyclic features added no measurable ranking gain.

## Experiment 10 — cyclical month (exploration)

**Hypothesis.** Add sine/cosine of `Month` (period 12) while retaining the original month category and all current best settings. Unlike the failed weekly pair, this encodes annual seasonal continuity, especially the December/January boundary; weather and seasonal travel can make adjacent months share delay patterns. It is a different cycle from the tested weekday feature.

**Research basis.** The scikit-learn [time-related feature engineering example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows a period-12 month transform alongside hour and weekday encodings. Flight-delay research also identifies month/season and scheduled time as relevant ([flight-delay feature study](https://www.theseus.fi/bitstream/10024/889008/4/Sumay_Valkama_Ana.pdf)).

**Result.** Eval AUC `0.6803` (commit `0309879`, status `ok`), tied with the current best but with more feature work and slower evaluation; discard and restore `d60e858`.

## Synthesis after 10 experiments

- Best so far: `0.6803` at `d60e858` (depth 4, 200 trees, learning rate 0.05, raw features plus cyclic departure-time sine/cosine).
- What helped: reducing depth from 6 to 4 and pairing a lower learning rate with more trees produced steady gains; cyclic departure time added a small further gain.
- What did not: the directed route category hurt; depth 5, row subsampling, child-weight and gamma regularization missed the best; weekday/month cyclic pairs tied and slowed row-wise evaluation.
- Current theory: cross-year generalization benefits from conservative trees and a compact representation of daily timing. Sparse pairwise categories and redundant cyclic calendar features add noise or cost without improving ranking.
- Next direction: investigate stable train-fitted airport/carrier delay-rate lookups or coarser departure-time segments. Prefer broad groups with sufficient training support and ensure each evaluation row receives a fixed lookup value, never a statistic of the row-scoring batch.

## Experiment 11 — smoothed origin delay rate (exploration)

**Hypothesis.** Add one numeric lookup, `OriginDelayRate`, estimated from the training labels and mapped by each row's origin. Historical airport propensity may transfer across the one-year split, while native categorical splits may not expose the same smooth ordering with the limited tree budget. Test origin alone before adding any other group.

**Research basis.** A benchmark of categorical encodings reports strong results for regularized target encodings and warns that unregularized means can overfit rare levels ([Pargent et al.](https://arxiv.org/abs/2104.00629)). CatBoost's primary paper also analyzes target leakage from categorical statistics ([NeurIPS 2018](https://proceedings.neurips.cc/paper/2018/hash/14491b756b3a51daac41c24863285549-Abstract.html)). A flight-delay feature-engineering project identifies airport-specific patterns as useful context ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)).

**Implementation.** Fit the origin target-rate lookup once on `train`, shrink each airport rate toward the global rate with smoothing strength 500, and map the fixed result inside `prepare`. Origin support is skewed (median 125, 10th percentile 20); the strong shrinkage limits the influence of any one training row. Only the smoothed rate is exposed as a feature—no group counts or evaluation-batch aggregates. The harness remains the sole AUC evaluation.

**Result.** Eval AUC `0.6804` (commit `6ee3549`, status `ok`), a small improvement over `0.6803`. Keep. The strongly smoothed origin rate appears to add a little transferable airport context despite the low-cardinality model already having origin as a category.

## Experiment 12 — smoothed destination delay rate (follow-up)

**Hypothesis.** Add a train-fitted, strongly smoothed `DestDelayRate` lookup with the same alpha 500 as the origin feature. Destination airport operating conditions and route context may add a signal distinct from the departure airport; the prior origin-rate improvement motivates testing the other endpoint. Keep all other features and model settings fixed.

**Research basis.** The flight-delay feature-engineering project groups airport/location context separately and includes both airport endpoints ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)); the categorical encoding benchmark supports regularized target statistics while warning about rare-level overfit ([Pargent et al.](https://arxiv.org/abs/2104.00629)).

**Result.** Eval AUC `0.6803` (commit `de9c622`, status `ok`), down from the origin-only `0.6804`; discard and restore `6ee3549`. Destination rate did not add useful information on top of origin and cyclic time.

## Experiment 13 — smoothed carrier delay rate (follow-up)

**Hypothesis.** Add a train-fitted `CarrierDelayRate` lookup to the kept origin-rate model, using the same smoothing strength 500. Carrier operating practices may add a stable signal beyond airport effects; this feature uses a different entity than the two airport lookups already tested. All 20 carriers have at least 916 training examples, limiting rare-level noise.

**Research basis.** A flight-delay XGBoost study reports carrier and departure time among influential features ([study](https://doi.org/10.1016/j.jcmds.2022.100030)); the regularized target-encoding benchmark supports smoothed category means and warns against unregularized rare levels ([Pargent et al.](https://arxiv.org/abs/2104.00629)).

**Result.** Eval AUC `0.6804` (commit `965fc0d`, status `ok`), equal to the origin-only best but with an additional lookup and slower evaluation; discard and restore `6ee3549`. Carrier rate did not add complementary signal.

## Experiment 14 — depth 3 on the current best features (follow-up)

**Hypothesis.** Test `max_depth=3` with all current best features and other parameters fixed. Depth 4 beat depth 5/6 on the earlier feature set; checking one shallower setting determines whether the benefit from less capacity continues after adding cyclic time and origin-rate features.

**Research basis.** XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies depth as a complexity control; this continues the targeted depth bracket motivated by observed results.

**Result.** Eval AUC `0.6797` (commit `ee81560`, status `ok`), below depth 4's `0.6804`; discard and restore `6ee3549`. Together with destination and carrier additions, this is three consecutive close discards; research before another change.

## Experiment 15 — categorical departure hour (exploration)

**Hypothesis.** Add `DepHour` as a native categorical feature with 24 possible levels, preserving `CRSDepTime` and its cyclic pair. This allows direct grouping of hourly delay patterns and sharp rush/overnight effects, whereas the cyclic representation is smooth. Use only the hour parsed from each row and levels fitted once on train.

**Research basis.** The UC Berkeley flight-delay feature-engineering project uses departure-time blocks at hourly intervals and reports worsening delays late at night, including a breakdown by carrier ([project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). A separate flight-delay study also includes departure-hour bins ([study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/)). This test adds only hour, not the higher-cardinality carrier-hour interaction.

**Result.** Eval AUC `0.6797` (commit `dcfd768`, status `ok`), below the best; discard and restore `6ee3549`. Four experiments after the origin-rate improvement have now missed narrowly. Research a more targeted interaction before continuing.

## Plateau research and Experiment 16 — carrier by daypart

**Research.** Hsiao and Hansen's U.S. airline delay analysis reports time-of-day heterogeneity: the measured delay impact of queuing was much higher in the morning than afternoon/evening ([Transportation Research Record, 2006](https://doi.org/10.3141/1951-13)). The flight-delay engineering project reports that delays worsen late at night and that this pattern differs by carrier ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). XGBoost trees can learn interactions, but its docs caution that deeper paths may capture spurious interactions; an explicit coarse interaction is a focused, regularized test ([XGBoost interaction guidance](https://xgboost.readthedocs.io/en/release_3.3.0/tutorials/feature_interaction_constraint.html)).

**Hypothesis.** The global 24-level hour category hurt, but airport/carrier-specific timing may still matter. Add `CarrierDaypart`, a categorical interaction with four row-local periods: night (21:00–04:59), morning (05:00–11:59), afternoon (12:00–17:59), evening (18:00–20:59). This gives at most 80 categories instead of 401 observed carrier-hour pairs and leaves all existing features/settings fixed.

**Result.** Eval AUC `0.6801` (commit `548873a`, status `ok`), below the kept `0.6804`; discard and restore `6ee3549`. Training/evaluation completed despite a pandas warning for unseen carrier-daypart combinations; those become missing categories. The coarse interaction did not help.

## Experiment 17 — lighter origin-rate smoothing (follow-up)

**Hypothesis.** The origin-rate lookup improved AUC with smoothing strength 500, but this shrinks the empirical airport mean strongly (e.g. a median-support origin has weight about 20%). Test strength 200 to let supported airports contribute more while retaining a global-prior shrinkage term. Keep the same one lookup and all model settings fixed.

**Research basis.** The target-encoding benchmark describes smoothing as the way to shrink noisy category effects toward the global mean and identifies regularization strength as an important design choice ([Pargent et al.](https://arxiv.org/abs/2104.00629)). The training-only lookup remains fixed for every row; no counts are exposed as features.

**Result.** Eval AUC `0.6800` (commit `ce5366b`, status `ok`), below the smoothing-500 result; discard and restore `6ee3549`. Lighter smoothing appears to increase noise or self-influence in rare-origin rates, so the next test checks stronger shrinkage.

## Experiment 18 — stronger origin-rate smoothing (follow-up)

**Hypothesis.** Test smoothing strength 1000 against the kept 500 after strength 200 lowered AUC. Stronger shrinkage may further reduce noisy small-airport estimates while preserving the largest airports' signal. No other features or model settings change.

**Result.** Eval AUC `0.6797` (commit `87914ba`, status `ok`), below the smoothing-500 best; discard and restore `6ee3549`. Very strong shrinkage also reduced the origin signal. Three experiments since the prior research pause have missed; investigate an ensemble or other new model direction before continuing.

## Plateau research and Experiment 19 — soft-vote two boosting paths

**Research.** Scikit-learn documents soft voting as averaging class probabilities and uses uniform weights by default ([VotingClassifier documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html)). A flight-delay stacking study on Boston Logan data reports improved accuracy and stability from combining classifiers ([Yi et al., 2021](https://onlinelibrary.wiley.com/doi/10.1155/2021/4292778)).

**Hypothesis.** Probability averaging between the current best (depth 4, 200 trees, learning rate 0.05) and the previous 100-tree, learning-rate-0.1 depth-4 model may smooth model-specific ranking noise. Use a 3:1 weight favoring the current best, since the 100-tree model was weaker alone, and the same features for both estimators. This tests complementary boosting trajectories without adding an external library or changing evaluation.

**Result.** Eval AUC `0.6806` (commit `51b2f09`, status `ok`), a new best. Keep. The soft vote improved the single 200-tree path by 0.0002; the alternate trajectory adds complementary ranking signal. Next compare uniform probability weights against the 3:1 blend.

## Experiment 20 — equal soft-vote weights (follow-up)

**Hypothesis.** Compare `[1, 1]` with the kept `[3, 1]` weights. The scikit-learn [VotingClassifier docs](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) use uniform weights by default; giving the lower-scoring but complementary model equal influence may improve the ensemble ranking, or may dilute the stronger model. No training or feature settings change.

**Result.** Eval AUC `0.6805` (commit `dda8278`, status `ok`), just below the kept 3:1 result; discard and restore `51b2f09`.

## Synthesis after 20 experiments

- Best so far: `0.6806` at commit `51b2f09`, a 3:1 soft vote of the 200-tree/0.05 and 100-tree/0.1 depth-4 XGBoost paths. Current features are the starter inputs, cyclic departure-time sine/cosine, and a strongly smoothed train-fitted origin delay rate.
- Earlier improvements: depth 4 beat the depth-6 baseline, and a lower learning rate with more trees improved again. Cyclic departure time and the smoothed origin-rate lookup added small gains. Soft voting added a further 0.0002.
- What did not help: directed route category, depth 5/3, row subsampling alone, gamma/child-weight controls, weekday/month cycles, global hour category, carrier-daypart interaction, destination/carrier rate additions, and stronger/weaker origin smoothing. Uniform voting was slightly worse than 3:1.
- Current theory: a modestly regularized boost model carries most of the signal; scheduled-time cyclic structure and broad origin history add small transfer across years; a lightly weighted alternate fit can smooth ranking noise. High-dimensional or overly specific pair features have not generalized.
- Next direction: research an alternative diversity source for the soft-vote ensemble and test a materially different second-model fit rather than adding more redundant calendar features.

## Experiment 21 — stochastic secondary booster (follow-up)

**Hypothesis.** Preserve the full-data best model as the primary estimator. Change only the secondary estimator to the same 200-tree, depth-4, learning-rate-0.05 configuration with `subsample=0.8` and a different seed, retaining 3:1 soft-vote weights. Random row samples may lower correlation between the two predictions enough to improve the blend, even though the standalone subsampled model was weaker.

**Research basis.** Friedman's [stochastic gradient boosting paper](https://doi.org/10.1016/S0167-9473(01)00065-2) describes random subsampling at each boosting iteration as improving robustness to overcapacity. Breiman's [Random Forests paper](https://doi.org/10.1023/A:1010933404324) relates ensemble generalization to both individual strength and predictor correlation. The previous subsampling run tested one model alone; this experiment tests its diversity in the kept soft vote.

**Result.** Eval AUC `0.6808` (commit `50405ab`, status `ok`), a new best. Keep. The subsampled secondary booster adds complementary ranking signal and improves the prior ensemble by 0.0002.

## Experiment 22 — equal weights for the stochastic pair (follow-up)

**Hypothesis.** Compare `[1, 1]` with the kept `[3, 1]` weights for the full-data and subsampled 200-tree models. Unlike the earlier equal-weight trial, both members now have matching capacity, and the secondary model's improvement comes from sampling diversity; a larger share may help the ranking.

**Result.** Eval AUC `0.6809` (commit `7ba26a8`, status `ok`), a new best. Keep. Equal weights improved the stochastic pair by another 0.0001.

## Experiment 23 — stronger secondary subsampling (follow-up)

**Hypothesis.** With equal weights, test `subsample=0.6` for the secondary booster while keeping the primary full-data model fixed. More row randomization may lower prediction correlation further; it may also weaken the secondary model. This directly probes the strength/correlation balance behind the `0.8` result.

**Research basis.** XGBoost's [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) notes that `subsample=0.5` randomly trains each iteration on half the data and can prevent overfitting. Breiman's [forest analysis](https://doi.org/10.1023/A:1010933404324) explains the tradeoff between predictor strength and correlation in ensembles.

**Result.** Eval AUC `0.6809` (commit `ca2e0c1`, status `ok`), tied with the kept `0.8` secondary model but no simpler/faster; discard and restore `7ba26a8`. The 0.6 and 0.8 settings are tied at four-decimal precision.

## Experiment 24 — lighter secondary subsampling (follow-up)

**Hypothesis.** Test secondary `subsample=0.9`, keeping equal weights and the primary model fixed. The 0.6 and 0.8 settings tied at four decimals; a milder sample may retain more tree strength while still decorrelating the two fits.

**Result.** Eval AUC `0.6808` (commit `f7e1bb7`, status `ok`), below the kept 0.8 model; discard and restore `7ba26a8`. The 0.9 sample appears to retain too much correlation without enough benefit.

## Experiment 25 — column sampling in the secondary booster (exploration)

**Hypothesis.** Keep the 0.8 row-sampled secondary model and additionally set `colsample_bytree=0.8` for it. Randomly varying which features each tree sees may diversify its predictions further from the full-data primary model; with 11 input columns, 0.8 is a mild reduction. The XGBoost [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as per-tree column sampling in `(0,1]`.

**Result.** Eval AUC `0.6810` (commit `b456438`, status `ok`), a new best. Keep. Adding mild column sampling to the stochastic secondary path improved over row sampling alone by 0.0001.

## Experiment 26 — stronger secondary column sampling (follow-up)

**Hypothesis.** Test `colsample_bytree=0.6` in the row-sampled secondary booster after 0.8 produced a small gain. More feature randomization could reduce correlation with the full-data model; it could also omit too many useful predictors. Keep all other settings fixed.

**Result.** Eval AUC `0.6814` (commit `b063047`, status `ok`), a new best by 0.0004. Keep. Stronger column sampling in the stochastic secondary model improved ranking while the full-data model remained unchanged.

## Experiment 27 — stronger secondary column sampling (follow-up)

**Hypothesis.** Test `colsample_bytree=0.4` in the row-sampled secondary booster after 0.6 improved on 0.8. Further reducing the per-tree feature subset could diversify the ensemble more, though it may omit useful predictors. Keep all other settings fixed.

**Result.** Eval AUC `0.6820` (commit `9c46a06`, status `ok`), a new best by 0.0006. Keep. With this configuration, the stronger feature randomization improved again.

## Experiment 28 — stronger secondary column sampling (follow-up)

**Hypothesis.** Test `colsample_bytree=0.3` in the secondary booster after 0.4 improved the best. This selects roughly three of the eleven features per tree, probing whether additional diversity helps or removes too much signal. All other settings remain fixed.

**Result.** Eval AUC `0.6817` (commit `2b4a23e`, status `ok`), below the kept `0.4` model; discard and restore `9c46a06`. Further feature subsampling lost useful signal.

## Final summary

- Best kept checkpoint: commit `9c46a06`, Eval AUC `0.6820` (baseline `0.6743`, gain `0.0077`).
- The final model uses a 200-tree, depth-4, learning-rate-0.05 full-data XGBoost model and an equal-weight soft-vote partner with `subsample=0.8` and `colsample_bytree=0.4`.
- The strongest gains came from reducing tree depth, lowering the learning rate while increasing tree count, adding cyclic scheduled departure time and a smoothed origin delay-rate feature, then ensembling a row- and column-sampled partner.
- Column-sampling sweep for the secondary model: 0.8 → `0.6810`, 0.6 → `0.6814`, 0.4 → `0.6820`, 0.3 → `0.6817`. Keep 0.4.
- All experiment scores and keep/discard decisions are recorded in `output/results.tsv`. The final unrun weight probe was reverted when the harness reached its two-minute stop threshold.
