# Research log: oct6

Baseline: b15ec66; Eval AUC 0.6743; training 1.5s including startup, evaluation 31.2s. Training has 200,000 balanced rows, 8 predictors, and no missing values. Evaluation is the provided 2006 split; all feature lookups use training data only.

## Initial research
- [XGBoost tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): balance complexity and variance; lower learning rate needs more boosting rounds.
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, child weight, L2 penalty, sampling and categorical split limits control complexity.
- [Categorical data](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): native partitioning groups levels by fitted leaf values; this can overfit sparse levels.
- [Time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): numerical/categorical time representations and interactions can complement trees.

## Experiment 1 — regularized, slower boosting
Type: exploration. Hypothesis: depth 4, minimum child weight 20, L2 10, row sampling 0.9, and category threshold 32 should reduce year-specific overfit. Use 500 rounds at learning rate 0.05 to retain fitting capacity. Feature preparation is the baseline.

Result: f0a8403, AUC 0.6813 (+0.0070), kept. Training 2.6s; evaluation 30.4s. Regularization is promising under the year shift.

## Experiment 2 — ordinal day of month
Type: follow-up. Hypothesis: ordered day-of-month splits reduce arbitrary day groupings that may reflect weather in 2005 rather than repeatable effects. Keep the month and weekday categorical, and retain experiment 1 hyperparameters.

Result: 56dd6de, AUC 0.6855 (+0.0042), kept. Training 2.5s; evaluation 28.3s. Less flexible date encoding helps transfer.

## Experiment 3 — remove day of month
Type: ablation/simplification. Hypothesis: the remaining day-of-month signal may still mostly encode nonrepeatable daily disruptions. Remove it, leaving month and weekday for calendar information.

Result: 453721c, AUC 0.6809 (-0.0046), discarded. Ordered day of month carries useful signal; restore 56dd6de.

## Experiment 4 — simplify row preparation
Type: ablation/simplification. Hypothesis: construct the feature frame once and use cached categorical dtypes without redundant membership filtering. Features must match the prior implementation exactly, including unseen categories. [Pandas Categorical docs](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) specify that values outside supplied categories become missing. Keep only with equal or better AUC and faster evaluation.

Result: a0e3c12, AUC 0.6855 (equal), kept for evaluation reduction from 28.3s to 9.6s. Feature-equivalence, unknown-category, and batch/single-row checks passed. Pandas warns about future handling of unknowns with explicit dtype; use explicit missing code -1 going forward.

## Experiment 5 — categorical interactions
Type: exploration. Hypothesis: explicit route, carrier-origin, and carrier-destination categories allow depth-4 trees to represent operational differences with fewer splits. Levels are fitted only on train; unseen combinations map to missing. Use explicit category-code lookup to preserve missing handling without pandas deprecation warnings. Source: XGBoost categorical documentation linked above.

Result: 5509bdc, AUC 0.6764 (-0.0091), discarded. High-cardinality interaction partitioning overfits; category-code preparation itself ran quickly (6.4s evaluation).

## Experiment 6 — one-hot categorical splits
Type: follow-up to regularization gains. Hypothesis: max_cat_to_onehot=1024 prevents flexible multi-category group splits, reducing overfit in the original airport/carrier/month/weekday variables. No crossed categories. Explicit category code lookup is retained as an equivalent implementation improvement for unknowns. Source: XGBoost categorical split documentation.

Result: b4b6084, AUC 0.6813 (-0.0042), discarded. One-hot may need more trees to express separate category effects; model shrank to 0.9 MB and evaluation took 5.0s.

## Experiment 7 — test one-hot underfitting
Type: exploration. Hypothesis: the 500-tree budget is insufficient when each categorical split isolates one level. Triple the rounds to 1500, with all settings and features from experiment 6 otherwise identical. This tests fitting capacity rather than another encoding tweak.

Result: f395d82, AUC 0.6834 (-0.0021), discarded. Extra one-hot capacity helps relative to experiment 6 but does not beat partitioning.

