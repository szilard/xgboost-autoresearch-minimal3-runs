# Research log — oct6

Baseline — 8d9c760: unchanged starter model, Eval AUC 0.6743; training 0.6s, full run 31.8s.

Initial research:
- XGBoost parameter reference: https://xgboost.readthedocs.io/en/stable/parameter.html — learning rate controls per-tree updates; max_depth and min_child_weight control complexity; subsample and colsample_bytree regularize; hist is the default tree method.
- XGBoost categorical tutorial: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html — categorical splits can use one-hot or partitioning, controlled by max_cat_to_onehot. Encoding must remain consistent at inference.
- UC Berkeley air-travel-delay project: https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches — scheduled time, carrier, and route context can carry delay signal. The project page was unavailable to open; search summary only.

Experiment 1 hypothesis (exploration): 100 trees may underfit; try 400 trees at otherwise baseline settings.
Experiment 1 — 8d58d96: Eval AUC 0.6652, discard. Raising rounds from 100 to 400 with depth 6 hurt by 0.0091, suggesting fitting the 2005 sample more closely does not transfer to 2006.

Experiment 2 hypothesis (follow-up): the baseline trees may be too deep; reduce max_depth from 6 to 4 at 100 rounds to regularize interactions. Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html
Experiment 2 — 77f4cfb: Eval AUC 0.6789, keep. Depth 4 improves by 0.0046 over baseline while shortening training and artifact size.

Experiment 3 hypothesis (follow-up): depth-4 trees have less capacity per round, so 200 rounds may improve over 100 without the depth-6 overfit seen in experiment 1.
Experiment 3 — 34af316: Eval AUC 0.6777, discard. More depth-4 rounds lost 0.0012, so the best round count at depth 4 may be at or below 100.

Experiment 4 hypothesis (follow-up): reducing depth to 3 at 100 rounds may further cut year-specific interactions while retaining broad departure-time and airport effects.
Experiment 4 — 2156491: Eval AUC 0.6798, keep. Smaller depth gives another 0.0009 gain and a 0.4 MB artifact.

Experiment 5 hypothesis (follow-up): depth 2 may generalize better still by limiting airport and schedule interactions across years. Use the same 100 rounds.
Experiment 5 — 69556f5: Eval AUC 0.6751, discard. Depth 2 lost 0.0047 versus depth 3; some interactions matter.

Experiment 6 hypothesis (follow-up): depth 3 at 150 rounds may capture those interactions more fully without the overfit at higher depth.
Experiment 6 — 7bb42f5: Eval AUC 0.6805, keep. At depth 3, adding 50 rounds helps by 0.0007, unlike at depth 4.

Experiment 7 hypothesis (follow-up): further boosting to 250 rounds at depth 3 may improve until a shallower-model capacity limit is reached.
Experiment 7 — 2ae43f5: Eval AUC 0.6805, discard. It tied the 150-round score but is larger and slower. The kept 150-round model has CRSDepTime importance 0.445 (XGBoost gain share).

Research before first feature change: https://arxiv.org/abs/1911.01605 studies flight departure delay with historical scheduling table features. This dataset lacks operational/weather data; we can still derive within-hour scheduling information from CRSDepTime.
Experiment 8 hypothesis (exploration): minute within hour may separate flight schedule patterns hidden by the four-digit clock representation; add DepMinute while retaining CRSDepTime.
Experiment 8 — 23860d6: Eval AUC 0.6805, discard. DepMinute tied the best, but adds code and about 1.6s to evaluation.

Experiment 9 hypothesis (ablation): DayofMonth may encode one-off 2005 weather/date effects that do not transfer to 2006. Remove it while retaining Month and DayOfWeek.
Experiment 9 — a61db0b: Eval AUC 0.6809, keep. Dropping DayofMonth improved by 0.0004 and eval became 3.5s faster. This supports the hypothesis that year-specific day effects are noisy.

Experiment 10 hypothesis (ablation): Distance had the lowest importance (0.016 share) in an earlier kept model and could be dispensable; remove it to seek a smaller, faster model.
Experiment 10 — c44033c: Eval AUC 0.6799, discard. Distance is low-importance but still useful (loss 0.0010).

## Synthesis after experiments 1–10
Depth 6 at 400 rounds overfit badly; depth 3 at 150 rounds is the strongest structure (0.6805 before calendar ablation). Depth 2 underfit. Removing DayofMonth improved to current best 0.6809, consistent with nonrecurring date-specific effects across years. Departure minute added no measured benefit, while distance contributes despite low split importance. Current theory: robust coarse time/season, carrier, and airport signals dominate; explicit route or carrier/airport interactions might let shallow trees capture operational patterns without deep trees.

