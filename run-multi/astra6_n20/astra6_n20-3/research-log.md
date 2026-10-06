# Flight delay XGBoost research — oct6

Run branch: `oct6`. Baseline commit: `b15ec66`.

## Baseline

Run the starter unchanged: 100 trees, depth 6, learning rate 0.1; categorical calendar, carrier, origin, and destination; raw scheduled departure time and distance. The harness Eval AUC is the decision metric. Training is limited to 60 seconds and evaluation to 300 seconds.

All features must work identically per row, use only training-fitted lookups, and remain fast enough for row-by-row evaluation. No counts or frequencies will be used as features.

Baseline result: **0.6743**; training phase 1.4s, evaluation 30.6s.

## Initial research

- [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html): control complexity, use shrinkage and randomness, inspect the data.
- [XGBoost parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html): depth, child Hessian thresholds, category partition thresholds, regularization and sampling are distinct controls.
- [Native categorical splits](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html): categories are grouped by learned gradient statistics; high-cardinality interactions need regularization.
- [Berkeley flight feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches): carrier, route and scheduled-flight characteristics motivate domain features; unavailable real-time information is out of scope. Search extract was available; full page did not load.

Training inspection: 200,000 complete rows; 20 carriers and 283 origin/destination levels. Day-of-month delay rates vary from roughly 0.46 to 0.56, potentially reflecting individual 2005 weather events. The next-year evaluation makes exact-date effects suspect.

## Experiment 1 — remove day of month

Category: ablation/simplification. Hypothesis: removing day of month prevents fitting date-specific disruptions that do not transfer from 2005 to 2006. Retain all other baseline settings to isolate its contribution. Motivated by the tuning guidance above and training-only inspection.

Result: commit `f197aff`, Eval AUC **0.6759**, **keep**. Run time: 28.3s (training 1.4s, eval 26.9s, ok)

Observation: removing day of month improved AUC by 0.0016; the feature had weak transfer.

## Experiment 2 — faster equivalent categorical preparation

Category: ablation/simplification. Hypothesis: build the frame once and reuse categorical dtypes to eliminate redundant membership tests and repeated column assignments. [pandas.Categorical documentation](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.html) guarantees unknown values map to missing when fixed categories are supplied. Require identical features on a training sample, on single rows, and on a synthetic unknown category. Equal AUC is keepable here because the code is simpler and expected to be faster.

Result: commit `8652e1e`, Eval AUC **0.6759**, **keep**. Run time: 11.9s (training 1.3s, eval 10.5s, ok)

Observation: equivalent preparation cut evaluation from 26.9s to 10.5s.

## Experiment 3 — shallow regularized boosting

Category: exploration. Hypothesis: depth-4 trees with smaller steps and more rounds will capture stable main effects and interactions while reducing variance from native categorical grouping. Try 600 trees at eta 0.04, minimum child weight 20, L2 10, and row sampling 0.8. The initial XGBoost tuning documentation motivates these joint changes; this is a new regularization regime, not an isolated parameter attribution. Baseline gain importance strongly favors departure time, followed by carrier and airport identities.

Result: commit `e0181ea`, Eval AUC **0.6793**, **keep**. Run time: 13.2s (training 3.0s, eval 10.3s, ok)

Observation: the shallow regularized regime improved AUC by 0.0034 to 0.6793.

## Experiment 4 — one-category splits

