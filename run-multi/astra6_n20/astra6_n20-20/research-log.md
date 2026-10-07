# Research log: oct7

## Setup — 2026-10-07

- Branch: `oct7`, created directly from the current HEAD, `b15ec66`.
- Baseline commit: `b15ec66`; the first run will use the existing `train.py`.
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed that `data/train.csv` and `data/eval.csv` exist.
- Checked only the training data: 200,000 rows, required columns, and Y/N target labels.
- Required library imports and Python source syntax checks passed.
- Initialized `output/results.tsv` with its header only.
- No experiments have run; the one-hour clock has not started at setup.

## Experiments

Baseline pending. Research external sources before the first non-baseline experiment.

### Baseline — b15ec66 — keep

Unchanged starter: Eval AUC **0.6743**, training 1.4s including startup, evaluation 30.6s. This is the initial reference.

### Initial research

- [XGBoost tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): balance tree complexity, sampling, and learning rate. Our data crosses years, so evaluate conservative models before increasing depth.
- [Parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): reviewed depth, child weight, regularization, sampling, and categorical controls. Initial working ranges are depth 3–6, child weight 10–100, learning rate 0.03–0.1, and hundreds of rounds; these are hypotheses for this data, not universal optima.
- [Categorical support](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): native categorical partitioning is available; category definitions must remain consistent.
- [Time features](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): ordinal and periodic time representations offer different inductive biases. Trees can already learn nonlinear time effects.
- [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): search excerpt identifies airport and schedule effects; full page returned 403. Only advance-known inputs will be considered here.

### Experiment 1 — exploration

Parent: b15ec66 (0.6743). Hypothesis: a longer ensemble of shallower, regularized trees may learn persistent effects while reducing 2005-specific interactions. Test 600 rounds, depth 4, learning rate 0.05, child weight 30, L2 10, and row sampling 0.8. Source: XGBoost tuning and parameter references above. Feature preparation stays the same so this first experiment tests the model regime.

Result: **0.6786**, **keep**, commit `f9c63fc`. Run time: 34.1s (training 3.2s, eval 30.9s, ok)
Compared with `b15ec66` (0.6743).

### Experiment 2 — ablation/simplification

Parent: f9c63fc (0.6786). Experiment 1 improved AUC by 0.0043, supporting the conservative ensemble regime. Evaluation still takes about 31s. Hypothesis: caching categorical dtypes and removing redundant membership masks preserves every feature value while reducing row-by-row overhead. A same-AUC result is acceptable only if this preparation is simpler or faster. Categorical handling follows the previously researched XGBoost requirement for consistent category definitions.

Result: **0.6786**, **keep**, commit `c633883`. Run time: 11.1s (training 3.1s, eval 7.9s, ok)
Compared with `f9c63fc` (0.6786).

### Experiment 3 — exploration

Parent: c633883 (0.6786). Experiment 2 preserved AUC and reduced evaluation from 30.9s to 7.9s; kept for speed. Hypothesis: treating day of month as ordered numeric discourages arbitrary 2005 day groupings and may transfer better to 2006. Replace only that categorical representation, preserving month and weekday categories. Source: [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). This tests representation, not new information.

Result: **0.6831**, **keep**, commit `ddf29fc`. Run time: 10.6s (training 3.1s, eval 7.5s, ok)
Compared with `c633883` (0.6786).

### Experiment 4 — ablation/simplification

Parent: `ddf29fc` (0.6831).

Hypothesis: Ordered days helped substantially, suggesting categorical day effects were noisy; dropping day of month entirely may improve transfer while simplifying the model.

Change: Remove day of month to reduce year-specific calendar noise.

Source/motivation: Experiment 3 improved 0.6786 to 0.6831; time representation research above.

Result: **0.6792**, **discard**, commit `e79b060`. Run time: 10.0s (training 2.9s, eval 7.1s, ok)
Compared with `ddf29fc` (0.6831).

### Experiment 5 — exploration

Parent: `ddf29fc` (0.6831).

Hypothesis: Explicit network and carrier-airport combinations can represent persistent operating differences with shallow trees, without requiring additional tree depth.

Change: Add route and carrier-origin/carrier-destination categorical interactions.

