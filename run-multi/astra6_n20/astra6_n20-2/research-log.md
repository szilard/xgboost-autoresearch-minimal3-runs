# XGBoost research log — oct6

## Setup — 2026-10-06

- Created branch `oct6` directly from the current HEAD, `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py` in full.
- Confirmed that `data/train.csv` and `data/eval.csv` exist. Inspected only the training data: 200,000 rows, nine expected columns, 100,000 examples of each target class, and no missing values.
- Verified installed dependencies import successfully: Python 3.14.4, XGBoost 3.4.1, pandas 3.0.6, NumPy 2.5.3, scikit-learn 1.9.1, and cloudpickle 3.1.2. Eight logical CPUs are available.
- Initialized `output/results.tsv` with the required four-column TSV header. Outputs are ignored by Git.
- Training code is unchanged. No baseline has run, and the experiment clock has not started.

## On confirmation

The first action will be `python3 harness.py start`, followed by the unchanged baseline via `python3 harness.py run > output/run.log 2>&1`. Record the baseline AUC against `b15ec66` before changing `train.py`.

Research external sources before the first non-baseline experiment, for each new category of change, at each ten-experiment synthesis, and when a plateau occurs. Record hypotheses, sources, commits, results, and keep/discard decisions here. Follow the harness limits of 60 seconds for training, 300 seconds for evaluation, and one hour for the full experiment.

## Baseline — b15ec66

Unchanged starter: 100 trees, depth 6, learning rate 0.1, native categorical features. Eval AUC **0.6743**; harness training 1.5 s, evaluation 30.7 s. Artifact saved. Kept as the initial reference.

## Initial research

