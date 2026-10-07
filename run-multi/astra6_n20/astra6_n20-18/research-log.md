# Experiment oct7 — 2026-10-07

Objective: maximize the harness's four-decimal eval AUC for 15-minute departure delays. Training data is 200,000 balanced 2005 flights; evaluation is handled only by the unchanged harness. The run starts at baseline commit `b15ec66` and has a one-hour wall-clock budget. Only `train.py` is modified and committed. All features must have identical meaning on one row and on a batch.

## Initial research

- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): smaller learning steps require more trees; tree depth, minimum child weight, regularization, and sampling control variance. Explore a longer, regularized boosting schedule before adding interactions.
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): use `min_child_weight` and categorical split limits to constrain sparse splits. The installed XGBoost is 3.4.1, so use stable-version behavior rather than development defaults.
- [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html): native categorical partitions can group similar categories; training-fitted category levels must remain consistent at inference.
- [Scikit-learn time feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html): calendar/time representations and interactions are candidates for later experiments. Do not adopt the example's evaluation protocol; all scoring here remains in the harness.

Training-only inspection: nine columns, no missing values; dates are strings such as `c-11`, scheduled departure uses HHMM, 20 carriers and 283 origin/destination airport levels. Counts are diagnostics only and will not be model features. Across-year shift makes high-complexity calendar memorization a concern.

## Baseline — b15ec66

Unchanged starter: 100 trees, depth 6, learning rate 0.1, six native categorical features and two numeric features. Run via the harness before any modeling edits.

Baseline result: **0.6743**, training 1.5s, evaluation 30.7s; kept.

## Experiment 1 — exploration: longer regularized boosting

Hypothesis: the starter has insufficient boosting capacity; 400 trees at learning rate 0.05 can improve ranking while minimum child weight 20, L2 penalty 10, and 80% row sampling protect against sparse categorical patterns. Motivated by the XGBoost tuning guide above. Keep the original feature representation to separate modeling capacity from feature engineering.

Result: `75144bb` — **0.6758**, **keep**. Run time: 34.2s (training 3.3s, eval 30.9s, ok) Previous kept AUC: 0.6743.

## Experiment 2 — exploration: airline/network interactions

