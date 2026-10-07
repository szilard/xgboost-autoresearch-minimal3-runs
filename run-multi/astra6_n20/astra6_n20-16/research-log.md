# Research log: oct7

## Setup — 2026-10-07

- Run branch: `oct7`, created directly from starting commit `b15ec66`.
- Read `program.md`, `train.py`, and `harness.py`.
- Confirmed `data/train.csv` and `data/eval.csv` exist.
- Checked training data only: 200,000 rows, all nine expected columns, 100,000 labels of each class, and no missing values.
- Verified imports: Python 3.14.4, NumPy 2.5.3, pandas 3.0.6, XGBoost 3.4.1, scikit-learn 1.9.1, and cloudpickle 3.1.2. Eight logical CPUs are available.
- Initialized `output/results.tsv` with the required header and no result rows.
- Experiment clock has not started; no training or evaluation has run.

After the user confirms the run, the first action is `python3 harness.py start`. The first experiment will run the unchanged baseline through the harness. Research must precede the first non-baseline experiment.

Outcome: **keep**; commit `b15ec66`; Eval AUC **0.6743**. Training time: 0.7s Eval time: 31.1s Eval AUC: 0.6743 Run time: 32.8s (training 1.5s, eval 31.3s, ok)

## Experiment 1 — exploration: regularized longer boosting

Hypothesis: 100 trees underfit; 500 trees at learning rate 0.05 with min_child_weight=20 and reg_lambda=10 can learn more stable interactions across years. Native categories and all features remain as in the baseline. Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html and https://xgboost.readthedocs.io/en/stable/parameter.html. Also reviewed categorical partitioning and scikit-learn time-feature engineering documentation.

Outcome: **discard**; commit `de6f683`; Eval AUC **0.6710**. Training time: 2.9s Eval time: 30.7s Eval AUC: 0.6710 Run time: 34.7s (training 3.7s, eval 31.0s, ok)

## Experiment 2 — ablation/simplification: faster equivalent preparation

Hypothesis: constructing one DataFrame with cached categorical dtypes removes repeated copying and redundant isin checks without changing features. A scratch check on all training rows confirmed exact feature equality; 400 row calls fell from 1.012s to 0.298s. Keep an equal AUC only if the harness confirms lower runtime. The longer boosting model lost 0.0033 AUC, suggesting cross-year overfitting or a need for different features rather than more trees.

Outcome: **keep**; commit `b12cec4`; Eval AUC **0.6743**. Training time: 0.6s Eval time: 10.1s Eval AUC: 0.6743 Run time: 11.8s (training 1.4s, eval 10.3s, ok)

## Experiment 3 — ablation: drop day of month

Hypothesis: arbitrary day-of-month category partitions capture weather/date effects in 2005 that do not recur in 2006. Remove this feature while leaving all baseline hyperparameters and other features intact. Baseline gain importance for day of month was 0.0398. Domain background: https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf (search result highlights calendar and holiday features); time-feature documentation https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html.

Outcome: **keep**; commit `d9eff0c`; Eval AUC **0.6759**. Training time: 0.6s Eval time: 9.3s Eval AUC: 0.6759 Run time: 10.9s (training 1.4s, eval 9.5s, ok)

## Experiment 4 — follow-up: shallower regularized boosting

Hypothesis: the day-of-month ablation gain (+0.0016) and failure of 500 depth-6 trees point toward excess variance. Test depth 4, 300 rounds, eta 0.05, min_child_weight 20 and lambda 10 to learn smooth main effects and lower-order interactions. Unlike experiment 1, this reduces tree depth and total leaf capacity. Source: XGBoost parameter-tuning documentation already reviewed.

Outcome: **keep**; commit `7adb656`; Eval AUC **0.6800**. Training time: 1.0s Eval time: 9.0s Eval AUC: 0.6800 Run time: 11.0s (training 1.8s, eval 9.2s, ok)

## Experiment 5 — exploration: carrier-airport interactions

Hypothesis: explicit carrier-origin and carrier-destination categories expose stable hub/operational effects to shallow trees. Fit category vocabularies on train only, and construct each row independently. Native category background: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html. Use explicit categorical codes so unknown categories become missing without pandas deprecation warnings; this preserves the prior feature meanings.

Outcome: **discard**; commit `4bf0fe8`; Eval AUC **0.6730**. Training time: 1.4s Eval time: 8.7s Eval AUC: 0.6730 Run time: 11.2s (training 2.3s, eval 8.9s, ok)

## Experiment 6 — follow-up: restrict categorical partitions

Hypothesis: the large loss from carrier-airport categories (-0.0070) suggests category partitions are exploiting sparse 2005-specific patterns. Set max_cat_threshold=16 instead of the default 64 while retaining the best feature set and depth-4 model. This tests categorical regularization rather than more engineered interactions. Source: https://xgboost.readthedocs.io/en/stable/parameter.html#parameters-for-categorical-feature. Experiment 5 passed batch/single-row invariance and unseen-category checks, so its loss was predictive rather than an inconsistent transform.