Fresh research: an original solution on this same flight-delay task constructs a route category from Origin+Dest and considers carrier/route interactions: https://gist.github.com/akatasonov/fc5f031791a3ad0344bb78272008de4f . XGBoost categorical documentation explains consistent categories and partition-based splitting: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html . Adaptation here: train-derived levels only, no use of evaluation rows while fitting the feature.

Experiment 11 hypothesis (exploration): a route category can expose origin-destination interactions to depth-3 trees, where separately splitting on both airports consumes two levels. This may increase useful capacity while retaining shallow regularization.
Experiment 11 — 9f5fc98: Eval AUC 0.6719, discard. Route category overfit and increased evaluation from 26.6s to 38.7s. The raw route interaction is too sparse for this year-to-year split.

Experiment 12 hypothesis (exploration): min_child_weight=10 requires more support before creating a child node, potentially reducing airport/category overfit even in the original feature set. Source: https://xgboost.readthedocs.io/en/stable/parameter.html
Experiment 12 — 03b211a: Eval AUC 0.6810, keep. The 0.0001 gain is small but meets the strict keep rule. Regularizing rare splits appears at least neutral.

Experiment 13 hypothesis (follow-up): min_child_weight=30 imposes more support per leaf; if sparse 2005-specific airport patterns still dominate, it should improve cross-year AUC further.
Experiment 13 — 3a71508: Eval AUC 0.6811, keep. Stronger child-weight regularization helps by another 0.0001, though the effect is near metric precision.

Experiment 14 hypothesis (follow-up): min_child_weight=100 will test whether substantially suppressing sparse leaves continues to improve cross-year ranking or starts to erase useful airport interactions.
Experiment 14 — 086c851: Eval AUC 0.6811, discard. It ties weight 30 without a simplicity or speed gain. Child-weight effect has plateaued at metric precision.

Inspecting the kept XGBoost configuration showed max_cat_threshold=64 and max_cat_to_onehot=4. The parameter docs say max_cat_threshold limits categories considered per partition split to prevent overfit: https://xgboost.readthedocs.io/en/stable/parameter.html
Experiment 15 hypothesis (exploration): reducing max_cat_threshold to 16 may regularize partitions of high-cardinality Origin and Dest without removing their useful signal.
Experiment 15 — 3d99637: Eval AUC 0.6760, discard. Limiting category partitions to 16 erased useful airport groupings; the default 64 is better here.

Experiment 16 hypothesis (ablation/simplification): pd.Categorical with explicit training categories already maps unseen values to missing; removing the extra per-call isin/where will preserve features and AUC but shorten row-wise evaluation. This tests an implementation simplification within the same model.
Experiment 16 — d3d439b: Eval AUC 0.6811, keep by equal-score simplification. Eliminating redundant isin/where preserves results and cuts evaluation time from 26.6s to 18.3s.

Experiment 17 hypothesis (exploration): subsample=0.8 injects row-level randomness into each tree and may reduce the influence of sample-specific 2005 patterns. Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html
Experiment 17 — e30ebc8: Eval AUC 0.6795, discard. Row sampling hurts 0.0016. It may remove rare airport signal rather than reduce overfit.

Experiment 18 hypothesis (exploration): colsample_bytree=0.8 gives non-time features some trees without the dominant CRSDepTime split, perhaps allowing complementary carrier/airport effects to improve ranking. Source: https://xgboost.readthedocs.io/en/stable/parameter.html
Experiment 18 — a9fc916: Eval AUC 0.6806, discard. Column sampling loses 0.0005 and raises training time; the available features are few and all appear useful.

Experiment 19 hypothesis (exploration): gamma=1 requires a larger loss gain for each split and may suppress small sample-specific airport/date effects while keeping strong splits. Source: https://xgboost.readthedocs.io/en/stable/parameter.html
Experiment 19 — 9774a5e: Eval AUC 0.6811, discard. Gamma=1 ties without clear speed/simplicity benefit. Split-gain regularization does not add to min_child_weight=30.

Experiment 20 hypothesis (follow-up): depth 4 might now learn useful carrier-airport-time interactions because min_child_weight=30 and removal of DayofMonth suppress overfit; compare at the same 150 rounds. Earlier depth 4 had child weight 1 and included DayofMonth.
Experiment 20 — 51874f6: Eval AUC 0.6793, discard. Even with child weight 30 and no DayofMonth, depth 4 loses 0.0018.