Category: follow-up. Hypothesis: forcing one-category-versus-rest splits avoids unstable multi-airport groupings learned from 2005 labels. Set max_cat_to_onehot=512 so all current categoricals use this split rule; keep the successful shallow configuration otherwise unchanged. [Native categorical documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains the distinction from partition splits.

Result: commit `ce6f3d8`, Eval AUC **0.6785**, **discard**. Run time: 12.9s (training 2.6s, eval 10.3s, ok)

Observation: one-category splits lost 0.0008, so native grouping remains useful.

## Experiment 5 — month ablation

Category: ablation/simplification. Hypothesis: month-specific disruption levels in 2005 may not repeat in 2006. Remove month while retaining weekday, schedule, carrier, airports and distance. This tests the cost of seasonality directly before considering softer calendar constraints.

Result: commit `379eb15`, Eval AUC **0.6822**, **keep**. Run time: 11.9s (training 2.8s, eval 9.0s, ok)

Observation: removing month gained 0.0029. Both fine calendar components tested so far hurt next-year transfer.

## Experiment 6 — explicit flight-network interactions

Category: exploration. Hypothesis: route and carrier-airport combinations describe stable operational context more directly than separate airport and carrier splits. Add three native categorical features: origin/destination, carrier/origin, carrier/destination. Levels are fitted on train only and applied identically per row. The initial flight-domain source motivates operational interactions and XGBoost categorical documentation motivates direct categorical representation. Risk: sparse combinations can overfit despite leaf regularization.

Result: commit `e0d3c3d`, Eval AUC **0.6710**, **discard**. Run time: 18.1s (training 5.3s, eval 12.8s, ok)

Observation: raw route/carrier-airport categories dropped AUC by 0.0112, strong evidence that sparse partitioned interactions fit nontransferable details.

## Experiment 7 — schedule geometry

Category: exploration. Hypothesis: explicit hour, minute-of-hour, a day clock beginning at 05:00, and sine/cosine of actual minutes after midnight help shallow trees capture daily delay buildup and the late-night decline. Preserve raw departure time and all other successful features. Train-only hourly delay rates rise from about 0.20 at 06:00 to 0.65 at 20:00 and fall to 0.56 by 23:00. [Scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) explains periodic representations and their inductive bias. These transformations depend only on each row.

Result: commit `8bbbd58`, Eval AUC **0.6826**, **keep**. Run time: 14.1s (training 3.1s, eval 11.0s, ok)

Observation: schedule geometry gained 0.0004; useful but much smaller than removing nontransferable calendar effects.

## Experiment 8 — more interaction capacity without calendar detail

Category: follow-up. Hypothesis: after removing month/day-of-month and adding schedule geometry, deeper trees can learn operational interactions without the worst calendar memorization. Increase depth from 4 to 6, keeping 600 rounds, eta 0.04, child weight 20, L2 10 and sampling fixed. This isolates capacity under the improved feature representation.

Result: commit `8d140b9`, Eval AUC **0.6774**, **discard**. Run time: 15.1s (training 4.4s, eval 10.8s, ok)

Observation: depth 6 lost 0.0052 even without month/day-of-month, so operational interactions also overfit when overly detailed.

## Experiment 9 — restrict category partition size

Category: follow-up. Hypothesis: limiting the categories considered per partition split can retain beneficial pooling (experiment 4 showed one-category splits were too restrictive) while reducing the noisy airport groupings suggested by experiments 6 and 8. Set max_cat_threshold=8, leave the successful depth-4 model fixed. [XGBoost categorical parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature) identifies this parameter as an overfitting control.

Result: commit `4513c45`, Eval AUC **0.6831**, **keep**. Run time: 13.4s (training 2.9s, eval 10.6s, ok)

Observation: restricting categorical partition search to 8 improved AUC by 0.0005.

## Experiment 10 — training-fitted schedule medians

Category: exploration. Hypothesis: numeric schedule summaries provide operational context with fewer degrees of freedom than raw route categories. Fit median scheduled minutes for origin, destination, carrier/origin and route; add each median and the row departure time minus that median. These are not counts or frequency features. [Day-ahead aircraft routing research](https://www.sciencedirect.com/science/article/abs/pii/S0377221723001698) motivates network and schedule context; the particular median representation is my adaptation and is also an explicit permitted example in program.md. Unknown keys map to NaN.

Result: commit `4771db7`, Eval AUC **0.6828**, **discard**. Run time: 15.3s (training 3.3s, eval 12.0s, ok)

## Synthesis after 10 experiments

Best: **0.6831**, commit `4513c45`, versus baseline 0.6743. Removing day-of-month and month helped, as did a shallower regularized regime and restricted category partitions. Rich route categories and depth 6 hurt strongly. Schedule geometry gave a small gain; median schedule summaries missed by 0.0003. Current theory: temporal transfer is limited by variance and year-specific relationships; departure time and broad operational identities carry the robust signal. Next prioritize randomness/averaging, simpler fits, and honest smoothed target summaries.

Research refresh: [XGBoost boosted random forests](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) documents num_parallel_tree alongside boosting rounds; [Friedman, Stochastic Gradient Boosting](https://www.sciencedirect.com/science/article/pii/S0167947301000652) motivates random subsamples during boosting. [TargetEncoder documentation](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) and [CatBoost paper](https://arxiv.org/abs/1706.09516) emphasize avoiding target leakage. Any supervised lookup experiment here must use disjoint encoder/model fitting data, and all reported model comparisons will still use only the harness. No cross-validation scoring will be introduced.

## Experiment 11 — boosted randomized forests

Category: exploration. Hypothesis: averaging four randomized trees in each boosting step lowers split-selection variance. Keep 600 rounds at eta 0.04 and depth 4; use four trees per round, row sampling 0.65 and per-node column sampling 0.8. This is a distinct model-averaging regime based on the refreshed sources above.

Result: commit `64d0ad6`, Eval AUC **0.6827**, **discard**. Run time: 24.6s (training 13.6s, eval 11.0s, ok)

Observation: boosted random forests lost 0.0004 and cost substantially more training time; discard. Gain importance in the best model shows minute-of-hour is the weakest feature by a wide margin (gain 3.8, versus 17+ for all others).

## Experiment 12 — remove minute-of-hour

Category: ablation/simplification. Hypothesis: minute-of-hour mainly identifies detailed timetable patterns that are unstable across years. Remove DepMinute while retaining hour, the shifted day clock and cyclic terms. Equal AUC is acceptable if this simpler feature set is no worse.

Result: commit `08b7941`, Eval AUC **0.6833**, **keep**. Run time: 13.6s (training 2.8s, eval 10.9s, ok)

Observation: minute-of-hour ablation gained 0.0002 and simplified the feature set.

## Experiment 13 — shorter boosting horizon

Category: ablation/simplification. Hypothesis: late boosting rounds fit residual year-specific airport and schedule noise. Halve boosting rounds from 600 to 300 at fixed eta and regularization. This is a substantial capacity reduction prompted by the depth and sparse-interaction failures, rather than a minor parameter perturbation. Equal AUC is keepable because the model is smaller and faster.

Result: commit `6931767`, Eval AUC **0.6812**, **discard**. Run time: 12.3s (training 1.8s, eval 10.5s, ok)

Observation: 300 rounds lost 0.0021, so the current representation still needs substantial boosting despite the overfitting from depth.

## Experiment 14 — honest smoothed delay lookups

Category: exploration. Hypothesis: smoothed numeric route/carrier-airport delay rates transfer better than unrestricted category groupings. Reserve a deterministic random 25% of train exclusively to fit target-rate lookups, then fit XGBoost on the disjoint remaining 75%. Retain original base features. Add rates for origin, destination, route, carrier/origin and carrier/destination, each shrunk toward the encoder-subset mean with prior strength 100. Only rates enter the model; no count or frequency features. Unknown groups use the prior. This deliberately sacrifices model-fitting rows to avoid self-target leakage. No validation scores, cross-validation, evaluation-file inspection or refit on additional data are used. Sources: [TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html), [CatBoost leakage analysis](https://arxiv.org/abs/1706.09516).

Result: commit `ff54a19`, Eval AUC **0.6819**, **discard**. Run time: 14.8s (training 2.6s, eval 12.2s, ok)

Observation: honest target-rate features reached 0.6819, losing 0.0014. The extra route information did not compensate for the smaller model-fitting subset and potentially confounded unconditional delay rates.

## Experiment 15 — distance-derived airport geography

Category: exploration. Hypothesis: distance to six airport landmarks supplies a smooth geographic representation that generalizes across sparse airports. Fit an undirected graph from median route distances in train only; fill absent direct connections with shortest-path mileage; look up origin and destination distances to ATL, ORD, DFW, DEN, LAX and JFK. No counts, frequencies, labels, or external airport data are used. This is an inferred representation, not actual coordinates. [SciPy shortest_path documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html) describes the distance calculation; [flight-network research](https://arxiv.org/abs/2207.06959) motivates geographic relations while its real-time components are unavailable here.

Result: commit `b1358ad`, Eval AUC **0.6848**, **keep**. Run time: 14.8s (training 3.3s, eval 11.4s, ok)

Observation: distance-derived geography improved AUC by 0.0015 to 0.6848. Unlike high-cardinality route features, this smoother representation transfers usefully.

## Experiment 16 — geographic representation without raw airport categories

Category: ablation/simplification. Hypothesis: geographic numeric features can preserve stable regional structure while avoiding label-dependent native category groupings. Remove raw Origin and Dest categorical columns, retain their distance-derived geographic lookups plus carrier, weekday and schedule. Equal AUC is acceptable because the input feature set is smaller.

Result: commit `4fa1bdc`, Eval AUC **0.6874**, **keep**. Run time: 12.1s (training 3.1s, eval 8.9s, ok)

Observation: removing raw airport categories while keeping geographic features gained 0.0026 to 0.6874. This is strong evidence that native label-driven airport partitions were a major source of transfer error.

## Experiment 17 — one-category splits for the remaining low-cardinality features

Category: follow-up. Hypothesis: individual carrier/weekday effects should transfer more stably than joint label-driven groupings. Set max_cat_to_onehot=32. This differs materially from experiment 4: the 283-level airport categories have been replaced with smooth geography; only 20 carriers and 7 weekdays remain categorical, so the former underfitting burden of separately splitting hundreds of airports is gone.

Result: commit `ad7617e`, Eval AUC **0.6866**, **discard**. Run time: 12.0s (training 2.9s, eval 9.1s, ok)

Observation: even for carrier/weekday alone, partition splits beat one-category splits by 0.0008.

## Experiment 18 — deeper trees on smooth geographic inputs

Category: follow-up. Hypothesis: the new numeric geography can support richer interactions without the noisy airport category partitions responsible for earlier overfitting. Increase depth 4 to 6 at fixed settings. Unlike experiment 8, no raw airport categories remain and spatial context comes from continuous mileage features.

Result: commit `0a10e19`, Eval AUC **0.6866**, **discard**. Run time: 12.9s (training 4.0s, eval 8.9s, ok)

Observation: depth 6 still lost 0.0008, although much less than with raw airport categories. Keep depth 4.

## Experiment 19 — favor recent training observations

Category: exploration. Hypothesis: operational carrier and airport relationships later in 2005 are more relevant for 2006. Weight training examples by exponential recency with a six-month half-life, normalized to mean one so regularization scale stays comparable. Month remains excluded from prediction features. This is a training-weight strategy, not an evaluation-derived adjustment. [Google Research on concept drift](https://research.google/blog/learning-the-importance-of-training-data-under-concept-drift/) motivates age-dependent weights; the fixed decay is my simpler adaptation, with no auxiliary evaluation or learned weighting model.

Result: commit `86f3aff`, Eval AUC **0.6880**, **keep**. Run time: 12.0s (training 3.1s, eval 8.9s, ok)

Observation: six-month recency weighting gained 0.0006. Train-only quarterly carrier rates change materially (e.g. AS 0.713 in Q2 to 0.539 in Q4; US 0.595 in Q1 to 0.428 in Q4), consistent with shifting operational effects.

## Experiment 20 — continuous coordinates and route direction

Category: follow-up. Hypothesis: a low-dimensional embedding of the full distance graph gives trees useful geographic boundaries and direction-of-travel effects beyond six separate landmark distances. Fit three classical multidimensional-scaling coordinates from the centered squared shortest-path distance matrix, then add origin, destination and destination-minus-origin coordinates. All fitting is unsupervised on training route distances. [MDS documentation](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.MDS.html) and [SVD-MDS localization paper](https://arxiv.org/abs/1811.12803) motivate reconstructing location-like representations from pair distances. Coordinates are approximate and arbitrarily oriented, not claimed latitude/longitude.

Result: commit `50d1c9f`, Eval AUC **0.6875**, **discard**. Run time: 13.5s (training 3.7s, eval 9.8s, ok)

## Synthesis after 20 experiments

Best: **0.6880**, commit `86f3aff`, +0.0137 over baseline. The strongest new result was replacing raw airport categories with distance-to-landmark features: +0.0015 when added and +0.0026 more when airport categories were removed. Mild recency weighting added 0.0006. Raw route categories, honest target encodings on a reserved subset, and additional MDS coordinates did not help. Individual carrier/weekday splits remain worse than small native partitions. Deeper trees still lose; halving rounds also loses, suggesting more shallow steps rather than more depth.

Research refresh: searched [XGBoost ranking objectives](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html), including pairwise logistic ranking with binary relevance, as a possible future alternative to pointwise classification. Also revisited histogram binning and leaf regularization in the parameter reference. Next: test longer shallow boosting, coarser numeric partitions, and then a distinct ranking objective if needed.

## Experiment 21 — longer shallow boosting

Category: follow-up. Hypothesis: smooth geographic features need additional small updates, while shallow trees limit interaction complexity. Increase 600 rounds to 1200 at fixed eta 0.04. Motivated by the underfitting at 300 rounds and the failure of depth 6; this doubles boosting duration without increasing each tree's interaction order.

Result: commit `b580f14`, Eval AUC **0.6877**, **discard**. Run time: 14.6s (training 5.4s, eval 9.2s, ok)

Observation: 1200 rounds lost 0.0003, so extra shallow updates also begin to fit noise.

## Experiment 22 — coarser numeric split resolution

Category: exploration. Hypothesis: reducing histogram bins from 256 to 64 pools nearby departure times and geographically similar airports, making it harder to memorize individual schedules or airports through precise continuous values. Keep the 600-round model and other settings fixed. The [XGBoost max_bin reference](https://xgboost.readthedocs.io/en/stable/parameter.html) defines the tradeoff between split resolution and computation.

Result: commit `b5536f5`, Eval AUC **0.6878**, **discard**. Run time: 12.0s (training 3.0s, eval 9.0s, ok)

## Plateau research after experiment 22

Three consecutive discards differ from the best by less than 0.001 (MDS -0.0005, extra rounds -0.0003, coarse bins -0.0002). Stop local changes and investigate another objective. Read [XGBoost learning-to-rank guide](https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html) and ranking parameter definitions; searched the original RankNet work and XGBRanker group weights. Pairwise logistic loss optimizes ordering, while the mean pair sampler covers the whole ranking rather than focusing on top-k.

## Experiment 23 — within-month pairwise ranking

Category: exploration. Hypothesis: learning to rank delayed flights above on-time flights within each training month reduces sensitivity to month-level delay prevalence, while matching AUC's ordering goal. Use rank:pairwise with 600 depth-4 rounds, four mean-sampled pairs per row, and query-level six-month recency weights. Each month is a training query; no query/month field enters prediction features. Disable score-difference normalization for a standard pairwise logistic formulation. A small wrapper converts ranking margins monotonically to two-column probabilities for the unchanged harness. No additional evaluation metric is computed.

Result: commit `c96e6e9`, Eval AUC **0.6858**, **discard**. Run time: 18.1s (training 8.9s, eval 9.3s, ok)

Observation: within-month pairwise ranking reached 0.6858, below 0.6880; restore pointwise classification.

## Experiment 24 — balance labels within training months

Category: exploration. Hypothesis: monthly weather severity changes the label mix and can indirectly confound operational features even when month itself is excluded. Keep logistic classification, but multiply recency weights by inverse within-month class prevalence so each month has equal total positive/negative weight. This removes month-label association in the training objective without changing any feature or introducing additional evaluation. [Class-conditional balancing research](https://proceedings.mlr.press/v306/zhao26bt.html) motivates reducing spurious group-label dependence; month as the grouping factor is my domain-specific adaptation. The weights are training-only, not model features.

Result: commit `8d8851d`, Eval AUC **0.6882**, **keep**. Run time: 12.0s (training 3.1s, eval 9.0s, ok)

Observation: monthly label balancing gained 0.0002.

## Experiment 25 — damp day-specific disruption prevalence

Category: follow-up. Hypothesis: daily disruptions create finer spurious correlations than monthly averages. Replace monthly balancing with a shrunk daily adjustment, targeting the training weekday's overall delay rate so recurring weekday effects remain. Estimate each day's probability with a prior strength of 200 toward its weekday rate, then reweight positive and negative examples toward that weekday prior. Keep recency weighting. All label-derived quantities are training weights only; prediction features stay unchanged. This is a finer environmental grouping motivated by experiment 24 and the class-conditional balancing source.

Result: commit `e887a07`, Eval AUC **0.6879**, **discard**. Run time: 12.0s (training 3.2s, eval 8.8s, ok)

Observation: daily prevalence adjustment lost 0.0003; retain the simpler monthly balancing.

## Experiment 26 — average five independently seeded models

Category: exploration. Hypothesis: independently randomized full boosting trajectories make different small split errors; averaging their probabilities lowers variance while keeping the same data, features and regularization. Use five fixed seeds (42, 137, 2026, 256, 991), all with equal weight. Seeds are not selected by evaluation performance, and no member is evaluated separately. This differs from experiment 11, which averaged trees within each step and used a different feature representation. [Scikit-learn ensemble guidance](https://scikit-learn.org/stable/modules/ensemble.html#voting-classifier) motivates probability averaging.

Result: commit `68dca8f`, Eval AUC **0.6880**, **discard**. Run time: 21.1s (training 11.7s, eval 9.4s, ok)

Observation: the fixed five-seed average lost 0.0002 and increased training time; retain the single model.

## Experiment 27 — pooled holiday proximity

Category: exploration. Hypothesis: travel behavior near major holidays repeats across years more reliably than raw month or day-of-month. Add only days until/since the nearest major holiday, clipped to seven days, pooling New Year, Memorial Day, Independence Day, Labor Day, Thanksgiving and Christmas. Movable holiday dates are computed row by row from calendar/weekday alignment using the [OPM holiday rules](https://www.opm.gov/faq/payleave/what-are-federal-holidays.ashx). Both dataset years are non-leap years. No year indicator, raw day-of-year, or individual holiday-date categories enter the model. The travel-demand effect is a hypothesis, not established by the calendar source.

Result: commit `f1696a1`, Eval AUC **0.6888**, **keep**. Run time: 13.5s (training 3.2s, eval 10.3s, ok)

Observation: pooled holiday proximity gained 0.0006; recurring travel-calendar structure can help even though unrestricted calendar categories failed.

## Experiment 28 — improve geographic landmark coverage

Category: follow-up. Hypothesis: adding SEA and MIA to the six central/coastal landmarks adds useful north-south regional resolution, particularly for sparse airports, without label-driven encodings. Keep all modeling settings and the graph construction fixed. The anchors are fixed airport identities, not selected by target rates or row counts.

Result: commit `c2a3740`, Eval AUC **0.6886**, **discard**. Run time: 13.8s (training 3.4s, eval 10.5s, ok)

Observation: extra SEA/MIA landmark features lost 0.0002; the six-anchor geography remains preferable.

## Experiment 29 — faster decay of older training observations

Category: follow-up. Hypothesis: the positive six-month recency result and marked within-2005 carrier changes suggest older observations may still have too much influence. Halve the recency half-life to three months, keeping the now-successful monthly balancing and pooled holiday features. This is a substantial weighting change (roughly 13:1 newest-to-oldest month influence versus 3.6:1), with a clear risk of losing useful sample size.

Result: commit `195ff17`, Eval AUC **0.6885**, **discard**. Run time: 14.1s (training 3.7s, eval 10.4s, ok)

Observation: three-month decay lost 0.0003; the six-month compromise retains valuable older examples.

## Experiment 30 — stronger leaf-level regularization

Category: exploration. Hypothesis: require larger effective leaves and shrink small regional/carrier effects more strongly, rather than reducing global tree depth or rounds. Raise min_child_weight from 20 to 100 and reg_lambda from 10 to 50, retaining the feature representation and 600 shallow rounds. This explores a substantially more conservative leaf-fitting regime motivated by recurring small overfitting losses.

Result: commit `bef1ceb`, Eval AUC **0.6889**, **keep**. Run time: 13.5s (training 3.2s, eval 10.3s, ok)

## Synthesis after 30 experiments

Best: **0.6889**, commit `bef1ceb`, +0.0146 over baseline. The last ten experiments added monthly label balancing (+0.0002), pooled holiday proximity (+0.0006), and stronger leaf regularization (+0.0001). Extra rounds, coarser bins, finer day balancing, five-seed averaging, more landmarks and stronger recency weighting failed. Pairwise ranking was meaningfully worse. These small recent gains call for distinct regularization mechanisms rather than tiny numeric retuning.

Research refresh: [DART documentation](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html) describes tree dropout and its slower training; [Does label smoothing mitigate label noise?](https://proceedings.mlr.press/v119/lukasik20a.html) investigates softer targets as a regularizer. The latter results are not specific guarantees for XGBoost or this dataset, but motivate a test given unobserved weather and operational causes.

## Experiment 31 — dropout boosting

Category: exploration. Hypothesis: occasional tree dropout prevents later trees from depending too strongly on a particular early fit, improving robustness beyond row sampling. Test DART with rate_drop=0.1 and skip_drop=0.8. Use 300 rounds at eta 0.08 (same nominal learning-rate-times-rounds as the current model) to accommodate DART's more expensive repeated prediction within the 60-second training limit. Other feature, weighting and leaf regularization choices remain fixed.

Result: commit `d0cd78f`, Eval AUC **0.6883**, **discard**. Run time: 42.6s (training 32.4s, eval 10.2s, ok)

Observation: DART lost 0.0006 and took 32.4s to train versus 3.2s for the kept model.

## Experiment 32 — mild label smoothing

Category: exploration. Hypothesis: a 10% mixture with uniform labels can reduce overconfidence in residuals driven by unavailable weather/operations information. Implement logistic gradients for training targets 0.05/0.95; keep the actual binary labels in prepare and the harness unchanged. Preserve all sample weights in both gradient and Hessian. This is regularization, not a claim that the observed labels are erroneous. Source: [Lukasik et al.](https://proceedings.mlr.press/v119/lukasik20a.html); implementation checked against [XGBoost custom objective docs](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html) and the installed sklearn wrapper's sample-weight handling and logistic prediction link.

Result: commit `b032eb6`, Eval AUC **0.6884**, **discard**. Run time: 14.1s (training 3.9s, eval 10.2s, ok)

Observation: label smoothing lost 0.0005 despite correct weighted derivatives; keep standard logistic loss.

## Experiment 33 — additive calendar effects

Category: exploration. Hypothesis: weekday/holiday effects should transfer better as shared calendar effects than as detailed interactions with particular carriers, airports and departure times. Use two disjoint interaction groups: weekday plus holiday proximity, and all operational/geographic features. This preserves flexible operational trees while making their contribution additive with the calendar component. [XGBoost interaction constraints](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) supports explicitly excluding potentially spurious feature interactions.

Result: commit `5f6d3bb`, Eval AUC **0.6864**, **discard**. Run time: 13.5s (training 3.2s, eval 10.3s, ok)

Observation: forcing calendar effects to be additive lost 0.0025, showing that some weekday/holiday interactions are important.

## Experiment 34 — smooth seasonality with geographic context

Category: exploration. Hypothesis: annual sine/cosine features can capture regional seasonal differences now that geographic features and within-month label balancing are present. This differs from the rejected raw month feature: cyclic numeric features favor nearby seasons, and monthly weighting removes global month-label prevalence differences. Add sine/cosine of month only (no raw day-of-year) to interact with the smooth geography. Motivated by the earlier cyclic feature reference and the current model's successful regional representation.

Result: commit `eb69008`, Eval AUC **0.6898**, **keep**. Run time: 13.7s (training 3.3s, eval 10.5s, ok)

Observation: smooth annual features gained 0.0009 to 0.6898 with geographic context and monthly balancing. The original month ablation does not imply all seasonal information is harmful; representation and weighting matter.

## Experiment 35 — reconstruct a consistent geographic distance model

Category: follow-up. Hypothesis: shortest-path mileage overestimates geographical separation when a direct training route is absent. Fit 3D airport positions to observed median route mileages, initialized by classical MDS of the shortest-path matrix, and compute the existing six landmark distances from those positions. This changes only the fitted geographic lookup, not feature count or model capacity. Equal weight per unique route pair prevents raw flight counts from entering the representation. Use sparse least squares with a robust loss and a bounded iteration count. Sources: [distance-based localization](https://arxiv.org/abs/1811.12803), [SciPy least_squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html). The result is an approximate learned geometry, not external airport coordinates.

Result: commit `fa4ece7`, Eval AUC **0.6895**, **discard**. Run time: 15.1s (training 4.6s, eval 10.4s, ok)

Observation: fitting a consistent 3D distance geometry lost 0.0003; the simpler shortest-path landmarks retain slightly more useful information.

## Experiment 36 — leaf-wise growth at fixed leaf budget

Category: exploration. Hypothesis: loss-guided growth allocates a fixed 16-leaf budget to the most useful regional/seasonal interactions rather than enforcing balanced depth-4 paths. Use grow_policy=lossguide, max_leaves=16, max_depth=0, retaining strong leaf regularization and 600 rounds. This offers deeper selected paths without the 64-leaf capacity of the failed depth-6 models. Sources: [XGBoost tree methods](https://xgboost.readthedocs.io/en/stable/treemethod.html) and grow_policy/max_leaves definitions in the parameter reference.

Result: commit `a780ad1`, Eval AUC **0.6901**, **keep**. Run time: 14.0s (training 3.6s, eval 10.5s, ok)

Observation: loss-guided 16-leaf trees improved AUC by 0.0003 to 0.6901; adaptive path allocation helps without greatly expanding leaf capacity.

## Experiment 37 — feature sampling across trees

Category: follow-up. Hypothesis: time and landmark-distance features are strongly redundant; sampling 70% of features per tree can diversify spatial/time boundaries and reduce dependence on a few early split choices. Add colsample_bytree=0.7 to the kept leaf-wise model, with no other change. This isolates feature sampling rather than the joint within-step forest/row-sampling changes tested in experiment 11.

Result: commit `43b5a4f`, Eval AUC **0.6904**, **keep**. Run time: 14.2s (training 3.4s, eval 10.8s, ok)

Observation: 70% feature sampling gained 0.0003, supporting diversification across correlated geographic and time representations.

## Experiment 38 — larger adaptive leaf budget

Category: follow-up. Hypothesis: the successful leaf-wise growth and feature sampling can support more regional/seasonal interaction detail under strong minimum-child and L2 constraints. Double max_leaves from 16 to 32, retaining 600 rounds and all regularization. This tests moderate leaf capacity in the newly successful growth/sampling regime, rather than the earlier unconstrained depth-6 regime.

Result: commit `d1471cb`, Eval AUC **0.6905**, **keep**. Run time: 14.8s (training 4.3s, eval 10.5s, ok)

Observation: increasing the adaptive leaf budget to 32 gained 0.0001; keep according to the printed-AUC rule despite the very small improvement.

## Experiment 39 — full-row fitting with feature sampling

Category: follow-up. Hypothesis: strong leaf constraints and feature sampling may provide sufficient regularization, while using all rows reduces stochastic gradient noise and preserves information for sparse carrier-region combinations. Set subsample=1.0 and keep colsample_bytree=0.7. This isolates row sampling after the successful feature-sampling change.

Result: commit `09f5601`, Eval AUC **0.6900**, **discard**. Run time: 15.6s (training 4.8s, eval 10.8s, ok)

Observation: full-row fitting lost 0.0005; both row and feature sampling remain useful.

## Experiment 40 — squared-error probability regression

Category: exploration. Hypothesis: changing from logistic to squared-error fitting changes which residuals and regions receive curvature weight, potentially improving ranking under unobserved outcome variability. Train an XGBRegressor on the unchanged 0/1 labels with reg:squarederror. Scale minimum child weight and L2 by four (400 and 200), approximating the Hessian scale change from logistic near p=0.5 to constant unit curvature. A monotonic sigmoid of the regression score provides bounded two-column output for the unchanged harness, preserving ranking without claiming calibration. [XGBoost tree-method discussion](https://xgboost.readthedocs.io/en/stable/treemethod.html) explicitly contrasts constant versus varying Hessians.

Result: commit `782b2b3`, Eval AUC **0.6905**, **discard**. Run time: 14.7s (training 4.2s, eval 10.5s, ok)

## Synthesis after 40 experiments

Best: **0.6905**, commit `d1471cb`, +0.0162 over baseline. Smooth seasonality became useful after geographic representation and monthly balancing. Loss-guided trees, feature sampling and a 32-leaf budget added smaller gains. DART, label smoothing, additive-only calendar effects and full-row fitting failed. Squared-error fitting matched the printed best but was discarded because its wrapper was not simpler or faster. It remains a candidate for a complementary-loss ensemble.

Research refresh: searched airport/network role research, including [Airport dominance, route network design and flight delays](https://doi.org/10.1016/j.tre.2022.103000), to motivate unsupervised route-distance summaries rather than prohibited traffic counts. Most published graph-delay systems require contemporaneous delays, weather or traffic frequencies, which are unavailable or excluded here. A permitted adaptation is typical unique-route mileage and the current flight's relative distance. Also retain the previously read probability-averaging reference for a distinct-loss ensemble.

## Experiment 41 — combine logistic and squared-error fits

Category: follow-up. Hypothesis: the equally performing but differently weighted losses from experiment 40 make complementary ranking errors. Fit both current logistic and squared-error variants on the same training data and weights, then average logistic probability and the regression score clipped to [0,1] with equal weights. The clipping is a fixed probability-interface choice, not fitted calibration; no constituent model is separately scored within this run. This differs from the failed same-loss seed ensemble.

Result: commit `a2015c3`, Eval AUC **0.6907**, **keep**. Run time: 18.3s (training 7.6s, eval 10.8s, ok)

Observation: the equal logistic/squared-error blend gained 0.0002, unlike same-loss seed averaging. Complementary loss geometry appears useful.

## Experiment 42 — typical route-distance context

Category: exploration. Hypothesis: an airport's typical unique-route mileage distinguishes regional versus longer-haul operational context beyond physical location. Fit median nonzero direct-route mileage per airport from the symmetric training route-distance matrix, weighting each distinct route equally. Add that median and actual-distance/median for origin and destination. No traffic counts, frequencies, targets or evaluation data enter these lookups. This is an adaptation of the network-role research in the latest synthesis.

Result: commit `134f5a8`, Eval AUC **0.6913**, **keep**. Run time: 19.4s (training 8.3s, eval 11.1s, ok)

Observation: typical unique-route mileage and relative distance gained 0.0006, supporting operational context beyond pure location.

## Experiment 43 — directional and destination-time proxies

Category: exploration. Hypothesis: destination-side time-of-day constraints affect departure risk, and explicit direction/time proxies make them easier to learn. Derive east/west progress from LAX/JFK landmark-distance differences and a second directional projection from DFW/ORD. Normalize direction by flight mileage. Approximate flight-end local minutes with departure + distance/7.5 + 30 minutes + 75 minutes per thousand miles eastward progress; these are fixed heuristic constants, not claimed actual scheduled duration or time zones. Add cyclic features of that proxy. The [flight-delay feature research](https://www.sciencedirect.com/science/article/pii/S092523122101612X) motivates schedule/distance context; this proxy is my adaptation to the available fields. Every value is computed per row from existing inputs and training-fitted geography.

Result: commit `67d85fe`, Eval AUC **0.6913**, **discard**. Run time: 21.6s (training 10.1s, eval 11.5s, ok)

Observation: direction and approximate arrival-time proxies tied 0.6913 but increased runtime and complexity, so discard.

## Experiment 44 — Hessian-weighted split proposals

Category: exploration. Hypothesis: the logistic member benefits from approximate splits that refresh Hessian-weighted candidate quantiles at each tree, concentrating resolution where its current uncertainty lies. Set tree_method=approx for the logistic classifier, retain hist for the squared-error regressor with constant Hessian. All features, weights and leaf budgets stay fixed. [XGBoost tree-method documentation](https://xgboost.readthedocs.io/en/stable/treemethod.html) explains this distinction and suggests approx may help varying-Hessian objectives.

Result: commit `5dad745`, Eval AUC **0.6915**, **keep**. Run time: 45.2s (training 34.1s, eval 11.1s, ok)

Observation: refreshing Hessian-weighted split candidates improved AUC from 0.6913 to 0.6915. Training rose to 34.1s, still under the 60s limit.

## Experiment 45 — route-distance diversity

Category: follow-up. Hypothesis: the successful typical-route mileage feature can be complemented by distance diversity: airports with a mixture of short and long routes may have different operational roles than airports with uniformly similar routes. Add the interquartile range of unique-route distance divided by its median, one value per origin/destination. Use the same training-only symmetric direct-route matrix, with no route-frequency weighting. This tests dispersion separately from the central distance and flight-relative distance retained in experiment 42; it is motivated by the same cited airport-network-role research.

Result: commit `bb78a8b`, Eval AUC **0.6913**, **discard**. Run time: 48.3s (training 36.6s, eval 11.7s, ok)

## Experiment 46 — remove redundant departure-time representations

Category: ablation/simplification. Hypothesis: the flight-day minute coordinate and cyclic sine/cosine already preserve departure time; raw HHMM and rounded hour may unnecessarily consume feature-sampling slots and split opportunities. Remove CRSDepTime and DepHour as model columns, retaining their input use to derive the remaining representations. Training-only gain inspection of experiment 44 shows DepHour is the logistic member's least-used feature, though CRSDepTime is strong; the ablation tests whether that importance is redundant rather than assuming it is. Equal AUC qualifies for keep because two columns and code are removed.

Result: commit `8fe9d77`, Eval AUC **0.6915**, **keep**. Run time: 44.2s (training 33.0s, eval 11.2s, ok)

Observation: the two departure-time columns were redundant at the printed precision: 0.6915 is unchanged and training fell from 34.1s to 33.0s. Keep the simpler 26-feature representation.

## Experiment 47 — single-model ablation after improved logistic fitting

Category: ablation/simplification. Hypothesis: the route-context features and Hessian-weighted splits introduced after the ensemble was retained may have strengthened the logistic member enough that the squared-error member is no longer useful. Remove the regressor and averaging wrapper, preserving the logistic model, training weights and features exactly. This tests the ensemble's continued value after substantial constituent changes, rather than repeating the earlier same-loss ensemble comparison. An equal score would keep the faster and much simpler single estimator.

Result: commit `3da3274`, Eval AUC **0.6910**, **discard**. Run time: 41.3s (training 30.6s, eval 10.8s, ok)

Observation: removing the squared-error member reduced AUC to 0.6910. Its complementary errors remain useful after the logistic improvements.

## Experiment 48 — reuse fitted categorical integer codes

Category: ablation/simplification of preparation overhead. Hypothesis: precomputing label-to-code maps avoids repeating categorical factorization for every evaluated row, without changing the feature matrix or model. Use Categorical.from_codes with the same training-fitted dtypes and -1 for unseen labels. [Pandas documentation](https://pandas.pydata.org/docs/reference/api/pandas.Categorical.from_codes.html) describes this constructor specifically for avoiding factorization and documents -1 as missing. Verify feature equality on training rows plus an unseen carrier and benchmark only preparation runtime; the harness remains the sole AUC metric. Keep an equal AUC only if preparation is faster.

Preparation check: identical feature frames and labels for 300 training rows including an unseen carrier. Three alternating timing passes over 299 individual rows averaged 0.2319s before versus 0.1625s after (29.9% faster). No AUC was computed outside the harness.

Result: commit `c47dcbd`, Eval AUC **0.6915**, **keep**. Run time: 44.5s (training 35.5s, eval 9.0s, ok)

Observation: fitted categorical codes preserved AUC at 0.6915; evaluation fell from 11.2s to 9.0s and the isolated preparation benchmark was 29.9% faster. Keep on preparation speed despite small training-time variability.

## Experiment 49 — reject weak logistic splits

Category: follow-up. Hypothesis: the improved approximate logistic trees may still spend their final leaves on noisy low-gain boundaries. Set gamma=5 for the logistic member, keeping gamma=0 for the unchanged squared-error member. Training-only tree inspection found gain percentiles 10%=4.47, 25%=5.91 and median=8.65; thus 5 deliberately targets the weaker internal splits, whereas gamma=2 would affect under 0.05%. [XGBoost's gamma documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) defines this as a minimum required loss reduction. This tests split acceptance separately from the existing minimum-child and L2 constraints.

Result: commit `43097e4`, Eval AUC **0.6918**, **keep**. Run time: 41.0s (training 32.2s, eval 8.9s, ok)

Observation: gamma=5 for the logistic member improved Eval AUC to 0.6918 and reduced training to 32.2s. Explicitly rejecting weak splits complements leaf-size and L2 regularization.

## Final summary

Completed 49 experiments after the baseline on branch `oct6`: 23 kept, 26 discarded, 0 crashes. Baseline Eval AUC was 0.6743; best printed Eval AUC is **0.6918** (**+0.0175**) at `43097e4b63c0d0b17090aa92ba825521795cf299`. Final runtime was 41.0s: 32.2s training and 8.9s evaluation (independently rounded components). The branch is left at this best kept commit and its artifact is `artifacts/43097e4b63c0d0b17090aa92ba825521795cf299.pkl`.

What worked: replacing airport IDs with training-fitted distance geography; removing brittle raw calendar categories while retaining smooth seasonality and pooled holiday proximity; recency and monthly class-balance weights; typical unique-route mileage; strongly regularized leaf-wise trees with row and feature sampling; complementary logistic/squared-error fitting; Hessian-weighted logistic split candidates; and a minimum split-gain threshold. Redundant departure-time columns could be removed without losing printed AUC, and fitted categorical-code maps reduced per-row preparation time while preserving features exactly.

What did not help: deeper unconstrained trees, raw route categories, target encodings fitted on a reduced disjoint training subset, extra geometric coordinates, same-loss seed ensembles, pairwise ranking, DART, label smoothing, additive-only calendar interactions, full-row fitting, approximate arrival-time proxies, and route-distance dispersion. Removing the squared-error ensemble member also hurt. These are conditional findings for the configurations tested, not claims that the methods never work.

Current interpretation: transferable schedule, geography and broad operational context matter more than fine airport/calendar identity. Regularization and moderate diversity help bridge the training/evaluation year shift. Many marginal gains are only a few printed AUC units, so the unseen holdout remains the human's independent check.

Next ideas: investigate carrier-specific recency schedules from training-year stability, test a smaller landmark subset, and examine whether a preregistered unequal loss blend improves the current recipe. Each should remain a separate committed harness experiment.

Final checks: every successful recorded commit has a saved artifact; only train.py differs from the baseline; tracked worktree is clean; the required harness call remains the last line. The final saved prepare matches the committed code, is identical for batch versus single-row calls, ignores target values when building features, and accepts unseen carriers/airports. The deserialized model produces finite two-column probabilities for training samples and unseen-category checks. No extra AUC metric was computed.
