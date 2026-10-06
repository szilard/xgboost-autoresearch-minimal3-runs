# Research log: oct6

## Setup — 2026-10-06

- Created fresh branch `oct6` directly from the current HEAD, `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py`.
- Verified that `data/train.csv` and `data/eval.csv` exist. Inspected only the training data: 200,000 rows, all 9 expected columns, 100,000 Y / 100,000 N labels, and no missing values.
- Verified installed dependencies import: pandas 3.0.6, NumPy 2.5.3, XGBoost 3.4.1, scikit-learn 1.9.1, and cloudpickle 3.1.2. Python is 3.14.4; 8 logical CPUs are available.
- Initialized `output/results.tsv` with its required four-column header. Run outputs remain ignored by git.
- Left the baseline code unchanged. No training or evaluation has run, and the experiment clock has not started.

## Start protocol

Await the user's confirmation, then run `python3 harness.py start` as the first action. Establish the baseline with the unchanged `train.py` through `python3 harness.py run`, redirecting output to `output/run.log`. Record the baseline before making any changes.

The run has a one-hour wall-clock budget, a 60-second training limit, and a 300-second evaluation limit per run. Research external sources before the first non-baseline experiment. Follow the harness-reported four-decimal Eval AUC keep rule and record each experiment here and in `output/results.tsv`.

## Initial research