## Synthesis after experiments 11–20
The high-cardinality route category hurt substantially; direct route identity is too sparse for this cross-year test. min_child_weight at 10 and 30 each added a small 0.0001. More severe child weight, a tighter category threshold, row/column sampling, gamma, and a deeper tree did not improve. Simplifying prepare cut evaluation from 26.6s to 18.3s with equal AUC. Best remains 0.6811 at d3d439b. Current theory: broad airport/season/time structure transfers, but fine categorical interactions overfit. Next try improved numerical split resolution or alternate growth policy rather than adding sparse identities.

Fresh research: XGBoost tree-method documentation says hist uses a global quantile sketch; larger max_bin can improve split accuracy, while approx uses Hessian-dependent sketches and sometimes helps nonconstant-Hessian objectives: https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html . The parameter reference identifies max_bin as the number of continuous-feature bins: https://xgboost.readthedocs.io/en/stable/parameter.html .
Experiment 21 hypothesis (exploration): CRSDepTime has 1,162 distinct values and dominates importance. Raising max_bin from 256 to 512 may place more useful departure-time split points without adding features or depth.
Experiment 21 — 7f500c3: Eval AUC 0.6809, discard. More histogram bins lowered by 0.0002; 256 was sufficient for these features.

Experiment 22 hypothesis (exploration): tree_method=approx uses Hessian-aware sketching each iteration for nonconstant-Hessian logistic loss, which might find more transferable splits than default hist. Source: https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html
Experiment 22 — 3ce37c8: Eval AUC 0.6808, discard. Approx sketching is 2.3s slower to train and loses 0.0003.

Experiment 23 hypothesis (exploration): treat Month as numeric 1–12 instead of categorical. Numeric splits constrain groups to adjacent months, which may smooth seasonal structure and avoid fitting arbitrary 2005-specific month partitions. This is an inference from XGBoost's numerical-vs-categorical split definitions: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html
Experiment 23 — e1ab62c: Eval AUC 0.6811, keep by the equal-score faster rule. Numeric Month evaluates in 17.8s versus 18.3s and artifact is 0.5 MB versus 0.6 MB. The modeling effect is below display precision.

Plateau research: XGBoost monotonic constraints can encode strong directional prior beliefs but may make histogram trees shallow: https://xgboost.readthedocs.io/en/stable/tutorials/monotonic.html . XGBoost feature interaction constraints can also limit noisy interactions: https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html . A primary study describes hour-by-hour delay propagation: https://arxiv.org/abs/1304.2528 . In our training sample, delay rate climbs from 0.19 at 05:00 to 0.65 at 20:00, then falls late at night; the overnight exception is a risk for a global constraint.
Experiment 24 hypothesis (exploration): a positive monotonic constraint on CRSDepTime may suppress overfit within the main daytime period enough to compensate for late-night exceptions.
Experiment 24 — 0e6644a: Eval AUC 0.6796, discard. A global increasing time constraint is too rigid, likely due late-night and overnight reversal.

Experiment 25 hypothesis (exploration): use the route's median scheduled departure time fitted on train as an unsupervised lookup, and add each flight's difference from it. This conveys unusual route scheduling to shallow trees without the high-cardinality route category that overfit in experiment 11. The technique is explicitly illustrated in program.md; the source dataset solution also explores route identity: https://gist.github.com/akatasonov/fc5f031791a3ad0344bb78272008de4f .
Experiment 25 — 54bfecf: Eval AUC 0.6813, keep. A train-fitted route schedule offset adds 0.0002 without using labels; evaluation remains fast enough (19.4s).

Experiment 26 hypothesis (follow-up): carrier-origin median scheduled time can capture an airline's hub schedule; deviation from that median may add context complementary to route offset.
Experiment 26 — c0e8c0b: Eval AUC 0.6822, keep. Carrier-origin schedule offset adds 0.0009 over route offset. The combination looks useful, despite a modest 1.4s evaluation cost.

Target-encoding research for a possible later direction: scikit-learn's TargetEncoder documentation warns that encoding the training rows using their own labels causes leakage, and uses cross-fitting to prevent it: https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html . If tried, the lookup must be fitted only on other training rows for each deterministic row partition and reused identically in row-wise evaluation. No target-encoding experiment is being proposed yet.

