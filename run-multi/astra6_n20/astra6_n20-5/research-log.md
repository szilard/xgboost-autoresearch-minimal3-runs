# Research log: oct6

## Setup and baseline
- Branch: oct6, starting commit b15ec66.
- Training data only: 200,000 balanced rows, eight predictors, no missing values; categorical date components have c- prefixes.
- Baseline b15ec66: Eval AUC 0.6743; training phase 1.5 s, evaluation 31.0 s. Kept.
- Eval and holdout contents are not inspected. Only harness Eval AUC determines selection. No counts used as features.

## Initial research
- https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html : control complexity with tree depth, leaf weights and regularization; smaller learning rates need additional boosting rounds.
- https://xgboost.readthedocs.io/en/stable/parameter.html : min_child_weight limits small leaves, reg_lambda shrinks leaf weights, subsampling adds robustness; category partition size can regularize native categorical splits.
- https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html : native partitioning groups categories by learned leaf responses, avoiding artificial numeric order.
- https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches : search excerpt motivates scheduled-time and carrier/route features; full page failed to load, so no stronger claims are drawn.

## Experiment 1 — regularized longer boosting
- Class: follow-up to baseline.
- Hypothesis: 500 rounds at learning rate 0.05 can learn beyond the 100-round baseline, while min_child_weight=20, reg_lambda=10 and subsample=0.8 restrain sample-specific interactions across the 2005 to 2006 shift.
- Source: XGBoost tuning guide and parameter reference above.
- Result: 459ffab, Eval AUC 0.6744; training 3.9 s, evaluation 30.8 s. Kept (+0.0001).

## Experiment 2 — remove day-of-month
- Class: ablation/simplification of experiment 1.
- Hypothesis: irregular marginal delay rates across day-of-month and interactions with month can fit weather on particular 2005 dates that does not repeat in 2006. Remove this categorical feature, retaining month and weekday.
- Motivation: longer boosting added only 0.0001, suggesting generalization rather than insufficient boosting is limiting.
- Result: c302667, Eval AUC 0.6747; training 3.6 s, evaluation 27.6 s. Kept (+0.0003).

## Experiment 3 — faster equivalent category preparation
- Class: simplification of experiment 2.
- Hypothesis: explicit train-fitted category-code dictionaries and one DataFrame construction can preserve features exactly while avoiding repeated Series filtering/copying in row-wise evaluation.
- Unknown values map to categorical code -1. Check batch/single-row equivalence and old/new equivalence on training examples and an unseen category before the harness run.
- Result: a6200e3, Eval AUC 0.6747; training 3.6 s, evaluation 11.0 s. Kept at equal AUC because evaluation is 60% faster. Old/new and row/batch checks passed.

## Experiment 4 — shallower interactions
- Class: ablation/simplification of the best model.
- Hypothesis: depth 4 rather than 6 will reduce high-order interactions and categorical overfitting across years. Hold all other hyperparameters and features constant.
- Source: XGBoost parameter tuning guide; https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html explains why unconstrained interactions can capture noise.
- Result: 8edf203, Eval AUC 0.6794; training 2.7 s, evaluation 10.2 s. Kept (+0.0047), a meaningful improvement supporting the overfitting hypothesis.

## Experiment 5 — carrier-airport interactions
- Class: exploration of explicit categorical feature engineering.
- Hypothesis: CarrierOrigin and CarrierDest categories let shallow trees learn airline-specific airport behavior directly while retaining shared carrier and airport effects.
- Source: native category partitions in https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html ; airline/airport operational context in the Berkeley project search excerpt. This particular pair-feature design is our inference, not a published result.
- Fit category levels on train only; all per-row transformations remain in prepare. No count features.
- Result: 277b9fa, Eval AUC 0.6714; training 3.4 s, evaluation 17.0 s. Discarded (-0.0080). Extra high-cardinality categories generalize poorly under these settings.

## Experiment 6 — restrict categorical partitions
- Class: follow-up to shallower-tree success and interaction failure.
- Hypothesis: max_cat_threshold=8 (default 64) limits category groupings that exploit sampling noise. Use the original features at the best kept commit, changing only this parameter.
- Source: categorical regularization in the XGBoost parameter reference.
- Result: 64051e4, Eval AUC 0.6793; training 2.5 s, evaluation 10.3 s. Discarded, even though the drop is only 0.0001.

## Experiment 7 — single-category splits
- Class: exploration of categorical split representation.
- Hypothesis: one-category-at-a-time splits may learn more stable airport/carrier effects than adaptive category groupings. Set max_cat_to_onehot=512, above every original feature cardinality, with all else at the best commit.
- Source: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html . This tests a qualitatively different split family from restricting partition size.
- Additional research: https://arxiv.org/abs/1706.09516 and https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html explain target-statistic leakage. Avoid naive target encoding; no CV or additional evaluation is introduced.
- Result: d5f5a48, Eval AUC 0.6784; training 2.3 s, evaluation 10.3 s. Discarded (-0.0010). Original grouped categorical splits are better so far.