Read [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html), [categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html), [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html), and [TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html). The initial search also identified the flight-delay paper [Zoutendijk and Mitici (2021)](https://www.mdpi.com/2226-4310/8/6/152), whose search excerpt describes schedule and calendar features; the full page could not be opened.

Useful directions: balance boosting capacity against regularization; compare categorical partitions and individual-category splits; represent calendar and departure time explicitly; any target encoding must prevent self-target leakage. Parameter ranges for initial exploration: depth 3–8, learning rate 0.03–0.1, 300–1000 rounds, child weight 10–100, row sampling 0.7–1.0. These are experiment choices, not universal recommended settings. All metrics remain the harness Eval AUC.

## Experiment 1 — exploration: regularized longer boosting

Hypothesis: the 100-tree baseline underfits stable interactions; 600 depth-6 trees at learning rate 0.05, child weight 20, L2 penalty 10, and row/column sampling 0.85/0.9 should add capacity while limiting overfitting across years. Features remain unchanged. Motivated by the XGBoost tuning guidance above.

Outcome: **0.6762 Eval AUC**, **keep**, commit `4a1bbc0`. Run time: 35.0s (training 4.4s, eval 30.7s, ok)

## Experiment 2 — exploration: explicit schedule and ordered calendar features

Hypothesis: departure hour/minute and ordered month/day representations let trees share nearby periods and distinguish minute-within-hour schedule patterns more easily than raw HHMM and unordered calendar categories. Add minute of day, hour, minute, numeric month/day/weekday, and day of year. Keep original features and the kept experiment-1 model parameters. The scikit-learn time-feature example above motivates alternative time representations; performance here must be established by the harness. Simplify category preparation by letting fixed pandas categories map unseen values to missing directly.

Outcome: **0.6755 Eval AUC**, **discard**, commit `38707e6`. Run time: 26.2s (training 4.8s, eval 21.4s, ok)

## Experiment 3 — exploration: individual-category splits

Hypothesis: native categorical partitions may group airports or calendar categories according to year-specific label noise. Set max_cat_to_onehot=512 so each categorical split isolates a single level, holding the kept experiment-1 features and other parameters fixed. Source: [XGBoost categorical splits](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html). Experiment 2 fell 0.0007 below the best despite faster preparation; discard under the strict keep rule.

Outcome: **0.6834 Eval AUC**, **keep**, commit `8035ce4`. Run time: 34.4s (training 3.2s, eval 31.2s, ok)

## Experiment 4 — ablation: remove day of month

Experiment 3 improved AUC from 0.6762 to 0.6834, supporting more constrained category handling. Hypothesis: DayofMonth permits fitting weather or disruption patterns specific to 2005; removing it may improve transfer to 2006 and simplify preparation. Change only this feature, retaining the other categories and experiment-3 parameters.

Outcome: **0.6815 Eval AUC**, **discard**, commit `355209b`. Run time: 30.2s (training 3.0s, eval 27.2s, ok)

## Experiment 5 — follow-up: more rounds for individual-category splits

The day-of-month ablation fell to 0.6815 and was discarded. Hypothesis: one-hot splits substantially reduce each tree's expressiveness, so 600 rounds may still underfit. Increase only n_estimators to 1200, keeping depth 6, learning rate 0.05 and regularization fixed. This follows the large gain from experiment 3, not the discarded partition-based calendar expansion.

Outcome: **0.6840 Eval AUC**, **keep**, commit `ce92ffa`. Run time: 36.4s (training 5.3s, eval 31.1s, ok)

## Experiment 6 — exploration: carrier-airport interactions

Experiment 5 improved AUC to 0.6840. Hypothesis: carrier-specific operations at an origin or destination can be captured more efficiently with explicit crossed categories than repeated deep splits. Add CarrierOrigin and CarrierDest, keeping all splits one-hot (threshold 10000). Read [TensorFlow feature-cross guidance](https://www.tensorflow.org/tutorials/structured_data/feature_columns) after searching its official documentation; the representation idea applies even though this model remains XGBoost. Replace repeated categorical masking with fixed-index lookups and Categorical.from_codes so unknown categories still become missing, while reducing per-row preparation overhead. No target statistics or row-count features are added.

Outcome: **0.6844 Eval AUC**, **keep**, commit `8ce9e54`. Run time: 28.3s (training 5.6s, eval 22.6s, ok)

Validation of experiment 6: loaded its saved artifact and confirmed exact equality of prepared features and labels for a 24-row training batch versus concatenated single-row calls. Unseen origin and carrier-origin categories map to missing.

## Experiment 7 — follow-up: deeper individual-category trees

Hypothesis: the constrained one-hot splits and useful carrier-airport crosses still leave multi-factor interactions underfit. Increase max_depth from 6 to 8, changing nothing else. This explicitly tests interaction capacity after experiments 3, 5, and 6 improved; retain child weight 20 and L2 penalty 10 to constrain small leaves.

Outcome: **0.6838 Eval AUC**, **discard**, commit `2956780`. Run time: 30.0s (training 7.1s, eval 22.9s, ok)

## Experiment 8 — exploration: geography inferred from route distances

Hypothesis: numerical airport coordinates inferred from the training route-distance graph let trees share regional effects among airports, unlike unrelated airport IDs. Fit an undirected graph from median route distances, use shortest paths to complete its distance matrix, then classical multidimensional scaling to obtain three coordinates per airport. Add origin/destination coordinates and their signed differences. These are approximate graph embeddings, not measured latitude/longitude. The training graph has 284 airports, 4290 directional route distances, and finite paths between every pair. No external geographic data or count features are used.

Sources read: [Isomap](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html) for shortest-path geometry and embedding, and [SciPy shortest_path](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html) for implementation. Fit every lookup once on training data; prepare only retrieves coordinates for each row. Retain the best depth-6 model after depth 8 failed.

Outcome: **0.6845 Eval AUC**, **keep**, commit `241a3f5`. Run time: 30.3s (training 6.4s, eval 23.8s, ok)

## Experiment 9 — follow-up: isolate minute within the hour

Experiment 8 improved rounded AUC by only 0.0001, so the embedding is retained under the stated keep rule but its evidence is weak. Hypothesis: the minute component of scheduled departures identifies recurring departure-bank patterns that raw HHMM cannot share across hours. Add only DepartureMinute. Unlike experiment 2, this introduces no new date/season feature and tests the timing idea on the stronger one-hot/crossed-category model. Source context: the earlier time-feature and flight-schedule research.

Outcome: **0.6841 Eval AUC**, **discard**, commit `24cd958`. Run time: 30.5s (training 6.5s, eval 24.1s, ok)

## Experiment 10 — ablation: simplify airport geometry

The isolated departure-minute feature failed (0.6841). Hypothesis: origin and destination coordinates provide regional context, while their three signed differences may be redundant with coordinates and distance and add variance. Remove the three RouteDirection features, keeping the six airport coordinates. This probes whether the marginal geographic gain can be retained or improved with simpler features.

Outcome: **0.6846 Eval AUC**, **keep**, commit `00b3cfb`. Run time: 29.9s (training 6.1s, eval 23.7s, ok)

## Synthesis after 10 experiments

Best: **0.6846**, commit `00b3cfb`, versus baseline 0.6743 (+0.0103). Six experiments were kept, four discarded; no crashes. The largest gain was constraining categorical splits to individual levels. Longer boosting helped this less expressive representation. Carrier-airport crosses helped modestly; inferred geography helped only marginally, and removing coordinate differences helped again. More depth, dropping day of month, and extra departure-minute/calendar features failed.

Current theory: stable airport/carrier effects matter, but flexible interactions can fit 2005-specific noise. Prefer controlled pooling and regularization over deeper trees or more date resolution. Next directions: leakage-safe smoothed categorical risk estimates, constraints on calendar interactions, and model averaging if individual models plateau.

Research refresh: searched for regularized target encodings and interaction constraints. [Pargent et al.](https://arxiv.org/abs/2104.00629) benchmark regularized target encoding; [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html) explain restricting spurious feature combinations. The [scikit-learn TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) emphasizes fitting encodings without a row's own target.

## Experiment 11 — exploration: leakage-safe smoothed target encodings

Hypothesis: numeric delay-risk estimates for airports, carriers, carrier-airport pairs, and routes permit useful pooling that individual-category splits learn inefficiently. Fit five lookup tables per feature, each excluding one deterministic feature-hash fold of the training rows. Each row selects the table excluding its own fold. The same feature-only hash and lookup rule runs on every evaluation row, so features are invariant to batch size and no training row contributes its own label. Shrink rates toward the training prior using strength 100. Internal group sample sizes are used only to fit means and shrinkage; counts are never exposed as model features. Keep the existing categorical features alongside these numeric estimates. No cross-validation model scores or extra evaluation metric are introduced.

Outcome: **0.6827 Eval AUC**, **discard**, commit `e6a8aab`. Run time: 35.4s (training 7.2s, eval 28.2s, ok)

## Experiment 12 — exploration: constrain exact-date interactions

Target encodings fell to 0.6827 and were discarded. Hypothesis: month and day-of-month interactions can identify particular 2005 dates and fit transient disruption patterns that will not recur in 2006. Keep both features, but constrain trees so no path can use both together. Every other feature can interact with either. This differs from removing day of month (which hurt): its main effect and non-month interactions remain available. Motivated by the XGBoost interaction-constraint guidance from the ten-experiment research refresh.

Outcome: **0.6822 Eval AUC**, **discard**, commit `9b1703c`. Run time: 30.2s (training 6.3s, eval 23.9s, ok)

## Experiment 13 — follow-up: stronger minimum leaf support

The explicit month/day interaction constraint hurt (0.6822), so hard exclusion appears too restrictive. Hypothesis: increase min_child_weight from 20 to 100 to reduce poorly supported interactions while allowing useful calendar combinations. All other parameters and features stay at the best commit. This changes the mechanism of regularization rather than repeating the failed feature removal or interaction ban; the parameter's role is described in the XGBoost reference read initially.

Outcome: **0.6846 Eval AUC**, **discard**, commit `2b29867`. Run time: 30.2s (training 6.2s, eval 24.0s, ok)

## Experiment 14 — exploration: aligned holiday proximity

The stronger leaf-support setting tied 0.6846 and was discarded without a compelling simplification. Research before this new feature category: [OPM holiday rules](https://www.opm.gov/policy-data-oversight/pay-leave/pay-administration/fact-sheets/holidays-work-schedules-and-pay/) give fixed and weekday-based dates. Also read [XGBoost boosted random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) as a potential subsequent direction.

Hypothesis: holiday travel effects align across 2005/2006 more reliably by relative holiday day than by day-of-month alone. Add signed distances within a two-week window of New Year, Memorial Day, Independence Day, Labor Day, Thanksgiving, and Christmas; outside each window use missing. Infer the year's January-1 weekday from the row's month/day/weekday, then apply holiday rules. Both dataset years are non-leap years. Do not add year, date identity, or other numeric calendar features, and do not read external calendar files.

Outcome: **0.6832 Eval AUC**, **discard**, commit `539607a`. Run time: 34.2s (training 9.5s, eval 24.7s, ok)

Holiday feature verification passed: batch/single-row features matched, and synthetic Thanksgiving rows for November 24, 2005 and November 23, 2006 both had zero holiday distance. Their lower AUC was therefore not due to these consistency bugs.

## Experiment 15 — exploration: boosted forests

Several feature and regularization changes have failed to beat 0.6846. Hypothesis: averaging three randomized trees per boosting step reduces variance of the learned interactions while retaining the successful representation. Change only num_parallel_tree to 3; keep the 1200 boosting rounds, learning rate 0.05, and existing row/column sampling. This is an ensemble-capacity change, not another feature tweak. Source read before implementation: [XGBoost boosted random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html). Expected training remains below the 60-second harness limit based on current fits.

Outcome: **0.6851 Eval AUC**, **keep**, commit `5c00033`. Run time: 45.6s (training 21.1s, eval 24.5s, ok)

## Experiment 16 — exploration: explicit route category

The boosted forest broke the plateau with AUC 0.6851. Hypothesis: an Origin-Dest crossed category lets the model isolate frequently observed route-specific effects more efficiently. Add Route to the fixed categorical dictionaries, retaining individual-category splits, leaf regularization, and the three-tree-per-round model. Unlike experiment 11's route risk estimate, this uses no target-derived preprocessing. The feature-cross research cited for experiment 6 motivates the representation.

Outcome: **0.6851 Eval AUC**, **discard**, commit `0109617`. Run time: 56.6s (training 23.8s, eval 32.8s, ok)

## Experiment 17 — follow-up: increase boosted-forest diversity

Adding a route category tied 0.6851 without simplifying, so it was discarded. Hypothesis: the gain from averaging three trees can be strengthened by decorrelating them. Reduce row subsampling from 0.85 to 0.65 and add colsample_bynode=0.8, while retaining colsample_bytree=0.9. This tests stronger stochastic regularization specifically in the kept boosted forest, following the forest documentation cited earlier.

Outcome: **0.6846 Eval AUC**, **discard**, commit `5ec8ada`. Run time: 49.0s (training 24.4s, eval 24.6s, ok)

## Experiment 18 — exploration: departures relative to group schedules

The more randomized forest fell to 0.6846 and was discarded. Hypothesis: a departure's position relative to its route/carrier-airport schedule can capture operational context beyond absolute clock time. Fit median scheduled minutes-of-day for Route, CarrierOrigin, and CarrierDest on train, then subtract those fixed medians inside prepare. This uses the allowed lookup pattern illustrated in program.md and adds no group counts. Research check: [scikit-learn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) reinforces learning preprocessing statistics only on training data. Unseen keys receive missing values.

Outcome: **0.6845 Eval AUC**, **discard**, commit `ff3efb2`. Run time: 47.3s (training 22.0s, eval 25.3s, ok)

## Plateau research after experiment 18

Experiments 16–18 were three consecutive discards within 0.001 of the best. Paused before editing and searched for alternatives to uniform-depth growth and for histogram split limitations. Read [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) and relevant parameter excerpts, and reviewed the abstract of the [original XGBoost paper](https://arxiv.org/abs/1603.02754). New candidates: allocate leaves by split gain, and test finer numerical bins. These alter the learner's structure or split resolution rather than adding more correlated features.

## Experiment 19 — exploration: loss-guided trees with a leaf budget

Hypothesis: one-hot categorical conditions sometimes require long unbalanced paths, but increasing every branch's depth (experiment 7) added noise. Use grow_policy=lossguide, max_leaves=31, and unlimited depth, retaining the existing boosted forest and regularization. A fixed leaf budget can allow useful longer paths while bounding tree size. The explicit hist method matches the previous auto setting.

Outcome: **0.6843 Eval AUC**, **discard**, commit `c5c9c9c`. Run time: 55.4s (training 29.8s, eval 25.6s, ok)

## Experiment 20 — exploration: finer histogram resolution

The loss-guided model trained within the cap (28.7 s fit) but fell to 0.6843. Continued the plateau research by opening [A Case for Library-Level k-Means Binning in Histogram Gradient-Boosted Trees](https://arxiv.org/abs/2505.12460); it discusses useful split boundaries lost by quantile binning. We do not implement its k-means method. Instead, test the simpler related hypothesis that increasing max_bin from 256 to 1024 preserves useful boundaries in the 1162 departure-time values, 1267 distance values, and airport coordinates. Keep the best depth-6 boosted forest unchanged otherwise.

Outcome: **0.6852 Eval AUC**, **keep**, commit `39f066b`. Run time: 46.1s (training 21.2s, eval 24.8s, ok)

## Synthesis after 20 experiments

Best: **0.6852**, commit `39f066b`, +0.0109 over baseline. Experiments 11–20 kept only the boosted forest and finer histogram bins; eight were discarded, including two exact ties with extra complexity or no clear simplification. No crashes or timeouts. Feature engineering after the carrier-airport and modest spatial gains has mostly added variance rather than information. Hard calendar-interaction constraints were too restrictive, while unconstrained loss-guided growth also failed. More randomized forests did not beat moderate existing sampling.

Current theory: the remaining useful gains may come from balancing different interaction complexities and averaging their errors, rather than adding correlated inputs. Retain precise numerical boundaries and conservative individual-category splits. Research refresh: searched [scikit-learn gradient boosting](https://scikit-learn.org/stable/modules/ensemble.html#gradient-boosting) for interaction order, and [soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) for probability averaging. Next test a lower-interaction model, then assess whether a heterogeneous ensemble helps; all constituents must fit on training data within the shared per-run cap.

## Experiment 21 — exploration: shallower trees with more rounds

Hypothesis: depth-4 trees with 2400 boosting rounds can capture stable lower-order effects more smoothly than depth-6 trees with 1200 rounds. The extra rounds compensate for lower per-tree capacity. Keep three trees per round, learning rate 0.05, 1024 bins, and all other settings. This tests a distinct bias/variance profile and may provide an ensemble complement even if the standalone score does not win.

Outcome: **0.6848 Eval AUC**, **discard**, commit `38d1c76`. Run time: 58.9s (training 33.8s, eval 25.1s, ok)

## Experiment 22 — follow-up: average shallow and deeper models

The depth-4 forest scored 0.6848, close to the depth-6 best of 0.6852, suggesting a possible complementary predictor. Hypothesis: an equal probability average combines lower-order stability with higher-order interaction capacity. Keep the depth-6 three-tree forest as one constituent; add a depth-4, 2400-round model with one tree per round and a fixed seed of 17. Reducing the shallow constituent's parallel-tree count gives comfortable training headroom relative to the measured 20.2 + 32.7 s of the full forests. Both models fit only train.csv, serially, and only the combined artifact receives harness evaluation. Use scikit-learn VotingClassifier soft voting, as researched at the 20-experiment synthesis.

Outcome: **0.6852 Eval AUC**, **discard**, commit `5a7f06c`. Run time: 55.0s (training 29.8s, eval 25.2s, ok)

## Experiment 23 — ablation: remove inferred geography

The heterogeneous probability average tied 0.6852 but added a second model, so it was discarded. Hypothesis: the geographic embedding's early 0.0002 aggregate gain may be unnecessary after introducing boosted forests and finer bins. Remove all six coordinate features and their fitted embedding machinery, while retaining base categories and carrier-airport crosses. Equal AUC would qualify as a meaningful simplification; any decrease still requires discard.

Outcome: **0.6846 Eval AUC**, **discard**, commit `729aa5f`. Run time: 43.6s (training 20.3s, eval 23.4s, ok)

## Plateau research after experiment 23

Three more near-best discards prompted fresh research. Read [XGBoost monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) and the search excerpts/abstract of [Fleurquin et al. on delay propagation](https://www.nature.com/articles/srep01159). The latter motivates considering within-day accumulation and overnight reset; it does not establish a universal monotonic rule. Our own training summaries showed a strong rise from early morning to evening, followed by a late-night decline.

## Experiment 24 — exploration: constrain the daytime delay trend

Hypothesis: a monotonic daytime clock reduces spurious local time effects while a separate nighttime feature preserves the observed late-night pattern. Replace CRSDepTime with scheduled minutes clipped to 06:00–20:00 and require an increasing model response to that feature. Add an unconstrained NightDepartureTime only outside that interval (missing during daytime). Thus nighttime behavior can differ without allowing an unconstrained daytime clock to bypass the constraint. Retain 1024 bins, which also addresses the documented interaction between histogram resolution and monotonic constraints.

Outcome: **0.6850 Eval AUC**, **discard**, commit `73926df`. Run time: 55.5s (training 29.4s, eval 26.1s, ok)

## Experiment 25 — exploration: L1 shrinkage of weak leaf updates

The daytime constraint was a near miss at 0.6850. With the plateau continuing, refreshed the XGBoost L1 parameter definition and searched the original DART paper for another regularization direction. Hypothesis for this trial: reg_alpha=10 suppresses weak residual leaf updates without banning calendar interactions or requiring much larger leaves. This differs from the min_child_weight trial because it penalizes leaf weights rather than split support. Keep all best features and other hyperparameters. Source: [XGBoost regularization parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

Outcome: **0.6850 Eval AUC**, **discard**, commit `adceff9`. Run time: 53.7s (training 28.6s, eval 25.1s, ok)

## Experiment 26 — exploration: dropout boosting

L1 regularization was another near miss (0.6850). Read the [DART paper abstract](https://arxiv.org/abs/1505.01866) and [XGBoost dropout tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html). Hypothesis: dropout may reduce late-tree overspecialization more effectively than leaf penalties. Use 300 rounds, one tree per round, learning rate 0.15, rate_drop=0.03, and skip_drop=0.8. This limits the expensive repeated predictions required during dropout training; it deliberately changes the boosting regime rather than making a cosmetic tuning change. Features and other regularization remain at the best commit.

Outcome: **0.6838 Eval AUC**, **discard**, commit `b28222c`. Run time: 82.0s (training 58.5s, eval 23.4s, ok)

## Experiment 27 — exploration: cyclic month representation

Dropout completed just within the training cap (58.5 s including startup) but scored 0.6838, so it was discarded. Refreshed the [time-feature tutorial's trigonometric section](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) during the continuing plateau. Hypothesis: replacing the unordered month category with sine/cosine coordinates changes the seasonal sharing bias and may reduce year-specific month effects. Unlike experiment 2, this replaces a representation rather than appending numeric calendar precision, and adds no day-of-year or day-of-month interactions beyond the original model's available inputs.

Outcome: **0.6847 Eval AUC**, **discard**, commit `d9de5f4`. Run time: 47.2s (training 21.9s, eval 25.3s, ok)

## Experiment 28 — exploration: landmark-distance geographic representation

Cyclic month replacement fell to 0.6847. During the continuing plateau, searched primary literature on landmark Isomap and revisited the training-graph representation. Hypothesis: distances to reference airports offer nonlinear regional partitions that a three-dimensional MDS projection may obscure, especially when remote airports influence its axes. Replace the six MDS coordinates with origin/destination shortest-path distances to LAX, JFK, MIA, and SEA. These are reference IDs observed in train, not imported coordinates. Remove the eigendecomposition; fit all distances from train's route-distance graph. This is a new geographic basis rather than adding another calendar feature. The graph-distance reasoning follows the Isomap documentation cited in experiment 8.

Outcome: **0.6850 Eval AUC**, **discard**, commit `cf59fbc`. Run time: 46.7s (training 21.7s, eval 25.0s, ok)

The landmark research also found the original [de Silva and Tenenbaum landmark-Isomap paper](https://proceedings.neurips.cc/paper_files/paper/2002/file/5d6646aad9bcc0be55b2c82f69750387-Paper.pdf). Our trial used raw landmark distances as a different tree basis, not that paper's full embedding algorithm.

## Experiment 29 — exploration: constrained grouping for high-cardinality categories

Landmark distances were a near miss at 0.6850. Refreshed the categorical partitioning tutorial and max_cat_threshold definition during the plateau. Hypothesis: the early all-one-hot gain need not imply that every high-cardinality feature should prohibit pooling. Set max_cat_to_onehot=32 so month/day/weekday/carrier keep individual-category splits, while airports and carrier-airport pairs use partitioning with max_cat_threshold=4. This narrowly limits split candidates, unlike the baseline's broad partitions (threshold 64), and may share reliable airport effects more efficiently. Source: [XGBoost categorical parameters](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature).

Outcome: **0.6818 Eval AUC**, **discard**, commit `2a0defc`. Run time: 52.3s (training 27.4s, eval 24.9s, ok)

## Experiment 30 — ablation: remove the last third of boosting rounds

Even narrowly constrained high-cardinality grouping hurt substantially (0.6818), reaffirming the one-hot representation. Hypothesis: after forest averaging and finer bins, some of the later residual corrections may be unnecessary or fit noise. Reduce rounds from 1200 to 800 while keeping the learning rate and all other settings fixed. This is a simplification test of the current stronger model, distinct from the early 600-to-1200 comparison before forest averaging and geography. Equal rounded AUC qualifies for keeping because it removes 1200 trees and reduces fit/prediction work.

Outcome: **0.6852 Eval AUC**, **keep**, commit `dc9e866`. Run time: 39.4s (training 14.9s, eval 24.5s, ok)

## Synthesis after 30 experiments

Best rounded AUC remains **0.6852**, now at the simpler commit `dc9e866`. Experiment 30 removed one third of the boosting rounds with no AUC loss: harness training fell from 21.2 s to 14.9 s and the artifact from 8.8 MB to 6.4 MB. Experiments 21–29 all failed the keep rule, including a tie from a larger heterogeneous ensemble. No crashes or timeouts; dropout came closest to the training cap at 58.5 s.

Evidence favors the existing one-hot representation, carrier-airport crosses, and modest MDS geography. Neither deeper/adaptive growth, alternate geographic or seasonal bases, stronger leaf penalties, monotonic time constraints, nor dropout improved on it. The most useful recent result is simplification. The small AUC differences remain within a narrow range, so next focus on purposeful sampling/boosting changes and further ablations rather than piling on features.

Research refresh: searched XGBoost's documentation for column sampling/feature weights and learning-rate scheduler callbacks. Candidate directions: always expose the dominant departure-time feature by disabling column sampling, and compare a decaying step schedule at similar total learning-rate budget.

## Experiment 31 — follow-up: use all features in each tree

Hypothesis: with only 16 inputs, several being related geographic coordinates, per-tree column sampling can omit the dominant departure-time predictor unnecessarily. Set colsample_bytree from 0.9 to 1.0 while retaining row sampling and three-tree averaging. This contrasts with experiment 17's unsuccessful stronger randomization and isolates whether feature availability is the limiting factor. Source: [XGBoost column-sampling parameters](https://xgboost.readthedocs.io/en/stable/parameter.html).

Outcome: **0.6849 Eval AUC**, **discard**, commit `8772057`. Run time: 40.0s (training 15.9s, eval 24.1s, ok)

## Experiment 32 — exploration: independent boosting trajectories

Removing column sampling fell to 0.6849. Hypothesis: averaging independently boosted models can reduce different residual errors than averaging three trees inside each shared boosting step. Replace the 800-round, three-tree forest with an equal soft vote of three 800-round, one-tree models, using fixed seeds 42, 17, and 2026. The total tree budget remains 2400; all models fit the same permitted training data with the existing row/column sampling. This is not a seed sweep: only the predetermined combined artifact is evaluated. Source: the soft-voting documentation researched at experiment 22.

Outcome: **0.6851 Eval AUC**, **discard**, commit `92a6bc4`. Run time: 35.9s (training 11.8s, eval 24.2s, ok)

## Experiment 33 — exploration: cosine learning-rate decay

Independent boosting trajectories were a near miss at 0.6851. Hypothesis: larger early steps and smaller late steps learn broad signal efficiently while reducing noisy late corrections. Over 800 rounds, use a cosine schedule from 0.08 to 0.02, with mean approximately 0.05, preserving the constant-rate model's overall learning-rate budget. The initial rate is 0.08 and a fresh LearningRateScheduler is constructed for this fit. Read the [callback API](https://xgboost.readthedocs.io/en/stable/python/python_api.html#xgboost.callback.LearningRateScheduler) during the preceding run; no validation set or early-stopping metric is introduced.

Outcome: **0.6850 Eval AUC**, **discard**, commit `88fb9c6`. Run time: 39.0s (training 14.8s, eval 24.2s, ok)

## Experiment 34 — follow-up: smaller constant steps at matched boosting budget

The cosine schedule scored 0.6850. Three near-best discards (31–33) prompted a search for Friedman's original stochastic-gradient-boosting work and another check of the shrinkage rationale. Hypothesis: a constant rate of 0.025 with 1600 rounds can make less noisy greedy updates than 0.05 with 800 rounds, without the large initial steps in the failed cosine schedule. The product of rounds and learning rate stays 40, and three-tree averaging is retained. This distinguishes discretization of boosting from its overall duration. Initial XGBoost tuning guidance explicitly recommends pairing a smaller step with more rounds.

Outcome: **0.6852 Eval AUC**, **discard**, commit `0ad34f0`. Run time: 53.9s (training 28.5s, eval 25.4s, ok)

The shrinkage research returned [Friedman's stochastic gradient boosting paper](https://www.sciencedirect.com/science/article/pii/S0167947301000652) and his [author-hosted discussion of shrinkage](https://jerryfriedman.su.domains/ftp/machine.pdf). The smaller-step trial tied AUC but used twice as many trees, so it was discarded.

Retained artifact verification: `dc9e866` produces exactly equal features and labels for a reordered, noncontiguous training batch versus individual rows. Synthetic unseen origin, destination, and carrier values map to missing in all five relevant categorical features and all six coordinate features. No new model score was computed in this check.

## Experiment 35 — ablation: retain only the carrier-origin cross

Hypothesis: the carrier-origin cross captures local departure operations, while the carrier-destination cross may add little beyond destination ID and geography. Remove only CarrierDest, preserving CarrierOrigin and all base features. An exact AUC tie would qualify for keeping because both the feature set and preparation become simpler.

Outcome: **0.6854 Eval AUC**, **keep**, commit `b816657`. Run time: 36.3s (training 15.6s, eval 20.7s, ok)

## Experiment 36 — ablation: two-dimensional airport embedding

Removing CarrierDest broke the plateau: **0.6854**, commit `b816657`, with one fewer feature. Inspecting the retained model's tree gain totals (not a new predictive score) also showed both Coordinate0 features below the other coordinate axes. Hypothesis: the smallest retained MDS eigencomponent adds more noise than useful geography. Keep only the two largest eigencomponents, reducing endpoint coordinate features from six to four. Retain the successful carrier-origin-only representation and model settings. Equality would qualify as a feature simplification.

Outcome: **0.6856 Eval AUC**, **keep**, commit `8ac2c82`. Run time: 34.7s (training 14.3s, eval 20.4s, ok)

## Experiment 37 — ablation: origin geography only

The two-dimensional embedding improved AUC to **0.6856** and reduced evaluation to 20.4 s. Together with removing CarrierDest, the recent gains suggest that some destination-context features may add variance. Hypothesis: origin coordinates carry the more direct regional signal for departure delays, while destination ID and flight distance already provide sufficient destination context. Remove only the two destination coordinate features; keep the complete training graph for fitting origin coordinates. This is a targeted follow-up to two successful simplifications, not a blanket removal of geography.

Outcome: **0.6856 Eval AUC**, **keep**, commit `c4328a2`. Run time: 34.2s (training 14.2s, eval 20.0s, ok)

## Experiment 38 — follow-up: more averaging on the simpler feature set

Origin-only coordinates tied **0.6856**, so the simpler 11-feature model is retained (`c4328a2`). Hypothesis: increasing num_parallel_tree from 3 to 7 reduces variance now that weaker features have been removed. Keep 800 rounds and all other parameters fixed. This follows experiment 15's benefit from adding per-round averaging, and differs from experiment 32's unsuccessful independent boosting trajectories. The projected fit time, scaled from roughly 14 s, remains below the training cap; a tie would be discarded because it adds trees.

Outcome: **0.6856 Eval AUC**, **discard**, commit `b7b05d3`. Run time: 52.2s (training 30.9s, eval 21.3s, ok)

## Experiment 39 — exploration: stronger L2 leaf shrinkage

Seven trees per round tied 0.6856 at substantially greater model size and training cost, so it was discarded. Hypothesis: increasing reg_lambda from 10 to 100 shrinks weakly supported leaf updates continuously, without removing candidate splits as a higher child-weight threshold does or zeroing small updates as L1 can. Keep the current 11 features, 800 rounds, and three-tree averaging. This is an order-of-magnitude regularization test on the newly simplified representation, grounded in the XGBoost leaf-weight regularization described in the parameter reference and original paper.

Outcome: **0.6859 Eval AUC**, **keep**, commit `cabaa53`. Run time: 34.7s (training 14.5s, eval 20.2s, ok)

## Experiment 40 — follow-up: more rounds with stronger L2 shrinkage

L2 regularization of 100 improved AUC to **0.6859**, commit `cabaa53`. Hypothesis: stronger shrinkage of smaller leaves can benefit from more boosting rounds before overfitting. Increase rounds from 800 to 1600, retaining the 0.05 learning rate and stronger L2 penalty. This tests duration under the newly successful regularization regime, unlike experiment 34's unchanged total boosting budget or experiment 30's weaker-regularization simplification. Expected training remains well under 60 s based on the measured 14.5 s run phase.

Outcome: **0.6861 Eval AUC**, **keep**, commit `dad6840`. Run time: 48.8s (training 27.9s, eval 20.9s, ok)

## Synthesis after 40 experiments

Best: **0.6861**, commit `dad6840`, versus 0.6743 baseline (+0.0118). The last ten experiments produced five keeps: remove CarrierDest (0.6854), reduce geography to two dimensions (0.6856), remove destination coordinates at equal AUC (0.6856), then stronger L2 shrinkage (0.6859) and additional rounds under that shrinkage (0.6861). Other averaging and learning-rate changes failed to beat the current best. No experiment crashed or timed out.

Current theory: compact departure-relevant features plus stronger smooth leaf regularization transfer better across years. Extra destination context and weak geographic components added variance. Stronger L2 makes a longer boosting trajectory useful, whereas longer training under weaker regularization was redundant. The retained model has 11 features, individual-category splits, a carrier-origin cross, two origin coordinates inferred from training route distances, and a three-tree forest per boosting round.

Research refresh: searched the official [feature-weight sampling example](https://xgboost.readthedocs.io/en/latest/python/examples/feature_weights.html). A remaining hypothesis is to weight column sampling toward the strongly supported departure-time signal and away from fine calendar effects while still allowing those effects. This is more selective than the unsuccessful no-column-sampling trial or hard calendar-interaction restriction.

## Experiment 41 — exploration: weighted feature sampling

At the loop clock check, 2m15s remained. Hypothesis: preserve random column selection but favor the strongest stable signal, departure time, over fine calendar effects. Set sampling weights to 4 for CRSDepTime, 0.5 for Month and DayofMonth, and 1 for every other feature. Keep the best 1600-round, L2=100 forest. This retains all features and their permitted interactions, unlike the unsuccessful hard exclusions. Based on the official feature-weight sampling example read for the 40-experiment synthesis. The expected approximately 50-second run fits within the remaining wall-clock budget.

Outcome: **0.6863 Eval AUC**, **keep**, commit `6826f09`. Run time: 48.2s (training 27.0s, eval 21.2s, ok)

## Final summary

- Best Eval AUC: **0.6863**, commit `6826f09` on branch `oct6`.
- Baseline: 0.6743 at `b15ec66`; absolute improvement **0.0120** (1.20 AUC percentage points).
- Completed **41 non-baseline experiments plus the baseline**: 15 experimental keeps, 26 discards, zero crashes/timeouts.
- Best artifact: `artifacts/6826f09dcc6587cb522448ae153363ec9a46627e.pkl` (13.6 MB), saved by the harness and matched to the clean branch HEAD.
- Final run: Run time: 48.2s (training 27.0s, eval 21.2s, ok)

The retained model uses 1600 boosting rounds with three depth-6 trees per round, learning rate 0.05, 1024 numerical bins, min_child_weight 20, L2 penalty 100, row sampling 0.85, and column sampling 0.9. Categorical splits isolate individual levels. Feature sampling favors scheduled departure time (weight 4), downweights month/day of month (0.5), and leaves other weights at 1.

Its 11 features are the eight original inputs, a carrier-origin category, and two origin-airport coordinates inferred solely from the training route-distance graph. Fixed training category levels handle unseen values as missing. All row transformations stay in prepare; its fitted lookups require no file reads during scoring.

What worked: individual-category splits produced the main early gain. More regularized boosting, modest carrier-origin/geographic context, and per-round tree averaging helped. Later gains came from removing CarrierDest, the weakest geographic axis, and destination coordinates, followed by stronger L2 shrinkage, longer boosting under that shrinkage, and selective feature-sampling weights.

What did not work: broad added calendar/departure features, holiday proximity, route categories, target-risk encodings, schedule-relative times, harder calendar interaction restrictions, deeper or loss-guided trees, alternate geography, cyclic month replacement, stronger random sampling, L1 penalties, monotonic daytime constraints, dropout, alternative learning-rate paths, and larger or independently trained ensembles. Some matched AUC but were discarded because they added complexity. The 800-round and origin-only-geography ties were kept when they simplified the model.

Validation: the final saved artifact passed exact batch-versus-single-row preparation checks. The same retained preparation logic was also checked on reordered rows and synthetic unseen airports/carriers. The final evaluation call remains last in train.py; harness.py and program.md are unchanged; the working tree is clean. Only harness Eval AUC determined keep/discard decisions.

Next ideas: isolate which feature-sampling weights produced the last gain, test whether a shorter trajectory can preserve the strongly regularized weighted model's AUC, and investigate a lower-variance train-only encoding of carrier-origin interactions. Any continuation should begin as a fresh timed run rather than extending this clock.

The harness reported less than two minutes remaining after experiment 41, so no further experiments were started. The experiment clock is stopped immediately after this summary and verification.