Experiment 27 hypothesis (follow-up): an origin-wide median departure-time offset provides a more stable airport baseline than carrier-origin alone and may add signal for sparse carrier-airport combinations.
Experiment 27 — 3f3d81a: Eval AUC 0.6820, discard. Airport-wide offset adds no useful information beyond route and carrier-origin offsets.

Experiment 28 hypothesis (exploration): carrier-destination median departure-time offset captures destination service timing, different from the origin-wide ablation and from carrier-origin schedule; it may reflect arrival-bank planning or route operations.
Experiment 28 — 072e278: Eval AUC 0.6815, discard. Carrier-destination offset loses 0.0007 and adds time; origin-side carrier context seems stronger for departure delays.

Experiment 29 hypothesis (exploration): learning_rate=0.05 with 300 rounds holds approximate total boosting strength constant while making each update smaller; this may smooth responses to the new schedule-offset features. Source: https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html
Experiment 29 — 365b27e: Eval AUC 0.6820, discard. Smaller learning rate with twice the rounds loses 0.0002 and increases artifact size. The original update size is adequate.

Experiment 30 hypothesis (follow-up): route and carrier-origin schedule offsets may make a fourth tree level useful for combining operational context with month/week/time, even though depth 4 lost before those offsets existed.
Experiment 30 — 6faca08: Eval AUC 0.6795, discard. Extra depth loses even with schedule offsets.

## Synthesis after experiments 21–30
Increasing numerical split resolution and using approx did not help. Numeric month tied with a modest speed gain. A global monotonic departure-time prior was too rigid. The route and carrier-origin *schedule offsets* (unsupervised train-fitted medians) improved AUC to 0.6822; airport-wide and carrier-destination offsets did not. Smaller learning rate and depth 4 failed on the new feature set. Current theory: compact, train-fitted operational context helps shallow trees, while raw high-cardinality route identity and extra model complexity overfit.

Fresh research: scikit-learn's target-encoding example shows why fitting an encoding on the same training row can leak the label and why cross-fitting prevents this: https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html . A benchmark of high-cardinality encoders likewise reports the value of smoothing and independent training observations: https://link.springer.com/article/10.1007/s00180-022-01207-6 .
Experiment 31 hypothesis (exploration): a smoothed carrier-origin delay-rate prior may expose stable airline-airport differences to shallow trees. A deterministic row-only fold selects a lookup trained on the other four folds for every training and evaluation row; no row's target contributes to its own feature. The encoded value is a smoothed rate, never a row count.
Experiment 31 — ae5f066: Eval AUC 0.6813, discard. Smoothed cross-fitted carrier-origin delay prior is leakage-safe but loses 0.0009 and adds 2s evaluation time. It likely duplicates categorical learning and may carry 2005-specific carrier-airport rates.

Experiment 32 hypothesis (exploration): max_cat_to_onehot=32 changes 7-level DayOfWeek and 20-level carrier to single-category splits while leaving 283-level airports partition-based. This may avoid unstable arbitrary groupings of carriers/weekdays across years. Source: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html
Experiment 32 — 8a96bf5: Eval AUC 0.6791, discard. Carrier/weekday one-hot splits reduce AUC 0.0031, so partitioning related categories is useful. In the kept model, CRSDepTime now has 0.564 gain share, followed by carrier, month and weekday.

Experiment 33 hypothesis (exploration): categorical departure hour can group noncontiguous hour bands (e.g. overnight and late evening), unlike the numeric CRSDepTime split. This might model the observed 21:00–04:00 reversal more robustly. Original same-dataset solution derives DepHour: https://gist.github.com/akatasonov/fc5f031791a3ad0344bb78272008de4f .
Experiment 33 — d3f440d: Eval AUC 0.6819, discard. Categorical hour loses 0.0003 and adds 3.2s evaluation time. Numeric departure time remains better.

In train, flights scheduled off a five-minute mark have delay rate 0.5266 versus 0.4897 otherwise. The same-dataset solution uses this as a Mod5 indicator: https://gist.github.com/akatasonov/fc5f031791a3ad0344bb78272008de4f .
Experiment 34 hypothesis (exploration): a binary off-five-minute schedule feature summarizes the unusual-minute pattern much more efficiently than the raw DepMinute feature (experiment 8), and may improve shallow-tree ranking.
Experiment 34 — aace12d: Eval AUC 0.6823, keep. Off-five-minute schedule adds 0.0001. The effect is small but distinct from the raw minute feature that tied earlier.