Outcome: **keep**; commit `294e6e1`; Eval AUC **0.6815**. Training time: 0.9s Eval time: 8.9s Eval AUC: 0.6815 Run time: 10.8s (training 1.7s, eval 9.1s, ok)

## Experiment 7 — follow-up: one-hot categorical splits

Hypothesis: the gain from limiting category partitions suggests arbitrary category groupings overfit. Set max_cat_to_onehot=512 so all existing categorical predictors use one-versus-rest splits. This is a different split strategy, not a small threshold adjustment. Keep the same shallow tree budget and regularization. Source: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html.

Outcome: **discard**; commit `ae172c7`; Eval AUC **0.6754**. Training time: 1.6s Eval time: 8.9s Eval AUC: 0.6754 Run time: 11.5s (training 2.4s, eval 9.1s, ok)

## Experiment 8 — exploration: constrain calendar interactions

Hypothesis: month/weekday interactions with airports or carriers encode local 2005 events that do not transfer to 2006. Allow calendar variables to interact with departure time, and allow operational variables to interact with departure time, but prevent calendar and operational variables appearing on the same tree path. Category grouping itself is useful: the one-hot trial lost 0.0061. Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html. Also researched target encoding; defer it because naive in-sample encodings leak labels and the task forbids cross-validation.

Outcome: **discard**; commit `133a267`; Eval AUC **0.6802**. Training time: 1.0s Eval time: 8.9s Eval AUC: 0.6802 Run time: 11.0s (training 1.8s, eval 9.2s, ok)

## Experiment 9 — exploration: smooth cyclic seasonality

Hypothesis: month partitions may encode noisy 2005 seasonal groupings; numeric month and sine/cosine coordinates bias splits toward adjacent or cyclic seasons. Replace categorical Month with these three row-local features. Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html. Inspected the prior constrained model: none of 4,375 leaf paths mixed calendar and operational predictors; its score loss was not caused by failed constraints.

Outcome: **keep**; commit `9fede9d`; Eval AUC **0.6817**. Training time: 0.9s Eval time: 10.1s Eval AUC: 0.6817 Run time: 12.0s (training 1.7s, eval 10.3s, ok)

## Experiment 10 — exploration: clock components

Hypothesis: departure hour captures broad congestion while minute within the hour can expose scheduled departure banks shared across hours. Add both to the existing raw HHMM value, with unchanged model settings. Baseline departure-time gain importance was 0.5966. Domain source: https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf; time feature background from the scikit-learn example.

Outcome: **keep**; commit `7aae707`; Eval AUC **0.6818**. Training time: 1.1s Eval time: 11.2s Eval AUC: 0.6818 Run time: 13.3s (training 1.9s, eval 11.4s, ok)

## Synthesis after 10 experiments

Best: 0.6818 at 7aae707, +0.0075 over baseline. Strongest gains came from removing day of month (+0.0016), shallow regularized trees (+0.0041), and restricted category partitions (+0.0015). Categorical carrier-airport interactions and unrestricted longer boosting hurt; one-hot splits also underperformed, so some category pooling remains useful. Cyclic month and clock components gave small positive gains. Current theory: stable, low-complexity temporal and airport effects generalize better across years than fine categorical interactions. Next investigate label-free geographic representations and stochastic regularization. New research: https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html and https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.

## Experiment 11 — exploration: infer airport geometry from route distances

Hypothesis: a low-dimensional airport representation can share geographic/seasonal structure without supervised high-cardinality route partitions. Fit a symmetric route-distance graph from training medians, complete missing distances via shortest paths, and use classical multidimensional scaling to fit two coordinates per airport. Only fixed coordinate lookups are applied in prepare; no counts, targets, external data, or evaluation data are used in fitting. Sources: scikit-learn Isomap and SciPy shortest_path documentation.

Outcome: **discard**; commit `34cf7f7`; Eval AUC **0.6818**. Training time: 1.1s Eval time: 17.9s Eval AUC: 0.6818 Run time: 20.1s (training 2.0s, eval 18.1s, ok)

## Experiment 12 — follow-up: depth-three boosting

Hypothesis: the large depth-6 to depth-4 gain suggests another reduction in interaction order may improve transfer. Use depth 3 and 500 rounds at eta 0.05, retaining categorical and leaf regularization. The higher round count compensates for smaller trees; this has fewer maximum leaves than the current depth-4 model. The geometry trial passed row-invariance checks on a connected 284-airport graph but only tied AUC and was slower, so was discarded.

Outcome: **discard**; commit `d427326`; Eval AUC **0.6802**. Training time: 1.4s Eval time: 10.9s Eval AUC: 0.6802 Run time: 13.3s (training 2.2s, eval 11.1s, ok)

## Experiment 13 — exploration: boosted subsampled forests

Hypothesis: average three independently subsampled trees per boosting round to reduce variance while keeping depth four and the current boosting schedule. Set num_parallel_tree=3 and subsample=0.75; retain all columns so the strong departure-time signal remains available. This tests stochastic averaging rather than further reducing interaction order. Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html.

Outcome: **keep**; commit `4f348e5`; Eval AUC **0.6820**. Training time: 4.7s Eval time: 11.4s Eval AUC: 0.6820 Run time: 17.1s (training 5.5s, eval 11.7s, ok)

