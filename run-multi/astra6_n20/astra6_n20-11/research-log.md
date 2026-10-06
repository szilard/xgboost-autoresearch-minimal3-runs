# Research log: oct6

- Setup date: 2026-10-06 (UTC)
- Branch: `oct6`, created directly from current HEAD `b15ec66`.
- Objective: improve harness-reported Eval AUC for flight departure delay prediction.
- Experiment budget: one hour, starting only after user confirmation.
- Both required data files exist; all required Python packages import successfully.
- Baseline: pending; the first run will use the unchanged `train.py`.

## Setup

Read `program.md`, `train.py`, and `harness.py`. Initialized `results.tsv` with
its header only. The experiment clock has not started and no training has run.

## Baseline — b15ec66

Eval AUC **0.6743**, training 1.5s including startup, evaluation 31.0s.
Unchanged starter: 100 trees, depth 6, learning rate 0.1; native categories.
Train-only inspection: 200,000 complete rows, 20 carriers, 283 airports per
endpoint; month/day fields use c-N strings, scheduled times use HHMM.

## Initial research

- https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html:
  balance capacity and regularization; smaller learning rates need more rounds.
- https://xgboost.readthedocs.io/en/stable/parameter.html:
  depth, child Hessian mass, L2 regularization, and sampling govern complexity.
- https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html:
  categorical partitioning can capture groups of airports/carriers; mappings
  must stay consistent at inference, with unknown levels handled as missing.
- Flight feature research surfaced the Berkeley project on temporal and network
  features; full page was inaccessible (403), so it is not implementation evidence.

Initial search region: 300–1000 trees, rates 0.03–0.1, depths 4–8,
min_child_weight 5–100, L2 1–30. Tune deliberately from measured outcomes.

## Experiment 1 — exploration: longer regularized boosting

Hypothesis: the 100-tree starter underfits stable carrier/time effects. Use 600
trees at rate 0.05, min_child_weight=20, and reg_lambda=10 to add capacity while
limiting noisy small leaves across the 2005-to-2006 shift. All features unchanged.
Source: XGBoost tuning guide and parameter reference above.

Result 9d256c8: **0.6697**, training 4.3s, eval 31.1s. Discard: -0.0046.
Extra boosting worsens next-year performance despite regularization; capacity
or calendar/category overfitting is a concern.

## Experiment 2 — ablation/simplification: faster preparation

Hypothesis: constructing the frame once with precomputed categorical dtypes
removes redundant copying and membership checks without changing any values.
Unknown categories already map to missing in pandas.Categorical. Train-only
single-row/batch equivalence passed on a scratch prototype. Keep only if AUC
matches baseline and the harness reports faster evaluation.

Result 9b015b0: **0.6743**, training 1.7s, eval 8.1s. Keep: same printed AUC,
~74% faster evaluation. pandas warns about unknown categories in a future version;
current inference correctly maps them to missing. Can simplify using explicit codes later.

## Experiment 3 — ablation: remove day-of-month

Hypothesis: interactions involving day-of-month memorize individual 2005 weather
or traffic events. Day-specific train label rates vary from ~0.458 to ~0.560,
which may not transfer to 2006. Remove this feature while retaining month and
weekday; all model parameters unchanged. Motivated by experiment 1 overfitting.
Time-feature source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html
(tree models can learn nonlinear temporal effects without sinusoidal encoding).

Result a456db6: **0.6759**, training 1.4s, eval 7.0s. Keep: +0.0016;
removing a date-specific feature helps and simplifies the model.
Baseline feature gain is dominated by scheduled departure time (~427), with
month (~57), carrier (~55), weekday (~48), origin (~45), destination (~43),
day-of-month (~28), distance (~12). Gain is descriptive, not a validation metric.

## Experiment 4 — follow-up: shallower regularized boosting

Hypothesis: fewer high-order interactions transfer better across years. Use
300 trees at depth 4/rate .05, child weight 20 and L2 10. More shallow rounds
can recover smooth time/airport effects while removing fragile depth-6 leaves.
This differs from experiment 1 by depth and exclusion of day-of-month.
Source: initial XGBoost tuning documentation.

Result 7212109: **0.6800**, training 1.9s, eval 7.1s. Keep: +0.0041.
This supports reducing interaction complexity rather than adding deep trees.

## Experiment 5 — exploration: single-category splits

Hypothesis: arbitrary airport/category partitions can group noisy 2005 effects.
Set max_cat_to_onehot=512 so every current categorical column uses one-vs-rest
splits. All other parameters and features stay at experiment 4's settings.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html

Result f466729: **0.6754**, training 1.6s, eval 7.0s. Discard: -0.0046.
Grouping categories is valuable at the current shallow-tree budget.

## Experiment 6 — ablation: remove month

Hypothesis: the strong seasonal rates in 2005 may partly reflect year-specific
weather. Removing Month tests whether this input helps generalization beyond
stable weekday, departure time, carrier and airport effects. Based on the
successful day-of-month ablation; no other changes.

Result 550de12: **0.6830**, training 1.7s, eval 6.3s. Keep: +0.0030.
Both date-related ablations help; current model uses weekday plus operational
features, without month/day-of-month.

## Experiment 7 — exploration: explicit route category