## Experiment 8 — seasonal feature ablation
- Class: ablation/simplification of the best model.
- Hypothesis: the large 2005 month-level delay differences may partly be weather-specific; removing Month directly measures whether this seasonal predictor transfers. Keep all other features and parameters unchanged.
- This diagnostic is distinct from removing day-of-month: it tests broad seasonality rather than within-month dates.
- Result: cdc5f4a, Eval AUC 0.6821; training 2.5 s, evaluation 9.1 s. Kept (+0.0027). Exact monthly effects hurt cross-year transfer in this configuration.

## Experiment 9 — minute within hour
- Class: exploration of scheduled-time feature engineering.
- Hypothesis: departure minute (CRSDepTime % 100) exposes repeating schedule-bank patterns that require many splits when only HHMM is available. Add one feature, retaining HHMM and all current predictors.
- Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html discusses representations of periodic time components. Schedule-bank relevance is our domain hypothesis.
- Result: c883c29, Eval AUC 0.6820; training 2.6 s, evaluation 9.1 s. Discarded (-0.0001).

## Experiment 10 — route-relative scheduled time
- Class: exploration of train-fitted numerical lookup features.
- Hypothesis: scheduled minutes since midnight minus the training route median captures position within a route's daily schedule. This may expose delay accumulation patterns using a smoother feature than a high-cardinality route category.
- Source: program.md explicitly motivates a route-median schedule offset; time representation research above. Median fitted at module level on train, never within prepare. No counts or targets enter the lookup.
- Result: 6ede8ea, Eval AUC 0.6821; training 2.6 s, evaluation 9.8 s. Discarded: equal AUC with additional code and slower evaluation. Row/batch equivalence passed.

## Synthesis after 10 experiments
- Best: cdc5f4a, Eval AUC 0.6821 (+0.0078 versus baseline).
- Strongest gain: reducing tree depth from 6 to 4 (+0.0047); removing Month also helps (+0.0027). Day-of-month removal helps a little.
- High-cardinality carrier-airport categories hurt; restricting partitions or forcing one-category splits did not help. Minute-of-hour and route-relative time did not improve ranking.
- Current theory: cross-year generalization is constrained by unstable detail and interaction variance, while broad time-of-day and airport/carrier signals transfer.
- New research: https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html explains shape constraints; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html describes averaging parallel randomized trees within boosting. Also searched arXiv for tree regularization under distribution shift.
- Next directions: constrained time shape, additional complexity ablations, targeted holiday features, and variance-reducing ensembles. No extra datasets, metrics or CV.

## Experiment 11 — constrained daily delay curve
- Class: exploration of shape-constrained boosting.
- Hypothesis: the observed rise from 05:00 to 20:00 and decline afterward can be enforced with two hinge features and monotone directions +1/-1, suppressing local time fluctuations and unstable interactions.
- Convert HHMM to minutes from 05:00 modulo 24 h; replace raw time by a rise capped at 900 minutes and an excess beyond 900. Keep other predictors unchanged.
- Source: XGBoost monotonic-constraints guide above. Peak placement comes only from training marginal patterns.
- Result: 5f1fc43, Eval AUC 0.6821; training 2.5 s, evaluation 9.3 s. Discarded: equal AUC with extra transformation code and no speed benefit.

## Plateau research after experiment 11
- Three consecutive discards (9-11) moved AUC less than 0.001. Stop feature tweaks and revisit model variance.
- Re-searched primary XGBoost docs for boosted random forests and Friedman's stochastic gradient boosting work.
- https://xgboost.readthedocs.io/en/stable/tutorials/rf.html supports num_parallel_tree with multiple boosting rounds and random row/column subsampling.
- https://arxiv.org/abs/1806.09762 studies a different regularized stochastic boosting algorithm based on averaging. Used as conceptual motivation, not as evidence that XGBoost implements that algorithm.

## Experiment 12 — boosted randomized forests
- Class: exploration of variance-reducing model architecture.
- Hypothesis: average four trees per boosting stage with colsample_bynode=0.8 to reduce noisy split choices while preserving the established 500 rounds, depth 4 and leaf regularization.
- Source: XGBoost random-forest guide above. Total 2,000 trees; expect training well below the 60-second cap.
- Result: 1a5964e, Eval AUC 0.6830; training 10.1 s, evaluation 9.8 s. Kept (+0.0009), supporting variance reduction.