## Experiment 14 — follow-up: feature-subsampled boosted forests

Hypothesis: the small gain from row-subsampled forests may improve further when their splits are less correlated. Set colsample_bynode=0.8; keep three trees per round and 0.75 row subsampling. Redundant time encodings should keep departure-time information available while varying other split candidates. Source: XGBoost random-forest tutorial, which recommends split-level column sampling.

Outcome: **keep**; commit `c42b375`; Eval AUC **0.6824**. Training time: 5.7s Eval time: 11.0s Eval AUC: 0.6824 Run time: 17.7s (training 6.5s, eval 11.3s, ok)

## Experiment 15 — follow-up: prune low-gain splits

Hypothesis: both row and feature randomization helped, suggesting weak splits still fit noise. Set gamma=5 to require stronger improvement from every split, retaining the successful boosted-forest settings. This regularizes split acceptance rather than depth or leaf weights. Source: https://xgboost.readthedocs.io/en/stable/parameter.html (gamma).

Outcome: **discard**; commit `310c56c`; Eval AUC **0.6823**. Training time: 4.6s Eval time: 11.2s Eval AUC: 0.6823 Run time: 16.8s (training 5.4s, eval 11.4s, ok)

## Experiment 16 — exploration: major-holiday proximity

Hypothesis: recurring holiday travel patterns may transfer even though raw day-of-month categories did not. Add one clipped nearest-holiday-distance feature for New Year, July 4, Thanksgiving and Christmas. Infer the fourth Thursday in November from each row’s month/day/weekday; the non-leap calendar matches both documented years. Do not expose raw day of year or day of month to the model. Domain source explicitly includes holiday proximity: https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf.

Outcome: **keep**; commit `fb4b04f`; Eval AUC **0.6854**. Training time: 4.4s Eval time: 14.0s Eval AUC: 0.6854 Run time: 19.5s (training 5.2s, eval 14.2s, ok)

## Experiment 17 — follow-up: signed holiday offset

Hypothesis: the +0.0030 holiday-distance gain reflects stable travel-calendar structure, but absolute distance conflates outbound pre-holiday travel with post-holiday return travel. Add a signed offset to the nearest of the same four holidays, clipped at 21 days, keeping the successful absolute-distance feature. The preceding feature passed known-date tests for Thanksgiving in both years and batch/single-row equality.

Outcome: **discard**; commit `fa02373`; Eval AUC **0.6851**. Training time: 4.3s Eval time: 14.4s Eval AUC: 0.6851 Run time: 19.8s (training 5.2s, eval 14.7s, ok)

## Experiment 18 — follow-up: extend holiday coverage

Hypothesis: the successful nearest-holiday distance can capture additional recurring travel peaks around Memorial Day and Labor Day. Extend the same single feature from four to six holidays, retaining the 21-day cap and avoiding the discarded signed offset. Infer dates row by row from weekday/calendar arithmetic. Source for date rules: https://www.opm.gov/faq/payleave/what-are-federal-holidays.ashx.

Outcome: **discard**; commit `437d862`; Eval AUC **0.6854**. Training time: 4.4s Eval time: 14.1s Eval AUC: 0.6854 Run time: 19.5s (training 5.2s, eval 14.3s, ok)

## Experiment 19 — exploration: pairwise ranking objective

Hypothesis: AUC measures ordering, so pairwise logistic loss may improve ranking over pointwise binary log loss. Train XGBRanker on a single training query group, using mean pair sampling with one pair per row and no lambda normalization. Keep the best feature preparation and boosted-forest settings. A serializable wrapper maps ranking scores monotonically through a sigmoid to satisfy the unchanged harness predict_proba interface; this is not probability calibration. Only the harness Eval AUC is scored. Source: https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html.

Outcome: **discard**; commit `1c48f21`; Eval AUC **0.6760**. Training time: 15.3s Eval time: 13.9s Eval AUC: 0.6760 Run time: 30.3s (training 16.1s, eval 14.2s, ok)

## Experiment 20 — exploration: piecewise monotonic departure time

Hypothesis: the training delay rate broadly rises from morning to 20:00 then falls, and flexible time splits may fit local noise. Replace raw HHMM and hour with an increasing DayProgress capped at 20:00 and a decreasing LateProgress after 20:00; allow a separate overnight indicator and retain minute within hour. Apply monotone constraints only to the two progress features. Source: https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html. Training EDA supported the broad curve; this remains a test, not an assumption about eval labels.

Outcome: **discard**; commit `05fc71d`; Eval AUC **0.6840**. Training time: 4.4s Eval time: 14.2s Eval AUC: 0.6840 Run time: 19.7s (training 5.3s, eval 14.4s, ok)

## Synthesis after 20 experiments