Training-only inspection: flights departing exactly at :00 have delay rate 0.4621 across 20,958 rows, compared with sample rate 0.5. This repeats across hours, so numeric CRSDepTime alone may need many splits to express it.
Experiment 35 hypothesis (follow-up): add an OnHour indicator alongside OffFiveMinuteMark to capture the repeated :00 schedule pattern efficiently.
Experiment 35 — 9c47930: Eval AUC 0.6823, discard. OnHour ties but evaluation is 2.2s slower and code is more complex; no keep-rule advantage.

Experiment 36 hypothesis (exploration): reg_lambda=10 shrinks leaf weights while preserving the split structure allowed by min_child_weight=30, potentially smoothing predictions from the new schedule features across years. Source: https://xgboost.readthedocs.io/en/stable/parameter.html
Experiment 36 — b5ebe62: Eval AUC 0.6818, discard. Stronger L2 shrinkage loses 0.0005, suggesting the existing min-child regularization is enough.

Experiment 37 hypothesis (exploration): lossguide growth with eight leaves lets a shallow-sized tree allocate leaves unevenly to high-gain time/airport regimes instead of depthwise growth. Source: https://xgboost.readthedocs.io/en/stable/parameter.html
Experiment 37 — daa6d22: Eval AUC 0.6811, discard. Leaf-wise growth with eight leaves loses 0.0012; the depthwise shape appears better for these broad signals.

Experiment 38 hypothesis (exploration): treating DayOfWeek as ordinal 1–7 may favor adjacent workday/weekend patterns and reduce arbitrary categorical partitions, analogous to the month encoding that tied with faster evaluation. Numeric split contiguity is explained in https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html .
Experiment 38 — c7593ea: Eval AUC 0.6807, discard. Numeric weekday loses 0.0016; flexible day-group partitions remain important.

Experiment 39 hypothesis (exploration): DayofMonth as numeric may capture broad within-month timing while avoiding the nontransferable 31-category partitioning that hurt in experiment 9.
Experiment 39 — 66651d4: Eval AUC 0.6854, keep. Numeric DayofMonth adds 0.0031, whereas categorical DayofMonth hurt. Smooth, contiguous date splits appear to transfer much better across years than arbitrary day-category groupings.

Experiment 40 hypothesis (follow-up): 225 rounds may let depth-3 trees use the new ordinal day-of-month structure more fully; before adding it, extra rounds did not help.
Experiment 40 — 8ded6b7: Eval AUC 0.6844, discard. More boosting loses 0.0010 even with numeric day-of-month; 150 rounds remain best.

## Synthesis after experiments 31–40
Cross-fitted carrier-origin target rate avoided leakage but added no benefit, and one-hot splits of small categories hurt. Categorical departure hour did not help. A compact off-five-minute indicator gave a small gain. The major gain came from numeric DayofMonth, raising AUC from 0.6823 to 0.6854, whereas categorical DayofMonth had been harmful. This suggests month/day effects are smoother and more transferable when represented as ordered values. Extra rounds after that gain overfit. Current best: 0.6854 at 66651d4.

Fresh research: scikit-learn's time-feature guide discusses continuous and cyclic date representations, including day-of-year boundaries: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html . An aviation prediction paper includes day of month/year among schedule-derived features: https://www.mdpi.com/2226-4310/8/6/152 . We will derive a day-of-year position only from the allowed month/day fields.
Experiment 41 hypothesis (exploration): adding numeric DayOfYear may let shallow trees learn seasonal transitions that cross month boundaries while retaining the strong within-month day effect.
Experiment 41 — 91e2707: Eval AUC 0.6857, keep. Continuous DayOfYear adds 0.0003, consistent with season transitions across month boundaries.

Experiment 42 hypothesis (follow-up): sine/cosine DayOfYear features remove the artificial Dec 31–Jan 1 break and may expose smooth recurring winter/summer regimes to shallow trees. Source: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html
Experiment 42 — e093f07: Eval AUC 0.6845, discard. Cyclic annual sine/cosine features lose 0.0012 and add evaluation time; the direct ordinal calendar values work better.

Experiment 43 hypothesis (exploration): retain numeric Month/DayOfMonth/DayOfYear but add a categorical Month copy. Numeric features capture smooth seasonality, while categorical splits can group distinct months with similar delay behavior. XGBoost category partitioning: https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html
Experiment 43 — f667d1f: Eval AUC 0.6866, keep. Adding MonthCategory to the numeric calendar representation gives 0.0009, confirming both smooth and month-specific seasonal effects are useful.

