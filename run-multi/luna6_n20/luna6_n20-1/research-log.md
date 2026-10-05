# Research log — oct5

## Baseline — b15ec66

Ran the starter unchanged: XGBoost with native categorical features, 100 trees, depth 6, learning rate 0.1. Eval AUC was 0.6743. This is the comparison point for all later experiments.

## Research before experiment 1

- The [XGBoost parameter tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) frames depth and regularization as bias–variance controls, recommends sampling (`subsample`/`colsample_bytree`) to improve robustness, and notes that preprocessing can matter as much as parameter tuning.
- The [XGBoost categorical data guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes category partitioning, which can group values with similar learned outputs instead of treating every category as an independent one-hot feature.
- The flight-delay study [Deciphering Air Travel Disruptions](https://arxiv.org/abs/2408.02802) discusses departure time, airline, airport, and spatial/route context as relevant factors. Its dataset and task differ from this experiment, so I use it only to motivate the interaction, not as a performance claim.

## Experiment 1 — add origin–destination route category

**Type:** exploration.

**Hypothesis:** the starter gives XGBoost separate `Origin` and `Dest` categories, so a depth-limited tree may need multiple splits to represent route-specific delay patterns. An explicit `Origin-Dest` categorical feature can expose that interaction directly. The 4,290 distinct routes in `train.csv` are represented as categories fitted once from train; each row’s route is then looked up through its own origin and destination. All starter model parameters stay fixed to isolate this feature change.

**Result — da890cb:** Eval AUC 0.6667 (`discard`; baseline 0.6743). The route category did not transfer as hoped from 2005 to 2006. Evaluation took 43.7s versus 30.1s at baseline, consistent with the cost of carrying a 4,290-level category through row-wise preparation. Reverted to the baseline commit.

## Experiment 2 — slower boosting schedule

**Type:** exploration (hyperparameter direction).

**Hypothesis:** the baseline’s 100 trees at learning rate 0.1 may stop before the model has learned weaker schedule and airport effects. Following the XGBoost tuning guide’s advice to lower `eta` while increasing boosting rounds, try 500 trees at 0.03 with depth 6 and all features unchanged. This tests a finer, longer boosting schedule without changing feature representation.

**Result — 4054e62:** Eval AUC 0.6745 (`keep`), a +0.0002 gain over baseline. Training took 3.1s and evaluation 31.3s. The slower schedule is now the best kept commit.

## Experiment 3 — row subsampling

**Type:** follow-up to the slower boosting schedule.

**Hypothesis:** the 500-tree schedule is a small improvement, and randomly fitting each tree on 80% of rows may reduce sensitivity to 2005-specific noise and improve transfer to 2006. Keep the best schedule, depth, and all features fixed.

**Result — 101c7f2:** Eval AUC 0.6766 (`keep`), +0.0021 over the previous best. Row subsampling reduced training time slightly to 3.1s and evaluation remained 30.4s. This is the new best.

## Experiment 4 — stronger row subsampling

**Type:** follow-up to experiment 3.

**Hypothesis:** `subsample=0.8` helped noticeably. Test a lower fraction (0.6) to see whether stronger randomness further reduces year-specific overfit; only this parameter changes from the best kept model.

**Result — 50e07f8:** Eval AUC 0.6764 (`discard`), 0.0002 below the kept 0.8 sampling fraction. Stronger row subsampling did not help. Reverted to 101c7f2.

## Experiment 5 — feature subsampling

**Type:** exploration of an orthogonal regularization direction.

**Hypothesis:** row subsampling helped while stronger row sampling was slightly worse. Following the XGBoost guide’s separate recommendation to use `colsample_bytree`, sample 80% of input columns per tree while retaining the best row-subsampling and boosting settings. This tests whether reducing dependence on the same few predictors improves transfer.

**Result — d17910a:** Eval AUC 0.6795 (`keep`), +0.0029 over the previous best. Column subsampling improved transfer; training was 3.0s and evaluation 30.5s. This is the new best.

## Experiment 6 — stronger column subsampling

**Type:** follow-up to experiment 5.

**Hypothesis:** feature subsampling improved AUC at 0.8. Test 0.6 to provide more tree-to-tree diversity; all other best settings remain fixed. With eight input columns, this still leaves several predictors available to each tree.

**Result — c979db5:** Eval AUC 0.6819 (`keep`), +0.0024 over the previous best. At this point, smaller `colsample_bytree` has helped at both 0.8 and 0.6. Training was 2.9s and evaluation 30.7s; this is the new best.

## Experiment 7 — stronger column subsampling again

**Type:** follow-up to experiments 5–6.

**Hypothesis:** `colsample_bytree=0.6` improved over 0.8, so test 0.4 to check whether still more tree diversity helps. Only the column fraction changes from the best kept model.

**Result — e572989:** Eval AUC 0.6819 (equal; `keep` for speed). Training stayed at 2.9s; total run time fell from 34.7s to 34.2s and artifact size from 9.5 MB to 8.4 MB. This is the best kept score with a smaller model artifact.

## Experiment 8 — shallower trees

**Type:** follow-up regularization experiment.

**Hypothesis:** row and column subsampling improved year-to-year transfer. Lowering `max_depth` from 6 to 4 may further reduce brittle interactions while keeping the best boosting schedule and sampling fractions. The XGBoost guide identifies depth as a direct model-complexity control.

**Result — 7d9d6e8:** Eval AUC 0.6806 (`discard`), down 0.0013. Shallower depth reduced model size but hurt AUC. Reverted to e572989; the intermediate depth 5 remains untested.

## Experiment 9 — intermediate tree depth

**Type:** follow-up to experiment 8.

**Hypothesis:** depth 4 was worse than 6 by 0.0013, so test depth 5 to see if a smaller but still interaction-capable tree keeps most of the best score. Other settings remain at the kept configuration.

**Result — df3f9c7:** Eval AUC 0.6818 (`discard`), 0.0001 below the best. Depth 5 nearly matched depth 6; depth 4 was worse. Reverted to e572989.

## Experiment 10 — deeper trees

**Type:** follow-up to the depth sweep.

**Hypothesis:** depths 4 and 5 were slightly worse than depth 6, so test depth 7 to check whether the row and feature subsampling now provide enough regularization for deeper interactions. Only depth changes from the best kept model.

**Result — 2899779:** Eval AUC 0.6808 (`discard`), down 0.0011. Depth 7 did not improve transfer; reverted to e572989.

## Synthesis after 10 experiments

- The best result is 0.6819 at e572989, an absolute +0.0076 over the 0.6743 baseline. The 500-tree, 0.03 learning-rate schedule gave a small gain; row subsampling at 0.8 helped more; feature subsampling helped further, with 0.4 tying 0.6 at four decimals and running slightly faster.
- Stronger row sampling (0.6), depth 4, depth 5, and depth 7 did not beat the best. Depth 6 remains the best tested depth. The explicit 4,290-level route category lowered AUC and slowed row-wise evaluation, suggesting sparse route memorization did not transfer well from 2005 to 2006.
- Current theory: the baseline’s main limitation is over-reliance on a subset of input features and year-specific patterns; stochastic regularization helps more than adding a sparse route interaction. Next, research compact time-of-day representations and useful XGBoost regularization parameters. Keep each feature row-local and avoid target or row-count encodings that would leak or change meaning in one-row evaluation.

## Research before experiment 11

- The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes `min_child_weight` and `gamma` as complexity controls, and confirms row/column sampling acts per tree. These are additional tuning directions after the time feature experiment.
- A recent [U.S. flight-delay analysis](https://github.com/kandulanikhilvarma/flight-delay-analysis) uses `DEP_HOUR` alongside month, weekday, carrier, and distance as pre-flight features, and reports strong hour-to-hour variation in departure-delay rates. Its 2019–2023 dataset differs from this 2005/2006 split, so this motivates testing the feature but does not establish it will help here.
- A [Bureau of Transportation Statistics-based feature study](https://www.mdpi.com/2079-9292/13/24/4910) extracts the hour from HHMM scheduled departure time; a [TU Delft thesis on flight delay probabilities](https://repository.tudelft.nl/file/File_98b0da88-14e1-4e30-87a5-583e78a882f8) also uses hour-of-day and notes that tree splits can model temporal intervals without sine/cosine transforms. This supports a simple integer hour feature rather than a cyclic encoding.

## Experiment 11 — explicit departure hour

**Type:** exploration (row-local feature engineering).

**Hypothesis:** raw `CRSDepTime` is HHMM, while delay pressure may vary by scheduled hour. Adding `DepHour = CRSDepTime // 100` exposes whole-hour structure and lets trees combine hour with carrier/airport/calendar features at a lower interaction depth. Keep the raw time, existing inputs, and best model settings; no aggregate or label-derived feature is used.

**Result — 53a092d:** Eval AUC 0.6826 (`keep`), +0.0007 over the previous best. Hour-level time structure improved the ranking; row-wise evaluation rose from 30.2s to 32.5s. This is now the best commit.

## Experiment 12 — within-hour departure minute

**Type:** follow-up time-feature experiment.

**Hypothesis:** after the hour feature helped, scheduled minute (0–59) may encode schedule-bank patterns such as common :00/:30 departures, independently of time of day. Add only `CRSDepTime % 100`; retain raw HHMM and hour to let the model combine coarse and fine timing.

**Result — 529bbfb:** Eval AUC 0.6828 (`keep`), a +0.0002 gain from the minute-of-hour feature. Training remained 2.9s; evaluation rose to 34.0s. This is the current best.

## Experiment 13 — late-night period indicator

**Type:** follow-up time-feature experiment.

**Hypothesis:** an [airline-delay feature study](https://www.mdpi.com/2079-9292/13/24/4910) explicitly isolates night flights (21:00–04:59). A binary flag can group hours across midnight in one split, an interaction that numeric hour and raw HHMM require several splits to express. Add this indicator, retaining the existing time features.

**Result — 6414e05:** Eval AUC 0.6824 (`discard`), down 0.0004; evaluation also grew to 36.0s. The explicit wrap-around indicator did not help beyond raw HHMM, hour, and minute. Reverted to 529bbfb.

## Experiment 14 — larger minimum child weight

**Type:** exploration of direct tree regularization.

**Hypothesis:** the best model uses depth 6 but trains on only 80% of rows per tree. Raising `min_child_weight` from its default 1 to 5 should discourage splits supported by very small leaves and may improve 2005-to-2006 generalization. Keep the best features and sampling unchanged.

**Result — baa8d09:** Eval AUC 0.6823 (`discard`), down 0.0005. A minimum child weight of 5 was too conservative; reverted to 529bbfb. A smaller increase remains worth checking.

## Experiment 15 — mild minimum child weight

**Type:** follow-up to experiment 14.

**Hypothesis:** 5 reduced AUC; try 2 as a milder increase above the default of 1. This checks the nearby regularization range while keeping the best feature and sampling configuration fixed.

**Result — a62c268:** Eval AUC 0.6824 (`discard`), down 0.0004. A mild child-weight increase still reduced the score; reverted to 529bbfb.

The last three experiments (late-night flag, child weight 5, child weight 2) were consecutive declines under 0.001, so I paused for research before another experiment. The parameter-only tuning direction appears to have plateaued; the next candidate direction is leakage-safe train-fitted category target statistics, which may add airport/carrier/route priors without the high-cardinality sparsity of a route category.

### Target encoding research

- The [scikit-learn TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) defines target encoding as a shrunk category-conditioned target mean and recommends cross-fitting for training data; it distinguishes `fit_transform` from a direct `fit().transform()` to prevent leakage.
- The [CatBoost paper](https://proceedings.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf) explains why a naive target mean leaks each training row’s label and notes that leave-one-out encoding alone can still leak through a global prior. Therefore this experiment uses stratified five-fold cross-fitting and computes each fold’s prior from only that fold’s fitting rows.
- The [regularized target-encoding benchmark](https://arxiv.org/abs/2104.00629) found regularized target encodings effective across many high-cardinality datasets, while warning that weak regularization can overfit some high-cardinality cases. The encodings below shrink to a train-only prior and expose only rates, never group counts.

## Experiment 16 — cross-fitted carrier, airport, and route rates

**Type:** exploration (encoding strategy).

**Hypothesis:** the native origin/destination categories did not express all of their learned delay propensities efficiently, and a sparse route category hurt. Smoothed target-rate features can provide direct carrier, origin, destination, and route priors with fewer dimensions. To avoid label leakage, each training row receives a rate computed from a different fold (including that fold’s prior); evaluation rows use the smoothed lookup fitted on all of `train`. The lookup uses group counts only to shrink the target mean; no count is exposed as a model input. All features are per-row key lookups and remain stable when `prepare` receives one row.

**Result — 202c8f4:** Eval AUC 0.6824 (`discard`), down 0.0004; evaluation took 40.1s. The full set of four cross-fitted rates did not improve over explicit time features, and the additional per-row lookups slowed scoring. Reverted to 529bbfb. Test an ablation to determine whether the route rate is responsible before dropping the idea entirely.

## Experiment 17 — ablate route target rate

**Type:** ablation of experiment 16.

**Hypothesis:** the 4,290-level route prior may be too sparse and volatile across years even when smoothed. Keep only the cross-fitted carrier, origin, and destination rates, then compare against the full four-rate experiment and current best. This isolates the route-rate contribution.

**Result — 8e8a37b:** Eval AUC 0.6836 (`keep`), +0.0008 over the current best. Removing the route rate reversed the decline from experiment 16. Carrier/origin/destination priors help; route-level rates appear too noisy for this split. Evaluation took 36.9s, still comfortably below the harness limit. This is the new best.

## Experiment 18 — stronger target-rate smoothing

**Type:** follow-up to the successful rate-feature ablation.

**Hypothesis:** cross-fitted carrier/origin/destination rates helped at smoothing 50. Doubling the shrinkage weight to 100 may reduce noise in airport rates as schedules and delay patterns shift across years. The same value changes all three maps; route rate remains excluded.

**Result — 24b5ce2:** Eval AUC 0.6838 (`keep`), +0.0002 over 50 smoothing. Stronger shrinkage helped slightly; evaluation time stayed at 37.2s. This is the new best.

## Experiment 19 — stronger target-rate smoothing again

**Type:** follow-up to experiment 18.

**Hypothesis:** increasing smoothing from 50 to 100 helped. Test 200 to see whether further shrinkage stabilizes the train-fitted delay priors under 2005-to-2006 drift. No other setting changes.

**Result — a71b6fc:** Eval AUC 0.6837 (`discard`), 0.0001 below the best. Doubling smoothing from 100 to 200 was slightly too strong; reverted to 24b5ce2. Test one intermediate value to check whether the local optimum is near 150.

## Experiment 20 — intermediate target-rate smoothing

**Type:** follow-up to the smoothing sweep.

**Hypothesis:** smoothing 100 beat 50, while 200 was marginally worse. Test 150 as an intermediate value to refine shrinkage without changing the three cross-fitted rate features or model.

**Result — 9ee3514:** Eval AUC 0.6835 (`discard`), 0.0003 below the best. Smoothing 150 was also too strong; reverted to 24b5ce2.

## Synthesis after 20 experiments

- Best Eval AUC is 0.6838 at 24b5ce2, +0.0095 over baseline. The strongest reliable changes are 500 trees at 0.03, row subsampling 0.8, column subsampling 0.4, explicit departure hour/minute, and cross-fitted smoothed carrier/origin/destination delay rates.
- The 4,290-level route category cost about 0.0076 AUC; a smoothed route target rate also hurt when added to the other rates. Removing the route rate improved the four-rate experiment by 0.0012. This points to temporal instability or sparsity in route-specific signal.
- Rate smoothing 100 was best among 50, 100, 150, and 200; more shrinkage beyond 100 reduced AUC slightly. Rate features should stay cross-fitted: CatBoost’s analysis and scikit-learn’s guidance both show why direct in-sample means (and even leave-one-out with a full-data prior) can leak.
- Depths 4, 5, and 7, `min_child_weight` 2/5, and a late-night binary flag did not help. The raw time plus hour and minute features remain useful.
- Current theory: broad carrier and airport propensities transfer across years, while route-level effects are too sparse. A useful next direction is conditional delay propensity by airport/carrier and scheduled hour, which can express local peak-hour patterns without creating a route ID.

### Airport-by-hour research for experiment 21

- Zhang et al., [A multi-step airport delay prediction model based on spatial-temporal correlation and auxiliary features](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071), defines average airport delay over one-hour intervals and identifies time-of-day as an auxiliary factor (especially around busy periods).
- Wang et al., [Flight delay forecasting and analysis of direct and indirect factors](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12183), explains that airports are busy at different times and that congestion relates to departure delay. This experiment approximates stable time-specific propensities from training labels because the provided features do not include scheduled-flight counts or real-time congestion.

## Experiment 21 — time-conditioned carrier and airport rates

**Type:** exploration (temporal interaction encoding).

**Hypothesis:** broad carrier/origin/destination rates improved AUC, and airport delay patterns vary by hour. Add cross-fitted smoothed rates for carrier-hour, origin-hour, and destination-hour pairs. The 100-point smoothing setting is inherited from the current best; each training row is encoded from other folds only, and evaluation uses full-train lookup maps. Counts are used only to shrink target means and are never model features.

**Result — f7e137b:** Eval AUC 0.6829 (`discard`), down 0.0009; evaluation increased to 44.9s. The three time-conditioned rates did not transfer well as a package. Reverted to 24b5ce2. Since carrier-hour groups are much denser than airport-hour groups, test a focused ablation with carrier-hour only.

## Experiment 22 — carrier-hour rate only

**Type:** ablation of experiment 21.

**Hypothesis:** carrier-hour groups have substantially more training examples than airport-hour pairs. Keep the carrier-hour rate while removing origin-hour and destination-hour rates, to test whether the denser interaction captures stable operating patterns without the sparse airport-hour noise.

**Result — a5c14b3:** Eval AUC 0.6827 (`discard`), down 0.0011. The carrier-hour rate alone did not recover the decline, so no time-conditioned rates are retained. Reverted to 24b5ce2.

## Experiment 23 — cyclical month features

**Type:** exploration (calendar encoding).

**Hypothesis:** the categorical `Month` feature can group arbitrary months, but a sine/cosine pair also makes neighboring months adjacent across December/January and can represent smooth seasonal trends with a small number of splits. Add month phase features while retaining categorical month. A flight-delay study on BTS data reports seasonal delay variation; a [time-series feature review](https://wires.onlinelibrary.wiley.com/doi/10.1002/widm.1475) describes sine/cosine encoding for periodic calendar variables. A [TU Delft flight-delay thesis](https://repository.tudelft.nl/file/File_98b0da88-14e1-4e30-87a5-583e78a882f8) notes that tree splits can already model time intervals, so this is an empirical test rather than an assumed improvement.

**Result — 3b4eebd:** Eval AUC 0.6832 (`discard`), down 0.0006. The cyclical month representation did not help alongside categorical month. Reverted to 24b5ce2.

## Experiment 24 — remove redundant raw departure time

**Type:** ablation/simplification of the successful hour/minute representation.

**Hypothesis:** `DepHour` and `DepMinute` together reconstruct `CRSDepTime` exactly. Removing raw HHMM from the model may reduce redundant competition under `colsample_bytree=0.4`, while retaining the same schedule information in decomposed form. This also tests whether raw HHMM’s ordinal splits add anything beyond hour/minute.

**Result — 2f4d967:** Eval AUC 0.6824 (`discard`), down 0.0014. Raw `CRSDepTime` contributes useful ordinal splits beyond hour and minute; reverted to 24b5ce2.

## Experiment 25 — slightly wider feature sampling

**Type:** follow-up regularization experiment after adding time and target-rate features.

**Hypothesis:** `colsample_bytree=0.4` worked best before engineered rates increased the feature set. At 0.5, each tree should see about one more feature on average, which may make better use of the new rate and schedule predictors while retaining randomness. Only this parameter changes.

**Result — a79f10e:** Eval AUC 0.6820 (`discard`), down 0.0018. The expanded feature set did not benefit from increasing the column fraction to 0.5. Reverted to 24b5ce2.

## Experiment 26 — finer, longer boosting schedule

**Type:** follow-up to the successful 500-tree schedule.

**Hypothesis:** the 500-tree schedule helped over baseline, and the stronger feature/rate representation may benefit from more smaller updates. Try 800 trees at learning rate 0.02 while keeping depth, subsampling, and features fixed. This tests the XGBoost guide’s lower-eta/more-rounds direction on the current best.

**Result — c7bb7fb:** Eval AUC 0.6840 (`keep`), +0.0002 over the previous best. Training took 4.7s; evaluation 37.5s. The finer schedule is now the best.

## Experiment 27 — still finer boosting schedule

**Type:** follow-up to experiment 26.

**Hypothesis:** 800 trees at 0.02 narrowly improved AUC. Test 1,000 at 0.015, keeping the cumulative learning-rate scale similar while allowing more, smaller updates. Features and sampling remain fixed.

**Result — 6af53a5:** Eval AUC 0.6835 (`discard`), down 0.0005. More and smaller updates did not outperform 800/0.02; reverted to c7bb7fb.

## Experiment 28 — mild split-gain threshold

**Type:** exploration of tree regularization.

**Hypothesis:** `min_child_weight` increases were too conservative, but weak splits may still overfit the sampled year. Test `gamma=0.1`, which requires a small minimum loss reduction for each split, as described in the [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html). Keep the best boosting schedule and features fixed.

**Result — 5dc797b:** Eval AUC 0.6839 (`discard`), 0.0001 below the best. Mild split-gain regularization did not improve the model; reverted to c7bb7fb.

## Experiment 29 — slightly stronger L2 leaf regularization

**Type:** exploration of weight regularization.

**Hypothesis:** `gamma=0.1` slightly reduced AUC, but shrinking leaf scores rather than restricting splits may still improve transfer. Try `reg_lambda=2` versus the default 1, with all other best settings fixed. The XGBoost parameter reference describes higher `reg_lambda` as more conservative.

**Result — 65ce984:** Eval AUC 0.6839 (`discard`), 0.0001 below the best. Doubling L2 regularization did not help; reverted to c7bb7fb.

## Experiment 30 — mild L1 leaf regularization

**Type:** exploration of a different weight-regularization penalty.

**Hypothesis:** L2 shrinkage at 2 was marginally worse. Test a small `reg_alpha=0.1` to shrink weak leaf scores sparsely while preserving the best 800/0.02 schedule and feature settings. The XGBoost parameter reference describes alpha as L1 regularization.

**Result — c8be3c4:** Eval AUC 0.6841 (`keep`), +0.0001 over the prior best. Training was 4.7s and evaluation 37.4s. Mild L1 regularization is now the best configuration.

## Synthesis after 30 experiments

- Best AUC is 0.6841 at c8be3c4, +0.0098 over the 0.6743 baseline. The kept configuration uses 800 trees at 0.02, depth 6, row sampling 0.8, column sampling 0.4, raw HHMM plus derived hour/minute, and cross-fitted/smoothed carrier/origin/destination target rates (smoothing 100), with `reg_alpha=0.1`.
- The most reliable gains came from row/column sampling, hour/minute features, and cross-fitted broad delay priors. Lower-rate boosting gave a small additional gain. Route categories/rates, time-conditioned target rates, cyclical month features, and extra depth/leaf/split regularization did not help.
- Current theory: broad carrier and airport reliability effects are stable across years; route and hour-specific effects are too sparse or volatile. More feature diversity and regularized target means help most. The best score is now near a plateau, so the final minutes should explore feature-selection/regularization ideas with clear hypotheses and revert quickly if lower.

### Feature-selection research for experiment 31

The [XGBoost Python API reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html) documents `feature_weights` as per-column selection probabilities when `colsample` is active, and exposes it in `XGBClassifier.fit`.

## Experiment 31 — prioritize cross-fitted rates in feature sampling

**Type:** follow-up to the successful target-rate features and column subsampling.

**Hypothesis:** broad carrier/origin/destination rates improved Eval AUC, but with 13 columns and `colsample_bytree=0.4`, some trees omit them. Give those three columns weight 2 versus 1 for all others so they are selected more often while preserving sampling diversity. No feature values or model parameters change.

**Result — 50026ad:** Eval AUC 0.6839 (`discard`), down 0.0002. Doubling rate-feature selection weights was too strong; the run emitted a deprecation warning because weights were passed to `fit`. Reverted to c8be3c4. Test a milder 1.5 weight through the model constructor.

## Experiment 32 — mild feature-selection weighting

**Type:** follow-up to experiment 31.

**Hypothesis:** a weight of 2 was too aggressive. Test 1.5 for carrier/origin/destination rates to raise their selection probability less while retaining column-sampling diversity. The weight vector is constructed in `X_train` column order and passed through the XGBoost constructor, as the API recommends.

**Result — 9103bc3:** Eval AUC 0.6839 (`discard`), down 0.0002. A 1.5 selection weight was also too strong; reverted to c8be3c4. Explicit feature-selection weighting does not improve on uniform column sampling.

## Experiment 33 — finer histogram bins

**Type:** exploration of numeric split resolution.

**Hypothesis:** the best model includes numeric `CRSDepTime`, `DepHour`, `DepMinute`, and distance. Raising `max_bin` from its default 256 to 512 may give histogram-based tree growth more precise threshold candidates for these features. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) says larger `max_bin` improves split optimality at extra computation cost. Keep all other settings fixed.

**Result — de6a11d:** Eval AUC 0.6844 (`keep`), +0.0003 over the prior best. Training was 4.8s; evaluation 37.3s. The finer histogram bins improved numeric split resolution; this is the current best.

## Experiment 34 — finer histogram bins again

**Type:** follow-up to experiment 33.

**Hypothesis:** `max_bin=512` helped. Test 1024 to see whether still more precise numeric thresholds improve the mix of scheduled time, hour, minute, and distance features. Training remains well under its timeout at 512; monitor the larger setting.

**Result — 3acfc18:** Eval AUC 0.6839 (`discard`), down 0.0005. More bins beyond 512 slightly hurt; reverted to de6a11d. Test 768 as one intermediate value.

## Experiment 35 — intermediate histogram bins

**Type:** follow-up to experiments 33–34.

**Hypothesis:** 512 beat the default, while 1024 was slightly worse. Test 768 as an intermediate split-resolution setting with all other best settings fixed.

**Result — b7100e2:** Eval AUC 0.6842 (`discard`), down 0.0002 from the best. An intermediate `max_bin=768` did not match 512; reverted to de6a11d.

## Final summary

The best kept run is **de6a11d**, Eval AUC **0.6844**, an improvement of **0.0101** over the 0.6743 baseline. Its strongest gains came from row and column subsampling, departure hour/minute features, cross-fitted smoothed carrier/origin/destination delay rates, mild L1 regularization, and `max_bin=512`. Route-level and hour-conditioned target rates, calendar cycles, feature-sampling weights, extra tree depth, and `max_bin` values of 768 or 1024 did not improve the score. The final 768-bin run scored 0.6842 and was discarded. The branch is restored to the best kept commit.

A useful next experiment would test a small `min_child_weight` increase around the best `max_bin=512` configuration, since values 2 and 5 were previously tried before the later feature/model improvements; any gain should be checked against the current best with a single-variable change.