- [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): manage complexity with depth/child weight and use shrinkage or sampling to control noise. Given the 2005-to-2006 shift, stronger regularization is a deliberate first model direction.
- [XGBoost categorical support](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): categorical partitions can group levels, and inference must preserve training category mappings. Numeric array inputs can also declare categorical feature types explicitly.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, child weight, categorical split thresholds, and sampling provide distinct capacity controls.
- [scikit-learn TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html): target means require shrinkage and cross-fitting to avoid leakage. Any future target-derived feature must preserve row-wise preparation and avoid using the scored row's label.
- [BTS departure statistics](https://www.transtats.bts.gov/ontime/Departures.aspx) confirms scheduled departure time is a departure scheduling field; only inputs available in advance are relevant here.

Training-only inspection: calendar values use `c-` prefixes; 20 carriers and 283 airports in each endpoint field; departure times are HHMM integers. Baseline fitting is fast, while row preparation dominates evaluation. No new model experiment has started yet.

## Baseline — b15ec66

Eval AUC **0.6743**; training phase 1.5s, evaluation 31.5s. Kept unchanged baseline.

## Experiment 1 — simplify row preparation

Classification: ablation/simplification. Hypothesis: constructing the frame once and letting `pd.Categorical` handle unknown categories directly preserves the feature values while reducing per-row overhead. Keep only if AUC is unchanged and evaluation becomes faster, or AUC improves. Source: the XGBoost categorical consistency documentation above; category levels remain fitted only on train.

Experiment 1 result — **73d6659**, Eval AUC **0.6743**, keep: exact equality and evaluation reduced from 31.5s to 17.5s. Verified prepared features against baseline on training samples, single-row consistency, and unknown-category behavior.

## Experiment 2 — regularized shallow boosting

Classification: exploration. Hypothesis: depth-4 trees with larger leaves and L2 regularization will transfer better across years than the baseline depth-6 category partitions. Use 400 trees at learning rate 0.05 to retain fitting capacity, min_child_weight 40, reg_lambda 10, subsample 0.85, and max_cat_threshold 32. This tests one coherent bias/variance direction, motivated by the XGBoost parameter-tuning and parameter references above.

Experiment 2 result — **ac0b398**, Eval AUC **0.6800**, keep (+0.0057); training 2.2s, evaluation 17.6s. Supports reducing categorical overfitting across years.

## Experiment 3 — remove day-of-month

Classification: ablation/simplification of experiment 2. Hypothesis: exact day-of-month encodes 2005-specific weather/date effects that need not recur in 2006. Removing it should improve transfer while retaining month and weekday seasonality. Training-only marginal delay rates vary irregularly by day (e.g. days 16, 22, 28 are high), which motivates this ablation but is not itself evidence of future performance. [Time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) distinguishes seasonal cycles; we test whether this particular calendar detail is useful here.

Experiment 3 result — **d85b272**, Eval AUC **0.6812**, keep (+0.0012); training 2.1s, evaluation 15.6s. Exact day-of-month appears harmful to temporal transfer. Model gain importance from experiment 2: departure time 0.582, carrier 0.090, weekday 0.078, month 0.078, origin 0.056, destination 0.046, day-of-month 0.040, distance 0.031. Importance is a training diagnostic, not an additional selection metric.

## Experiment 4 — one-hot categorical tree splits

Classification: exploration. Hypothesis: one-category-versus-rest splits impose a more stable airport/carrier effect than gradient-sorted category partitions. Set max_cat_to_onehot=512 (above all current cardinalities), leaving all other model settings unchanged. The categorical tutorial and parameter reference above describe this distinct splitting strategy. It may need more boosting rounds, but this first test isolates the strategy.

Experiment 4 result — **736e573**, Eval AUC **0.6771**, discard (-0.0041); training 2.0s, evaluation 15.2s. One-hot splits at this capacity underperform partitioning, so restore experiment 3.

## Experiment 5 — remove month seasonality

Classification: ablation/simplification of experiment 3. Hypothesis: month-level weather differences between 2005 and 2006 may outweigh repeatable seasonal effects, similar to the observed day-of-month issue. Remove Month alone while retaining weekday, time, carrier, airports, and distance. This directly tests whether the apparent temporal instability extends to the larger calendar scale.

Experiment 5 result — **d3d9412**, Eval AUC **0.6837**, keep (+0.0025); training 2.0s, evaluation 13.3s. Month's training signal does not reliably transfer in its current representation. Retain weekday, schedule, carrier, airport, distance.

## Experiment 6 — explicit category codes

Classification: ablation/simplification. Hypothesis: fixed category codes plus explicit XGBoost feature_types preserve categorical splits and predictions while avoiding per-row pandas Categorical construction. Fit code dictionaries on train only, map unseen levels to NaN, and return a numeric DataFrame for the harness. The XGBoost categorical tutorial documents explicit feature types for encoded inputs. No statistical feature changes are intended.

Experiment 6 result — **7f1baf3**, Eval AUC **0.6837**, keep: evaluation fell from 13.3s to 3.9s; training 2.1s. Verified exact prediction equivalence on 100 training rows and single-row/batch preparation consistency. Booster feature types remain explicitly categorical for all four code columns.

## Experiment 7 — more boosting without unstable date features

Classification: follow-up to experiments 3 and 5. Hypothesis: removing two high-variance calendar predictors permits more iterations to learn stable airport/carrier/time interactions. Increase boosting rounds from 400 to 1000, keeping depth, learning rate, and all regularization fixed. This tests remaining underfitting versus cross-year overfitting after the successful ablations.

Experiment 7 result — **224fc17**, Eval AUC **0.6817**, discard (-0.0020); training 3.9s, evaluation 4.0s. More iterations worsen transfer even without the unstable date features.

## Experiment 8 — fewer boosting rounds

Classification: ablation/simplification of experiment 6, motivated by experiment 7. Hypothesis: temporal generalization peaks earlier than 400 rounds. Halve the round count to 200 with all remaining settings fixed. This brackets the capacity question in the opposite direction rather than making small arbitrary changes.

Experiment 8 result — **4399805**, Eval AUC **0.6837**, keep: equal printed AUC with half as many trees; training 1.5s, evaluation 3.8s. This favors compact models over longer boosting.

## Experiment 9 — network interaction categories

Classification: exploration. Hypothesis: route and carrier-airport operating patterns contain stable joint signal that depth-4 trees cannot efficiently learn from individual categories. Add Origin×Dest, UniqueCarrier×Origin, and UniqueCarrier×Dest as categorical features, with dictionaries fitted on train and unknown pairs mapped to NaN. No counts or target encodings. Motivation: [CatBoost paper, feature combinations](https://proceedings.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf) describes pairwise categorical combinations as a way to expose joint dependencies. We adapt this feature idea to XGBoost's native category handling.

Experiment 9 result — **bdc8047**, Eval AUC **0.6789**, discard (-0.0048); training 2.5s, evaluation 4.7s. Raw high-cardinality network categories introduce more harmful variance than useful transferable signal at these settings.

## Experiment 10 — coarse seasonal categories

Classification: follow-up to the successful month ablation. Hypothesis: grouping calendar months into winter/spring/summer/fall will retain broad repeatable seasonality while removing month-specific 2005 effects. Add only the four-valued Season feature, computed per row as (month mod 12)//3. This is distinct from restoring exact Month. Motivation: the scikit-learn time-related feature engineering reference above discusses representations at multiple seasonal scales.

Experiment 10 result — **ce97526**, Eval AUC **0.6820**, discard (-0.0017); training 1.5s, evaluation 4.0s. Even coarse seasonality underperforms the date-free model.

## Synthesis after 10 experiments

Best: **0.6837**, commit **4399805**, versus baseline 0.6743. Stronger regularization and deleting month/day-of-month improved transfer. One-hot splits, longer boosting, raw network combinations, and coarse seasons hurt. Preparation simplifications cut evaluation from 31.5s to about 4s; 200 trees retain the best printed score. Working theory: stable time-of-day and marginal operating effects matter, while high-order or year-specific effects overfit. Next: constrain interactions, test train-fitted schedule-relative features, and consider independent-fold target encodings to stabilize network information.

### Research refresh

- [XGBoost feature interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html): restrict which features may share tree paths to reduce noise and encode an additive structure. We can permit time-by-airport effects without unrestricted route interactions.
- [XGBoost 3.2 parameters](https://xgboost.readthedocs.io/en/release_3.2.0/parameter.html): gradient-based sampling is available on CPU in the installed newer release, so it is a possible later alternative to uniform subsampling.
- The CatBoost paper above motivates categorical combinations but also explains why target statistics need protection against leakage. Raw combination categories failed here; a regularized encoding is a meaningfully different future test.

## Experiment 11 — restrict interactions to stable time effects

Classification: exploration based on the 10-experiment synthesis. Hypothesis: an additive model of time×origin, time×destination, time×carrier, time×distance, and a separate weekday effect will suppress brittle high-order interactions while preserving plausible scheduling relationships. Set explicit interaction constraints; keep 200 depth-4 trees and all other settings fixed.

Experiment 11 result — **3a69f13**, Eval AUC **0.6796**, discard (-0.0041); training 1.4s, evaluation 3.8s. The proposed interaction restrictions discard useful relationships.

## Experiment 12 — departure time relative to typical schedules

Classification: exploration. Hypothesis: a flight's position relative to its route, origin, and carrier-origin typical schedule captures stable operating patterns without a high-cardinality category split. Fit median departure minutes on train for those three groupings; add the three per-row offsets as numeric features. No target values or counts are used. [RobustScaler documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.RobustScaler.html) describes fitting median centers on training data and applying them later; here that principle is adapted to fixed group lookups, as also illustrated in program.md.

Experiment 12 result — **0327a73**, Eval AUC **0.6841**, keep (+0.0004); training 1.7s, evaluation 5.1s. Verified row-invariant features and unchanged features after flipping the provided labels. Fixed schedule-relative measurements are a promising alternative to raw network category combinations.

## Experiment 13 — departure minute and circular time

Classification: exploration. Hypothesis: minute-of-hour exposes scheduled departure banks, while daily sine/cosine components allow trees to capture relationships spanning midnight with few splits. Add DepMinute, TimeSin, TimeCos; retain HHMM and all schedule offsets. Based on the scikit-learn time-related feature engineering source, adapted to the observed time-of-day dominance and pre-departure inputs only.

Experiment 13 result — **9091038**, Eval AUC **0.6841**, discard: equal score without simplification or speed improvement; training 1.8s, evaluation 5.4s.

## Experiment 14 — simplify schedule offsets to origin only

Classification: ablation/simplification of experiment 12. Hypothesis: the origin-relative offset carries most of the useful scheduling signal, while route and carrier-origin offsets add unnecessary detail. Their training gain shares were 0.010 and 0.019 versus 0.047 for origin. Remove the two finer-grained offsets and keep everything else fixed.

Experiment 14 result — **4d9d5d9**, Eval AUC **0.6837**, discard (-0.0004); training 1.5s, evaluation 4.4s. Simpler and faster but lower AUC, so restore all three offsets under the strict keep rule.

## Experiment 15 — larger minimum leaves

Classification: follow-up to the regularization gain in experiment 2. Hypothesis: larger minimum Hessian mass will suppress unstable small-group airport/carrier effects while retaining the useful numeric schedule offsets. Increase min_child_weight from 40 to 200 (roughly fivefold more effective support), holding depth, round count, sampling, and feature set fixed. The XGBoost parameter reference explains this as a direct complexity control.

Experiment 15 result — **3cb6daa**, Eval AUC **0.6840**, discard (-0.0001); training 1.7s, evaluation 5.2s. The larger-leaf constraint does not improve the best score.

### Plateau research after experiments 13–15

Three consecutive discards within 0.001 of the best trigger a research pause. Read [Random Forests in XGBoost](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html): num_parallel_tree can combine row/column randomization with multiple boosting rounds. This suggests averaging several randomized trees at each step rather than further increasing leaf restrictions. No additional evaluation metric is introduced.

## Experiment 16 — boosted random forests

Classification: exploration prompted by the plateau research. Hypothesis: four randomized trees per boosting step reduce variance in airport/category split choices. Set num_parallel_tree=4 and colsample_bynode=0.8; retain 200 rounds, existing subsample=0.85, and the best features/regularization. This changes the ensemble construction, not just the number of sequential boosting steps.

Experiment 16 result — **765ea8a**, Eval AUC **0.6841**, discard: equal score with fourfold tree count; training 5.5s, evaluation 5.3s.

## Experiment 17 — independent-sample target lookups

Classification: exploration. Hypothesis: smoothed airport, carrier, route, and carrier-airport delay rates expose stable rankings while avoiding the variance of native high-cardinality combination splits. Partition training rows into two fixed random halves. For each half, fit lookup tables only on that half and fit an XGBoost model on the other half; average the two models for inference. There is no fold scoring or cross-validation metric. Every row's prepared features use fixed lookups only, never the row label, index, or the batch contents. Both halves contribute to the final ensemble. Smooth each mean toward 0.5 with weight 50; counts are used only as denominators during fitting and are never features. Scale min_child_weight from 40 to 20 because each model sees half the data. Motivation: TargetEncoder documentation and the CatBoost paper's analysis of separate-sample target statistics, read earlier.

Experiment 17 result — **8a9fbff**, Eval AUC **0.6836**, discard (-0.0005); training 2.3s, evaluation 7.1s. Serialized ensemble loads successfully; rate features pass row-invariance and label-independence checks. This leakage-free encoding design is viable but does not improve selection AUC.

## Experiment 18 — balance labels within training months

Classification: exploration. Hypothesis: balancing Y/N separately within each training month reduces confounding from unusual 2005 weather while preserving month coverage. Train with weights n_month/(2*n_month_label), normalized to mean one; Month remains absent from prepared features. The [scikit-learn balanced sample-weight reference](https://scikit-learn.org/stable/modules/generated/sklearn.utils.class_weight.compute_sample_weight.html) documents inverse-class-frequency weighting; applying it within months is our temporal-robustness hypothesis. Counts affect training weights only and never become model features. This uses all train rows and does not introduce another metric.

Experiment 18 result — **35fa976**, Eval AUC **0.6842**, keep (+0.0001); training 1.7s, evaluation 5.1s. Very small improvement; treat the interpretation cautiously, while following the prescribed printed-AUC keep rule.

## Experiment 19 — conservative categorical partitions

Classification: follow-up to the successful regularization direction. Hypothesis: reducing max_cat_threshold from 32 to 8 will limit noisy category partition candidates, a different control from minimum leaf size (which did not help). Leave numeric features, sample weights, and other model settings unchanged. This categorical-specific regularizer is described in the XGBoost parameter and tuning references.

Experiment 19 result — **1f7cae3**, Eval AUC **0.6804**, discard (-0.0038); training 1.7s, evaluation 5.1s. Limiting category partition candidates too strongly loses useful signal.

## Experiment 20 — continuous airport geometry from training distances

Classification: exploration. Hypothesis: continuous airport positions inferred from route mileages allow nearby airports to share broad geographic/time patterns, avoiding arbitrary categorical groups. Build an undirected graph whose edge lengths are median route distances in train, compute shortest-path distances, and obtain a three-dimensional classical MDS embedding. Add origin coordinates, destination coordinates, and their differences (nine numeric features). All coordinates are fixed train-fitted lookups; no outside airport data or target values are used. [scikit-learn Isomap documentation](https://scikit-learn.org/stable/modules/manifold.html#isomap) explains graph shortest paths followed by an eigendecomposition; adapting an observed route-distance graph is our hypothesis. Coordinates are approximate latent geometry, not claimed latitude/longitude.

Experiment 20 result — **221ff7e**, Eval AUC **0.6842**, discard: equal score with extra fitting/features; training 2.1s, evaluation 5.9s. The inferred geometry did not add selection value.

## Synthesis after 20 experiments

Best: **0.6842**, commit **35fa976**. The second block yielded modest gains from fixed schedule offsets (+0.0004) and monthly class balancing (+0.0001). More time transforms, broader leaves, boosted forests, independent-sample target encoding, stricter categorical partitions, interaction constraints, and latent airport geometry did not improve the kept result. No crashes or timeouts. Working theory: useful improvements come from removing temporal nuisance and expressing stable schedule context; additional categorical complexity is hard to justify. The gains in this block are small enough that holdout generalization remains uncertain.

### Research refresh

Read [XGBoost tree methods](https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html): histogram training uses a global quantile sketch based on user weights, while approximate training refreshes Hessian-weighted sketches. Histogram bin count changes numerical split resolution. This motivates testing coarser thresholds as a distinct regularization direction, with an alternative approximate tree method if necessary. The airport-geometry research just completed also provided a new representation, but its equal-score complexity is rejected.

## Experiment 21 — coarser numeric split resolution

Classification: exploration. Hypothesis: max_bin=64 (instead of default 256) reduces sensitivity to exact scheduled times, distances, and offsets, improving transfer across yearly schedule changes. Keep the successful monthly weighting and all other model/feature settings unchanged. This interpretation is an experiment-specific inference from the documented histogram mechanism.

Experiment 21 result — **13f1665**, Eval AUC **0.6841**, discard (-0.0001); training 1.8s, evaluation 5.4s. Coarser numeric quantization does not improve this model.

## Experiment 22 — deeper trees with stable features

Classification: exploration. Hypothesis: after removing calendar noise and balancing monthly labels, depth-6 trees may recover legitimate carrier/airport/time interactions suppressed by depth 4. This is not a repeat of the baseline: leaf weight is 40, L2 is 10, month/day-of-month are removed, and schedule offsets plus monthly weights are present. Change depth alone from 4 to 6; keep 200 rounds. Contrast with experiment 7, which increased sequential boosting without allowing deeper interactions.

Experiment 22 result — **9d4578b**, Eval AUC **0.6828**, discard (-0.0014); training 2.0s, evaluation 5.2s. Higher-order operating interactions still overfit despite temporal regularization.

## Experiment 23 — remove day-specific global delay shocks in training weights

Classification: follow-up to the small gain from monthly weighting. Hypothesis: unusual 2005 disruption days bias stable airport/carrier relationships. Reweight Y/N within each Month×DayofMonth to the overall training Y/N rate for that weekday. This removes daily global shocks while retaining typical weekday differences, unlike indiscriminately forcing every date to 50/50. Weights are fitted entirely on train and remain outside prepare; every training row still participates. This is an adaptation of inverse-class-frequency weighting, not an estimate of future labels.

Experiment 23 result — **5260816**, Eval AUC **0.6837**, discard (-0.0005); training 1.7s, evaluation 5.1s. Date-level balancing is too aggressive or removes useful variation; monthly balancing remains preferred.

## Experiment 24 — pairwise ranking objective

Classification: exploration. Hypothesis: directly learning positive-over-negative orderings may suit AUC better than pointwise logistic probability fitting. Use XGBRanker with rank:pairwise, one global training query, and four mean-sampled pairs per row. Disable query/score normalization so the very large query does not collapse gradient scale. The ranking interface uses group weights, so omit the classifier's row-level monthly weights for this test. Wrap ranking scores with a monotone sigmoid solely to satisfy predict_proba; the harness still supplies the only selection metric. [XGBoost learning to rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) documents the unscaled pairwise logistic objective and mean pair construction. Its applicability to this AUC task is our inference.

Experiment 24 result — **9a5f307**, Eval AUC **0.6810**, discard (-0.0032); training 15.8s, evaluation 5.1s. Pairwise ranking is feasible within the runtime limit but does not improve this task at the tested settings.

## Experiment 25 — blend schedule and geometry models

Classification: exploration combining a promising near-miss with the best model. Hypothesis: the best classifier and the geometry-augmented classifier (both 0.6842 individually) may make complementary ranking errors. Train both afresh on train with identical monthly weights and take a fixed equal mean of their probabilities. This differs from experiment 20's standalone geography model and experiment 16's randomized trees within a shared boosting trajectory. [scikit-learn soft voting](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier) describes probability averaging; no blend weights are fitted on eval and no prior artifacts are read by train.py.

Experiment 25 result — **30ae55b**, Eval AUC **0.6843**, keep (+0.0001); training 2.8s, evaluation 5.9s. Serialized ensemble and row-invariant preparation verified. Improvement is slight, consistent with partially complementary representations.

## Experiment 26 — average independent boosting trajectories

Classification: follow-up to the small blending improvement. Hypothesis: averaging fixed seeds 42, 137, and 2026 for each of the two feature representations will reduce training-subsample variance. Preserve equal overall representation weights and every model's settings. This is not seed selection: all six trained members contribute equally. Unlike experiment 16, each member has its own complete sequence of boosting residuals. Source: soft probability averaging and XGBoost sampling references already read.

Experiment 26 result — **df3244f**, Eval AUC **0.6845**, keep (+0.0002); training 6.0s, evaluation 6.1s. Averaging complete boosting trajectories improved the blend.

## Experiment 27 — remove geography after seed averaging

Classification: ablation/simplification of experiment 26. Hypothesis: independent-seed averaging may provide the variance reduction that geometry previously supplied, allowing the full embedding and three of six models to be removed. Retain the three schedule-only seeds with equal weights and identical monthly weighting/hyperparameters. Keep only if AUC matches with simpler/faster code or improves; otherwise restore all six members.

Experiment 27 result — **092ca0c**, Eval AUC **0.6845**, keep: equal score with three rather than six models and no geography fitting/features; training 3.2s, evaluation 5.2s. Removes 35 lines and supports seed averaging as the useful variance reduction.

## Experiment 28 — remove the remaining calendar predictor

Classification: ablation/simplification of experiment 27. Hypothesis: weekday may also reflect unstable training-year disruption patterns, despite its plausible repeatable demand cycle. Drop DayOfWeek only, preserving the monthly training weights and all schedule features. Unlike the earlier date ablations, this tests weekly effects in the stabilized seed ensemble. Retain it if the ablation lowers AUC.

Experiment 28 result — **99778d7**, Eval AUC **0.6791**, discard (-0.0054); training 3.1s, evaluation 5.0s. Weekly effects transfer materially better than month/day-of-month effects.

## Experiment 29 — regularize the direct departure-time effect

Classification: exploration. Hypothesis: constraining the direct CRSDepTime effect to increase reduces noisy time thresholds, consistent with delay propagation later in operating days. Keep schedule offsets unconstrained so the full model can still learn night/route-specific departures from the overall tendency. Set monotone_constraints={CRSDepTime: 1}; keep the three seeds and all other settings. [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) describes shape constraints as a way to encode a strong prior. This is a tested partial-effect prior, not a claim that every later flight is more likely to be delayed.

Experiment 29 result — **88ff34c**, Eval AUC **0.6841**, discard (-0.0004); training 3.2s, evaluation 5.3s. The partial monotonicity prior is not helpful at the tested settings.

## Experiment 30 — deterministic excluded-partition target lookups

Classification: exploration addressing experiment 17's loss of model-fitting data. Hypothesis: a full-data model can benefit from independent target lookups if the lookup partition is a deterministic function of the input row. Hash the eight original predictors (never label or index) with stable CRC32 into five partitions. For each partition, fit smoothed rate tables on the other four partitions. Inside prepare, compute that same row hash and select the fixed corresponding tables. Thus a training row and all input-identical duplicates are excluded from their own rate tables, all 200K rows can train each classifier, and preparation remains invariant to batch size/order/index. Smooth six marginal/network rates with prior weight 100. There is no cross-validation scoring or alternative selection metric; partitions only fit feature lookups. [TargetEncoder's internal cross-fitting example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) motivates excluding own labels. The deterministic input-hash routing adapts that principle to this harness's strict row-wise contract.

Experiment 30 result — **4f5bbe9**, Eval AUC **0.6840**, discard (-0.0005); training 4.3s, evaluation 7.8s. Verified that prepared features are unchanged by batching, input-label flips, or row-index changes. The safer full-data target-lookup design still does not beat native categories plus schedule offsets.

## Synthesis after 30 experiments

Best: **0.6845**, commit **092ca0c**. Probability averaging helped: geometry blending first added 0.0001, then averaging three complete boosting trajectories added 0.0002, after which geometry could be removed at equal AUC. This leaves a simpler three-seed schedule ensemble. Weekday is strongly useful (-0.0054 when removed), unlike month/day-of-month. Deeper trees, monotonic time, daily class balancing, pairwise ranking, coarse bins, and the second target-encoding strategy failed. Main remaining directions: alternative stochastic sampling, different tree-growth/shrinkage controls, and simpler stable context features. Many late gains are one or two printed AUC units; the unseen holdout remains the check on their transfer.

### Research refresh

Read [Minimal Variance Sampling in Stochastic Gradient Boosting](https://arxiv.org/abs/1910.13204), which derives nonuniform sampling to improve estimation of tree split scores. This motivates testing gradient-informed sampling rather than uniform sampling. The XGBoost parameter documentation already checked confirms CPU support in the installed release family; we are not claiming its implementation is identical to the paper. Also read the TargetEncoder cross-fitting demonstration before experiment 30, which motivated the tested leakage protection.

## Experiment 31 — gradient-based row sampling

Classification: exploration. Hypothesis: gradient-informed sampling with subsample=0.35 keeps informative rows while introducing more useful diversity across the three seeds. Set sampling_method=gradient_based, retain the successful weights and feature set, and leave other model controls unchanged. This tests a new sampling mechanism rather than searching arbitrary random seeds.

Experiment 31 result — **fa9afe7**, Eval AUC **0.6814**, discard (-0.0031); training 6.2s, evaluation 5.2s. Gradient-informed aggressive subsampling is supported but performs worse.

## Experiment 32 — smaller boosting updates at matched strength

Classification: follow-up to the stable compact ensemble. Hypothesis: reducing learning_rate from 0.05 to 0.025 while doubling rounds from 200 to 400 yields a smoother optimization path and less greedy categorical split evolution. Total learning-rate×round-count remains 10, unlike experiment 7's much longer boosting exposure. All features, weights, leaf constraints, and seeds remain fixed. Source: XGBoost tuning guidance on pairing smaller steps with more rounds.

Experiment 32 result — **974dee2**, Eval AUC **0.6846**, keep (+0.0001); training 5.3s, evaluation 5.3s. Smaller updates slightly improve the seed-averaged model at matched cumulative strength.

## Experiment 33 — deterministic full-row fitting

Classification: ablation/simplification. Hypothesis: using every row per boosting step may remove the sampling variance that required three independent seeds. Set subsample=1 and fit one classifier directly; remove the ensemble wrapper. Retain the 400 rounds at 0.025 and all features, monthly weights, and other regularizers. This tests eliminating the randomness rather than merely averaging more seeds.

Experiment 33 result — **480e1fe**, Eval AUC **0.6842**, discard (-0.0004); training 2.3s, evaluation 5.3s. The cheaper deterministic model does not match the sampled three-seed ensemble.

## Experiment 34 — time-conditioned independent delay rates

Classification: exploration of a different target-encoding signal. Hypothesis: origin, destination, and carrier have repeatable time-of-day delay profiles that marginal rates and route identities miss. Add only three rate features, each conditioned on a three-hour departure block. Use the deterministic input-hash excluded-partition scheme from experiment 30, but shrink each group rate toward its partition's corresponding time-block rate (prior strength 100), not the global 0.5. This differs materially from experiment 30's six marginal/network rates: it explicitly models the observed dominant daily cycle and uses a relevant conditional prior. All lookup fitting uses train only; no row counts are features. Sources: target-encoding leakage/smoothing references, time-related feature engineering, and BTS delay-propagation background already read.

Experiment 34 result — **60b4dc6**, Eval AUC **0.6831**, discard (-0.0015); training 6.2s, evaluation 7.3s. Row invariance verified. Even structured conditional target-rate lookups do not outperform native categorical handling here.

## Experiment 35 — allow broader airport category partitions

Classification: follow-up to experiment 19's informative negative result. Hypothesis: the sharp loss at max_cat_threshold=8 suggests useful airport effects need pooling many categories; the current limit of 32 may still be restrictive. Increase it to 128, leaving depth/leaf size, shrinkage, sampling, weights, and ensemble unchanged. This expands only the categorical partition candidate search, unlike adding deeper interactions or new high-cardinality feature crosses.

Experiment 35 result — **8acfb0c**, Eval AUC **0.6837**, discard (-0.0009); training 5.8s, evaluation 5.5s. The current categorical threshold 32 is preferable to both tested extremes.

## Experiment 36 — best-first trees with a fixed leaf budget

Classification: exploration. Hypothesis: lossguide growth can allocate splits to a few valuable airport/time contexts without deepening every branch. Use grow_policy=lossguide, max_depth=0, max_leaves=16; depth-4 trees also have at most 16 leaves, so this changes allocation rather than the leaf ceiling. All other model controls stay fixed. Re-read the [XGBoost grow_policy/max_leaves parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html): lossguide prioritizes the largest loss reduction instead of expanding the shallowest nodes.

Experiment 36 result — **f5b6a9e**, Eval AUC **0.6848**, keep (+0.0002); training 6.8s, evaluation 5.6s. Adaptive allocation of a fixed leaf budget improves over depthwise expansion.

## Experiment 37 — refreshed Hessian-weighted split candidates

Classification: exploration using the new best tree-growth policy. Hypothesis: tree_method=approx can find better numeric split candidates for logistic loss because it refreshes Hessian-weighted sketches during boosting, unlike hist's fixed initial sketch. Keep lossguide, 16 leaves, the ensemble, weights, features, and all remaining parameters fixed. Source: XGBoost tree-method documentation read at the 20-experiment synthesis, which notes potential benefits for objectives with nonconstant Hessians. The harness will enforce the training-time ceiling.

Experiment 37 result — **8a359df**, Eval AUC **0.6846**, discard (-0.0002); training 30.2s, evaluation 5.8s. Refreshed sketches are much slower and do not improve the fixed-histogram model.

## Experiment 38 — prune weak-loss splits

Classification: follow-up to the successful lossguide growth policy. Hypothesis: requiring gamma=5 training-loss reduction will let best-first trees retain valuable local interactions but stop weak branches before filling all 16 leaves. This differs from larger minimum leaf mass: even a well-supported branch must clear a gain threshold. Keep all other settings fixed. Source: XGBoost parameter documentation on gamma/min_split_loss.

Experiment 38 result — **026b1dd**, Eval AUC **0.6848**, discard. Training 6.8s, evaluation 5.5s. All three members' tree dumps are exactly identical to the previous best (6,400 leaves each); gamma=5 is inactive. Minor wall-time differences are not evidence of an implementation speedup. Training split-gain quantiles from the kept model: minimum 5.49, 10th percentile 11.78, 25th percentile 20.96, median 38.46.

## Experiment 39 — active split-gain pruning

Classification: follow-up to the diagnostic from experiment 38. Hypothesis: gamma=20 targets roughly the weakest quarter of existing split gains, unlike gamma=5 which changed no trees at all. This is a deliberately active pruning threshold grounded in the model structure, not a cosmetic near-duplicate. Retain all other settings and assess only the harness AUC for selection.

Experiment 39 result — **809b2c7**, Eval AUC **0.6842**, discard (-0.0006); training 5.1s, evaluation 5.3s. Active pruning reduces computation but loses AUC, so restore the unpruned best.

### Plateau research before experiment 40

Experiments 37–39 are three discards within 0.001 of best. Shift away from tree parameters and research an explicit seasonal mechanism: [OPM's holiday definitions](https://www.opm.gov/frequently-asked-questions/pay-and-leave-faq/pay-administration/what-are-federal-holidays/?os=v) confirm Thanksgiving is the fourth Thursday of November, Christmas is December 25, New Year is January 1, and Independence Day is July 4. Only calendar definitions are used; no external flight records or outcome statistics are accessed.

## Experiment 40 — narrow holiday-relative calendar features

Classification: exploration. Hypothesis: travel patterns around recurring holidays transfer more reliably than arbitrary month/day-of-month effects. Add numeric relative-day features in narrow windows around Thanksgiving (-5 to +5), Christmas through New Year (-7 to +10 from December 25), and July 4 (-3 to +3). Outside each window, use NaN. Thanksgiving's date is inferred from the row's day-of-month and weekday, so no year identifier or training/evaluation detection is needed. Broad month/day features remain excluded; all transformations are in prepare and use only the individual row.

Experiment 40 result — **aa2150c**, Eval AUC **0.6871**, keep (+0.0023); training 8.4s, evaluation 6.5s. Row invariance and Thanksgiving offsets for synthetic 2005/2006 calendar examples verified. Narrow calendar mechanisms transfer better than broad monthly categories.

## Synthesis after 40 experiments

Best: **0.6871**, commit **aa2150c**. Smaller boosting updates and best-first 16-leaf growth added modest gains; explicit holiday-relative features added a larger 0.0023. Gradient-based sampling, deterministic full-row fitting, approximate tree construction, conditional delay-rate tables, category-threshold extremes, and active gain pruning failed. Gamma=5 was a true no-op, verified by identical tree dumps, and was discarded despite tiny timing variation. The successful holiday result refines the earlier theory: calendar information is useful when tied to recurring events, while arbitrary dates or broad months are less stable.

### Research refresh

The OPM calendar-rule research before experiment 40 supplied a new domain-specific representation. Also read [scikit-learn's correlated-feature importance example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html): importance can be spread across correlated features, so gain shares only motivate ablations, not automatic deletion. We do not add permutation evaluation or another selection metric. Before holidays, RouteTimeOffset had the smallest gain share (0.015); a targeted future ablation is justified, but the new holiday result takes priority.

## Experiment 41 — Memorial Day and Labor Day windows

Classification: follow-up to experiment 40. Hypothesis: the same event-relative representation can capture repeatable long-weekend travel patterns around the last Monday of May and first Monday of September. Add two numeric offsets within ±4 days in their respective months, derived from day-of-month and weekday. OPM's already-read holiday definitions verify those rules. All existing holiday windows and model settings remain fixed.

Experiment 41 result — **d990aac**, Eval AUC **0.6876**, keep (+0.0005); training 8.4s, evaluation 6.7s. A second group of event-relative dates improves transfer, reinforcing the holiday representation rather than a single holiday coincidence.

## Experiment 42 — winter Monday holiday windows

Classification: follow-up to the two successful holiday experiments. Hypothesis: the recurring January/February long weekends have a shared travel pattern distinct from arbitrary winter month effects. Add one combined numeric offset within ±4 days of the third Monday of January or February (MLK Day and Washington's Birthday, per the OPM definitions). Sharing one feature reduces holiday-specific variance; no additional exact month predictor is introduced. Retain all earlier holiday features.

Experiment 42 result — **b0e924c**, Eval AUC **0.6880**, keep (+0.0004); training 8.3s, evaluation 6.7s. A third holiday-family improvement supports using repeatable event-relative timing.

## Experiment 43 — remove the weakest schedule-offset feature

Classification: ablation/simplification of the holiday model. Hypothesis: RouteTimeOffset contributes little beyond the origin and carrier-origin offsets once best-first trees and explicit holidays are present. It had the smallest pre-holiday gain share (0.015) and remained low after the initial holiday addition (0.016). Remove only RouteTimeOffset, unlike experiment 14 which removed two offsets together in an earlier model. The selection remains based solely on harness AUC, not on importance values.

Experiment 43 result — **828bde1**, Eval AUC **0.6881**, keep (+0.0001); training 8.0s, evaluation 6.3s. The route-specific offset is now unnecessary; retain origin and carrier-origin offsets only.

## Experiment 44 — remove monthly label weighting

Classification: ablation/simplification of the holiday ensemble. Hypothesis: monthly class balancing may no longer help after recurring holiday effects are explicitly represented; its earlier benefit was only 0.0001. Remove the weighting calculation and use equal row weights, retaining every feature and model setting. This tests a changed context rather than repeating the earlier unweighted model.

Experiment 44 result — **50e74b8**, Eval AUC **0.6900**, keep (+0.0019); training 7.7s, evaluation 6.6s. Monthly balancing is harmful once holiday effects are modeled explicitly. This successful simplification illustrates why previously useful choices need rechecking after major feature changes.

## Experiment 45 — complete holiday windows across month boundaries

Classification: follow-up/refinement of the holiday representation. Hypothesis: post-Memorial flights in early June and pre-Labor flights in late August should use the same relative-day feature as nearby dates inside May/September. Extend the existing ±4-day windows across those boundaries using the row's weekday and month length. No new window width or model parameter is introduced. This corrects an intentionally limited first representation and preserves the same calendar mechanism across years.

Experiment 45 result — **c93136d**, Eval AUC **0.6898**, discard (-0.0002); training 7.8s, evaluation 6.6s. Boundary calculations pass independent datetime checks for 2005 and 2006, but the broader feature support lowers AUC. Restore the explicitly month-limited representation under the keep rule.

## Experiment 46 — halve the tree leaf budget

Classification: ablation/simplification of the final holiday ensemble. Hypothesis: eight-leaf best-first trees can retain the broad recurring calendar and operating effects while reducing fine interaction variance. Set max_leaves from 16 to 8 only. The holiday feature set and removal of monthly weights materially changed the model since the earlier complexity tests. Equal AUC with fewer leaves and faster fitting would justify keeping this simplification.

Experiment 46 result — **e4832c1**, Eval AUC **0.6890**, discard (-0.0010); training 5.6s, evaluation 6.2s. Fewer leaves are cheaper but lose AUC. The clock reports less than two minutes remaining, so no further experiments are started.

## Final summary

- Best Eval AUC: **0.6900**, commit **50e74b8d2c9cac58aff904770a831325fdaaf338**, branch **oct6**.
- Baseline: **0.6743** at `b15ec66`; absolute improvement **0.0157 AUC**.
- Completed **46 non-baseline experiments plus the baseline**. Result decisions including baseline: {'keep': 19, 'discard': 28}. All 47 harness runs completed successfully; no crashes or timeouts.
- Final artifact: `artifacts/50e74b8d2c9cac58aff904770a831325fdaaf338.pkl` (9.2 MB). The branch has been restored to the best kept commit.

### Final model

Three XGBoost classifiers with fixed seeds 42, 137, and 2026, averaged equally. Each uses 400 rounds at learning rate 0.025, best-first growth with 16 leaves, minimum child weight 40, L2 regularization 10, row subsampling 0.85, and categorical threshold 32. Training uses all 200,000 rows with equal weights. Four native categorical inputs (weekday, carrier, origin, destination), scheduled departure time and distance, two train-fitted schedule offsets (origin and carrier-origin), and six event-relative holiday features yield 14 prepared columns. Category dictionaries and schedule medians are fitted only on train; prepare reads no files.

### What worked

Regularizing the starter and removing arbitrary month/day-of-month predictors improved cross-year transfer. Fixed numeric category codes preserved predictions while greatly reducing row-preparation overhead. Schedule-relative times, independent-seed averaging, smaller boosting steps, and best-first tree growth added incremental gains. Explicit holiday-relative features produced the largest later improvement. Rechecking old choices mattered: route offsets and monthly label balancing could both be removed after adding holiday features, with higher AUC and simpler code. Weekday remained useful.

### What did not work

Raw route/carrier-airport category crosses; both independent-sample target-rate designs and time-conditioned rate features; coarse seasons; one-hot splitting at all cardinalities; broader/deeper fitting without the right features; restrictive interaction or monotonic constraints; aggressive gradient-based sampling; daily class balancing; pairwise ranking; approximate tree construction; and active split-gain pruning did not beat the kept model. Geographic embeddings added no lasting benefit after seed averaging and were removed. Completing holiday windows across month boundaries was calendar-correct but reduced AUC, so the earlier explicitly month-limited windows were retained.

### Verification and next ideas

The saved best artifact passed batch-versus-single-row feature equality, label-independence, and unseen-category scoring checks. Calendar arithmetic was checked against independent datetime examples. Only train.py differs from the starting commit; harness and repository instructions are unchanged. Every results row matches a successful harness timing row, and the artifact exists for the best commit. Outputs remain uncommitted.

Next research directions: carefully specified additional recurring-event features; simpler holiday representations or fewer ensemble members at equal AUC; and targeted regularized airport/time interactions. Future work should distinguish the relatively large holiday gains from the one- or two-unit printed-AUC improvements that may be sensitive to the evaluation sample.

No more runs will be launched. The final action is to stop the experiment clock.