Hypothesis: an Origin–Dest category gives shallow trees useful route interactions
without having to spend two levels selecting airports. Keep native partitioning
and the conservative depth-4 model. The categorical source is the XGBoost native
categorical tutorial cited above. Category dictionaries are fitted only on train.
Switch category construction to explicit train-fitted codes (unknown=-1); this is
semantically equivalent and avoids pandas' future unknown-category warning.
Verify row/batch equality and unknown-level behavior before the harness run.

Result 2521738: **0.6756**, training 2.5s, eval 4.7s. Discard: -0.0074.
The unrestricted route category hurts substantially; sparse route effects are
not yet useful. Explicit category codes were faster but bundled with this loss.

## Experiment 8 — follow-up: more rounds after calendar ablation

Hypothesis: longer boosting may now help because both unstable calendar fields
are gone. Increase 300 to 800 depth-4 trees; keep rate .05, child weight20, L2 10.
This isolates iteration count, unlike experiment 1 with date features/depth6.

Result bdc0cba: **0.6787**, training 3.2s, eval 6.4s. Discard: -0.0043.
Longer boosting still hurts after date removal; high-cardinality airport or
schedule effects may also shift between years.

## Experiment 9 — follow-up: stronger minimum leaf evidence

Hypothesis: increasing min_child_weight from 20 to 100 (other settings unchanged)
prevents weakly supported airport/time splits and improves next-year transfer.
Uses the documented Hessian-mass regularizer rather than adding features or rounds.

Result 46f0a57: **0.6828**, training 1.7s, eval 6.2s. Discard: -0.0002,
per strict printed-AUC keep rule. Greater leaf support alone did not help.

## Experiment 10 — ablation: depth-three trees

Hypothesis: further reducing high-order interactions improves transfer, following
experiment 4's gain with shallower trees. Change only max_depth 4 to 3; retain
300 rounds at .05 and the last kept child weight20/L2 10 settings.

Result 7150569: **0.6838**, training 1.5s, eval 6.2s. Keep: +0.0008.

## Synthesis after 10 experiments

Best: 7150569, **0.6838** versus baseline 0.6743 (+0.0095).
Helpful: efficient preparation, removing day-of-month and month, shallower
regularized trees. Harmful: more boosting, raw route categories, single-category
splits for all fields. Increasing child weight alone was a near miss.
Current theory: between-year drift makes detailed calendar and operational
interactions fragile; smooth time effects plus pooled airport/carrier effects
transfer better. Next test time coarsening, restricted feature interactions and
randomized ensembles rather than more unstructured depth.

### Research refresh

- https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html:
  constraints can impose shape on numeric effects. Train hourly label means
  rise from ~0.20 at 06:00 to ~0.65 at 20:00, then fall; a global increasing
  constraint on raw HHMM would be inappropriate without a time transformation.
- https://xgboost.readthedocs.io/en/stable/tutorials/rf.html:
  num_parallel_tree combined with subsampling supports boosted forests.
- https://github.com/dmlc/xgboost/blob/master/doc/tutorials/feature_interaction_constraint.rst:
  interaction groups provide a way to restrict specific feature combinations.

## Experiment 11 — exploration: coarser scheduled departure time

Hypothesis: half-hour departure bins preserve the dominant daily delay curve
while reducing sensitivity to small timetable differences across years. Replace
raw HHMM with floor(minutes_since_midnight/30); other features/settings unchanged.
Time engineering source: scikit-learn cyclical-feature example cited earlier.

Result 15312a1: **0.6838**, training 1.5s, eval 6.3s. Discard: equal AUC,
more preparation code and no speed improvement. Fine time resolution is not
currently hurting enough to justify this transformation.

## Experiment 12 — exploration: boosted randomized forests

Hypothesis: averaging four randomized trees per boosting step reduces variance
in category partitions without increasing the number of sequential gradient
updates. Keep 300 rounds/depth3/rate.05; add num_parallel_tree=4, subsample=.8,
colsample_bynode=.8. Unlike experiment 8, boosting duration remains fixed.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html

Result e3e224e: **0.6838**, training 5.6s, eval 6.4s. Discard: equal AUC
with a larger/slower model. Randomized forest averaging did not beat the simple fit.

## Experiment 13 — exploration: additive operational effects

Hypothesis: airport/carrier main effects are more transferable than their detailed
interactions. Permit time-distance interactions, but put weekday, carrier, origin
and destination into individual non-overlapping interaction groups. Keep 300
rounds/depth3/rate.05 and all features. This directly tests the low-interaction
explanation suggested by experiments 4 and 10.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html

Result 7049e52: **0.6755**, training 1.6s, eval 6.5s. Discard: -0.0083.
Pure main effects lose useful interactions; shallow joint trees remain preferable.

## Experiment 14 — exploration: train-only airport geometry

Hypothesis: numeric airport positions allow shallow trees to pool nearby airports
and learn broad geographic effects more robustly than airport IDs alone. Build
an undirected graph using only train route distances (minimum observed distance
per airport pair, no frequency/count features), infer missing distances by shortest
paths, and use two-dimensional classical MDS. Fit the airport lookup at module
level; prepare only looks up origin and destination coordinates. Unknown airports
map to NaN. Keep all existing features and the last kept model settings.
Sources:
- https://scikit-learn.org/stable/modules/generated/sklearn.manifold.Isomap.html
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.shortest_path.html
The geographic interpretation is an experimental hypothesis, not a source claim
about this particular dataset. No external airport data is used.