Best: 0.6854 at fb4b04f, +0.0111 over baseline. Experiments 13–14 improved from 0.6818 to 0.6824 through row and feature randomness, then four-holiday proximity added 0.0030. Geography tied at extra cost; depth three, pairwise ranking, and monotonic departure-time structure underperformed. Signed holiday offsets hurt slightly and broader holiday coverage tied without simplification. Working theory: recurring calendar structure is valuable, but extra feature detail and excessively rigid shape constraints can hurt cross-year ranking. Next prioritize ablations, boosting dynamics and feature precision. New research at this pause: XGBoost DART tutorial and histogram tree-method documentation.

## Experiment 21 — ablation: remove cyclic month coordinates

Hypothesis: numeric month plus the strong holiday feature may now describe seasonality adequately; the extra sine/cosine representations gave only a small early gain and may add unstable split choices under feature sampling. Remove MonthSin and MonthCos while retaining MonthNumber. Keep equal AUC because this is a simplification.

Outcome: **discard**; commit `0f72d26`; Eval AUC **0.6849**. Training time: 4.6s Eval time: 14.0s Eval AUC: 0.6849 Run time: 19.6s (training 5.4s, eval 14.2s, ok)

## Experiment 22 — simplification/performance: direct frozen lookups

Hypothesis: explicit categorical codes avoid deprecated unknown-category conversion, and direct frozen calendar lookups avoid constructing temporary pandas mapping objects per evaluation row. Preserve feature names, ordering, values and model parameters. Require exact training-feature equivalence plus equal AUC and lower harness runtime for a tie keep.

Outcome: **keep**; commit `40b0506`; Eval AUC **0.6854**. Training time: 4.4s Eval time: 7.6s Eval AUC: 0.6854 Run time: 13.0s (training 5.2s, eval 7.9s, ok)

## Experiment 23 — ablation: remove minute within hour

Hypothesis: minute within hour mainly encodes incidental timetable detail. It has the lowest gain importance (0.0041), whereas raw departure time and hour together account for 0.5893. Remove DepartureMinute while retaining both broad time variables. Keep an AUC tie as a simplification. Experiment 22 preserved all training features exactly and lowered harness evaluation from 14.0s to 7.6s.

Outcome: **keep**; commit `efe0916`; Eval AUC **0.6854**. Training time: 4.4s Eval time: 7.3s Eval AUC: 0.6854 Run time: 12.8s (training 5.2s, eval 7.5s, ok)

## Experiment 24 — exploration: departure relative to route schedule

Hypothesis: a flight scheduled late relative to its route’s typical schedule may have different inherited-delay risk from one that is simply late in local clock time. Fit median scheduled minutes by origin/destination using training data only; add departure minutes minus this fixed median. No label statistics or count features are used. This follows the safe lookup pattern in program.md; external reference: https://pandas.pydata.org/docs/user_guide/groupby.html.

Outcome: **keep**; commit `fabdf66`; Eval AUC **0.6856**. Training time: 6.2s Eval time: 8.7s Eval AUC: 0.6856 Run time: 16.0s (training 7.1s, eval 8.9s, ok)

## Experiment 25 — exploration: training recency weights

Hypothesis: airline operations may drift between 2005 training and 2006 evaluation, so later training months could be more representative. Apply exponentially decaying sample weights with a 12-month half-life, normalized to mean one to preserve regularization scale. Compute weights from the prepared MonthNumber feature; no evaluation data or extra scoring is used. This is an adaptation, not a replication, of temporal weighting discussed in https://arxiv.org/abs/1602.04435. The first direct pandas median URL returned 404; the linked GroupBy guide was successfully read instead.

Outcome: **keep**; commit `f9219ca`; Eval AUC **0.6858**. Training time: 4.4s Eval time: 8.2s Eval AUC: 0.6858 Run time: 13.7s (training 5.3s, eval 8.4s, ok)

## Experiment 26 — follow-up: stronger recency weighting

Hypothesis: the gain from modest temporal weighting may reflect real operational drift. Shorten the half-life from twelve to six months to distinguish a robust recency benefit from a small perturbation; this materially reduces early-year influence and risks losing seasonal coverage. Keep the mean-one normalization and all model settings. Motivation: experiment 25 improved from 0.6856 to 0.6858.

Outcome: **discard**; commit `8592c7d`; Eval AUC **0.6851**. Training time: 4.4s Eval time: 8.1s Eval AUC: 0.6851 Run time: 13.6s (training 5.2s, eval 8.3s, ok)

## Experiment 27 — follow-up: smaller boosting steps

Hypothesis: the current randomized forest may fit more stably with 600 rounds at eta 0.025 than 300 rounds at eta 0.05. Hold cumulative nominal shrinkage constant and retain features, recency weighting and regularization. This tests path stability rather than simply extending the boosting horizon. Source: XGBoost parameter-tuning guidance on coupling smaller eta with more rounds. Six-month weighting lost 0.0007, so twelve months remains best.

Outcome: **discard**; commit `9cfc685`; Eval AUC **0.6855**. Training time: 9.6s Eval time: 8.3s Eval AUC: 0.6855 Run time: 19.1s (training 10.5s, eval 8.6s, ok)

## Experiment 28 — exploration: tree dropout

