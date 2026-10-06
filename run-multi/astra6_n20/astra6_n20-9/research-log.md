# Research log

## Setup — 2026-10-06

- Run tag and branch: `oct6`.
- Starting commit: `b15ec66f306812020bf48c0fc4fc83e50cb24ce1`; branched directly from the current HEAD.
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist.
- Training data check: 200,000 rows, 9 expected columns, 100,000 Y and 100,000 N labels, no missing values.
- Verified installed Python dependencies import successfully: NumPy, pandas, XGBoost, scikit-learn, and cloudpickle.
- Initialized `output/results.tsv` with the required tab-separated header; output remains ignored by Git.
- Starter code remains unchanged. The first run will establish the baseline.
- Setup completed before starting the experiment clock; awaiting confirmation to begin the one-hour run.

## Experiment protocol

- Start with `python3 harness.py start`, then run the unchanged baseline through the harness.
- Record every experiment's commit, printed Eval AUC, keep/discard/crash decision, hypothesis, and observations.
- Research external sources before the first non-baseline experiment and at the intervals required by `program.md`.
- Respect the harness limits: 60 seconds for training and 300 seconds for evaluation.

## Baseline — b15ec66

- Unchanged starter: Eval AUC **0.6743**; training phase 1.5s, evaluation 31.0s. Kept.
- Clock started after user confirmation.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): lower learning rate with more rounds; manage complexity and stochasticity to control variance.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, minimum child Hessian, leaf regularization, and sampling are distinct controls.
- [Categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): categorical partitions can pool related values; category vocabularies must remain consistent at prediction.
- [AWS tuning ranges](https://docs.aws.amazon.com/sagemaker/latest/dg/xgboost-tuning.html): broad ranges include depths 0–10 and learning rates 0–1; use conservative interior values here.
- Training inspection: calendar fields have c-N labels; 283 origins and destinations; HHMM departure times; no missing values. Year shift argues for restraint on calendar memorization.

## Experiment 1 — exploration: smoother boosting

Hypothesis: 600 depth-4 trees at learning rate 0.05, minimum child weight 20, L2 10 and row subsampling 0.85 can learn more stable structure than the short depth-6 baseline. Motivated by the tuning guide and the 2005-to-2006 shift. Keep features unchanged to isolate model capacity/regularization as a category of change.

Result: **0.6786**, commit `08ae37d`, **keep**. Run time: 34.1s (training 3.1s, eval 31.1s, ok)

Improved by 0.0043 over baseline. More sustained but conservative fitting is a useful starting point.

## Experiment 2 — ablation: remove day of month

Hypothesis: day-of-month categorical splits capture weather/day patterns in 2005 that do not repeat in 2006. Remove this column while keeping the successful model settings. [Scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) distinguishes categorical and ordered time representations; this ablation tests whether the detailed calendar signal is useful at all.

Result: **0.6794**, commit `feb7777`, **keep**. Run time: 30.1s (training 2.9s, eval 27.1s, ok)

AUC rose by 0.0008 and evaluation became faster. Supports avoiding detailed day-of-month effects across years.

## Experiment 3 — simplification: faster categorical preparation

Hypothesis: construct the frame directly and let fixed-vocabulary pandas categoricals map unseen values to missing, removing redundant membership masks and assignment overhead. Features and ordering must be exactly unchanged; keep only equal AUC with faster evaluation or a higher AUC. This addresses per-row inference overhead rather than model capacity.

Result: **0.6794**, commit `a50cfe7`, **keep**. Run time: 19.6s (training 2.9s, eval 16.7s, ok)

Kept identical AUC with evaluation reduced from 27.1s to 16.7s. Tests confirmed exact feature equality and row invariance, including an unseen airport. Pandas emits a deprecation warning for unseen categories; explicit Index.get_indexer/from_codes will preserve the tested behavior in the next change.

## Experiment 4 — exploration: route category

Hypothesis: origin-destination identity exposes route-specific delay structure without requiring two separate splits. Use a vocabulary fitted only on train; unseen routes map to missing. There are 4,290 training routes. Based on [XGBoost categorical partitions](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) and [flight-delay research examining time, airline and airport factors](https://arxiv.org/abs/2408.02802). Also replace deprecated unknown-category construction with explicit integer codes, preserving all existing features.

Result: **0.6704**, commit `fa6bd3a`, **discard**. Run time: 18.7s (training 4.4s, eval 14.3s, ok)

Route feature reduced AUC by 0.0090 and expanded the artifact to 33.8 MB. Strong evidence that unrestricted high-cardinality interactions overfit this sample/year shift. Discarded; the category-code implementation itself passed invariance tests and will be retained in the next candidate as an equivalent cleanup.

## Experiment 5 — follow-up: limit categorical partitions

Hypothesis: limiting max_cat_threshold to 8 reduces noisy grouping of airport categories. The route failure motivates a direct test of categorical regularization on the original retained features. [Parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature). Preserve the explicit-code cleanup from experiment 4; it changes no feature values.

Result: **0.6799**, commit `c09ab85`, **keep**. Run time: 11.0s (training 2.6s, eval 8.4s, ok)

Improved AUC by 0.0005. Evaluation fell to 8.4s with explicit codes, and the artifact is 2.7 MB. Retain both the regularization and equivalent preparation cleanup.

## Experiment 6 — follow-up: richer interactions under categorical regularization

Hypothesis: depth 6 may recover useful carrier-airport-time interactions while max_cat_threshold=8 limits the category grouping that overfit in experiment 4. Change depth only from the kept experiment 5; 600 rounds and all regularization remain fixed.

Result: **0.6803**, commit `bd946b5`, **keep**. Run time: 11.9s (training 3.2s, eval 8.7s, ok)

Depth 6 improved AUC by 0.0004 after categorical regularization; retain. This is modest evidence for useful interactions, not a reason to grow unrestricted deep trees.

## Experiment 7 — exploration: within-hour scheduled departure minute

Hypothesis: the minute component of HHMM captures recurring scheduling/connection banks independent of time of day; a single split on CRSDepTime cannot express this. Add CRSDepTime % 100, retaining the original time. Informed by the [time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html); the specific flight-bank hypothesis is an inference to test, not a reported result of that example.

Result: **0.6807**, commit `f986834`, **keep**. Run time: 13.4s (training 3.3s, eval 10.2s, ok)

AUC increased by 0.0004. The feature passed single-row invariance and input-label independence checks. Retain.

## Experiment 8 — ablation: exclude month interactions

Hypothesis: retain the broad monthly delay prior but disallow interactions between month and operational predictors, reducing year-specific weather/schedule memorization. Use disjoint interaction groups: Month alone and all other features together. [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) explicitly support restricting potentially spurious interactions.

Result: **0.6817**, commit `aefb79b`, **keep**. Run time: 13.2s (training 3.2s, eval 10.0s, ok)

AUC improved by 0.0010. Broad seasonality helps more when isolated from detailed operational interactions. Retain the constraint. Last-kept training gain ranked time highest, then carrier, origin, month and destination; this diagnostic used no evaluation data.

## Experiment 9 — exploration: departure relative to route median

Hypothesis: a route-relative schedule position captures recurring service patterns with one numeric feature, without the noisy native route category from experiment 4. Fit the median scheduled time in minutes per origin-destination route on train and look it up inside prepare; emit departure minutes minus that median. No row frequencies are used as features. This follows the allowed lookup pattern in program.md and the earlier time-feature research.

Result: **0.6815**, commit `a192f54`, **discard**. Run time: 16.0s (training 3.5s, eval 12.6s, ok)

AUC decreased by 0.0002; discarded under the strict keep rule. Unlike raw route categories this was close, but no evidence yet that unsupervised route schedule centering helps.

## Experiment 10 — ablation: one-hot categorical splits

Hypothesis: one-category-at-a-time splits will avoid noisy category pooling and transfer airport/carrier effects more robustly across years. Set max_cat_to_onehot=10000 so all retained categories use this strategy; other hyperparameters and additive-month constraint remain fixed. This differs from experiment 5 by eliminating pooling entirely rather than merely limiting group size. Based on the [categorical split documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html).

Result: **0.6833**, commit `2ef73b4`, **keep**. Run time: 13.1s (training 3.1s, eval 10.0s, ok)

AUC improved by 0.0016, the largest gain since initial boosting changes. Artifact shrank to 1.7 MB. Category pooling was overfitting despite the threshold reduction.

## Synthesis after 10 experiments

Best: **0.6833**, commit `2ef73b4`, versus baseline 0.6743 (+0.0090). Conservative boosting, dropping day of month, separating month from operational interactions, and especially replacing category pooling with one-hot splits helped. Scheduled minute gave a small improvement. Raw route identity strongly hurt; route-relative median time was a near miss. Preparation is now about three times faster, leaving room for richer models.

Working theory: stable time-of-day, carrier, and individual airport effects transfer; detailed date effects and broad data-driven category groups are fragile across years. Test more rounds under one-hot splits, then smoothed historical effects and geography inferred solely from train distances.

New research at the 10-experiment pause:
- [Gradient boosting regularization example](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_regularization.html): explore the interaction of shrinkage, subsampling and iteration count.
- [Isomap documentation](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html) and [SciPy shortest paths](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html): a weighted distance graph can supply continuous airport representations without external airport data or traffic counts. This is an experimental inference for this dataset.
- [CatBoost target-statistics paper](https://papers.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf): even leave-one-out target means can leak via conditional shifts. Any future target-mean features must use frozen lookup subsets that exclude each row and preserve exactly the same mapping at row-wise inference.

## Experiment 11 — follow-up: longer one-hot boosting

Hypothesis: one-category splits need more rounds to learn the many airport effects; increase 600 rounds to 1500 while preserving learning rate and all structural regularization. Unlike experiment 1 this isolates iteration count under the now-successful feature/constraint setup.

Result: **0.6833**, commit `c253c99`, **discard**. Run time: 16.4s (training 6.2s, eval 10.2s, ok)

Printed AUC tied 0.6833 while training and model size increased. Discarded: no simplification or speed gain. More rounds alone do not improve the current representation.

## Experiment 12 — exploration: smoothed historical target lookups

Hypothesis: continuous, shrunk historical delay rates expose airport and carrier-route structure more safely than raw high-cardinality categories. Add five rates: origin, destination, carrier-origin, carrier-destination, and route, smoothed with strength 100 toward 0.5.

Fit five frozen lookup variants using deterministic hashes of the eight input fields. Each variant excludes its own hash bucket; every row, whether training or inference, uses the variant selected by its input-only hash. This is feature estimation only: fit one XGBoost model and use only the harness metric, with no auxiliary model evaluation. The same row always gets the same features and its own target cannot enter its lookups. Counts only normalize/smooth means and are never output as features.

Sources: [scikit-learn TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) on shrinkage and self-exclusion, and the previously read CatBoost paper on leakage pitfalls.

Result: **0.6820**, commit `2da62f4`, **discard**. Run time: 32.9s (training 5.1s, eval 27.8s, ok)

AUC dropped by 0.0013 and evaluation grew to 27.8s. Discarded. The encoding passed row and label-independence checks, so this is an unhelpful representation here rather than an inference inconsistency.

## Experiment 13 — exploration: distance-derived airport coordinates

Hypothesis: continuous airport coordinates allow nearby airports to share stable regional structure without learning high-cardinality target-based groups. Build an undirected airport graph from median training route distances, compute weighted shortest-path distances, and fit three classical multidimensional-scaling coordinates. Prepare only looks up origin/destination coordinates; labels, route frequencies and external data are not used for this representation.

Sources read: [Isomap analysis](https://arxiv.org/abs/2006.10858) on representing shortest-path structure with Euclidean coordinates, and [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html). Using this to approximate regional airport relationships is a hypothesis, not a claim of recovering true geographic coordinates.

Result: **0.6845**, commit `9333601`, **keep**. Run time: 19.2s (training 3.9s, eval 15.3s, ok)

Improved AUC by 0.0012. The graph was connected; row/label invariance checks passed. Coordinates offer useful continuous airport structure without target statistics or external data.

## Experiment 14 — follow-up: larger supported leaves with geographic sharing

Hypothesis: now that continuous airport coordinates can pool regional structure, raising min_child_weight from 20 to 80 should reduce noisy small-airport or local-interaction effects. Change this parameter only; no direct frequency features are introduced.

Result: **0.6843**, commit `c4106c1`, **discard**. Run time: 18.7s (training 3.5s, eval 15.2s, ok)

AUC decreased by 0.0002 despite a smaller model. Discarded under the strict keep rule; geographic features do not remove the need for some locally supported effects.

## Experiment 15 — exploration: boosted randomized forests

Hypothesis: averaging four randomized trees at each boosting step reduces variance while retaining the successful depth and features. Set num_parallel_tree=4 and colsample_bynode=0.85, keeping row subsampling 0.85. The change is a variance-reduction strategy, distinct from adding later boosting rounds (experiment 11). Source: [XGBoost forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html).

Result: **0.6846**, commit `4355150`, **keep**. Run time: 29.7s (training 14.0s, eval 15.7s, ok)

AUC increased by 0.0001, so kept under the printed-AUC rule. Training rose to 14.0s, leaving headroom within the 60s cap. The gain is small and should not be interpreted as established holdout improvement.

## Experiment 16 — exploration: holiday-relative calendar features

Hypothesis: holiday position transfers across years better than raw day of month. Derive the nearest major holiday type and signed day offset within seven days from each row's month, day and weekday. Cover New Year, Memorial Day, Independence Day, Labor Day, Thanksgiving and Christmas, including adjacent-month boundaries. Keep these features with Month in a separate calendar interaction group.

[BTS Thanksgiving travel analysis](https://www.bts.gov/topics/airlines-and-airports/increase-regional-air-travel-during-thanksgiving) documents holiday-related shifts in travel patterns; it does not establish that these features will improve this delay model. No external traffic measurements are incorporated.

Result: **0.6871**, commit `c492d8a`, **keep**. Run time: 40.7s (training 20.5s, eval 20.2s, ok)

Improved AUC by 0.0025 to 0.6871. Holiday formulas passed explicit checks around 2005/2006 dates and all preparation invariance checks. Training 20.5s and evaluation 20.2s remain within limits.

## Experiment 17 — exploration: pairwise ranking loss

Hypothesis: uniform positive-negative pair comparisons align more directly with discrimination/AUC than pointwise log loss. Use rank:pairwise with mean pair sampling (two pairs per sample), one global training group, and a monotonic logistic mapping of ranking scores for the harness prediction API. This mapping is not a probability-calibration claim. Start with 400 single-tree rounds to keep pair construction within the 60s training budget; retained features and regularization otherwise stay fixed.

Read [XGBoost ranking tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) and ranking parameter documentation. Only the usual harness Eval AUC will select the model.

Result: **0.6858**, commit `3fe581d`, **discard**. Run time: 43.1s (training 23.8s, eval 19.3s, ok)

AUC was 0.6858, 0.0013 below the kept classifier, so discarded. Training completed in 23.8s; no timing failure. Pointwise logistic boosting remains preferable in the tested budget/configuration.

## Experiment 18 — follow-up: continuous route direction

Hypothesis: differences between destination and origin coordinates, normalized by route distance, expose directional route structure that requires complex interactions between separate endpoint coordinates. Add three direction features using the already retained distance-derived representation. This does not use route identity, counts, or targets. Training-only gain inspection confirms both airport coordinates and holiday features are used by the kept model.

Result: **0.6874**, commit `cb1d734`, **keep**. Run time: 42.2s (training 19.9s, eval 22.3s, ok)

AUC improved by 0.0003; retained. All features passed single-row, unknown-airport and label-independence checks.

## Experiment 19 — follow-up: prune low-gain splits

Hypothesis: gamma=5 removes small residual splits on the expanded geographic and holiday feature set, reducing variance without the broad leaf-size restriction that hurt in experiment 14. This changes the minimum split loss improvement only.

Result: **0.6866**, commit `1ba6167`, **discard**. Run time: 37.9s (training 16.0s, eval 21.9s, ok)

AUC fell by 0.0008, despite faster training and smaller artifact. Discarded; the retained model benefits from some smaller incremental splits.

## Experiment 20 — ablation: narrower holiday window

Hypothesis: only the three days immediately surrounding holidays provide stable transferable demand effects; the seven-day window may capture weather noise. Change the inclusion window from ±7 to ±3, keeping identical holiday formulas and all model settings.

Result: **0.6873**, commit `0b8edbf`, **discard**. Run time: 42.4s (training 19.9s, eval 22.5s, ok)

AUC decreased by 0.0001; discarded. Retain the full seven-day holiday context.

## Synthesis after 20 experiments

Best: **0.6874**, commit `cb1d734`, +0.0131 from baseline. New gains came from distance-derived airport coordinates, normalized route direction, and especially transferable holiday features. Generic target means and pairwise ranking loss did not help. More boosting rounds, larger leaves, heavier split pruning, and a narrower holiday window failed the keep rule. A boosted forest helped only slightly.

Working theory: stable domain structure matters more than additional model complexity. Keep the seven-day holiday context and flexible operational interactions, with calendar effects separated. The best model trains in about 20s, allowing a two-member ensemble within the 60s cap.

Research at this pause: [soft voting](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier) motivates averaging probabilities; [XGBoost base margins](https://xgboost.readthedocs.io/en/stable/tutorials/intercept.html) allow separate control of calendar and operational model complexity; [monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) may help impose a daytime delay trend, but the observed overnight downturn means a naive all-day constraint is unsuitable.

## Experiment 21 — follow-up: average two independently randomized forests

Hypothesis: equal-weight probabilities from fixed seeds 42 and 2026 reduce seed-specific variance left after within-round averaging. Fit both only on train.csv, with no component evaluation or weight selection. Keep the current features/settings; total training is expected around 40s.

Result: **0.6874**, commit `2083555`, **discard**. Run time: 62.8s (training 39.3s, eval 23.5s, ok)

AUC tied 0.6874 with almost twice the training time and artifact size. Discarded. Experiments 19–21 are three consecutive near-best discards, triggering focused plateau research.

## Plateau research after experiment 21

Three consecutive discards within 0.001 of the best suggest further generic variance reduction is not enough. Revisited [XGBoost base margins](https://xgboost.readthedocs.io/en/stable/tutorials/intercept.html) and searched additive boosted-model research to separate calendar complexity from richer operational interactions. The next test changes how model capacity is allocated rather than adding another similar regularizer.

## Experiment 22 — exploration: shallow calendar component plus operational residual

Hypothesis: month and holidays need a smoother component than the operational features. Fit a 200-round depth-2 calendar model with minimum child weight 200 and L2 50, then fit the retained 600-round depth-6 operational boosted forest using the calendar raw margins as its initial offset. Predictions supply the same calendar margins to the operational component. Calendar inputs cannot leak into operational trees; all features remain in prepare. No extra evaluation or data is introduced.

Result: **0.6893**, commit `a87bd7d`, **keep**. Run time: 37.2s (training 14.9s, eval 22.3s, ok)

AUC improved by 0.0019 to 0.6893 and training decreased to 14.9s. Separately controlling calendar capacity broke the plateau. Keep the serialized two-component predictor.

## Experiment 23 — follow-up: shrink calendar contribution

Hypothesis: reducing calendar log-odds to half strength limits reliance on 2005-specific seasonal amplitudes while preserving holiday and monthly ordering. Multiply calendar margins by 0.5 both when fitting the operational residual and when predicting; no mismatch between training and inference. The successful separate-component model makes this otherwise unavailable regularization test possible.

Result: **0.6908**, commit `e4feece`, **keep**. Run time: 37.5s (training 15.1s, eval 22.4s, ok)

AUC improved by 0.0015 to 0.6908. This supports reducing the amplitude of calendar effects learned from one year.

## Experiment 24 — follow-up: test whether calendar shrinkage continues helping

Hypothesis: the gain from weight 1.0 to 0.5 suggests a stronger reduction may further improve year transfer. Test weight 0.25 in both fitting and prediction, with every other aspect fixed. This is one deliberate continuation of the observed trend, not a fine-grained weight search.

Result: **0.6896**, commit `813bd37`, **discard**. Run time: 37.3s (training 15.1s, eval 22.2s, ok)

AUC decreased by 0.0012. Retain half-strength calendar effects; reducing them further removes useful signal.

## Experiment 25 — exploration: one-hot carrier-airport interactions

Hypothesis: carrier-specific airport operations deserve explicit pair categories under the retained one-hot splitting regime. Add carrier-origin and carrier-destination categories with training-fitted vocabularies. Unlike experiment 4, these are lower-cardinality pairs and cannot pool arbitrary collections of noisy categories; unlike experiment 12, they contain no target estimates or hash-bucket noise. This revisits interaction information under the categorical strategy proven in experiment 10.

Result: **0.6908**, commit `7589ee3`, **discard**. Run time: 45.1s (training 15.7s, eval 29.4s, ok)

Printed AUC tied 0.6908, but evaluation increased from 22.4s to 29.4s and the code became more complex. Discarded under the tie rule. The distinction from earlier pooled route categories was tested without improvement.

## Experiment 26 — follow-up: separate month and holiday amplitudes

Hypothesis: monthly effects reflect year-specific conditions more than recurring holiday effects do. Fit a month-only shallow model, then a shallow holiday residual using the unshrunk month margin. Give month half weight and the holiday residual full weight when fitting/predicting the operational component. This preserves the successful reduced monthly signal while testing whether shared holiday effects were over-shrunk by experiment 23. Both components use the same depth-2/200-round regularization as the retained calendar model.

Result: **0.6897**, commit `0288118`, **discard**. Run time: 37.6s (training 15.1s, eval 22.5s, ok)

AUC decreased by 0.0011. Discarded; full-strength holiday residuals were not better than jointly shrunk calendar effects.

## Experiment 27 — exploration: constrained daytime delay trend

Hypothesis: a rising daytime trend can reduce noisy time/airport interactions. Replace raw HHMM with scheduled minutes clipped to 05:00–20:00, constrained to increasing, plus an unconstrained overnight phase. Keep minute-within-hour. The initial training-only hourly means motivate the daytime trend and explicitly show why a global 24-hour monotonic constraint would be wrong. Read [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html); all other features and the calendar component remain unchanged.

Result: **0.6902**, commit `88596b3`, **discard**. Run time: 44.0s (training 19.8s, eval 24.2s, ok)

AUC decreased by 0.0006. Discarded; conditional departures from the broad daytime trend appear useful. Row invariance and label independence passed.

## Focused research after the recent discards

Searched XGBoost loss-guided growth and leaf limits as a new structural direction. A fixed leaf budget can distribute depth unevenly rather than restricting every path equally. Before that, test whether within-round forest averaging is still necessary after calendar shrinkage.

## Experiment 28 — simplification: single tree per boosting round

Hypothesis: the improved calendar architecture may remove the marginal need for four parallel trees. Reduce num_parallel_tree from 4 to 1, keeping the column/row subsampling, depth and 600 rounds unchanged. An equal printed AUC would qualify as a faster, smaller kept model.

Result: **0.6904**, commit `d12cb11`, **discard**. Run time: 27.0s (training 5.2s, eval 21.7s, ok)

AUC fell by 0.0004. Discarded despite training dropping to 5.2s and a smaller artifact; parallel-tree averaging still provides useful accuracy.

## Experiment 29 — exploration: loss-guided trees with a leaf budget

Hypothesis: allocating a 32-leaf budget according to loss improvement can fit asymmetric airport/time interactions more efficiently than limiting every branch to depth 6. Use grow_policy=lossguide, max_depth=0, max_leaves=32 in the operational model, keeping four trees per round and the calendar model fixed. Reviewed the [tree-method documentation](https://xgboost.readthedocs.io/en/stable/treemethod.html) and the parameter reference after the recent near-best discards.

Result: **0.6910**, commit `432fa74`, **keep**. Run time: 40.7s (training 18.1s, eval 22.6s, ok)

AUC improved by 0.0002 to 0.6910. Retain asymmetric tree growth under a leaf budget.

## Experiment 30 — ablation: remove weakest geographic component

Hypothesis: the smallest of the three retained distance-embedding eigencomponents may encode route-network distortion more than useful geography. Remove OriginGeo0, DestGeo0 and Direction0 while preserving the other components exactly. This isolates the weakest component without refitting or rotating the remaining axes; a tie would favor fewer features.

Result: **0.6911**, commit `47c19da`, **keep**. Run time: 38.6s (training 18.2s, eval 20.4s, ok)

AUC improved by 0.0001 to 0.6911 and evaluation decreased to 20.4s. Retain the two strongest geographic components.

## Synthesis after 30 experiments

Best: **0.6911**, commit `47c19da`, +0.0168 over baseline. The biggest recent advance was separating a shallow calendar model from operational residual boosting, then shrinking its log-odds to half strength. Quarter strength lost signal, and separate full-strength holiday effects were worse. Explicit carrier-airport categories tied while slower. A daytime monotonic constraint and single-tree simplification lost accuracy. Loss-guided growth under 32 leaves and removal of the weakest geographic component gave small further gains.

Current theory: the dominant time/carrier signal needs flexible operational interactions, while calendar amplitudes and weak geographic detail need restraint. The remaining budget will test distinct feature-selection and numeric-resolution choices, and simplify only if AUC is preserved.

Research at this pause: the [XGBoost API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) documents feature_weights for column-sampling probabilities (verified constructor support in installed 3.4.1), while [tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) describe how histogram resolution controls split candidates. These suggest prioritizing strong original variables and testing coarser numeric bins.

## Experiment 31 — exploration: prioritize stable features during column sampling

Hypothesis: random column sampling should rarely omit departure time and carrier, the dominant training-gain signals. Use sampling weights 3 for CRSDepTime, 2 for UniqueCarrier, and 1 for all other operational features, keeping colsample_bynode=0.85 and all model/feature choices fixed. These are fixed feature-selection priorities, not row frequencies or target encodings.

Result: **0.6911**, commit `d4f8c6d`, **discard**. Run time: 38.2s (training 17.6s, eval 20.6s, ok)

AUC tied 0.6911. Total runtime differed by only 0.4s, not a meaningful established speed benefit, and configuration became more complex. Discarded in favor of the simpler retained model.

## Experiment 32 — exploration: coarser numeric histogram bins

Hypothesis: max_bin=64 (instead of 256) pools nearby numeric time/geographic values and reduces sensitivity to fine distinctions, while one-hot airport/carrier identities remain available. Test the change only in the operational model. The histogram split-candidate mechanism is documented in the tree-method/parameter references read at the 30-experiment pause.

Result: **0.6907**, commit `e5ba63d`, **discard**. Run time: 37.5s (training 17.2s, eval 20.4s, ok)

AUC decreased by 0.0004. Discarded; the retained model needs finer numeric distinctions.

## Experiment 33 — ablation: additive weekday effect

Hypothesis: weekday-specific airport/time interactions may encode 2005 weather noise. Keep weekday in the operational model but isolate it with disjoint interaction groups, as month isolation helped earlier. Other operational variables can still interact freely. This tests a remaining calendar interaction under the improved model architecture.

Result: **0.6889**, commit `973e152`, **discard**. Run time: 37.4s (training 16.9s, eval 20.5s, ok)

AUC decreased by 0.0022. Discarded: weekday interactions transfer better than month interactions in this dataset.

## Experiment 34 — simplification: additive calendar stumps

Hypothesis: depth-1 calendar trees enforce a shared holiday-offset curve plus separate month/holiday-type effects, avoiding calendar interactions that may be year-specific. Change only calendar depth from 2 to 1. Read [Lou, Caruana and Gehrke, Intelligible Models for Classification and Regression](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/06/kdd2012.pdf), which studies additive feature-shape models; improved transfer here remains an experimental hypothesis.

Result: **0.6902**, commit `8468c61`, **discard**. Run time: 38.2s (training 17.9s, eval 20.4s, ok)

The shallower calendar model lost 0.0009 AUC. Depth-two interactions among month and holiday position remain useful; restore the best model.

### Experiment 35 — follow-up: stronger operational leaf regularization

Hypothesis: raising operational L2 leaf regularization from 10 to 50 may smooth noisy residual updates while retaining useful splits. The previously reviewed [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes this from gamma and minimum child support, which failed earlier. Only operational reg_lambda changes.

Result: **0.6913**, commit `d1fbdd2`, **keep**. Run time: 38.2s (training 17.6s, eval 20.7s, ok)

AUC improved by 0.0002, so keep the stronger operational leaf regularization. The clock is below two minutes: this is the final experiment.

## Final summary

Completed 35 experiments plus the unchanged baseline on branch `oct6`. All 36 harness runs succeeded within the per-phase time limits. Best Eval AUC: **0.6913**, commit `d1fbdd2`; baseline **0.6743**, absolute improvement **0.0170**. The branch is at this best kept commit. The saved artifact is `artifacts/d1fbdd2428145627717d57075fb8468d929a0725.pkl`. Its final harness timing was 17.6s training and 20.7s evaluation.

What worked: regularized boosting; removing raw day-of-month; fixed one-hot categorical splits; departure-minute information; airport geometry learned only from training route distances and normalized route direction; holiday-relative features; a shallow calendar model supplying half-strength base margins to the operational model; loss-guided trees with 32 leaves; removing the weakest geometry dimension; and the final increase in operational L2 regularization to 50. Faster preparation also reduced row-wise evaluation cost.

What did not help: pooled route categories, route-relative departure time, target-encoding lookups, ranking loss, stronger split/support restrictions, additional boosting rounds, a second random-seed model, carrier-airport pairs, splitting month and holiday models, monotonic daytime constraints, coarse histogram bins, isolated weekday effects, and calendar stumps. Equal-score changes were discarded when they added cost without a meaningful simplification.

Working interpretation: broad spatial and operational interactions transfer across years, while calendar effects benefit from restricted capacity and shrinkage. These are observations from this evaluation-driven search, not a claim of independent validation.

Next directions for a future run: test calendar smoothness and regularization with this final operational model, then try physically motivated route-time interactions using only training-derived geometry. An independent assessment remains necessary to determine how much of the observed improvement generalizes beyond the reused evaluation set.

Final verification: every result matches the harness timing ledger; tracked worktree is clean; only `train.py` differs from the initial commit; the final `save_and_evaluate(model, prepare)` call is preserved. Loaded the best saved artifact and checked single-row versus batch preparation, label-independent features, and finite predictions including an unseen airport. No extra AUC metric was computed.