Result 0835e2b: **0.6838**, training 1.8s, eval 7.1s. Discard: equal AUC
with more code and slower preparation. Distance-derived geography did not help.

## Experiment 15 — simplification/speed: explicit category codes

Hypothesis: train-fitted dictionary codes and Categorical.from_codes avoid costly
per-row category inference and handle unknown values explicitly. Isolate this
semantics-preserving part of experiment 7, with no route feature. Keep only if
printed AUC matches or improves and preparation is faster. Verify identical
categorical columns on training rows plus unknown and row/batch behavior.

Result 4f14bdb: **0.6838**, training 1.5s, eval 4.4s. Keep: same AUC,
~29% faster evaluation than 7150569, with explicit missing-category handling.

## Experiment 16 — follow-up: limit categorical split search

Hypothesis: max_cat_threshold=16 (instead of default64) reduces noisy broad
category partitions while preserving more pooling than experiment 5's one-vs-rest
splits. All other features/settings unchanged. Source: XGBoost categorical
parameter reference, which identifies this parameter as an overfitting control.

Result 75256cb: **0.6827**, training 1.5s, eval 4.4s. Discard: -0.0011.
Broader categorical groupings remain useful.

## Experiment 17 — exploration: shaped departure-time effect

Hypothesis: a monotonic daytime component captures delay propagation without
fitting small reversals in the training timetable. Replace raw HHMM with
DayProgress=clip(minutes,360,1200), unconstrained LateTime=max(minutes-1200,0),
and a before-05:00 RedEye indicator. Constrain only DayProgress to increasing.
LateTime and RedEye permit the observed nighttime departures from that trend.
Retain distance, weekday, carrier, airports and the same depth3 model.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html
The proposed shape is based on train-only hourly summaries, not evaluation data.

Result 5b6625e: **0.6838**, training 1.6s, eval 5.6s. Discard: equal AUC,
more features and slower preparation. A hard daytime shape did not add value.

## Experiment 18 — exploration: remove seasonal label imbalance in training

Hypothesis: even without Month as a feature, differing monthly positive rates can
confound airport/carrier patterns through their seasonal traffic mix. Fit monthly
positive-rate lookups on train; set sample_weight=.5/p_month for positives and
.5/(1-p_month) for negatives. This balances class weight within each month while
preserving its total weight. Inference features and prepare are unchanged.
No counts, rates or labels are added as prediction features.
Sources:
- https://arxiv.org/abs/1911.08731 (motivation about robustness to group shifts)
- https://xgboost.readthedocs.io/en/stable/python/python_api.html (sample_weight API)
This fixed balancing scheme is our adaptation, not an implementation of group DRO.

Result 1a581d4: **0.6841**, training 1.6s, eval 4.4s. Keep: +0.0003.
Fixed monthly class balancing adds a small measured gain without changing inference.

## Experiment 19 — follow-up: daily balancing with weekday prior

Hypothesis: unusual 2005 days also bias stable operational effects. Fit the delayed
rate per Month/DayofMonth and use the overall train weekday rate as that day's
target prior. Positive weight=p_weekday/p_day, negative=(1-p_weekday)/(1-p_day).
This keeps each day's total weight and preserves weekday differences, while
reducing date-specific label-rate variation. These are fit-time weights only;
prepare still has no calendar date or label-derived prediction features.
This differs from experiment 18 by daily rather than monthly balancing and
preservation of the weekday class prior.

Result 7739099: **0.6838**, training 1.7s, eval 4.4s. Discard: -0.0003.
Daily balancing is too aggressive or unnecessary; retain coarse monthly weighting.

## Experiment 20 — follow-up: recency-weighted training

Hypothesis: later-2005 carrier/airport relationships better match 2006. Multiply
experiment 18's monthly-balanced weights by exp2((month-12)/6), a six-month
half-life, then normalize to mean one so regularization scale stays comparable.
No date feature is supplied at inference. This tests operational recency while
controlling for the seasonal label imbalance that previously helped.
Source: XGBoost sample_weight API; the temporal weighting is our domain hypothesis.

Result b5eb08c: **0.6843**, training 1.6s, eval 4.4s. Keep: +0.0002.

## Synthesis after 20 experiments

Best: b5eb08c, **0.6843** (+0.0100 from baseline). The compact depth3 model
remains strongest. Fine time binning, randomized boosted forests, airport distance
geometry and a monotonic time representation tied but did not justify extra code.
Fully additive effects hurt substantially, so retain selected interactions.
Explicit category coding reduced evaluation cost further. Monthly label balancing
and six-month recency weights provided small gains; daily balancing did not.
Current theory: coarse domain adaptation and regularized operational interactions
matter more than adding flexible features. Next: test stronger recency, lower
boosting capacity, and an objective aimed at positive/negative ordering.

### Research refresh

- https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html:
  rank:pairwise is pairwise logistic loss; mean pair sampling can cover the full
  ranking rather than only its highest positions.
- https://arxiv.org/abs/1208.0645:
  studies the relationship between pairwise surrogate losses and AUC consistency.
