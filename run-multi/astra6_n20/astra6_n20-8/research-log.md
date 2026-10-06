# Research log: oct6

## Setup — 2026-10-06

- Branch: `oct6`, created directly from current HEAD `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist.
- Required dependencies are installed; no packages added.
- Initialized `output/results.tsv` with the required header only.
- `train.py` and `harness.py` are unchanged.
- Clock has not started. Awaiting confirmation before `python3 harness.py start`.
- The first run will establish the unchanged baseline via `python3 harness.py run`.
- Web research is required before the first non-baseline experiment.

## Baseline — b15ec66

Eval AUC **0.6743**; harness training 1.5 s, evaluation 31.2 s, total 32.7 s. Kept unchanged starter.
Training-only inspection: 200,000 rows; eight predictors; no missing values. Calendar columns are strings such as `c-11`; carrier/origin/destination have 20/283/283 levels. Eight CPUs available.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): regulate tree complexity and sampling; pair a smaller learning rate with more rounds.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, minimum child Hessian, L2 leaf penalty, and categorical split thresholds control complexity.
- [AWS tuning ranges](https://docs.aws.amazon.com/sagemaker/latest/dg/xgboost-tuning.html): supports exploring depths 0–10, child weight up to 120, rounds up to 4000, and sampling 0.5–1.0. These broad ranges are starting points, not prescriptions.
- [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): native partitioning groups categories; levels must remain consistent in training and inference.
- [scikit-learn temporal features](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): ordered and periodic representations are candidates for schedule/calendar features.
- [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): search excerpt motivates scheduled time and route features; full page was inaccessible, so use only as domain motivation.

## Experiment 1 — regularized shallow boosting

Category: exploration. Hypothesis: depth-4 trees, 500 rounds at learning rate 0.05, child weight 20, L2 penalty 10, and row sampling 0.8 should emphasize broad effects and resist year-specific interactions. Motivated by the tuning guide above. No feature changes.

Result: **0.6788**, commit `01bd06e`, **keep**. Run time: 34.0s (training 2.8s, eval 31.3s, ok)
Regularized shallow boosting gains 0.0045 over baseline. All predictors unchanged.

## Experiment 2 — simpler categorical preparation

Category: ablation/simplification. Hypothesis: fixed categorical dtypes can replace redundant membership filtering and repeated frame mutation with identical features and lower inference overhead. [pandas Categorical](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) documents conversion of values outside the specified categories to missing values. Keep only at equal AUC if faster/simpler, or at higher AUC.

Result: **0.6788**, commit `c9795e4`, **keep**. Run time: 13.0s (training 2.7s, eval 10.3s, ok)
AUC unchanged; evaluation falls from 31.1 s to 10.1 s. Pandas emits a deprecation warning for unseen category values; current behavior remains correct, but explicit category codes would be more robust.

## Experiment 3 — remove day-of-month categories

Category: ablation/simplification. Hypothesis: arbitrary partitions of the 31 day-of-month values learn weather and calendar coincidences from 2005 that do not transfer to 2006. Removing this feature should reduce that variance. Motivation: baseline feature gain gives day-of-month considerable weight despite its weak year-invariant meaning. All hyperparameters unchanged.

Result: **0.6794**, commit `c1cd931`, **keep**. Run time: 11.8s (training 2.6s, eval 9.2s, ok)
Removing day-of-month improves by 0.0006 and further reduces row preparation cost; retain the smaller feature set.

## Experiment 4 — carrier-airport interaction categories

Category: exploration. Hypothesis: explicit carrier/origin and carrier/destination categories let shallow trees learn airline-specific airport effects without spending multiple levels on their component columns. This adapts [XGBoost native categorical partitioning](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) to the airline/airport predictors. Fit category dictionaries on training only. Use category indexers to map unseen combinations to missing values and avoid pandas deprecated unseen-value construction; feature values remain row-independent.

Result: **0.6714**, commit `faa7fad`, **discard**. Run time: 11.6s (training 3.4s, eval 8.2s, ok)
A large 0.0080 loss suggests these high-cardinality interactions overfit or shift between years; discard. Explicit index-based categorical conversion was faster and can be retained independently in a later simplification.

## Experiment 5 — shallower additive structure

Category: follow-up. Hypothesis: the gain from shallower regularized trees and the loss from explicit high-cardinality interactions indicate that broad main effects and low-order interactions transfer best. Reduce depth from 4 to 2 while doubling rounds from 500 to 1000 (learning rate remains 0.05) to recover main-effect fitting capacity. Based on the XGBoost complexity guidance already researched.

Result: **0.6786**, commit `dfa894a`, **discard**. Run time: 12.2s (training 3.0s, eval 9.2s, ok)
AUC drops 0.0008; depth-2 trees appear too restrictive despite extra rounds. Revert to depth 4.

## Experiment 6 — ordered month encoding

Category: exploration. Hypothesis: replacing arbitrary category partitions of Month with its numeric order encourages contiguous seasonal intervals and limits year-specific grouping. The [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) motivates testing temporal representation rather than assuming unordered encoding. Keep all other predictors and the best depth-4 model fixed.

Result: **0.6803**, commit `218d66b`, **keep**. Run time: 11.5s (training 2.6s, eval 8.9s, ok)
Ordered month improves 0.0009, supporting smoother seasonal modeling; keep.

## Experiment 7 — schedule components

Category: exploration. Hypothesis: hour-of-day and minute-within-hour separate coarse daily delay accumulation from schedule bank patterns. Add hour, minute, and periodic time-of-day sine/cosine while retaining the original ordered schedule time. This is an inference from the [scikit-learn temporal feature discussion](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), adapted for boosted trees. No data-dependent fitting or counts are involved.

Result: **0.6813**, commit `6b9edc7`, **keep**. Run time: 12.3s (training 2.7s, eval 9.6s, ok)
Schedule components improve AUC by 0.0010. Training-only hour summaries rise from morning through evening, then decline late at night; a globally monotonic time constraint would be misspecified.

## Experiment 8 — one-category-versus-rest splits

Category: exploration. Hypothesis: native category partitions can group many airports using noisy training residuals. Forcing one-category-versus-rest splits (`max_cat_to_onehot=512`) may produce more stable airport effects at the same tree depth. Based on [XGBoost categorical split documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). This changes split semantics, not feature dictionaries.

Additional research: [target encoding](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) and its [cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) emphasize excluding a row's target from its own encoding. Any future target lookup must obey that and the repository's row-independent preparation rule. [Monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) can smooth known relationships, but training hour patterns are not globally monotonic, so a simple positive time constraint is not justified.

Result: **0.6795**, commit `b60d0fc`, **discard**. Run time: 12.2s (training 2.3s, eval 9.9s, ok)
AUC falls 0.0018. Grouping airports is useful; unrestricted one-versus-rest splitting is too weak at the current tree count.

## Experiment 9 — stronger leaf and split regularization

Category: follow-up. Hypothesis: airport group partitions are useful (experiment 8), but their smaller leaves may fit unstable residuals. Increase minimum child weight 20→100, L2 leaf penalty 10→50, and minimum split gain 0→2 while keeping best features, depth, and rounds fixed. These jointly test stronger smoothing rather than a different category representation; parameter rationale comes from the XGBoost tuning guide.

Result: **0.6805**, commit `f74154b`, **discard**. Run time: 12.5s (training 2.8s, eval 9.7s, ok)
Stronger leaf regularization loses 0.0008; revert. The main limitation may be representation of airport interactions rather than tree complexity alone.

## Experiment 10 — excluded-partition target lookup features

Category: exploration. Hypothesis: stable smoothed delay rates may represent airports and their interactions with less variance than native high-cardinality categorical partitions. Replace raw Origin/Dest categories with rate features for Origin, Dest, CarrierOrigin, CarrierDest, and Route, retaining native carrier/day-of-week. Source: [scikit-learn target encoding and leakage example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html).

Construction: deterministically hash each row's predictors (never its target or index) into one of five partitions. Each partition's lookup is fitted on the other four training partitions. `prepare` chooses that same excluded-partition lookup using the row alone, at both training and inference. Thus a training label cannot enter its own feature; no cross-validation model fitting or additional scoring is performed. Counts are used only internally as denominators for smoothed means, never returned as features. Smoothing uses 100 pseudo-observations for airports and 200 for pairs. All model training remains on the complete training file, with the harness as the sole evaluation metric.

Result: **0.6774**, commit `b875ec8`, **discard**. Run time: 21.5s (training 3.1s, eval 18.5s, ok)
AUC drops 0.0039. Global delay-rate ordering loses useful conditional airport information or encodes unstable year-specific rates; discard. Training-only consistency and label-independence checks passed.

## Synthesis after 10 experiments

Best is **0.6813 at 6b9edc7**, +0.0070 over baseline. The successful changes are shallower regularized boosting, removing arbitrary day-of-month categories, using ordered month values, and adding schedule components. Simpler categorical preparation saves about 21 seconds per evaluation without changing AUC. Depth 2, one-versus-rest airport splits, and stronger leaf penalties each lose performance; grouping airport effects and some interaction capacity are necessary. Both raw carrier-airport combinations and excluded-partition target rates failed, so unconstrained high-cardinality interactions and global target summaries are not good directions yet.

Working theory: departure time is dominant, and stable conditional airport/carrier effects need moderate tree depth. Fine calendar effects and high-cardinality interactions can capture the wrong year's structure. Next: constrain which variables interact rather than uniformly reducing depth, test non-target schedule-relative features, and examine variance reduction with boosted random forests. Revisited external sources after the tenth experiment as required.

## Research refresh and experiment 11 — separate calendar effects

Sources: [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) describes restricting allowed feature combinations; [boosted random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes averaging multiple sampled trees within a boosting round. Both provide ways to lower variance without making every tree shallow.

Category: exploration. Hypothesis: month/weekday effects should be broad additive adjustments, whereas schedule, carrier, airport, and distance interactions can remain flexible. Separate these two feature groups with interaction constraints. This directly targets potentially unstable calendar-by-airport interactions, rather than uniformly reducing model capacity.

Result: **0.6810**, commit `bcc8fcc`, **discard**. Run time: 12.2s (training 2.7s, eval 9.5s, ok)
AUC is 0.0003 below best; some calendar interactions seem useful. Revert rather than keep a near tie.

## Experiment 12 — departures relative to typical schedules

Category: exploration. Hypothesis: time relative to the usual origin/route departure schedule captures operational context beyond absolute departure time. Fit origin and route median departure minutes on training predictors only, then add both medians and current-minus-median offsets. This adapts the explicit route-median example in `program.md`; [pandas group median documentation](https://pandas.pydata.org/docs/reference/groupby.html) verifies the fitting operation. No target or frequency features are involved. All aggregation happens before `prepare`, with fixed lookups inside it.

Result: **0.6810**, commit `6c536e7`, **discard**. Run time: 13.5s (training 3.0s, eval 10.5s, ok)
AUC is again 0.6810, 0.0003 below best; schedule-relative summaries add complexity without a gain. Discard.

## Experiment 13 — boosted random forests

Category: exploration. Hypothesis: averaging three differently sampled trees per boosting round should reduce the instability of categorical partitions without losing their expressive power. Use 500 rounds, three parallel trees, row sampling 0.7, and per-node column sampling 0.8. The redundant schedule representations ensure most nodes retain time information despite feature sampling. Source: [XGBoost random forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). Training remains far below the one-minute limit at the observed two-second single-tree runtime.

Result: **0.6817**, commit `3f7660e`, **keep**. Run time: 19.7s (training 9.7s, eval 10.0s, ok)
AUC improves 0.0004 to 0.6817; keep. Training is 9.7 s, comfortably inside the one-minute limit.

## Experiment 14 — geography from training route distances

Category: exploration. Hypothesis: numeric airport coordinates inferred from route distances allow regional sharing while retaining native airport identities. Build an undirected graph whose edge weights are median route miles; fill missing distances with graph shortest paths; use the top three classical scaling components as airport coordinates. Add coordinates for origin and destination. This uses no labels, counts, external datasets, or additional files.

Sources: [scikit-learn Isomap explanation](https://scikit-learn.org/stable/modules/manifold.html#isomap) connects shortest paths with eigenvector embeddings; [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html) documents the graph operation. Applying it to route-distance geometry is my hypothesis, not a claim from these sources. Also replace deprecated categorical construction with explicit index codes; this preserves existing category values and unknown-to-missing behavior.

Result: **0.6816**, commit `88253ef`, **discard**. Run time: 17.6s (training 9.5s, eval 8.1s, ok)
AUC 0.6816 narrowly misses best by 0.0001; discard under the strict keep rule. The representation is plausible but has not shown a gain. Explicit category codes reduce evaluation to 7.8 s despite added features.

## Experiment 15 — holiday-relative calendar features

Category: exploration. Hypothesis: distances to major travel holidays transfer across years better than day-of-month categories, especially for movable holidays. Compute signed day offsets (clipped at two weeks) to Thanksgiving, Christmas, New Year, July 4, Memorial Day, and Labor Day from month/day/weekday alone. The weekday supplies the calendar alignment for movable holidays; both dataset years are non-leap years. No year indicator, target, or cross-row calculation enters `prepare`. Source for the holiday calendar: [OPM federal holidays](https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/). Travel-delay benefit is a hypothesis, not asserted by OPM.

Result: **0.6834**, commit `fbce28e`, **keep**. Run time: 22.2s (training 10.2s, eval 12.0s, ok)
Holiday alignment improves AUC by 0.0017, the largest feature gain so far. Keep. Calendar alignment checks passed for both years.

## Experiment 16 — fewer rounds after holiday features

Category: ablation/simplification. Hypothesis: later boosting rounds may fit year-specific residual patterns once strong schedule and holiday effects have been captured. Reduce rounds 500→200 at the same learning rate, feature set, sampling, and forest size. This tests training duration/model complexity directly; the earlier depth experiment changed interaction capacity instead. Source: XGBoost learning-rate/round complexity guidance from the initial research.

The exact holiday definitions used in experiment 15 are also documented by [OPM holiday FAQ](https://www.opm.gov/frequently-asked-questions/pay-and-leave-faq/pay-administration/what-are-federal-holidays/).

Result: **0.6846**, commit `91310ec`, **keep**. Run time: 16.4s (training 4.3s, eval 12.1s, ok)
Shorter boosting improves AUC by 0.0012 to 0.6846 while cutting training from10.2 s to4.3 s. Strong evidence that late rounds overfit temporal residuals.

## Experiment 17 — locate the underfitting boundary

Category: follow-up. Hypothesis: since 200 rounds beats 500, test 100 rounds to determine whether the useful signal is learned even earlier. This deliberately halves the effective boosting duration, preserving every other setting. A loss would establish that the optimum lies beyond this underfitting boundary rather than justify repeatedly shrinking the model.

Result: **0.6846**, commit `00b5521`, **keep**. Run time: 14.4s (training 2.6s, eval 11.8s, ok)
Printed AUC remains exactly 0.6846 while training falls from4.3 s to2.6 s and tree count halves. Keep under the equal-AUC simplification rule.

## Experiment 18 — more interactions with a short boosting path

Category: follow-up. Hypothesis: at only 100 rounds the model can afford richer within-tree interactions without the late residual fitting that hurt at 500 rounds. Increase depth 4→5 while retaining the short path, holiday features, and sampled forest. This tests whether stable holiday/schedule/airport interactions require an extra level, distinct from earlier depth tests on the much longer path without these features.

Result: **0.6847**, commit `86abd8b`, **keep**. Run time: 14.7s (training 2.9s, eval 11.8s, ok)
Depth5 improves printed AUC by 0.0001 to0.6847. Keep under the strict rule; this small gain needs cautious interpretation until independent holdout scoring by the human.

## Experiment 19 — coarser numeric split bins

Category: exploration. Hypothesis: reducing histogram resolution from256 to64 bins smooths exact schedule and distance thresholds while preserving the low-cardinality holiday values. This regularizes numerical split locations rather than airport partitions or tree depth. [XGBoost max_bin documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) explains the split-resolution tradeoff. Keep other settings at the current best.

Result: **0.6851**, commit `21bb201`, **keep**. Run time: 14.7s (training 3.0s, eval 11.8s, ok)
AUC improves by0.0004 to0.6851. Coarse numerical boundaries seem more transferable across years.

## Experiment 20 — pairwise ranking objective

Category: exploration. Hypothesis: a pairwise logistic ranking loss can emphasize positive-versus-negative ordering, which is directly relevant to AUC, instead of probability calibration. Treat the whole training set as one ranking group, use `rank:pairwise` with mean pair sampling and four pairs per sample, and preserve the best tree settings. Wrap raw scores with a monotonic sigmoid solely to provide the harness's required two-column `predict_proba` interface. No alternate evaluation or extra data is introduced.

Source: [XGBoost learning-to-rank tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) explains pairwise objectives and mean sampling. The potential AUC advantage for this classification dataset is my inference, to be tested by the harness.

Result: **0.6829**, commit `31106f7`, **discard**. Run time: 21.6s (training 9.8s, eval 11.8s, ok)
Pairwise objective scores0.6829, below logistic0.6851; discard. It trains and serializes successfully, but does not improve ranking on the evaluation year.

## Synthesis after 20 experiments

Best is **0.6851 at 21bb201**, +0.0108 over baseline. The strongest recent findings: properly aligned holiday offsets add0.0017, shortening 500→200 rounds adds0.0012, and 100 rounds ties200 with lower cost. Depth5 and64 numeric bins give further smaller gains. Three sampled trees per round improve stability. Schedule-relative medians, disjoint calendar interactions, and distance-derived airport geometry narrowly miss; pairwise ranking and target-rate replacement lose more clearly.

Working theory: useful signal is learned early; later trees amplify year-specific residuals. Preserve moderate interaction depth and meaningful holiday structure while smoothing numerical thresholds. Next research/experiments: independent probability averaging versus within-round forests, categorical partition limits, ablation of successful feature bundles, and blending useful near-miss representations under the much shorter boosting path.

Research refresh: [scikit-learn voting ensembles](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier) describes probability averaging; [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) limits partition split candidates; [pandas explicit category codes](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.from_codes.html) supports stable missing-value encoding.

## Experiment 21 — explicit categorical codes

Category: ablation/simplification. Hypothesis: direct indexing against the fitted category Index and `Categorical.from_codes` preserve all model inputs while avoiding repeated dtype construction checks and the pandas warning for unseen values. This isolated simplification reuses a performance improvement observed in discarded geography experiment14. Keep at equal AUC only if faster or simpler; unlike experiment14, no geographic features are added.

Result: **0.6851**, commit `5142fc1`, **keep**. Run time: 11.9s (training 3.0s, eval 9.0s, ok)
AUC unchanged at0.6851; evaluation improves from11.5 s to8.7 s and the run emits no unseen-category deprecation warnings. Keep the faster equivalent representation.

## Experiment 22 — average independent boosting paths

Category: follow-up. Hypothesis: averaging three complete forests with fixed seeds42,17,2026 reduces sampling variance that within-round averaging alone does not remove, because later residuals also depend on earlier random splits. Train each member sequentially on all training rows with identical best hyperparameters and average probabilities. This is the [soft-voting approach](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier); no seed is selected by a separate score and only the overall ensemble is evaluated by the harness.

Result: **0.6848**, commit `2df6f46`, **discard**. Run time: 16.4s (training 7.2s, eval 9.2s, ok)
Averaged model scores0.6848, below the current single forest0.6851. Discard; do not select individual seeds based on additional evaluations.

## Experiment 23 — ablate minute-within-hour

Category: ablation/simplification. Hypothesis: exact scheduled minute mostly reflects mutable schedule details rather than stable delay risk. It has the lowest training split gain (5.4 versus16.6 for the next-lowest, Distance). Remove only DepMinute, leaving absolute time, hour, and periodic time components. This checks which part of the successful schedule bundle is necessary; split gain is used only to select the ablation, not as an evaluation metric.

Result: **0.6850**, commit `cdc76bd`, **discard**. Run time: 11.8s (training 3.0s, eval 8.8s, ok)
AUC0.6850 is0.0001 below best; revert despite the simpler representation. Weak training gain does not establish that a feature is dispensable.

## Experiment 24 — continuous annual season

Category: follow-up. Hypothesis: the successful holiday offsets partly provide within-month seasonal resolution. Adding coarse week-of-year and annual sine/cosine can represent broader transitions without depending on arbitrary month boundaries. Use the already calculated non-leap day-of-year, with all transforms inside `prepare`. Source: [scikit-learn periodic time features](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). This differs from restoring unordered day-of-month: ordering and periodicity carry stable calendar structure.

Result: **0.6844**, commit `8b53424`, **discard**. Run time: 13.0s (training 3.0s, eval 10.0s, ok)
AUC0.6844 is0.0007 below best. Fine annual progression adds unstable within-season detail beyond the useful holiday windows. Third consecutive discard with less than0.001 movement: trigger plateau research before the next experiment.

## Plateau research after experiment24

Three consecutive small discards (22–24) prompted fresh research. [Categorical split limits](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) offer a targeted way to reduce category partition overfitting. [DART documentation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and the [original DART paper](https://arxiv.org/abs/1505.01866) describe dropout as a way to reduce dependence on early trees and over-specialization of later trees. These are meaningfully different from averaging independently trained models.

## Experiment 25 — limit categorical partitions

Category: exploration. Hypothesis: limiting `max_cat_threshold` to16 prevents splits from selecting large collections of noisy airport categories while retaining multi-category grouping that outperformed pure one-versus-rest splits. Preserve numerical bins, features, and boosting duration. This tests a previously untouched categorical-specific regularizer.

Result: **0.6851**, commit `e5e4a2b`, **keep**. Run time: 11.7s (training 2.8s, eval 8.9s, ok)
AUC ties0.6851. Training falls slightly3.0→2.8 s and artifact size3.7→3.2 MB as category partitions get smaller; keep the cheaper split search under the equal-AUC efficiency rule.

## Experiment 26 — dropout boosting

Category: exploration. Hypothesis: dropout prevents later trees from specializing in residuals tied too tightly to early trees, potentially addressing the temporal overfitting seen in longer ordinary boosting. Use rate_drop0.1 and skip_drop0.5 with tree normalization; double rounds100→200 because many dropout rounds receive reduced weight. All other best settings remain fixed. Source: [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) and its original paper from the plateau research. XGBoost3.4 accepts these dropout parameters directly with the tree booster.

Result: **0.0000**, commit `e3db4ad`, **crash**. Run time: 60.0s (training 60.0s, eval 0.0s, timeout-training)
Harness killed training at60.0 s before evaluation; log as crash and restore best. Dropout removes prediction caching, so its quadratic prediction cost is material here.

## Experiment 27 — resource-bounded dropout retry

Category: exploration. Hypothesis: retaining the best100-round duration should make dropout fit the training budget; its reduced update weights may still regularize the model usefully. This is a direct response to the200-round timeout, not a cosmetic repeat. Keep dropout rate0.1 and skip probability0.5, but use100 rounds. If this fails or underperforms, move on from this expensive approach.

Result: **0.6838**, commit `35c5bb4`, **discard**. Run time: 26.8s (training 17.9s, eval 8.9s, ok)
The shorter dropout run fits the limit (17.9 s training) but scores0.6838, below0.6851; discard and stop pursuing this dropout configuration.

## Experiment 28 — geometry under shorter regularized boosting

Category: exploration. Hypothesis: geography's earlier near-miss (experiment14, only0.0001 below its comparator) may become useful under100 rather than500 rounds,64 numerical bins, a categorical partition cap, and holiday features. These changes substantially reduce capacity for fitting unstable regional residuals. Reintroduce the exact three-dimensional route-distance geometry while preserving all current best settings. This is a deliberate combination of a near-miss representation with independently successful regularization, not a duplicate trial.

Result: **0.6851**, commit `ddd32cf`, **discard**. Run time: 12.6s (training 3.1s, eval 9.5s, ok)
Geometry ties0.6851 but adds code, features, and runtime, so discard. Two different model regimes have failed to show an advantage.

## Experiment 29 — joint departure-time and distance proxy

Category: exploration. Hypothesis: a smooth combination of departure time and distance may represent long-haul/overnight timing that requires many axis-aligned tree splits. Add a rough end-of-flight clock proxy `departure_minutes + Distance/8 +30`, modulo1440, plus its sine/cosine. The480mph and30minute constants are simple fixed feature heuristics, not estimates of actual arrival or local destination time.

Domain research: an expanded search extract from the [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) discusses scheduled duration and time-of-day as useful inputs. Our dataset lacks duration/arrival information, so this experiment uses only a deterministic proxy from permitted predictors, with no external flight data or meta-model targets.

Result: **0.6849**, commit `431a3de`, **discard**. Run time: 12.4s (training 2.9s, eval 9.5s, ok)
AUC0.6849 is0.0002 below best; discard this joint transformation. It does not add enough useful information beyond time and distance at present.

## Experiment 30 — isolate within-round averaging

Category: ablation/simplification. Hypothesis: row and column sampling may explain the gain from experiment13 without needing three trees per round. Remove `num_parallel_tree=3` (default is one), keeping every other best setting fixed. The earlier forest experiment changed sampling and forest size together; this ablation resolves that ambiguity and could reduce training/model size substantially at equal AUC.

Result: **0.6838**, commit `f0df75b`, **discard**. Run time: 10.3s (training 1.5s, eval 8.9s, ok)
AUC drops0.0013 to0.6838. Three-tree averaging provides real benefit beyond row/column sampling in this configuration; restore it.

## Synthesis after 30 experiments

Best is **0.6851 at e5e4a2b**, with efficient categorical codes and capped partition candidates. Independent three-seed averaging, minute-feature removal, annual cyclic features, and the joint time-distance proxy all miss by small margins. Geometry now ties but is too complex to keep. Dropout200 times out; dropout100 is feasible but worse. The decisive ablation is one versus three trees per round: removing within-round averaging loses0.0013, confirming its benefit under otherwise identical settings.

Working theory remains a short, moderately deep stochastic forest with calendar alignment. Further gains likely need more stable estimation or useful coarse structure, not many additional fine-grained features. Next: test more within-round averaging, modest recency weighting for temporal drift, and targeted feature-bundle/regularization ablations. Research refreshed at this checkpoint as required.

## Experiment 31 — larger within-round forest

Category: follow-up. Hypothesis: the loss from removing averaging in experiment30 suggests sampling variance still matters. Increase parallel trees3→9 at the same100 boosting rounds, rather than increasing residual-fitting duration. This is distinct from averaging independent complete models (experiment22) because the nine trees share a residual target each round. Based on the XGBoost boosted-forest documentation; expected training remains well inside60 seconds.

Result: **0.6849**, commit `4eb06f9`, **discard**. Run time: 15.6s (training 6.5s, eval 9.1s, ok)
Nine trees score0.6849, slightly below three-tree0.6851 while tripling model size; discard. The one/three/nine comparison favors the moderate forest.

## Experiment 32 — mild temporal importance weighting

Category: exploration. Hypothesis: late-2005 flights are modestly more representative of2006 carrier/airport operations. Apply exponential training weights with a24-month half-life, normalized to mean1, computed from MonthNumber already returned by `prepare`. All rows remain in training, and inference features are unchanged. The long half-life retains seasonal coverage rather than concentrating training on winter.

Research: [Instance-Conditional Timescales of Decay](https://arxiv.org/abs/2212.05908) discusses the tradeoff between recent relevance and losing useful history; [Handling Concept Drift in Global Time Series Forecasting](https://arxiv.org/abs/2304.01512) includes exponential/linear weighting baselines. This simple fixed decay is a test inspired by that literature, not an implementation of their learned weighting systems.

Result: **0.6852**, commit `4fdc056`, **keep**. Run time: 11.7s (training 2.8s, eval 8.9s, ok)
AUC improves one printed increment to0.6852; keep, while treating this very small difference cautiously. Full training coverage and inference preparation are unchanged.

## Experiment 33 — smoothed logistic targets

Category: exploration. Hypothesis: replacing binary training targets in the loss by0.05/0.95 discourages overconfident fits to uncertain flight outcomes while preserving their ideal ranking. Implement weighted logistic gradient/Hessian using a custom objective; retain original labels in `prepare` and in harness evaluation.

Sources: [Does label smoothing mitigate label noise?](https://arxiv.org/abs/2003.02819) studies smoothing under noisy labels; [XGBoost custom objectives](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html) documents the interface. Applicability to these boosted trees is an experimental inference, not established by the cited neural-network results. Inspected the installed objective adapter to ensure sample weights are applied exactly once. Validate the derivatives numerically on synthetic values before training.

Result: **0.6855**, commit `205250f`, **keep**. Run time: 11.8s (training 3.0s, eval 8.8s, ok)
AUC improves0.0003 to0.6855. Synthetic finite-difference checks pass, and the serialized classifier retains the binary:logistic prediction link. Keep.

## Experiment 34 — loss-guided tree growth

Category: exploration. Hypothesis: a fixed24-leaf budget with loss-guided growth allocates more depth to genuinely useful conditional effects while limiting overall tree size. Replace depth5 growth with `grow_policy=lossguide`, max_depth0, max_leaves24, and explicit hist method. Other settings, including smoothing and recency weights, stay fixed.

Sources: [XGBoost grow-policy parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) specify loss-change-prioritized growth; [LightGBM's leaf-wise explanation](https://lightgbm.readthedocs.io/en/stable/Features.html#leaf-wise-best-first-tree-growth) motivates the leaf budget tradeoff. The implementation continues to use XGBoost only.

Result: **0.6857**, commit `b4f6243`, **keep**. Run time: 12.3s (training 3.4s, eval 8.8s, ok)
AUC improves0.0002 to0.6857. A fixed leaf budget allocates interactions more effectively than uniform depth5 in this setting; keep.

## Experiment 35 — stronger label smoothing

Category: follow-up. Hypothesis: if limiting overconfidence is the mechanism behind experiment33, stronger0.15/0.85 target smoothing may further stabilize the now loss-guided trees. Change only the smoothing strength, from a10% mixture with uniform labels to30%. This deliberately tests a larger regularization step; a loss would indicate useful signal is being over-smoothed. The derivative formula is unchanged from the finite-difference-validated objective.

Result: **0.6854**, commit `205293e`, **discard**. Run time: 12.4s (training 3.4s, eval 9.0s, ok)
AUC falls0.0003 to0.6854, suggesting stronger smoothing removes useful signal. Restore mild0.05/0.95 smoothing.

## Experiment 36 — additive warmup before interactions

Category: exploration. Hypothesis: fitting broad main effects with100 rounds of depth-1 trees before adding100 loss-guided rounds prevents interactions from absorbing stable time/calendar effects too early. Use training continuation on the same complete training frame and same weights throughout; no additional dataset, validation metric, or saved earlier-run model is used. The final artifact contains one continued booster.

Source: [XGBoost training continuation example](https://xgboost.readthedocs.io/en/stable/python/examples/continuation.html) documents `xgb_model` and the additive round count. Changing the growth policy between the two stages is the experimental hypothesis.

Result: **0.6843**, commit `37c5779`, **discard**. Run time: 13.9s (training 4.7s, eval 9.2s, ok)
Staged training scores0.6843, losing0.0014. The additive prefix does not improve transfer and adds trees; discard.

## Experiment 37 — require meaningful split gain

Category: ablation/simplification. Hypothesis: loss-guided growth should avoid using its leaf budget on very weak residual splits. Set gamma2 while preserving child weight20 and L2 penalty10; this isolates the split-gain requirement, unlike experiment9 which simultaneously increased three regularizers on a different long-path model. The XGBoost parameter guide explains gamma as the minimum split loss reduction.

Result: **0.6857**, commit `d8749b7`, **discard**. Run time: 13.0s (training 4.0s, eval 9.0s, ok)
AUC ties0.6857, but training is slower4.0 versus3.4 s and code adds a parameter; discard because the equal-AUC efficiency/simplicity condition is not met.

## Experiment 38 — stronger row sampling

Category: follow-up. Hypothesis: with three-tree within-round averaging confirmed useful, reducing row sampling0.7→0.5 may further decorrelate residual fits and improve temporal generalization. Keep forest size, leaf budget, column sampling, and objective fixed. This falls within the uniform-sampling range discussed in the XGBoost parameter guide and tests randomness independently of tree complexity.

Result: **0.6857**, commit `e767316`, **discard**. Run time: 12.6s (training 3.4s, eval 9.2s, ok)
The stronger row sampling tied the best AUC but was slightly slower and produced a larger artifact, so retain subsample=0.7.

## Experiment 39 — narrower holiday windows

Category: ablation/simplification. Hypothesis: the successful holiday offsets may retain incidental day-level weather associations outside the immediate travel week. Clip each offset to plus/minus 7 instead of 14 days, preserving holiday alignment while reducing the number of distinct date values. This follows up the strong calendar gain in experiment 15, with all model settings fixed. The holiday definitions remain those verified against the OPM sources above.

Result: **0.6861**, commit `abbe46c`, **keep**. Run time: 12.6s (training 3.4s, eval 9.3s, ok)
AUC improves by 0.0004 to 0.6861. Keeping the shorter windows suggests the most useful holiday distinctions are close to the holiday itself.

## Research refresh — residual-aware sampling

Read the current [XGBoost sampling and regularization documentation](https://xgboost.readthedocs.io/en/stable/parameter.html). CPU gradient-based sampling became supported in version 3.2, so installed 3.4.1 can use it with histogram trees. It samples using gradient and Hessian magnitudes. Unlike changing the uniform sampling fraction in experiment 38, this changes which residual patterns are represented. The gain is uncertain because harder examples may also carry unobserved weather noise. L1 regularization is another untested direction: it shrinks weak leaf updates selectively.

## Experiment 40 — gradient-based row sampling

Category: exploration. Hypothesis: gradient-aware sampling can represent the remaining residual structure more efficiently than uniform sampling within the three-tree average. Change only sampling_method, preserving subsample=0.7 to isolate the selection mechanism. This is distinct from experiment 38's smaller uniform sample. Source: XGBoost sampling documentation linked above.

Result: **0.6852**, commit `aed6770`, **discard**. Run time: 13.1s (training 4.2s, eval 8.9s, ok)
Gradient-based sampling drops AUC by 0.0009 to 0.6852 and increases training cost. Uniform sampling remains preferable.

## Synthesis after 40 experiments

Best is 0.6861 at `abbe46c`, versus the baseline's 0.6743. In experiments 31–40, mild recency weighting, mild label smoothing, loss-guided leaf allocation, and shorter holiday windows helped. Larger forests, stronger smoothing, staged stump warmup, split-gain thresholds, stronger uniform sampling, and gradient-based sampling did not help. Stable low-complexity timing and calendar structure still appears to matter more than large ensembles or a focus on hard residuals.

Fresh research: [Zhang and Yu's boosting early-stopping analysis](https://arxiv.org/abs/math/0508276) treats stopping as regularization; [XGBoost's learning-rate scheduler API](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler) provides per-round control; and [hierarchical shrinkage](https://arxiv.org/abs/2202.00858) suggests post-hoc regularization toward ancestor predictions. These are mechanisms, not evidence that they improve this dataset. Near-term direction: test a more finely stepped boosting path at the same total nominal learning rate, then simplify the per-tree leaf budget or isolate L1 shrinkage. Ancestor shrinkage would need more implementation and validation than the remaining time justifies.

## Experiment 41 — finer boosting steps

Category: follow-up. Hypothesis: reducing learning_rate from 0.05 to 0.025 while increasing rounds from 100 to 200 keeps nominal total shrinkage at 5 but makes residual updates less abrupt and averages over more independent row samples. This differs from experiments 16–17, which changed cumulative boosting strength by changing only rounds. The current model also has loss-guided growth and soft targets. Source: XGBoost's eta documentation and boosting regularization research above.

Result: **0.6860**, commit `d0a17a4`, **discard**. Run time: 15.0s (training 5.9s, eval 9.0s, ok)
AUC slips to 0.6860 while model size doubles. The finer boosting path does not improve this evaluation set; restore the 100-round fit.

## Experiment 42 — halve the leaf budget

Category: ablation/simplification. Hypothesis: loss-guided growth improved by allocating a fixed 24-leaf budget, but some remaining deeper interactions may be year-specific. Halving the leaf budget to 12 tests whether the stable short holiday windows and timing features need fewer interactions. Unlike the earlier depth-2 experiment, this permits selective deep paths while limiting total leaves, on the current short boosting path. Source: the loss-guided growth documentation cited for experiment 34.

Result: **0.6842**, commit `4dabe76`, **discard**. Run time: 11.6s (training 2.8s, eval 8.9s, ok)
The smaller trees train faster but lose 0.0019 AUC. The useful timing and holiday interactions need more than the 12-leaf budget allows; restore 24.

## Experiment 43 — selective leaf shrinkage with L1

Category: exploration. Hypothesis: experiment 42 shows that a strict global leaf cap removes useful interactions, while stronger label smoothing also lost signal. Adding reg_alpha=5 instead penalizes small leaf outputs, potentially suppressing weak residual patterns while retaining the full 24-leaf structural budget. Keep L2, sampling, smoothing, and all features fixed. Source: [XGBoost L1 regularization parameter](https://xgboost.readthedocs.io/en/stable/parameter.html), read in the experiment 40 research refresh. This is the first isolated L1 penalty in this run.

Result: **0.6874**, commit `a996279`, **keep**. Run time: 12.6s (training 3.4s, eval 9.3s, ok)
AUC improves by 0.0013 to 0.6874. Selectively shrinking weak leaf outputs works substantially better than removing half the structural leaf budget.

## Experiment 44 — stronger L1 shrinkage

Category: follow-up. Hypothesis: the large 0.0013 gain from alpha=5 indicates that many weak residual leaf updates are unreliable across years. Increase alpha to 20, a fourfold change, to test whether more aggressive sparsity retains the strongest transferable effects. This explicitly follows the first isolated L1 success, with tree capacity and all other regularizers fixed. A loss would indicate that the stronger threshold removes useful residual signal. Source: XGBoost L1 documentation cited in experiment 43.

Result: **0.6861**, commit `0617ebf`, **discard**. Run time: 12.2s (training 3.2s, eval 9.0s, ok)
AUC falls by 0.0013 despite a smaller model, showing that the fourfold stronger L1 threshold removes useful signal. Keep alpha=5.

## Experiment 45 — increase recency weighting

Category: follow-up. Hypothesis: the positive but small gain from 24-month half-life weighting in experiment 32 may have been limited by noisy unregularized leaves. With alpha=5 now protecting weak leaf updates, increase the temporal weighting contrast using a 12-month half-life. January-to-December weight contrast changes from about 1.37 to 1.89. All training rows remain included, with mean-normalized weights. This tests whether stronger emphasis on more recent operations complements L1; seasonal coverage loss is the counter-hypothesis. Sources: time-decay papers cited for experiment 32.

Result: **0.6877**, commit `954290c`, **keep**. Run time: 12.4s (training 3.4s, eval 9.0s, ok)
AUC rises by 0.0003 to 0.6877. Stronger recency weighting complements the selected L1 regularization in this evaluation.

## Experiment 46 — remove redundant raw departure time

Category: ablation/simplification. Hypothesis: the hour, minute, sine, and cosine features already encode scheduled departure time. Removing the raw HHMM column may reduce redundant split choices and simplify the model without losing ranking signal. This differs from experiment 23's removal of minute detail: minute precision remains available in three features. Keep all training settings fixed.

Result: **0.6879**, commit `eccad8d`, **keep**. Run time: 12.6s (training 3.5s, eval 9.2s, ok)
Removing the redundant departure column improves AUC by 0.0002 to 0.6879 with one fewer input feature; keep.

## Experiment 47 — longer boosting with selective regularization

Category: follow-up. Hypothesis: L1 regularization suppresses weak late-stage updates and may allow a longer useful boosting path. Increase rounds from 100 to 200 at unchanged learning_rate=0.05. This deliberately doubles total nominal shrinkage, unlike experiment 41, which kept it fixed and predated L1 regularization and stronger recency weighting. Earlier reductions from 500 to 100 rounds warned against overfitting, so this trial directly tests whether the new regularization changes that balance. Source: boosting stopping/shrinkage research discussed at the 40-experiment synthesis.

Result: **0.6875**, commit `68c0995`, **discard**. Run time: 14.7s (training 5.8s, eval 8.9s, ok)
AUC falls to 0.6875 and the artifact more than doubles. L1 does not remove the benefit of stopping at 100 rounds; restore the shorter fit.

## Experiment 48 — retain only winter holiday offsets

Category: ablation/simplification. Hypothesis: summer holiday offsets may partly capture year-specific warm-season weather effects already broadly represented by month. Remove Memorial Day, July 4, and Labor Day offsets together, retaining Thanksgiving, Christmas, New Year, numeric month, and weekday. This tests a coherent feature family rather than selecting individual dates from evaluation outcomes. If accuracy holds, preparation and interpretation become simpler; if it drops, the full holiday bundle is justified.

Result: **0.6873**, commit `41a43e9`, **discard**. Run time: 11.8s (training 3.3s, eval 8.5s, ok)
Removing the summer holiday offsets lowers AUC by 0.0006. Their signal is useful beyond month and weekday, so retain all six holiday offsets.

## Experiment 49 — ablate random column sampling

Category: ablation/simplification. Hypothesis: the three-tree average may obtain enough diversity from row sampling, making random per-node column exclusion unnecessary after redundant raw departure time was removed. Remove colsample_bynode=0.8 so every split considers every feature. This isolates one component of experiment 13's successful joint averaging setup; experiment 30 already established that the parallel-tree component matters. An equal result would justify a simpler configuration; a loss would establish that feature sampling still adds useful diversity. Source: the XGBoost column-sampling documentation reviewed above.

Result: **0.6877**, commit `f2491c8`, **discard**. Run time: 12.4s (training 3.3s, eval 9.1s, ok)
AUC falls by 0.0002 to 0.6877. Per-node feature sampling adds useful diversity beyond row sampling, so restore the best model with colsample_bynode=0.8.

## Final summary

Completed 49 experiments plus the untouched baseline on branch `oct6`. Including the baseline, there are 21 keeps, 28 discards, and one training-timeout crash. Every trial is recorded in `output/results.tsv`. The last three experiments were discarded and the branch is restored to the best kept commit.

**Best Eval AUC: 0.6879**, commit `eccad8d65b44c7584a9f80f1bcc37a5b54ad770a`, compared with baseline **0.6743** at `b15ec66`: an absolute gain of **0.0136**. Its saved artifact is `artifacts/eccad8d65b44c7584a9f80f1bcc37a5b54ad770a.pkl`. The selected run took 12.6 seconds (3.5 seconds training, 9.2 seconds evaluation; rounded components), versus 32.7 seconds for the baseline. Faster row preparation accounts for the evaluation speed improvement.

The final model uses 16 features: distance; numeric month; six holiday offsets clipped to one week; departure hour, minute, sine, and cosine; and native categorical weekday, carrier, origin, and destination. It fits 100 boosting rounds with three parallel trees per round, loss-guided growth with a 24-leaf budget, 64 histogram bins, L1=5, L2=10, row sampling=0.7, and node-level column sampling=0.8. Mild label smoothing uses targets 0.05 and 0.95; mean-normalized training weights have a 12-month recency half-life.

What worked: simplifying calendar representation, decomposing departure time, aligning movable holidays, shortening holiday windows, reducing cumulative boosting, averaging three trees within each round, coarse numerical bins, mild smoothing and recency weighting, selective L1 regularization, and removing redundant raw departure time. Fixed category lookups and explicit category codes made row-at-a-time preparation much faster. Ablations showed that the summer holiday family and random feature sampling still contribute to the final model.

What did not work: high-cardinality categorical combinations, replacing native categories with target encodings, inferred airport geography, route-relative departure features, approximate arrival-time features, pairwise ranking, DART, larger whole-model or within-round ensembles, gradient-based row sampling, stronger label smoothing, excessive L1 shrinkage, halving the leaf budget, staged stump warmup, or extending the final boosting path. One DART trial exceeded the 60-second training limit; the shorter DART trial completed but lost accuracy.

Interpretation: this evaluation favors compact, regularized interactions between stable timing/calendar structure and airport/carrier effects. The L1 result suggests weak residual leaf predictions were a more useful regularization target than a uniformly smaller structural tree budget. These are conclusions from the prescribed evaluation set; tiny fourth-decimal gains are not evidence of statistical certainty or unseen holdout performance.

Next: have the human assess the saved artifacts on the untouched holdout using their workflow. In a new research run, explore ancestor-based shrinkage or a small, predeclared ensemble of structurally different regularized models; also test whether the mild smoothing still helps after introducing L1. Those would address distinct mechanisms rather than selecting more random seeds or finely sweeping one parameter.

Final verification passed: the saved artifact reloads; features and labels are identical for batch and single-row preparation on 128 training rows; flipping target labels leaves all features unchanged; unseen airport/carrier categories map to missing and produce finite predictions; probability outputs are finite and normalized; feature names match the saved booster; and the required final save_and_evaluate call remains last. All 50 result rows have valid four-column structure and unique commit hashes. Git is clean on the best commit, only train.py differs from the starting commit, and harness.py is unchanged. No additional metric was computed and no holdout data was accessed.

The experiment loop ended when the harness reported 1 minute 55 seconds remaining, as required by the two-minute wrap-up rule. The clock stop command is the final action of this run.