Experiment 44 hypothesis (follow-up): categorical DayofMonth alongside numeric DayofMonth may capture a small number of recurring date effects while retaining smooth splits. This differs from the earlier categorical-only representation that hurt.
Experiment 44 — 18b8a37: Eval AUC 0.6841, discard. Categorical DayofMonth loses 0.0025 even with numeric DayofMonth; individual date identities remain noisy across years.

Experiment 45 hypothesis (follow-up): add numeric DayOfWeek alongside the existing categorical representation. Numeric-only weekday lost, but a paired representation may capture a broad workweek trend while retaining categorical groupings, as with month.
Experiment 45 — e9e6280: Eval AUC 0.6866, discard. Numeric weekday tied but raised eval from 30.0s to 32.4s, so category alone remains better.

Experiment 46 hypothesis (follow-up): with richer numeric day/month/year features, min_child_weight=10 may permit useful finer seasonal interactions; the earlier 30-over-10 advantage was only 0.0001 on a weaker feature set.
Experiment 46 — 806ba36: Eval AUC 0.6865, discard. Lower min-child weight loses 0.0001; greater leaf support still looks preferable.

Experiment 47 hypothesis (follow-up): min_child_weight=60 may filter 2005-specific date interactions introduced by numeric DayOfMonth and improve transfer, while retaining the strong coarse calendar signal.
Experiment 47 — ea61346: Eval AUC 0.6862, discard. Stronger leaf support loses 0.0004; 30 remains the best tested value on the richer date set.

Experiment 48 hypothesis (follow-up): a fourth tree level may now combine numeric day-of-month, month category, and schedule offsets usefully; previous depth-4 tests predated the successful calendar representation.
Experiment 48 — cc41c09: Eval AUC 0.6842, discard. Depth 4 still overfits, now by 0.0024, even with the richer calendar representation.

Experiment 49 hypothesis (follow-up): new high-signal date features may mean 150 rounds overfit; 225 rounds already lost, so reducing to 100 may improve generalization and simplify the model.
Experiment 49 — cff786d: Eval AUC 0.6852, discard. Fewer rounds lose 0.0014; 150 remains bracketed by worse 100 and 225.

Research before new model structure: XGBoost's random-forest tutorial documents boosted random forests with num_parallel_tree > 1 and multiple boosting rounds: https://xgboost.readthedocs.io/en/stable/tutorials/rf.html . It recommends subsample and column sampling to differentiate trees. This is an ensemble within one XGBoost model, still scored by the unchanged harness.
Experiment 50 hypothesis (exploration): three sampled trees per boosting round may average out sample-specific noise and retain the strong calendar signal, even though single-tree row and column sampling hurt.
Experiment 50 — b12448b: Eval AUC 0.6859, discard. Boosted random forest with three sampled trees per round loses 0.0007 and triples tree count.

## Synthesis after experiments 41–50
Continuous DayOfYear added a small gain. Cyclic annual features hurt, while adding MonthCategory alongside numeric month/day/year improved to current best 0.6866. Categorical DayofMonth and numeric DayOfWeek copies were worse or slower. The original depth 3, 150 rounds, min_child_weight=30 remained best after retuning leaf support, depth, and rounds. A boosted random forest did not help. Current theory: strong calendar structure matters; extra model capacity or noisy rare-day categories overfit.

Fresh research: XGBoost DART documentation describes dropout of boosting trees to prevent overfitting, but warns about slower training: https://xgboost.readthedocs.io/en/stable/tutorials/dart.html . The original DART paper describes why downweighting early influential trees can improve ensemble generalization: https://arxiv.org/abs/1505.01866 .
Experiment 51 hypothesis (exploration): modest DART dropout may prevent dependence on early trees and improve year-to-year ranking while keeping the proven feature set and depth.
Experiment 51 — bdc59df: Eval AUC 0.6850, discard. DART dropout loses 0.0016 and training time rises to 7.3s.

Research for holiday features: a flight-delay ensemble study uses holidays as predictors: https://www.mdpi.com/2076-3417/12/20/10621 . An original U.S. flight analysis defines Thanksgiving's travel period from Wednesday through Sunday around the fourth Thursday of November: https://flyerintel.com/research/holiday-travel-reliability/ . The rule is derivable from each row's month/day/weekday and does not require the hidden year.
Training-only inspection: Thanksgiving Wednesday–Sunday has 2,432 rows and delay rate 0.5008, versus 0.4611 for other November flights. This is suggestive, not an evaluation.
Experiment 52 hypothesis (exploration): a moving Thanksgiving window flag may capture travel demand that numeric DayOfYear cannot align across 2005 and 2006.
Experiment 52 — c8076b0: Eval AUC 0.6866, discard. Thanksgiving window ties and adds 5.9s evaluation time, so it does not meet the keep rule.