Potential adaptation: a single query group of all training flights with binary
labels. A saved wrapper can expose predict_proba through a monotonic sigmoid.
The only experiment score will remain the unchanged harness's Eval AUC.

## Experiment 21 — follow-up: three-month recency half-life

Hypothesis: experiment 20's gain indicates changing operational patterns; a
three-month rather than six-month half-life should better track late-2005 changes,
at the cost of reducing effective training diversity. Change only the half-life
and retain monthly balancing and normalized mean weight.

Result 8dad4aa: **0.6822**, training 1.6s, eval 4.4s. Discard: -0.0021.
Moderate recency helps slightly but strongly concentrating the sample hurts.

## Experiment 22 — exploration: pairwise ranking objective

Hypothesis: optimizing positive/negative ordering directly may improve AUC over
pointwise classification. Use XGBRanker rank:pairwise with all training rows in
one query group, mean pair sampling and four pairs/sample. Keep depth3, 300
rounds, rate.05, child20 and L2 10. Because ranker's weights apply to groups,
this trial replaces the pointwise monthly/recency weights with unweighted pairs.
A saved adapter maps raw rank scores through sigmoid and returns two-column
predict_proba; this preserves score ordering and uses the unchanged harness.
Sources: XGBoost learning-to-rank tutorial and AUC consistency paper in synthesis20.

Result a8728ec: **0.6826**, training 23.3s, eval 4.4s. Discard: -0.0017.
Pairwise learning is viable but global unweighted pairs underperform the adapted
classifier and cost much more training time.

## Experiment 23 — follow-up: monthly pair groups with recency weights

Hypothesis: ranking within each training month reduces sensitivity to monthly
class-prior shifts; recency can be supported through the ranker's group weights.
Replace the single global query with 12 month groups, ordered by month, and use
six-month half-life query weights. Keep the four-pair sampling, 300 rounds and
other ranking parameters from experiment22. This specifically restores a temporal
adaptation mechanism absent in experiment22; it is not a random seed retry.
No query identifier is a feature, and no monthly information is needed at inference.
Source: the XGBoost ranking and sample-weight documentation already researched.

Result 5786efe: **0.6829**, training 4.4s, eval 4.4s. Discard: -0.0014.
Monthly ranking is faster and a little better than global ranking but still trails
pointwise classification; return to the stronger, simpler objective.

## Experiment 24 — exploration: monthly nuisance offsets

Hypothesis: fitting residual log-odds after accounting for each month's training
label prior isolates operational effects more cleanly than class reweighting.
Use base_margin=logit(p_month) in training, retain six-month recency weights,
and set base_score=.5. At inference the model uses the neutral zero-logit baseline;
no month, prior lookup, or labels enter inference. Monthly class balancing is
replaced by the offset, not applied twice. All features/tree settings unchanged.
Source: https://xgboost.readthedocs.io/en/stable/tutorials/intercept.html
This deliberately removes a training nuisance offset at prediction; it is a
transfer hypothesis, not a claim that the resulting probabilities are calibrated.

Result f850104: **0.6841**, training 1.6s, eval 4.4s. Discard: -0.0002.
Offsets are competitive but do not improve on simple monthly class weighting.

## Experiment 25 — ablation: fewer boosting rounds

Hypothesis: the best depth3 model may still fit some weak late-round detail.
Reduce 300 to 200 rounds, retaining rate .05, monthly balancing and six-month
recency weights. This is a capacity ablation of the now-adapted model, not a repeat
of experiment8's 800 depth4 trees without temporal sample weighting.

Result 80110a1: **0.6839**, training 1.4s, eval 4.3s. Discard: -0.0004.
Three hundred rounds remain better than a shorter adapted fit.

## Experiment 26 — exploration: blend interaction depths

Hypothesis: shallow and moderately deeper trees make complementary ranking errors.
Average depth2/500-round, depth3/300-round, and depth4/200-round classifiers with
weights 1:2:1. The strongest existing depth3 model receives half the weight; the
other two provide different interaction complexity at roughly comparable capacity.
All use the same training rows, monthly balancing, recency weights and rate.05.
No validation predictions or extra evaluation metric are computed.
Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html
(soft voting averages class probabilities; use a small saved adapter here).

Result 99fae21: **0.6850**, training 3.2s, eval 4.5s. Keep: +0.0007.
Averaging different interaction depths helps, unlike averaging similarly shaped
randomized trees within each boosting round (experiment12).

## Experiment 27 — ablation/simplification: remove deepest ensemble member

Hypothesis: depth2 and depth3 may supply the useful complementary predictions,
with the depth4 member adding unnecessary variance. Drop depth4/200 and average
depth2/500 with depth3/300 in a 1:2 ratio. This directly tests whether all members
of the promising ensemble are necessary and could reduce fitting cost.

Result 54babad: **0.6847**, training 2.5s, eval 4.5s. Discard: -0.0003.
All three depths contribute to the best measured ensemble.

## Experiment 28 — exploration: relative schedule position

Hypothesis: departing earlier/later than a route's or carrier-origin's usual
schedule captures operational context more compactly than the raw route category
that failed in experiment7. Fit median departure minutes per route and per
carrier-origin on train only, then add row departure minus the two fitted medians.
Unknown pairs map to NaN. No counts or target statistics are prediction features.
Uses the explicit allowed lookup/relative-time pattern in program.md, informed by
the earlier research on scheduled-time effects. Keep the three-depth ensemble
and all training weights unchanged. Verify row/batch consistency and unknown pairs.