## Experiment 13 — airport geometry learned from training routes
- Class: exploration of unsupervised representation features.
- Hypothesis: low-dimensional coordinates inferred from airport-to-airport distances allow geographic sharing that categorical IDs cannot express efficiently. Use only the train route-distance graph; no external airport metadata, targets or counts.
- Fit undirected edge lengths as route median Distance, complete distances with shortest paths, and use classical MDS (two positive leading eigenvectors of the centered squared-distance matrix). Add origin and destination coordinates to the existing features.
- Sources: https://scikit-learn.org/1.9/modules/manifold.html and https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html . This adapts graph-distance embedding to airline routes; transfer benefits are a hypothesis.
- Result: 07dd661, Eval AUC 0.6829; training 11.3 s, evaluation 10.6 s. Discarded (-0.0001). Airport coordinate features passed row/batch and unknown-category checks but did not improve ranking.

## Experiment 14 — recurring holiday travel patterns
- Class: exploration of compact calendar features.
- Hypothesis: major holidays recur across years even when individual calendar dates and monthly weather differ. Add a holiday-window flag (within four days) and exact-holiday flag, pooling New Year, Memorial Day, July 4, Labor Day, Thanksgiving and Christmas.
- Moving dates are calculated from each row's month/day/weekday, not a year inferred from the dataset. No raw month/day feature is restored.
- Sources: https://www.opm.gov/faq/payleave/what-are-federal-holidays.ashx verifies holiday definitions; scikit-learn time-feature example motivates holiday indicators. Expected flight-delay benefit is a hypothesis.
- Result: 13eca94, Eval AUC 0.6838; training 10.9 s, evaluation 11.0 s. Kept (+0.0008). Moving-date calculations tested on 2005/2006 Thanksgiving, Memorial and Labor days; row/batch equivalence passed.

## Experiment 15 — shallower randomized ensemble
- Class: follow-up to the strong depth-6 to depth-4 improvement and the ensemble gain.
- Hypothesis: depth 3 further limits unstable interactions while the four-tree boosting ensemble captures reliable shared effects. Change only max_depth from 4 to 3.
- Source: XGBoost complexity-control and boosted-random-forest documentation already reviewed.
- Result: 9b804b3, Eval AUC 0.6851; training 9.3 s, evaluation 10.9 s. Kept (+0.0013).

## Experiment 16 — at most pairwise tree interactions
- Class: follow-up/simplification of the successful shallower ensemble.
- Hypothesis: depth 2 removes all paths involving three predictors, testing whether broad pairwise effects transfer better than the current third-order interactions. Change depth only; keep 500 boosting rounds and all features fixed.
- Additional research for a later new direction: https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html explains the unweighted pairwise logistic objective and mean pair sampling. AUC is pair-order based, so this is a potential alternative to pointwise classification loss.
- Result: 6e3aa98, Eval AUC 0.6825; training 7.9 s, evaluation 10.7 s. Discarded (-0.0026). Depth 2 appears too restrictive at this boosting budget.

## Experiment 17 — longer, slower depth-three boosting
- Class: follow-up to the depth-three ensemble.
- Hypothesis: 1,500 rounds at eta=0.03 can fit reliable residual structure with smaller per-step changes. This tests whether the current shallow model is limited by boosting budget; effective total step size rises from 25 to 45.
- Source: XGBoost tuning guide recommends coupling smaller eta with more boosting rounds. Four trees per round gives 6,000 total trees; expected training under 30 seconds.
- Result: 244d2e6, Eval AUC 0.6842; training 25.7 s, evaluation 11.9 s. Discarded (-0.0009). Additional boosting is not beneficial at current regularization.

## Experiment 18 — pairwise ranking objective
- Class: exploration of a different XGBoost training objective.
- Hypothesis: unweighted pairwise logistic loss targets positive-versus-negative score ordering, closely related to AUC, and may rank ambiguous flights better than pointwise log loss.
- Source: https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html . Use one query group containing all training rows, mean sampling with one pair per row, and disable query-level lambda normalization so Hessians are not shrunk by the single large group.
- Use 250 rounds at eta=0.1 to bound pair-sampling overhead while keeping total nominal step size 25. Preserve depth 3, four parallel trees and feature preparation. A small adapter applies sigmoid to rank scores for the harness predict_proba interface. No additional evaluation is performed.
- Result: 23e0d3d, Eval AUC 0.6812; training 14.2 s, evaluation 10.7 s. Discarded (-0.0039). Ranking adapter serialized and evaluated successfully; standard classification remains preferable.

## Experiment 19 — larger minimum leaf support
- Class: follow-up to the best regularized shallow ensemble.
- Hypothesis: min_child_weight=100 instead of 20 suppresses poorly supported category-specific leaves without removing useful three-way interactions. This targets leaf estimation variance rather than tree depth.
- Source: XGBoost parameter reference on minimum Hessian support. Change this one parameter only.
- Result: d425153, Eval AUC 0.6850; training 9.2 s, evaluation 11.0 s. Discarded (-0.0001).