Source/motivation: [Google feature crosses](https://developers.google.com/machine-learning/crash-course/categorical-data/feature-crosses) and XGBoost native categorical documentation. Experiment 4 showed ordered day of month retains useful information; its deletion was reverted.

Result: **0.6709**, **discard**, commit `1eb29de`. Run time: 16.1s (training 5.4s, eval 10.6s, ok)
Compared with `ddf29fc` (0.6831).

### Experiment 6 — follow-up

Parent: `ddf29fc` (0.6831).

Hypothesis: The large loss from route categories suggests excessive categorical flexibility; restricting partition searches on the original categories may improve cross-year generalization.

Change: Limit categorical partition searches with max_cat_threshold=8.

Source/motivation: [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature), and experiment 5 (0.6709).

Result: **0.6838**, **keep**, commit `1485773`. Run time: 10.4s (training 2.8s, eval 7.7s, ok)
Compared with `ddf29fc` (0.6831).

### Experiment 7 — follow-up

Parent: `1485773` (0.6838).

Hypothesis: The day-of-month representation gain may extend to month: ordered splits can express broad seasonal changes with fewer arbitrary month groupings.

Change: Replace categorical month with ordered numeric month.

Source/motivation: Experiment 3 and [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).

Result: **0.6844**, **keep**, commit `04ee082`. Run time: 9.7s (training 2.7s, eval 6.9s, ok)
Compared with `1485773` (0.6838).

### Experiment 8 — exploration

Parent: `04ee082` (0.6844).

Hypothesis: Separating the scheduled HHMM value into hour and minute exposes recurring scheduling slots and gives the trees a coarse time-of-day feature. Training-only summaries show a strong daily pattern.

Change: Add departure hour and minute-of-hour features.

Source/motivation: [scikit-learn time-feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) and training data inspection. No target-derived features are added.

Result: **0.6839**, **discard**, commit `f0b8128`. Run time: 9.9s (training 2.8s, eval 7.1s, ok)
Compared with `04ee082` (0.6844).

### Experiment 9 — follow-up

Parent: `04ee082` (0.6844).

Hypothesis: With smoother calendar representations and constrained categorical splits in place, moderately deeper trees may recover useful airport-carrier-time interactions without the many sparse categories that failed in experiment 5.

Change: Increase tree depth from 4 to 6 with existing regularization.

Source/motivation: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html); this isolates depth from experiment 1's bundled regime change.

Result: **0.6851**, **keep**, commit `19698b2`. Run time: 10.4s (training 3.3s, eval 7.0s, ok)
Compared with `04ee082` (0.6844).

### Experiment 10 — exploration

Parent: `19698b2` (0.6851).

Hypothesis: Day of month is useful alone but its interactions with month and airports can fit individual 2005 weather days. An additive day effect should retain shared calendar patterns while blocking exact-date interactions.

Change: Make day of month an additive effect using interaction constraints.

Source/motivation: [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html). Use disjoint feature groups to avoid overlap semantics.

Result: **0.6805**, **discard**, commit `49f5282`. Run time: 10.3s (training 3.3s, eval 7.0s, ok)
Compared with `19698b2` (0.6851).

## Synthesis after 10 experiments

Best: **0.6851**, `19698b2`, versus baseline 0.6743 (+0.0108). Six experiments were kept, including the preparation speed simplification; three modeling changes were discarded plus the additive-day restriction (four discards total).

What helps: regularized boosting, ordered day/month representations, restricted categorical partition searches, and then modestly deeper trees. What did not: deleting day of month (0.6792), high-cardinality route/carrier crosses (0.6709), extra hour/minute features (0.6839), and forbidding day interactions (0.6805). The gains from calendar smoothing do not imply that calendar interactions should be removed. The current theory is that useful seasonal and operational interactions coexist with substantial temporal noise.

Evaluation preparation now takes about 7s instead of 31s. Further experiments can be more focused. Planned directions: a continuous annual calendar, training-budget/regularization balance, label-free schedule lookups, and boosted-forest averaging.

### Research refresh

- [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html): disjoint groups can impose additive structure. The tested day restriction reduced AUC, so no longer impose it.
- [XGBoost forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html): multiple trees per boosting round offer a different variance-control mechanism. A future test can retain boosting while averaging sampled trees at each step.
- [TargetEncoder](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.TargetEncoder.html): reviewed leakage risk when target statistics are fitted on the same rows consumed by the learner. If tested, use a separate reference subset of train.csv for the lookups; do not introduce cross-validation or a second selection metric.

