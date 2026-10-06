# Research log: oct6

## Setup — 2026-10-06

- Branch: `oct6`, created directly from the current HEAD (`b15ec66`).
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist.
- Initialized `output/results.tsv` with the required header only.
- Baseline: run the existing, unchanged `train.py` through the harness first.
- Experiment clock has not started; awaiting confirmation to begin.

## Run protocol

On confirmation, the first action is `python3 harness.py start`, followed by the baseline run. Research sources before the first non-baseline experiment, every 10 experiments, at plateaus, and before new categories of changes. Record hypotheses, experiment categories, sources, commits, AUCs, and keep/discard decisions here as experiments proceed.

Only modify `train.py` and the permitted output logs. Read only the training data for model development; let the unchanged harness handle evaluation. Keep features consistent for single-row preparation and commit each model change before running it. Follow the printed AUC keep rule, the 60-second training and 300-second evaluation limits, and the one-hour experiment budget.

## Clock start and initial research

User confirmed go. Started the clock as the first action, then launched the unchanged baseline at `b15ec66`. Training data has 200,000 rows, eight predictors, no missing values, 283 origins/destinations, and 20 carriers. Dates use `c-N` strings; departure time is HHMM.

Sources read before the first non-baseline experiment:
- [XGBoost tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): balance capacity against variance; smaller learning rates need more trees.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, child weight, leaf penalties, sampling, and categorical split controls.
- [Categorical support](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): partition versus one-hot splits; category mappings must remain consistent.
- [SageMaker tuning ranges](https://docs.aws.amazon.com/sagemaker/latest/dg/xgboost-tuning.html): broad ranges are guidance, not a prescription; start with depths 4–8, learning rates 0.03–0.1, and moderate child/leaf regularization.
- [Time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): time representations and interactions are candidates for later feature experiments.

Plan: first test whether the short baseline boosting schedule underfits, then adjust regularization and examine time/categorical features. The 2005-to-2006 shift motivates checking generalization using only harness Eval AUC.

## Baseline — b15ec66

Eval AUC 0.6743; training phase 1.5s, evaluation 31.1s. Kept.

## Experiment 1 — exploration

Hypothesis: 100 trees underfit. Increase to 500 trees at learning rate 0.05 (depth and features unchanged), following the XGBoost tuning guide linked above. More total boosting capacity with smaller steps may improve ranking.

Result: **0c25f03 — 0.6707 — discard**. Run time: 34.8s (training 3.6s, eval 31.2s, ok)

## Experiment 2 — ablation/simplification

The longer schedule lost 0.0036 AUC: more boosting alone overfits across years. Before regularizing, remove redundant isin/where before Categorical, which already maps out-of-vocabulary values to NaN. Source: https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html . Hypothesis: identical feature values and AUC with faster row preparation. Equal AUC is acceptable for this simplification.

Result: **38bc84b — 0.6743 — keep**. Run time: 22.5s (training 1.4s, eval 21.1s, ok)

## Experiment 3 — follow-up

Baseline gain importance is dominated by departure time (427), followed by month/carrier (57/55). Experiment 1 suggests excess variance. Test a coherent conservative schedule: 600 trees, eta 0.05, depth 4, min_child_weight 50, lambda 10, subsample 0.8. Hypothesis: sustained shallow learning captures broad stable patterns while limiting sparse category/date interactions. Source: XGBoost tuning and parameter docs above. Experiment 2 emits pandas future warnings for unseen categories, but current behavior is correct; a later explicit-code simplification can remove warnings.

Result: **9a554ae — 0.6787 — keep**. Run time: 24.1s (training 3.1s, eval 21.0s, ok)

## Experiment 4 — ablation/simplification

Regularized shallow trees gained 0.0044 over baseline. Remove DayofMonth from predictors. Hypothesis: day-of-month category interactions memorize 2005 weather/calendar shocks that move in 2006, whereas month and weekday preserve more stable effects. This isolates one potentially unstable predictor.

Result: **6db680f — 0.6792 — keep**. Run time: 22.7s (training 3.9s, eval 18.8s, ok)

## Experiment 5 — ablation/simplification

Explicit fixed category code dictionaries and cached CategoricalDtype objects replace repeated inference; build the feature frame once. Hypothesis: equivalent features with less per-row overhead and no future warnings for unknown categories. Verified exact equality of all training features against prior prepare, five batch-versus-single-row cases, and missing encoding for a synthetic unseen airport. Sources: pandas Categorical and XGBoost category consistency docs above. Equal AUC is acceptable if faster.

Result: **d0d5ebc — 0.6792 — keep**. Run time: 8.2s (training 3.0s, eval 5.1s, ok)

## Experiment 6 — exploration

Switch all categorical predictors from partition grouping to one-hot-style splits via max_cat_to_onehot=512, preserving 600-tree schedule and other settings. Hypothesis: splitting individual airport/carrier categories is less prone to fitting noisy gradient-based category groups across years. Source: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html .

Result: **ebf37a5 — 0.6789 — discard**. Run time: 7.5s (training 2.6s, eval 4.9s, ok)

## Experiment 7 — exploration

One-hot-only splits scored 0.6789, slightly below best, and were discarded. New research: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html . Restrict Month to additive trees while allowing all non-month features to interact. Hypothesis: seasonality is useful but month-by-airport/carrier interactions encode year-specific shocks. Read the CatBoost paper (https://arxiv.org/abs/1706.09516) and sklearn TargetEncoder docs (https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) for later encoding ideas; target leakage must be avoided, and no cross-validation metric will be introduced.

Result: **d47b8e6 — 0.6804 — keep**. Run time: 7.7s (training 2.9s, eval 4.8s, ok)

## Experiment 8 — exploration

Add departure hour and minute-within-hour as numerical features, retaining HHMM. Hypothesis: coarse daily patterns and within-hour scheduling structure are easier to learn separately; minutes need not have the same effect as the overall time of day. Source: sklearn time-feature example linked in initial research. Month isolation improved AUC to 0.6804 and remains. All features are row-local.

Result: **a154928 — 0.6804 — discard**. Run time: 8.9s (training 3.2s, eval 5.6s, ok)

## Experiment 9 — follow-up

Hour/minute features tied at 0.6804 but add complexity and evaluation cost, so discarded. Test depth 2 with 1600 trees instead of depth 4 with 600. Hypothesis: low-order interactions transfer better; additional shallow trees compensate for the smaller tree capacity. This differs from experiment 1 by controlling interaction order and retaining strong regularization and month isolation.

Result: **da30290 — 0.6788 — discard**. Run time: 9.3s (training 4.3s, eval 4.9s, ok)

## Experiment 10 — follow-up

Depth 2 underperformed (0.6788), so useful interactions exceed purely pairwise effects. Test max_cat_threshold=16 with the depth-4 best model. This regularizes category partition search without forcing the one-hot-only strategy from experiment 6. Hypothesis: moderate category grouping preserves useful airport interactions while reducing noisy large partitions. Source: XGBoost parameter reference. Training hour means rise strongly from 05:00 to 20:00 but fall late at night, so a global monotonic departure-time constraint is not justified.

Result: **e546c33 — 0.6821 — keep**. Run time: 7.6s (training 2.7s, eval 4.9s, ok)

## Synthesis after experiments 1–10

Best is 0.6821 at e546c33 (+0.0078 over baseline). Broad regularization, excluding day of month, additive month effects, and restricting category search helped. More unconstrained boosting, depth two, one-hot-only splits, and redundant time decomposition did not. Cached category preparation reduced evaluation from 31s to 5s with identical AUC. Current theory: stable time-of-day effects plus moderate airport/carrier interactions matter; calendar shocks and flexible category grouping overfit 2005. Next examine variance reduction and schedule-relative features.

Research refresh: searched XGBoost boosted forests and flight-delay papers. [Boosted forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) average multiple randomized trees per boosting step. [Airport situational awareness](https://arxiv.org/abs/1911.01605) and [delay absorption](https://arxiv.org/abs/2512.08197) motivate schedule context, but their additional operational/weather data are unavailable here; use only train-fitted schedule summaries.

## Experiment 11 — exploration

Set num_parallel_tree=4, retaining row subsample 0.8 and the best schedule. Hypothesis: averaging randomized gradient fits reduces category noise without discarding the useful depth-4 interactions.

Result: **15706bd — 0.6823 — keep**. Run time: 16.8s (training 11.4s, eval 5.3s, ok)

## Experiment 12 — exploration

Add departure minutes relative to train-fitted route and carrier-origin medians. Hypothesis: schedule context makes the effect of flight timing easier to transfer across networks. This adapts the schedule-context idea from the flight-delay papers read above and the allowed median-lookup example in program.md. No counts or target statistics are used. Lookups are fitted once on train, and prepare only reads each row plus fixed tables.

Result: **6924641 — 0.6824 — keep**. Run time: 18.1s (training 12.0s, eval 6.1s, ok)

## Experiment 13 — exploration

Schedule residuals gained 0.0001 AUC; checked identical batch/single-row features. New direction: infer low-dimensional airport geometry from the route distances in train.csv. Build an undirected distance graph, compute shortest-path distances, and use classical MDS coordinates as origin/destination features. Hypothesis: shared regional structure pools information across airports and supports smoother generalization than category identities alone. Sources: https://scikit-learn.org/stable/modules/manifold.html#isomap and https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html . Coordinates are an approximation derived only from training distances, not external geographic data. No counts are features.

Result: **e4ba7f5 — 0.6825 — keep**. Run time: 19.6s (training 13.3s, eval 6.3s, ok)

## Experiment 14 — follow-up

Airport geometry gained 0.0001 to 0.6825; embedding covers 284 airports and batch/single-row checks passed. Test depth 6 with all other best settings fixed. Hypothesis: restricted category search, month isolation, and tree averaging now provide enough regularization to benefit from deeper carrier/airport/time interactions. This revisits depth only after materially changing the regularization and feature context, unlike the unregularized baseline.

Result: **933e0ed — 0.6825 — discard**. Run time: 22.3s (training 15.7s, eval 6.6s, ok)

## Experiment 15 — follow-up

Depth 6 tied at 0.6825 with more complexity and runtime, so discarded. Halve the best boosting schedule from 600 to 300 rounds. Hypothesis: even the regularized model may fit year-specific residuals late in training; a shorter schedule could improve transfer or tie with a smaller model. This directly probes the remaining overfitting risk and tests simplification.

Result: **f2762dd — 0.6819 — discard**. Run time: 13.2s (training 7.2s, eval 6.0s, ok)

## Experiment 16 — follow-up

Neither extra depth nor halving rounds improved the current model. Add gamma=5, leaving depth, rounds, and features fixed. Hypothesis: a minimum split-gain threshold suppresses low-signal residual partitions while retaining the useful boosting horizon. Source: XGBoost gamma definition in the parameter reference.

Result: **1b41f21 — 0.6824 — discard**. Run time: 19.1s (training 12.5s, eval 6.6s, ok)

## Plateau research and experiment 17 — exploration

Experiments 14–16 were three discards within 0.001 of best. Paused parameter tuning and searched holiday feature modeling. Sources: https://facebook.github.io/prophet/docs/holiday_effects.html and https://facebook.github.io/prophet/docs/seasonality,_holiday_effects,_and_regressors.html . Adapt the recurring-event window idea, without using Prophet or adding dependencies. Hypothesis: Thanksgiving, Christmas/New-Year vicinity, and summer holiday windows align across years better than raw dates. Infer the weekday calendar from each row's month/day/weekday; both specified years are non-leap years. Keep each holiday feature additive to reduce single-year event overfitting.

Result: **97c8784 — 0.6843 — keep**. Run time: 21.6s (training 12.9s, eval 8.7s, ok)

## Experiment 18 — exploration

Holiday windows improved to 0.6843; known-date and batch/single-row checks passed. Test honest smoothed target-rate features for Origin, Dest, carrier, route, carrier-origin, and carrier-destination. Reserve a fixed random 25% of train solely to fit rate tables; fit XGBoost on the other 75%. Thus no model-fit row contributes its target to its encoded predictors, and prepare is identical for train/eval rows. Retain native categories and unsupervised features. Group sizes are used only internally for mean shrinkage; no count/frequency columns are produced. Sources: CatBoost prediction-shift paper and sklearn TargetEncoder docs from initial research. No CV or auxiliary scoring is performed. Hypothesis: stable historical rates supply useful interactions with less categorical split noise, enough to offset the reduced booster sample.

Result: **13c0e9f — 0.6819 — discard**. Run time: 19.5s (training 10.8s, eval 8.7s, ok)

## Experiment 19 — exploration

Disjoint target encoding lost 0.0024 despite passing scored-label and row-consistency checks. It may sacrifice too many booster rows or add noisy historical rates. Return to the full-data best. Add a native CarrierOrigin categorical feature with a train-fitted vocabulary. Hypothesis: airline-specific airport operating patterns can be expressed as one split rather than requiring multiple conditional category splits. No target statistics or frequencies are used. This extends the categorical representation mechanism documented by XGBoost.

Result: **d15950d — 0.6805 — discard**. Run time: 23.0s (training 14.3s, eval 8.6s, ok)

## Experiment 20 — ablation/simplification

CarrierOrigin categories hurt substantially (0.6805), supporting the concern about sparse category combinations. Remove the inferred geographic coordinates and their fitting code from the current holiday model. Hypothesis: their initial 0.0001 gain may not persist after the calendar features; eliminating approximate geometry could simplify and regularize the final model. Equal AUC is acceptable for this removal.

Result: **5fde1d2 — 0.6843 — keep**. Run time: 19.6s (training 11.7s, eval 7.9s, ok)

## Synthesis after experiments 11–20

Best remains 0.6843 at 5fde1d2, now without geographic embedding. Averaged trees and schedule residuals helped slightly; calendar-aligned holiday windows gave the largest recent gain (+0.0018). Added depth, split gamma, and fewer rounds did not help. Honest target encoding and high-cardinality CarrierOrigin categories hurt, consistent with limited stable interaction signal. Geography became redundant after holiday features and was removed at equal AUC. Working theory: broad timing and calendar effects plus regularized categorical structure transfer best; sparse historical combinations do not.

Research refresh: read XGBoost learning-to-rank documentation (https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) and searched AUC surrogate objectives. The initial narrow search was empty; a broader search found [Gao and Zhou on AUC pairwise consistency](https://arxiv.org/abs/1208.0645), supporting logistic pairwise loss as a theoretical candidate. This motivates an empirical test, not an expectation of guaranteed improvement.

## Experiment 21 — exploration

Train XGBRanker with rank:pairwise, one global group, mean pair sampling, four pairs per sample, and disabled group/score normalization. Scale child weight and lambda by four to roughly compensate for multiple pair contributions. Preserve best features, 600 rounds, depth four, and four trees per round. Expose a monotone sigmoid of the rank score through predict_proba for the unchanged harness. Hypothesis: explicitly learning delayed/non-delayed ordering improves AUC over pointwise classification.

Result: **4392e73 — 0.6802 — discard**. Run time: 61.3s (training 53.5s, eval 7.8s, ok)

## Experiment 22 — follow-up

Pairwise ranking scored 0.6802 and required 53.5s of the 60s training allowance; discarded. Test colsample_bytree=0.8 on the pointwise best model with four parallel trees. Hypothesis: feature subsampling adds useful diversity beyond the existing row sampling, reducing correlated category errors. This follows the stochastic forest guidance read at experiment 11.

Result: **c07a08f — 0.6845 — keep**. Run time: 20.5s (training 12.7s, eval 7.8s, ok)

## Experiment 23 — follow-up

Feature sampling improved AUC to 0.6845. Reduce max_cat_threshold from 16 to 8, keeping all other settings fixed. Hypothesis: the strongest prior category-regularization gain (experiment 10) may extend to smaller airport groups; this tests a specific further reduction in partition flexibility, not a new random parameter combination.

Result: **2d0f285 — 0.6807 — discard**. Run time: 19.4s (training 11.5s, eval 7.9s, ok)

## Experiment 24 — ablation/simplification

Reducing category threshold to 8 lost 0.0038; moderate grouping capacity is necessary. Isolate DayOfWeek as an additive effect alongside the existing additive month and holiday terms. Hypothesis: weekly demand is stable but its fitted airport/carrier interactions include calendar-specific noise. This follows the successful month-interaction ablation and changes only the allowed interaction structure.

Result: **1ef5335 — 0.6825 — discard**. Run time: 19.8s (training 11.6s, eval 8.1s, ok)

## Experiment 25 — follow-up

Test stronger leaf shrinkage by increasing reg_lambda from 10 to 100. Hypothesis: sparse categorical leaves need more shrinkage than broad time-of-day leaves; L2 regularization adapts to leaf support and may reduce year-specific deviations without removing interactions or shortening the boosting horizon.

Result: **60186de — 0.6866 — keep**. Run time: 20.1s (training 11.8s, eval 8.2s, ok)

## Experiment 26 — follow-up

Lambda 100 improved AUC by 0.0021 to 0.6866, confirming that sparse-leaf shrinkage matters. Average three independently seeded copies of the current best model (seeds 42, 1729, 2026), each fitted on all train rows. Hypothesis: averaging whole boosting trajectories reduces residual sampling variance beyond parallel trees within a shared trajectory. Source: probability averaging described in https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html . Seeds and equal weights are specified in advance; no per-member evaluation or weight fitting. Estimated training about 33–36s from the preceding run.

Result: **f716fda — 0.6866 — discard**. Run time: 43.8s (training 34.6s, eval 9.2s, ok)

## Experiment 27 — follow-up

Three independent trajectories tied at 0.6866 with three times the model size/training cost; discarded. Increase lambda from 100 to 500 to bracket the strong improvement observed between 10 and 100. Hypothesis: further shrinking small leaves improves temporal robustness; the directional test will reveal whether the shrinkage benefit is saturating.

Result: **71d08cd — 0.6869 — keep**. Run time: 19.6s (training 11.8s, eval 7.8s, ok)

## Experiment 28 — follow-up

Lambda 500 improved to 0.6869, with diminishing but positive gains. Revisit max_cat_threshold=64 under this much stronger leaf shrinkage. Hypothesis: larger category groups can now pool stable airport effects without the weakly regularized overfitting seen before experiment 10. This tests the interaction between grouping flexibility and leaf shrinkage, rather than repeating the original unconstrained regime.

Result: **b4f8033 — 0.6849 — discard**. Run time: 21.6s (training 13.8s, eval 7.9s, ok)

## Experiment 29 — ablation/simplification

Broad category search still underperforms under lambda 500 (0.6849), so retain threshold 16. Remove both route and carrier-origin schedule-median residuals and their fitted tables. Hypothesis: these features had only a tiny initial gain and may now be redundant with regularized time/category effects. Equal AUC is acceptable if the simpler preparation suffices.

Result: **ca9067d — 0.6869 — keep**. Run time: 18.9s (training 11.6s, eval 7.3s, ok)

## Experiment 30 — follow-up

Removing both schedule residuals tied at 0.6869 while simplifying preparation, so kept. Increase lambda from 500 to 2000 to locate the upper side of the useful shrinkage range. Hypothesis: if rare-leaf effects remain too noisy, additional shrinkage will help; otherwise the fixed 600-round model will begin to underfit. This is the next directional step after positive results at 100 and 500.

Result: **e1fafa9 — 0.6857 — discard**. Run time: 18.3s (training 11.3s, eval 7.0s, ok)

## Synthesis after experiments 21–30

Best is 0.6869 at ca9067d (+0.0126 over baseline), with both geography and schedule residuals removed. Strong L2 shrinkage is the clearest recent gain: lambda 100 beat 10, 500 improved slightly, and 2000 declined. Moderate category search remains essential; thresholds 8 and 64 both hurt. Weekday interactions are useful, unlike month interactions. Feature subsampling helped slightly. Pairwise ranking lost accuracy and nearly exhausted training time; a three-seed average tied and was discarded for complexity. Next investigate smooth objectives and numerical resolution, then revisit model structure with the simpler feature set.

Research refresh: searched and read [When Does Label Smoothing Help?](https://arxiv.org/abs/1906.02629) and [XGBoost custom objectives](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html). The smoothing evidence is primarily for neural networks, so transfer to boosted trees is an experimental hypothesis. Inspected installed XGBClassifier.fit to verify custom objectives retain the binary-logistic prediction link.

## Experiment 31 — exploration

Use 10% uniform label smoothing in the logistic objective (training targets 0.05/0.95), with exact sigmoid gradient and Hessian. Keep the data labels and evaluation unchanged. Hypothesis: reducing pressure for confident fits limits noisy residual learning and improves year-to-year ranking.

Result: **8e16e5c — 0.6867 — discard**. Run time: 19.4s (training 12.3s, eval 7.1s, ok)

## Experiment 32 — exploration

Label smoothing declined slightly to 0.6867 and was discarded. Reduce numerical histogram resolution from the default 256 bins to 64. Hypothesis: coarser time/distance thresholds smooth fragile fine-scale schedule distinctions while preserving dominant daily patterns. Categorical partition settings and holiday windows are unchanged. Source: max_bin in the XGBoost parameter reference.

Result: **f68ed05 — 0.6867 — discard**. Run time: 18.8s (training 11.4s, eval 7.3s, ok)

## Experiment 33 — follow-up

Coarser numerical bins also scored 0.6867, so revert. Extend each holiday interaction group to include scheduled departure time, while Month remains a singleton. Hypothesis: holiday travel changes the daily delay profile, so completely additive holiday terms miss useful timing variation. The groups overlap on CRSDepTime, following the documented XGBoost interaction-constraint mechanism.

Result: **be1d272 — 0.6864 — discard**. Run time: 19.2s (training 11.9s, eval 7.3s, ok)

## Plateau research and experiment 34 — exploration

Experiments 31–33 were three small discards; refreshed research before the next change. Read the [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) and [XGBoost dropout tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html). DART addresses over-specialization of later trees via tree dropout, a different mechanism from label or leaf shrinkage.

Test DART with 300 rounds at eta 0.1, one tree per round, rate_drop 0.05 and skip_drop 0.5. Preserve features, leaf shrinkage, and interaction restrictions. The shorter single-tree schedule bounds the extra prediction cost of dropout and matches the nominal eta-times-rounds of the best model. Hypothesis: dropout improves transfer by reducing dependence on particular early trees.

Result: **37b199a — 0.6858 — discard**. Run time: 41.5s (training 34.9s, eval 6.6s, ok)

## Experiment 35 — exploration

DART scored 0.6858 and trained in 34.9s; discarded. Test month as an ordered numerical predictor instead of a categorical predictor, retaining its isolated seasonal effect. Hypothesis: contiguous seasonal partitions are more transferable than arbitrary month groupings. Preserve the original feature order to avoid changing column-sampling semantics. This follows the time-representation research from the initial phase.

Result: **6e2bd16 — 0.6885 — keep**. Run time: 18.3s (training 11.6s, eval 6.7s, ok)

## Experiment 36 — follow-up

Ordered Month improved AUC by 0.0016 to 0.6885. Replace it with sine/cosine month coordinates in one isolated seasonal interaction group. Hypothesis: circular adjacency joins December and January and may express stable winter/summer patterns more naturally than the linear month axis. Source: sklearn cyclical time-feature example read earlier. Holiday arithmetic still uses the integer month locally inside prepare.

Result: **d938453 — 0.6875 — discard**. Run time: 18.4s (training 11.4s, eval 7.0s, ok)

## Experiment 37 — ablation/simplification

Circular month features underperformed the ordered month axis (0.6875). Remove the summer-holiday window while keeping Thanksgiving and Christmas windows. Hypothesis: the combined summer window pools dissimilar events and may add noise; the winter travel windows could account for the calendar gain. Equal AUC is acceptable for this simplification.

Result: **42ef031 — 0.6881 — discard**. Run time: 19.0s (training 12.6s, eval 6.4s, ok)

## Experiment 38 — exploration

Removing the summer window lost 0.0004, so retain all three holiday features. Test loss-guided tree growth with at most 16 leaves and no fixed depth cap, preserving roughly the leaf budget of depth-four trees. Hypothesis: allocating splits to the strongest residual regions uses capacity more efficiently than expanding levels evenly. Read https://xgboost.readthedocs.io/en/stable/treemethod.html and the grow_policy/max_leaves section of https://xgboost.readthedocs.io/en/stable/parameter.html before this new growth-policy category.

Result: **f99b6ee — 0.6886 — keep**. Run time: 20.2s (training 13.2s, eval 6.9s, ok)

## Experiment 39 — follow-up

Loss-guided growth gave a small gain to 0.6886. Double boosting rounds from 600 to 1200 at the same learning rate. Hypothesis: lambda 500 greatly slows updates to smaller leaves, so the strongly regularized, ordered-seasonality model may now benefit from a longer fitting horizon. The original longer-schedule failure used unregularized depth-six trees and does not settle this regime. Expected training roughly 25s from experiment 38.

Result: **a46748e — 0.6867 — discard**. Run time: 35.2s (training 27.3s, eval 7.9s, ok)

## Experiment 40 — ablation/simplification

Doubling the boosting horizon still overfits (0.6867), even with lambda 500. Remove the explicit min_child_weight=50 setting, reverting to its default 1 while keeping strong leaf shrinkage and the 16-leaf budget. Hypothesis: the hard support threshold may now be redundant or suppress a few useful splits; if AUC ties, one less tuned constraint simplifies the model.

Result: **2a49482 — 0.6886 — keep**. Run time: 20.5s (training 13.4s, eval 7.1s, ok)

## Synthesis after experiments 31–40

Best is 0.6886 at 2a49482 (+0.0143 over baseline). Ordered numerical month was the main gain (+0.0016); circular month coordinates did not improve it. Summer holidays remain useful. Loss-guided 16-leaf growth improved slightly, and the explicit child-weight constraint could be removed at equal AUC. Label smoothing, coarser numerical bins, holiday-time interactions, DART, and a longer boosting horizon all failed to improve. Working theory: coarse ordered seasonal structure and strong shrinkage are robust; extra residual fitting and event interactions overfit.

Research refresh: searched temporal weighting and concept drift. Read [Random Forest Based Approach for Concept Drift Handling](https://arxiv.org/abs/1602.04435) and [Learning under Concept Drift: an Overview](https://arxiv.org/abs/1010.4784). Their adaptation settings differ from this fixed year split, but motivate testing modest recency weighting without looking at evaluation features or labels.

## Experiment 41 — exploration

Weight training rows by exp2((Month-12)/12), normalized to mean one. Hypothesis: later-2005 operational patterns are more representative of 2006 than earlier patterns, while a one-year half-life retains broad seasonal coverage. These are training loss weights, not additional predictor columns; prepare and the scoring procedure remain unchanged.

Result: **1b08f86 — 0.6889 — keep**. Run time: 20.9s (training 14.0s, eval 6.9s, ok)

## Experiment 42 — follow-up

One-year recency decay improved AUC to 0.6889. Shorten the weighting half-life to six months, retaining mean-one normalization. Hypothesis: the positive first result reflects operational drift, and moderately stronger emphasis on late-2005 data may improve transfer further. This brackets the strength of an observed useful weighting direction.

Result: **cca2109 — 0.6886 — discard**. Run time: 20.1s (training 13.1s, eval 6.9s, ok)

## Experiment 43 — follow-up

Six-month weighting declined to 0.6886; keep the gentler one-year decay. Add a numerical two-week seasonal position, grouped with numerical Month while isolated from operational predictors. Hypothesis: stable seasonal transitions need not coincide with month boundaries, but daily resolution risks fitting weather shocks; 14-day bins provide a deliberately coarse intermediate scale. Unlike the discarded raw DayofMonth categories, this feature preserves annual order and cannot freely interact with airport/carrier identifiers.

Result: **9a1151e — 0.6922 — keep**. Run time: 22.3s (training 15.3s, eval 7.0s, ok)

## Experiment 44 — follow-up

Two-week seasonal position improved AUC by 0.0033 to 0.6922. Current mean split gains put it second (49.9) after departure time (254.7), ahead of carrier and weekday. Refine the isolated seasonal position from 14-day to 7-day bins and rename it SeasonWeek. Hypothesis: moderately finer seasonal transitions explain the gain, but weekly bins may expose the boundary where weather-specific fitting begins. Keep all regularization and recency weights fixed.

Result: **ce43b01 — 0.6915 — discard**. Run time: 22.2s (training 15.1s, eval 7.1s, ok)

## Experiment 45 — follow-up

Weekly resolution lost 0.0007 versus fortnightly bins. Average two models that use 14-day seasonal bins shifted by seven days relative to one another. Hypothesis: the useful scale is coarse, but individual bin boundaries are arbitrary; representation diversity can reduce boundary artifacts without moving to noisier weekly resolution. This differs from the tied seed ensemble by varying seasonal representation while keeping seeds fixed. Both seasonal columns are computed row-locally in prepare; the wrapper only selects columns for its two estimators. Equal weights are fixed in advance.

Result: **eabfb3d — 0.6917 — discard**. Run time: 37.5s (training 29.6s, eval 7.9s, ok)

## Experiment 46 — follow-up

Averaging seasonal alignments scored 0.6917, below the simpler unshifted model, and was discarded. Increase the loss-guided leaf budget from 16 to 32 at the same 600 rounds. Hypothesis: the improved seasonal representation and strong shrinkage leave some useful operational interactions underfit; additional local branching differs from the longer boosting horizon that failed in experiment 39.

Result: **d4c5b7c — 0.6914 — discard**. Run time: 25.0s (training 17.6s, eval 7.4s, ok)

## Plateau research and experiment 47 — exploration

Weekly seasonality, phase averaging, and 32-leaf trees were three consecutive discards within 0.001 of best. Researched [Systemic delay propagation in the US airport network](https://www.nature.com/articles/srep01159), which discusses schedule-linked propagation and daily resets. We lack aircraft, connection, and congestion data, so those quantities cannot be reconstructed here.

Add an operational time feature: scheduled minutes since 05:00 modulo 24 hours, keeping the original HHMM. Hypothesis: the early-morning low-delay reset observed in the training-only hour summary makes this ordering more natural for overnight services. The 05:00 boundary comes from that training observation, not evaluation inspection. All calculations are row-local.

Result: **774c754 — 0.6924 — keep**. Run time: 21.0s (training 13.9s, eval 7.1s, ok)

## Experiment 48 — ablation/simplification

OperationalTime gained 0.0002 to 0.6924. Remove raw CRSDepTime from the prepared predictors after computing OperationalTime. Hypothesis: the rotated clock retains all scheduled-time information and may make the raw representation redundant; one time predictor could reduce split competition and simplify the model. Equal AUC is acceptable for removing a predictor.

Result: **b799422 — 0.6924 — keep**. Run time: 21.1s (training 14.1s, eval 7.1s, ok)

## Experiment 49 — follow-up

Test lambda 250 instead of 500 with the improved seasonal features. Hypothesis: fortnightly seasonality supplies more useful structured signal than the earlier month-only model, so moderately lighter shrinkage may now fit that signal better. This revisits leaf shrinkage after the material representation gain, using a single controlled change.

Result: **07c6cd9 — 0.6925 — keep**. Run time: 21.4s (training 14.3s, eval 7.1s, ok)

## Experiment 50 — ablation/simplification

Lambda 250 nudged AUC to 0.6925. Remove num_parallel_tree=4 and use the default one tree per boosting round. Hypothesis: stronger features and leaf regularization may make within-round averaging redundant, as several earlier complex additions became redundant. At equal AUC this would substantially reduce model size and training time.

Result: **18a2874 — 0.6922 — discard**. Run time: 10.0s (training 3.5s, eval 6.6s, ok)

## Synthesis after experiments 41–50

Best is 0.6925 at 07c6cd9 (+0.0182 over baseline). The main gain was isolated fortnightly seasonality (+0.0033). Mild recency weighting helped, but stronger decay did not. Weekly bins, averaging shifted fortnight boundaries, and more leaves did not improve. Operational-day timing helped and replaced raw HHMM at equal AUC. Lambda 250 improved slightly; one tree per round lost 0.0003, so retain four. Current model is still a single XGBoost classifier with row-local calendar/time features, categorical airline/airport/weekday inputs, strong shrinkage, and bounded seasonal interactions.

Research refresh: searched and read [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html). Constraints can encode a shape prior, but may reduce effective tree capacity. The earlier training-only hour summary suggests an increase from 05:00 to roughly 20:00 followed by a decline; applying this conditional on other predictors is a hypothesis, not an established fact.

## Experiment 51 — exploration

Replace operational time by two hinge features: daytime progress capped at 900 minutes after 05:00 and overnight progress after that cap. Constrain the former increasing and the latter decreasing. Hypothesis: this piecewise shape discourages noisy local clock-time reversals while retaining the observed evening peak. Keep calendar and operational interaction grouping otherwise unchanged.

Result: **fb8f076 — 0.6919 — discard**. Run time: 21.3s (training 14.1s, eval 7.2s, ok)

## Experiment 52 — follow-up

The piecewise monotonic time prior scored 0.6919, so retain unconstrained operational time. Add reg_alpha=10 alongside lambda 250. Hypothesis: soft-thresholding weak leaf gradients removes small residual adjustments that L2 shrinkage only scales, improving transfer without restricting all time-response shapes. Source: XGBoost L1 regularization parameter definition.

Result: **54340b1 — 0.6933 — keep**. Run time: 21.0s (training 13.9s, eval 7.1s, ok)

## Experiment 53 — follow-up

Alpha 10 improved AUC by 0.0008 to 0.6933 and reduced the artifact from about 15.2 to 11.8 MB. Increase alpha to 30 to bracket the strength of the useful sparsity penalty. Hypothesis: additional weak leaf corrections remain year-specific; excessive thresholding will reveal itself as lost ranking signal.

Result: **39761f2 — 0.6919 — discard**. Run time: 19.7s (training 12.8s, eval 7.0s, ok)

## Experiment 54 — follow-up

Alpha 30 lost 0.0014; keep alpha 10. Reduce row subsample from 0.8 to 0.5 and scale lambda/alpha by 0.5/0.8 (250→156.25, 10→6.25). Hypothesis: more diverse parallel trees may average category noise better. Scaling penalties approximately preserves their strength relative to expected per-tree gradient/Hessian totals, separating diversity from simply increasing effective shrinkage. Source: XGBoost random-forest and sampling documentation read earlier.

Result: **8fb67ca — 0.6932 — discard**. Run time: 23.2s (training 15.8s, eval 7.5s, ok)

## Experiment 55 — follow-up

More row-sampling diversity scored 0.6932, slightly below best. Coarsen the isolated seasonal position from 14 to 21 days, keeping Month alongside it. Hypothesis: the weekly experiment showed excessive resolution hurts; three-week bins test whether a smaller number of within-month transitions gives a better bias/variance balance than fortnightly bins. This brackets granularity on the coarser side without searching arbitrary bin offsets.

Result: **ad0af52 — 0.6923 — discard**. Run time: 21.8s (training 14.7s, eval 7.0s, ok)

## Experiment 56 — follow-up

Three-week seasonality scored 0.6923, so retain the fortnightly representation. Average the current best model (subsample 0.8, lambda 250, alpha 10) and experiment 54's near-miss (subsample 0.5, lambda 156.25, alpha 6.25), with equal weights fixed in advance. Hypothesis: different sampling strengths produce complementary errors even though their individual Eval AUCs differ by only 0.0001. Both models are fitted anew on train in the same harness run; no artifact reuse, extra scoring, or weight tuning.

Result: **7073db1 — 0.6935 — keep**. Run time: 37.8s (training 29.8s, eval 8.0s, ok)

## Experiment 57 — follow-up

The complementary-sampling ensemble improved AUC to 0.6935. Test max_cat_threshold=32 for both members. Hypothesis: the added L1 penalty suppresses weak category adjustments, potentially allowing a moderate increase in grouping flexibility. Threshold 64 failed before L1 was introduced; this tests an intermediate setting in the new sparse-leaf regime.

Result: **ecf99f4 — 0.6929 — discard**. Run time: 38.4s (training 30.4s, eval 8.0s, ok)

## Experiment 58 — ablation/simplification

Threshold 32 lost 0.0006, so retain threshold 16. Simplify preparation by reading raw clock time into a temporary array instead of adding then deleting a predictor. Define calendar interaction groups once rather than repeating their names in a long parameter expression. Hypothesis: exact feature/configuration equivalence preserves AUC while making the retained implementation clearer and less error-prone. Verify equivalence before committing; equal AUC qualifies for this cleanup.

Pre-run checks passed: exact equality of all 200,000 prepared training rows, labels, and model parameters; batch-versus-single-row equality on four separated rows.

Result: **7cdfba0 — 0.6935 — keep**. Run time: 37.1s (training 28.9s, eval 8.2s, ok)

## Final experiment summary

Completed 58 non-baseline experiments plus the baseline. Best retained commit: `7cdfba0ed0a00544134af0fada52ed2295790bd7` on branch `oct6`. Best Eval AUC: **0.6935**, versus baseline **0.6743**, an absolute improvement of **0.0192**. Outcomes including baseline: 27 keeps, 32 discards, 0 crashes.

The final predictor averages two regularized XGBoost models with different row-sampling strengths. Its retained features include training-defined categorical mappings, ordinal month, isolated fortnight seasonality and holiday windows, distance, and scheduled departure time measured from 05:00. Mild recency weighting uses the training month. Stronger L1/L2 penalties, limited category grouping, and calendar interaction constraints improved generalization on the supplied Eval metric.

Useful simplifications removed day-of-month categories, redundant raw-clock inputs, inferred geometry, route-relative scheduling features, and duplicated configuration. Larger trees or category budgets, weekly or three-week seasonal bins, shifted-bin ensembles, overly strong recency weights, DART, ranking loss, label smoothing, and the tested disjoint-data target encoding did not improve the retained result. Each experiment's rationale and primary research sources are recorded above.

Final validation: only train.py differs from the starting commit; the working tree is clean; all 59 runs have unique logged commits; HEAD matches the best retained score. The final cleanup exactly preserved prepared features, labels, and model parameters over all 200,000 training rows. The final saved artifact was reloaded and checked for finite normalized predictions and batch/single-row consistency on training examples. No separate scoring metric was computed. Final harness run: training 28.9 seconds, evaluation 8.2 seconds, total 37.1 seconds. Artifact: `artifacts/7cdfba0ed0a00544134af0fada52ed2295790bd7.pkl` (26.7 MB).

Potential next experiments: assess calendar and recency robustness on additional independent years, then consider more heterogeneous regularized ensembles or smoother seasonal representations. The present result is the best observed Eval AUC after repeated selection on the supplied evaluation set; independent-year robustness remains untested. No holdout or human data was accessed.

Experimentation ended with under two minutes remaining. Results and research notes remain uncommitted under output/ as required. The harness clock is stopped immediately after these final checks.
