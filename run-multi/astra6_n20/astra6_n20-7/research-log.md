# Experiment oct6

## Setup — 2026-10-06

- Branch: `oct6`, created directly from the current HEAD, `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist. Inspected only the training data: 200,000 rows, 9 columns, 100,000 examples per class, and no missing values.
- Verified imports: Python 3.14.4, pandas 3.0.6, NumPy 2.5.3, XGBoost 3.4.1, scikit-learn 1.9.1, cloudpickle 3.1.2. Eight CPUs are available.
- Initialized `output/results.tsv` with its four-column header.
- Baseline code is unchanged. No models have been trained and the experiment clock has not started.

## Next steps after confirmation

1. Start the one-hour clock with `python3 harness.py start` as the first action.
2. Run the unchanged baseline through `python3 harness.py run`, redirecting output to `output/run.log`, and record its result.
3. Research primary sources before designing the first non-baseline experiment.
4. Follow the experiment, logging, keep/discard, research, and wrap-up rules in `program.md`.

## Baseline — b15ec66

- Eval AUC: **0.6743**; keep. Model fitting 0.6s; harness training 1.5s; evaluation 31.2s.
- Original 100 trees, depth 6, learning rate 0.1, native categorical features.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): balance capacity and regularization; lower learning rates need more rounds.
- [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): partition-based splits group categories; keep encoding consistent during inference.
- [AWS XGBoost tuning ranges](https://docs.aws.amazon.com/sagemaker/latest/dg/xgboost-tuning.html): broad ranges include depth 0–10, min_child_weight 0–120, and 1–4000 rounds; use these as boundaries, not a blind grid.
- [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): search excerpt emphasizes airport context. Full page returned 403, so treat this as a lead rather than verified methodological evidence.
- Training-only inspection: month/day fields are strings prefixed c-; 20 carriers and 283 airports per endpoint. Scheduled time is HHMM.

## Experiment 1 — more boosting rounds

- Classification: follow-up to baseline.
- Hypothesis: 100 trees underfit useful interactions; increase only n_estimators to 300 at learning rate 0.1.
- Source: XGBoost tuning guide above.

- Result: b3f5d13, Eval AUC **0.6678**, discard (−0.0065). Model fitting 1.7s; evaluation 30.9s. More rounds markedly hurt transfer from 2005 to 2006; regularization and less specific calendar features deserve priority.

## Additional feature research

- [Scikit-learn time feature engineering](https://scikit-learn.org/1.8/auto_examples/applications/plot_cyclical_feature_engineering.html): compare categorical, ordered, and periodic time representations; trees already handle nonlinear numeric relationships, so extra cyclic features require empirical justification.
- [BTS reporting notes](https://transtats.bts.gov/ONTIME/): scheduled times are local 24-hour clock values; HP and US begin reporting jointly as US in January 2006. A train-only HP→US harmonization is a potential way to reduce carrier drift.

## Experiment 2 — simplify categorical preparation

- Classification: ablation/simplification of baseline.
- Hypothesis: construct the feature frame once and reuse training-fitted categorical dtypes; remove redundant membership filtering because pandas categoricals encode unknown levels as missing. Same model/features should give the same AUC, with faster row-wise evaluation.
- Source: [pandas Categorical API](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html).

- Result: 029705b, Eval AUC **0.6743**, keep on equal AUC and much faster code. Evaluation fell to 7.7s (harness 7.9s); total run 9.3s. Pandas warns about unknown categories but correctly maps them to missing in this installed version.

## Experiment 3 — remove day-of-month

- Classification: ablation/simplification.
- Hypothesis: categorical day-of-month encourages memorization of 2005 calendar/weather conditions that do not repeat in 2006. Training delay rates range from 0.458 to 0.560 by day-of-month; retain month and weekday, which have more plausible recurring meaning.
- Motivation: extra boosting rounds overfit badly in experiment 1. Temporal representation research above supports treating calendar components deliberately; transfer rationale is our inference.

- Result: 53f3a8d, Eval AUC **0.6759**, keep (+0.0016). Evaluation 7.1s; total run 8.7s. Removing day-of-month helps modestly; it was not the sole source of overfitting.
- Baseline artifact inspection: scheduled departure time has by far the highest mean split gain. Baseline uses categorical partitioning (one-hot threshold 4, category split threshold 64), min_child_weight 1, and lambda 1.

## Experiment 4 — shallower trees

- Classification: follow-up to evidence of overfitting.
- Hypothesis: reducing max_depth from 6 to 4 while keeping 100 rounds and eta 0.1 will suppress fragile high-order interactions and improve transfer.
- Source: [XGBoost tree parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster).

- Result: 9bd4174, Eval AUC **0.6804**, keep (+0.0045). Total run 8.3s. Shallower interactions are much more robust.

## Experiment 5 — capacity of the shallower model

- Classification: follow-up to experiment 4.
- Hypothesis: with depth 4 instead of 6, additional rounds can recover useful additive structure without the earlier depth-6 overfit; test 300 rounds at eta 0.1.
- Difference from experiment 1: fewer interactions per tree and no day-of-month, both supported by intervening gains. This tests whether boosting duration depends on the improved regularization.

- Result: bcc6d6d, Eval AUC **0.6771**, discard (−0.0033). Even depth-4 trees lose transfer performance with more boosting.

## Experiment 6 — regularize categorical partitions

- Classification: exploration of categorical split regularization.
- Hypothesis: the default max_cat_threshold=64 allows overly flexible partitions of hundreds of airports. Reduce it to 16, keeping the best 100-round depth-4 model.
- Source: [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature), which describes this as a guard against overfitting.
- Research lead: [sklearn TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) stresses cross-fitting; do not introduce naive high-cardinality target means without addressing leakage.

- Result: 804ff74, Eval AUC **0.6774**, discard (−0.0030). Restricting categorical partitions removed useful signal; revert to threshold 64.

## Experiment 7 — month ablation

- Classification: ablation/simplification.
- Hypothesis: training monthly delay rates vary sharply (roughly 0.40–0.59), some from year-specific weather rather than recurring seasonality. Remove Month to test its net transfer value, motivated by the successful day-of-month ablation.

- Result: 00d9ae4, Eval AUC **0.6829**, keep (+0.0025). Month also hurts temporal transfer at this capacity. Total run 7.4s.

## Experiment 8 — broad seasonal feature

- Classification: exploration of a coarser temporal representation.
- Hypothesis: winter/spring/summer/autumn may retain stable seasonality while avoiding individual month-specific conditions. Add a four-level Season derived deterministically from Month; do not restore Month or day-of-month.
- Source: [sklearn time-related feature engineering](https://scikit-learn.org/1.8/auto_examples/applications/plot_cyclical_feature_engineering.html); coarsening is our inference from experiments 3 and 7.

- Result: 6496aa1, Eval AUC **0.6808**, discard (−0.0021). Even coarse seasons fail to improve this cross-year transfer; leave them out.

## Experiment 9 — harmonize carrier merger

- Classification: exploration using domain research.
- Hypothesis: merge HP into US during training preparation to match the January 2006 reporting transition, improving predictions on the combined carrier.
- Source: [BTS on-time reporting notes](https://transtats.bts.gov/ONTIME/), opened and verified. The mapping is static known business metadata; no extra dataset is read.

- Result: dec4d13, Eval AUC **0.6830**, keep (+0.0001 at harness precision). Small gain; avoid overstating its reliability. Total run 7.5s.
- Saved-artifact check: prepare(batch) equals concatenated prepare(single row) for 26 training rows; labels also agree.

## Experiment 10 — minimum leaf support

- Classification: follow-up regularization.
- Hypothesis: min_child_weight=50 (from 1) will prevent low-support leaves while preserving broad categorical partitions, unlike the failed threshold restriction in experiment 6.
- Source: XGBoost tree parameter reference, previously read. Keep depth 4 and 100 rounds fixed to isolate this effect.

- Result: 4596fe1, Eval AUC **0.6832**, keep (+0.0002). Leaf support helps slightly. Total run 7.5s.

## Synthesis after 10 experiments

- Best: **0.6832**, commit **4596fe1**, compared with baseline 0.6743 (+0.0089).
- Clear gains: shallower trees; removal of day-of-month and month. The latter includes a failed attempt to restore four seasons.
- Small gains: carrier reporting harmonization and stronger minimum leaf support.
- Failures: tripling rounds at both depths 6 and 4; overly restricting categorical partitions.
- Preparation simplification preserved AUC and reduced evaluation from about 31s to 6–8s.
- Current theory: temporal distribution shift makes exact calendar effects unreliable; persistent airport/carrier/time structure carries most transferable signal. Control interaction complexity, but retain the ability to pool categorical levels.
- Next: compare one-hot split behavior, stable route/schedule features, and stochastic averaging. Revisit boosting duration only after a substantial feature or regularization change.

## Research refresh after 10 experiments

- [XGBoost categorical splitting RFC](https://github.com/dmlc/xgboost/issues/12130): adaptive category ordering can exaggerate split gains. This is a proposal, not an available implemented option; test existing one-hot splitting instead.
- [Feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html): restrict combinations to reduce spurious interactions; candidate for weekday effects later.
- [Monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html): a possible regularizer, but departure delays need not rise all the way through midnight, so inspect training pattern first.
- [Boosted random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html): num_parallel_tree combines averaging within each round with boosting between rounds.

## Experiment 11 — one-hot categorical splitting

- Classification: exploration of a different categorical split strategy.
- Hypothesis: one-hot splits avoid adaptive large airport groups and may support more boosting without transfer loss. Set max_cat_to_onehot=1024, 500 rounds, eta 0.05; retain depth 4 and min_child_weight 50.
- More rounds/smaller steps compensate for the reduced expressiveness per categorical split. This is distinct from merely increasing rounds on the partition model.
- Source: categorical RFC and XGBoost categorical tutorial above.

- Result: 7475247, Eval AUC **0.6826**, discard (−0.0006). One-hot is competitive but does not beat partitioning with present regularization.
- Training-only hourly delay rates rise from about 0.19 at 05–06h to 0.65 at 20h, then fall at 22–23h. A global monotonic constraint would contradict the late-night pattern; defer it.

## Experiment 12 — route-relative departure time

- Classification: exploration of schedule context features.
- Hypothesis: departure minutes relative to the route's median departure time captures schedule position that shallow trees cannot easily infer from separate airport features.
- Fit route medians only on train, then perform row-local lookups in prepare. Unknown routes get NaN. No frequency/count features.
- Sources: program.md explicitly illustrates this permissible lookup design; sklearn temporal feature engineering research informs the schedule representation.

- Result: a233875, Eval AUC **0.6830**, discard (−0.0002). Feature correctness checked on 26 training rows: batch and single-row preparation agree. The schedule-context feature does not improve the metric in this form.

## Experiment 13 — boosted random forests

- Classification: exploration of stochastic averaging.
- Hypothesis: four parallel trees per boosting round, with subsample=0.8 and colsample_bynode=0.9, will average noisy category decisions while retaining the best 100-round duration.
- Source: [XGBoost random forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). This adds averaging within rounds rather than the extra sequential correction that previously overfit.

- Result: 9f61a4c, Eval AUC **0.6833**, keep (+0.0001). Modest improvement from stochastic averaging. Harness training 2.7s, total run 9.2s.

## Experiment 14 — distance-derived airport geometry

- Classification: exploration of an unsupervised geographic representation.
- Hypothesis: continuous airport coordinates inferred from route distances let shallow trees share regional patterns across airports, while categorical airport identities retain local effects.
- Fit an undirected graph of median route distances using train only, complete missing distances by shortest paths, then classical multidimensional scaling to three axes. Add three coordinates for each endpoint. No external coordinates, target labels, or frequency/count features enter the geometry.
- Sources: [sklearn manifold learning](https://scikit-learn.org/1.8/modules/manifold.html), [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html). This adapts the Isomap distance-embedding idea to the observed route graph.

- Result: b42688b, Eval AUC **0.6832**, discard (−0.0001). Geometry was used by the model but did not improve transfer. Saved preparation passed batch/single-row invariance. Total run 10.5s.

## Experiment 15 — boosting after removing calendar drift

- Classification: follow-up to the improved feature/regularization design.
- Hypothesis: 300 rounds may now fit stable airport and schedule structure because Month is absent, min_child_weight is 50, and each round averages randomized trees.
- Difference from experiment 5: that failed longer model still included Month and had neither leaf regularization nor averaging. The substantial intervening changes justify revisiting duration.

- Result: f810db2, Eval AUC **0.6819**, discard (−0.0014). Longer boosting still overfits after calendar removal and stochastic averaging. The preferred short boosting horizon is robust across these interventions.

## Experiment 16 — carrier–origin interaction

- Classification: exploration of a categorical interaction feature.
- Hypothesis: airline-specific airport operations are stable across years but hard to isolate with shallow trees; a CarrierOrigin category exposes that interaction in one split.
- Build levels from training data after HP→US harmonization. Unknown pairs map to missing; do not use frequencies or labels to construct levels.
- Source: XGBoost categorical tutorial (category partitions) and feature-interaction constraint tutorial (tree paths encode interactions), previously researched.

- Result: a713052, Eval AUC **0.6780**, discard (−0.0053). High-cardinality adaptive interaction splits sharply overfit. Prefer regularized numeric summaries if revisiting these interactions.

## Experiment 17 — date-excluded, smoothed delay-rate lookups

- Classification: exploration of regularized target statistics.
- Hypothesis: numeric rates for Origin, Dest, CarrierOrigin, and Route pool operational signal without the adaptive partition explosion in experiment 16.
- Fit each lookup only from training labels, excluding all rows with the query row's month/day. Shrink toward the fixed balanced-class prior 0.5 with strength 100. This algebraically excludes the row's own target and same-day conditions. Apply the exact same lookup rule during training and inference.
- No separate models, cross-validation runs, or alternative scores are used. All 200K rows still train the one final XGBoost model. Counts are used only internally to calculate smoothed means; no count or frequency is a feature.
- Sources: [CatBoost paper](https://arxiv.org/abs/1706.09516), [sklearn TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html). The date-group exclusion is our adaptation; not a claim to implement CatBoost's ordered boosting.

- Result: a19f18d, Eval AUC **0.6720**, discard (−0.0113). This encoding design is harmful. Date-excluded statistics may still carry unstable within-group variation; withholding the row's label alone is not enough to guarantee robust target encoding. Prefer the much simpler kept model.

## Experiment 18 — coarser numeric histogram bins

- Classification: exploration of numerical split regularization.
- Hypothesis: max_bin=64 instead of 256 smooths fragile minute-level departure-time and distance splits while retaining categorical identities. Keep the 100-round, depth-4 averaged model unchanged otherwise.
- Source: XGBoost parameter reference, max_bin section, re-read before this experiment.

- Result: a375971, Eval AUC **0.6832**, discard (−0.0001). Coarse bins do not beat the incumbent; revert to the default 256.

## Experiment 19 — shallower additive correction

- Classification: follow-up to the earlier successful depth reduction.
- Hypothesis: depth 3 with 200 rounds allocates capacity to more low-order corrections rather than depth-4 interactions. Doubling rounds compensates roughly for halving the maximum leaves per tree; retain stochastic averaging and min_child_weight 50.
- This tests structure at a comparable leaf budget, not another simple duration increase.

- Result: a6f16bf, Eval AUC **0.6837**, keep (+0.0004). Lower-order corrections with a comparable leaf budget improve transfer. Harness training 4.0s; total run 10.5s.

## Experiment 20 — constrained daily delay shape

- Classification: exploration of a structured time feature and monotonic regularization.
- Hypothesis: replacing raw HHMM by two pieces of a clock starting at 05:00, increasing until 20:30 and then decreasing overnight, removes noise while respecting the training-only hourly pattern.
- DaytimeProgress is clipped at 930 minutes and constrained increasing; LateNightProgress starts thereafter and is constrained decreasing. The pair retains time ordering within each segment and is computed entirely from each row.
- Source: [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html); chosen turning point is an inference from training delay rates, not evaluation data.

- Result: ee567b6, Eval AUC **0.6835**, discard (−0.0002). The daily-shape constraint is plausible but slightly too restrictive at this configuration.

## Synthesis after 20 experiments

- Best: **0.6837**, commit **a6f16bf**, versus baseline 0.6743 (+0.0094).
- New useful direction: depth 3 with 200 rounds, retaining leaf support and within-round averaging. Averaging alone was a small gain.
- Near misses: one-hot categories, route-relative time, airport distance geometry, coarser bins, and monotonic clock shape. None meets the strict keep rule.
- Clear failures: explicit CarrierOrigin categories, date-excluded target-rate features, and longer depth-4 boosting even without calendar features.
- Current theory: low-order airport/carrier/time effects transfer; fitting sparse groups or complicated relationships mostly adds temporal variance. Numeric target statistics did not solve that problem here.
- Next: explore training weights to remove global calendar nuisance effects, restrict weekday interactions, and test simple schedule components. Preserve a simple final candidate unless complexity earns an AUC gain.

## Research refresh after 20 experiments

- [Importance weighting under label shift](https://arxiv.org/abs/2011.14251): reweighting can address distribution shifts when its assumptions hold. We cannot estimate the target distribution here and will not inspect evaluation rows; use calendar balancing only as an explicit regularization hypothesis.
- [XGBoost intercept and offsets](https://xgboost.readthedocs.io/en/stable/tutorials/intercept.html): base_margin supports per-row offsets, while base_score is a global intercept. A possible alternative is removing training-only calendar nuisance effects via an offset.
- XGBoost Python API confirms sample_weight is a training input; the evaluation path remains untouched.

## Experiment 21 — balance labels within training months

- Classification: exploration of training-loss weighting.
- Hypothesis: even after removing Month from model inputs, seasonal label imbalance can distort airport/carrier effects. Weight each class inversely to its training monthly class proportion so each month contributes equally weighted positive and negative labels.
- All rows remain in model fitting. Weights are learned only from train labels and are not inference features. This does not claim that the unknown evaluation monthly proportions are 50/50.

- Result: 45fe7d3, Eval AUC **0.6839**, keep (+0.0002). Monthly nuisance balancing gives a small gain. Total run 11.5s.

## Experiment 22 — date balancing while preserving weekdays

- Classification: follow-up to monthly weighting.
- Hypothesis: daily weather shocks still distort stable features. Reweight labels within each month/day to the overall training delay proportion for that weekday, preserving the weekday signal while removing date-specific prevalence.
- Difference from monthly balancing: finer nuisance removal, but deliberately do not flatten the recurring weekday effect. No dates or weights enter prediction features.

- Result: 01243cc, Eval AUC **0.6834**, discard (−0.0005). Finer date balancing removes too much signal or adds weight variance; monthly balancing remains best.

## Experiment 23 — additive weekday effect

- Classification: exploration of interaction constraints.
- Hypothesis: weekday's general business/travel rhythm transfers, while weekday×airport/carrier interactions may reflect incidental 2005 conditions. Put DayOfWeek in its own interaction group and allow the other five features to interact freely.
- Source: [XGBoost feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html), read in the previous research refresh. Use disjoint groups to make the restriction unambiguous.

- Result: 7135af7, Eval AUC **0.6828**, discard (−0.0011). Weekday interactions contain useful signal; restore them.

## Experiment 24 — blend categorical split strategies

- Classification: follow-up to the near-miss one-hot model from experiment 11.
- Hypothesis: a 75% weight on the best partition model and 25% on a one-hot model reduces strategy-specific errors. Both are trained fresh on train with the kept monthly loss weights; no extra evaluation or external data.
- The second model matches experiment 11's 500 rounds, depth 4, eta 0.05, min_child_weight 50, one-hot threshold 1024. It differs structurally from the incumbent's depth-3 averaged partitions.
- Source: [sklearn soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html). A small serializable wrapper averages probabilities; the harness still performs the only scoring.

- Result: 7fb6983, Eval AUC **0.6855**, keep (+0.0016). Complementary categorical strategies produce the first larger gain since calendar/depth simplification. Harness training 5.3s; total run 11.9s.

## Experiment 25 — one-hot component ablation

- Classification: ablation/simplification of a promising blend.
- Hypothesis: the one-hot model may account for most of the gain under monthly weighting; evaluate it alone and remove the partition model/wrapper if it matches or improves the blend.
- This differs from experiment 11 through monthly training weights, whose interaction with split strategy has not yet been isolated.

- Result: a9b8f71, Eval AUC **0.6826**, discard (−0.0029). The weaker component adds value through complementary errors rather than superior standalone accuracy.

## Experiment 26 — equal blend weights

- Classification: follow-up to the blend and its component ablation.
- Hypothesis: equal weighting may further exploit error diversity; compare 50/50 with 75/25 while keeping both trained component configurations fixed. A tied score alone will not justify keeping a coefficient-only change.

- Result: 6740b54, Eval AUC **0.6859**, keep (+0.0004). Equal weighting improves on 75/25 despite the secondary's lower standalone AUC.

## Experiment 27 — minute-of-hour schedule feature

- Classification: exploration of a simple schedule component.
- Hypothesis: the minute component of HHMM may capture recurring scheduling conventions that are difficult to share across hours with raw HHMM alone. Add DepartureMinute=CRSDepTime%100 to both components.
- Source: BTS confirms local 24-hour time format; the predictive rationale is our hypothesis. This feature is purely row-local and uses no fitted statistics.

- Result: 4b8e8fb, Eval AUC **0.6860**, keep (+0.0001). Minute-of-hour contributes a small gain. Total run 13.0s.

## Experiment 28 — geometry with complementary categorical models

- Classification: follow-up combining the geometry near miss with the successful ensemble.
- Hypothesis: numeric geography supplies regional pooling that a one-hot split cannot do cheaply, so the geometry from experiment 14 may help the blended model even though it did not improve the partition-only model.
- Reuse the same train-only distance graph and three-dimensional embedding, avoiding new arbitrary representation choices. Both model components receive the coordinates.

- Result: b91276e, Eval AUC **0.6866**, keep (+0.0006). Geometry helps in combination with categorical strategy diversity, even though it failed alone. Total run 14.2s.

## Experiment 29 — reduce geometry to two axes

- Classification: ablation/simplification of the successful geometry blend.
- Hypothesis: the third coordinate mostly captures small embedding distortions; retain only the two leading axes to simplify the feature space while preserving regional relationships.
- Motivated by the weak third-axis gains in the earlier artifact inspection, not a fresh arbitrary embedding variant.

- Result: df32702, Eval AUC **0.6866**, keep on equal AUC and a smaller feature space (four geographic features instead of six). Total run 14.1s.

## Experiment 30 — pairwise ranking loss

- Classification: exploration of a different training objective.
- Hypothesis: pairwise logistic ranking loss more directly learns delayed-before-on-time ordering. Form comparison groups by training month to avoid rewarding month-level prevalence, consistent with the useful weighting idea.
- Train one XGBRanker with 200 depth-3 rounds, eta 0.1, min_child_weight 200, four sampled pairs per row, and no LambdaRank gradient normalization. Use subsample 0.8 and node column sampling 0.9. The larger child weight accounts approximately for the larger pairwise Hessian scale.
- Replace the blend for this experiment. A sigmoid of ranking scores supplies the harness's required two-column output without changing ordering. No extra metric, evaluation, or validation set.
- Source: [XGBoost learning to rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html), read before implementation.

- Result: d961d2e, Eval AUC **0.6824**, discard (−0.0042). Pairwise training is efficient (3.2s harness training) but does not outperform the two-model logistic ensemble in this configuration.

## Synthesis after 30 experiments

- Best: **0.6866**, commit **df32702**, +0.0123 versus baseline.
- Strongest new finding: partition-based and one-hot models have complementary errors; their equal blend outperforms either component. One-hot alone remained at 0.6826.
- The geometry near miss became useful inside the blend; two axes matched three with fewer features. Minute-of-hour helped marginally.
- Monthly class balancing helped slightly; daily balancing and additive-only weekday constraints hurt. Preserve weekday interactions.
- Direct pairwise ranking did not replace the blend successfully; no extra validation metric was used.
- Next: tune the structurally weaker one-hot component's capacity, strengthen smooth regularization, and examine more targeted calendar effects rather than restoring raw month/day categories. Also verify and simplify inference where possible.

## Research refresh after 30 experiments

- [DART paper](https://arxiv.org/abs/1505.01866): tree dropout is an alternative regularization direction, though repeated prediction during fitting may be costly under the training limit.
- XGBoost parameter reference revisited for L2 and split-gain penalties; these have not yet been tested directly.
- BTS has holiday travel-period definitions, suggesting targeted holiday features as a possible alternative to the failed raw calendar inputs. Do not use holiday performance tables or external flight records as features.

## Experiment 31 — increase only the one-hot component depth

- Classification: follow-up to the successful complementary-strategy ensemble.
- Hypothesis: one-hot splits are less expressive than grouped categorical splits; depth 5 instead of 4 may allow the secondary model to learn airport/time interactions now that geographic pooling is available. Hold the primary model, number of rounds, learning rate, and weights fixed.

- Result: f7dc1a3, Eval AUC **0.6872**, keep (+0.0006). Extra depth is useful in the less-adaptive one-hot component. Total run 15.2s.

## Experiment 32 — targeted holiday flags

- Classification: exploration of domain-specific calendar semantics.
- Hypothesis: actual holidays and their nearby travel windows transfer across years more reliably than raw date categories. Add two row-local indicators: HolidayDay and HolidayTravelWindow.
- Thanksgiving is derived as the fourth Thursday of November from month, day, and weekday. Include Christmas, New Year's Day, and July 4 as fixed-date holidays; broad windows are a modeling hypothesis, not externally observed delay statistics.
- Source: [OPM holiday definitions](https://www.opm.gov/faq/payleave/what-are-federal-holidays.ashx). No external flight performance data are used.

- Result: ef014b1, Eval AUC **0.6893**, keep (+0.0021). Targeted calendar semantics succeed where raw month/day and coarse seasons failed. Total run 15.5s.
- Checked saved preparation on 26 training rows for batch/single-row equality. Synthetic calendar cases verify Thanksgiving on Nov 24 (Thursday) and Nov 23 (Thursday), and not Nov 24 (Friday), without reading any evaluation rows.

## Experiment 33 — holiday-window ablation

- Classification: ablation/simplification of a strong feature gain.
- Hypothesis: the actual holiday flag may provide the transferable signal, while the broader travel window could capture incidental weather. Remove HolidayTravelWindow, retaining HolidayDay and all other settings.

- Result: 4ce4ac8, Eval AUC **0.6872**, discard (−0.0021). The travel-window feature accounts for the observed holiday improvement; the actual-holiday flag alone does not improve over the pre-holiday model.

## Experiment 34 — actual-holiday ablation

- Classification: ablation/simplification.
- Hypothesis: keep HolidayTravelWindow but remove HolidayDay, since experiment 33 attributes the gain to the broader window. This isolates whether the actual-day flag adds any complementary value.

- Result: 8e9971a, Eval AUC **0.6893**, keep on equal AUC with one less feature and six fewer lines. The broader travel window provides the useful holiday signal.

## Experiment 35 — stronger L2 leaf shrinkage

- Classification: exploration of smooth weight regularization.
- Hypothesis: reg_lambda=20 in both components will shrink less-supported leaves and improve transfer, without removing splits entirely or restricting category groups. Other settings remain fixed.
- Source: XGBoost regularization reference, revisited at the 30-experiment research pause. This tests a regularization mechanism distinct from the earlier depth, child-weight, and split-threshold changes.

- Result: 62e624e, Eval AUC **0.6894**, keep (+0.0001). Small gain from smooth leaf shrinkage. Total run 15.5s.

## Experiment 36 — cached categorical code lookup

- Classification: implementation simplification for faster, stable inference.
- Hypothesis: train-fitted value→code dictionaries plus Categorical.from_codes give the exact existing feature values and missing-category semantics with less per-row work and no deprecated unknown-value constructor path.
- Source: pandas categorical API, previously read. Keep all model and scientific feature choices fixed; require equal AUC and a practical simplification/speed benefit.

- Result: 8d7aed3, Eval AUC **0.6894**, keep on equal AUC, faster evaluation (7.2s vs 8.9s), and explicit robust unknown-category handling. Total run 13.6s; saved artifact 4.1 MB.
- Verified cached-code features equal previous features on training rows, unknown categories become missing without warnings, and batch/single-row preparation agrees.

## Experiment 37 — distinguish holiday travel windows

- Classification: follow-up to the strong travel-window result.
- Hypothesis: Thanksgiving, year-end, and July holiday periods may have different effects; replace the pooled indicator with three indicators using exactly the same window boundaries. No raw month/day values enter the feature frame.

- Result: 104f916, Eval AUC **0.6892**, discard (−0.0002). Sharing one travel-window effect is more robust than separating holiday periods at this capacity.

## Experiment 38 — further one-hot interaction capacity

- Classification: follow-up to experiment 31's successful depth increase.
- Hypothesis: depth 6 may recover additional airport/time/holiday interactions in the one-hot component, which remains less adaptive per categorical split. Retain the strengthened L2 penalty and fixed primary model; change only secondary depth 5→6.

- Result: e9f7ec6, Eval AUC **0.6900**, keep (+0.0006). The one-hot component continues benefiting from interaction capacity. Total run 13.6s; artifact 4.4 MB.

## Experiment 39 — add ranking-objective diversity

- Classification: exploration combining the ranking near miss with the successful blend.
- Hypothesis: a 20% pairwise-ranking contribution may improve the ensemble despite weaker standalone AUC, analogous to the successful one-hot blend. The original components each retain 40% weight.
- Reuse experiment 30's within-month ranking configuration on the current feature set, with base_score=0 to center its raw scores before sigmoid conversion. Train all components fresh on train; the harness evaluates the combined prediction only.

- Result: a961790, Eval AUC **0.6897**, discard (−0.0003). Extra objective diversity does not earn its complexity; retain two models.

## Experiment 40 — one-hot depth boundary

- Classification: follow-up to consistent gains at depths 5 and 6.
- Hypothesis: depth 7 may still help the one-hot component; testing this establishes whether the observed capacity trend continues. Keep every other setting fixed, including L2=20 and min_child_weight=50.

- Result: 601eaed, Eval AUC **0.6902**, keep (+0.0002). Depth 7 still helps, but less than the previous two depth increases. Total run 13.9s.

## Synthesis after 40 experiments

- Best: **0.6902**, commit **601eaed**, +0.0159 versus baseline.
- Major new gain: a pooled holiday travel-window indicator (+0.0021). Actual-holiday flags were unnecessary; splitting the windows into three types was worse.
- One-hot depth increases from 4 to 5, 6, and 7 improved the blend; gains are now diminishing.
- L2=20 gave a small gain. Cached categorical codes preserved AUC, removed warnings, and sped evaluation by roughly two seconds.
- A third model trained with pairwise ranking did not improve the ensemble, so retain two components.
- Remaining work: check whether the now much-improved one-hot component can stand alone, then a small number of focused regularization/simplification trials. Finish with artifact, row-preparation, log, and branch consistency checks.

## Research refresh after 40 experiments

- [Original XGBoost paper](https://arxiv.org/abs/1603.02754) and current parameter documentation revisited for stochastic regularization.
- Current docs describe gradient-based CPU sampling; uniform subsampling of the secondary is a simpler remaining variance-control experiment.
- With little time remaining, prioritize component ablations and focused tests over a new expensive model family.

## Experiment 41 — current one-hot component alone

- Classification: ablation/simplification.
- Hypothesis: the secondary has substantially changed since experiment 25 (geometry, holiday window, minute feature, L2, and depth 7); it may now replace the ensemble. Train that exact component alone with the same monthly weights.
- This revisits model necessity after substantial intervening improvements, rather than repeating the earlier standalone model.

- Result: 53ae862, Eval AUC **0.6888**, discard (−0.0014). The current one-hot component is substantially stronger than before, but the blend remains valuable. Its lower standalone artifact size does not override the AUC drop.

## Experiment 42 — stochastic secondary training

- Classification: follow-up regularization of the deeper one-hot component.
- Hypothesis: subsample=0.8 in the secondary will reduce variance from depth-7 interactions. The primary already uses sampling; change only the secondary's row sampling.
- Source: XGBoost sampling documentation and original paper revisited after experiment 40.

- Result: 063f35f, Eval AUC **0.6905**, keep (+0.0003). Row subsampling improves the depth-7 component inside the blend. Harness training 6.9s, evaluation 7.1s, total 14.0s; artifact 4.8 MB.

## Final summary

- Completed baseline plus **42 experiments**, all 43 harness runs successful; no crashes or timeouts.
- Best Eval AUC **0.6905**, commit **063f35ff652d1eec464134af55e968ebbe2bf7de**, branch **oct6**. Baseline **0.6743**; absolute improvement **0.0162**. The branch is left at the best kept commit and its saved artifact is available.
- Final model averages a shallow, partition-based categorical model with a deeper one-hot categorical model. Both use monthly class-balancing weights, minimum child weight 50, L2 regularization 20, and row subsampling. The primary also averages four parallel trees per round.
- What worked: removing raw month/day-of-month categories; HP-to-US carrier harmonization; restrained tree complexity and monthly loss balancing; complementary categorical models; departure minute; two-dimensional airport geometry fitted only from training route distances; a pooled holiday travel window; deeper secondary trees with L2 and row subsampling. Cached categorical preparation substantially reduced evaluation time.
- What did not: adding raw calendar flexibility, seasons, route categories, route-relative time, date-excluded target rates, aggressive boosting, standalone one-hot replacement, fine holiday indicators, and within-month ranking. Geometry mattered more after introducing the blend, so controlled retesting after major changes was useful.
- Working theory: transfer from 2005 training to 2006 evaluation benefits from limiting unstable calendar effects while preserving carrier/airport interactions through complementary categorical handling and train-only geography. This is an interpretation of the observed Eval AUC changes, not a holdout finding.
- Next experiments: ablate unnecessary primary parallel trees; isolate which pooled holiday windows transfer; test complementary-model diversity with controlled seeds or DART after establishing runtime feasibility. Evaluate further only in a separately authorized run. Human holdout assessment remains unseen.
- Final verification: saved artifact reloads; batch and single-row preparation match on training rows; changing labels leaves features unchanged; unseen carriers/airports map to missing values; predictions are finite valid probabilities. Syntax and final harness call verified. Results and timing logs agree on all 43 commits. Tracked working tree is clean and only train.py differs from the starting commit. No additional validation metric was computed.
- The loop ended with less than two minutes remaining, as required. All outputs and artifacts are left in place for human review.