Training-only inspection: Dec 23–26 has delay rate 0.5644 (2,268 rows), and Dec 31–Jan 2 has 0.6024 (1,640 rows). July 3–5 is near sample mean. The holiday analysis source defines a Christmas/New Year window crossing the calendar boundary: https://flyerintel.com/research/holiday-travel-reliability/ .
Experiment 53 hypothesis (exploration): a compact Dec 23–Jan 2 flag may reveal a stable holiday-period effect that numeric DayOfYear cannot express with one contiguous split.
Experiment 53 — fa4e3ce: Eval AUC 0.6866, discard. Year-end holiday window ties and adds 3.3s eval time, so explicit holiday flags have not helped.

Feature-importance inspection of best f667d1f: numeric Month has zero gain share; MonthCategory has 0.130, DayOfYear 0.036, and numeric DayofMonth 0.036. The numeric Month input appears redundant.
Experiment 54 hypothesis (ablation/simplification): drop numeric Month as a model input but still parse it locally to compute DayOfYear; expect equal AUC with one fewer column and a simpler model.
Experiment 54 — cc61e23: Eval AUC 0.6866, keep by equal-score simplification. Numeric Month had zero split importance and removal reduced eval from 30.0s to 29.6s.

Experiment 55 hypothesis (ablation): RouteTimeOffset has low gain share (0.015). With stronger calendar features and CarrierOriginTimeOffset, it may no longer contribute; removing it could simplify and speed up prepare at no AUC cost.
Experiment 55 — 05c088e: Eval AUC 0.6862, discard. RouteTimeOffset still contributes 0.0004 despite low importance, so keep it.

Experiment 56 hypothesis (ablation): OffFiveMinuteMark gave only 0.0001 when introduced and has 0.005 gain share. The enriched calendar model may no longer need it; removal could simplify and speed preparation.
Experiment 56 — d1a2176: Eval AUC 0.6865, discard. OffFiveMinuteMark still adds 0.0001; the strict keep rule retains it.

Experiment 57 hypothesis (exploration): reg_alpha=1 applies L1 shrinkage to leaf scores, possibly removing weak year-specific date corrections while preserving the useful larger effects. Source: https://xgboost.readthedocs.io/en/stable/parameter.html
Experiment 57 — 26f0a7c: Eval AUC 0.6854, discard. L1 shrinkage loses 0.0012; weak leaves appear useful rather than noise.

Experiment 58 hypothesis (exploration): carrier-route median scheduled time may reveal flights unusually timed for that carrier's exact service, complementary to route-wide and carrier-origin schedule offsets. There are 6,588 carrier-route groups in train, so the effect may be noisy; the lookup uses no target labels and is fitted on train only.
Experiment 58 — c859a20: Eval AUC 0.6860, discard. Carrier-route time offset loses 0.0006; too many sparse service groups make its median less useful than broader offsets.

Experiment 59 hypothesis (follow-up): lowering max_cat_threshold to 16 badly hurt earlier; raising it from 64 to 128 may let 283-level airport categories form more useful partition groups with the current richer calendar features. Source: https://xgboost.readthedocs.io/en/stable/parameter.html
Experiment 59 — 76d5f1f: Eval AUC 0.6849, discard. More categories per split lose 0.0017, confirming the default threshold 64 is a good balance; 16 had also hurt.

Experiment 60 hypothesis (exploration): max_bin=128 coarsens numeric CRSDepTime/DayOfYear split candidates; since 512 bins lost before calendar engineering, fewer bins may regularize year-specific fine thresholds and improve transfer. Source: https://xgboost.readthedocs.io/en/stable/parameter.html