## Experiment 20 — additive calendar contribution
- Class: exploration of structured interaction constraints.
- Hypothesis: force weekday/holiday effects to add to the operational prediction, preventing unstable calendar-by-airport/carrier/time interactions while retaining all interactions among operational features.
- Two disjoint allowed groups: [DayOfWeek, HolidayWindow, HolidayDay] and [CRSDepTime, Distance, UniqueCarrier, Origin, Dest]. Other settings unchanged.
- Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html . Motivated by gains from dropping raw calendar detail and shallower trees.
- Result: a1a75f9, Eval AUC 0.6841; training 9.2 s, evaluation 10.9 s. Discarded (-0.0010). Some calendar-operational interactions remain useful.

## Synthesis after 20 experiments
- Best: 9b804b3, Eval AUC 0.6851 (+0.0108 versus baseline).
- Improvements in experiments 11-20: averaging four randomized trees (+0.0009), compact holiday features (+0.0008), and depth 3 (+0.0013).
- Unsuccessful: graph-derived airport coordinates, constrained time shape, depth 2, extended boosting, pairwise ranking loss, increased minimum leaf support and additive calendar constraints.
- Current theory: moderate operational interactions matter, but precise calendar and high-dimensional categorical effects overfit. Variance reduction helps more than increasing fit capacity. Holiday identity transfers better than raw month/day.
- Fresh research: searched primary literature on concept drift and exponential forgetting; reviewed XGBoost sample weighting and https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html on early stopping.
- Next directions: temporal training weights, chronological internal early stopping, and split-gain regularization. Harness Eval AUC remains the only selection metric; any early-stopping validation will be carved out of train.csv only.

## Experiment 21 — recency-weighted training
- Class: exploration of training distribution weighting.
- Hypothesis: airline and airport operations late in 2005 may better resemble 2006. Give examples exponentially increasing weights with a six-month half-life; normalize to mean one so regularization scale stays comparable. Retain every training row and do not add month as a predictor.
- Sources: concept-drift/exponential-forgetting literature search and XGBoost fit sample_weight API. Six months is a preselected heuristic, not inferred from evaluation contents.
- Result: f12489b, Eval AUC 0.6854; training 10.0 s, evaluation 10.9 s. Kept (+0.0003).
- Relevant primary research found: https://arxiv.org/abs/2304.01512 (Handling Concept Drift in Global Time Series) discusses exponential weighting for boosting under drift. Our flight-classification weighting is an adaptation, not that paper's evaluated setting.

## Experiment 22 — split-gain threshold
- Class: follow-up to the shallow weighted ensemble and the failure of longer boosting.
- Hypothesis: gamma=5 prunes weak loss-reduction splits while preserving strong interactions, addressing noisy residual fitting more selectively than reducing depth or requiring large leaves.
- Source: XGBoost parameter reference on gamma/min_split_loss. Keep every other setting fixed.
- Result: 7b7712f, Eval AUC 0.6854; training 9.2 s, evaluation 10.8 s. Kept at equal AUC with lower observed training/run time (20.0 s total versus 20.9 s).

## Experiment 23 — stronger recency weighting
- Class: follow-up to the successful six-month recency weights.
- Hypothesis: a three-month half-life further emphasizes recent operational relationships, testing whether the gain persists under stronger forgetting. Relative weight changes over six months increase from 2x to 4x; all training rows remain included.
- Source: concept-drift weighting paper referenced in experiment 21. Change only the half-life.
- Result: be3e88a, Eval AUC 0.6835; training 9.2 s, evaluation 11.0 s. Discarded (-0.0019). Mild recency weighting helps, aggressive forgetting loses useful older observations.
- Complexity check for kept gamma change: f12489b had 29,946 tree nodes / 15,973 leaves; 7b7712f has 29,364 / 15,682, consistent with measured speed improvement.

## Experiment 24 — coarse seasonal flags
- Class: follow-up to the raw-month ablation, with a meaningfully coarser representation.
- Hypothesis: binary winter (December-February) and summer (June-August) indicators preserve broad weather/travel seasonality without learning 12 separate month effects. All other dates remain grouped together.
- Source: time-feature engineering research already reviewed. Specific season grouping is a domain hypothesis. Add two boolean features using month already parsed for holidays; no raw Month predictor.
- Result: 9096ba3, Eval AUC 0.6839; training 9.4 s, evaluation 11.0 s. Discarded (-0.0015). Broad season flags also fail to transfer in this configuration.

## Experiment 25 — chronological internal early stopping
- Class: exploration of training/regularization procedure.
- Hypothesis: stopping according to later 2005 months may select a model that generalizes across temporal changes better than a fixed round count. Fit January-October; reserve November-December from train.csv for early stopping only.
- Source: https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html . Use up to 2,000 rounds, 75-round patience and internal AUC; suppress validation output. Only harness Eval AUC decides keep/discard.
- The saved model remains the one trained on the fitting partition. No CV, no retraining on more data, and no evaluation-data inspection. Retain six-month recency weighting and renormalize weights on the fitting partition.
- Result: dfb2cd2, Eval AUC 0.6809; 369 selected rounds; training 8.0 s, evaluation 11.1 s. Discarded (-0.0045). Losing later fitting data and/or the internally selected stopping point hurts transfer; no full-data retrain was performed.