Result 01fce2e: **0.6851**, training 3.6s, eval 5.8s. Keep: +0.0001.
Compressed, unsupervised schedule context helps marginally despite raw route
categories failing. This is a small rounded gain and should not be overinterpreted.

## Experiment 29 — exploration: compact holiday travel flags

Hypothesis: pooled holiday/pre-holiday/post-holiday indicators transfer more
reliably than raw month/day categories. Add indicators for Thanksgiving, Christmas,
New Year's Day and July4, pooling the three days before and after each holiday.
Thanksgiving's date is computed from the row's month/day/weekday alone; no year,
evaluation identity, lookup fitted on evaluation, or external dataset is used.
Sources:
- https://www.opm.gov/frequently-asked-questions/pay-and-leave-faq/pay-administration/what-are-federal-holidays/?os=v
- https://www.transportation.gov/briefing-room/fact-sheet-usdot-faa-work-improve-holiday-air-travel-and-strengthen-passenger-rights
The DOT source motivates holiday traffic context, not a measured effect in our data.

Result b643577: **0.6865**, training 3.6s, eval 7.1s. Keep: +0.0014.
Compact calendar structure helps even though unrestricted calendar categories hurt.

## Experiment 30 — follow-up: coarse season indicators

Hypothesis: pooling winter (Dec–Feb) and summer (Jun–Aug) months gives the model
broad seasonal context with less freedom to memorize individual 2005 months.
Add two binary flags using the month already parsed for holiday features; all
other features, ensemble members and fit-time weighting unchanged. This is a
coarser hypothesis than restoring the raw Month category rejected in experiment6.
Source: earlier time-feature engineering research; grouping is our domain hypothesis.

Result 1e9a8b2: **0.6872**, training 4.0s, eval 7.5s. Keep: +0.0007.

## Synthesis after 30 experiments

Best: 1e9a8b2, **0.6872**, baseline +0.0129. Stronger recency, pairwise objectives,
monthly offsets and fewer rounds did not beat the classifier. Averaging depths
2/3/4 improved AUC; all three members contributed. Relative schedule medians
added a small gain. Pooled holiday flags and coarse winter/summer indicators
added larger gains while avoiding the poor transfer of raw month/day categories.
Current theory: robust calendar pooling, moderate temporal adaptation, and modest
interaction diversity work together. Keep testing simplifications and regularized
extensions, especially season-sensitive geography and less specialized boosting.

### Research refresh

- https://xgboost.readthedocs.io/en/stable/tutorials/dart.html
- https://arxiv.org/abs/1505.01866
DART drops existing trees during fitting to limit over-specialization; its training
is slower because prediction buffers cannot be reused. Limit the first test to
the central ensemble member to stay comfortably within the one-minute fit limit.

## Experiment 31 — exploration: DART central ensemble member

Hypothesis: dropout makes the depth3 member less dependent on early fitted trees
and more complementary to the depth2/depth4 members. Use booster=dart,
rate_drop=.05, skip_drop=.5 for depth3 only, retaining all round counts, weights,
features and other settings. The other ensemble members stay ordinary boosted trees.

Result 941286b: **0.6870**, training 30.1s, eval 7.4s. Discard: -0.0002,
substantially slower. Installed XGBoost also deprecates booster=dart in favor of
direct tree dropout parameters; this warning did not affect successful execution.
Best ensemble feature gains confirm use of relative carrier-origin schedule,
Summer and PostHoliday; departure time remains dominant. These are descriptive
training gains, not a second evaluation metric.

## Experiment 32 — follow-up: geometry with seasonal context

Hypothesis: airport geometry may help pool geographic seasonal effects now that
Winter/Summer flags are useful. Reintroduce experiment14's train-distance MDS
lookup into the successful seasonal/holiday ensemble. This is deliberately a
new combination: experiment14 had neither season flags nor the depth ensemble,
and tested geography mainly as static airport information. All current features
and weighting stay. Use the same train-only fitting and per-row lookup safeguards.
Sources: the Isomap and SciPy shortest-path references logged in experiment14.

Result 3be8673: **0.6872**, training 4.1s, eval 8.6s. Discard: equal AUC,
more code and slower preparation. Geometry remains unnecessary even with seasons.

## Experiment 33 — follow-up: L1 shrinkage on leaf weights

Hypothesis: the expanded ensemble may benefit from suppressing weak leaf updates
rather than constraining entire features. Add reg_alpha=5 to each member; keep
L2=10 and all other settings fixed. This differs from prior minimum-leaf and depth
experiments by shrinking weak signed gradient sums toward zero.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html (L1 regularization).

Result fdb1056: **0.6890**, training 3.6s, eval 7.3s. Keep: +0.0018.
L1 regularization is valuable in the expanded ensemble; suppressing weak updates
works better than forcing main effects or making all splits one-vs-rest.

## Experiment 34 — ablation/simplification: drop route schedule lookup

Hypothesis: the route-relative departure feature may be redundant with raw time,
distance and carrier-origin schedule. Remove only Route from schedule_pairs,
leaving carrier-origin median and all other features/settings including L1=5.
This tests necessity of the smaller-gain lookup from experiment28 and could
reduce both model inputs and per-row work. Training feature gain supports trying
the ablation but does not substitute for harness Eval AUC.