Hypothesis: explicit route, carrier-origin, and carrier-destination categories expose stable network/operational differences at shallower tree levels. [Systemic delay propagation in the US airport network](https://pmc.ncbi.nlm.nih.gov/articles/PMC3557445/) motivates airline connectivity and scheduling as relevant mechanisms; these static pairs are a hypothesis adapted to the available inputs, not direct measurements of congestion. Fit category levels only on train and use the same row-local concatenations in prepare. No frequency/count features.

Result: `04bd2b0` — **0.6686**, **discard**. Run time: 73.4s (training 6.0s, eval 67.5s, ok) Previous kept AUC: 0.6758.

Interpretation of experiment 2: high-cardinality route/airline interactions hurt cross-year generalization and more than double evaluation cost. Reverted to the regularized original features.

## Experiment 3 — ablation: remove day-of-month

Hypothesis: day-of-month enables memorizing 2005 weather/date effects that do not recur on the same dates in 2006. Removing it leaves month, weekday, schedule, carrier, airports, and distance to model more transferable structure. This tests a specific suspected source of temporal overfitting rather than increasing capacity further.

Result: `1756d97` — **0.6761**, **keep**. Run time: 30.2s (training 3.1s, eval 27.1s, ok) Previous kept AUC: 0.6758.

## Experiment 4 — simplification: reuse fixed categorical dtypes

Hypothesis: removing repeated category validation and redundant membership masking preserves every feature value while reducing row-at-a-time evaluation overhead. [Pandas categorical documentation](https://pandas.pydata.org/docs/user_guide/categorical.html) shows that a fixed CategoricalDtype preserves levels and maps unknown values to missing. Construct the output DataFrame once. Keep on an equal AUC only if measurably faster.

Result: `160e851` — **0.6761**, **keep**. Run time: 12.4s (training 3.1s, eval 9.3s, ok) Previous kept AUC: 0.6761.

Experiment 4 observation: eval fell from 27.1s to 9.3s with identical four-decimal AUC, so retained under the equal-score speed rule. Pandas emits deprecation warnings for unknown categories; current behavior is correct but explicit category codes are a possible later cleanup.

## Experiment 5 — exploration: one-category splits

Hypothesis: arbitrary category partitions can overfit airport/carrier combinations across years. Force native one-hot splits with max_cat_to_onehot=1024 while keeping the model size and features fixed; this tests whether individually regularized category effects transfer better. Based on the XGBoost categorical tutorial and parameter reference cited above.

Result: `65f3d4a` — **0.6807**, **keep**. Run time: 11.6s (training 2.3s, eval 9.3s, ok) Previous kept AUC: 0.6761.

## Experiment 6 — follow-up: more rounds with one-hot categories

Hypothesis: the one-hot improvement (+0.0046) indicates category partitions were harming transfer, but one-at-a-time airport effects need more boosting rounds. Increase 400 to 1200 trees with all other parameters fixed. This tests underfitting in the newly successful split strategy, not a random change of learning rate.

Result: `00117dd` — **0.6818**, **keep**. Run time: 14.7s (training 5.2s, eval 9.6s, ok) Previous kept AUC: 0.6807.

## Experiment 7 — follow-up: deeper one-hot trees

Hypothesis: native one-hot trees spend depth on individual airport tests; increasing depth 6 to 8 may capture carrier, airport, and departure-time interactions more efficiently now that category partitions are disabled. Keep 1200 rounds and the successful regularization unchanged to isolate depth. The longer schedule improved AUC to 0.6818, supporting additional capacity exploration.

Result: `c4862ef` — **0.6803**, **discard**. Run time: 16.2s (training 6.2s, eval 10.0s, ok) Previous kept AUC: 0.6818.

## Experiment 8 — ablation: shallower one-hot trees

Hypothesis: the depth-8 decline to 0.6803 suggests cross-year variance, not missing interactions, now limits performance. Reduce depth from the kept 6 to 4 at the same 1200 rounds to regularize interaction order. This deliberately tests the opposite side of the capacity tradeoff after the deeper model failed.

Result: `c5ae35d` — **0.6811**, **discard**. Run time: 13.6s (training 4.2s, eval 9.4s, ok) Previous kept AUC: 0.6818.

## Experiment 9 — exploration: departure hour and minute

Hypothesis: scheduled hour and minute-within-hour expose schedule-bank structure more directly than raw HHMM. Keep raw departure time and add these two deterministic per-row features. Motivated by the scikit-learn time-feature example and the schedule/propagation research above. Also replace deprecated unknown-category conversion with fixed-index codes; this is intended to preserve categorical values exactly and avoids repeated warnings.

Result: `91c6ef4` — **0.6813**, **discard**. Run time: 12.5s (training 5.5s, eval 7.0s, ok) Previous kept AUC: 0.6818.

### Plateau research after experiment 9

The last three modeling experiments did not beat 0.6818. [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) offer structural regularization: restrict which features share a tree path instead of changing all trees uniformly. [Monotonic constraints](https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html) offer shape restrictions, but strictly increasing HHMM would mishandle overnight departures; defer that approach until time is represented appropriately.

## Experiment 10 — exploration: additive seasonality

Hypothesis: an additive month effect can retain broad seasonality while removing 2005-specific month-by-airport/weather interactions. Put Month in its own interaction-constraint group and all other features in a separate group. Disjoint groups intentionally avoid the union behavior of overlapping constraint groups. Keep current depth and regularization unchanged.

Result: `5b4f31b` — **0.6840**, **keep**. Run time: 15.8s (training 6.2s, eval 9.6s, ok) Previous kept AUC: 0.6818.

## Synthesis after 10 experiments

Best: **0.6840**, commit `5b4f31b`, versus baseline 0.6743. Stable individual-category splits and additive seasonality helped most. More boosting rounds helped modestly; adding route categories, changing depth either way, and separating departure hour/minute hurt. Removing day-of-month helped slightly. Fixed dtypes cut evaluation from ~27s to ~9s at identical AUC. Current theory: cross-year transfer benefits from smooth/shared effects and restricting opportunistic categorical/calendar interactions.

Research refresh: [XGBoost boosted random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) explains num_parallel_tree within each boosting step. [Scikit-learn gradient boosting regularization](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_regularization.html) motivates combining shrinkage with stochastic sampling to reduce variance. Future directions: further calendar ablations, larger minimum leaves, and variance reduction through parallel trees; then train-fitted schedule medians as compact alternatives to route categories.

## Experiment 11 — follow-up: additive weekday effects

Hypothesis: experiment 10 improved by removing seasonal interactions; extending the same restriction to weekday may suppress accidental calendar-specific carrier/airport interactions. Put weekday in its own group, keeping month additive and the remaining five operational features interactive.

Result: `ebc22d8` — **0.6819**, **discard**. Run time: 14.8s (training 5.1s, eval 9.8s, ok) Previous kept AUC: 0.6840.

## Experiment 12 — follow-up: larger minimum leaves

Hypothesis: sparse airport/time/weekday leaves still overfit even after month is additive. Raise min_child_weight from 20 to 100, retaining depth 6 and the complete interaction set that beat the additive-weekday ablation. Unlike reducing depth, this selectively suppresses low-support leaf splits. Based on XGBoost parameter documentation.

Result: `3caaedd` — **0.6836**, **discard**. Run time: 15.1s (training 5.1s, eval 10.0s, ok) Previous kept AUC: 0.6840.

## Experiment 13 — simplification: explicit categorical codes only

Hypothesis: retain the efficient category-code conversion from discarded experiment 9 without its harmful time features. Fixed training category indices map unseen values to -1/missing, avoid deprecated Pandas behavior, and should further reduce preprocessing overhead. All feature values and model parameters stay identical; require exact feature equivalence and equal AUC with faster runtime.

Result: `6f0afce` — **0.6840**, **keep**. Run time: 11.0s (training 5.1s, eval 5.9s, ok) Previous kept AUC: 0.6840.

## Experiment 14 — exploration: boosted small forests

Hypothesis: averaging four stochastic trees at each boosting step reduces noisy updates while retaining the best model's depth and additive seasonality. Set num_parallel_tree=4 and colsample_bynode=0.8, preserving 1200 rounds and 80% row sampling. Based on XGBoost's boosted-random-forest tutorial. Expect higher training cost, still comfortably under 60s based on current ~5s training.

Result: `abcb5db` — **0.6844**, **keep**. Run time: 31.7s (training 24.4s, eval 7.4s, ok) Previous kept AUC: 0.6840.

## Experiment 15 — exploration: airport geography inferred from train distances

Hypothesis: two continuous airport-location coordinates allow nearby airports to share effects more efficiently than independent categories. Inspired by [Isomap/geodesic embeddings](https://scikit-learn.org/stable/modules/manifold.html#isomap) and [SciPy shortest paths](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html). Fit an undirected graph from median route Distance values in train only, complete distances by shortest paths, and use classical distance embedding into two coordinates. Training-only inspection confirmed all 284 airports are connected. Coordinates are approximate learned geometry, not external geolocation. Add origin and destination coordinates to the operational interaction group; retain additive month. No row counts, target encodings, or external data.

Result: `86f0c6c` — **0.6850**, **keep**. Run time: 34.3s (training 26.2s, eval 8.1s, ok) Previous kept AUC: 0.6844.

## Experiment 16 — ablation: smaller boosted forests

Hypothesis: two trees per boosting step may retain the variance reduction of four while halving the main training cost, leaving capacity for useful engineered features. Keep learned airport geography, additive month, and all other parameters fixed. Permit an equal AUC only if training is faster. This is an explicit simplification of the successful forest experiment, not a seed search.

Result: `24fff19` — **0.6847**, **discard**. Run time: 20.9s (training 13.8s, eval 7.0s, ok) Previous kept AUC: 0.6850.

## Experiment 17 — exploration: recurring holiday timing

Hypothesis: distance to major travel holidays transfers across years more reliably than raw day-of-month. Use [OPM holiday rules](https://www.opm.gov/faq/payleave/what-are-federal-holidays.ashx) for New Year, Memorial Day, Independence Day, Labor Day, Thanksgiving, and Christmas. Infer the weekday of January 1 from each row's month/day/weekday (both dataset years are non-leap), then compute signed and absolute distance to the nearest holiday, clipped at 14 days. Include these only in the calendar interaction group with Month. Rules are deterministic and use no target or external data files.

Result: `30b31f1` — **0.6843**, **discard**. Run time: 37.5s (training 27.6s, eval 10.0s, ok) Previous kept AUC: 0.6850.

## Experiment 18 — simplification/follow-up: shared coarse holiday phase

Hypothesis: experiment 17's detailed offsets with Month can reconstruct noisy calendar dates. Replace them with four states: within three days before, holiday itself, within three days after, or away from a holiday. Put this feature in its own additive group, sharing the response across all months. This sharply reduces degrees of freedom while testing the recurring travel-demand hypothesis. Reuse the verified holiday arithmetic from experiment 17.

Result: `3dabc7e` — **0.6854**, **keep**. Run time: 35.6s (training 26.0s, eval 9.5s, ok) Previous kept AUC: 0.6850.

## Experiment 19 — exploration: departure relative to typical schedules

Hypothesis: minutes earlier/later than the training median for a route or carrier-airport pair summarize a flight's position in its typical schedule without high-cardinality category partitions. Fit three median departure-time lookups on train (route, carrier-origin, carrier-destination), then only retrieve fixed values inside prepare. Based on the schedule/propagation paper above and the train-fitted median pattern explicitly described in program.md. Unlike discarded route categories, these are compact numerical schedule features, with no frequency information or target statistics.

Result: `d172a33` — **0.6843**, **discard**. Run time: 38.1s (training 27.1s, eval 11.0s, ok) Previous kept AUC: 0.6854.

## Experiment 20 — exploration: loss-guided trees with a leaf budget

Hypothesis: one-hot airport splits produce asymmetric trees, so a depth cap may spend capacity poorly. Use loss-guided growth with at most 16 leaves and unlimited depth, keeping the best features, constraints, and forest size. The [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) describes loss-guided growth as prioritizing nodes with the greatest loss improvement. This tests allocation of a limited leaf budget rather than a near-duplicate depth setting.

Result: `2c87c05` — **0.6855**, **keep**. Run time: 35.9s (training 26.5s, eval 9.5s, ok) Previous kept AUC: 0.6854.

## Synthesis after 20 experiments

Best: **0.6855**, commit `2c87c05`, gain +0.0112 from baseline. Individual-category splits and isolating Month remain the largest gains. Boosted forests, training-distance airport geometry, and a shared coarse holiday phase each helped modestly. Detailed holiday dates, additive weekday, large minimum leaves, schedule-median offsets, and a smaller forest failed. A 16-leaf loss-guided model marginally improved AUC and reduced artifact size. Current theory: sparse identities and transient date interactions need regularization, but weekday/operational interactions matter.

Research refresh: [When Does Label Smoothing Help?](https://arxiv.org/abs/1906.02629) studies generalization and calibration in neural models; adapting smoothing to tree logistic loss is a hypothesis, not a demonstrated result for this dataset. [XGBoost custom objectives](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html) supplies the gradient/Hessian interface. [XGBoost learning to rank](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) offers a possible future ranking-loss experiment. Next: objective regularization, independent-model averaging, and schedule shape constraints.

## Experiment 21 — exploration: smoothed logistic labels

Hypothesis: target probabilities 0.05/0.95 reduce overconfident corrections to outcomes driven by unobserved weather/operations. Implement logistic gradient p-(0.05+0.9*y) with unchanged Hessian p*(1-p), preserving all features and model parameters. Verified from the installed XGBClassifier source that a callable objective retains the binary-logistic prediction transform. Evaluation labels and harness metric remain unchanged.

Result: `8b3a5f2` — **0.6857**, **keep**. Run time: 36.2s (training 26.6s, eval 9.6s, ok) Previous kept AUC: 0.6855.

## Experiment 22 — exploration: average independent boosted models

Hypothesis: independently evolved boosting trajectories provide useful diversity beyond averaging trees within each step. Fit three 1200-round single-tree-per-step models with fixed seeds 42, 137, and 2026, then average probabilities. Keep smoothed logistic objective, features, leaf budget, and structural constraints. [Scikit-learn soft voting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) documents averaging class probabilities. Models train sequentially on train only; no seed-specific evaluation or selection.

Result: `d8e9602` — **0.6859**, **keep**. Run time: 26.7s (training 17.6s, eval 9.0s, ok) Previous kept AUC: 0.6857.

## Experiment 23 — exploration: pairwise ranking objective

Hypothesis: a pairwise logistic ranking loss targets positive-vs-negative ordering more directly than pointwise cross-entropy, potentially improving AUC. Based on the XGBoost learning-to-rank tutorial. Treat all training rows as one ranking group, sample one mean-strategy pair per row, disable extra lambda/score normalization, and use 500 single-tree rounds to bound ranking-gradient cost. Keep features and structural constraints. Convert ranking margins through sigmoid only to satisfy predict_proba; that monotone transform does not change rankings. No additional evaluation metric is computed.

Result: `3c8ecfc` — **0.6819**, **discard**. Run time: 29.1s (training 21.0s, eval 8.1s, ok) Previous kept AUC: 0.6859.

## Experiment 24 — ablation: shrink the additive seasonal component

Hypothesis: Month's learned 2005 marginal effect may partially reflect year-specific conditions. Since constraints make Month additive, identify that component from each fitted model's margins on 12 otherwise identical training-feature probes, then halve its contribution at prediction. Centering the probe margins removes the arbitrary reference level. This is model-component regularization; prepare and all input features stay unchanged. Check the extracted component against a second training anchor to verify independence from operational features. No evaluation rows or evaluation labels are used in fitting this correction.

Result: `62e0326` — **0.6900**, **keep**. Run time: 26.7s (training 17.7s, eval 9.0s, ok) Previous kept AUC: 0.6859.

## Experiment 25 — ablation: remove the fitted month contribution

Hypothesis: the large +0.0041 improvement from halving Month suggests substantial year-specific seasonality. Test removing its entire fitted contribution while preserving how it controlled for season during training. All other learned components and parameters remain fixed. This distinguishes complete non-transfer from partial useful seasonality.

Training-only time diagnostic: delay rates rise from about 0.19 at 05:00 to 0.65 at 20:00, then decline to 0.56 at 23:00. A globally increasing time constraint would be misspecified; consider a shape constraint that allows a late-night decline instead.

Result: `bf01862` — **0.6886**, **discard**. Run time: 27.0s (training 17.8s, eval 9.3s, ok) Previous kept AUC: 0.6900.

## Experiment 26 — exploration: shape-constrained operating-day risk

Hypothesis: the dominant departure-time signal should vary smoothly rather than fit arbitrary minute-level fluctuations. Training-only hour rates show a rise from 05:00 through 20:00 and a subsequent fall. Replace raw HHMM with a rising operating-day coordinate capped at 20:00 and a late-night coordinate, constrained increasing/decreasing respectively. The operating day wraps at 05:00. Retain airport/carrier interactions, so curve shapes can differ by context. Based on XGBoost monotonic-constraint documentation and the previously cited daily delay-propagation research.

Result: `b039e87` — **0.6891**, **discard**. Run time: 28.8s (training 19.4s, eval 9.4s, ok) Previous kept AUC: 0.6900.

## Experiment 27 — follow-up: refine seasonal shrinkage once

Hypothesis: zero/half/full shrinkage gave 0.6859/0.6900/0.6886 under otherwise identical models. A quadratic interpolation places the peak near 0.62 shrinkage. Test 0.625 as one targeted interior refinement, retaining 37.5% of the fitted month effect. This is a bracketed refinement of a large, reproducible structural gain; do not continue a fine-grained sweep. The shape-constrained time model failed and was reverted.

Result: `1f5c0f6` — **0.6901**, **keep**. Run time: 27.6s (training 18.5s, eval 9.1s, ok) Previous kept AUC: 0.6900.

## Experiment 28 — exploration: departure-distance arrival-phase proxy

Hypothesis: adding departure minutes and a rough distance-based duration exposes an oblique time-distance interaction relevant to destination congestion. Compute (departure_minutes + Distance/8 + 30) modulo 1440. This is deliberately labeled a proxy in the origin clock, not actual arrival time: 8 miles/minute and 30 minutes are heuristic constants, and no time-zone or actual-arrival data is used. Motivated by the previously cited schedule/network delay research. Add only this one numeric feature to the operational group and retain all best settings.

Result: `2b92739` — **0.6898**, **discard**. Run time: 27.7s (training 17.9s, eval 9.8s, ok) Previous kept AUC: 0.6901.

## Experiment 29 — ablation/simplification: omit month during fitting

Hypothesis: instead of learning then shrinking a year-specific seasonal component, omit Month from the model entirely. This changes how the operational components are fitted and removes the seasonal-correction subclass. Holiday phase still uses calendar inputs inside prepare, but Month is no longer an output feature. Distinct from experiment 25, which removed Month only after training. Keep an equal AUC if the simpler model matches the best.

Result: `f44d9db` — **0.6887**, **discard**. Run time: 25.9s (training 17.3s, eval 8.6s, ok) Previous kept AUC: 0.6901.

## Experiment 30 — follow-up: stronger leaf-value regularization

Hypothesis: after explicitly handling seasonal drift, residual sparse airport/weekday effects may benefit from stronger shrinkage. Raise L2 leaf penalty from 10 to 50 with all ensemble settings fixed. Unlike the discarded min_child_weight=100 trial, this retains small supported splits but shrinks their output values. This follows the variance-reduction evidence from smoothing and independent averaging.

Result: `2983d9f` — **0.6899**, **discard**. Run time: 26.7s (training 17.6s, eval 9.1s, ok) Previous kept AUC: 0.6901.

## Synthesis after 30 experiments

Best: **0.6901**, commit `1f5c0f6`, gain +0.0158 from baseline. The key new finding is temporal drift in Month: retaining 37.5% of its fitted additive component outperforms both full use and removal. Learning Month during fitting still helps separate operational effects, since omitting it entirely scored 0.6887. Independent smoothed models improve the result at lower cost than a single boosted forest. Pairwise ranking, a hard daily-time shape, an arrival-phase proxy, and stronger leaf L2 did not improve AUC.

Research refresh: [Robust-GBDT](https://arxiv.org/abs/2310.05067) motivates considering noise-robust objectives, but hidden weather is not evidence of erroneous labels and this experiment does not reproduce that paper's nonconvex loss. The [XGBoost reference](https://xgboost.readthedocs.io/en/stable/parameter.html) provides a native twice-differentiable Pseudo-Huber objective. Further directions: robust scoring loss, more boosting rounds under the new regularization, and a richer low-dimensional airport geometry.

## Experiment 31 — exploration: robust Pseudo-Huber scoring loss

Hypothesis: fitting binary targets with Pseudo-Huber loss (delta 0.5) can reduce the influence of large residuals driven by unavailable conditions. Replace smoothed logistic loss while retaining ensemble, structural constraints, and seasonal shrinkage. Raw additive regression scores pass through the existing sigmoid adapter, yielding finite scores in [0,1] for AUC; they are ranking scores rather than calibrated delay probabilities. The experiment uses only the unchanged harness metric.

Result: `7edf182` — **0.6891**, **discard**. Run time: 22.7s (training 13.7s, eval 9.0s, ok) Previous kept AUC: 0.6901.

### Plateau review after experiment 31

Recent exploratory changes cluster below 0.6901. Refreshed research on [gradient boosting regularization](https://scikit-learn.org/stable/modules/ensemble.html#gradient-tree-boosting): boosting iteration count controls the bias/variance tradeoff alongside learning rate. The substantial changes since the early 400-vs-1200 comparison (constraints, geometry, ensembles, smoothing, seasonal correction) justify rechecking the iteration budget rather than adding more marginal features.

## Experiment 32 — follow-up: longer regularized ensemble

Hypothesis: seasonal correction and averaging now permit more rounds to fit stable operational effects. Double each ensemble member from 1200 to 2400 trees, keeping all other settings fixed. Projected training ~35s from current ~18s, below the harness limit.

Result: `9fea2a8` — **0.6889**, **discard**. Run time: 42.8s (training 32.6s, eval 10.2s, ok) Previous kept AUC: 0.6901.

## Experiment 33 — follow-up: third airport geometry coordinate

Hypothesis: the two-dimensional distance embedding omits some stable regional geometry. Training-only eigenspectrum diagnostics show two dimensions retain 78.7% of positive eigenvalue mass versus 82.3% for three. Add the third component while preserving the original first two coordinate columns and signs. Keep the reverted 1200-round schedule, since doubling rounds harmed generalization.

Result: `beea9aa` — **0.6898**, **discard**. Run time: 27.1s (training 18.0s, eval 9.1s, ok) Previous kept AUC: 0.6901.

## Experiment 34 — ablation: shorter boosting schedule

Hypothesis: 2400 rounds clearly overfit, and the additional geometry coordinate also failed. Test 600 rounds per member, half the kept 1200, to reduce residual variance and simplify the ensemble. This is the opposite side of the iteration tradeoff motivated by the recent failed capacity increase; all features and shrinkage are unchanged. Equal AUC would qualify for keeping due to fewer trees and faster inference.

Result: `85b64a0` — **0.6893**, **discard**. Run time: 18.5s (training 10.0s, eval 8.5s, ok) Previous kept AUC: 0.6901.

### Plateau research after experiment 34

Both shorter and longer schedules lose to 1200 rounds. Reviewed Friedman's [Recent Advances in Predictive Learning](https://jerryfriedman.su.domains/ftp/machine.pdf) and the [scikit-learn regularization example](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_regularization.html): row subsampling and small weak learners provide distinct regularization mechanisms. This motivates separating column randomness from the already successful row-sampled ensemble and testing weaker individual trees rather than more of the same trees.

## Experiment 35 — ablation: let every feature compete at splits

Hypothesis: with only a small number of meaningful features, excluding the dominant time feature at some splits may add bias. Remove column subsampling (default 1.0), keeping 80% row sampling and three independently seeded models for diversity. This separates the two randomness mechanisms added together in experiment 14.

Result: `88a1855` — **0.6899**, **discard**. Run time: 27.0s (training 17.8s, eval 9.2s, ok) Previous kept AUC: 0.6901.

## Experiment 36 — follow-up: smooth the retained seasonal component

Hypothesis: broad annual and semiannual patterns should transfer better than irregular monthly anomalies. Project each model's centered month effect onto first- and second-harmonic sine/cosine terms, retaining the same 37.5% amplitude used by the best model. Inspired by [scikit-learn cyclic feature representations](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html). Apply this to model coefficients after fitting, rather than altering the operational training inputs. Actual month numbers define the Fourier basis so lexicographic category order cannot affect it.

Result: `68789c6` — **0.6892**, **discard**. Run time: 27.6s (training 18.6s, eval 9.0s, ok) Previous kept AUC: 0.6901.

## Experiment 37 — exploration: more stages of weaker trees

Hypothesis: the same approximate total leaf capacity may generalize better when allocated to smaller weak learners. Use 2400 rounds with 8 leaves instead of 1200 rounds with 16 leaves; preserve learning rate, features, and seasonal correction. Motivated by Friedman's discussion of small fixed-size trees in the indexed lecture excerpt reviewed above. Distinct from experiment 32, which doubled tree count without reducing each tree's complexity.

Result: `0209f9e` — **0.6897**, **discard**. Run time: 37.9s (training 28.4s, eval 9.5s, ok) Previous kept AUC: 0.6901.

## Experiment 38 — ablation: remove inferred airport geometry

Hypothesis: the original geometry gain was small and preceded the ensemble and seasonal correction; the extra features may now be redundant. Remove the graph embedding and its four numeric columns, retaining native airport identities and all best model settings. This tests whether the substantive feature-engineering complexity still earns its place. Equal AUC qualifies as a simpler model.

Result: `662ed59` — **0.6893**, **discard**. Run time: 26.0s (training 17.4s, eval 8.7s, ok) Previous kept AUC: 0.6901.

## Experiment 39 — ablation: remove holiday phase

Hypothesis: after correcting seasonal drift, the small earlier holiday gain may no longer justify the calendar transformation. Remove the holiday phase and its additive group while keeping Month, operational features, and geographic coordinates. Equal AUC would qualify as simpler and faster preprocessing. Geometry ablation failed at 0.6893, so the coordinates remain.

Result: `117e4c6` — **0.6898**, **discard**. Run time: 24.8s (training 17.3s, eval 7.4s, ok) Previous kept AUC: 0.6901.

## Experiment 40 — exploration: tightly limited categorical partitions

Hypothesis: grouping only a few similar categories may share information without the broad, unstable partitions that failed early. Set max_cat_to_onehot=4 and max_cat_threshold=4. The refreshed [XGBoost categorical parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html) explicitly describes the split threshold as an overfitting control. Unlike experiment 2 and the starter, partition search is now tightly restricted, and the stronger ensemble/seasonal regularization remains.

Result: `3e28943` — **0.6876**, **discard**. Run time: 30.4s (training 21.1s, eval 9.3s, ok) Previous kept AUC: 0.6901.

## Synthesis after 40 experiments

Best remains **0.6901**, commit `1f5c0f6`. The last ten experiments sharpened the boundary: robust loss, alternate boosting schedules/tree sizes, additional geometry dimensions, full feature sampling, smooth Fourier seasonality, and small categorical partitions all lost. Ablations confirm that both the two-dimensional geometry and coarse holiday phase still help in the final model family. There is no evidence that greater complexity alone improves this plateau.

Research refresh: [CatBoost categorical-feature documentation](https://catboost.ai/docs/en/features/categorical-features) discusses combinations of categorical inputs. Use only that feature-combination idea here; retain XGBoost and the native one-hot split strategy supported by this run, without installing or switching libraries or using target encodings.

## Experiment 41 — exploration: one conservative carrier-origin cross

Hypothesis: a single carrier-origin category can expose a stable ground-operation interaction in one split. Unlike experiment 2, omit route and carrier-destination crosses, force one-hot splits for the new field, and retain the stronger ensemble, minimum leaves, and seasonal correction. Fit its levels on train and construct the string pair inside prepare. Raising max_cat_to_onehot to 10000 changes no existing categorical treatment; it only ensures this larger cross also uses individual-category splits.

Result: `062fe44` — **0.6901**, **discard**. Run time: 31.5s (training 20.2s, eval 11.2s, ok) Previous kept AUC: 0.6901.

Experiment 41 matched 0.6901 but added complexity and slowed evaluation, so discarded under the keep rule.

## Experiment 42 — follow-up: average five independent models

Hypothesis: the successful three-member ensemble may retain some sampling variance. Add two predetermined seeds (2718 and 31415) to the same estimator family and average all five equally. Existing members are unchanged; no individual seed is scored or selected. Expected training remains below 60s based on the measured three-member cost. This tests ensemble size, not a search for a fortunate seed.

Result: `6ad5f15` — **0.6901**, **discard**. Run time: 39.4s (training 29.6s, eval 9.8s, ok) Previous kept AUC: 0.6901.

Experiment 42 matched the best AUC but increased training and inference costs, so the three-member ensemble remains.

## Experiment 43 — exploration: diagonal axes for airport geometry

Hypothesis: axis-aligned trees may model regional boundaries more economically if they can also split along 45-degree directions in the existing two-dimensional geometry. Add coordinate sum and difference for origin and destination, preserving all original coordinates. Unlike experiment 33, this adds no new geometric information; it changes how easily a small tree can express boundaries. The transform is deterministic, uses only the fitted training lookup, and has negligible preparation cost.

Result: `aba3067` — **0.6901**, **discard**. Run time: 28.3s (training 19.0s, eval 9.2s, ok) Previous kept AUC: 0.6901.

## Final summary

The loop ended after the harness reported less than two minutes remaining. Completed **43 non-baseline experiments**, **44 total runs**: 16 keeps including baseline, 28 discards, and zero crashes/timeouts. All trials are recorded in `output/results.tsv`; the last trial matched the best score with additional complexity and was discarded.

- **Best eval AUC: 0.6901**, versus baseline **0.6743**, an absolute gain of **0.0158**.
- **Best commit:** `1f5c0f6fa3f046acd58c68741244c936fb23ed48` on branch `oct7`.
- **Saved artifact:** `artifacts/1f5c0f6fa3f046acd58c68741244c936fb23ed48.pkl`.
- Best measured run: 27.6s total, 18.5s training phase and 9.1s evaluation phase.

The retained model averages three independently seeded XGBoost classifiers, each with 1200 rounds, learning rate 0.05, loss-guided 16-leaf trees, minimum child weight 20, L2 penalty 10, 80% row/column sampling, native one-hot category splits, and smoothed logistic targets. The 12 prepared features include the original operational inputs, two training-distance-derived coordinates for each airport, and a shared coarse holiday phase. Raw day-of-month is used only to derive the recurring holiday feature. Month and holiday effects are additive; 37.5% of each fitted model's month component is retained at prediction.

The strongest gains came from individual-category splits, limiting seasonal interactions, and shrinking the learned month effect to account for cross-year instability. Independent averaging, label smoothing, airport geometry, and coarse holidays added smaller gains. Cached categorical types and explicit codes substantially reduced row-wise preprocessing time. Broader route interactions, detailed holiday dates, hard time-shape constraints, ranking and robust losses, larger/smaller boosting schedules, richer geometry, and extra ensemble members did not beat the final model. Removing either geometry or holidays also reduced AUC.

Final verification passed: HEAD is the best kept commit; the working tree is clean; only `train.py` differs from the starting commit; the harness is unchanged; `save_and_evaluate(model, prepare)` remains the final statement; the best artifact exists and reloads; its preparation is consistent between batches and individual rows and independent of supplied target values; its probabilities are finite, bounded, correctly shaped, and sum to one. Earlier feature checks also covered unknown categories and serialization. No holdout or archived-run results were consulted.

Next ideas would be training-only regional representations that use fewer degrees of freedom, partial regularization of weekday/operational interactions, or a deliberately heterogeneous ensemble with prespecified members. These should be tested as new hypotheses rather than continued fine adjustments of seasonal shrinkage. Holdout generalization remains for the human's independent assessment.

The harness stop command immediately following this entry records the final wall-clock duration.
