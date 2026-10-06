# Research log: oct6

## Setup — 2026-10-06

- Branch: `oct6`, created directly from starting HEAD `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py`.
- Verified that `data/train.csv` and `data/eval.csv` exist without reading evaluation data.
- Initialized `output/results.tsv` with the required header only.
- Baseline code is unchanged; no experiments have run and the clock has not started.
- On user confirmation, the first action is `python3 harness.py start`, followed by the unchanged baseline through `python3 harness.py run`.
- Research external sources before the first non-baseline experiment; record hypotheses, sources, outcomes, and keep/discard decisions here.

## Baseline — b15ec66

Unchanged starter: 100 trees, depth 6, learning rate 0.1, native categorical columns.
Eval AUC **0.6743**, training phase 1.4s, evaluation phase 30.6s. Kept.
Train-only inspection: 200,000 complete rows, balanced target, 283 origins/destinations, 20 carriers; calendar fields use `c-N` strings. Eight CPU cores available.

## Initial research

- [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): control complexity and use shrinkage/subsampling; smaller learning rates require more rounds.
- [Parameter definitions](https://xgboost.readthedocs.io/en/stable/parameter.html): checked depth, child-weight, regularization, and categorical split controls.
- [Categorical tutorial](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html): native partitions group categories by learned responses; category mappings must remain consistent at inference.
- [AWS tuning ranges](https://docs.aws.amazon.com/sagemaker/latest/dg/xgboost-tuning.html): practical search dimensions include learning rate, rounds, child weight, and subsampling.
- [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): temporal and airport/carrier context are relevant candidate feature families. Search excerpt available; full-page fetch failed. Only features derivable from the allowed input columns will be considered.

## Experiment 1 — regularized longer boosting

Classification: exploration. Hypothesis: the baseline's depth-6 categorical partitions can fit 2005-specific noise; depth 5, child weight 20, L2 10, and 80% row sampling should improve transfer. Use 400 rounds at learning rate 0.05 to learn stable effects gradually. Features unchanged. Motivated by the initial XGBoost research above.

Result: experiment 1, commit `791cc82`, Eval AUC **0.6781**, **keep**. Previous best 0.6743 at `b15ec66`.
- Training time: 2.0s
- Eval time: 30.8s
- Run time: 33.8s (training 2.8s, eval 31.0s, ok)

## Experiment 2 — simplify categorical preparation

Classification: ablation/simplification of experiment 1. Hypothesis: constructing the dataframe once and letting fixed categorical levels map unknown values to missing values removes redundant membership tests and repeated assignment. Exact feature equality is checked on training examples and synthetic unknown categories before running. Keep on equal AUC only if evaluation becomes faster.

Result: experiment 2, commit `25542f4`, Eval AUC **0.6781**, **keep**. Previous best 0.6781 at `791cc82`.
- Training time: 2.0s
- Eval time: 18.6s
- Run time: 21.5s (training 2.8s, eval 18.8s, ok)

Experiment 2 verification: exact equality to the old features and batch-versus-single-row equality passed, including a synthetic unseen origin. The first scratch check needed `__file__` populated in its execution namespace; corrected without changing training code. Eval time fell from 30.8s to 18.6s, justifying the equal-score keep. Pandas emitted deprecation warnings for unseen categories; use fixed-index codes in a later preparation change.

## Experiment 3 — remove day-of-month

Classification: ablation/simplification of the current model. Hypothesis: arbitrary day-of-month categories can memorize 2005-specific weather or calendar events; the training-only means have isolated peaks (16th, 22nd, 28th), with no convincing ordinal trend. Removing the feature may improve year-to-year transfer and simplify the model. Other settings remain fixed.

Feature research read before this category of change: [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses ordinal and cyclic representations; [flight-delay paper](https://www.mdpi.com/2226-4310/8/6/152) describes schedule-derived temporal features. Later experiments will compare stable temporal representations rather than assuming fine calendar identity transfers.

Result: experiment 3, commit `ca98ffe`, Eval AUC **0.6786**, **keep**. Previous best 0.6781 at `25542f4`.
- Training time: 1.9s
- Eval time: 16.2s
- Run time: 19.0s (training 2.6s, eval 16.4s, ok)

## Experiment 4 — carrier-airport categorical interactions

Classification: exploration. Hypothesis: explicit carrier-origin and carrier-destination identities capture operational differences without requiring two separate tree splits. Keep experiment 3's settings and add these two categories, with levels fitted only on train. Supported by the previously cited flight-delay research's airport/carrier context and XGBoost's categorical partitioning tutorial. Also use fixed-index category codes to preserve unknown-as-missing behavior without pandas deprecation warnings. This coding change preserves existing categories exactly.

Result: experiment 4, commit `f6c57bb`, Eval AUC **0.6722**, **discard**. Previous best 0.6786 at `ca98ffe`.
- Training time: 2.5s
- Eval time: 13.4s
- Run time: 17.1s (training 3.4s, eval 13.7s, ok)

Observation from experiment 4: adding high-cardinality carrier-airport pairs reduced AUC by 0.0064. This argues against unregularized expansion of categorical identities. The fixed-index category construction was faster and is reused because it preserves the original features and avoids warnings.

## Experiment 5 — departure-time decomposition

Classification: exploration. Hypothesis: hour/minute components and sine/cosine of minutes since midnight expose schedule structure and the midnight boundary more directly than HHMM alone. Train-only delay rates rise through the day and fall late at night. Add these four features to experiment 3, leaving model hyperparameters fixed. Research basis: the scikit-learn time-feature example and flight-delay schedule features cited above; no assumption that this necessarily helps trees.

Result: experiment 5, commit `0b6ef6a`, Eval AUC **0.6790**, **keep**. Previous best 0.6786 at `ca98ffe`.
- Training time: 2.0s
- Eval time: 9.0s
- Run time: 11.9s (training 2.8s, eval 9.2s, ok)

## Experiment 6 — restrict categorical partitions

Classification: follow-up to experiments 1 and 5, informed by experiment 4's failure. Hypothesis: small categorical partitions will learn reusable airport effects more conservatively than broad arbitrary groups. Change only `max_cat_threshold` from the default to 8. The XGBoost parameter reference identifies this control as categorical regularization. The time features and fixed-index preparation from experiment 5 stay in place.

Result: experiment 6, commit `ca7d3df`, Eval AUC **0.6806**, **keep**. Previous best 0.6790 at `0b6ef6a`.
- Training time: 1.6s
- Eval time: 8.8s
- Run time: 11.5s (training 2.5s, eval 9.0s, ok)

## Experiment 7 — extend conservative boosting

Classification: follow-up to experiment 6. Hypothesis: limiting category partitions reduced overfitting but may require more additive steps to learn airport effects. Double rounds from 400 to 800, keeping the learning rate, depth, features, and all regularization fixed. This is a capacity test of the newly constrained model, not a seed search.

Result: experiment 7, commit `6091e98`, Eval AUC **0.6805**, **discard**. Previous best 0.6806 at `ca7d3df`.
- Training time: 3.0s
- Eval time: 9.1s
- Run time: 13.2s (training 3.8s, eval 9.3s, ok)

## Experiment 8 — holiday-relative calendar feature

Classification: exploration. Hypothesis: distance to major travel holidays captures recurring demand patterns that raw day-of-month could not transfer across years. Add only clipped signed distance to the nearest New Year, Memorial Day, Independence Day, Labor Day, Thanksgiving, or Christmas. Movable dates are derived from each row's month/day/weekday, using the non-leap calendar shared by 2005 and 2006. All computation is row-local. [OPM calendar definitions](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay/) verified the movable-holiday rules. Retain the 400-round model after experiment 7 failed to improve.

Result: experiment 8, commit `e5659ef`, Eval AUC **0.6808**, **keep**. Previous best 0.6806 at `ca7d3df`.
- Training time: 1.6s
- Eval time: 10.4s
- Run time: 13.1s (training 2.5s, eval 10.6s, ok)

## Experiment 9 — require more evidence per leaf

Classification: follow-up to categorical regularization in experiment 6. Hypothesis: increasing child weight from 20 to 100 suppresses small airport/calendar/time interactions that may not transfer into 2006. Change only this parameter; retain holiday proximity after its small improvement. This tests minimum leaf support rather than the number of categories searched or the boosting duration.

Result: experiment 9, commit `0b04d34`, Eval AUC **0.6819**, **keep**. Previous best 0.6808 at `e5659ef`.
- Training time: 1.8s
- Eval time: 10.4s
- Run time: 13.3s (training 2.7s, eval 10.6s, ok)

## Experiment 10 — shallow interaction ablation

Classification: ablation/simplification of experiment 9. Hypothesis: depth-5 trees still combine airport identities with too many calendar/time conditions; depth 3 may capture the dominant schedule, airline, and location effects more robustly. Change depth only, leaving 400 rounds and child weight 100 fixed. If equal AUC, the smaller, faster trees qualify for a keep.

Result: experiment 10, commit `0c0ac39`, Eval AUC **0.6773**, **discard**. Previous best 0.6819 at `0b04d34`.
- Training time: 2.2s
- Eval time: 10.3s
- Run time: 13.6s (training 3.1s, eval 10.6s, ok)

## Synthesis after experiments 1–10

Best: **0.6819**, `0b04d34`, versus baseline 0.6743. Native categorical regularization (small partitions and child weight 100) provided clear gains. Day-of-month removal, time decomposition, and holiday proximity helped modestly. Raw carrier-airport categories hurt substantially; doubling boosting duration did not help; depth 3 underfit, indicating that some richer interactions remain necessary. Preparation simplification reduced evaluation from ~31s to ~10s while preserving row invariance.

Current theory: transfer from 2005 to 2006 rewards regularized location/schedule interactions, with explicit categorical combinations otherwise too noisy. Next directions: smoothed label-independent-at-inference encodings, train-fitted schedule context, and variance reduction through ensembles.

Fresh research at the ten-experiment pause:
- [Regularized target encoding benchmark](https://arxiv.org/abs/2104.00629): motivates testing a smoothed numerical representation for high-cardinality categories.
- [scikit-learn cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html): encoding a training row using its own label can cause overfitting.
- [CatBoost paper](https://arxiv.org/abs/1706.09516): ordered target statistics address a related source of prediction shift.
- [XGBoost random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html): parallel trees can be combined with boosting and subsampling.
- [One-hot GBDT robustness paper](https://arxiv.org/abs/2304.13761): this paper encodes TREE LEAVES, not raw input categories; it does not directly support replacing airport categories with one-hot input features.

## Experiment 11 — deterministic cross-fitted target statistics

Classification: exploration. Hypothesis: smoothed origin, destination, carrier-airport, and route delay rates provide more stable interactions than experiment 4's raw identities. Fit five sets of lookup tables on train only, excluding each hash-assigned fold. A row's fold is a deterministic hash of its allowed predictor values, independent of its target and dataframe index. The same row always uses the same out-of-fold table, even when evaluated alone. Thus no training row contributes its target to its own encoding. Use smoothing 100 toward 0.5; no counts are emitted as features. This is feature fitting only, with no cross-validation model evaluation or extra metric. Native categories and the existing XGBoost model remain in place.

Result: experiment 11, commit `04a1e37`, Eval AUC **0.6823**, **keep**. Previous best 0.6819 at `0b04d34`.
- Training time: 1.8s
- Eval time: 20.3s
- Run time: 24.0s (training 3.5s, eval 20.5s, ok)

## Experiment 12 — replace airport identities with smoothed rates

Classification: ablation/simplification of experiment 11. Hypothesis: numerical cross-fitted risk features capture stable airport and carrier-airport effects, while native airport identities may still encourage year-specific interactions. Remove only native Origin and Dest columns from the model. Retain all rate lookups, which still use those input values as keys. This tests whether the categorical identities provide useful residual information.

Result: experiment 12, commit `43782c7`, Eval AUC **0.6808**, **discard**. Previous best 0.6823 at `04a1e37`.
- Training time: 1.7s
- Eval time: 18.5s
- Run time: 22.0s (training 3.3s, eval 18.8s, ok)

## Experiment 13 — geography inferred from route distances

Classification: exploration. Hypothesis: a low-dimensional representation of airport geography can share spatial patterns across airports, supplementing identity-specific effects. Build an undirected graph using median observed route distances from train, compute shortest-path distances, and obtain three classical scaling coordinates. These are inferred geometric axes, not externally sourced latitude/longitude. Add three coordinates for each endpoint, with unknown airports mapped to missing values. Read-only training inspection found all 284 airports connected and the major-airport coordinates geographically plausible.

Research: [scikit-learn Isomap description](https://scikit-learn.org/stable/modules/manifold.html#isomap) explains shortest-path distances and eigendecomposition; [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html) provides the installed graph routine. This adapts those ideas to the observed route graph. No row counts or external data are used as features.

Result: experiment 13, commit `beb5f09`, Eval AUC **0.6834**, **keep**. Previous best 0.6823 at `04a1e37`.
- Training time: 2.0s
- Eval time: 21.2s
- Run time: 25.2s (training 3.7s, eval 21.4s, ok)

## Experiment 14 — departure time relative to schedule context

Classification: exploration. Hypothesis: the same local departure time has different meaning for different airports and routes; train-fitted medians can provide this context without introducing noisy category identities. Add departure minutes minus median departure minutes for Origin, Dest, Origin-Dest, and Carrier-Origin. These are target-free fitted lookups, not aggregates over the evaluation input. Research: the flight-delay schedule feature literature cited earlier and [scikit-learn's training-only preprocessing guidance](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage); this also follows the permitted route-median example in program.md.

Result: experiment 14, commit `17a7273`, Eval AUC **0.6832**, **discard**. Previous best 0.6834 at `beb5f09`.
- Training time: 3.2s
- Eval time: 25.3s
- Run time: 30.6s (training 5.1s, eval 25.5s, ok)

## Experiment 15 — boosted randomized forests

Classification: exploration. Hypothesis: averaging four randomized trees per boosting step reduces variance in the airport, rate, and geographic splits while preserving the needed depth-5 interactions. Set `num_parallel_tree=4` and `colsample_bynode=0.8`, retaining the existing 80% row subsampling and 400 boosting rounds. [XGBoost's random-forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) explicitly supports boosting multiple parallel trees per round. Training so far takes only a few seconds, leaving room under the 60-second limit.

Result: experiment 15, commit `d132fa6`, Eval AUC **0.6841**, **keep**. Previous best 0.6834 at `beb5f09`.
- Training time: 10.1s
- Eval time: 21.6s
- Run time: 33.6s (training 11.8s, eval 21.8s, ok)

## Experiment 16 — ablate parallel trees

Classification: ablation/simplification of experiment 15. Hypothesis: its gain may come from per-node feature sampling rather than the larger ensemble. Remove `num_parallel_tree=4` while keeping `colsample_bynode=0.8`. If AUC is unchanged, prefer the smaller/faster model; otherwise this isolates whether averaging trees contributes to the observed gain.

Result: experiment 16, commit `ee83e59`, Eval AUC **0.6840**, **discard**. Previous best 0.6841 at `d132fa6`.
- Training time: 2.0s
- Eval time: 21.3s
- Run time: 25.3s (training 3.8s, eval 21.5s, ok)

## Experiment 17 — additive calendar effects

Classification: exploration. Hypothesis: month/weekday/holiday interactions with particular airports and routes capture 2005-specific events. Use two disjoint interaction groups: calendar features (Month, DayOfWeek, HolidayOffset), and all other features. This retains rich operational interactions and flexible global calendar effects while preventing them from sharing a tree path. [XGBoost interaction-constraint documentation](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) supports explicit feature groups; disjoint groups avoid the subtleties of overlapping constraints. Restore the four-tree forest because experiment 16 was lower, even though only by 0.0001.

Result: experiment 17, commit `26c89e4`, Eval AUC **0.6816**, **discard**. Previous best 0.6841 at `d132fa6`.
- Training time: 10.1s
- Eval time: 21.7s
- Run time: 33.8s (training 11.9s, eval 21.9s, ok)

## Experiment 18 — simplify inferred geography

Classification: ablation/simplification of experiment 13's geography in the current best model. Hypothesis: the third, weakest geometric direction reflects route-network detours more than stable geographic structure. Remove OriginGeo0 and DestGeo0, retaining the two strongest eigendirections (Geo1, Geo2). The top eigenvalues were approximately 374M, 92M, and 22M, so the discarded axis carries much less distance structure. Keep on equal AUC because the model uses two fewer features.

Result: experiment 18, commit `9ae35ba`, Eval AUC **0.6840**, **discard**. Previous best 0.6841 at `d132fa6`.
- Training time: 9.9s
- Eval time: 21.6s
- Run time: 33.5s (training 11.6s, eval 21.9s, ok)

## Experiment 19 — stronger smoothing of target statistics

Classification: follow-up to experiment 11. Hypothesis: rare carrier-airport and route rates still vary too much across training folds and years. Increase the smoothing prior strength from 100 to 500 observations, keeping its mean at 0.5. All five deterministic out-of-fold lookup structures and model settings remain fixed. This changes the reliability shrinkage of target statistics, not XGBoost leaf support. Motivated by the regularized target-encoding benchmark cited above. Also reviewed [hierarchical target-encoder documentation](https://contrib.scikit-learn.org/category_encoders/targetencoder.html) as a possible later extension; no new package is installed or used.

Result: experiment 19, commit `7439161`, Eval AUC **0.6841**, **discard**. Previous best 0.6841 at `d132fa6`.
- Training time: 10.0s
- Eval time: 21.8s
- Run time: 33.8s (training 11.8s, eval 22.0s, ok)

## Experiment 20 — route direction in inferred geography

Classification: follow-up to experiment 13. Hypothesis: endpoint-coordinate differences normalized by route distance expose broad directional travel patterns that separate endpoint splits cannot express compactly. Add three inferred direction components; retain the full original geographic coordinates. This is an algebraic transformation of the train-fitted geometry and the row's distance, independent of labels and other evaluation rows. Experiment 19 tied AUC but had no meaningful simplification or speed benefit, so its smoothing change was discarded.

Result: experiment 20, commit `8592a63`, Eval AUC **0.6837**, **discard**. Previous best 0.6841 at `d132fa6`.
- Training time: 12.2s
- Eval time: 22.8s
- Run time: 37.0s (training 13.9s, eval 23.1s, ok)

## Synthesis after experiments 11–20

Best: **0.6841**, `d132fa6`. Cross-fitted delay-rate encodings helped modestly, and the target-free airport geometry improved AUC more clearly. Both raw airport identities and all three geometry axes still contribute. Parallel randomized trees improved the score, although their advantage over feature sampling alone was only 0.0001. Schedule-relative medians, additive calendar restrictions, stronger target smoothing, and explicit route directions did not improve the best model.

Current theory: the model needs location/calendar interactions, but benefits from stable numerical context and averaging. The last three experiments changed AUC by less than 0.001 without a keep, so this is also a plateau research pause. Stop local representational tweaks and explore a different objective, then revisit model capacity and smoothing in light of the result.

Fresh research:
- [AUC pairwise optimization consistency](https://arxiv.org/abs/1208.0645) motivates logistic pairwise surrogate losses for ranking.
- [XGBoost learning-to-rank guide](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) describes unscaled RankNet pairwise loss and sampled-pair construction.
- [Original RankNet paper](https://www.microsoft.com/en-us/research/publication/learning-to-rank-using-gradient-descent/) explains the pairwise probabilistic objective.

## Experiment 21 — pairwise ranking objective

Classification: exploration. Hypothesis: optimizing relative ordering of delayed and on-time flights can improve the AUC objective compared with pointwise logistic training. Use XGBRanker with `rank:pairwise`, one global query group, mean pair sampling, and one sampled pair per example. Keep all best features and tree settings. A thin saved wrapper applies a monotonic sigmoid to rank scores to provide `predict_proba`; it does not change the harness or compute a new evaluation metric. Training stays on the allowed training set only.

Result: experiment 21, commit `4dff55d`, Eval AUC **0.6800**, **discard**. Previous best 0.6841 at `d132fa6`.
- Training time: 23.7s
- Eval time: 22.1s
- Run time: 47.8s (training 25.4s, eval 22.4s, ok)

## Experiment 22 — deeper trees with stable representations

Classification: follow-up to experiments 11, 13, and 15. Hypothesis: the rate/geography features and stronger regularization now permit useful richer interactions that the old baseline lacked. Increase depth from 5 to 7, keeping child weight 100, categorical threshold 8, feature sampling, and four parallel trees. Experiment 10 showed that depth 3 underfit; this tests the opposite capacity direction on the improved representation. Restore pointwise logistic classification after pairwise ranking reduced AUC to 0.6800.

Result: experiment 22, commit `2018053`, Eval AUC **0.6830**, **discard**. Previous best 0.6841 at `d132fa6`.
- Training time: 13.4s
- Eval time: 22.2s
- Run time: 37.7s (training 15.2s, eval 22.5s, ok)

## Experiment 23 — smaller boosting steps

Classification: follow-up to the best regularized forest. Hypothesis: smaller updates yield a more stable optimization path on correlated time/rate/geographic features. Use 1,000 rounds at learning rate 0.02 instead of 400 at 0.05; the nominal rounds-times-rate product remains 20. This differs from experiment 7, which doubled that product before the new features were introduced. Restore depth 5 after depth 7 failed. Research basis: the initial XGBoost shrinkage guidance. Estimated training remains comfortably under 60 seconds.

Result: experiment 23, commit `f479eb2`, Eval AUC **0.6842**, **keep**. Previous best 0.6841 at `d132fa6`.
- Training time: 25.9s
- Eval time: 22.5s
- Run time: 50.5s (training 27.7s, eval 22.8s, ok)

## Experiment 24 — prune weak splits

Classification: follow-up to experiment 23. Hypothesis: with many small boosting steps, weak late-stage splits mostly fit noise. Set gamma=5 so each additional split must provide sufficient training-loss reduction. Keep depth, child weight, all features, and ensemble configuration unchanged. [XGBoost's tree objective](https://github.com/dmlc/xgboost/blob/master/doc/tutorials/model.rst) and the parameter reference distinguish this split penalty from L2 leaf regularization. Equal AUC will only be kept if the measured run is meaningfully faster.

Result: experiment 24, commit `3b822ee`, Eval AUC **0.6837**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 21.1s
- Eval time: 22.5s
- Run time: 45.7s (training 22.8s, eval 22.9s, ok)

## Experiment 25 — average independent boosting paths

Classification: follow-up to experiment 15's variance reduction. Hypothesis: averaging models that follow independent boosting trajectories provides more diversity than averaging four trees within every common boosting round. Fit four 1,000-tree models with fixed seeds 42, 137, 271, and 419, then average their probabilities with equal weights. This uses the same nominal total 4,000 trees as the incumbent 1,000-round four-tree forest. No seed is selected separately and no model receives additional data. The saved model is the complete ensemble. Research basis: [scikit-learn's ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier) describes probability averaging for robustness. Remove gamma after its lower AUC.

Result: experiment 25, commit `a229779`, Eval AUC **0.6838**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 20.3s
- Eval time: 22.8s
- Run time: 45.1s (training 22.0s, eval 23.1s, ok)

## Experiment 26 — label-smoothed logistic objective

Classification: exploration. Hypothesis: softer targets reduce confidence in 2005-specific outcomes and improve transfer. Keep the binary labels and evaluation unchanged; only the training loss uses targets 0.05/0.95 through an explicit logistic gradient and Hessian. [Label-smoothing research](https://arxiv.org/abs/1906.02629) studies neural networks, so applying the idea to this tree model is an experimental adaptation rather than a directly established result. [XGBoost custom-objective documentation](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html) explains the gradient/Hessian interface. The installed classifier implementation retains the binary-logistic prediction link for a callable objective.

Result: experiment 26, commit `b06cf76`, Eval AUC **0.6839**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 27.0s
- Eval time: 22.9s
- Run time: 52.0s (training 28.7s, eval 23.3s, ok)

## Plateau research after experiments 24–26

Three consecutive small discards (0.6837, 0.6838, 0.6839) versus 0.6842 triggered a research pause. Revisited the official categorical tutorial and XGBoost implementation documentation. The installed 3.4.1 model configuration confirms `max_cat_to_onehot=4`; newer development documentation changes that default, so installed behavior was checked directly. One-category-versus-rest splitting is an untested alternative to the learned category partitions.

## Experiment 27 — native one-hot categorical splits

Classification: exploration. Hypothesis: independent category effects generalize better than learned groups of airports/carriers/months. Set `max_cat_to_onehot=512`, exceeding every categorical cardinality, and remove the now-unused categorical partition threshold. Keep the learned numerical features, model size, and regularization fixed. [Official categorical documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) and [implementation parameter documentation](https://github.com/dmlc/xgboost/blob/master/python-package/xgboost/sklearn.py) describe the two split strategies. No dense one-hot dataframe is constructed.

Result: experiment 27, commit `feb6da9`, Eval AUC **0.6834**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 22.1s
- Eval time: 22.6s
- Run time: 46.7s (training 23.8s, eval 22.9s, ok)

## Experiment 28 — time-specific airport and carrier risk

Classification: follow-up to experiment 11 with a new interaction family. Hypothesis: airport and airline effects differ by time of day, so add cross-fitted, smoothed rates for Origin×three-hour departure block, Dest×block, and Carrier×block. Keep the same five deterministic folds and smoothing 100. This remains a rate feature fitted on train, never a contemporaneous aggregate or traffic count. [Airport delay temporal research](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071) and [delay propagation analysis](https://www.mdpi.com/2227-7390/13/21/3551) motivate airport/time interactions; only schedule information available in the supplied row is used. Restore categorical partitioning after native one-hot splits scored 0.6834.

Result: experiment 28, commit `1ca343c`, Eval AUC **0.6837**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 25.9s
- Eval time: 26.0s
- Run time: 54.5s (training 28.1s, eval 26.4s, ok)

## Experiment 29 — remove redundant standalone airport rates

Classification: ablation/simplification of the kept rate features. Hypothesis: OriginRisk and DestRisk are redundant with native airport categories and geometric context, and their fold variability adds noise. Both had low gain importance in the best model, while carrier-airport rates were much stronger. Remove only these two lookup features, retaining the three interaction risk features. Recent [XGBoost feature-selection guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) and [scikit-learn feature selection discussion](https://scikit-learn.org/stable/modules/feature_selection.html) motivate an explicit ablation; no independent validation/CV metric is introduced.

Result: experiment 29, commit `1ac61f1`, Eval AUC **0.6841**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 27.6s
- Eval time: 22.3s
- Run time: 51.8s (training 29.1s, eval 22.6s, ok)

## Experiment 30 — cyclic month representation

Classification: exploration. Hypothesis: treating the year as a cycle favors nearby seasonal groupings that transfer across years better than unconstrained month categories. Replace native Month with sine/cosine of its 12-month position, while retaining all operational interactions and the holiday feature. The earlier time-feature research supports this representation as an option; tree models may already handle the original categories well, so this is a direct test, not an assumed improvement. Restore standalone airport rates after their removal scored 0.6841.

Result: experiment 30, commit `a3d9afd`, Eval AUC **0.6838**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 25.1s
- Eval time: 21.7s
- Run time: 48.8s (training 26.9s, eval 22.0s, ok)

## Synthesis after experiments 21–30

Best: **0.6842**, `f479eb2`. The sole improvement in this block was lower learning rate with proportionally more rounds. Pairwise ranking, label smoothing, deeper trees, pruning, independent-trajectory averaging, native one-hot categories, time-specific rate encodings, and cyclical month did not improve. Removing low-gain standalone airport rates was also slightly worse. The current representation appears close to a local plateau; individual small differences should not be overinterpreted, but every decision followed the printed four-decimal keep rule.

Fresh research: [XGBoost growth-policy documentation](https://github.com/dmlc/xgboost/blob/master/doc/parameter.rst), [original histogram/lossguide implementation discussion](https://github.com/dmlc/xgboost/issues/1950), and [leaf-wise tree-growth description](https://lightgbm.readthedocs.io/en/stable/Features.html#leaf-wise-best-first-tree-growth). These motivate allocating a fixed leaf budget by loss reduction instead of forcing uniform depth. Only XGBoost will be trained; no package changes.

## Experiment 31 — loss-guided tree growth

Classification: exploration. Hypothesis: a 24-leaf budget focused on the highest-gain branches can express important uneven interactions more efficiently than depth-5 trees. Set grow_policy=lossguide, max_depth=0, max_leaves=24, retaining all other best settings. This differs from merely increasing depth: the total leaf budget is explicitly bounded and growth is prioritized by loss reduction.

Result: experiment 31, commit `e51417d`, Eval AUC **0.6842**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 31.9s
- Eval time: 22.7s
- Run time: 56.7s (training 33.7s, eval 23.1s, ok)

Experiment 31 tied AUC but increased training from 25.9s to 31.9s and artifact size from 23.5MB to 32.9MB; no equal-score keep justification exists.

## Experiment 32 — bracket minimum leaf support

Classification: follow-up to experiment 9. Hypothesis: the earlier gain when increasing child weight from 20 to 100 may continue with more conservative local estimates in the richer model. Test child weight 300, keeping the best depth-5 small-step forest otherwise unchanged. This brackets the successful regularization direction; it is not a repeated seed or cosmetic variation.

Result: experiment 32, commit `6902660`, Eval AUC **0.6838**, **discard**. Previous best 0.6842 at `f479eb2`.
- Training time: 26.6s
- Eval time: 22.5s
- Run time: 51.1s (training 28.4s, eval 22.8s, ok)

## Experiment 33 — stronger leaf-value shrinkage

Classification: follow-up to the regularization results. Hypothesis: shrinking noisy leaf estimates continuously can help even though the hard child-weight increase removed useful structure. Restore child weight 100 and increase L2 lambda from 10 to 100. Split eligibility, depth, features, and boosting schedule stay unchanged. This tests leaf-output magnitude rather than minimum leaf support or gamma pruning. The XGBoost objective/parameter documentation supplies the mechanism.

Result: experiment 33, commit `c58ee9e`, Eval AUC **0.6843**, **keep**. Previous best 0.6842 at `f479eb2`.
- Training time: 25.3s
- Eval time: 23.0s
- Run time: 50.4s (training 27.0s, eval 23.4s, ok)

## Experiment 34 — blend complementary model capacities

Classification: exploration/follow-up to ensemble research. Hypothesis: a depth-4 model may make complementary errors to the best depth-5 forest, even though averaging equally complex independently seeded models did not help. Fit the incumbent and an auxiliary 1,500-round depth-4 single-tree-per-round classifier, then combine probabilities at fixed weights 0.75/0.25. Both use the same prepared training set and L2=100; no weights or seeds are selected through extra scoring. [Dietterich's ensemble review](https://web.engr.oregonstate.edu/~tgd/publications/mcs-ensembles.pdf) motivates accurate, diverse members. Predicted total training is under 60 seconds. The prior best artifact also passed an independent-load, row-invariance, finite-probability check using training rows only.

Result: experiment 34, commit `248ec70`, Eval AUC **0.6842**, **discard**. Previous best 0.6843 at `c58ee9e`.
- Training time: 32.1s
- Eval time: 22.6s
- Run time: 56.9s (training 33.8s, eval 23.0s, ok)

### Experiment 35 — coarser histogram bins

Sources: https://xgboost.readthedocs.io/en/stable/treemethod.html and https://xgboost.readthedocs.io/en/stable/parameter.html explain that max_bin controls the discretization of numerical predictors (default 256), trading split accuracy against computation. Hypothesis: 64 bins may regularize the continuous airport geometry and target-risk features and improve transfer to 2006. Keep all other best-model settings fixed.

Classification: exploration of numerical split discretization.

Result: experiment 35, commit `f0eb202`, **crash / interrupted**. Training completed in 24.7s and the artifact was saved, but the process ended during evaluation without an Eval AUC or completed run summary. No process remained to resume. The TSV uses 0.0000 as the required failure placeholder, not a measured score. Discard and restore `c58ee9e`; fewer than two minutes remained, so no new experiment was started.

## Final summary

Best Eval AUC: **0.6843** at `c58ee9e` on branch `oct6`, versus baseline **0.6743**: absolute gain **0.0100**. Completed 34 scored experiments after the baseline; the 35th trial was interrupted during evaluation and discarded without a score. Across all 36 logged runs: 13 keep (including baseline), 22 discard, 1 interrupted/crash.

What worked: stronger regularization and categorical split limits; removing the raw day-of-month category; scheduled-time and holiday-offset features; deterministic cross-fitted, smoothed target-risk lookups; airport geometry learned only from training route distances; randomized parallel trees; smaller boosting steps; and stronger L2 leaf shrinkage. The final classifier uses 1,000 boosting rounds with four parallel depth-5 trees per round, learning rate 0.02, child weight 100, and L2 lambda 100.

What did not help: raw high-cardinality route/carrier categories, excessive tree depth or shallow capacity, hard interaction restrictions, time-relative route features, stronger minimum child support, pairwise ranking, label smoothing, all-category one-hot splits, calendar cycles replacing month, extra time-block risks, and model averaging/blending. Several simplifications tied or narrowly missed, and only changes satisfying the printed-AUC keep rule were retained. The coarser-bin hypothesis remains unresolved because its evaluation was interrupted.

Next ideas: finish the coarse-bin experiment in a fresh budget; test hierarchical shrinkage for carrier-airport target risks; and examine whether simplifying low-value clock features retains AUC. Small eval improvements should be checked on untouched data before drawing conclusions about transfer.

Final verification: independently loaded `/home/ubuntu/xgboost-autoresearch-minimal3/artifacts/c58ee9ee37b2a1fa17a91398fb40c50e7e9caaae.pkl` (22.7 MB); prepared 32 training rows both in a batch and individually with identical features/labels; confirmed changing the supplied labels leaves features unchanged; handled an unseen origin; and produced finite, normalized probabilities. No additional AUC evaluation was performed. The branch matches the best kept commit, tracked files are clean, only `train.py` differs from the starting code, and `save_and_evaluate(model, prepare)` remains the final line. All model fitting used `train.csv`; eval scoring was delegated to the unchanged harness. The holdout and archived results were never accessed.

Closing the experiment clock after entering the required under-two-minute wrap-up window.