Result 623c77d: **0.6891**, training 3.6s, eval 7.0s. Keep: +0.0001,
fewer features and less preparation work. Carrier-origin context is sufficient.

## Experiment 35 — follow-up: stronger L1 shrinkage

Hypothesis: the large gain from L1=5 suggests weak-leaf noise remains important.
Increase reg_alpha from5 to20 in all members to bracket the useful shrinkage
range. Everything else stays at the simplified best configuration. This is a
motivated stronger-regularization test, not a cosmetic parameter variation.

Result 6b1b6f4: **0.6885**, training 3.5s, eval 7.0s. Discard: -0.0006.
L1=5 beats both zero and20; stronger shrinkage removes some useful signal.

## Experiment 36 — follow-up: balance months within coarse seasons

Hypothesis: monthly balancing to .5 was useful before season features existed,
but may now remove useful broad seasonal priors. Target each month's class weights
to the train positive rate of its coarse season (winter/summer/other) instead of
.5, while keeping six-month recency and mean-one weight normalization. Thus
within-season month fluctuations are smoothed and between-season priors retained.
This is a motivated adaptation of experiment18 to the feature gains in experiment30.
Features, ensemble and L1=5 remain unchanged.

Result 3542724: **0.6865**, training 3.6s, eval 7.1s. Discard: -0.0026.
The successful seasonal features work best while monthly label priors are balanced;
restoring even coarse source-year seasonal priors is harmful.

## Experiment 37 — ablation: winter indicator

Hypothesis: Summer supplied most of experiment30's gain, whereas Winter had lower
training gain and may retain unstable weather effects. Remove only the Winter
column, keeping Summer and every other feature/weight/model setting. This isolates
the necessity of one member of a previously added feature group.

Result 2eb8943: **0.6893**, training 3.6s, eval 6.7s. Keep: +0.0002,
less preparation. Summer is useful; the extra Winter feature was unnecessary.

## Experiment 38 — follow-up: carrier-origin operating window

Hypothesis: time relative to typical first/last departures captures schedule
context not fully represented by the carrier-origin median. Fit 5th and95th
percentiles of departure minutes per carrier-origin on train. Add minutes after
the lower percentile and minutes until the upper percentile. These are fixed
schedule lookups, not counts or target aggregates; unknown pairs map to NaN.
Keep the successful median, Summer/holiday flags, weights and ensemble unchanged.
Motivation: experiment28's schedule result and program.md's allowed fitted-lookups
pattern. Verify identical features for individual rows and a batch.

Result 879dd21: **0.6892**, training 3.7s, eval 7.2s. Discard: -0.0001.
The median schedule lookup remains sufficient; more window statistics did not help.

## Experiment 39 — exploration: loss-guided tree growth

Hypothesis: allocating splits by gain rather than uniform depth may fit important
time/airport regions more efficiently. Replace depth-limited growth with hist
lossguide, max_depth=0 and max_leaves=4/8/16 for the three members, matching the
maximum leaf counts of depths2/3/4. All round counts, L1, features and weights stay.
Source: https://xgboost.readthedocs.io/en/stable/parameter.html (grow_policy/max_leaves).
This holds a rough capacity bound while changing the shape and allocation of splits.

Result 57d25fc: **0.6894**, training 3.9s, eval 7.0s. Keep: +0.0001.
Uneven split allocation helps slightly under the same approximate leaf capacity.

## Experiment 40 — follow-up: intermediate L1 with loss-guided trees

Hypothesis: reg_alpha=10 may balance useful weak effects and noise better than5,
while avoiding the underfitting seen at20. This is one intermediate check inside
the observed 5-versus20 regularization bracket, now with the kept loss-guided
ensemble. Keep every other parameter, feature and weight fixed.

Result 2e97e07: **0.6895**, training 3.9s, eval 6.8s. Keep: +0.0001.

## Synthesis after 40 experiments

Best: 2e97e07, **0.6895** (+0.0152 from baseline). DART and geographic features
failed to improve. L1=5 gave a substantial gain;20 was too strong, while10 added a
small gain with loss-guided growth. Removing the route schedule lookup and Winter
feature improved both AUC and simplicity. Extra operating-window statistics did
not help. Source-year seasonal label priors remain harmful even though Summer
and holiday features help under month-balanced training.
Current theory: pooled seasonal/travel context plus sparse operational interactions
is the useful signal; over-detailed source-year priors and extra schedule/geographic
features mostly add noise. The saved ensemble remains fast and self-contained.
Next: mild target smoothing, numeric split resolution and sampling/leaf allocation,
with further ablations when an added component looks redundant.

### Research refresh

- https://arxiv.org/abs/1906.02629 (soft-target regularization; evidence is for neural
  networks, so its transfer to boosted trees is an experiment, not an established claim).
- https://xgboost.readthedocs.io/en/stable/parameter.html (reg:logistic returns
  probabilities and permits a regression interface for soft targets).

## Experiment 41 — exploration: mild label smoothing

