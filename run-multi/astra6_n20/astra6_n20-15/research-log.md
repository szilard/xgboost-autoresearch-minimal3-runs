# Research log

## Setup — 2026-10-07

- Run tag and branch: `oct7`, created directly from the starting HEAD.

- Starting commit: `b15ec66f306812020bf48c0fc4fc83e50cb24ce1`. The first run will use the unchanged baseline `train.py`.
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist. Only `train.csv` was inspected.
- Training data: 200,000 rows, 9 columns; target labels: {'Y': 100000, 'N': 100000}.
- Required Python packages import successfully; both in-scope Python files pass syntax checks.
- `output/results.tsv` contains only the required tab-separated header.
- Experiment clock has not started. No training or evaluation has run during setup.

## Run protocol

- Start the one-hour clock only after the user confirms the completed setup.
- Establish the unchanged baseline with `python3 harness.py run`.
- Research external sources before the first non-baseline experiment and at the required intervals.
- Keep all model changes in `train.py`; commit them before each run.
- Record the harness Eval AUC and keep/discard decisions in `output/results.tsv`.
- Training limit: 60 seconds. Evaluation limit: 300 seconds. Stop new experiments with less than two minutes remaining.

## Baseline — b15ec66

Eval AUC **0.6743**; training 1.7 s, evaluation 30.7 s. Kept unchanged baseline.

## Experiment 1 — exploration: shallower regularized boosting

Hypothesis: 500 depth-4 trees at learning rate 0.08, minimum child weight 20, L2 penalty 10, and row subsampling 0.85 can capture broad interactions while reducing year-specific noise compared with the 100 depth-6 baseline trees.