Hypothesis: dropping subsets of existing trees during boosting may distribute predictive work more evenly and reduce overfitting beyond row/column sampling. Use DART with 180 rounds, eta 0.1, one tree per round, rate_drop=0.05, skip_drop=0.5 and forest normalization. The compact configuration accounts for DART’s slower prediction-buffer behavior under the 60-second training cap. Keep features, recency weights, depth and other regularization. Source: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html.

Outcome: **keep**; commit `bcee39f`; Eval AUC **0.6862**. Training time: 13.3s Eval time: 8.0s Eval AUC: 0.6862 Run time: 22.4s (training 14.1s, eval 8.2s, ok)

## Experiment 29 — ablation: remove dropout from the new winner

Hypothesis: experiment 28 improved to 0.6862, but changed tree count and learning rate as well as adding dropout. Remove dropout while preserving its 180 rounds, eta 0.1, and one tree per round to test whether dropout itself contributes. A tie is a keep because the code and training are simpler. XGBoost 3.4 emitted a deprecation warning for the dart booster alias; future retained dropout variants should use the default tree booster with dropout parameters.

Outcome: **discard**; commit `d798ad6`; Eval AUC **0.6838**. Training time: 0.7s Eval time: 8.0s Eval AUC: 0.6838 Run time: 9.7s (training 1.5s, eval 8.2s, ok)

## Experiment 30 — exploration: coarser numeric split candidates

Hypothesis: timetable details may still be too granular after removing minute-of-hour. Set max_bin=64, reducing candidate splits for departure time, distance and route-relative time while preserving low-cardinality calendar features. The dropout ablation lost 0.0024, providing controlled evidence that dropout helps under the compact schedule. Source: https://xgboost.readthedocs.io/en/stable/treemethod.html and the max_bin parameter documentation.

Outcome: **keep**; commit `26a8295`; Eval AUC **0.6863**. Training time: 13.2s Eval time: 8.0s Eval AUC: 0.6863 Run time: 22.3s (training 14.1s, eval 8.2s, ok)

## Synthesis after 30 experiments

Best: 0.6863 at 26a8295, +0.0120 over baseline. The original calendar feature family remains useful; removing cyclic month coordinates hurt, while removing minute-of-hour tied and simplified. Direct frozen lookups halved evaluation time. Route-relative departure and a mild twelve-month recency weighting each added 0.0002, but stronger recency weighting hurt. DART improved to 0.6862, and a controlled dropout ablation fell to 0.6838, so the dropout component itself contributes. Coarse numeric bins added 0.0001. Current theory: broad temporal structure plus restrained route context and regularization transfer better than fine categories or heavy recency bias. Next test asymmetric tree growth and objective regularization. Research at this pause covered lossguide/max_leaves and custom objectives in XGBoost documentation.

## Experiment 31 — exploration: leaf-budget growth

Hypothesis: a fixed twelve-leaf budget with loss-guided growth can focus model capacity on useful time/holiday splits while avoiding the full balanced depth-four shape. Set max_depth=0, grow_policy=lossguide and max_leaves=12, retaining the successful dropout schedule and 64-bin representation. Source: https://xgboost.readthedocs.io/en/stable/parameter.html (grow_policy and max_leaves).

Bookkeeping correction: an early status read occurred while evaluation was still running. The premature crash entry was removed; this is not a model crash. Wait for the completed harness summary before recording the result. The result-recording helper now refuses unfinished logs.

Outcome: **discard**; commit `9e1574c`; Eval AUC **0.6857**. Training time: 17.9s Eval time: 8.3s Eval AUC: 0.6857 Run time: 27.3s (training 18.8s, eval 8.5s, ok)

Timing annotation for experiment 31: the harness row starting at Unix time 1791339421.2 carries commit 26a8295 because HEAD was briefly reset during evaluation. That row actually describes commit 9e1574c (18.8s training, 8.5s evaluation, status ok). Its saved artifact and results.tsv entry correctly identify 9e1574c and AUC 0.6857. The protected timing file was left untouched.

## Experiment 32 — exploration: mild label smoothing in the loss

Hypothesis: mild smoothing can regularize confident fits to delays that are unpredictable from advance schedule information. Use a custom binary logistic objective with targets 0.05 and 0.95 (10% mixing toward 0.5), preserving original binary labels in prepare and all harness scoring. Apply the existing recency weights to both gradients and Hessians. Local XGBoost source confirmed the callback sample_weight interface and native binary-logistic prediction link. Research: https://arxiv.org/abs/1906.02629 and https://arxiv.org/abs/2003.02819 (adapted from other model settings), plus https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html.

Outcome: **discard**; commit `93e625a`; Eval AUC **0.6853**. Training time: 13.3s Eval time: 8.0s Eval AUC: 0.6853 Run time: 22.4s (training 14.2s, eval 8.2s, ok)

## Experiment 33 — follow-up: slightly deeper dropout trees

Hypothesis: controlled ablation confirmed dropout reduces overfitting, so it may allow depth-five interactions that were too noisy under ordinary boosting. Change max_depth from four to five with the same 180-round dropout schedule and leaf regularization. This revisits capacity under a materially different successful regularization regime. The discarded smoothed objective passed weighted gradient/Hessian finite-difference checks; its AUC loss was not an implementation failure.