## Experiment 26 — average independent boosting trajectories
- Class: exploration of a complete-model ensemble.
- Hypothesis: average predicted probabilities from three models with preselected seeds 42, 137 and 2026, reducing random split/boosting-path variation beyond averaging trees at each shared stage.
- Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html documents probability averaging. Use a minimal serializable adapter around three XGBoost estimators.
- Every member is trained from scratch on all train.csv rows with the same best hyperparameters and six-month weights. No member is individually scored or selected; the fixed equal-weight ensemble is evaluated once by the harness. Expected training about 26 seconds.
- Result: 46f5dd1, Eval AUC 0.6853; training 25.9 s, evaluation 11.7 s. Discarded (-0.0001). Complete-model averaging adds cost and does not improve the current ranking.

## Experiment 27 — ablate parallel trees
- Class: ablation/simplification of the best model.
- Hypothesis: the earlier randomized-forest gain may chiefly come from column sampling; removing num_parallel_tree=4 while retaining colsample_bynode=0.8 tests whether repeated trees at each stage are necessary. Return to one tree per round, 500 total instead of 2,000.
- This separates the two mechanisms introduced together in experiment 12 and could substantially reduce training cost.
- Result: 0339663, Eval AUC 0.6850; training 2.4 s, evaluation 10.8 s. Discarded despite the speed gain because AUC is lower (-0.0004). Within-stage tree averaging contributes to the best score.

## Experiment 28 — full-row trees
- Class: ablation/simplification of the best randomized ensemble.
- Hypothesis: using every training row stabilizes leaf estimates while column subsampling retains diversity across the four parallel trees. Remove subsample=0.8 to use the default 1.0.
- Source: XGBoost sampling and random-forest guidance. This isolates row sampling from the other randomization mechanisms.
- Result: 8aada05, Eval AUC 0.6858; training 7.2 s, evaluation 10.7 s. Kept (+0.0004), with lower runtime and smaller artifact.

## Experiment 29 — deterministic full-data boosting
- Class: ablation/simplification following the full-row improvement.
- Hypothesis: considering all features at every split may stabilize the remaining random variation. Remove colsample_bynode=0.8.
- Also remove num_parallel_tree=4: once both row and column sampling are disabled, same-stage trees have identical data and candidates, so repeated parallel trees provide no useful diversity. This is a consequence of the sampling ablation, unlike experiment 27 where both sampling mechanisms were active.
- All feature preparation, recency weights, depth, round count and penalties remain fixed.
- Result: 18df288, Eval AUC 0.6854; training 1.9 s, evaluation 10.5 s. Discarded (-0.0004), despite substantial simplification and speed. Feature sampling remains useful with full-row training.

## Experiment 30 — tree dropout
- Class: exploration of dropout-regularized boosting.
- Hypothesis: DART reduces over-specialization of later trees, a distinct mechanism from sampling rows/columns and averaging same-stage trees.
- Sources: https://arxiv.org/abs/1505.01866 and https://xgboost.readthedocs.io/en/stable/tutorials/dart.html . The guide warns that dropout prevents prediction caching, so use 250 rounds at eta=0.1 and one tree per round to fit the 60-second training cap.
- Set rate_drop=0.05 and skip_drop=0.5; retain full-row fitting, feature subsampling, holiday features, recency weights and other regularization.
- Result: c343afc, Eval AUC 0.6858; training 19.4 s, evaluation 10.6 s. Discarded at equal AUC: extra dropout parameters and slower training. The legacy dart booster name emits a deprecation warning in installed XGBoost; future dropout trials can use the standard tree booster with dropout parameters directly.

## Synthesis after 30 experiments
- Best: 8aada05, Eval AUC 0.6858 (+0.0115 versus baseline).
- Improvements in experiments 21-30: six-month recency weighting (+0.0003), gamma=5 at equal AUC with fewer nodes and faster runtime, full-row training (+0.0004).
- Stronger recency weights, broad season flags and chronological early stopping hurt. Complete-model averaging and removing same-stage tree averaging also failed. Fully deterministic boosting is faster but lower in AUC.
- DART is a promising equal-AUC near miss, though currently slower; a limited-capacity follow-up may still be informative.
- Current theory: stable leaf estimation and mild temporal weighting help; random feature selection provides useful diversity, while row sampling is unnecessary here.
- New research search: histogram max_bin and feature-weighted column sampling. Sources: https://xgboost.readthedocs.io/en/stable/parameter.html and https://xgboost.readthedocs.io/en/latest/python/examples/feature_weights.html .
- Next directions: numeric split granularity, sampling emphasis for the dominant scheduled-time signal, and a bounded follow-up to DART.

