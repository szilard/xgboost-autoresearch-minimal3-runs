# October 6 experiment

Baseline 8d9c760: unchanged starter, Eval AUC 0.6743, 0.6 s fit and 30.1 s evaluation.

Research before experiment 1: [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends controlling complexity with tree depth and min_child_weight and reducing the step size while increasing boosting rounds. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) confirms native categorical splits; the starter already uses this. [A flight-delay study](https://www.mdpi.com/2079-9292/13/24/4910) highlights scheduled departure hour as a useful feature, a candidate for later experiments.

Experiment 1 hypothesis (exploration): 400 shallower trees with a 0.05 learning rate, min_child_weight 5 and row/column sampling 0.8 may capture smoother cross-year patterns than the starter's 100 depth-6 trees, improving Eval AUC. This is one coherent regularized boosting regime. No feature changes.

Experiment 1 result: 9929f55, Eval AUC 0.6808, kept (+0.0065). The slower, regularized regime appears helpful, but this run does not isolate which component mattered.

Research before experiment 2: [XGBoost categorical data guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains partition-based categorical splits, which can group categories by similar leaf values. [UC Berkeley flight delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) discusses airport and route distance effects on delay. Training has 4,290 observed origin-destination pairs. Experiment 2 hypothesis (exploration): a route category will expose pair-specific effects to the shallow trees and improve AUC over separate origin and destination categories.

Experiment 2 result: 86b0c61, Eval AUC 0.6731, discarded. Route categories harmed cross-year generalization and added warnings for unseen 2006 pairs. Reverted to 9929f55.

Research before experiment 3: [Probabilistic Flight Delay Predictions](https://www.mdpi.com/2226-4310/8/6/152) includes day of year among its schedule-derived features, reflecting seasonal and holiday patterns. Experiment 3 hypothesis (exploration): an ordered day-of-year feature may let shallow trees share seasonal information across neighboring dates more effectively than separate categorical month and day-of-month fields. No external date data are used.

Experiment 3 result: 025174b, Eval AUC 0.6833, kept (+0.0025). Ordered seasonal information helped.

Experiment 4 hypothesis (ablation): day-of-month as a separate category may overfit weekday and holiday patterns specific to 2005 now that day-of-year is available. Dropping it may improve the 2006 score or simplify the model without loss. Keep month and ordered day-of-year.

Experiment 4 result: b116968, Eval AUC 0.6841, kept (+0.0008) with one less categorical feature. This supports using ordered calendar position in place of a standalone day-of-month category.

Experiment 5 hypothesis (ablation): the remaining Month category may duplicate seasonality already represented by ordered DayOfYear, while allowing unnecessary abrupt month-specific fits. Removing Month tests whether the ordered feature can carry seasonality on its own. This differs from experiment 4, which removed day-of-month and retained Month.

Experiment 5 result: b5ad9ca, Eval AUC 0.6852, kept (+0.0011). Ordered calendar position alone is stronger on the 2006 eval year than including either original date category.

Research for experiment 6: [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) supports partitioning categorical levels by similar model effects. [Flight delay study](https://www.mdpi.com/2226-4310/8/6/152) lists airport and airline as relevant schedule-based variables. Training has 1,551 carrier-origin pairs versus 4,290 routes, with 78% of rows in carrier-origin groups of 100 or more. Experiment 6 hypothesis (exploration): a carrier-origin category may expose stable operational effects that depth-4 trees do not learn efficiently from two separate categorical splits. Missing 2006 pairs will be mapped to NaN.

Experiment 6 result: d6f5f95, Eval AUC 0.6807, discarded. The interaction harmed generalization and made the artifact and scoring heavier. Reverted to b5ad9ca.

Experiment 7 hypothesis (follow-up): the 0.05 learning rate may need more than 400 rounds to fit broad seasonal and airport effects now that the date categories are removed. Increase trees to 800 with all other parameters fixed. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) links smaller step size with more boosting rounds.

Experiment 7 result: db6ae25, Eval AUC 0.6834, discarded. More rounds reduced the cross-year score by 0.0018, suggesting the 400-round model is already past the useful point or the extra trees fit year-specific detail.

Experiment 8 hypothesis (follow-up): if extra boosting harms AUC, 200 rounds may retain broad effects with less variance and beat 400. Hold all other parameters fixed to measure the round-count effect in the opposite direction.

Experiment 8 result: 01174c5, Eval AUC 0.6854, kept (+0.0002) and faster/smaller than 400 rounds. The observed ordering is 200 > 400 > 800 on the 2006 eval set.

Experiment 9 hypothesis (follow-up): if reduced boosting is still helpful, 100 rounds at the same step size may further reduce variance. This brackets the useful round count below 200 without changing the tree shape or features.

Experiment 9 result: 6adfac0, Eval AUC 0.6849, discarded. The current 200 rounds sit between underfitting at 100 and decreasing cross-year score at 400 or 800.

Experiment 10 hypothesis (exploration): with 200 rounds fixed, depth 3 may suppress fragile high-order interactions while retaining the strong time and airport effects. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) identifies max_depth as a primary complexity control. This tests tree shape rather than another round count.

Experiment 10 result: 9278944, Eval AUC 0.6846, discarded. Depth 4 is better than depth 3 at 200 rounds.

## Synthesis after 10 experiments

Best Eval AUC is 0.6854 at 01174c5, up from baseline 0.6743. The biggest gain came from a shallower, slower, sampled boosting setup. Ordered DayOfYear helped, and removing categorical DayofMonth and Month helped further. High-cardinality Route and CarrierOrigin interactions hurt substantially despite plausible domain effects. The useful boosting range appears near 200 rounds: 100, 400 and 800 all scored lower with the current features. My working theory is that smooth temporal effects and restrained interactions transfer better from 2005 to 2006 than memorized schedule groups. Next I will examine categorical split regularization, time-of-day representation, and sampling.

Research after experiment 10: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) says max_cat_threshold limits categories considered per partition split to prevent overfitting; the current booster config reports the default 64. [Spatio-temporal flight-delay feature study](https://www.mdpi.com/2079-9292/13/24/4910) extracts departure hour and a night-flight indicator, suggesting a later time-of-day test. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) also points to min_child_weight, subsample, and column sampling as variance controls.

Experiment 11 hypothesis (exploration): limiting categorical split candidates from 64 to 32 may reduce overfitting on airports with thin 2005 samples and improve 2006 AUC. Keep all features and other model parameters fixed.

Experiment 11 result: 1f4026b, Eval AUC 0.6848, discarded. Three consecutive discards (experiments 9-11) with less than 0.001 movement from the best score triggered a plateau research pause.

Plateau research: [Spatio-temporal flight-delay study](https://www.mdpi.com/2079-9292/13/24/4910) constructs departure-hour and cyclic time features; [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) explains that categorical partitioning can group levels with similar effects. A [flight-delay temporal analysis](https://recherche.enac.fr/~steve.lawford/airline_papers/tu_etal05.pdf) reports delays building during the day and declining late at night. Training data show the same pattern, with late-night hours nonmonotonic in HHMM.

Experiment 12 hypothesis (exploration): adding a categorical scheduled-departure hour will allow the model to group nonadjacent hours and model the late-night downturn more efficiently than splits on numeric HHMM alone. Keep the original numeric CRSDepTime, which still captures within-hour ordering. This tests a new time representation after the plateau rather than another complexity adjustment.

Experiment 12 result: 14d8e9f, Eval AUC 0.6857, kept (+0.0003). A categorical hour adds a small signal beyond numeric scheduled departure time.

Research before experiment 13: [Probabilistic Flight Delay Predictions](https://www.mdpi.com/2226-4310/8/6/152) uses sine and cosine encodings for cyclic calendar fields; [Predicting Probabilistic Flight Delay for Individual Flights](https://repository.tudelft.nl/file/File_dd877cbc-4b73-480c-ae5f-155c76b8e2e1) considers sine of day of year. Experiment 13 hypothesis (exploration): a cyclic annual representation may let trees treat late December and early January as neighboring seasonal periods while DayOfYear retains local ordering. Add sine and cosine of DayOfYear with a 365-day period.

Experiment 13 result: c1f7ce2, Eval AUC 0.6835, discarded. The extra cyclic features hurt and slowed rowwise preparation; ordered DayOfYear alone remains better.

Experiment 14 hypothesis (exploration): raising min_child_weight from 5 to 20 may prevent thin, year-specific airport or date splits while preserving the large time effect. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe larger min_child_weight as more conservative. This differs from depth-3 experiment 10: keep depth 4 but require more evidence for each leaf.

Experiment 14 result: af8fedd, Eval AUC 0.6852, discarded. More restrictive leaves slightly lowered AUC.

Experiment 15 hypothesis (follow-up): if min_child_weight 20 was too restrictive, allowing smaller leaves (value 1 versus current 5) may recover useful airport-hour patterns. Hold all other parameters fixed to test the other side of the regularization range.

Experiment 15 result: 90d3a13, Eval AUC 0.6855, discarded. The value 5 is between two lower-scoring settings. Experiments 13-15 form a second three-discard plateau.

Plateau research: [UC Berkeley flight-delay feature engineering project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes both airport and schedule-time effects. A [schedule-based feature study](https://thesai.org/Publications/ViewPaper?Code=IJACSA&Issue=8&SerialNo=82&Volume=17) explores schedule intensity and airline-route stability; this dataset's balancing and the experiment rules exclude row-count features. The repo instructions explicitly allow a train-fitted median schedule lookup, which is stable under rowwise evaluation.

Experiment 16 hypothesis (exploration): departure time relative to the origin airport's median scheduled time may expose an airport-specific temporal pattern without adding a high-cardinality interaction category. Fit median scheduled minute on train once and apply it to each row. This is an unsupervised schedule statistic, not a row count or target-derived feature.

Experiment 16 result: cf21516, Eval AUC 0.6856, discarded under the strict keep rule (-0.0001). The feature cost evaluation time and gave no score gain.

Experiment 17 hypothesis (exploration): numeric departure time has over half the fitted feature importance. With colsample_bytree 0.8 it is omitted from some trees; including all predictors in every tree may improve the fit to strong time and calendar effects. Set colsample_bytree to 1.0 and keep row subsampling 0.8. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) document the per-tree column sampling behavior.

Experiment 17 result: 1cba2cc, Eval AUC 0.6845, discarded. Some column sampling is useful, possibly because it lets airport and carrier effects develop without the dominant time split.

Experiment 18 hypothesis (follow-up): stronger column sampling at 0.6 may encourage more trees to model the weaker airport, carrier, and weekday effects and reduce dependence on time. This brackets the current 0.8 with the 1.0 result while holding the tree count and row sampling fixed.

Experiment 18 result: 1f4aaa2, Eval AUC 0.6864, kept (+0.0007). Stronger column sampling helped, consistent with the model relying too much on departure time when it is always available.

Experiment 19 hypothesis (follow-up): reducing the per-tree column fraction again to 0.4 may amplify the useful diversity seen at 0.6. With only eight inputs it also risks hiding important temporal and airport interactions, so this test will indicate whether 0.6 is near the best range.

Experiment 19 result: 531f92d, Eval AUC 0.6867, kept (+0.0003). A smaller column fraction helped again; the fitted model is also slightly smaller.

Experiment 20 hypothesis (follow-up): with 0.2 column sampling each tree sees roughly two of the eight predictors. This strongly favors additive ensembles and might suppress fragile interactions even more. The large change in available predictors per tree makes this distinct from the 0.6-to-0.4 adjustment; it will test whether the performance trend has reached a useful limit.

Experiment 20 result: 37db054, Eval AUC 0.6772, discarded. Two predictors per tree are too few. Reverted to 531f92d.

## Synthesis after 20 experiments

Best Eval AUC is now 0.6867 at 531f92d. Experiments 11-20 found a modest gain from categorical departure hour, while cyclic annual features, origin-median schedule time, and both larger and smaller min_child_weight did not help. Column sampling was the clear positive direction: AUC improved moving from 1.0 to 0.8 to 0.6 to 0.4, then collapsed at 0.2. This suggests a few predictors per tree promote useful diversity, but one or two cannot express enough interactions. Next I will test row sampling independently and revisit date/time features only if a new mechanism is clear.

Research after experiment 20: [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends row and column sampling to make fitting robust to noise. [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) says uniform row subsampling happens every boosting iteration and typically uses a fraction at least 0.5. A [flight-delay feature study](https://www.mdpi.com/2079-9292/13/24/4910) identifies week-of-year and time blocks as possible schedule-derived signals not yet tried here; I will return to these if sampling plateaus.

Experiment 21 hypothesis (exploration): with column sampling held at 0.4, lowering row subsample from 0.8 to 0.6 may reduce sensitivity to noisy 2005 flight patterns and improve the 2006 score. Each tree will still see about 120,000 rows, enough for broad effects.

Experiment 21 result: 0ee67de, Eval AUC 0.6856, discarded. Stronger row sampling hurt despite the helpful stronger column sampling.

Experiment 22 hypothesis (follow-up): row sampling at 0.6 may have made category gradient estimates too noisy; using all rows while retaining colsample_bytree 0.4 may improve those estimates. Set subsample to 1.0 to bracket the current 0.8.

Experiment 22 result: d7d0191, Eval AUC 0.6865, discarded. Row subsample 0.8 is better than both 0.6 and 1.0 on this setup.

Research before experiment 23: [Spatio-temporal flight-delay feature study](https://www.mdpi.com/2079-9292/13/24/4910) includes week of year to capture seasonal trends and holiday periods. [BTS holiday flight-delay statistics](https://transtats.bts.gov/holidaydelay.asp) treats holiday travel periods as distinct calendar windows. Experiment 23 hypothesis (exploration): fixed seven-day seasonal bins as a categorical feature may share information within a week and group separated holiday or weather periods, complementing numeric DayOfYear. The bins use only each row's calendar date.

Experiment 23 result: 8ee51bf, Eval AUC 0.6839, discarded. Coarse seasonal week categories overfit or obscured the beneficial continuous date signal.

Research before experiment 24: [BTS holiday delay statistics](https://transtats.bts.gov/holidaydelay.asp) shows that holiday travel windows move between calendar dates as weekday placements change; Thanksgiving in 2005 and 2006 falls on November 24 and 23. Training rows near the 2005 holiday show a lower delayed share on Thanksgiving and the following two days, then a higher share on the Sunday/Monday return. Experiment 24 hypothesis (exploration): a rowwise offset from fourth-Thursday Thanksgiving within a seven-day window may transfer that pattern to the shifted 2006 holiday better than raw DayOfYear. The feature uses only month, day, and weekday known in advance.

Experiment 24 result: d4e2f30, Eval AUC 0.6861, discarded. Thanksgiving alignment did not beat the existing calendar and weekday features, and slowed rowwise preparation.

Research before experiment 25: [XGBoost categorical guide](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) distinguishes one-hot equality splits from grouped-category partition splits. The current max_cat_to_onehot default is 4, so carrier, weekday, and departure-hour categories use partitioning. Experiment 25 hypothesis (exploration): one-hot splitting for categories with fewer than 32 levels may make carrier/hour effects more stable across years, while origin and destination remain partitioned. Set max_cat_to_onehot to 32; no feature changes.

Experiment 25 result: 22d2c6e, Eval AUC 0.6840, discarded. Partitioning small categories remains preferable.

Plateau research after five discards: [XGBoost parameter guidance](https://xgboost.readthedocs.io/en/stable/parameter.html) distinguishes depthwise versus loss-guided growth and documents depth as an interaction control. [Feature Interactions in XGBoost](https://arxiv.org/abs/2007.05758) studies interaction structure in boosted trees. The successful column sampling reduced available features per tree, so the next test checks whether more depth recovers useful interactions within each sampled feature set.

Experiment 26 hypothesis (exploration): with colsample_bytree now 0.4, depth 5 may capture conditional airport/time effects that depth 4 misses while column sampling continues to regularize the ensemble. This differs from the earlier depth-3 test under colsample_bytree 0.8.

Experiment 26 result: 3207333, Eval AUC 0.6866, discarded by the strict keep rule (-0.0001) and nearly twice the artifact size. More balanced depth does not look promising.

Experiment 27 hypothesis (exploration): loss-guided growth with at most 16 leaves may allocate splits to the strongest conditional effects instead of filling shallow levels evenly. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) say lossguide splits nodes with highest loss change and max_leaves caps complexity. Compare to depth-4 trees with a similar maximum of 16 leaves, while retaining the same features and sampling.

Experiment 27 result: e653274, Eval AUC 0.6869, kept (+0.0002). Loss-guided allocation of a similar leaf budget slightly improved AUC without increasing the artifact much.

Experiment 28 hypothesis (follow-up): limiting the loss-guided model to eight leaves may focus it on the broad effects that transfer between years and further reduce variance. Only max_leaves changes, preserving growth policy and sampling.

Experiment 28 result: 1b68b8b, Eval AUC 0.6860, discarded. Eight leaves underfit useful structure.

Experiment 29 hypothesis (follow-up): 32 leaves per loss-guided tree may better express origin, carrier, and time interactions while keeping the successful split-allocation policy. This tests capacity above the 16-leaf best; 8 leaves was too restrictive.

Experiment 29 result: da79746, Eval AUC 0.6856, discarded. Sixteen leaves outperformed both 8 and 32, suggesting a useful capacity range around the original setting.

Experiment 30 hypothesis (exploration): with the 16-leaf tree shape fixed, 300 rounds at learning_rate 0.03 may give smoother convergence than 200 rounds at 0.05 while keeping roughly similar total update weight. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends increasing rounds when reducing the step size. Earlier round tests were on a different tree policy and column fraction.

Experiment 30 result: e0169f1, Eval AUC 0.6868, discarded by 0.0001. It increased model size and training time without beating the simpler 200-round setup.

## Synthesis after 30 experiments

Best Eval AUC is 0.6869 at e653274, versus baseline 0.6743. Experiments 21-30 did not find gains from changing row subsampling, seasonal-week or Thanksgiving features, or one-hot splits for small categories. Loss-guided growth with 16 leaves gave a small gain; eight leaves underfit and 32 leaves reduced the cross-year score. A slower 300-round schedule matched the best closely but did not exceed it. The strongest general lesson remains: moderate capacity, strong feature sampling, and simple calendar representation transfer best to 2006. Next I will try explicit split and leaf regularization under the successful loss-guided policy.

Research after experiment 30: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) defines gamma as the minimum loss reduction required for another split and reg_lambda as L2 shrinkage on leaf weights. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) lists gamma among complexity controls. These can regularize the 16-leaf model without changing its feature preparation.

Experiment 31 hypothesis (exploration): gamma 5 may stop low-gain branches within otherwise useful loss-guided trees, reducing year-specific fits. Keep the 16-leaf cap and all other parameters fixed.

Experiment 31 result: 837e399, Eval AUC 0.6868, discarded (-0.0001). Extra split pruning gave no gain.

Experiment 32 hypothesis (exploration): stronger L2 leaf-weight regularization (reg_lambda 10 versus default 1) may make category effects less sensitive to 2005 noise while retaining the successful loss-guided topology. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) describe larger reg_lambda as more conservative.

Experiment 32 result: 4a8f3a9, Eval AUC 0.6874, kept (+0.0005). Stronger leaf shrinkage improved the cross-year score without a material runtime penalty.

Experiment 33 hypothesis (follow-up): raising reg_lambda to 30 may further stabilize leaf estimates with the same 16-leaf policy. This tests whether the useful shrinkage trend continues or 10 is already enough.

Experiment 33 result: c7c19c0, Eval AUC 0.6878, kept (+0.0004). Stronger L2 shrinkage helped again, suggesting some leaf effects were still too responsive to training-year noise.

Experiment 34 hypothesis (follow-up): reg_lambda 100 tests whether the benefit from stronger shrinkage extends another order of magnitude or crosses into underfitting. Keep tree structure, features and rounds fixed.

Experiment 34 result: 7d02dfe, Eval AUC 0.6865, discarded. Heavy L2 shrinkage underfit; the useful value lies below 100.

Experiment 35 hypothesis (follow-up): reg_lambda 50 tests the upper part of the interval between the kept value 30 and the underfitting value 100. It may give a little more smoothing while avoiding the loss of signal seen at 100.

Experiment 35 result: f822ba7, Eval AUC 0.6872, discarded. The 30 setting remains best among tested L2 strengths.

Experiment 36 hypothesis (exploration): L1 regularization may zero weak leaf contributions instead of uniformly shrinking all leaves. Add reg_alpha 5 on top of the kept reg_lambda 30. [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) identifies reg_alpha as L1 regularization on leaf weights.

Experiment 36 result: f25d6ee, Eval AUC 0.6874, discarded. L1 shrinkage did not add to the successful L2 setting. Experiments 34-36 are three consecutive discards.

Plateau research: [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) confirms that colsample_bytree chooses predictors once per tree; [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) treats this randomness as an overfitting control. The current loss-guided, L2-regularized model differs from the depthwise model used when testing column fractions 0.4 and 0.6, so the balance may have shifted.

Experiment 37 hypothesis (follow-up): colsample_bytree 0.5 may offer the loss-guided, reg_lambda 30 model more feature interactions than 0.4 without reaching the weaker 0.6 setting from the older tree policy. Test this midpoint with all other settings fixed.

Experiment 37 result: ca09b30, Eval AUC 0.6870, discarded. The original 0.4 column fraction remains better under the loss-guided, L2-regularized setup.

Experiment 38 hypothesis (exploration): the default histogram has 256 bins, fewer than the 365 day-of-year values and 1,162 scheduled departure values in training. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) say more bins improve split optimality at a computation cost. Increasing max_bin to 512 may preserve useful calendar and time thresholds without changing feature semantics. Training is currently far below the one-minute limit.

Experiment 38 result: 0d1de46, Eval AUC 0.6868, discarded. More numeric bins did not help.

## Final summary

Best Eval AUC: 0.6878 at c7c19c0, up 0.0135 from the unchanged baseline 0.6743. The branch ends at c7c19c0. The strongest improvements came from regularized boosting, ordered DayOfYear, removing month/day-of-month categories, categorical departure hour, strong column sampling, loss-guided 16-leaf trees, and L2 leaf shrinkage at 30. High-cardinality route and carrier-origin categories, cyclic and coarse seasonal features, holiday offset, one-hot splitting for small categories, extreme sampling, and excessive tree capacity or shrinkage reduced AUC. The holdout set has not been inspected or scored.

Next experiment if this work is continued in a fresh run: test a different way to express airport and time interactions without high-cardinality pair categories, or investigate whether targeted calendar features based on other movable holidays transfer across years. The current gain is measured only on the provided 2006 eval split; the human holdout check will determine generalization.