Hypothesis: fitting targets .05/.95 instead of0/1 may reduce overconfident fits to
unpredictable delays. Use reg:logistic XGBRegressor members on y_soft=.9*y+.05,
retain all sample weights/features/tree settings, and expose the same weighted
mean through a two-column predict_proba adapter. prepare and the harness still
return/use original binary labels; only training targets change. No extra metric.

Result 0d44d86: **0.6897**, training 3.7s, eval 6.8s. Keep: +0.0002.
Mild target smoothing helps slightly; harness reload and evaluation succeeded
with the saved regression-to-probability ensemble adapter.

## Experiment 42 — exploration: coarser numeric histogram cuts

Hypothesis: max_bin=64 rather than256 reduces sensitivity to fine timetable,
distance and relative-schedule distinctions without removing those features.
Change histogram resolution in all members, retaining categories, soft labels,
leaf limits, L1 and weights. Unlike experiment11, this affects all numeric inputs
and is tested in the much richer regularized ensemble.
Source: XGBoost parameter reference on max_bin and histogram split accuracy.

Result c0d2c85: **0.6893**, training 3.7s, eval 6.8s. Discard: -0.0004.
The numeric detail retained by default256 bins remains useful.

## Experiment 43 — exploration: carrier-origin category under strong regularization

Hypothesis: a carrier's station-specific operations can be represented directly
by a CarrierOrigin category, complementing its median departure-time feature.
This is different from experiment7's Origin–Dest route category: the interaction
is operationally narrower, and now L1=10, soft labels, temporal weighting and the
leaf-limited ensemble provide much stronger regularization. Fit the category
mapping only on train; unknown combinations become missing. All other settings
unchanged. Source: previously researched XGBoost categorical handling documentation.

Result 8d5d93c: **0.6897**, training 4.1s, eval 7.3s. Discard: equal AUC,
extra mapping/feature and slower preparation. The numeric schedule context suffices.

## Experiment 44 — ablation: remove recency weighting

Hypothesis: six-month recency gave only a small early gain and may now be redundant
with calendar pooling and the regularized soft-label ensemble. Remove just the
recency multiplier and its month parsing, keeping monthly class balance and
mean-one normalization. This tests an inherited component in the improved model,
and would simplify training if AUC is preserved.

Result b5dcec2: **0.6888**, training 3.7s, eval 6.8s. Discard: -0.0009.
Recency weighting still contributes in the final feature family.

### Plateau research after experiment44

Three consecutive discards within0.001 of the best prompted renewed research.
https://xgboost.readthedocs.io/en/stable/treemethod.html explains the distinction
between static hist cuts and per-tree Hessian-weighted approximate sketches,
and recommends considering higher max_bin for accuracy without the full cost
of repeated sketching. Also reviewed raw-margin prediction for a possible
alternative ensemble pooling rule:
https://xgboost.readthedocs.io/en/stable/prediction.html

## Experiment 45 — follow-up: finer histogram cuts

Hypothesis: the loss from64 bins in experiment42 suggests useful numeric detail
is being removed. Test512 rather than the default256 bins, retaining all capacity
and regularization settings. This checks the opposite, accuracy-oriented side
of the split-resolution tradeoff documented above.

Result 740085f: **0.6893**, training 3.7s, eval 7.0s. Discard: -0.0004.
Both64 and512 bins lose to default256; stop exploring histogram resolution.

## Experiment 46 — exploration: average ensemble log-odds

Hypothesis: combining member margins before sigmoid may preserve useful confident
rankings that probability averaging compresses. Keep the exact same training and
1:2:1 weights, but request output_margin=True from each logistic regressor,
average the margins, and sigmoid once. This changes the model's pooling rule;
prepare and harness evaluation remain unchanged. Read the primary prediction/API
reference for raw-margin semantics before this plateau experiment:
https://xgboost.readthedocs.io/en/stable/prediction.html

Result bb6c56e: **0.6897**, training 3.7s, eval 7.1s. Discard: equal AUC
without a simpler/faster implementation. Keep probability averaging.

## Experiment 47 — exploration: feature sampling in the expanded ensemble

Hypothesis: selecting85% of features per tree encourages complementary use of
raw time, carrier schedule and calendar context, reducing dependence on one split
sequence. Set colsample_bytree=.85 for all members, leaving row sampling at1.
Unlike experiment12, this uses one tree per round, the expanded features, soft
labels and strong L1, and isolates column sampling rather than adding parallel trees.
Source: XGBoost parameter reference on column sampling and regularization.

Result 8a28150: **0.6895**, training 3.6s, eval 7.1s. Discard: -0.0002.
The current ensemble works better with all features available to each tree.

## Experiment 48 — follow-up: additional pooled travel holidays

Hypothesis: extending the successful pooled holiday flags to Memorial Day and
Labor Day improves coverage without creating holiday-specific parameters.
Compute the last Monday in May and first Monday in September from the row's
month/day/weekday; include cross-month windows into June and from August.
Keep the same three pooled flags, with no additional model columns.
Source: OPM holiday definitions already researched in experiment29.
Verify moving-date and boundary cases using synthetic rows before the harness run.

Result 6523914: **0.6887**, training 3.7s, eval 6.9s. Discard: -0.0010.
Broader holiday pooling is harmful; keep the original four holidays rather than
assuming more calendar coverage is always useful.

## Experiment 49 — follow-up: stronger soft targets