## Experiment 31 — coarser numeric splits
- Class: exploration of histogram resolution as regularization.
- Hypothesis: max_bin=64 reduces finely localized departure-time/distance splits and encourages broader boundaries that transfer across years. Native categorical levels are unchanged.
- Source: XGBoost max_bin parameter documentation; any regularization benefit is our hypothesis. Change only max_bin from its default 256.
- Result: 5392421, Eval AUC 0.6855; training 7.9 s, evaluation 10.6 s. Discarded (-0.0003). Coarser numeric boundaries are not helpful.

## Plateau research after experiment 31
- Experiments 29-31 are three consecutive discards within 0.001 of best. Revisited the primary DART paper via PMLR and its explanation of over-specialization versus shrinkage.
- DART's equal score at 250 rounds is a more promising lead than further small perturbations of ordinary boosting. More dropout rounds test a different learning trajectory; longer standard boosting already failed.

## Experiment 32 — additional dropout capacity
- Class: follow-up to the DART near miss in experiment 30.
- Hypothesis: 350 rather than 250 dropout rounds can add broadly useful trees without the late-tree specialization observed in ordinary boosting. Keep eta=0.1, rate_drop=0.05, skip_drop=0.5 and one tree per round from that trial.
- Use the standard tree booster with dropout parameters, per installed XGBoost's deprecation guidance, rather than the legacy dart name. Expected training approximately 36-40 seconds, below the 60-second cap.
- Sources: https://arxiv.org/abs/1505.01866 and https://xgboost.readthedocs.io/en/stable/tutorials/dart.html .
- Result: 5208571, Eval AUC 0.6858; training 34.9 s, evaluation 11.0 s. Discarded at equal AUC with slower training and more parameters. The current dropout API worked without the legacy warning.

## Experiment 33 — prioritize scheduled time in feature sampling
- Class: exploration of feature-weighted randomization.
- Hypothesis: scheduled time has by far the highest training gain; give it sampling weight 2 while every other feature has weight 1, preserving column diversity while reducing splits where the dominant signal is absent.
- Source: https://xgboost.readthedocs.io/en/latest/python/examples/feature_weights.html and parameter reference. Confirmed the installed sklearn estimator accepts feature_weights in its constructor.
- Weights are preselected from the qualitative importance observation, not optimized against individual eval rows.
- Result: 1fa54d6, Eval AUC 0.6858; training 7.1 s, evaluation 10.8 s, total 17.9 s. Discarded at equal AUC and identical total runtime with extra parameter code.

## Experiment 34 — stronger L2 leaf shrinkage
- Class: follow-up to the stable full-row shallow ensemble.
- Hypothesis: reg_lambda=100 instead of 10 smoothly shrinks uncertain leaf updates. This differs from the unsuccessful minimum-leaf constraint, which rejects small leaves entirely, and gamma, which prunes split gains.
- Source: XGBoost parameter reference on L2 leaf-weight regularization. Change this one parameter only.
- Result: 836402c, Eval AUC 0.6860; training 7.2 s, evaluation 10.6 s. Kept (+0.0002).

## Experiment 35 — direct route identity
- Class: exploration of a distinct categorical interaction.
- Hypothesis: Origin-Dest identity captures stable route-specific structure that shallow trees need several splits to express. Unlike experiment 5, this excludes carrier interactions; the current model also has shallower trees, stronger L2 shrinkage, full-row fitting and no raw month predictor.
- Source: https://developers.google.com/machine-learning/crash-course/categorical-data/feature-crosses explains explicit interactions and sparsity risk. Apply XGBoost native categories with a vocabulary fitted only on train.
- Cache route levels as a pandas Index to avoid rebuilding the large vocabulary for every evaluation row. Unknown routes map to missing; no count feature is used.
- Result: c19ad72, Eval AUC 0.6788; training 11.4 s, evaluation 14.3 s. Discarded (-0.0072). Route categories generalize poorly even with stronger regularization; row/batch equivalence passed.

## Experiment 36 — cache existing category indexes
- Class: simplification/performance follow-up to the preparation improvement in experiment 3.
- Hypothesis: keeping fitted category levels as pandas Index objects avoids reconstructing their metadata for each evaluation row, with identical feature values, categories and ordering.
- No model hyperparameter or feature changes. Verify feature equivalence to the saved best artifact on training examples including an unseen category before running the harness.
- Result: e94a02c, Eval AUC 0.6860; training 7.7 s, evaluation 8.5 s. Kept at equal AUC with evaluation reduced from 10.6 s and total runtime from 17.8 to 16.2 s. Old/new feature equivalence passed.