Research: [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) describes complexity controls, shrinkage, and subsampling; [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines the controls. [Categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains grouped category splits. [Berkeley flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) motivates future time-of-day and calendar features; only the search excerpt was accessible. These are candidate mechanisms, not evidence of gains on our data.

Result: **0.6769**, commit `9165728`, keep (+0.0026); training 2.7 s, eval 30.8 s.

## Experiment 2 — simplification: categorical preparation

Hypothesis: precomputed categorical dtypes and constructing the frame once remove redundant per-row work without changing features or AUC. [Pandas Categorical documentation](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) confirms that values outside supplied categories become missing automatically. Check equivalence on training rows plus a synthetic unknown category before the harness run.

Result: **0.6769**, commit `3f1269c`, keep: same AUC with evaluation reduced from 30.8 s to 11.3 s. Training 2.7 s. Unknown categories produce a pandas future-deprecation warning; use explicit category codes with -1 for missing next.

## Experiment 3 — exploration: ordinal calendar and departure components

Hypothesis: numeric day of month, day of year, departure hour, and departure minute expose contiguous calendar and clock effects to shallow trees. Retain native categorical month and weekday. [Scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses temporal representations and notes trees can handle nonlinear effects; the earlier flight-delay research motivates scheduled-time features. Day-of-year effects may overfit the training year, so judge only the harness score. Also express the equivalent category conversion via explicit codes to avoid the deprecation warning.

Result: **0.6831**, commit `cc608a9`, keep (+0.0062); training 2.6 s, eval 8.2 s. Temporal representation is more promising than the initial parameter change.

## Experiment 4 — exploration: categorical route and carrier-airport interactions

Hypothesis: explicit Origin-Dest, UniqueCarrier-Origin, and UniqueCarrier-Dest identities expose operational interactions in one tree split instead of requiring several levels. Use only train-fitted category vocabularies, no target means or frequency features. [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) supports grouped category splits; the [CatBoost paper](https://proceedings.neurips.cc/paper/7898-catboost-unbiased-boosting-with-categorical-features.pdf) motivates categorical combinations while warning about naive target statistics. Here the model remains XGBoost.

Result: **0.6713**, commit `e03fc4c`, discard (-0.0118); training 4.6 s, eval 11.6 s. Unrestricted high-cardinality interactions generalize poorly across years; do not assume richer categorical identities help.

## Experiment 5 — follow-up: deeper trees on the successful temporal features

Hypothesis: the compact successful features still have useful multiway interactions that depth 4 cannot capture. Increase only max_depth from 4 to 6, retaining 500 rounds and the stronger leaf/L2/subsampling regularization from experiment 1. Based on the XGBoost complexity controls already researched.

Result: **0.6737**, commit `e161abf`, discard (-0.0094); training 4.7 s, eval 8.5 s. Greater depth is harmful under the year shift, consistent with the poor high-cardinality interactions.

## Experiment 6 — ablation: shorten boosting

Hypothesis: 500 rounds may also learn too much year-specific detail. Reduce rounds to 200 with depth 4 and all other successful settings fixed. This tests overall ensemble capacity separately from depth.

Result: **0.6853**, commit `851c3a5`, keep (+0.0022); training 1.6 s, eval 8.2 s. Both depth and round-count evidence favor controlling capacity.

## Experiment 7 — exploration: holiday-relative calendar

Hypothesis: travel patterns around holidays transfer across years when expressed relative to the actual holiday instead of raw day-of-year. Compute nearest holiday offset and holiday identity from month/day/weekday alone, using fixed non-leap calendar offsets appropriate to 2005/2006. Moving Monday/Thursday holidays follow [OPM calendar rules](https://www.opm.gov/faq/payleave/what-are-federal-holidays.ashx). No external dataset or inferred train/eval flag. Test known moving holidays in both years and row invariance.

Result: **0.6841**, commit `bcff59e`, discard (-0.0012); training 1.7 s, eval 10.3 s. Generic nearest-holiday identity/offset did not improve the stronger baseline, despite correctly handling moving holidays.

## Experiment 8 — exploration: restrict categorical partition complexity

Hypothesis: noisy category groupings are a remaining source of year-specific overfitting. Set max_cat_threshold=16 and max_cat_to_onehot=32: small calendar/carrier variables get single-category splits, while airport partitions are limited. [XGBoost categorical parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) describes both controls. This is different from reducing overall depth/rounds: it targets the categorical split search.

Result: **0.6832**, commit `65ca1bc`, discard (-0.0021); training 1.5 s, eval 8.2 s. Small-category one-hot splits plus restricted airport partition search lose useful signal.

Training split-gain inspection of kept artifact `851c3a5` shows scheduled departure time dominates; calendar, carrier, and airports follow. These are training diagnostics, not an additional evaluation metric.

## Experiment 9 — exploration: boosted small forests

Hypothesis: averaging four randomized trees per boosting round reduces variance in categorical partitions without removing their expressiveness. Use num_parallel_tree=4, subsample=0.65, colsample_bynode=0.8 with the same 200 rounds/depth 4. [XGBoost random-forest documentation](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes the combination of parallel trees and multiple boosting rounds. No cross-validation or separate metric.

Result: **0.6854**, commit `11f7a90`, keep (+0.0001 under the rounded-AUC rule); training 5.1 s, eval 8.4 s. Tiny improvement is not strong evidence on its own, but forest averaging is a viable direction.

## Experiment 10 — ablation: remove fine-grained calendar

Hypothesis: numeric day-of-month and day-of-year allow memorizing transient weather and date-specific disruptions in 2005. Remove both, keeping month/weekday categories and the clock components, to measure whether a coarser calendar transfers better.

Result: **0.6810**, commit `089f422`, discard (-0.0044); training 5.3 s, eval 8.2 s. Fine-grained calendar contains useful transferable signal despite the risk of year-specific effects.

## Synthesis after experiments 1–10

Best: **0.6854** at `11f7a90`, vs baseline 0.6743. Successful changes are ordered calendar/clock representation, fewer regularized shallow trees, and marginally forest averaging. Preparation simplification made evaluation about 3–4x faster. Deeper trees, raw pair categories, generic holiday features, and restrictive categorical splitting hurt. Removing fine-grained dates also hurt, so deleting the calendar is too blunt. Current theory: scheduled time dominates and date main effects matter, but flexible airport/date interactions can fit transient weather. Next isolate interaction structure, then test train-fitted schedule-relative features and smoother time representations.

Research refresh: searched feature interaction and monotonic constraints. [Interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) allow specified groups of features to share tree paths; [monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) impose directional effects. A global monotonic clock effect is questionable for overnight flights, so prioritize interaction constraints first.

## Experiment 11 — exploration: additive fine-calendar effects

Hypothesis: retain valuable calendar signal while preventing day-of-year/day-of-month from interacting with airport, carrier, and clock variables. Use two disjoint groups: core operational features (including month/weekday) and fine calendar (day-of-month/day-of-year). Disjoint groups avoid the overlapping-group behavior described in the documentation. This is more targeted than deleting dates, which experiment 10 showed was harmful.

Result: **0.6857**, commit `cd5a55f`, keep (+0.0003); training 5.1 s, eval 8.3 s. Keeping fine-calendar effects but separating their interactions is modestly helpful.

## Experiment 12 — exploration: distance-derived airport geometry

Hypothesis: a low-dimensional representation of airports learned from known route distances shares regional signal across airports better than identities alone. Fit a symmetric graph of median route distances on train, fill missing pair distances via shortest paths, and perform classical MDS for two coordinates. Prepare only looks up origin/destination coordinates. No counts, labels, or external airport data enter the embedding. [Isomap/manifold documentation](https://scikit-learn.org/stable/modules/manifold.html#isomap) and [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html) supply the algorithmic basis. Graph-path coordinates approximate geography; they are not actual latitude/longitude.

Result: **0.6856**, commit `d0145d2`, discard (-0.0001); training 5.5 s, eval 9.1 s. Geometry is a near-miss but the keep rule requires reverting even this small decline.

## Experiment 13 — exploration: schedule-relative departure times

Hypothesis: relative position in an origin, carrier-origin, or route schedule is a useful proxy for accumulated operational disruption. Fit median scheduled departure minutes for those groups on train, then expose row departure minus the fitted median. [Systemic delay propagation study](https://www.nature.com/articles/srep01159) discusses daily schedules and cascading delay, while [pandas grouping documentation](https://pandas.pydata.org/docs/user_guide/groupby.html) defines the aggregation. These are coarse schedule proxies, not measured aircraft rotations. No frequency or count features.

Result: **0.6863**, commit `e9b376a`, keep (+0.0006); training 5.4 s, eval 9.7 s. Low-dimensional schedule context works better than raw route identities.

## Experiment 14 — follow-up: larger leaf support

Hypothesis: the schedule features may expose broad stable patterns, while small leaves still fit noisy airport/date details. Increase min_child_weight from 20 to 200, leaving feature construction, ensemble length, depth, and all other settings fixed. This tests leaf support, a separate capacity control from the depth and round-count experiments.

Result: **0.6862**, commit `9b09cf1`, discard (-0.0001); training 5.4 s, eval 9.7 s. Tenfold larger leaf support is a near-miss but not a gain.

## Experiment 15 — exploration: cyclic operational clock

Hypothesis: cyclic sine/cosine departure time and a clock starting at 04:00 make overnight continuity and the daily operational reset easier for shallow trees to represent. Retain raw departure time and schedule offsets. Based on [scikit-learn cyclic feature examples](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) and the daily-reset discussion in [delay propagation research](https://www.nature.com/articles/srep01159). The 04:00 reset is a hypothesis, not an observed boundary in the evaluation data.

Result: **0.6863**, commit `50a881e`, discard: equal rounded AUC with extra code and slower runtime (training 6.0 s, eval 10.3 s). The keep rule rejects this tie.

## Experiment 16 — exploration: independent target-encoding stage

Hypothesis: smoothed historical route/carrier-airport delay rates may supply useful interactions without the overfitting of raw pair categories. Reserve a fixed random 20% of train only to fit the label-mean lookups, and fit one XGBoost model on the remaining 80%. Keep these lookups fixed for both training preparation and evaluation. Use a prior strength of 20 and global prior 0.5; only label means become features. There is one model fit, no validation scoring, and no retraining. This sacrifices some classifier data to prevent self-label leakage. [TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) explains smoothed label means; its [leakage example](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html) motivates separating lookup-fitting labels from model-fitting labels. This experiment uses a single disjoint split rather than that example's cross-fitting procedure.

Result: **0.6848**, commit `b6a7adf`, discard (-0.0015); training 5.0 s, eval 11.4 s. Independently fitted label means did not compensate for the reduced classifier data. Verified disjoint fitting subsets, row invariance, and feature independence from supplied row labels.

## Experiment 17 — exploration: single-category splits for all identities

Hypothesis: fully one-hot-style categorical splitting avoids the adaptive grouping of rare airport categories that can fit noise. Set max_cat_to_onehot=1024 so every existing categorical feature, including airports, uses single-category splits. Unlike experiment 8, this changes the airport splitting method rather than merely limiting category partitions; retain all other settings for a controlled test. Basis: XGBoost categorical split documentation already researched.

Result: **0.6798**, commit `a46335d`, discard (-0.0065); training 4.8 s, eval 9.6 s. Airport category grouping is valuable, and eliminating it is too restrictive at this ensemble size.

## Experiment 18 — ablation/simplification: weekly calendar resolution

Hypothesis: coarsening day-of-year and day-of-month into seven-day bins retains the useful date information established by experiment 10 while removing single-date sensitivity. Keep their existing feature names and isolated interaction group, change only the numerical resolution. This tests a middle ground between deleting dates and unrestricted fine resolution.

Result: **0.6852**, commit `433f2e4`, discard (-0.0011); training 5.4 s, eval 9.7 s. Seven-day bins remove useful date distinctions; revert to exact ordinal dates.

## Experiment 19 — exploration: pairwise ranking loss

Hypothesis: optimizing pairwise ordering of delayed versus non-delayed flights may better match AUC than pointwise logistic loss. Use XGBRanker with rank:pairwise, one group containing the training set, and mean sampling with two pairs per sample. Wrap its scores in a monotone sigmoid for the existing predict_proba interface. The harness and its metric remain unchanged. [XGBoost ranking tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) defines the pairwise logistic loss and pair sampling. Keep the successful tree/feature configuration.

Result: **0.6834**, commit `36748d6`, discard (-0.0029); training 15.0 s, eval 9.9 s. Pairwise training is feasible within the timeout but underperforms logistic classification at these settings.

## Experiment 20 — follow-up: smaller boosting steps at matched total shrinkage

Hypothesis: 400 rounds at learning rate 0.04 can refine the successful classifier more gently than 200 rounds at 0.08, while keeping the nominal total shrinkage at 16. This isolates update size from the harmful increase in total boosting explored earlier. Keep four trees per round and all successful features/constraints. Basis: shrinkage guidance in the XGBoost tuning documentation.

Result: **0.6863**, commit `e843784`, discard: tied AUC with training increased to 9.9 s and eval 9.8 s. Keeping 200 rounds at 0.08 is simpler and faster.

## Synthesis after experiments 11–20

Best: **0.6863** at `e9b376a`. Isolating fine-calendar interactions and schedule-relative departures improved the prior best by 0.0009. Airport geometry and larger leaves nearly tied, but failed the keep rule. Removing/coarsening dates and removing category grouping lost signal. Independently fitted label rates with a smaller classifier training subset and pairwise ranking did not help. Cyclic clock expansion and smaller update size tied without simplifying. Current theory: useful operational structure is mostly smooth and low-order, but global date effects and grouped airport effects remain necessary. Next test monotone operational-clock priors, magnitude regularization, and selective feature sampling rather than removing whole signal families.

Research refresh: [monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) supports named numerical feature directions; [feature-weight documentation](https://xgboost.readthedocs.io/en/stable/python/python_api.html) allows weighted column sampling. The former is a stronger shape prior, the latter can selectively regularize noisy feature families.

## Experiment 21 — exploration: increasing operational-clock prior

Hypothesis: positive monotonic constraints on raw departure time, departure hour, and each schedule-relative departure offset suppress spurious downward trends while preserving airport/carrier/calendar effects. Daily delay propagation provides a domain rationale, but overnight flights may violate this prior; evaluate it rather than assume it is correct. Minute-of-hour stays unconstrained because it represents schedule-bank structure.

Result: **0.6856**, commit `238d4bf`, discard (-0.0007); training 5.5 s, eval 9.6 s. Training-only hourly summaries show the delayed fraction peaks around 20:00 then declines (0.653 at 20:00, 0.559 at 23:00), so a universal increasing clock prior is questionable. These summaries were descriptive training-data inspection, not another metric.

## Experiment 22 — follow-up: stronger L2 leaf shrinkage

Hypothesis: increase reg_lambda from 10 to 100 to shrink noisy leaf predictions while still allowing small, informative airport groups. This differs from experiment 14's minimum-support restriction: it retains small leaves but reduces their magnitude. All features and other hyperparameters stay fixed.

Result: **0.6862**, commit `9bd890f`, discard (-0.0001); training 5.5 s, eval 9.9 s. Stronger L2 does not improve this configuration.

Plateau research: experiments 20–22 are consecutive discards within 0.001 of best. Searched again rather than continuing arbitrary penalty tweaks. [Friedman's gradient boosting paper](https://doi.org/10.1214/aos/1013203451), with an accessible [paper copy](https://www.cse.iitb.ac.in/~soumen/readings/papers/Friedman1999GreedyFuncApprox.pdf), connects tree size with interaction order. This suggests reallocating tree capacity toward more shallow components.

## Experiment 23 — follow-up: more depth-3 components

Hypothesis: 400 depth-3 rounds can model smooth low-order structure more effectively than 200 depth-4 rounds. Keep learning rate 0.08 and four parallel trees; the maximum total leaf budget is approximately unchanged (400*4*8 versus 200*4*16), while each component supports fewer interactions. This is different from experiment 20, which changed only update size at fixed depth.

Result: **0.6856**, commit `1366d25`, discard (-0.0007); training 8.6 s, eval 10.0 s. Reallocating leaf capacity toward shallower components does not beat the current depth-4 model.

## Experiment 24 — exploration: average independent boosting trajectories

Hypothesis: three independently seeded copies of the successful configuration reduce partition and boosting-trajectory variance beyond the existing within-round forest averaging. Use fixed seeds 42, 137, and 2026, uniform probability averaging, and train every member on all of train. No seed selection or individual member evaluation. [Scikit-learn ensemble guidance](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier) describes averaging predicted probabilities. The single harness AUC evaluates the combined model.

Result: **0.6865**, commit `51d7d3b`, keep (+0.0002); training 14.4 s, eval 10.1 s. Full-trajectory averaging gives a small improvement beyond within-round forests.

## Experiment 25 — ablation/simplification: remove within-round forests

Hypothesis: three independently averaged models may make four parallel trees per round redundant. Set num_parallel_tree from 4 to 1 while keeping the three seeds and all other settings fixed. If rounded AUC is preserved, the faster smaller ensemble qualifies for keeping.

Result: **0.6862**, commit `8ef8f4d`, discard (-0.0003); training 3.8 s, eval 9.6 s. Faster, but lower AUC is not eligible for keeping. Within-round forest averaging still contributes.

## Experiment 26 — exploration: selectively sample fine calendar less often

Hypothesis: assigning day-of-month/day-of-year feature weights 0.25 versus 1 for all other features preserves fine-date effects while reducing how often they enter the split search. Unlike deleting or binning dates, this keeps their full resolution. The [XGBoost feature-weight API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) supports weights for column sampling; confirmed feature_weights is a supported estimator parameter in the installed version.

Result: **0.6851**, commit `4baa78a`, discard (-0.0014); training 14.4 s, eval 10.0 s. Fine-calendar availability should not be reduced this aggressively.

## Experiment 27 — exploration: seasonal specialist blend

Hypothesis: winter/spring/summer/autumn models can capture seasonal airport and carrier behavior that the global shallow model underfits. Train four specialist XGBoost models on fixed DJF/MAM/JJA/SON subsets, each with 100 rounds and min_child_weight=50. Blend 25% matching-season probability with 75% of the kept global three-model average. [Local-expert research](https://www.cs.toronto.edu/~hinton/absps/jjnh91.html) motivates specialization; this uses fixed known calendar routing rather than learned gates. Every learner uses train data only and only the combined model is evaluated by the harness.

Result: **0.6862**, commit `aa1103c`, discard (-0.0003); training 17.4 s, eval 10.3 s. Fixed seasonal specialists did not add useful diversity to the global ensemble.

## Experiment 28 — exploration: low-cardinality calendar interaction

Hypothesis: a Month-DayOfWeek category (at most 84 levels) captures seasonal shifts in weekly travel patterns with much stronger group support than experiment 4's route/carrier-airport categories. Keep native category partitioning and existing calendar isolation. Fit only the category vocabulary on train and build each row's key in prepare. This follows the categorical-combination literature already reviewed, with cardinality deliberately limited.

Result: **0.6836**, commit `f0d715a`, discard (-0.0029); training 14.8 s, eval 11.0 s. Even low-cardinality joint calendar categories can add unstable year-specific structure.

## Experiment 29 — ablation/simplification: shorter averaged ensemble

Hypothesis: the successful three-model ensemble may still overfit at 200 rounds. Halve to 100 with all other settings fixed. This probes the low-capacity side of the learning curve; previous testing only established that 500 rounds was worse than 200 in the earlier single-model configuration.

Result: **0.6850**, commit `e126238`, discard (-0.0015); training 8.7 s, eval 9.8 s. The shorter averaged ensemble underfits; retain 200 rounds.

## Experiment 30 — exploration: additive linear XGBoost with local basis functions

Hypothesis: one-hot categorical main effects plus piecewise-linear cyclic clock/calendar bases and distance/schedule-offset bases can capture stable nonlinear effects with fewer interactions. Use XGBoost gblinear, deterministic coordinate descent, 80 updates, learning rate 0.5, L2=0.0002 (normalized by sample count). Prepare emits all engineered numeric columns; the model only converts dense storage to CSR for efficiency. No additional data or metric. [XGBoost linear booster documentation](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-linear-booster-booster-gblinear) explains normalized penalties and solvers; [time-basis examples](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) motivate smooth periodic bases. gblinear is deprecated in current docs but supported by the installed package for this experiment.

Result: **0.6768**, commit `0c82a23`, discard (-0.0097); training 12.7 s, eval 10.1 s. The additive model is compact (0.2 MB), but removing interactions loses substantial predictive information. Row invariance passed for its 736 prepared numeric features.

## Synthesis after experiments 21–30

Best: **0.6865** at `51d7d3b`. Three independently trained boosting trajectories helped slightly. One tree per round, fewer rounds, monotone time constraints, stronger L2, selective calendar suppression, and seasonal specialists all fell short. Joint calendar categories hurt even at modest cardinality. An additive model lost nearly 0.01 AUC, establishing that some interactions are essential rather than pure noise. Keep the current moderate-depth ensemble as the anchor. Next investigate tree dropout and heterogeneous feature/model averaging, then revisit numeric resolution and split penalties.

Research refresh: [DART paper](https://proceedings.mlr.press/v38/korlakaivinayak15.html) proposes dropping trees during training to combat over-specialization of later components. [XGBoost dropout parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#additional-dropout-parameters-for-tree-boosters) define rate_drop, skip_drop, and normalization.

## Experiment 31 — exploration: tree dropout

Hypothesis: DART with rate_drop=0.05 and skip_drop=0.5 improves temporal transfer by reducing dependence on specialized trees. Test one seed with the existing four-tree-per-round configuration to keep the more expensive training within 60 seconds. The earlier single-model comparator was 0.6863; the strict keep threshold remains the current ensemble's 0.6865.

Result: **training timeout**, commit `f7957ac`, crash; killed by harness after 60.0 s, no AUC/artifact. Revert. Tree dropout repeatedly predicts the growing ensemble during fitting, so four parallel trees make this configuration too costly.

## Experiment 32 — follow-up: dropout within the training limit

Hypothesis: two independently seeded dropout models with one tree per round retain dropout regularization at much lower total training cost than one four-tree-per-round model. Use the current native tree-booster dropout interface (rate_drop=0.05, skip_drop=0.5), 200 rounds, seeds 42/137. XGBoost's warning and current documentation recommend the tree booster directly rather than the deprecated dart alias. This is a compute-constrained redesign of experiment 31, not an attempt to bypass the timeout.

Result: **0.6856**, commit `11fbccc`, discard (-0.0009); training 33.8 s, eval 9.6 s. Dropout fits the budget after reducing parallel trees, but remains below the kept ensemble.

## Experiment 33 — follow-up: blend the geometry near-miss with the anchor

Hypothesis: experiment 12's airport geometry may add complementary errors even though it narrowly missed as a replacement. Preserve the three anchor models and add a fourth learner with the distance-derived geometry; average all four equally. Base members use their original features and constraints, the extra member uses the added coordinates. Geometry remains fitted solely on train route distances. The ensemble-averaging sources already reviewed motivate testing diversity rather than requiring every component to win alone.

Result: **0.6864**, commit `541ef84`, discard (-0.0001); training 19.2 s, eval 10.9 s. Geometry remains a near-miss even as a minority component of the ensemble.

## Experiment 34 — exploration: loss-guided tree growth at fixed leaf budget

Hypothesis: permitting uneven branch depth allocates the same 16-leaf budget more effectively than fully depth-wise growth. Set grow_policy=lossguide, max_leaves=16, max_depth=8, tree_method=hist. Retain the three-member ensemble and 200 rounds. Unlike the earlier depth-6 experiment, this does not permit 64 leaves per tree. [XGBoost growth-policy documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) and the [LightGBM paper](https://proceedings.neurips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree.pdf) describe best-first leaf growth; the implementation here remains XGBoost.

Result: **0.6865**, commit `45ae31c`, discard: tied AUC but extra parameters, larger artifact, and slower training (17.3 s versus 14.4 s); eval 10.3 s.

## Experiment 35 — follow-up: targeted moving-holiday alignment

Hypothesis: an explicit signed distance to Thanksgiving corrects the one-day holiday shift between training and evaluation years without the many unrelated holiday identities from experiment 7. Compute the fourth Thursday of November from the row's month/day/weekday, clip distance to +/-10 days, and expose one numeric feature. [OPM holiday rules](https://www.opm.gov/faq/payleave/what-are-federal-holidays.ashx) define the date. No hardcoded split year or external data.

Result: **0.6861**, commit `3fbeb63`, discard (-0.0004); training 14.8 s, eval 10.4 s. Correct holiday alignment alone did not add enough signal.

Plateau research refresh: read about [group shifts and spurious correlations](https://arxiv.org/abs/1911.08731) and [importance-weighted learning](https://proceedings.mlr.press/v97/byrd19a.html). These motivate changing the training objective's emphasis rather than adding more feature interactions. We cannot estimate evaluation-domain weights because evaluation rows are off-limits.

## Experiment 36 — exploration: temper training-day label fluctuations

Hypothesis: some daily delay-rate variation reflects transient 2005 weather that should not dominate future-year prediction. Compute train-only daily delay means and month-weekday means, then give each class a square-root importance weight toward its month-weekday prior. Clip weights to [0.5,2] and normalize their mean to 1. This partially reduces daily label-rate differences while preserving coarse seasonal/weekly patterns. Weights affect only training loss, never prepare features. This is a heuristic adaptation inspired by weighting research, not an implementation of group DRO or a claim to know the future label distribution. Genuine holiday signals could be weakened; the harness determines whether the tradeoff helps.

Result: **0.6832**, commit `15cd617`, discard (-0.0033); training 14.6 s, eval 10.2 s. The weighting hypothesis removed useful signal or distorted operational relationships. Do not assume daily variation is merely transient noise.

## Experiment 37 — exploration: coarser numeric split histograms

Hypothesis: max_bin=64 reduces sensitivity to tiny numeric differences in departure times, distances, and schedule offsets while retaining native categorical handling and all features. This differs from experiment 18's calendar-only binning: the histogram approximation regularizes every numeric split using training quantiles. [XGBoost histogram parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) define max_bin and its precision/complexity tradeoff.

Result: **0.6858**, commit `e7458d2`, discard (-0.0007); training 13.5 s, eval 10.0 s. Coarser thresholds lose useful numeric resolution.

## Experiment 38 — exploration: robust generalized cross-entropy

Hypothesis: scheduled flight features leave much outcome variation unexplained; a robust loss may spend less capacity on the hardest-to-explain training labels. This does not assume that the recorded labels are incorrect. Adapt the [generalized cross-entropy paper](https://papers.neurips.cc/paper/8094-generalized-cross-entropy-loss-for-training-deep-neural-networks-with-noisy-labels.pdf) with q=0.3. For true-class probability u, scale the logistic gradient by (2u)^q, preserving initial gradient scale. Use the correspondingly scaled logistic Hessian, a positive upper bound on the true generalized-loss Hessian; [XGBoost custom objective guidance](https://xgboost.readthedocs.io/en/stable/tutorials/advanced_custom_obj.html) motivates positive curvature approximations. All features, rounds, and ensemble seeds stay fixed. The installed sklearn wrapper retains binary:logistic prediction transformation for a callable objective. Check the derivative numerically on synthetic margins before the harness run.

Result: **0.6861**, commit `246f5bc`, discard (-0.0004); training 14.8 s, eval 10.0 s. Downweighting hard outcomes did not improve future-year ranking.

## Experiment 39 — ablation/simplification: remove day-of-month feature

Hypothesis: day-of-year carries useful seasonal and holiday timing, whereas a separate day-of-month feature encourages monthly repetition that does not generalize. Experiment 10 removed both date features and lost AUC; this ablation preserves day-of-year while removing only the redundant monthly ordinal. Keep the disjoint calendar/operations constraint, now with a one-feature calendar group. No new feature family or parameter is introduced.

Result: **0.6858**, commit `f97c2ec`, discard (-0.0007); training 13.2 s, eval 9.8 s. Both calendar coordinates contribute to this model; the monthly ordinal is not redundant at this capacity.

## Experiment 40 — follow-up: destination-side schedule offsets

Hypothesis: the successful origin, carrier-origin, and route schedule offsets omit the destination's broader arrival schedule. Add train-fitted median departure-time offsets grouped by destination and carrier-destination. These encode where a flight lies in the incoming schedule without using any row-count features. This is a complementary endpoint grouping rather than another numerical tuning of the same feature. The previously reviewed [flight-delay propagation study](https://www.nature.com/articles/srep01159) motivates destination-network effects, though this feature is only a schedule proxy and contains no actual arrival or congestion data.

Result: **0.6863**, commit `46f5c3b`, discard (-0.0002); training 14.9 s, eval 10.3 s. Destination-side offsets are plausible but do not improve the best ensemble.

## Synthesis after 40 experiments

Best remains **0.6865** at `51d7d3b`. The strongest durable changes were numeric calendar coordinates, fewer boosting rounds, train-fitted schedule offsets, disjoint calendar interactions, and seed averaging. Experiments 31–40 found no improvement: dropout was either too slow or weaker; geometry as a minority ensemble component and loss-guided growth were close; holiday alignment, daily reweighting, robust loss, and numeric coarsening lost AUC. Removing day-of-month also lost signal. Current theory: reliable schedule timing and modest categorical interactions matter more than elaborate correction of year-specific noise. Reading the best saved model's gain importances (no data scoring) confirms departure time/hour and origin-relative schedule position dominate; gain alone does not justify dropping weaker variables. Refresh searched [XGBoost regularization guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter definitions](https://xgboost.readthedocs.io/en/stable/parameter.html), and [shrinkage research](https://proceedings.mlr.press/v28/telgarsky13.html). Next: test pruning weak splits, then targeted schedule-feature simplification and sample diversity. These differ from reducing every tree's maximum depth or number of rounds.

## Experiment 41 — exploration: prune weak splits with gamma

Hypothesis: retaining 200 rounds and depth 4 while requiring a split loss reduction of 5 preserves strong late corrections and removes weak branches. Earlier global reductions in depth or rounds removed useful capacity; a local split threshold may be more selective. [XGBoost's gamma parameter](https://xgboost.readthedocs.io/en/stable/parameter.html) directly implements this minimum improvement. Set gamma=5 with all other best settings unchanged.

Result: **0.6864**, commit `c0b70fb`, discard (-0.0001); training 14.2 s, eval 9.8 s. Selective pruning is close but does not beat the anchor.

## Experiment 42 — ablation/simplification: origin-only schedule offset

Hypothesis: the origin's typical departure time carries most of the useful schedule context, while route and carrier-origin medians add sparse, year-specific detail. Gain diagnostics of the best saved model support this hypothesis but do not prove it. Keep OriginDepOffset and remove CarrierOriginDepOffset and RouteDepOffset together; evaluate the simpler schedule representation. This directly decomposes experiment 13's three-feature improvement and reduces lookup storage and per-row work.

Result: **0.6861**, commit `3aa75b4`, discard (-0.0004); training 13.0 s, eval 9.2 s. The route and carrier-origin offsets together add signal despite low gain importance.

Plateau research refresh: re-read [categorical partitioning](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) and [tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html). The early categorical experiment changed both the one-hot threshold and partition threshold, so it did not identify their separate effects. Later all-one-hot performance was much worse, making a partition-only follow-up informative.

## Experiment 43 — follow-up: isolate categorical partition regularization

Hypothesis: limiting category partition search to max_cat_threshold=16 can regularize airport splits while preserving the useful grouping of carrier and month categories. Experiment 8 also set max_cat_to_onehot=32, forcing these smaller categories to one-hot splits; experiment 17 showed one-hot behavior was harmful. Change only max_cat_threshold now, leaving native partitioning defaults intact. This explicitly removes the earlier confound instead of repeating its configuration. Source: [categorical parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: **0.6858**, commit `3ec19e7`, discard (-0.0007); training 12.3 s, eval 9.7 s. Partition restriction itself is harmful, not merely the one-hot change in experiment 8.

## Experiment 44 — follow-up: increase rows available to each tree

Hypothesis: with three independently seeded models already reducing variance, subsample=0.65 may inject unnecessary noise into airport-category estimates. Increase subsample to 0.9 while retaining column sampling, four parallel trees, and the same three seeds. This trades some tree diversity for stronger category estimates; unlike experiment 25 it does not remove parallel trees. [XGBoost random-forest guidance](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) describes the diversity role of row and column sampling.

Result: **0.6872**, commit `472aa3f`, KEEP (+0.0007); training 11.9 s, eval 9.7 s. Higher row sampling improves the three-seed ensemble and is faster; stable estimates outweigh the lost row diversity in this setting. New best kept commit is `472aa3f494a437aa17294e845c6a5aca88648214`.

## Experiment 45 — follow-up: remove row subsampling

Hypothesis: the improvement from 0.65 to 0.9 row sampling in experiment 44 suggests sample noise is now excessive after seed averaging. Test the full-data endpoint subsample=1.0; keep column sampling and independent seeds to retain diversity. This tests whether all-row gradient estimates beat the remaining row regularization rather than making an arbitrary small numerical step. Source: [XGBoost sampling parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

Result: **0.6865**, commit `bbdec09`, discard (-0.0007); training 11.2 s, eval 9.6 s. Some row sampling remains useful; keep the 0.9 setting.

## Experiment 46 — ablation/simplification: single model at higher row sampling

Hypothesis: after increasing row sampling to 0.9, the more stable individual learners may no longer need seed averaging. Remove the wrapper and train one seed-42 model, retaining four parallel trees per boosting round. Experiment 25 removed parallel trees but kept three seeds, so it tested a different source of diversity. This removes code and two-thirds of training work if AUC is preserved.

Result: **0.6869**, commit `4677596`, discard (-0.0003); training 3.9 s, eval 9.7 s. The ensemble still adds measurable AUC, so retain it despite the single model's speed advantage.

## Experiment 47 — follow-up: scale schedule offsets by group spread

Hypothesis: being two hours after a group's typical departure is more unusual for a narrow departure bank than for an airport with an all-day schedule. Replace the three minute offsets by offsets divided by each training group's interquartile departure-time range, with a 60-minute floor. The [RobustScaler documentation](https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.RobustScaler.html) explains train-fitted median/IQR scaling. Here it is fitted separately per group, so it changes cross-group ordering; ordinary global scaling alone would not materially change tree splits. All scales are fitted on train outside prepare, with no frequencies or counts used as features.

Result: **0.6870**, commit `eaddc82`, discard (-0.0002); training 11.9 s, eval 9.9 s. Minute-scale offsets remain slightly better than within-group spread scaling.

Plateau research refresh after experiments 45–47: reviewed [partition limits in the XGBoost documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) and the [installed-version split implementation](https://raw.githubusercontent.com/dmlc/xgboost/v3.4.1/src/tree/hist/evaluate_splits.h). The next change tests less restrictive category grouping while retaining shallow trees, motivated by the isolated restriction test losing AUC.

## Experiment 48 — follow-up: broader categorical partition search

Hypothesis: with 283 training airports per endpoint and stronger 0.9 row sampling, the default 64-category partition search may be too restrictive. Set max_cat_threshold=256, allowing broader groups without increasing tree depth, number of leaves, or one-hot behavior. Experiment 43 found the tighter 16-category limit harmful; this explores the opposite structural endpoint rather than another small threshold adjustment.

Result: **0.6864**, commit `f62dfe3`, discard (-0.0008); training 12.4 s, eval 9.7 s. Broadening category search overfits relative to the default limit; both tighter and looser limits have now lost AUC.

## Experiment 49 — ablation/simplification: remove minute-within-hour feature

Hypothesis: the explicit departure minute encourages carrier-specific schedule quirks that change between years. Remove only DepMinute, the lowest-gain feature in the saved model. Raw HHMM and all minute-resolution schedule offsets remain, so no basic departure-time information is lost; only the standalone repeating minute pattern is removed. The earlier calendar ablation showed low gain need not mean dispensability, so this remains a harness-tested hypothesis.

Result: **0.6873**, commit `9da3268`, KEEP (+0.0001); training 11.9 s, eval 9.5 s. Removing the minute-within-hour feature modestly improves AUC and simplifies preparation. New best is `9da326800b81270f6398d6703e0bd0646f57efd1`.

## Experiment 50 — follow-up: expand averaging from three seeds to five

Hypothesis: seed averaging still contributed 0.0003 AUC at the stronger sampling setting (experiment 46), so two additional independently seeded models may reduce residual sampling variation. Add fixed seeds 31415 and 2718 to the existing 42, 137, 2026 set, retaining equal weights and identical hyperparameters. The seeds are specified before evaluation and no per-member evaluation is performed. This follows the [ensemble averaging principle](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier) already reviewed; a tied score will be discarded because the model is larger and slower.

Result: **0.6873**, commit `f44b062`, discard: tied AUC with more models and slower training (21.3 s versus 11.9 s); eval 10.0 s. Keep three seeds.

## Synthesis after 50 experiments

Best is now **0.6873** at `9da3268`, an absolute gain of 0.0130 over baseline. Increasing per-tree row sampling from 0.65 to 0.9 contributed the largest late gain (+0.0007), and removing the standalone minute feature added 0.0001 while simplifying preparation. Full-row sampling lost the gain, so modest sampling still helps. A single model remained weaker, while five same-configuration seeds merely tied three. Both tighter and broader categorical partition search lost AUC; default partition handling remains best. Schedule spread normalization and several feature removals were near misses. Fresh research read [Wood et al.'s diversity theory](https://jmlr.org/papers/v24/23-0041.html) and [Liu and Mazumder's randomization study](https://www.jmlr.org/beta/papers/v26/24-0255.html): ensemble diversity trades off with member accuracy and is not an objective to maximize blindly. Next test structural diversity across tree depths while preserving the three best base learners, then use the last remaining time for a focused capacity check.

## Experiment 51 — follow-up: ensemble diversity across interaction depth

Hypothesis: the unchanged score from two more same-depth seeds suggests their errors are redundant. Preserve the three depth-4 learners and add a depth-3 / 400-round member and depth-5 / 100-round member, each with the same nominal maximum leaf budget as a 200-round depth-4 model. Average all five equally. The source on [ensemble diversity tradeoffs](https://jmlr.org/papers/v24/23-0041.html) motivates testing complementary complexity, not assuming that a larger ensemble must win. The earlier shallower standalone model missed the best; averaging may use its different interaction bias without replacing the anchor.

Result: **0.6875**, commit `896f434`, KEEP (+0.0002); training 21.9 s, eval 10.0 s. Structural diversity across interaction depths helps where two extra same-depth seeds did not. New best is `896f43480b4a7599487e643d56db3f97ebd8e5c0`.

## Experiment 52 — follow-up: longer boosting with the more stable ensemble

Hypothesis: higher row sampling and complementary depths may allow useful smaller effects to be learned beyond the old 200-round budget. Double every member's boosting rounds while retaining learning rate 0.08 and the same relative member capacities: depth-4 members 400 rounds, depth-3 member 800, depth-5 member 200. Unlike experiment 20, learning rate is not reduced, so this tests increased effective fitting capacity. Expected training is about 44 seconds from the last run, below the 60-second limit. The [shrinkage research](https://proceedings.mlr.press/v28/telgarsky13.html) and previous round-count results motivate checking the optimization length after materially changing regularization and averaging.

Result: **0.6865**, commit `bd973d8`, discard (-0.0010); training 42.6 s, eval 11.5 s. Doubling effective fitting capacity overfits despite the more stable ensemble.

Independent correctness check on the saved best artifact `896f434`: 40 sampled training rows produce identical batch and per-row features; predicted probabilities have the correct shape, are finite, and sum to one. Synthetic unknown carrier/origin/destination codes map to missing categories and yield finite predictions. This check computed no evaluation metric and used only train rows plus synthetic category substitutions.

## Experiment 53 — ablation/simplification: remove the deepest ensemble member

Hypothesis: experiment 51's improvement may come chiefly from the shallower depth-3 member, while the depth-5 member adds unnecessary high-order interactions. Remove only the depth-5 member; keep all three depth-4 members and the depth-3 member with their original round counts. This isolates the two additions from experiment 51 and could deliver a smaller, faster ensemble without losing AUC. Experiment 52's longer-fit regression reinforces checking excess complexity, though it does not itself prove the deeper member is harmful.

Result: **0.6874**, commit `a6aa196`, discard (-0.0001); training 19.5 s, eval 9.9 s. The deepest member contributes a small additional gain; retain the five-member mixed-depth ensemble.

Timing deviation: experiment 53 was designed after a status showing 2m22s remaining, but its launch was queued in the same tool batch as the next status check, which reported 1m57s. It therefore started just after the prescribed two-minute cutoff and should have been skipped. It completed within the one-hour budget. No further experiments were started.

## Final summary

Completed 53 experiments plus the baseline on branch `oct7`. Best Eval AUC is **0.6875**, up **0.0132** from baseline **0.6743**, at commit **`896f43480b4a7599487e643d56db3f97ebd8e5c0`**. Restored this commit after the final ablation. The corresponding saved artifact is `artifacts/896f43480b4a7599487e643d56db3f97ebd8e5c0.pkl` (22.0 MB). Its recorded fit time is 21.9 s; complete training phase 22.8 s; evaluation 10.0 s.

The retained model averages five XGBoost classifiers: three depth-4 / 200-round learners with seeds 42, 137, 2026, a depth-3 / 400-round learner with seed 31415, and a depth-5 / 100-round learner with seed 2718. All use four parallel trees per round, learning rate 0.08, row sampling 0.9, node-level column sampling 0.8, min_child_weight 20, lambda 10, native categorical features, and disjoint fine-calendar/operational interaction groups. Features include ordinal calendar positions, departure hour, and train-fitted origin, carrier-origin, and route departure-median offsets; the standalone minute feature was removed.

What worked: numeric calendar representation, shorter initial boosting, schedule context fitted only on training data, constrained calendar interactions, averaging, stronger per-tree sampling, removing a weak redundant feature, and modest diversity across tree depths. What did not: high-cardinality category combinations, one-hot category behavior, deeper standalone trees, holiday additions, train-only target encoding with a disjoint fitting split, pairwise ranking, monotonic time constraints, aggressive weighting, linear/additive replacement, dropout, geography features, strong split restrictions, expanded category search, extra same-depth seeds, and doubling all boosting rounds. Some near misses may still be useful in a different regime, but none were kept against the stated AUC rule.

Validation: the TSV contains every experiment, including one training timeout. Every successful run has its committed artifact; the largest logged AUC matches the last kept commit; tracked worktree is clean; only train.py differs from baseline; save_and_evaluate remains the final call. Saved-artifact checks confirmed batch/row preparation equivalence, valid probabilities, and safe unseen-category handling. All model selection used the harness metric; no separate evaluation metric was computed.

Next research direction: investigate a cheaper heterogeneous ensemble that preserves the depth diversity gain, and more structured schedule representations using only training-fitted, row-consistent lookups. Tiny late AUC differences remain selection results on this evaluation set, not proof of an equivalent gain on future data. The timing deviation for the final experiment is recorded above. Stopping the clock as the final action.