Hypothesis: experiment41's mild smoothing gain may extend to a little stronger
noise regularization. Fit y_soft=.8*y+.1 instead of .9*y+.05; everything else
including loss-guided leaf limits, L1=10 and sample weighting stays unchanged.
This is a targeted follow-up to the only successful objective modification,
with the same unmodified binary-label harness evaluation.
Source: the label-smoothing paper and logistic-objective documentation researched
in experiments40–41; applying it to trees remains an empirical adaptation.

Result fa375e1: **0.6894**, training 3.7s, eval 6.7s. Discard: -0.0003.
The mild .05/.95 targets remain preferable to stronger smoothing.

## Experiment 50 — exploration: minimum split improvement

Hypothesis: gamma=1 removes low-gain late-stage splits without changing the
maximum leaf count. Add this split-level regularizer to all members; retain
L1=10, mild soft targets and all other kept settings. It acts on whether to split,
which differs from L1's shrinkage of leaf weights.
Read the primary parameter documentation before testing:
https://xgboost.readthedocs.io/en/stable/parameter.html (min_split_loss).

Result 8dc2c14: **0.6897**, training 3.7s, eval 7.0s. Discard: equal AUC
without a measured speed or code simplification benefit.

## Synthesis after 50 experiments

Best: 0d44d86, **0.6897** (+0.0154 from baseline). Mild soft targets gave a small
gain; stronger smoothing did not. Default256 histogram bins beat64 and512.
Carrier-origin categories, log-odds pooling and gamma1 tied but added complexity.
Recency weighting remains useful. Feature sampling and broader holiday pooling
hurt. Recent experiments have established a stable accuracy plateau; favor the
simpler retained model and finish with a semantics-preserving speed improvement.

### Research refresh

https://xgboost.readthedocs.io/en/latest/python/examples/feature_weights.html
shows weighted column sampling, a possible future alternative to uniform feature
sampling: preserve frequent access to the dominant departure-time feature while
diversifying weaker features. This remains untested in this run.

## Experiment 51 — simplification/speed: cheaper per-row calendar preparation

Hypothesis: the harness calls prepare on single rows, so scalar calendar arithmetic
inside a local helper avoids multiple tiny NumPy operations per row. Retain the
same four calendar columns and every model setting. Verify exact feature equality
against the kept implementation on all200,000 training rows, plus single-row
invariance, before running the unchanged harness. Keep only if AUC is preserved
and total evaluation cost is reduced. All transformations remain inside prepare.

Result d9dcf2d: **0.6897**, training 3.7s, eval 6.1s, total9.8s. Keep:
identical AUC and exact training features, with faster calendar preparation.
Full-frame equivalence passed on all200,000 training rows, plus single-row checks.

## Final summary

- Best Eval AUC: **0.6897** at **d9dcf2d0a3950808e834f691b9023917ba120736**, branch **oct6**.
- Baseline: **0.6743** at b15ec66; absolute improvement **0.0154**.
- Completed **51 experiments plus the baseline** (52 harness runs):
  **20 kept** including baseline, **32 discarded**, **0 crashes**.
- Final artifact: `artifacts/d9dcf2d0a3950808e834f691b9023917ba120736.pkl` (about3.2MB).
- Final run: training3.7s including startup/preparation, evaluation6.1s, total9.8s.
- Clock reached the program's less-than-two-minutes stopping threshold before wrap-up.

### Retained approach

Three XGBoost logistic regressors with4/8/16 leaf limits and500/300/200 boosting
rounds, averaged in a1:2:1 ratio. Loss-guided histogram trees use rate.05,
child weight20, L2=10 and L1=10. Training targets are .05/.95; the evaluation
labels remain binary. Monthly class balancing and six-month recency weights
reduce dependence on source-year patterns.

Features are raw departure time and distance; native categorical weekday, carrier,
origin and destination; a train-fitted carrier-origin median schedule offset;
Summer and pooled holiday/pre/post-holiday flags for Thanksgiving, Christmas,
New Year's Day and July4. Unknown categories/pairs map to missing. Every feature
is computed inside prepare from its row plus fixed train-fitted lookups.

### What worked

Removing raw month/day categories, regularized shallow structure, averaging
complementary leaf capacities, modest temporal weighting, compact holiday/Summer
features, L1 shrinkage, mild target smoothing, and targeted simplifications.
Preparation changes substantially reduced row-by-row evaluation cost.

### What did not

Longer/deeper unrestricted fits, raw route categories, broad one-vs-rest category
splits, purely additive feature effects, extra geography/window lookups, DART,
pairwise ranking, restoring source seasonal priors, stronger recency/smoothing,
nondefault histogram resolution, uniform feature sampling and broader holiday pooling.
Small AUC ties were discarded unless the code became simpler or faster.

### Next directions

Try weighted feature sampling that protects the dominant departure-time signal,
using the primary XGBoost feature-weight example researched after experiment50.
Further feature and ensemble ablations could reduce cost. Any additional model
claims should be checked through the human's separate holdout process; no holdout
performance is inferred here from the Eval AUC gains.

### Final verification

All52 result rows are unique and well formed; all successful runs have their
commit-addressed artifacts. The branch is at the final kept commit, the tracked
working tree is clean, only train.py differs from the starting commit, outputs
remain uncommitted, and save_and_evaluate(model, prepare) remains the last call.