Outcome: **discard**; commit `1e4ebaf`; Eval AUC **0.6853**. Training time: 17.1s Eval time: 8.1s Eval AUC: 0.6853 Run time: 26.3s (training 18.0s, eval 8.3s, ok)

## Plateau research and experiment 34 — exploration: two-seed averaging

Three recent variants failed to improve the 0.6863 best. Reviewed ensemble averaging before another change: https://scikit-learn.org/1.9/modules/ensemble.html. Hypothesis: independent row/column/dropout randomization still leaves variance that probability averaging can reduce. Train two otherwise identical models on the full permitted training set, using prespecified seeds 42 and 137, and average their probabilities. No individual-seed evaluation, seed selection, cross-validation, or extra metric is performed. The pair should fit within the 60-second training cap based on the 13.2-second single-model timing.

Outcome: **keep**; commit `b447255`; Eval AUC **0.6868**. Training time: 26.5s Eval time: 8.5s Eval AUC: 0.6868 Run time: 36.1s (training 27.4s, eval 8.7s, ok)

## Experiment 35 — follow-up: three-member averaging

Hypothesis: the two-model average gained 0.0005, so a third independent model may further reduce variance. Add prespecified seed 2026 to seeds 42 and 137 with equal probability weights. Do not score members separately. Expected training time is about 40 seconds, leaving margin below the 60-second cap.

Outcome: **discard**; commit `5f04d97`; Eval AUC **0.6866**. Training time: 41.0s Eval time: 8.0s Eval AUC: 0.6866 Run time: 50.2s (training 41.9s, eval 8.3s, ok)

## Experiment 36 — exploration: stronger leaf-value shrinkage

Hypothesis: averaging reduces random variance, but leaf estimates for sparse airport/route combinations may still be too large. Increase reg_lambda from 10 to 100 while retaining two-model averaging, the current split structure and dropout. This tests L2 shrinkage of leaf values rather than hard restrictions on tree structure. Source: XGBoost parameter documentation. The three-member ensemble ran within budget but lost 0.0002, so the fixed two-member version remains best.

Outcome: **keep**; commit `1518ab9`; Eval AUC **0.6885**. Training time: 27.6s Eval time: 8.4s Eval AUC: 0.6885 Run time: 37.0s (training 28.5s, eval 8.6s, ok)

## Experiment 37 — follow-up: test the L2 bias-variance boundary

Hypothesis: increasing lambda from 10 to 100 produced a meaningful +0.0017 gain, so sparse-leaf estimates were still too large. Increase lambda to 300 to test whether further shrinkage helps before underfitting dominates. This changes leaf estimates substantially for low-Hessian leaves while leaving split eligibility and the dropout/ensemble design unchanged.

Outcome: **keep**; commit `7bd7c40`; Eval AUC **0.6888**. Training time: 28.2s Eval time: 8.1s Eval AUC: 0.6888 Run time: 37.4s (training 29.1s, eval 8.3s, ok)

## Experiment 38 — ablation: is dropout still needed after strong L2?

Hypothesis: thirty-fold stronger leaf regularization than in the earlier dropout ablation may now provide sufficient smoothing without dropout. Remove dropout parameters and the legacy booster alias, preserving two-member averaging, lambda 300 and the same schedule. A tie is a keep because it removes code and should greatly reduce training time. This is a justified repeat under a materially changed regularization regime, not a duplicate of experiment 29.

Outcome: **discard**; commit `70ca449`; Eval AUC **0.6871**. Training time: 1.5s Eval time: 8.1s Eval AUC: 0.6871 Run time: 10.6s (training 2.3s, eval 8.3s, ok)

## Experiment 39 — follow-up: carrier-origin schedule context

Hypothesis: the route-median feature helped, but airline departure banks at a given origin may provide complementary schedule context across destinations. Fit training-only median scheduled minutes by carrier and origin, and add the row’s departure offset from that median. This is label-free, does not use counts, and uses fixed missing fallback for unseen combinations. Reference: the previously reviewed pandas GroupBy guide and safe lookup pattern in program.md. Dropout still helped under lambda 300 (ablation lost 0.0017).

Outcome: **keep**; commit `fd9ab43`; Eval AUC **0.6894**. Training time: 29.0s Eval time: 8.4s Eval AUC: 0.6894 Run time: 38.6s (training 30.0s, eval 8.7s, ok)

## Experiment 40 — ablation: remove raw distance

Hypothesis: airport identities plus route/carrier schedule context may now capture the useful operational signal that distance provided, while raw distance adds weak noisy splits. Remove only the Distance predictor; retain the training-only schedule lookup construction. A tie is acceptable as a simplification. Experiment 39 improved AUC by 0.0006 and passed row-invariance/unseen-pair checks.

Outcome: **discard**; commit `ff35ac4`; Eval AUC **0.6878**. Training time: 27.4s Eval time: 8.7s Eval AUC: 0.6878 Run time: 37.3s (training 28.4s, eval 8.9s, ok)

## Synthesis after 40 experiments