## Experiment 8 — airport geography from route distances
Type: exploration. Hypothesis: numerical airport coordinates allow nearby airports to share seasonal/geographic effects that categorical identities cannot express smoothly. Infer shortest-path distances from unique training routes, then apply classical MDS (3 positive eigenvectors); add origin, destination and displacement coordinates. Fit uses no labels and no row-count features. [Isomap/MDS documentation](https://scikit-learn.org/1.9/modules/manifold.html) motivates the distance embedding; this is an adaptation to known route mileage. Training airport graph has 284 nodes and one connected component.

Result: 5fce5ad, AUC 0.6855 (equal), discarded because geography adds complexity with no accuracy gain. Evaluation 6.0s is faster due to code-based categorical construction; isolate that improvement next without geographic features.

## Experiment 9 — isolate fast categorical codes
Type: ablation/simplification of experiment 4 preparation. Hypothesis: explicit fitted maps with missing code -1 preserve all model inputs while reducing row preparation overhead and avoiding unknown-category warnings. Restore the best feature/model configuration and only change category construction.

Result: fccc8f2, AUC 0.6855 (equal), kept for evaluation reduction to 5.0s and explicit unseen-category handling. Feature equivalence and row consistency verified.

## Experiment 10 — movable holiday features
Type: exploration. Hypothesis: days relative to Thanksgiving, Memorial Day, Labor Day, Presidents Day, Christmas and July 4 should transfer better than fixed dates alone. Derive weekday-based dates from each row's month/day/weekday; use values only within 10 days in the relevant month, otherwise missing. No year or external flight data is used. [BTS holiday methodology](https://transtats.bts.gov/holidaydelay.asp) explains shifting holiday travel windows.

Result: 704efa1, AUC 0.6841 (-0.0014), discarded. Movable holidays did not help under this model configuration.

## Synthesis after 10 experiments
Best: fccc8f2, AUC 0.6855, +0.0112 over baseline. Strongest evidence supports regularizing model complexity and replacing arbitrary day-of-month categories with an ordered value. Removing day of month completely loses signal. High-cardinality crossed categories overfit badly; one-hot needs more trees but still loses. Geographic and holiday features have not improved accuracy. Preparation simplification cut evaluation from 31s to 5s while preserving inputs. Current theory: the challenge is separating repeatable seasonal/operational effects from 2005-specific disruptions, more than adding unconstrained features.

Research refresh: [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) motivates restricting spurious feature combinations. [Target encoding cross fitting](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) motivates label-independent partition assignment to keep smoothed group-risk features from learning their own labels. Next directions: restrict calendar interactions, tune regularization with fixed features, and test properly excluded target lookups.

## Experiment 11 — constrain day-of-month interactions
Type: follow-up to ordinal calendar improvement. Hypothesis: allow day of month to interact with month, weekday and departure time, while keeping the other operational features jointly flexible. Prevent airport/carrier-specific day-of-month splits that may fit isolated 2005 disruptions. Use the two explicit feature groups documented by XGBoost.

Result: de7dfd5, AUC 0.6850 (-0.0005), discarded. The selected overlapping feature groups did not improve transfer.

## Experiment 12 — truncate boosting
Type: ablation/simplification. Hypothesis: 500 rounds may overfit the native categorical model even with shallower trees; halve to 250 rounds to directly test late-round harm. All other settings and features match the best model.

Result: 5ec6ed4, AUC 0.6852 (-0.0003), discarded. Halving rounds nearly ties but does not meet the keep rule.

## Experiment 13 — excluded-partition smoothed target lookups
Type: exploration. Hypothesis: low-variance risk summaries capture route/carrier-airport effects more robustly than native high-cardinality partitions. Fit six sets of smoothed target means (50 pseudo-observations at prior 0.5). Assign each row to one of five partitions via a deterministic hash of its predictors; its lookup table is fitted on the other four partitions. Apply identical hash/table logic during training and single-row evaluation, excluding the current training row and exact predictor duplicates from its own lookup. No validation score or alternate evaluation is computed; partitions are only for feature fitting. Group sample totals are used only internally for smoothing, never exposed as features. Source: scikit-learn target-encoding cross-fitting example linked above.

Result: 9a5ed96, AUC 0.6838 (-0.0017), discarded. Cross-fitted group risks did not help this native-categorical model. Row consistency, label independence, and exclusion of the training row's entire partition were verified. Training 4.0s; evaluation 11.6s.

## Experiment 14 — shallower interactions
Type: ablation/simplification of the successful regularized model. Hypothesis: depth 3 instead of 4 limits interaction complexity broadly while retaining 500 boosting rounds. Complex interaction features have repeatedly failed to transfer; test whether the original features also benefit from simpler trees.

Result: fe30e6c, AUC 0.6848 (-0.0007), discarded. Depth 4 retains useful interactions.

## Experiment 15 — boosted small forests
Type: exploration. Hypothesis: averaging four independently sampled trees per boosting step reduces variance in category partitioning without removing interactions. Keep 500 depth-4 boosting steps and learning rate 0.05, use num_parallel_tree=4, subsample=0.8 and colsample_bynode=0.8. [XGBoost random forest tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) documents boosting a forest at each round.

Result: ce33a49, AUC 0.6853 (-0.0002), discarded. Training increased to 11.4s with no accuracy gain. Read-only gain importance from best saved model puts CRSDepTime at 362, versus 52 or less for other predictors, suggesting schedule representation deserves direct attention.

## Experiment 16 — departure clock components
Type: exploration. Hypothesis: minute-of-hour captures scheduling banks; explicit hour and sine/cosine of actual minutes since midnight make coarse and cyclic time effects easier for shallow trees. Retain raw scheduled time and all original features. Source: scikit-learn time-related feature engineering example linked in initial research.

Result: 3dda7b8, AUC 0.6852 (-0.0003), discarded. Raw departure time is already effective.

Plateau research after experiments 14–16: three consecutive small losses (-0.0007, -0.0002, -0.0003). Read [Rethinking Distribution Shifts for Tabular Data](https://arxiv.org/abs/2307.05284) and [Examining and Combating Spurious Features](https://proceedings.mlr.press/v139/zhou21g.html). Robust methods are not uniformly better; assumptions about the shift must be tested. Candidates: stronger support per leaf and moderate training reweighting of date-specific shocks. Neither needs evaluation-row access.

## Experiment 17 — increase minimum leaf support
Type: follow-up to initial regularization gain. Hypothesis: minimum child weight 200 instead of 20 suppresses small, unstable subgroup partitions while retaining depth-4 interactions. Change this single regularization dimension by a factor of ten to test a distinct support regime; all features and other settings stay at best.

Result: d558752, AUC 0.6852 (-0.0003), discarded. Raising minimum leaf support alone is insufficient.

## Experiment 18 — attenuate date-specific prevalence shocks
Type: exploration. Hypothesis: daily weather shocks in 2005 should have less influence on the transferable schedule model. Compute training-only date delay rates and month-by-weekday rates; use square-root importance ratios to move daily class balance halfway toward the corresponding seasonal/weekday rate. Smooth each date toward 0.5 with 100 pseudo-observations, clip final weights to [0.5,2]. Weights are only used by model.fit, not as features or evaluation inputs. This is a heuristic inspired by distribution-shift/reweighting research above, not an implementation of group DRO.

Result: f747db0, AUC 0.6830 (-0.0025), discarded. The proposed attenuation of daily shocks removed useful structure or imposed the wrong shift assumption.

## Experiment 19 — ordinal month
Type: follow-up to successful ordered day-of-month encoding. Hypothesis: native month partitions may group unrelated months based on 2005-specific outcomes; numerical month enforces contiguous seasonal splits. Replace the categorical month representation with integer 1–12, leaving other features and parameters unchanged.

Result: 2c44c6d, AUC 0.6852 (-0.0003), discarded. Unlike day of month, categorical month remains slightly better.

## Experiment 20 — average complementary boosting models
Type: exploration. Hypothesis: the best single booster (0.6855) and the sampled boosted forest (0.6853) have sufficiently different errors to benefit from an equal probability average. Train both on all train rows with their previously tested settings; prepare once and average their probability outputs. This differs from experiment 15, which averages trees within each boosting stage rather than complete fitted predictors. Source: [scikit-learn ensemble guidance](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier).

Result: 3d84601, AUC 0.6857 (+0.0002), kept. Training 12.0s; evaluation 5.5s. Complete-model averaging helps slightly where forest-only does not.

## Synthesis after 20 experiments
Best: 3d84601, AUC 0.6857 (+0.0114 versus baseline). Experiments 11–19 mostly cluster near 0.685; removing depth, rounds, detailed leaf splits, or categorical month loses small amounts. Explicit risk lookups, date reweighting and richer temporal features also fail. The original predictors appear to carry the available transferable signal, with a narrow useful complexity range. The two-model probability average is the only accuracy gain in this block, supporting some benefit from reducing prediction variance rather than adding features.
Research refresh: reviewed [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html), [categorical encoding comparisons in gradient boosting](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_categorical.html), and [regularized target-encoding study](https://arxiv.org/abs/2104.00629). Next: test quantization and shrinkage, followed by a numerical-risk replacement model if needed. Retain the strict printed-AUC keep rule.

## Experiment 21 — coarser numerical splits
Type: follow-up to regularization and averaging gains. Hypothesis: 64 histogram bins instead of 256 reduces sensitivity to fine schedule/distance thresholds and stabilizes both ensemble members. Change only max_bin for both models; original calendar and categorical inputs stay the same. XGBoost tree-method documentation describes the binning/accuracy tradeoff.

Result: cc595a1, AUC 0.6855 (-0.0002), discarded. Coarse numerical splits did not improve the ensemble.

## Experiment 22 — smaller boosting steps
Type: follow-up to the successful ensemble. Hypothesis: smaller steps reduce greedy path sensitivity in native category partitioning. Use 1250 rounds at learning rate 0.02 for both members instead of 500 at 0.05, preserving the product rounds * learning rate = 25. This changes optimization granularity rather than simply stopping later. Source: XGBoost tuning guidance on shrinkage and additional rounds.

Result: 4c702d7, AUC 0.6857 (equal), discarded: 35.3s total versus 17.6s without any AUC gain.

## Experiment 23 — replace raw airport categories with smoothed risks
Type: exploration. Hypothesis: native airport partitioning may dominate and negate risk features when both are present (experiment 13). Remove raw Origin and Dest categories, retain carrier/calendar categories, and use the same six partition-excluded smoothed risk lookups. Use the best 500-round two-member architecture. This tests the encoding as a replacement rather than an additional correlated input. Sources: [categorical encoding comparison](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_categorical.html) and [regularized target encoding study](https://arxiv.org/abs/2104.00629).

Result: feb8760, AUC 0.6827 (-0.0030), discarded. Native airport categories retain useful conditional effects beyond their average risks.

## Experiment 24 — suppress weak leaf contributions
Type: follow-up to regularization and model averaging. Hypothesis: L1 penalty reg_alpha=10 can zero weak leaf updates while keeping useful depth-4 interactions; this differs from restricting depth or minimum leaf support. Add it to both ensemble members, with the original features and all other best settings. Source: XGBoost parameter reference, reg_alpha.

Result: 3e8b018, AUC 0.6870 (+0.0013), kept. L1 leaf regularization breaks the plateau; the artifact shrank from 14.9 to 12.2 MB. Training 12.8s; evaluation 5.8s.

## Experiment 25 — stronger L1 regime
Type: follow-up to experiment 24. Hypothesis: the gain from alpha=10 indicates weak leaf updates are an important overfitting source; raise alpha to 50 to test a substantially stronger sparsity regime, retaining depth and rounds. This brackets the useful penalty strength instead of tweaking unrelated parameters.

Result: 63b2e27, AUC 0.6840 (-0.0030), discarded. Alpha 50 is too strong. Read-only model structure check: first-member zero leaf fraction rises from 0 at alpha 0 to 10.5% at alpha 10, confirming actual sparsification.

## Experiment 26 — ablate the forest member after L1 regularization
Type: ablation/simplification. Hypothesis: once L1 suppresses weak updates, a single booster may match or improve the ensemble while sharply reducing runtime and artifact size. Keep the alpha-10 best settings, remove only the forest member and probability-average wrapper.

Result: 108eed1, AUC 0.6862 (-0.0008), discarded. Ensemble diversity still helps after L1, despite the single model's lower runtime.

## Experiment 27 — larger category split search with L1
Type: follow-up to successful L1 regularization. Hypothesis: alpha 10 controls weak updates enough to allow more expressive category partitions. Increase max_cat_threshold from 32 to 128 for both ensemble members, which principally affects airport categories; retain depth, rounds and penalties. This tests added categorical capacity under the newly effective penalty rather than increasing unconstrained feature complexity.

Result: 4dd5962, AUC 0.6871 (+0.0001), kept per printed-AUC rule. Broader category partitions are viable with L1 regularization.

## Experiment 28 — deeper interactions under L1
Type: follow-up to experiments 24 and 27. Hypothesis: alpha 10 can suppress weak leaves while depth 5 captures a few additional useful operational interactions. Increase depth from 4 to 5 for both members, retaining the successful categorical threshold 128. This revisits tree capacity under stronger penalties, distinct from the earlier unpenalized depth-3 ablation.

Result: c752a6c, AUC 0.6860 (-0.0011), discarded. L1 does not make the extra interaction depth transfer well.

## Experiment 29 — monotone daytime delay accumulation
Type: exploration. Hypothesis: the strong rising training delay rate from 05:00 to 20:00 can be regularized with a shape constraint. Replace raw time with minutes clipped to [300,1200], constrained increasing, plus unrestricted actual minutes only outside that interval (missing during daytime). This preserves nonmonotonic overnight behavior while removing daytime oscillations. Retain the best depth-4 L1 ensemble. Source: [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html).

Result: b8ad6e0, AUC 0.6866 (-0.0005), discarded. The prior is plausible globally but too restrictive conditionally on the other predictors.

## Experiment 30 — sampled pairwise ranking objective
Type: exploration. Hypothesis: directly contrasting positive and negative training examples may improve ranking under the AUC metric. Train one XGBRanker with rank:pairwise, one global training group, mean sampling with one pair per sample, and no additional gradient/score normalization. Use 300 rounds at learning rate 0.08 (effective budget 24) to keep the larger ranking-gradient workload inside the 60s cap. Preserve best features, depth4, alpha10 and category threshold128. A sigmoid converts ranking scores to the two-column predict_proba interface without changing ordering. Evaluation remains solely the harness AUC. Source: [XGBoost ranking tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html).

Result: 1c39700, AUC 0.6860 (-0.0011), discarded. Ranking objective ran within limits (13.1s training) but did not beat the probability ensemble.

## Synthesis after 30 experiments
Best: 4dd5962, AUC 0.6871 (+0.0128 over baseline). L1 regularization at alpha 10 is the substantial gain in this block; alpha 50 loses strongly. With L1, broader category partitions add a small gain, but depth 5 overfits and removing the ensemble loses 0.0008. Smaller learning steps only tie at twice the runtime. Risk encodings, monotone daytime constraints and direct pairwise ranking do not beat the current model. The evidence now favors preserving native airport interactions while suppressing weak fitted contributions and averaging diverse models.
Research refresh: [LightGBM leaf-wise growth guidance](https://lightgbm.readthedocs.io/en/v4.5.0/Parameters-Tuning.html) and XGBoost's grow_policy/max_leaves parameters motivate a fixed-leaf asymmetric-tree test; [DART paper](https://arxiv.org/abs/1505.01866) suggests dropout as another way to limit excessive reliance on prior trees. These are algorithm ideas; the implementation remains XGBoost and uses installed packages only.

## Experiment 31 — fixed-leaf asymmetric trees
Type: exploration. Hypothesis: allocating the same approximate 16-leaf budget by loss reduction can capture useful local interactions without doubling all branches as depth5 did. Set grow_policy=lossguide, max_depth=0 and max_leaves=16 for both ensemble members. Keep the best L1 penalty and category split threshold.

Result: cba13f9, AUC 0.6872 (+0.0001), kept per printed-AUC rule. Fixed-leaf asymmetric trees help slightly.

## Experiment 32 — tree dropout
Type: exploration. Hypothesis: occasional dropout of earlier trees prevents later trees from specializing on a narrow residual subset. Use one 300-round classifier at learning rate 0.1, rate_drop=0.05 and skip_drop=0.8 (dropout in roughly one fifth of rounds), with tree normalization. Preserve the successful 16-leaf lossguide growth and L1/category settings. A single member and bounded rounds leave room for the more costly dropout predictions under the training cap. Sources: [DART original paper](https://arxiv.org/abs/1505.01866) and [XGBoost DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html).

Result: c2b240a, AUC 0.6867 (-0.0005), discarded. Training 53.6s approaches the cap and does not improve accuracy.

## Experiment 33 — departure time relative to usual schedules
Type: exploration. Hypothesis: time relative to typical origin, route and carrier-origin schedules captures operational context with a simple numeric split. Fit medians of actual departure minutes on train (no labels); expose row departure minutes minus the fitted group median. Unseen groups map to missing. This follows the train-fitted group-median construction illustrated in program.md and earlier time-feature research, now applied to interactions rather than clock shape alone. Use the best lossguide ensemble.

Result: 5568b0c, AUC 0.6879 (+0.0007), kept. Label-free schedule context is useful with the regularized model. Training 15.9s; evaluation 6.9s. Batch/single-row equality and unseen-group missing handling passed.

## Experiment 34 — ablate finer schedule lookups
Type: ablation/simplification. Hypothesis: origin-relative departure is the transferable part of experiment 33, while finer route and carrier-origin medians may add noise. Training-model total-gain shares: origin-relative 1.8%/5.7% in the two members, carrier-origin 0.6%/1.4%, route 0.4%/0.5%. Retain only the origin lookup and test the simpler feature set through the unchanged harness. Importance is only a diagnostic, not an alternate metric.

Result: 03b1ca8, AUC 0.6874 (-0.0005), discarded. Lower-gain route/carrier-origin schedule features still contribute useful complementary information.

## Experiment 35 — prune low-gain splits
Type: follow-up to L1 and schedule-context gains. Hypothesis: L1 controls leaf contributions, while gamma=3 separately suppresses branches with insufficient split improvement. Add the gain floor to both members of the best three-schedule-feature ensemble; retain all other settings. Source: XGBoost gamma/min_split_loss parameter reference.

Result: 2d267a3, AUC 0.6881 (+0.0002), kept. Gain-based split pruning complements L1. Training 14.9s; evaluation 6.9s.

## Experiment 36 — ablate the plain booster after schedule features
Type: ablation/simplification. Hypothesis: the sampled forest uses the schedule offsets more extensively, and may now match or exceed the average on its own. This removes the opposite member from experiment 26 and uses the improved schedule/gamma/lossguide setup. Train only the forest configuration (subsample0.8, colsample_bynode0.8, four trees per round), removing the wrapper and first booster.

Result: e8e4e36, AUC 0.6881 (equal), kept for simpler code, smaller artifact (10.5 versus 12.7 MB), and faster training (13.0 versus 14.9s).

## Experiment 37 — normalize origin schedule offset
Type: follow-up to schedule-feature gains. Hypothesis: a 2-hour offset means something different at an airport with a narrow schedule than at an all-day hub. Add origin-relative minutes divided by the origin's training interquartile range (floor 60 minutes); all scaling statistics are fitted once on train, never on the frame passed to prepare. Retain raw offsets. Source: [RobustScaler documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.RobustScaler.html) describes median/IQR-based scaling.

Result: cc4ba53, AUC 0.6881 (equal), discarded for added feature/lookup complexity and slightly longer runtime.

## Experiment 38 — balance leaf shrinkage with split pruning
Type: follow-up to gamma and L1 gains. Hypothesis: gamma=3 now removes weak branches, so reducing alpha from 10 to 5 may recover useful remaining leaf contributions without restoring those branches. This tests the interaction of two regularizers in the new schedule-aware forest; earlier alpha50 explored the opposite, much stronger regime before gamma.

Result: 65ad711, AUC 0.6872 (-0.0009), discarded. Alpha10 remains useful despite split pruning.

## Experiment 39 — halve trees per boosting round
Type: ablation/simplification. Hypothesis: two sampled trees per round may provide enough averaging after schedule features and regularization, matching AUC with substantially less training and storage. Keep 500 rounds and all settings, reduce num_parallel_tree from 4 to 2. This changes within-stage averaging, not the separate whole-model averaging tested earlier.

Result: fe648d5, AUC 0.6880 (-0.0001), discarded despite faster training. The strict keep rule requires retaining 0.6881. Best saved artifact e8e4e36 passes batch/single-row equality (including an unknown origin), label independence, finite normalized two-column probabilities, and artifact reload without retraining.

## Experiment 40 — destination-relative schedule context
Type: follow-up to experiment 33. Hypothesis: destination-level typical departure schedules complement origin and route offsets, representing service patterns for the receiving airport. Add one label-free training-fitted median lookup for Dest; keep the best four-tree boosted forest and all penalties. This is a broad airport summary rather than a new sparse category interaction.

Result: 4c91b06, AUC 0.6879 (-0.0002), discarded. Destination-level offset does not improve the chosen schedule features.

## Synthesis after 40 experiments
Best: e8e4e36, AUC 0.6881 (+0.0138 over baseline). Fixed-leaf loss-guided growth helped slightly. The most useful new feature family was departure time relative to training-fitted origin, route and carrier-origin medians. All three are needed in the tested model: dropping the finer lookups lost 0.0005. Gamma split pruning added a small gain. The sampled boosted forest alone now matches the two-member model, so the simpler single estimator is retained. Schedule IQR scaling and destination offsets did not improve AUC; two parallel trees lost 0.0001 and were rejected despite lower cost. Dropout was too slow for its accuracy gain, and stronger/weaker L1 penalties underperformed the selected alpha10.
Research refresh: [Minimal Variance Sampling in Stochastic Gradient Boosting](https://arxiv.org/abs/1910.13204) motivates investigating nonuniform sampling as a future alternative to the uniform row sampling used here. This was researched but not run because the clock reached the final two-minute window.

## Final summary
- Run branch: oct6. Baseline b15ec66, Eval AUC 0.6743.
- Best retained commit: e8e4e36c93383f410428690d558817251b9c54a3. Eval AUC 0.6881, absolute gain 0.0138.
- Completed 40 non-baseline experiments plus the unchanged baseline. All evaluations used the supplied harness and its printed four-decimal AUC.
- Selected model: XGBClassifier boosting 4 sampled trees per round for 500 rounds; lossguide, at most 16 leaves per tree, learning rate 0.05, min_child_weight20, L2=10, L1=10, gamma3, subsample0.8, colsample_bynode0.8, category threshold128, seed42.
- Selected features: original time/distance and carrier/airport/month/weekday categories, ordered numeric day of month, plus departure-minute offsets from origin/route/carrier-origin training medians. All lookups are fitted only on train and are applied identically to individual rows.
- Best run timing: 13.0s training including startup/preparation, 6.8s evaluation, 19.7s total. Artifact size about 10.5 MB.
- What worked: early regularization, ordered day of month, efficient categorical-code preparation, L1 leaf shrinkage, loss-guided growth, schedule-relative features, and split pruning. Forest averaging helped; the separate plain booster became unnecessary after the later improvements.
- What did not: native crossed categories, explicit target-risk lookups, extra clock/holiday features, inferred geography, date reweighting, monotone daytime constraints, and direct ranking objective. Very strong L1, extra depth, fewer forest trees and weaker late L1 lost AUC.
- Validation: best saved artifact passes row consistency including unseen origins, label independence of features, and finite normalized predict_proba output. No holdout or human-only tools/data were inspected. Harness and data files were not edited; no dependencies were installed.
- Next ideas: gradient-based sampling with the installed XGBoost version; separate ablations of route versus carrier-origin schedule medians; investigate schedule summaries conditional on month while retaining row-safe train-only lookups. Any future model-selection run should have its own fresh clock/logs.
- Stopped launching experiments at 58m10s elapsed, with less than two minutes remaining, as required by program.md. Results and research logs remain uncommitted in output/.

Final integrity check: all 41 runs match results.tsv in order; every commit has its saved artifact; all harness statuses are ok; HEAD is e8e4e36 and the tracked worktree is clean. Only train.py differs from the baseline tracked files.