## Experiment 37 — remove potentially redundant distance
- Class: ablation/simplification of the best model.
- Hypothesis: Origin and Dest may capture the useful route information, making detailed Distance splits an unnecessary source of variability. Remove only the Distance predictor and leave training settings fixed.
- Motivated by the low relative baseline distance gain and unsuccessful richer geographical representations; this directly tests whether the original distance feature is still useful.
- Result: fe13391, Eval AUC 0.6853; training 6.9 s, evaluation 7.3 s. Discarded (-0.0007), despite faster preparation. Distance retains useful information beyond airport IDs.

## Experiment 38 — ablate the holiday travel window
- Class: ablation/simplification of the successful holiday feature family.
- Hypothesis: the exact holiday-day flag may transfer more reliably than a pooled four-day window, which could absorb unrelated date-specific weather. Remove HolidayWindow while retaining HolidayDay and its existing date calculations.
- This separates the two predictors introduced together in experiment 14. All model settings remain unchanged.
- Result: b149c46, Eval AUC 0.6850; training 6.9 s, evaluation 7.3 s. Discarded (-0.0010). The surrounding holiday-window feature contributes useful signal.

## Experiment 39 — extra rounds under stronger shrinkage
- Class: follow-up to the stronger-L2 improvement.
- Hypothesis: 1,000 rounds at the existing eta=0.05 may recover useful structure now that reg_lambda=100 and full-row fitting stabilize updates. Change round count only.
- This is distinct from experiment 17, which used weak L2 (10), row subsampling, eta=0.03 and 1,500 rounds. The new test probes the interaction between the kept regularization changes and boosting capacity.
- Result: 2bbd991, Eval AUC 0.6860; training 11.8 s, evaluation 7.6 s. Discarded at equal AUC with more trees and slower total runtime.

## Experiment 40 — L1 suppression of weak corrections
- Class: follow-up to useful L2 and split-gain regularization.
- Hypothesis: reg_alpha=10 soft-thresholds small leaf-gradient sums, potentially removing weak corrections that L2 only shrinks. Keep L2=100 and the established 500 rounds.
- Source: XGBoost parameter reference on L1 leaf-weight regularization. This is a distinct penalty mechanism from previous tests.
- Result: 0a7313a, Eval AUC 0.6876; training 7.0 s, evaluation 7.7 s. Kept (+0.0016), a clear gain with a smaller artifact and faster runtime.

## Synthesis after 40 experiments
- Best: 0a7313a, Eval AUC 0.6876 (+0.0133 versus baseline).
- Improvements in experiments 31-40: stronger L2 (+0.0002), caching category indexes at equal AUC with faster scoring, and L1=10 (+0.0016).
- Coarse numeric bins, route categories, distance removal, holiday-window removal and extra boosting rounds did not help. Dropout and prioritized time sampling tied but were not simpler/faster overall.
- Current theory: shrinking or eliminating weak leaf corrections is a stronger generalization tool here than adding feature detail. The compact original operational features plus two holiday flags remain useful.
- Fresh research search revisited L1 regularization and learning-rate scheduling in primary XGBoost documentation. https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler supports callable schedules applied after iterations.
- Final budget priorities: follow up the L1 improvement, test a controlled learning-rate trajectory and a simple operational-day time representation, then check simplifications within the remaining clock.

## Experiment 41 — stronger L1 suppression
- Class: follow-up to the clear experiment-40 gain.
- Hypothesis: raising reg_alpha from 10 to 30 will eliminate more weak leaf corrections and test whether the gain extends to stronger sparsity. All other settings and features remain fixed.
- Source: XGBoost L1 parameter documentation, freshly re-searched at the synthesis pause.
- Result: 03853be, Eval AUC 0.6864; training 7.6 s, evaluation 7.4 s. Discarded (-0.0012). Moderate L1 is better than stronger suppression.

## Experiment 42 — declining learning-rate trajectory
- Class: exploration of training schedule.
- Hypothesis: front-load learning of broad structure and shrink late residual corrections with a linear rate decline from 0.09 to 0.01 across 500 rounds. The mean is 0.05 and summed rates equal the baseline fixed-rate total of 25.
- Source: XGBoost LearningRateScheduler API, researched at the experiment-40 synthesis. The callback runs after each iteration, so it sets the next round's rate; the initial rate is supplied separately.
- All other parameters and features match the best L1=10 model.
- Result: 4db8d93, Eval AUC 0.6874; training 6.6 s, evaluation 7.6 s. Discarded (-0.0002). The learning-rate callback serialized successfully, but fixed eta=0.05 remains better.

## Experiment 43 — continuous operational-day time
- Class: exploration/follow-up to the constrained-time near miss.
- Hypothesis: replacing HHMM by minutes since 05:00 modulo 24 h places overnight flights next to the preceding evening, potentially yielding more coherent tree boundaries. Keep one unconstrained numeric time feature.
- This differs from experiment 11: no hinge expansion and no monotonic constraints. The 05:00 origin is motivated by the lowest-delay period in training marginals.
- Source: scikit-learn cyclical time-feature engineering example already reviewed. All transformations remain row-local in prepare.
- Result: a3317fc, Eval AUC 0.6875; training 6.9 s, evaluation 7.7 s. Discarded (-0.0001). Boundary calculations passed, but raw HHMM remains better.