### Experiment 60 — larger histogram bin count
From best cc61e23, set `max_bin=128` to give the histogram tree finer numeric split resolution. Eval AUC was 0.6855, below 0.6866, so discarded. This completes the 51–60 batch. Recent sweeps of ablations, categorical threshold, regularization, and tree binning did not improve on the DayOfMonth + schedule-relative feature set. For the next batch, test whether a flight's distance relative to its carrier's usual flights from the same origin captures a different operating pattern. Flight-delay research discusses airline network and hub effects ([Flight delays in European airline networks](https://www.sciencedirect.com/science/article/abs/pii/S2210539521000146)) and distance/schedule effects ([Generation and prediction of flight delays in air transport](https://ietresearch.onlinelibrary.wiley.com/doi/full/10.1049/itr2.12057)). This is a train-fitted median-distance lookup, with no label aggregates or row-count feature.
Experiment 61 hypothesis (exploration): distance relative to the same carrier's median distance from an origin might identify unusual long- or short-haul services, complementing raw Distance. Train-only median lookup, no target aggregate.
Experiment 61 — e31dea2: Eval AUC 0.6864, discard. The extra distance normalization loses 0.0002 and adds lookup cost. Next, test a broader airport-weekday schedule offset, which can generalize over routes and carriers while representing weekday schedule banks.
Experiment 62 hypothesis (exploration): departure time relative to the origin airport's median time on that weekday may describe weekly schedule banks across routes and carriers. This uses train-only median scheduled time, without labels.
Experiment 62 — 43d5c46: Eval AUC 0.6870, keep. Gain +0.0004 over prior best, suggesting airport-weekday schedule context transfers to evaluation. Next test destination-weekday median scheduled departure offset: destination flight banks may add independent context.
Experiment 63 hypothesis (follow-up): destination-weekday median scheduled departure offset might capture schedule banks not represented by origin-weekday context.
Experiment 63 — 7e2eb2f: Eval AUC 0.6857, discard. Destination-side weekday offset loses 0.0013; likely a weaker description of departure operations. Next test the carrier's weekday schedule, a broader group that may generalize across airports.
Experiment 64 hypothesis (follow-up): carrier-wide weekday time offset could represent weekly airline operations across airports with a robust, large training group.
Experiment 64 — 6569090: Eval AUC 0.6859, discard. The carrier weekday axis loses 0.0011. Airport-specific weekday context appears more useful. Next test seasonal changes in an origin's departure-time distribution through a train-fitted origin-month median.
Experiment 65 hypothesis (follow-up): origin-month median departure-time offset might reveal seasonal schedule shifts beyond categorical Month and origin-weekday context.
Experiment 65 — 2f5b55f: Eval AUC 0.6863, discard. The added seasonal airport lookup loses 0.0007. Focus shifts to simplifying the new best: test whether origin-weekday context supersedes RouteTimeOffset.
Experiment 66 hypothesis (ablation): origin-weekday context may replace route-relative time, allowing removal of a lookup and faster evaluation.
Experiment 66 — c321848: Eval AUC 0.6866, discard. Removal loses 0.0004 even though evaluation is about two seconds faster; the route offset remains useful. Next bracket 150 rounds with 175 on the new feature set. Earlier 100 and 225 rounds both scored below the prior best, so 175 is a targeted interpolation.
Experiment 67 hypothesis (hyperparameter interpolation): with origin-weekday offset, 175 boosting rounds may capture slightly more residual structure than 150 without the overfit observed at 225.
Experiment 67 — 172c9ab: Eval AUC 0.6867, discard. The extra 25 rounds lose 0.0003; 150 remains best. Next interpolate min_child_weight=20 between prior tested 10 and 30 to see if modestly smaller leaves help use the new feature.
Experiment 68 hypothesis (hyperparameter interpolation): min_child_weight=20 may allow a few more origin-weekday interactions than 30 while avoiding the weaker result at 10.
Experiment 68 — 2996970: Eval AUC 0.6868, discard. A small reduction in leaf weight loses 0.0002. Final test: replace only the origin-weekday scheduled-time median with a mean, which may summarize the full daily departure distribution better.
Experiment 69 hypothesis (feature-statistic comparison): mean scheduled departure time for each origin-weekday group may describe its overall daily schedule better than median.
Experiment 69 — 1a225de: Eval AUC 0.6863, discard. Mean loses 0.0007; the median is more robust for this feature.

## Final summary
Completed 69 experimental variants plus baseline within the one-hour budget. Baseline Eval AUC was 0.6743 at 8d9c760. Best Eval AUC is 0.6870 at 43d5c46, a gain of 0.0127. Best configuration: 150 boosting rounds, depth 3, min_child_weight 30, native categorical airport/carrier/weekday/month inputs; numeric schedule time, distance, date position, and a five-minute flag; train-fitted route, carrier-origin, and origin-weekday median schedule offsets. The final improvement was the origin-weekday time offset (+0.0004). Follow-ups using destination-weekday, carrier-weekday, origin-month, mean rather than median, route-offset ablation, 175 rounds, and min_child_weight 20 all scored below 0.6870. Restore best commit before stopping.