Best: 0.6894 at fd9ab43, +0.0151 over baseline. Two independent dropout models outperformed one; a third member did not help. Increasing lambda from 10 to 100 and then 300 raised AUC from 0.6868 to 0.6888. Carrier-origin schedule context added another 0.0006. Dropout remains useful even with strong L2, and raw distance still contributes despite its low importance. Extra depth, loss-guided growth and label smoothing hurt. Current theory: the useful signal is broad timing/calendar plus stable operational context; regularized leaf values and averaging suppress unstable airport partitions. New research at this pause examined feature-weighted column sampling and CPU gradient-based row sampling (supported since XGBoost 3.2). Sources: https://xgboost.readthedocs.io/en/stable/parameter.html and https://xgboost.readthedocs.io/en/release_3.2.0/changes/v3.2.0.html.

## Experiment 41 — exploration: weighted feature sampling

Hypothesis: uniform column sampling sometimes omits the strongest timing/calendar signals; giving CRSDepTime, DepartureHour and HolidayDistance twice the sampling weight may preserve their signal without removing ensemble diversity. Set constructor feature_weights accordingly. Confirmed this parameter is supported by the installed XGBoost constructor. No additional scoring or feature selection procedure is used.

Outcome: **discard**; commit `fe0c821`; Eval AUC **0.6886**. Training time: 28.2s Eval time: 8.6s Eval AUC: 0.6886 Run time: 38.0s (training 29.1s, eval 8.8s, ok)

## Experiment 42 — exploration: gradient-based row sampling

Hypothesis: sampling in proportion to regularized gradient magnitude can allocate training effort more effectively than uniform sampling. Use CPU hist gradient_based sampling with subsample=0.5, retaining the ensemble, dropout and strong L2. Confirmed CPU support in the XGBoost 3.2 release notes; installed version is 3.4.1. Sources: https://xgboost.readthedocs.io/en/release_3.2.0/changes/v3.2.0.html and the sampling_method parameter documentation.

Outcome: **discard**; commit `ce40354`; Eval AUC **0.6892**. Training time: 29.4s Eval time: 8.7s Eval AUC: 0.6892 Run time: 39.3s (training 30.4s, eval 8.9s, ok)

## Experiment 43 — follow-up: stronger L2 shrinkage boundary

Hypothesis: lambda 100 and 300 both improved ranking; increasing it to 1000 tests whether further leaf shrinkage helps or starts to underfit. Inspection of the current saved model found leaf Hessian-mass percentiles 52.8, 718.3 and 6050.8 (10th, 50th, 90th), so this materially changes typical leaf estimates. No additional scoring was used. Fresh research: the XGBoost paper and sklearn regularization discussion explain leaf weights as negative gradient sum divided by Hessian sum plus lambda. Sources: https://arxiv.org/abs/1603.02754 and https://scikit-learn.org/1.9/modules/ensemble.html.

Outcome: **discard**; commit `8aa36ab`; Eval AUC **0.6885**. Training time: 28.8s Eval time: 8.4s Eval AUC: 0.6885 Run time: 38.4s (training 29.8s, eval 8.6s, ok)

## Experiment 44 — simplification: remove redundant legacy booster settings

Hypothesis: the installed XGBoost version activates tree dropout through rate_drop and skip_drop, so the deprecated booster="dart" alias is redundant. Remove it and num_parallel_tree=1, whose default is already one. Preserve all dropout parameters and ensemble behavior; keep an equal AUC as a code simplification. Fresh source reviewed after the plateau: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html explicitly identifies the dart name as a compatibility alias and demonstrates dropout with the default booster. This differs from experiments 29 and 38, which removed dropout itself.

Outcome: **keep**; commit `cb6c121`; Eval AUC **0.6894**. Training time: 29.1s Eval time: 8.6s Eval AUC: 0.6894 Run time: 38.9s (training 30.0s, eval 8.8s, ok)

Cleanup verification: saved artifacts cb6c121 and fd9ab43 produced identical features and probabilities on the first 1000 training rows. No additional metric was computed.

## Experiment 45 — ablation: remove recency weights after regularization gains

Hypothesis: recency weighting added only 0.0002 before dropout, averaging and much stronger L2; it may now be redundant or reduce effective training information. Remove its two-line construction and sample_weight argument, leaving all predictors and model parameters fixed. This is a justified ablation under the changed regularization regime, not a repeat of the six-month-half-life experiment. Keep an equal score as a simplification. Reference: the previously reviewed temporal weighting paper https://arxiv.org/abs/1602.04435; weighting is useful when recent data better represents the target period, but that assumption should still earn its complexity.

Outcome: **discard**; commit `45e076c`; Eval AUC **0.6887**. Training time: 28.0s Eval time: 8.3s Eval AUC: 0.6887 Run time: 37.6s (training 29.0s, eval 8.6s, ok)

## Experiment 46 — follow-up: categorical partition flexibility under stronger L2

Hypothesis: max_cat_threshold=16 helped when lambda was 10, but with lambda 300, dropout and averaging, it may now restrict useful broad airport groupings. Raise the threshold to 64 while retaining the newer regularizers. This differs materially from the early comparison by testing categorical split complexity under thirty-fold stronger leaf shrinkage. Newly reread sources explain that categories are sorted by leaf-value estimates and max_cat_threshold limits categories considered to prevent overfitting: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html and https://xgboost.readthedocs.io/en/stable/parameter.html.