## Experiment 44 — fewer regularized boosting rounds
- Class: ablation/simplification of the best model.
- Hypothesis: with L1=10, L2=100 and gamma=5 suppressing weak corrections, reducing boosting rounds from 500 to 300 may preserve useful structure and avoid unnecessary later trees.
- Unlike earlier additional-round tests, this directly seeks a cheaper model at the same or better harness AUC. All other settings remain fixed.
- Result: ade4fcf, Eval AUC 0.6876; training 5.1 s, evaluation 7.6 s. Kept at equal AUC with 1,200 rather than 2,000 trees and total runtime 12.8 s rather than 14.6 s.

## Experiment 45 — milder temporal weighting
- Class: follow-up to recency-weighting findings and the now more regularized model.
- Hypothesis: a twelve-month half-life may preserve useful older observations while retaining some preference for recent operations. Six months helped earlier; three months hurt, so this tests the milder side of that tradeoff.
- Source: concept-drift/exponential-weighting research recorded in experiment 21. Change the half-life only, keeping the shorter best ensemble.
- Result: ede777a, Eval AUC 0.6873; training 5.2 s, evaluation 7.4 s. Discarded (-0.0003). Six-month weighting remains best among uniform, three-, six- and twelve-month choices tested across the run.

## Experiment 46 — ablate exact holiday day
- Class: ablation/simplification of the holiday feature pair.
- Hypothesis: the surrounding holiday window, shown useful in experiment 38, may contain enough calendar information; removing the exact-day indicator could simplify the model without losing ranking quality.
- This complements the earlier opposite ablation and changes only one prepared column. Keep the 300-round best model and six-month training weights.
- Result: 6409c5d, Eval AUC 0.6870; training 5.8 s, evaluation 7.4 s. Discarded (-0.0006). Both holiday predictors are useful in the final compact model.

## Experiment loop closed
- Harness status after experiment 46: 58m11s elapsed, 1m49s remaining. No further experiments are started, following the under-two-minute wrap-up rule.
- Restore the last kept commit ade4fcf and audit saved artifacts and logs before stopping the clock.

## Final summary
- Best kept commit: ade4fcfde94564fb8b4be6040a3e925a396cfee8 on branch oct6.
- Best harness Eval AUC: **0.6876**, versus baseline **0.6743**, an absolute gain of **0.0133**.
- Completed 46 experiments plus the unchanged baseline: 16 kept rows including baseline, 31 discards, 47 successful harness runs, no crashes or timeouts.
- Best model: 300 boosting rounds, four parallel trees per round, depth 3, learning rate 0.05, min_child_weight 20, L2 100, L1 10, gamma 5, full-row fitting and colsample_bynode 0.8. Six-month half-life training weights have mean one.
- Final predictors: scheduled departure time, distance, weekday, carrier, origin, destination, holiday travel window and exact holiday day. Raw month and day-of-month are excluded as direct predictors. Category vocabularies/codes are fitted on train and cached; unseen categories become missing values.
- Best run time: 12.8 s (training phase 5.1 s, evaluation phase 7.6 s), compared with baseline 32.4 s. Rounded phase times may not sum exactly to rounded total.
- What worked: reducing interaction complexity, removing unstable calendar detail, compact recurring-holiday indicators, moderate recency weighting, stronger leaf regularization, full-row fitting with feature diversity, and faster row-wise categorical preparation.
- What did not: high-cardinality route/carrier-airport crosses, inferred airport coordinates, more exact seasonality, stronger recency weighting, chronological early stopping on a reduced fitting partition, ranking loss, larger full-model ensembles, and the tested constrained/cyclic time representations. Dropout tied a previous best but cost more; extra boosting rounds added no useful improvement.
- Next ideas: study structured operational interaction constraints that preserve useful calendar effects; examine the L1/boosting-round tradeoff around the successful compact model; explore target-statistic features only with separate training-only lookup fitting to avoid self-label leakage, with no additional evaluation metric or CV.
- Final audit passed: all 47 result rows match harness timing records; every attempted commit has its saved artifact; every run respected training/evaluation limits; kept AUC never decreased. Saved best preparation works in a fresh process, gives identical batch and single-row features including unknown categories, and produces identical features after changing labels. Its globals contain fitted lookups rather than the training frame or data path.
- Only train.py changed in tracked files. Harness and repository instructions are unchanged. Output logs remain uncommitted. No holdout data or human-only tools/results were accessed.
- The branch was restored to ade4fcf. Final audit/report showed 59m24s elapsed, including 15m23s in harness runs. The authoritative final stop time is recorded by the immediately following harness stop command.