### Experiment 11 — follow-up

Parent: `19698b2` (0.6851).

Hypothesis: Ordered month/day helped and their interactions remain valuable. A continuous annual coordinate may capture seasonal transitions within months using fewer splits.

Change: Add continuous day-of-year calendar feature.

Source/motivation: Experiments 3, 7 and 10; [time-feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).

Result: **0.6833**, **discard**, commit `901eec4`. Run time: 10.7s (training 3.4s, eval 7.3s, ok)
Compared with `19698b2` (0.6851).

### Experiment 12 — ablation/simplification

Parent: `19698b2` (0.6851).

Hypothesis: After two calendar experiments failed, test whether the current ensemble runs too long for transfer across years. Cutting rounds by two thirds directly tests overfitting and reduces model size.

Change: Reduce boosting rounds from 600 to 200.

Source/motivation: Observed failures in experiments 10–11 and the previously reviewed XGBoost bias-variance guidance.

Result: **0.6847**, **discard**, commit `2148e23`. Run time: 8.6s (training 1.8s, eval 6.8s, ok)
Compared with `19698b2` (0.6851).

### Experiment 13 — exploration

Parent: `19698b2` (0.6851).

Hypothesis: Holiday travel shifts relative to dates and weekdays. Event-relative calendar features may transfer more naturally across years than a raw annual coordinate.

Change: Add row-local Thanksgiving Christmas and New Year distances.