Outcome: **discard**; commit `a045e46`; Eval AUC **0.6860**. Training time: 29.6s Eval time: 8.8s Eval AUC: 0.6860 Run time: 39.6s (training 30.5s, eval 9.0s, ok)

## Experiment 47 — follow-up: carrier-destination schedule context

Hypothesis: route and carrier-origin departure medians both helped, so a carrier-destination schedule reference may add complementary information across origins. Add departure minutes minus the training-only median for carrier and destination. This describes scheduled departure patterns, not physical arrival time. As with the retained lookups, fit without labels or counts and map unseen combinations to NaN. Source: https://pandas.pydata.org/docs/user_guide/groupby.html and the empirical gain in experiment 39.

Outcome: **discard**; commit `2cb60f1`; Eval AUC **0.6893**. Training time: 28.4s Eval time: 9.0s Eval AUC: 0.6893 Run time: 38.6s (training 29.4s, eval 9.2s, ok)

Feature validation for experiment 47 passed batch-versus-single-row equality and unseen-destination fallback checks. Its AUC of 0.6893 was lower, so the feature was discarded despite the small difference.

## Experiment 48 — follow-up: require more support for each leaf

Hypothesis: the best model still has low-Hessian leaves (10th percentile 52.8), whose split selection may remain unstable even when lambda shrinks their output. Raise min_child_weight from 20 to 100 to prevent sparsely supported splits, preserving lambda 300 and categorical threshold 16. This tests eligibility for a split, unlike experiment 43 which only increased leaf shrinkage. Source newly reread: https://xgboost.readthedocs.io/en/stable/parameter.html defines min_child_weight as the minimum summed Hessian in each child.

Outcome: **discard**; commit `767e2b6`; Eval AUC **0.6889**. Training time: 29.2s Eval time: 8.4s Eval AUC: 0.6889 Run time: 38.8s (training 30.1s, eval 8.7s, ok)

## Final summary

Completed 48 experiments plus the unchanged baseline on branch `oct7`. Best Eval AUC: **0.6894**, at kept commit `cb6c121` (full hash `cb6c1217faf6559b6981c5a7fa7bcb0f3b627a1b`). Baseline: **0.6743**; absolute improvement: **0.0151**. The same best score was first reached at `fd9ab43`; experiment 44 simplified redundant booster settings without changing predictions or AUC. Saved artifact: `artifacts/cb6c1217faf6559b6981c5a7fa7bcb0f3b627a1b.pkl`. Final elapsed time before stopping is approximately 0h59m24s.

The retained model averages two fixed-seed, 180-tree dropout models with depth 4, learning rate 0.1, lambda 300, minimum child Hessian 20, 64 numeric bins and categorical split threshold 16. It uses 13 predictors: raw scheduled departure and distance; weekday, carrier, origin and destination categories; numeric and cyclic month coordinates; departure hour; four-holiday proximity; and departure offsets from training-only route and carrier-origin medians. Training uses normalized twelve-month recency weights. Best-commit run time was 38.9 seconds (30.0 seconds training/startup, 8.8 seconds evaluation), within both limits.

What worked: dropping raw day-of-month, shallower regularized trees, constrained categorical partitions, seasonal and holiday features, label-free schedule context, dropout, two-model averaging and stronger leaf shrinkage. Frozen category/calendar lookups reduced evaluation time from about 31 seconds to about 9 seconds. Ablations confirmed continued value from dropout, distance and recency weighting.

What did not work: richer carrier-airport category interactions, one-hot expansion, airport geometry, strict interaction or monotonic constraints, pairwise ranking, label smoothing, extra depth, loss-guided growth, a third ensemble member, stronger recency decay, broader categorical partitions, still stronger L2, weighted feature sampling, stronger minimum leaf support and the extra carrier-destination schedule median. The latter reached 0.6893 and was discarded under the strict keep rule.

Next directions: test label-free schedule spread (such as training-only within-route interquartile ranges), a compact smooth day-of-year representation, and whether stronger dropout paired with a longer schedule improves stability within the training cap. Prioritize distinct hypotheses and ablations over small parameter sweeps.

Final verification: all 49 runs completed successfully, with no model crashes or timeouts. Every result has a saved artifact; HEAD matches the best kept row; only train.py differs from the starting commit; the harness is unchanged; results and this log remain uncommitted. The final saved prepare function passed batch-versus-single-row equality, unseen-category/lookup fallback, and finite probability checks using training rows only. No holdout or archived results were inspected, and no additional performance metric was computed.

Bookkeeping caveat: experiment 31's protected timing row is labeled 26a8295 instead of 9e1574c because HEAD was reset before evaluation finished. Its artifact and results.tsv correctly identify 9e1574c and AUC 0.6857. The discrepancy is annotated above; the timing file was not changed. The recording helper was then guarded against unfinished runs, and all subsequent outcomes were recorded after process completion.
