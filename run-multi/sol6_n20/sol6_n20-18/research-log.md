# Research log — oct6

## Baseline — 8d9c760
- Unmodified `train.py`: 100 trees, depth 6, eta 0.1, native categoricals.
- Eval AUC 0.6743; training 1.4s, rowwise evaluation 30.4s.
- Train has 200,000 balanced rows, no missing values. Scheduled departure is HHMM (5–2359), which is not a linear measure of time.

## Research before experiments
- [XGBoost parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends controlling complexity with depth, child weight and gamma; subsampling and lower learning rate can reduce overfitting.
- [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) documents categorical partitioning and `max_cat_to_onehot`, with consistent category codes required at inference.
- [Berkeley flight-delay feature study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies scheduled departure hour and carrier as operational signals. That motivates converting HHMM to minutes and testing time interactions.

## Experiment 1 — longer boosting schedule (exploration)
Hypothesis: the baseline's 100 trees underfit. Following the XGBoost tuning guide, use 300 trees at eta 0.05 to make smaller updates over more rounds; keep depth and features fixed.
Result: Eval AUC 0.6743, equal to baseline; training and artifact size increased. Discard under the keep rule.

## Experiment 2 — shallower trees (follow-up)
Hypothesis: depth 6 learns year-specific interactions that dilute 2006 generalization. Use depth 4 with 300 small eta 0.05 steps. The tuning guide identifies depth as a main overfitting control.
Result: Eval AUC 0.6795 (+0.0052). Keep; shallower interactions with a longer boosting schedule transfer better to 2006.

## Experiment 3 — departure hour category (exploration)
Hypothesis: departure hour has a non-monotone daily risk profile; XGBoost categorical partitioning can group hours more efficiently than raw HHMM thresholds. The Berkeley study highlights hour-of-day signal, and the XGBoost categorical tutorial documents partitioned splits.
Result: Eval AUC 0.6792 (-0.0003); discard. Hour category adds redundant signal and slows rowwise evaluation.

## Experiment 4 — depth 3 (follow-up)
Hypothesis: reducing interaction depth further improves transfer to 2006. Hold 300 rounds and eta 0.05 fixed; only change max_depth 4 to 3.
Result: Eval AUC 0.6812 (+0.0017). Keep. The depth trend favors simpler interactions.

## Experiment 5 — depth 2 (follow-up)
Hypothesis: the depth trend continues; hold all other settings fixed to find the complexity sweet spot.
Result: Eval AUC 0.6760 (-0.0052). Discard. Depth 3 is the current best of the tested depths.

## Experiment 6 — more depth-3 trees (follow-up)
Hypothesis: 300 depth-3 trees leave useful low-order structure unlearned. Double rounds at the same eta and depth to isolate boosting duration.
Result: Eval AUC 0.6810 (-0.0002). Discard; extra rounds add little and slightly hurt transfer.

## Research on interaction features
- [XGBoost categorical tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains category grouping in splits and inference recoding. A combined carrier-hour category could expose an interaction to a depth-3 tree in one split.
- [scikit-learn TargetEncoder docs](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html) warn that training on encodings built from the same targets causes leakage and recommend cross fitting. I am avoiding target-derived lookup features for now.
- In `train.csv`, carrier-hour has 401 levels with median 360 rows per level, making the interaction more stable than route or origin-hour.

## Experiment 7 — carrier by hour category (exploration)
Hypothesis: carrier operations vary across the day; a combined categorical split can model this with fewer tree levels. Derive category levels from train and apply them identically rowwise.
Result: Eval AUC 0.6787 (-0.0025), rowwise eval 36.6s. Discard; interaction is noisy or redundant.

## Experiment 8 — one-hot categorical splits (exploration)
Hypothesis: native category partitioning groups airports or carriers based on 2005-specific noise. Per-category splits (`max_cat_to_onehot=1000`) may regularize and transfer better. Source: XGBoost categorical tutorial and parameter reference.
Result: Eval AUC 0.6735 (-0.0077). Discard. Category grouping is important for these high-cardinality predictors.

## Experiment 9 — larger minimum child weight (follow-up)
Hypothesis: some categorical partitions form small leaves that capture 2005 noise. Raising min_child_weight from 1 to 10 regularizes leaf formation. Source: XGBoost parameter tuning guide.
Result: Eval AUC 0.6810 (-0.0002). Discard; this level of leaf regularization did not help.

## Experiment 10 — row subsampling (exploration)
Hypothesis: using 80% of rows per tree reduces overfitting to 2005-specific variation. Keep all other settings fixed. Source: XGBoost tuning guide.
Result: Eval AUC 0.6798 (-0.0014). Discard.

## Synthesis after 10 experiments
- Best: 0.6812 at 34f38d2, using 300 trees, depth 3, eta 0.05.
- Shallower trees helped until depth 2 underfit. More depth-3 rounds, heavy child-weight regularization and row subsampling did not help.
- Derived hour and carrier-hour categorical features hurt. Native category partitioning is much better than forcing one-hot splits.
- Working theory: the small set of base features needs broad categorical grouping and modest interaction depth to generalize across years. Next test stable calendar and location representations, plus feature ablations.

## Research refresh after 10 experiments
- [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe `max_cat_threshold` as a cap on categories considered at each partition split, intended to prevent overfitting. This is relevant because grouped categorical splits help, yet airport IDs are numerous.
- [scikit-learn time feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) discusses cyclic encodings for month, weekday and hour; tree models can already handle numeric time, so I will test calendar representation changes cautiously.

## Experiment 11 — smaller category split threshold (exploration)
Hypothesis: restricting category partitions to 16 candidates per split reduces year-specific airport grouping noise while retaining the useful grouped-split mechanism.
Result: Eval AUC 0.6737 (-0.0075). Discard. Restricting partitions to 16 is too severe.

## Experiment 12 — larger category split threshold (follow-up)
Hypothesis: the poor result at threshold 16 means large category groups matter; allow up to 128 candidates to see whether the default is limiting them.
Result: Eval AUC 0.6795 (-0.0017). Discard; the default category threshold is better than 16 or 128.

## Experiment 13 — remove day of month (ablation)
Hypothesis: day-of-month effects in 2005 may be date-specific and shift in 2006. Its model gain is moderate (102 vs 708 for departure time). Removing it may reduce calendar overfit.
Result: Eval AUC 0.6811 (-0.0001), faster but keep rule requires no decline. Discard. The feature retains slight useful signal.

## Experiment 14 — ordered day of month (follow-up)
Hypothesis: day of month carries weak but useful signal; numeric splits can pool neighboring days and reduce arbitrary categorical groups that may overfit 2005.
Initial attempt crashed: DayofMonth values are strings like `c-22`, so XGBoost rejected them as numeric. Fixed by parsing the integer inside `prepare` and amended the experiment commit.
Result: Eval AUC 0.6856 (+0.0044), eval 28.8s. Keep. Adjacent calendar days pooling via numeric splits generalizes much better.

## Experiment 15 — ordered month (follow-up)
Hypothesis: numeric month splits pool adjacent months, like the successful day-of-month representation, reducing year-specific categorical grouping. Keep all other settings fixed.
Result: Eval AUC 0.6854 (-0.0002). Discard; month grouping retains a small advantage, possibly for winter wrap-around.

## Experiment 16 — ordered weekday (follow-up)
Hypothesis: adjacent weekdays have related travel demand patterns, and numeric splits can pool them more stably than arbitrary categorical subsets. This uses the same parsing scheme that helped day of month.
Result: Eval AUC 0.6833 (-0.0023). Discard; weekday has non-contiguous risk patterns better handled categorically.

## Experiment 17 — day-of-year feature (exploration)
Hypothesis: one ordered day-of-year variable exposes seasonal boundaries to shallow trees without a month-by-day interaction. Both data years are non-leap years. The fixed cumulative-month lookup is applied identically to each row.
Result: Eval AUC 0.6857 (+0.0001), eval 32.9s. Keep. Benefit is small; next test whether it can replace a redundant calendar input.

## Experiment 18 — day-of-year replaces day of month (ablation)
Hypothesis: day of year contains the same calendar position as the numeric day-of-month plus month, so the separate day-of-month split may be redundant and can be removed.
Result: Eval AUC 0.6844 (-0.0013). Discard. Numeric day-of-month retains a useful within-month effect beyond day of year.

## Experiment 19 — day-of-year replaces month (ablation)
Hypothesis: day of year gives precise seasonal position, perhaps making month category redundant. The month value still enters the deterministic day-of-year calculation.
Result: Eval AUC 0.6854 (-0.0003). Discard. Month categories still add value alongside day of year.

## Experiment 20 — cyclic annual features (exploration)
Hypothesis: sine/cosine day-of-year lets a depth-3 tree group late December and early January in one split, while retaining calendar position. Source: [scikit-learn cyclical feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html).
Result: Eval AUC 0.6842 (-0.0015), evaluation slower. Discard.

## Synthesis after 20 experiments
- Best: 0.6857 at 144065e. Parsing day-of-month into an ordered number supplied the largest new gain; day-of-year gave a small additional gain.
- Month and weekday are better categorical, and month/day each remain useful alongside day-of-year. Annual sine/cosine hurt.
- Large category groups matter; both one-hot splits and a small category partition limit sharply hurt AUC. The default category settings perform better than tested alternatives.
- Next direction: test route and airport-level operational structure, plus time-of-day transformations and measured feature ablations.

## Research refresh after 20 experiments
- [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) confirm histogram models quantize numerical features with `max_bin=256`; a coarse hour feature may preserve exact hourly boundaries separately from the 1162-valued HHMM input.
- [Flight delay situational-awareness research](https://arxiv.org/abs/1911.01605) emphasizes airport-level operational state, motivating origin/route schedule features that can be computed only from training data.

## Experiment 21 — numeric departure hour (exploration)
Hypothesis: a separate 0–23 hour feature makes hourly boundaries accessible to the histogram learner while retaining the fine-grained HHMM value. Earlier categorical hour hurt; this is a lower-capacity representation.
Result: Eval AUC 0.6856 (-0.0001), eval slower. Discard; HHMM already exposes hourly boundaries adequately.

## Experiment 22 — minute within hour (exploration)
Hypothesis: scheduled minute (0–59) may encode carrier scheduling conventions repeatedly across hours. Raw HHMM cannot group the same minute values across the day in one split.
Result: Eval AUC 0.6855 (-0.0002). Discard; minute pattern is weak or redundant and slows preparation.

## Experiment 23 — origin by carrier category (exploration)
Hypothesis: hub-specific airline operations give an airport-carrier interaction beyond separate effects. About 1551 observed levels have median 43 train rows, so the feature has support. Values and levels are built solely from train and applied rowwise.
Result: Eval AUC 0.6798 (-0.0059), eval 40.4s. Discard. The high-cardinality interaction overfits or duplicates useful existing splits.

## Experiment 24 — departure relative to origin median (exploration)
Hypothesis: an airport's usual operating time shapes congestion; relative departure time compresses the origin-time interaction for shallow trees. The median is fitted on training predictors only and looked up per row, matching the program's safe lookup pattern.
Result: Eval AUC 0.6858 (+0.0001), eval 36.9s. Keep. Airport-relative time may help slightly; test a more specific route-relative counterpart.

## Experiment 25 — departure relative to route median (follow-up)
Hypothesis: route-specific scheduled departure tendencies refine the airport-relative feature. The median is fitted only on training predictors; unseen routes map to NaN, handled by XGBoost. This follows the safe lookup example in `program.md`.
Result: Eval AUC 0.6855 (-0.0003), eval 40.1s. Discard. Route-relative schedule is noisier than origin-relative time.

## Experiment 26 — finer numeric histogram (exploration)
Hypothesis: CRSDepTime has 1162 distinct values and is the strongest feature; raising XGBoost histogram `max_bin` from 256 to 512 may retain useful finer departure-time thresholds. Source: XGBoost parameter docs.
Result: Eval AUC 0.6860 (+0.0002). Keep. Finer bins help slightly, plausibly for scheduled departure time.

## Experiment 27 — 1024 histogram bins (follow-up)
Hypothesis: if 512 bins helped resolve departure-time thresholds, 1024 might help more. Only max_bin changes.
Result: Eval AUC 0.6858 (-0.0002). Discard; 512 bins outperform 1024 on this setup.

## Experiment 28 — revisit depth 4 (follow-up)
Hypothesis: explicit calendar and airport-relative features may alter optimal interaction depth. Test depth 4 with the new best feature set and max_bin 512, keeping all else fixed.
Result: Eval AUC 0.6846 (-0.0014). Discard; depth 3 remains preferable with new features.

## Experiment 29 — eight-leaf best-gain trees (exploration)
Hypothesis: the tree's best interaction may occur deeper in one branch; `lossguide` can spend eight leaves where gain is highest instead of growing level by level. Source: [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html).
Result: Eval AUC 0.6854 (-0.0006). Discard; variable-depth best-gain trees did not improve transfer.

## Experiment 30 — destination ablation (ablation)
Hypothesis: destination effects may reflect 2005-specific weather and may be redundant with origin and distance. Removing it also speeds rowwise preparation.
Result: Eval AUC 0.6781 (-0.0079). Discard; destination is a substantial predictor.

## Synthesis after 30 experiments
- Best: 0.6860 at 3fb1f20. Ordered day-of-month remains the largest gain, followed by smaller improvements from day-of-year, origin-relative departure time and 512 histogram bins.
- Time-part decomposition, high-cardinality category interactions, and route-relative schedule either hurt or added evaluation cost without gain. Destination airport is essential.
- Depth 3 remains better than depth 4, including after feature improvements. Best-first eight-leaf trees did not beat depthwise growth.
- Next direction: consider averaging complementary models and targeted regularization of the stronger calendar feature set, while preserving the best commit as fallback.

## Research refresh after 30 experiments
- [scikit-learn ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) describes soft voting as averaging classifier probabilities so different errors can offset each other. A depth-4 model was weaker alone but may add complementary interactions.
- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) still suggests targeted complexity controls; if averaging fails I will revisit these on the improved feature set.

## Experiment 31 — depth 3/4 soft-voting ensemble (exploration)
Hypothesis: combining best depth 3 with a depth 4 model in a 2:1 probability average improves ranking by canceling different errors. Both models train solely on `train.csv` with the same rowwise features.
Result: Eval AUC 0.6862 (+0.0002), training 2.7s. Keep. Complementary depth-4 predictions slightly improve ranking despite that model's weaker standalone AUC.

## Experiment 32 — equal blend weights (follow-up)
Hypothesis: if depth-4 predictions are complementary, giving them equal influence may improve further. Only voting weights change from 2:1 to 1:1.
Result: Eval AUC 0.6861 (-0.0001). Discard. Depth-4 predictions help most as the smaller contributor.

## Experiment 33 — slower depth-4 ensemble member (follow-up)
Hypothesis: depth-4 model's individual weakness reflects overfitting; 500 rounds at eta 0.03 gives smoother updates with similar total boosting exposure. Keep depth-3 anchor and 2:1 weights unchanged.
Result: Eval AUC 0.6862, equal but slower and more complex. Discard under the keep rule.

## Experiment 34 — gamma split penalty (exploration)
Hypothesis: weak 2005-specific splits remain in both ensemble members. XGBoost `gamma=1` requires extra loss reduction before splitting, potentially improving 2006 transfer. Source: XGBoost tuning and parameter docs.
Result: Eval AUC 0.6864 (+0.0002). Keep. Mild split penalty helps, consistent with residual overfitting.

## Experiment 35 — stronger gamma penalty (follow-up)
Hypothesis: gamma 1 helped by excluding weak splits, and gamma 2 might remove more year-specific splits. All else fixed.
Result: Eval AUC 0.6862 (-0.0002). Discard; gamma 1 is better than 2.

## Experiment 36 — stronger L2 leaf regularization (exploration)
Hypothesis: shrinking leaf scores can reduce year-specific effects without changing splits as directly as gamma. Raise XGBoost `reg_lambda` from 1 to 10 on both models; source: parameter docs.
Result: Eval AUC 0.6852 (-0.0012). Discard; L2=10 shrinks useful signal too much.

## Research on holiday calendar features
- [BTS holiday delay tables](https://www.transtats.bts.gov/holidaydelay.asp) track departure delays during holiday travel seasons, which vary around dates and weekdays. Fixed holidays can be represented from the available month/day fields without a year or other data source.

## Experiment 37 — distance to fixed holidays (exploration)
Hypothesis: delays around New Year, July 4 and Christmas share a travel-demand effect. Distance in days to the nearest fixed holiday pools these short windows for shallow trees. The wrap-around to next New Year is included.
Result: Eval AUC 0.6863 (-0.0001), rowwise evaluation slower. Discard; this holiday pooling adds little beyond existing calendar features.

## Experiment 38 — origin-median ablation (ablation)
Hypothesis: the origin-relative time feature improved a single model only by 0.0001 and might be redundant in the ensemble. Removing it can reduce rowwise preparation cost substantially if AUC holds.
Result: Eval AUC 0.6856 (-0.0008), faster but keep rule requires no decline. Discard; the origin-median feature remains useful in the ensemble.

## Experiment 39 — distance ablation (ablation)
Hypothesis: distance is the least-used feature in both ensemble members (gain 36/17), and origin/destination may already encode route length. Removing it may reduce noise without harming AUC.
Result: Eval AUC 0.6854 (-0.0010). Discard; even low-gain distance adds useful information.

## Experiment 40 — L1 leaf penalty (exploration)
Hypothesis: L1=1 may suppress weak leaf outputs that transfer poorly, while keeping strong effects. Gamma remains at its kept value of 1. Source: XGBoost parameter docs.
Result: Eval AUC 0.6860 (-0.0004). Discard; L1=1 is too restrictive.

## Synthesis after 40 experiments
- Best: 0.6864 at 55b9ff7, a 2:1 soft vote of depth-3 and depth-4 XGBoost models with gamma 1.
- Probability averaging contributed a small gain; equal weights and a slower depth-4 member did not. Gamma 1 helped; gamma 2, L1 1 and L2 10 hurt.
- Ablations show origin-relative schedule and distance still help in the ensemble, despite modest individual gain.
- Next direction: research a different regularization mechanism and explore stable weekday/season interactions with low-cardinality features.

## Research refresh after 40 experiments
- [scikit-learn time-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) demonstrates different hourly patterns on working days and weekends and explicit time-by-day-type interactions.
- [XGBoost parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe column sampling and DART as alternative regularizers. They offer next directions if feature interactions fail.

## Experiment 41 — weekend-specific scheduled time (exploration)
Hypothesis: the departure-time effect differs on weekends because schedules and demand change. A weekday code of `c-6` occurs on Saturday 2005-01-01, so `c-6`/`c-7` are weekend. The new feature exposes weekend time thresholds in one split.
Result: Eval AUC 0.6863 (-0.0001), slower. Discard; weekend/time interaction is already captured well enough by the ensemble.

## Experiment 42 — column subsampling (exploration)
Hypothesis: sampling 80% of features per tree reduces correlated errors and 2005-specific reliance on a few predictors. Source: XGBoost parameter docs on `colsample_bytree`.
Result: Eval AUC 0.6860 (-0.0004). Discard; feature subsampling loses useful information in a small feature set.

## Experiment 43 — DART depth-4 member (exploration)
Hypothesis: dropout during deeper-tree training reduces overfit while preserving different interactions for the 2:1 ensemble. Use a mild 0.05 tree dropout rate with 0.5 skip probability, based on [XGBoost's DART tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/dart.html). The depth-3 anchor is unchanged.
Result: Eval AUC 0.6861 (-0.0003), training 37s vs 3s. Discard. DART does not justify its cost here.

## Plateau pause after experiments 41–43
Three consecutive small declines from 0.6864. Pause for new evidence before the next change; the weekend-time interaction, feature subsampling and DART each underperformed. I will look for a calendar interaction with stronger domain support.

## Plateau research refresh
- [Berkeley flight-delay study](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) identifies month and weekday as operational timing signals; a combined, low-cardinality feature may let shallow trees express their interaction efficiently.
- [scikit-learn categorical boosting guide](https://scikit-learn.org/stable/modules/ensemble.html) explains that native categorical splits can partition a feature's levels into groups without one-hot depth overhead.

## Experiment 44 — month by weekday category (exploration)
Hypothesis: business and leisure travel patterns for weekdays vary seasonally. With only 84 possible combinations, a combined category may generalize better than prior high-cardinality interactions.
Result: Eval AUC 0.6825 (-0.0039), eval 41.6s. Discard. Even 84-level explicit calendar combinations overfit or distract the shallow trees.

## Experiment 45 — third, faster boosting schedule (exploration)
Hypothesis: a depth-3 model with 150 rounds at eta 0.1 follows a different update path, adding complementary ranking signal. Give it one seventh of the vote and retain the original depth3/depth4 ratio among existing members.
Result: Eval AUC 0.6863 (-0.0001), greater complexity. Discard; alternate boosting schedule adds little diversity.

## Experiment 46 — modest minimum child weight (follow-up)
Hypothesis: mild leaf-size regularization at weight 3 can complement gamma 1 without the underfit seen at weight 10. Apply equally to both ensemble members.
Result: Eval AUC 0.6862 (-0.0002). Discard; even mild child-weight regularization fails to improve the ensemble.

## Experiment 47 — stronger gamma only for depth 4 (follow-up)
Hypothesis: the deeper member overfits more than the depth-3 anchor. A gamma 2 split penalty only in depth 4 may improve its complementary predictions while preserving the anchor.
Result: Eval AUC 0.6862 (-0.0002). Discard; stronger regularization of only depth 4 does not help.

## Experiment 48 — remove redundant categorical membership scan (ablation/simplification)
Hypothesis: `pd.Categorical(..., categories=...)` already converts unseen levels to missing, so the preceding `.isin()`/`.where()` is redundant. Removing it should keep identical features while reducing rowwise scoring cost.
Result: Eval AUC 0.6864, equal to previous best; eval 28.9s vs 37.2s. Keep as a simpler, faster equivalent.

## Experiment 49 — gamma 0.5 (follow-up)
Hypothesis: the best split penalty may lie between default 0 (0.6862 with the ensemble) and gamma 1 (0.6864). Hold the streamlined feature preparation fixed.
Result: Eval AUC 0.6864, equal with similar speed and complexity. Discard under the keep rule; gamma 1 remains.

## Experiment 50 — 250-tree ensemble (ablation/simplification)
Hypothesis: gamma 1 and averaging may let the two models reach the same ranking with fewer boosting rounds. If AUC ties, fewer trees make the artifact smaller and training faster.
Result: Eval AUC 0.6861 (-0.0003); discard despite smaller artifact. The full 300 rounds retain signal.

## Synthesis after 50 experiments
- Best: 0.6864 at 08500bb, same AUC as the previous best with rowwise eval reduced from about 37s to 29s through categorical-preparation simplification.
- Recent interaction and regularization changes did not improve AUC: weekend time, month-weekday, column sampling, DART, a third model, child weight, and altered gamma settings all missed the best.
- The ensemble still benefits from 300 rounds; 250 lost 0.0003. Next test whether small calendar inputs remain necessary in the final ensemble, then pursue a small number of principled refinements while time permits.

## Research refresh after 50 experiments
- [XGBoost tuning guide](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) notes that preprocessing often matters more than exhaustive tuning. Recent regularization changes have plateaued, so simplify and verify the final calendar representation.
- [scikit-learn time features](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html) shows tree boosting can model heterogeneous raw time features with little preprocessing; our own annual sine/cosine test also underperformed.

## Experiment 51 — remove day of year from ensemble (ablation)
Hypothesis: day of year added only 0.0001 to a single model and may be redundant with month plus ordered day of month in the current ensemble. Removing it could cut feature prep cost if AUC ties.
Result: Eval AUC 0.6863 (-0.0001), eval 24.8s; discard per strict keep rule. Day of year contributes a small ranking gain.

## Experiment 52 — 350 trees (follow-up)
Hypothesis: 250 rounds underfit the final ensemble, and a modest increase beyond 300 may capture additional low-order signal before the overfit seen at 600 rounds in an earlier single model.
Result: Eval AUC 0.6864, equal but slightly slower and larger. Discard; retain 300 trees.

## Experiment 53 — 384 histogram bins (follow-up)
Hypothesis: the optimum resolution may be between 256 and 512 for the strongly predictive departure time. Try 384 while keeping the ensemble fixed.
Result: Eval AUC 0.6862 (-0.0002). Discard; 512 bins remains better.

## Experiment 54 — depth-5 secondary model (exploration)
Hypothesis: depth 5 captures a distinct set of higher-order interactions that may complement depth 3 better than depth 4 at one-third ensemble weight. Gamma 1 and all other settings stay fixed.
Result: Eval AUC 0.6859 (-0.0005). Discard; extra interaction depth adds noise.

## Plateau pause after experiments 51–54
Recent AUC changes are all below 0.001 and none improved the best. Pause for new evidence before trying another parameter or feature; do not merely walk neighboring values.

## Plateau research refresh
- [XGBoost feature map](https://xgboost.readthedocs.io/en/stable/contrib/featuremap.html) and [scikit-learn ensemble guide](https://scikit-learn.org/stable/modules/ensemble.html) describe interaction constraints as a way to encode prior knowledge about plausible feature combinations.
- [Transportation Department delay directive](https://www.transportation.gov/sites/dot.gov/files/2020-02/Technical%20Directive%20No%20%2031%20On-Time%202019.pdf) highlights schedule and late-arriving aircraft as operational delay mechanisms. Aircraft history is absent here; airport and scheduled-time combinations are the closest available proxies.

## Experiment 55 — constrain tree interactions (exploration)
Hypothesis: restricting trees to schedule/airport/carrier, schedule/calendar, or schedule/route groups suppresses accidental 2005-specific mixed interactions while retaining plausible operations patterns.
Result: Eval AUC 0.6862 (-0.0002). Discard; these constraints remove useful cross-group interactions.

## Experiment 56 — dictionary origin lookup (ablation/simplification)
Hypothesis: storing 283 origin medians in a plain dictionary can reduce artifact overhead and potentially speed rowwise mapping. The mapped numeric values should remain identical.
Result: Eval AUC 0.6864, equal but eval 29.7s vs 28.9s. Discard; no simplicity or speed gain.

## Experiment 57 — gamma 1.5 (follow-up)
Hypothesis: split regularization optimum might be just above gamma 1; gamma 2 reduced AUC by 0.0002. Test the midpoint with the final streamlined preparation.
Result: Eval AUC 0.6862 (-0.0002). Discard; gamma 1 remains best.

## Experiment 58 — 768 histogram bins (follow-up)
Hypothesis: 512 bins beat 1024, but an intermediate higher resolution may improve departure-time thresholds slightly. This is the final bin-width bracket within the clock.
Result: Eval AUC 0.6864, equal but slightly slower than 512 bins. Discard.

## Final summary
- Best Eval AUC: **0.6864**, commit **08500bb** on branch `oct6`.
- Main gains: depth 3 at 300 rounds and eta 0.05; numeric day-of-month; day-of-year; origin-relative departure time; 512 histogram bins; a 2:1 depth-3/depth-4 soft-voting ensemble; gamma 1. Simplifying categorical preparation preserved AUC and reduced evaluation time to about 29s.
- Changes that did not help: forcing one-hot category splits, explicit high-cardinality interactions, stronger regularization, DART, additional ensemble member, cyclic annual encoding, several calendar interactions, and the tested feature ablations.
- Next: check this commit on the human-only holdout. If the gains transfer, test other train-only, leakage-safe schedule summaries or additional temporally stable flight features in a future run.