Source/motivation: [BTS Thanksgiving travel](https://www.bts.gov/topics/airlines-and-airports/increase-regional-air-travel-during-thanksgiving) and [OPM holiday definitions](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay/). Only holiday rules relevant to 2005/2006 are used; no delay observations from external data.

Result: **0.6832**, **discard**, commit `14b2b5a`. Run time: 11.5s (training 3.4s, eval 8.0s, ok)
Compared with `19698b2` (0.6851).

### Experiment 14 — exploration

Parent: `19698b2` (0.6851).

Hypothesis: Averaging randomized trees at each boosting step may reduce the variance left by a single-tree ensemble, while preserving the same 600-step learning schedule.

Change: Boost four sampled trees per round with node-wise feature sampling.

Source/motivation: [XGBoost random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). Feature expansion has not improved the best model; test a different variance-control mechanism.

Result: **0.6853**, **keep**, commit `268c7a1`. Run time: 21.8s (training 14.0s, eval 7.8s, ok)
Compared with `19698b2` (0.6851).

### Experiment 15 — exploration

Parent: `268c7a1` (0.6853).

Hypothesis: Airport IDs treat locations as unrelated categories. Distances from each airport to LAX, ORD, and ATL may expose regional structure and help generalize across airports and seasons.

Change: Add airport landmark-distance lookups fitted only on training routes.

Source/motivation: [Spatial flight-delay feature engineering](https://www.mdpi.com/2079-9292/13/24/4910). Adapt geographic-feature motivation without external datasets: fit median physical-distance lookups on train.csv; use neither flight counts nor labels.

Result: **0.6861**, **keep**, commit `1397e4b`. Run time: 29.2s (training 19.7s, eval 9.5s, ok)
Compared with `268c7a1` (0.6853).

### Experiment 16 — follow-up

Parent: `1397e4b` (0.6861).

Hypothesis: Geography adds useful shared structure. Requiring substantially more support per leaf may favor broad regional effects over small, year-specific airport and calendar interactions.

Change: Raise minimum child weight from 30 to 200.

Source/motivation: Experiments 14–15 and XGBoost parameter documentation already reviewed. This is a deliberate stronger-regularization test, not an additional feature change.

Result: **0.6852**, **discard**, commit `bcadd6c`. Run time: 30.7s (training 21.0s, eval 9.6s, ok)
Compared with `1397e4b` (0.6861).

### Experiment 17 — follow-up

Parent: `1397e4b` (0.6861).

Hypothesis: Direct landmark distances cover only 75–163 of 284 training airports. Weighted shortest paths can extend regional descriptors to less connected airports, though detours may distort physical distance.

Change: Fill landmark geography using shortest distances through the training route network.

Source/motivation: Experiment 15 and [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html). Edge weights are physical Distance values, never route frequencies or labels.

Result: **0.6863**, **keep**, commit `e05998e`. Run time: 24.3s (training 15.1s, eval 9.3s, ok)
Compared with `1397e4b` (0.6861).

### Experiment 18 — exploration

Parent: `e05998e` (0.6863).

Hypothesis: Geographic features now supply shared regional structure. One-category-at-a-time splits may let the model learn airport-specific residuals without grouping unrelated airports by noisy gradients.

Change: Use one-hot categorical splits instead of category partitions.

Source/motivation: [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html); set max_cat_to_onehot=512, above the largest training category vocabulary.

Result: **0.6864**, **keep**, commit `f24ced1`. Run time: 23.7s (training 14.3s, eval 9.3s, ok)
Compared with `e05998e` (0.6863).

### Experiment 19 — exploration

Parent: `f24ced1` (0.6864).

Hypothesis: A departure's position relative to its airport and route schedule may capture operational timing that absolute clock time misses. Median lookups preserve row-local evaluation and use no delay labels.

Change: Add departure-time offsets from origin and route schedule medians.

Source/motivation: The schedule-effect motivation from initial flight-delay research and the train-fitted lookup design in program.md. This is an original adaptation; no counts or evaluation-row aggregates are features.

Result: **0.6860**, **discard**, commit `d4aa4a4`. Run time: 24.9s (training 14.8s, eval 10.0s, ok)
Compared with `f24ced1` (0.6864).

### Experiment 20 — follow-up

Parent: `f24ced1` (0.6864).

Hypothesis: Minimum leaf support was too blunt. A split-gain penalty can suppress weak residual fits while retaining small airport groups when their evidence is strong.

Change: Require split gain of at least 2 using gamma regularization.

Source/motivation: XGBoost gamma/min_split_loss parameter documentation; motivated by experiment 16's failure and small recent gains from variance controls.

Result: **0.6862**, **discard**, commit `cb959b4`. Run time: 23.4s (training 14.1s, eval 9.2s, ok)
Compared with `f24ced1` (0.6864).

## Synthesis after 20 experiments

Best: **0.6864**, `f24ced1`; 10 experiments kept and 10 discarded. Baseline remains 0.6743.

Experiments 11–20: continuous annual dates, holiday distances, and relative schedule medians did not help. Boosted forests improved slightly, and train-derived geographic distances produced a more useful feature direction. Completing those distances via the route graph and changing to one-hot categorical splits gave further small gains. Increasing minimum leaf support and adding a split-gain penalty both lost AUC; neither was kept. One-hot splits also reduced artifact size from roughly 19 MB to 7.6 MB.

Working theory: preserve moderate interaction capacity, constrain categorical flexibility, and supply label-free structure shared by airports. The remaining increments are small, so test a different loss and numeric resolution rather than repeatedly adjusting the same regularizers.

### Research refresh

- [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html): histogram training uses a global numeric sketch. A coarser grid as a smoothing mechanism is our hypothesis, not a guarantee in the documentation.
- [XGBoost ranking](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html): pairwise logistic ranking offers a distinct objective. Any ranking trial must still be selected only by harness Eval AUC and supply predict_proba for the unchanged scoring call.
- [SciPy shortest paths](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html): the geography lookups use symmetric physical-distance edges, with no count features and no labels.

### Experiment 21 — exploration

Parent: `f24ced1` (0.6864).

Hypothesis: Coarser clock-time, distance, and geography thresholds may smooth fine-grained regional and schedule noise while retaining useful category-specific effects.

Change: Use 64 numeric histogram bins instead of 256.

Source/motivation: [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html). This tests resolution regularization after leaf support and gain thresholds failed.

Result: **0.6860**, **discard**, commit `79edd2f`. Run time: 24.8s (training 15.5s, eval 9.3s, ok)
Compared with `f24ced1` (0.6864).

### Plateau research pause after experiment 21

Experiments 19–21 all discarded with less than 0.001 loss versus the best. Stop local regularizer changes and review a different objective. Read XGBoost pairwise-ranking guidance and ranking normalization details; search the original RankNet work. Proposed adaptation: rank all training flights in one group with binary labels and mean pair sampling, keeping the harness AUC as the sole selection metric. A monotone sigmoid adapter supplies the existing predict_proba interface; it is not a new evaluation.

### Experiment 22 — exploration

Parent: `f24ced1` (0.6864).

Hypothesis: AUC depends on positive-negative ordering. Pairwise logistic training may prioritize those comparisons differently from pointwise logistic classification and break the current plateau.

Change: Train pairwise RankNet-style XGBoost on one global flight-ranking group.

Source/motivation: [RankNet original work](https://www.microsoft.com/en-us/research/publication/learning-to-rank-using-gradient-descent/) and [XGBoost learning to rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html). Use mean sampling, one pair per row, default pair-count normalization, and disable score-difference normalization.

Result: **0.6865**, **keep**, commit `0e9621c`. Run time: 48.0s (training 38.7s, eval 9.4s, ok)
Compared with `f24ced1` (0.6864).

### Experiment 23 — exploration

Parent: `0e9621c` (0.6865).

Hypothesis: Destination congestion and long-flight scheduling can depend jointly on departure time and distance. An approximate arrival coordinate makes this diagonal interaction easy to split on.

Change: Add approximate arrival clock time from departure and distance.

Source/motivation: Schedule-feature motivation from the flight-delay papers researched earlier. Formula is our explicit approximation: 30 minutes fixed overhead plus distance at 500 mph, measured in the origin's clock and wrapped to 24 hours; no actual arrival data is used.

Result: **0.6864**, **discard**, commit `aa90845`. Run time: 48.4s (training 38.0s, eval 10.4s, ok)
Compared with `0e9621c` (0.6865).

### Experiment 24 — ablation/simplification

Parent: `0e9621c` (0.6865).

Hypothesis: A training-fitted string-to-code lookup preserves categorical values while avoiding repeated category inference. Scratch checks found 0.250s versus 0.341s for 500 rows and no warning for unseen airports.

Change: Use cached categorical codes for faster preparation and explicit unknown handling.

Source/motivation: Direct preparation equivalence and unknown-category checks on training rows; categorical consistency requirement in the XGBoost documentation. Accept equal AUC because the measured preparation is faster.

Result: **0.6865**, **keep**, commit `66f3964`. Run time: 44.6s (training 37.0s, eval 7.6s, ok)
Compared with `0e9621c` (0.6865).

### Experiment 25 — follow-up

Parent: `66f3964` (0.6865).

Hypothesis: A fixed random permutation and 32 large groups approximate global positive-negative comparisons while reducing sorting work and allowing group-level parallelism. The features and training rows remain identical.

Change: Train pairwise ranking using 32 randomly mixed comparison groups.

Source/motivation: [XGBoost ranking tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html), which explains group-local comparisons and mean pair sampling. This tests computational grouping, not cross-validation or query-dependent features.

Result: **0.6868**, **keep**, commit `83d7f52`. Run time: 25.2s (training 17.8s, eval 7.3s, ok)
Compared with `66f3964` (0.6865).

### Experiment 26 — follow-up

Parent: `83d7f52` (0.6868).

Hypothesis: Mixed ranking groups improved quality and halved training time. More sampled comparisons may stabilize the pairwise gradient while pair-count normalization preserves its scale.

Change: Increase mean ranking pair sampling from 1 to 8 pairs per flight.

Source/motivation: [XGBoost ranking guidance](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) and [3.0 normalization changes](https://xgboost.readthedocs.io/en/stable/changes/v3.0.0.html). Experiment 25 is the direct motivation.

Result: **0.6859**, **discard**, commit `755d4e3`. Run time: 27.8s (training 20.4s, eval 7.4s, ok)
Compared with `83d7f52` (0.6868).

### Experiment 27 — exploration

Parent: `83d7f52` (0.6868).

Hypothesis: A cyclic month representation can express winter patterns spanning December and January without separate calendar boundaries. This avoids the daily resolution that failed in experiment 11.

Change: Replace ordered month with sine and cosine seasonal coordinates.

Source/motivation: [Scikit-learn cyclical feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). Round the trigonometric values to preserve intended symmetry between months.

Result: **0.6849**, **discard**, commit `7599937`. Run time: 24.6s (training 17.0s, eval 7.6s, ok)
Compared with `83d7f52` (0.6868).

### Experiment 28 — exploration

Parent: `83d7f52` (0.6868).

Hypothesis: Independent boosting trajectories may make different errors. Average raw ranking scores from two preselected seeds while retaining roughly the same total tree count as the current four-trees-per-round model.

Change: Average two independent rankers with two trees per boosting round each.

Source/motivation: [Scikit-learn ensemble overview](https://scikit-learn.org/stable/modules/ensemble.html). Seeds 42 and 137 are fixed in advance; no individual-seed scores are evaluated or selected.

Result: **0.6868**, **discard**, commit `9bf2f2b`. Run time: 26.6s (training 19.2s, eval 7.4s, ok)
Compared with `83d7f52` (0.6868).

### Experiment 29 — follow-up

Parent: `83d7f52` (0.6868).

Hypothesis: Large contradictory ranking errors may reflect unpredictable flight disruptions. Downweighting pairs with large score separation may regularize their influence without increasing leaf-size constraints.

Change: Enable score-difference normalization for pairwise ranking gradients.

Source/motivation: [XGBoost ranking normalization changes](https://xgboost.readthedocs.io/en/stable/changes/v3.0.0.html) and the ranking parameter reference reviewed before experiment 22. The flight-noise interpretation is our hypothesis.

Result: **0.6835**, **discard**, commit `3696332`. Run time: 24.4s (training 16.7s, eval 7.6s, ok)
Compared with `83d7f52` (0.6868).

### Experiment 30 — exploration

Parent: `83d7f52` (0.6868).

Hypothesis: Numerical delay priors may pool airport and carrier risk more effectively than independent one-hot splits. Fit these means on a fixed 20% reference subset and train the ranker on the other 80%, so no fitted row contributes its label to its own prior.

Change: Add disjoint-reference airport/carrier delay-mean lookups.

Source/motivation: [Target encoding leakage example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html). Adapt the separation principle using one reference split; no cross-validation, secondary metric, or count/frequency features. Geographic and category vocabularies still use train.csv inputs only.

Result: **0.6864**, **discard**, commit `16362e5`. Run time: 22.4s (training 14.4s, eval 8.0s, ok)
Compared with `83d7f52` (0.6868).

## Synthesis after 30 experiments

Best: **0.6868**, `83d7f52`; 13 experiments kept, 17 discarded. Gain over baseline: +0.0125 AUC.

The last ten trials found a small gain from pairwise ranking and a useful improvement from 32 randomly mixed comparison groups. Cached categorical codes preserved AUC, improved evaluation speed, and removed unseen-category warnings. More sampled ranking pairs, cyclic months, arrival-time proxies, score-difference normalization, and a separate-reference target-prior design did not improve the kept model. Two independent rankers tied AUC but were slower and more complex, so they were discarded under the keep rule.

The target-prior trial used a disjoint reference subset, so its result does not rely on self-label encoding. Its small loss could reflect the tradeoff between useful priors and fewer rows for the ranker; that experiment does not establish that target priors have no signal.

Next directions: change how trees allocate leaves, trade bagging for slower sequential boosting, and test whether broad calendar effects still help under the new ranking model. Preserve the feature and serialization invariants.

### Research refresh

- [Leaf-wise growth tuning](https://lightgbm.readthedocs.io/en/v4.5.0/Parameters-Tuning.html): leaf budgets and depth limits control different aspects of best-first trees. Apply that general idea using XGBoost's existing lossguide implementation, not another dependency.
- [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html): confirms histogram support for leaf-guided growth and maximum leaves.
- [Target-encoding separation](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html): reviewed why same-row target fitting overfits. Used only a reference split, not the source example's cross-validation procedure or evaluation.

### Experiment 31 — exploration

Parent: `83d7f52` (0.6868).

Hypothesis: One-hot airport effects may need long, selective paths. Best-first growth can allocate a limited number of leaves to those paths instead of expanding all levels uniformly.

Change: Use loss-guided tree growth with a 32-leaf budget.

Source/motivation: [Leaf-wise growth tuning](https://lightgbm.readthedocs.io/en/v4.5.0/Parameters-Tuning.html) and [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html). Test grow_policy=lossguide, max_depth=0, max_leaves=32.

Result: **0.6869**, **keep**, commit `4de24be`. Run time: 28.0s (training 20.4s, eval 7.6s, ok)
Compared with `83d7f52` (0.6868).

### Experiment 32 — exploration

Parent: `4de24be` (0.6869).

Hypothesis: More gradual residual updates may be more valuable than averaging four trees against the same residuals. Preserve the approximate total learning-rate budget while halving total trees and removing the parallel-tree parameter.

Change: Trade per-step forests for 1200 single-tree rounds at learning rate 0.025.

Source/motivation: XGBoost shrinkage guidance and the recent ranking/leaf-growth results. This compares sequential refinement with per-step averaging under a similar training budget.

Result: **0.6865**, **discard**, commit `3d9f2c9`. Run time: 19.6s (training 12.6s, eval 7.1s, ok)
Compared with `4de24be` (0.6869).

### Experiment 33 — follow-up

Parent: `4de24be` (0.6869).

Hypothesis: The 64-bin trial hurt accuracy. Finer thresholds may preserve useful schedule and geographic distinctions that are merged by the current global sketch, especially for less frequent airports.

Change: Increase numeric histogram resolution from 256 to 1024 bins.

Source/motivation: Experiment 21 and [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html). This tests the opposite, higher-resolution direction rather than another coarse-bin variation.

Result: **0.6869**, **discard**, commit `fe68a1c`. Run time: 29.0s (training 21.4s, eval 7.6s, ok)
Compared with `4de24be` (0.6869).

### Experiment 34 — exploration

Parent: `4de24be` (0.6869).

Hypothesis: A geometric representation based on all pairwise network distances may expose shared regional structure more efficiently than three handpicked landmarks. Keep six total geography features, three for each endpoint.

Change: Replace landmark distances with three classical-MDS airport coordinates.

Source/motivation: [Classical MDS](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.ClassicalMDS.html). Fit only on the undirected physical-distance graph built from train.csv; coordinates are approximations, not external latitude/longitude data.

Result: **0.6868**, **discard**, commit `79922bd`. Run time: 26.7s (training 19.8s, eval 6.9s, ok)
Compared with `4de24be` (0.6869).

### Plateau research pause after experiment 34

Experiments 32–34 failed to improve, each within 0.0004 of the best. Reviewed [a theory of ensemble diversity](https://arxiv.org/abs/2301.03962): the useful tradeoff involves both individual model quality and their dependent errors. This does not guarantee gains for AUC. Our next hypothesis is that different training objectives create more useful diversity than the identical-objective seed average that tied in experiment 28.

### Experiment 35 — exploration

Parent: `4de24be` (0.6869).

Hypothesis: Pairwise and pointwise objectives may make complementary errors across years. Combine the current full ranker with a matching XGBoost probability classifier using fixed equal margin weights.

Change: Blend equal ranking and logistic-classification margins.

Source/motivation: [Ensemble diversity theory](https://arxiv.org/abs/2301.03962), XGBoost ranking research, and experiment 28's tie for same-objective seed averaging. Train both models only on train.csv and evaluate only the combined model through the harness.

Result: **0.6867**, **discard**, commit `3053092`. Run time: 43.3s (training 34.5s, eval 8.8s, ok)
Compared with `4de24be` (0.6869).

### Experiment 36 — ablation/simplification

Parent: `4de24be` (0.6869).

Hypothesis: Year-specific seasonal severity may hurt transfer even with ordered months. Earlier tests changed the representation; this directly tests whether month contributes useful cross-year information to the current geographic ranker.

Change: Remove month from the final ranking feature set.

Source/motivation: The 2005-to-2006 split described in program.md and calendar results from experiments 7, 11, 13 and 27. This is a feature ablation with a simpler model if AUC ties.

Result: **0.6858**, **discard**, commit `bc9085c`. Run time: 27.3s (training 19.5s, eval 7.8s, ok)
Compared with `4de24be` (0.6869).

### Experiment 37 — ablation/simplification

Parent: `4de24be` (0.6869).

Hypothesis: Leaf-guided allocation helped slightly. Halving its leaf budget tests whether the lower-value branches are unnecessary or overfit; an equal score would justify the smaller model.

Change: Halve the loss-guided tree budget from 32 to 16 leaves.

Source/motivation: Experiment 31 and the previously reviewed leaf-wise tree tuning guidance. This is a direct simplification of the kept growth-policy result.

Result: **0.6858**, **discard**, commit `3feec22`. Run time: 23.2s (training 15.6s, eval 7.6s, ok)
Compared with `4de24be` (0.6869).

### Experiment 38 — exploration

Parent: `4de24be` (0.6869).

Hypothesis: The broad three-cross experiment failed with partitioned categories. A single carrier-origin feature with one-category splits may capture airline-specific hub behavior without the same arbitrary grouping flexibility.

Change: Add only a one-hot carrier-origin interaction.

Source/motivation: Experiment 5 versus the later one-hot categorical success, and [feature-cross guidance](https://developers.google.com/machine-learning/crash-course/categorical-data/feature-crosses). This explicitly changes both the scope and split representation of the earlier failed idea.

Result: **0.6876**, **keep**, commit `45a8abb`. Run time: 31.6s (training 22.6s, eval 9.0s, ok)
Compared with `4de24be` (0.6869).

### Experiment 39 — ablation/simplification

Parent: `45a8abb` (0.6876).

Hypothesis: Every categorical vocabulary is below the one-hot threshold, so max_cat_threshold does not control any split. Removing it should preserve predictions and make the configuration clearer.

Change: Remove inactive categorical-partition threshold under all-one-hot splitting.

Source/motivation: XGBoost categorical parameter definitions and experiment 38's one-hot configuration. Equal AUC is acceptable because this removes an unused parameter.

Result: **0.6876**, **keep**, commit `fc0e2f7`. Run time: 33.6s (training 24.9s, eval 8.7s, ok)
Compared with `45a8abb` (0.6876).

## Final summary

- Branch: `oct7`.
- Best Eval AUC: **0.6876**, commit `fc0e2f7da7077d7b2d58e503c9c4c41a91ed89e5`.
- Baseline: **0.6743**, `b15ec66`. Absolute AUC gain: **+0.0133**.
- Completed 39 non-baseline experiments plus the baseline (40 harness runs): 16 kept, 23 discarded, 0 crashes/timeouts.
- Saved artifact: `artifacts/fc0e2f7da7077d7b2d58e503c9c4c41a91ed89e5.pkl` (7.6 MB).
- Final run: training 24.9s including preparation/startup, evaluation 8.7s, total 33.6s. The last cleanup preserved the preceding best AUC and removed an unused parameter.

### What worked

The larger regularized ensemble and ordered day/month features produced the main early gains. Restricting categorical flexibility helped, as did one-hot categorical splits after adding train-derived geography. The geography uses shortest physical distances through the observed training route network to three landmarks; no flight counts are features. Pairwise ranking with 32 randomly mixed comparison groups improved AUC and reduced training cost. Leaf-guided trees with 32 leaves helped slightly. A late, narrow carrier-origin feature improved the score to 0.6876 when represented with one-hot splits. Cached categorical maps reduced per-row preparation overhead and explicitly handle unseen categories.

### What did not work

Broad partitioned route/carrier crosses were harmful early, illustrating that feature representation matters: the later single one-hot carrier-origin cross succeeded. Removing calendar variables, extra time/holiday features, schedule-median offsets, cyclical month features, and MDS geography did not improve the kept model. More ranking pairs, score-difference normalization, stronger leaf support, gain penalties, alternate bin resolutions, and fewer leaves also failed to improve. Independent-ranker averaging tied without simplifying the model; the ranking/classification blend was slightly worse. Disjoint-reference target means were close but did not offset their training-data tradeoff.

### Verification and limits

All model comparisons used the unchanged harness and its printed four-decimal Eval AUC. The only tracked file changed is train.py. The final artifact was reloaded successfully and passed batch-versus-single-row feature equivalence, target-label independence of features, unseen-airport/carrier handling, and finite prediction-shape checks using training rows only. These checks computed no additional AUC. The selected score is the development evaluation score; this run establishes no unseen-holdout performance claim.

### Next ideas

Test a similarly constrained carrier-destination interaction, and then ablate the carrier-origin feature within any improved combination. Investigate whether a small set of stable operational relationships helps more than additional high-cardinality route features. Keep paired comparisons deliberate, since most late gains were less than 0.001 AUC.

Stopped launching experiments when the harness reported less than two minutes remaining, as specified in program.md. The final clock stop follows this verification and summary.
