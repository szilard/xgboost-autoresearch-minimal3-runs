# Research log: oct7

## Setup

- Setup date: 2026-10-07 (UTC).
- Branch: `oct7`, created directly from starting HEAD `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist; no data contents inspected during setup.
- Verified installed pandas, NumPy, XGBoost, scikit-learn, and cloudpickle import successfully.
- Initialized `output/results.tsv` with only the required header; outputs remain uncommitted.
- Baseline code is unchanged. No training or evaluation has run, and the experiment clock has not started.
- After user confirmation, the first action is `python3 harness.py start`, followed by the unchanged baseline through `python3 harness.py run`.
- Web research is required before the first non-baseline experiment and thereafter as specified in `program.md`.

## Baseline — b15ec66

Eval AUC **0.6743**; training 1.5s including startup; evaluation 30.7s. Kept unchanged starter.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): control complexity with depth, child weight and regularization; reduce learning rate with more rounds; sampling can reduce sensitivity to noise.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): learning rate 0–1, subsampling 0–1, nonnegative child weight and regularization. Start with conservative depth 4, rate 0.05, 500 rounds, child weight 20, L2 5 and row sampling 0.8; these are hypotheses, not universally optimal settings.
- [Categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): partition splits group categories with similar gradients; categorical level mappings must be consistent during inference.
- [Time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): ordinal time features are useful to trees; cyclic transforms can expose periodic continuity. Candidate domain features are departure hour/minute and calendar position, computed per row.
- Training-only inspection: 200,000 complete rows; 20 carriers and 283 origin/destination airports. Month/day/week are strings prefixed `c-`. No evaluation data inspected.

## Experiment 1 — regularized shallow boosting

Classification: exploration. Hypothesis: 500 depth-4 trees at rate 0.05, child weight 20, L2 5 and 0.8 row sampling can learn more stable low-order effects than the 100 depth-6 baseline trees. The year shift makes variance control valuable. Source: XGBoost tuning guide above. All input features remain unchanged.

Result: **0.6793**, +0.0050 over baseline; kept `9892545`. Training 2.7s, evaluation 30.9s. Stronger regularization plus more boosting helps the year-shift score.

## Experiment 2 — explicit calendar and departure-time features

Classification: follow-up. Hypothesis: departure hour, minute within hour, numeric month/day and day of year expose schedule and smooth seasonal structure that categorical calendar splits must otherwise reconstruct. Add these to the kept shallow model. Based on the scikit-learn time-feature example cited above. Construct the frame once and let fixed pandas categorical levels handle unknowns directly, reducing per-row overhead without changing existing feature values. Verify singleton/batch consistency on training rows before the harness run.

Result: **0.6825**, +0.0032; kept `a28127a`. Training 3.8s, evaluation 21.0s. Batch/singleton feature checks passed on 24 training rows. Direct categorical conversion handles unseen values as missing in the installed pandas version, with a future deprecation warning; a future cleanup should use explicit codes for unknowns. Read-only gain importance of the prior kept model places scheduled departure time far ahead of other inputs; this is descriptive, not an additional evaluation metric.

## Experiment 3 — individual-category splits

Classification: exploration. Hypothesis: `max_cat_to_onehot=512` makes all existing categorical splits isolate one category, reducing opportunistic grouping of unrelated airports and calendar days that might not transfer across years. Keep all other settings and features fixed to isolate this categorical-modeling change. Source: XGBoost categorical documentation, optimal partitioning and `max_cat_to_onehot`.

Result: **0.6815**, -0.0010; discarded `cd75e43`, restored `a28127a`. Training 2.5s, evaluation 20.8s. Pure one-hot splitting does not beat partitioning at this capacity.

## Experiment 4 — airline and route interactions

Classification: exploration. Hypothesis: explicit origin–destination, carrier–origin and carrier–destination categories let shallow trees learn airport/airline operating patterns without spending multiple levels reconstructing those relationships. Their category levels are fitted only on training data; no counts or target statistics are used. Native partitioning remains in place. Based on XGBoost categorical documentation and flight-delay domain literature identifying route/airline/airport relationships: https://arxiv.org/abs/2105.08969 .

Also replace direct categorical construction with fixed Index.get_indexer/from_codes, an equivalent unknown-to-missing conversion that avoids the pandas deprecation warning. Check old features against the saved kept prepare function and test row independence before training.

Result: **0.6716**, -0.0109; discarded `5a5086b`, restored `a28127a`. Training 4.9s, evaluation 20.1s. Explicit high-cardinality interaction categories cause a substantial generalization loss. The encoding equivalence and singleton tests passed, so the failure points toward the new model inputs, not row-dependent computation.

## Experiment 5 — remove exact date information

Classification: ablation/simplification. Hypothesis: categorical day of month, numeric day of month, and day of year give the model access to weather/disruption patterns specific to dates in 2005. Remove all three, retaining month/season and weekday plus departure-time features. This directly tests temporal overfitting rather than adding more capacity. Training-only inspection shows strong time-of-day and broad monthly effects; no claim is made that individual calendar days repeat in 2006.

Result: **0.6794**, -0.0031; discarded `6691471`, restored `a28127a`. Training 3.8s, evaluation 17.8s. Exact date removal was too aggressive: at least some added calendar structure helps on the official evaluation split.

## Experiment 6 — deeper regularized trees

Classification: follow-up. Hypothesis: depth 4 is limiting useful interactions of schedule, season, carrier and airports. Increase only max_depth from 4 to 6, retaining child weight 20, L2 5, row sampling 0.8, 500 rounds and the existing features. This differs from the baseline in its longer boosting and regularization, and differs from experiment 4 by learning interactions selectively rather than exposing high-cardinality composite categories. Source: XGBoost parameter/tuning documentation.

Result: **0.6773**, -0.0052; discarded `988164c`, restored `a28127a`. Training 4.0s, evaluation 21.0s. More tree depth worsens temporal transfer; prioritize shallower or more constrained fits.

## Experiment 7 — equivalent categorical codes and faster preparation

Classification: ablation/simplification. Hypothesis: passing fixed numeric category codes with explicit XGBoost feature types reproduces the existing categorical splits while avoiding repeated pandas Categorical construction and unknown-category warnings. There are no new model inputs or hyperparameter changes. Use the documented numeric-code categorical interface: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html#using-native-interface . Keep only if official AUC improves, or ties with lower run time. Verify codes match existing categorical levels and single-row output matches batch output.

Result: **0.6825**, exact rounded AUC tie; kept `a252681` for speed and simpler handling of unknown categories. Training 3.0s, evaluation **7.0s**, compared with 21.0s for the previous kept model. Old-feature code equivalence, singleton consistency, and unseen-category checks passed. No pandas deprecation warnings remain.

## Experiment 8 — one-hot only for calendar and carrier

Classification: exploration. Hypothesis: `max_cat_to_onehot=32` reduces flexible grouping of small calendar/carrier categories while preserving useful partitioned airport splits. Unlike experiment 3 (threshold 512), the 283-category origin and destination columns retain partitioning. Keep other features and training parameters fixed. Source: XGBoost categorical documentation.

Result: **0.6825** (+0.0000 vs previous best); **discard** `5bda441`. Run time: 9.6s (training 2.9s, eval 6.7s, ok)

## Experiment 9 — limit categorical split groups to 16

Classification: follow-up. Hypothesis: Reducing max_cat_threshold from 64 to 16 restricts complex category groupings while preserving native partitioning. This may reduce category-specific noise without losing the airport grouping that all-one-hot splitting removed. All other settings stay at the kept model.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature

Result: **0.6830** (+0.0005 vs previous best); **keep** `88339dc`. Run time: 9.5s (training 2.8s, eval 6.7s, ok)

## Experiment 10 — 1000 depth-3 trees with learning rate 0.03

Classification: follow-up. Hypothesis: The depth-6 loss and categorical regularization gain suggest variance is limiting transfer. Use depth 3 with 1000 rounds and rate 0.03 instead of depth 4 with 500 rounds and rate 0.05, maintaining similar total boosting strength while focusing on lower-order interactions.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html

Result: **0.6819** (-0.0011 vs previous best); **discard** `89fba8e`. Run time: 10.7s (training 3.9s, eval 6.7s, ok)

## Synthesis after 10 experiments

- Regularized shallow boosting improved the baseline; additional calendar/schedule inputs helped further.
- Explicit route/carrier-airport categories and deeper trees lost generalization. Removing every exact-date input also hurt, so date information is useful but must be controlled.
- Fixed categorical codes preserve AUC while reducing evaluation time from ~21 to ~7 seconds. Limiting categorical split groups gave another small gain.
- Current theory: broad schedule, carrier and airport effects dominate, and unsupported combinations overfit across the year boundary. Seek compact, interpretable context features and constrained interactions; avoid adding arbitrary high-cardinality identifiers.

### New research and directions

- [XGBoost feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html): restrict allowed combinations to suppress spurious relationships. Candidate: separate fine calendar effects from airport-specific interactions.
- [OPM holiday rules](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay/): Thanksgiving is the fourth Thursday of November, Memorial Day the last Monday in May, Labor Day the first Monday in September. Use calendar rules to express distance from movable holidays from each row's month/day/weekday; the proposed relation to delay is our hypothesis.
- [scikit-learn soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html): averaging predicted probabilities supports a later ensemble experiment if complementary models fit within 60 seconds.
- [Target-encoding cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html): naive target means can leak training labels. Do not introduce a different train/evaluation feature transform or use row outcomes as features. Favor unsupervised training-fitted schedule medians for now.

## Experiment 11 — major holiday proximity features

Classification: exploration. Hypothesis: Signed distance to Thanksgiving, Christmas, and the nearest major travel holiday may explain date effects more consistently across years than bare dates. Derive movable holidays from month/day/weekday for each row, using a non-leap calendar appropriate to the provided years; add three clipped numeric offsets, with no external data or labels.
Source: https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay/

Result: **0.6825** (-0.0005 vs previous best); **discard** `3419e9d`. Run time: 11.5s (training 4.0s, eval 7.5s, ok)

## Experiment 12 — departure offsets from training-fitted schedule medians

Classification: exploration. Hypothesis: A departure's position relative to typical origin, destination and route schedules may describe operating context without high-cardinality target fitting. Fit three median departure-minute lookups on train only and add departure-minus-median features. Unseen keys remain NaN; no counts or outcome statistics become features.
Source: program.md feature-engineering example; pandas group median semantics: https://pandas.pydata.org/pandas-docs/version/1.5/reference/api/pandas.core.groupby.GroupBy.median.html

Result: **0.6827** (-0.0003 vs previous best); **discard** `7c819fa`. Run time: 11.8s (training 3.2s, eval 8.7s, ok)

## Experiment 13 — boost four randomized trees per round

Classification: exploration. Hypothesis: Recent feature additions have plateaued. Average four row-subsampled trees at each boosting round and sample 80% of columns per split to reduce unstable split choices. Keep 500 boosting rounds, depth 4 and learning rate 0.05. This tests boosted-forest variance reduction rather than another feature expansion.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html; plateau research also reviewed DART https://proceedings.mlr.press/v38/korlakaivinayak15.html

Result: **0.6834** (+0.0004 vs previous best); **keep** `8e5a2b3`. Run time: 18.6s (training 11.5s, eval 7.1s, ok)

## Experiment 14 — require more support per leaf

Classification: follow-up. Hypothesis: The boosted forest improved transfer slightly. Raise min_child_weight from 20 to 100 so each leaf needs substantially more training support, reducing unstable small-airport and calendar interactions while keeping depth and boosting strength unchanged.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster

Result: **0.6831** (-0.0003 vs previous best); **discard** `5ad77ed`. Run time: 17.8s (training 10.5s, eval 7.3s, ok)

## Experiment 15 — separate exact-date effects from operating features

Classification: exploration. Hypothesis: Removing exact dates entirely hurt, but flexible interactions also hurt. Keep DayofMonth, DayNum and DayOfYear as a separate disjoint interaction group, preventing them from combining with airport, carrier, weekday or departure-time splits. Other features retain their existing interactions. This tests additive date effects rather than deleting them.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html

Result: **0.6841** (+0.0007 vs previous best); **keep** `8c28abf`. Run time: 17.7s (training 10.7s, eval 7.1s, ok)

## Experiment 16 — airport geometry learned from training route distances

Classification: exploration. Hypothesis: Continuous airport coordinates inferred from observed inter-airport distances may share regional effects more smoothly than airport IDs. Build an undirected distance graph from training routes, complete distances by shortest paths, fit a three-dimensional classical MDS embedding, and look up origin/destination coordinates per row. No labels, frequencies or external airport data enter this lookup.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html (shortest-path distance embedding and centered distance kernel)

Result: **0.6844** (+0.0003 vs previous best); **keep** `dd5909e`. Run time: 19.4s (training 11.6s, eval 7.8s, ok)

## Experiment 17 — separate all calendar effects from flight operations

Classification: follow-up. Hypothesis: Exact-date isolation improved AUC. Extend its disjoint group to Month, MonthNum and DayOfWeek as well, testing whether calendar effects transfer better as a separate additive component while schedule, carrier, distance and airport/geography interactions remain flexible.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html

Result: **0.6821** (-0.0023 vs previous best); **discard** `32fa34e`. Run time: 19.7s (training 11.7s, eval 8.0s, ok)

## Experiment 18 — halve boosting rounds to 250

Classification: ablation/simplification. Hypothesis: Read-only tree statistics show later rounds concentrate on airport and calendar splits, while the dominant schedule effects are fitted early. Cut boosting rounds from 500 to 250 to test whether those later corrections harm year-to-year transfer. All features, regularization and four-tree averaging stay fixed.
Source: XGBoost bias/variance and learning-rate guidance: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html

Result: **0.6838** (-0.0006 vs previous best); **discard** `b5a6aa5`. Run time: 14.5s (training 7.1s, eval 7.5s, ok)

## Experiment 19 — double boosting rounds to 1000

Classification: follow-up. Hypothesis: The 250-round ablation lost 0.0006 AUC, so later corrections have some value. Test 1000 rounds versus the kept 500 to bracket whether the present ensemble is still underfit or has already reached its useful boosting horizon; keep all other settings fixed.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html

Result: **0.6841** (-0.0003 vs previous best); **discard** `42f7564`. Run time: 30.9s (training 22.6s, eval 8.3s, ok)

## Experiment 20 — favor recent training months with six-month half-life

Classification: exploration. Hypothesis: Operational patterns near the end of 2005 may transfer better into 2006. Weight each training row by 2**((MonthNum-12)/6), normalized to mean one so regularization scale is comparable. All rows remain in training; preparation and evaluation are unchanged. This is our simple recency-weighting adaptation, not a reproduction of streaming adaptive XGBoost.
Source: Concept-drift motivation: https://arxiv.org/abs/2005.07353

Result: **0.6843** (-0.0001 vs previous best); **discard** `2519628`. Run time: 19.4s (training 11.6s, eval 7.8s, ok)

## Synthesis after 20 experiments

The dominant gains still come from broad features and controlled complexity. Four randomized trees per boosting round help; isolating exact-date interactions helps; continuous airport geometry inferred solely from training distances gives another small gain. Major-holiday offsets and schedule-relative medians were near misses. Constraining all calendar interactions was too restrictive. Both 250 and 1000 rounds lost to 500 in the current model, so more boosting alone is not the next priority.

Current theory: retain the strong schedule/season effects and airport context, but reduce narrow conditional fits. Next directions are a materially different loss function, selective removal of redundant inputs, and regularization that acts on split quality rather than only leaf size.

### Research refresh

- [Adaptive XGBoost](https://arxiv.org/abs/2005.07353) motivates adaptation to changing relationships. Our recency-weight test is a simpler, explicitly distinct approach, with no online or external data.
- [XGBoost learning to rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html): `rank:pairwise` uses pairwise logistic loss without NDCG/MAP scaling. Mean pair sampling covers the full ranking, unlike top-k optimization. A single group containing the training rows is a potential AUC-oriented classification surrogate; official harness AUC remains the only selection metric.
- [DART](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and its [original paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) propose tree dropout to reduce overspecialization. Training is more costly, so a trial must respect the 60-second training cap.
- [Isomap documentation](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html) informed the training-only shortest-path/MDS airport lookup. It does not establish that geography will improve flight predictions; that was tested through the harness.

## Experiment 21 — pairwise ranking loss as an AUC surrogate

Classification: exploration. Hypothesis: Replace pointwise logistic classification with rank:pairwise using one query group containing all training rows, two uniformly sampled pairs per row, and no ranking-specific gradient/score normalization. This trains a pairwise logistic ordering surrogate aligned with the AUC task. Keep the existing features and tree settings. A monotone sigmoid supplies the harness predict_proba interface; no separate metric or validation is introduced.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html

Result: **0.6817** (-0.0027 vs previous best); **discard** `b50c9f5`. Run time: 44.1s (training 36.4s, eval 7.7s, ok)

## Experiment 22 — replace airport categories with continuous geometry

Classification: ablation/simplification. Hypothesis: The added airport coordinates helped slightly, and late boosted trees focus on airport IDs. Remove raw Origin and Dest categorical inputs while retaining their learned three-dimensional coordinates, testing whether smoother regional effects generalize better than target-driven category groups.
Source: Follow-up to experiment 16 and the training-only MDS lookup; https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html

Result: **0.6807** (-0.0037 vs previous best); **discard** `00d9052`. Run time: 18.6s (training 11.0s, eval 7.6s, ok)

## Experiment 23 — DART tree dropout

Classification: exploration. Hypothesis: Try tree dropout to reduce late-tree overspecialization: DART with rate_drop 0.05, skip_drop 0.5, forest normalization, and one tree per round instead of four. Retain 500 rounds and the kept feature set and constraints. Reducing parallel trees leaves runtime headroom for dropout's more expensive prediction updates.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html; https://proceedings.mlr.press/v38/korlakaivinayak15.html

Result: **0.0000** (-0.6844 vs previous best); **crash** `82d8241`. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)

## Experiment 24 — DART within budget: 250 rounds at rate 0.1

Classification: follow-up. Hypothesis: The 500-round DART trial exceeded the training cap before evaluation. Halve rounds to 250 and double learning rate to 0.1 to preserve nominal boosting strength while sharply reducing dropout's repeated-prediction cost. Use the current tree-booster dropout API instead of the deprecated dart alias. Retain rate_drop 0.05, skip_drop 0.5, forest normalization and one tree per round.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html

Result: **0.6833** (-0.0011 vs previous best); **discard** `09cb563`. Run time: 33.6s (training 26.3s, eval 7.3s, ok)

## Experiment 25 — prune weak splits with gamma 5

Classification: follow-up. Hypothesis: A shorter fit lost some useful corrections, but late airport/calendar splits may still be noisy. Set gamma=5 to require greater training-loss improvement for each split, selectively removing weak branches without shortening the useful boosting horizon or imposing a larger leaf-size floor.
Source: Refreshed split-gain/pruning research: https://xgboost.readthedocs.io/en/latest/tutorials/model.html#learn-the-tree-structure

Result: **0.6849** (+0.0005 vs previous best); **keep** `9f12b66`. Run time: 19.2s (training 11.5s, eval 7.7s, ok)

## Experiment 26 — smoothed delay rates from other carriers and airports

Classification: exploration. Hypothesis: Add three fixed training-fitted conditional means: origin delay risk from OTHER carriers, destination risk from OTHER carriers, and carrier risk at OTHER origins. Excluding the whole matching carrier-airport cell removes each training row's own label from its features. Smooth toward the known balanced prior 0.5 with strength 200. Counts are used only to calculate these means, never exposed as features. The same frozen lookup applies to single rows, batches and future years; no cross-validation or alternate scoring is added.
Source: Target-leakage motivation: https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html . The conditional exclusion lookup is our adaptation to the row-wise preparation contract.

Result: **0.6851** (+0.0002 vs previous best); **keep** `f9238a2`. Run time: 20.9s (training 12.1s, eval 8.7s, ok)

## Experiment 27 — route and carrier-airport rates excluding the current month

Classification: follow-up. Hypothesis: The peer-risk lookup helped. Add smoothed historical delay means for route, carrier-origin and carrier-destination cells using only OTHER months. Every training row and its entire month are excluded from the corresponding fitted estimate, and the lookup is fixed by the row's known categories/month at inference. Use prior 0.5 and strength 200, with no count features.
Source: Follow-up to experiment 26; leakage considerations from https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html

Result: **0.6842** (-0.0009 vs previous best); **discard** `71277e1`. Run time: 24.0s (training 13.9s, eval 10.1s, ok)

## Experiment 28 — remove categorical day-of-month but retain ordered dates

Classification: ablation/simplification. Hypothesis: Experiment 5 removed all exact dates and lost information. Here remove only categorical DayofMonth, retaining numeric DayNum and DayOfYear in the isolated date component. This preserves calendar position while preventing arbitrary noncontiguous groups of calendar days.
Source: XGBoost categorical versus numeric split semantics: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html

Result: **0.6867** (+0.0016 vs previous best); **keep** `f3ed57c`. Run time: 20.2s (training 11.7s, eval 8.5s, ok)

## Experiment 29 — retain day-of-year without recurring day-of-month

Classification: ablation/simplification. Hypothesis: Removing categorical day-of-month improved AUC by 0.0016. Remove the remaining numeric DayNum feature as well, leaving only DayOfYear in the isolated date component. This tests whether a recurring monthly day effect is noise while preserving annual calendar position.
Source: Motivated by experiment 28; ordinal time representations: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html

Result: **0.6866** (-0.0001 vs previous best); **discard** `fd2e00b`. Run time: 21.1s (training 12.5s, eval 8.6s, ok)

## Experiment 30 — average three independently seeded boosted forests

Classification: exploration. Hypothesis: Average probabilities from the kept configuration trained with seeds 42, 137 and 2026. Whole-ensemble averaging may reduce remaining split-path variance beyond averaging four trees within each round. Each member sees the same permitted training data and features; only the combined model is scored by the harness. Expected training cost is about 35 seconds.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html

Result: **0.6868** (+0.0001 vs previous best); **keep** `550e6f9`. Run time: 40.9s (training 31.5s, eval 9.5s, ok)

## Synthesis after 30 experiments

The largest recent gain came from removing categorical day-of-month while retaining ordered calendar fields. Numeric day-of-month removal then lost 0.0001, so keep both ordered day and annual position. Split-gain pruning helped. Smoothed airport/carrier peer rates offered a small gain with explicit exclusion of each row's carrier-airport cell; more specific other-month route rates lost accuracy. Their tests verified singleton/batch equality, input-label independence, and the intended excluded groups.

Pairwise ranking and DART did not beat logistic boosted forests. One DART run exceeded the training limit and was logged as a crash; its smaller follow-up finished and lost. Raw airport IDs remain useful alongside continuous geometry. The current direction is selective simplification and robust averaging, rather than increasing interaction complexity.

### Research refresh

- [Single estimator versus bagging](https://scikit-learn.org/stable/auto_examples/ensemble/plot_bias_variance.html): averaging is a variance-reduction strategy; this motivates evaluating multiple independently seeded boosted models, without assuming a guaranteed improvement.
- [Systemic delay propagation](https://www.nature.com/articles/srep01159): schedules and connected operations permit delays to propagate within a day. Our training-only summaries also show increasing delay risk from early morning toward evening followed by a decline. A proposed next test will encode a daytime rise and overnight decline with monotonic constraints, explicitly treating the shape as a hypothesis.
- [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html): constraints can impose directional effects on chosen numerical inputs. Raw departure time is not globally monotone, so a direct constraint on HHMM would be inappropriate; use separate operational-day components if testing this idea.

## Experiment 31 — stronger split pruning with gamma 10

Classification: follow-up. Hypothesis: Gamma 5 improved the single-model configuration. Increase it to 10 in the current three-seed ensemble to remove more weak branches while retaining the useful ordered-date and peer-risk inputs. This tests stronger split evidence, not additional boosting or leaf-size constraints.
Source: https://xgboost.readthedocs.io/en/latest/tutorials/model.html#learn-the-tree-structure

Result: **0.6867** (-0.0001 vs previous best); **discard** `c0b25d7`. Run time: 39.8s (training 30.6s, eval 9.2s, ok)

## Experiment 32 — constrain daytime rise and overnight decline

Classification: exploration. Hypothesis: Replace raw HHMM and departure hour with an operational day starting at 05:00: a rise capped at 20:00 and an overnight component afterward. Constrain the rise positively and the overnight component negatively, retaining minute-of-hour. This regularizes the observed broad daily shape while preserving carrier/airport interactions and uses only per-row scheduled time.
Source: https://www.nature.com/articles/srep01159; https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html

Result: **0.6862** (-0.0006 vs previous best); **discard** `4db5df7`. Run time: 41.8s (training 32.4s, eval 9.4s, ok)

## Experiment 33 — smaller boosting steps at matched total tree count

Classification: follow-up. Hypothesis: Use 1000 rounds at rate 0.025 with two parallel trees per round, instead of 500 rounds at 0.05 with four. Each seeded member still has 2000 trees and nominal learning-rate-times-rounds of 25. This tests finer gradient updates without adding model size, and avoids the longer-boosting strength that failed in experiment 19.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html

Result: **0.6868** (+0.0000 vs previous best); **discard** `ceccc1d`. Run time: 42.7s (training 33.1s, eval 9.5s, ok)

## Experiment 34 — ablate peer-risk lookups from the ensemble

Classification: ablation/simplification. Hypothesis: Peer rates added only 0.0002 before later calendar simplification and ensembling. Remove the three peer-risk features and their fitted lookup code to test whether they still add value in the current model. An AUC tie is acceptable because this removes substantial preparation code and input features.
Source: Plateau refresh on prediction shift and categorical statistics: https://arxiv.org/abs/1706.09516 . We retain XGBoost; this is a feature ablation, not a CatBoost implementation.

Result: **0.6862** (-0.0006 vs previous best); **discard** `4067348`. Run time: 40.1s (training 31.7s, eval 8.4s, ok)

## Experiment 35 — use all columns at every split

Classification: ablation/simplification. Hypothesis: Feature sampling and four-tree averaging were introduced together in experiment 13. With stronger pruning and three whole-model seeds now in place, remove per-split column sampling to test whether withholding strong schedule or airport context is unnecessary. Row subsampling remains 0.8.
Source: https://xgboost.readthedocs.io/en/stable/python/examples/feature_weights.html; https://xgboost.readthedocs.io/en/stable/tutorials/rf.html

Result: **0.6868** (+0.0000 vs previous best); **discard** `1947e00`. Run time: 42.0s (training 32.5s, eval 9.5s, ok)

## Experiment 36 — add route direction in learned geographic coordinates

Classification: follow-up. Hypothesis: The airport embedding helped but trees must reconstruct differences from separate origin/destination coordinates. Add destination-minus-origin for each of the three learned axes. This exposes route direction as a low-dimensional numeric interaction without introducing high-cardinality route IDs or external location data.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html; greedy one-feature split limitations: https://xgboost.readthedocs.io/en/latest/tutorials/model.html#learn-the-tree-structure

Result: **0.6866** (-0.0002 vs previous best); **discard** `7962131`. Run time: 43.5s (training 33.9s, eval 9.6s, ok)

## Experiment 37 — use ordered month without a categorical duplicate

Classification: ablation/simplification. Hypothesis: The day-of-month categorical ablation helped substantially. Remove only categorical Month while retaining MonthNum and DayOfYear, testing whether arbitrary month groupings capture year-specific conditions beyond useful ordered seasonality. An equal AUC would be kept for fewer inputs.
Source: Refreshed encoding research: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html; https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_categorical.html

Result: **0.6873** (+0.0005 vs previous best); **keep** `31af94b`. Run time: 39.9s (training 30.8s, eval 9.2s, ok)

## Experiment 38 — add circular month features

Classification: follow-up. Hypothesis: Ordered-month simplification improved AUC to 0.6873. Add sine and cosine of month with period 12 so December and January can share a seasonal split. Use month rather than exact day-of-year, preserving the separation of fine-date effects from flight operations.
Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html

Result: **0.6877** (+0.0004 vs previous best); **keep** `8bee287`. Run time: 42.3s (training 32.6s, eval 9.7s, ok)

## Experiment 39 — coarsen numeric split resolution to 64 bins

Classification: exploration. Hypothesis: Use max_bin=64 instead of 256 to limit fine thresholds on day-of-year, departure time, peer rates and coordinates. DayNum, MonthNum, departure hour and minute still provide low-cardinality detail. The hypothesis is that coarser numeric resolution improves transfer by smoothing year-specific fluctuations.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster

Result: **0.6875** (-0.0002 vs previous best); **discard** `401d278`. Run time: 41.0s (training 31.0s, eval 10.0s, ok)

## Experiment 40 — stronger L2 shrinkage of leaf predictions

Classification: follow-up. Hypothesis: Increase reg_lambda from 5 to 50 to shrink small-support leaf predictions continuously. This differs from the failed larger child-weight floor and stronger split-pruning trials: potentially useful small groups retain their branches but receive weaker corrections.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster

Result: **0.6895** (+0.0018 vs previous best); **keep** `bb5259e`. Run time: 42.2s (training 32.2s, eval 10.0s, ok)

## Synthesis after 40 experiments

The clearest new evidence is about calendar representation: removing categorical Month helped, then adding circular month features helped again. Retain the ordered day/month fields and restrict fine-date effects to their own trees. The three-seed ensemble gives a small gain; removing peer-risk inputs loses 0.0006, so they remain useful after later changes. Finer learning steps, all-column splitting, monotone clock components and route-coordinate differences did not improve AUC. Coarse 64-bin numerics were a near miss.

### Research refresh and remaining directions

- [XGBoost growth controls](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster) distinguish depth-wise and loss-guided growth; the latter prioritizes higher-loss-reduction nodes.
- [LightGBM's leaf-wise tuning discussion](https://lightgbm.readthedocs.io/en/v4.6.0/Parameters-Tuning.html) explains why leaf count and depth must both be bounded for best-first trees. Use this structural insight in XGBoost, without adding packages or changing libraries: test a 16-leaf cap with depth at most 6.
- Remaining priority: alternative tree allocation under the same leaf budget, then simplifications that preserve or improve the official AUC. Leave the final branch at the best kept commit and verify its serialized prepare function before stopping the clock.

## Experiment 41 — loss-guided growth with 16 leaves and depth cap 6

Classification: exploration. Hypothesis: The stronger L2 penalty improved AUC by 0.0018. With that safeguard, use lossguide growth to allocate up to 16 leaves where loss reduction is greatest, allowing depth up to 6. This keeps the same maximum leaf budget as depth-4 trees while permitting useful uneven branch depths.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster; https://lightgbm.readthedocs.io/en/v4.6.0/Parameters-Tuning.html

Result: **0.6894** (-0.0001 vs previous best); **discard** `0653cdb`. Run time: 49.7s (training 39.1s, eval 10.6s, ok)

## Experiment 42 — increase L2 leaf shrinkage from 50 to 200

Classification: follow-up. Hypothesis: L2=50 gave a 0.0018 improvement over 5, while loss-guided allocation did not help. Raise L2 to 200 in the retained depth-4 ensemble to test whether smaller-group corrections still need more shrinkage under the year shift. This is a fourfold change in the denominator penalty, with no added model capacity.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster

Result: **0.6898** (+0.0003 vs previous best); **keep** `32a8e6b`. Run time: 43.2s (training 33.4s, eval 9.8s, ok)

## Experiment 43 — bracket L2 shrinkage with penalty 800

Classification: follow-up. Hypothesis: L2 improvements tapered from +0.0018 at 50 to +0.0003 at 200. Test 800 to determine whether still stronger shrinkage helps or begins to underfit. This brackets the regularization response with a fourfold increase, keeping architecture and all features fixed.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster

Result: **0.6895** (-0.0003 vs previous best); **discard** `2c1bb2e`. Run time: 44.3s (training 34.4s, eval 9.9s, ok)

## Experiment 44 — depth 5 with strong L2 regularization

Classification: follow-up. Hypothesis: Depth 6 failed with weak L2 earlier. After the large gains from reg_lambda=200, test whether modestly deeper trees (depth 5) now capture useful interactions without excessive year-to-year overfit. Keep other settings and the three-seed ensemble fixed.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-tree-booster

Result: **0.6894** (-0.0004 vs previous best); **discard** `80c56f4`. Run time: 49.6s (training 39.3s, eval 10.2s, ok)

## Experiment 45 — simplify ensemble from three seeds to two

Classification: ablation/simplification. Hypothesis: The initial three-seed ensemble added only 0.0001 before stronger regularization. Remove seed 2026 and retain seeds 42 and 137 to test whether the final regularized model preserves or improves AUC with one-third fewer trees and less training time. Keep a tie because this is a concrete simplification.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html

Result: **0.6898** (+0.0000 vs previous best); **keep** `a567151`. Run time: 33.0s (training 23.6s, eval 9.4s, ok)

## Final summary

Best official Eval AUC: **0.6898**, commit **`a567151`** on branch `oct7`. Baseline: **0.6743** (`b15ec66`); absolute improvement: **0.0155**. Completed 45 experiments after the baseline: 16 kept, 28 discarded, 1 training timeout. Each candidate was committed before its official harness run; the branch ends at the best kept commit. Experiment 45 retained the same four-decimal AUC with two instead of three ensemble members, reducing training from 33.4s to 23.6s. Its full harness run took 33.0s (9.4s evaluation).

What worked: shallow regularized trees; ordered calendar and departure-time fields; separating fine-date effects from operating-feature interactions; removing categorical copies of day and month; circular month features; training-fitted airport geometry and peer-risk means; randomized parallel trees; and strong L2 leaf shrinkage. The peer-risk construction excludes the current carrier-airport cell, and no row counts are supplied as features. Fixed numeric category codes also made row-by-row preparation substantially faster.

What did not work: larger categorical route interactions, deeper trees, eliminating all exact-date information, one-hot categorical splits, holiday offsets, schedule-relative time, recency weighting, pairwise ranking, DART, hard monotone clock restrictions, coarse numeric bins, stronger split pruning, and loss-guided tree allocation. DART's original 500-round trial exceeded the 60-second training limit; its shorter follow-up scored below the best. L2=800 underperformed 200, and depth 5 did not improve the final strongly regularized model.

Current interpretation: the 2005-to-2006 shift rewards smoothing small-group effects and calendar structure while retaining useful airport/carrier identities. Improvements are measured on the designated Eval set; the human-only holdout was not accessed. Next ideas to research would be circular scheduled-time features with carrier interactions, additional label-excluding peer-risk definitions, and whether more structured geographic features can replace some categorical capacity. These are proposals, not tested results.

Final verification: reloaded the saved artifact for `a567151` using the harness loader. On 24 training-only fixture rows, batch preparation matched concatenated single-row preparation exactly; flipping input labels left features unchanged. Two synthetic unseen-category rows produced finite normalized probabilities. No additional accuracy metric was computed. Verified the two-member ensemble, clean worktree, unchanged harness and other tracked files, `save_and_evaluate(model, prepare)` as the final line, and HEAD matching the highest-AUC kept result. Results and research notes remain uncommitted in output/. The harness clock reported 58m04s elapsed and 1m56s remaining at the end of the final experiment, triggering the required wrap-up.
