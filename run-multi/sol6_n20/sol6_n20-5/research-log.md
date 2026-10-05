# oct5 research log

Baseline (8d9c760): Untouched starter model scored Eval AUC 0.6743. Training took 1.7 s and row-by-row evaluation 30.2 s. The training sample is balanced, with 200,000 rows and no missing values. The 2006 evaluation split is a later year, so I will use its AUC for keep/discard decisions and avoid trusting random 2005 validation gains.

Research before first change: [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends balancing tree complexity and stochastic regularization, and emphasizes data preparation. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains the existing native categorical handling and its partitioning controls. [UC Berkeley's flight-delay project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) highlights scheduled flight characteristics and temporal patterns as predictors.

Experiment 1 (exploration): Convert HHMM into minutes since midnight and hour. Hypothesis: numeric HHMM has artificial 41-minute jumps at hour boundaries; minute-of-day gives continuous clock order, while hour exposes daily operating patterns. Keep all other inputs and hyperparameters fixed.

Experiment 1 result (08123e6): Eval AUC 0.6751, a +0.0008 gain. Keep. Training 1.4 s, eval 35.0 s. In the training data, late rate rises sharply from early morning through evening, so scheduled time has a strong signal.

Experiment 2 (exploration): Increase n_estimators from 100 to 300, holding learning rate and all features fixed. Hypothesis: 100 rounds underfits temporal and location interactions. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) highlights boosting rounds and learning rate as linked capacity controls; first isolate the round count.

Experiment 2 result (f4f534e): Eval AUC 0.6674, a -0.0077 drop. Discard. The year-shifted eval strongly penalized additional trees at the same depth and learning rate.

Experiment 3 (follow-up): Try 50 rounds at the original learning rate. Hypothesis: the baseline's 100 trees may also be past the ideal stopping point for this temporal split. This probes the opposite side of the round-count axis before tuning other complexity controls.

Experiment 3 result (47820d7): Eval AUC 0.6766, a +0.0015 gain. Keep. The 50-round model appears to generalize better to 2006.

Experiment 4 (follow-up): Try 25 rounds at the same learning rate and depth. Hypothesis: if the trend from 300 to 100 to 50 reflects overfitting, fewer rounds may help further. This bounds the low end of the useful boosting budget.

Experiment 4 result (c7c14ce): Eval AUC 0.6770, +0.0004. Keep. The gain is smaller than the 100-to-50 change.

Experiment 5 (follow-up): Try 10 rounds. Hypothesis: if even 25 rounds overfits the year-shifted evaluation, a very small ensemble could generalize better. This also tests whether 25 is close to the underfitting boundary.

Experiment 5 result (0607825): Eval AUC 0.6741, -0.0029. Discard. The useful range for depth-6 trees appears above 10 and at or below 50 rounds.

Experiment 6 (exploration): Reduce max_depth from 6 to 4 with 25 rounds held fixed. Hypothesis: shallower trees reduce spurious 2005-specific location and date interactions, improving transfer to 2006. Motivated by [XGBoost's overfitting guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html).

Experiment 6 result (20af723): Eval AUC 0.6747, -0.0023. Discard. Depth 4 loses interactions that apparently matter even with a small ensemble.

Experiment 7 (exploration): Add a categorical Origin-Dest route feature, keeping 25 rounds and depth 6. Hypothesis: some directional routes have repeatable operational risk that separate Origin and Dest splits fail to capture within 25 trees. Train has 4,290 routes, median 32 samples per route; model-level category levels are fixed from train, so single-row scoring is stable. [Stanford flight-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) uses route-relevant airport and scheduled-flight predictors; [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) describes native partitioned splits.

Experiment 7 result (76a2e83): Eval AUC 0.6710, -0.0060, and eval 47.5 s versus about 35 s. Discard. The route feature is likely too granular/noisy for a 2005-to-2006 transfer.

Experiment 8 (exploration): Raise min_child_weight from 1 to 10, leaving depth 6 and 25 rounds. Hypothesis: the model needs deep interactions, but should reject thin leaves built on sparse carrier/airport combinations. [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) explains that larger min_child_weight makes splitting more conservative.

Experiment 8 result (1b8984e): Eval AUC 0.6775, +0.0005. Keep. Modest evidence that suppressing thin leaves helps.

Experiment 9 (follow-up): Raise min_child_weight to 30, with other settings fixed. Hypothesis: a stronger leaf-size constraint could further limit 2005-specific airport and date splits. Unlike reducing max_depth, it keeps deep paths available where enough data support them.

Experiment 9 result (fe0a7cc): Eval AUC 0.6773, -0.0002. Discard. The 10 setting is better so far.

Experiment 10 (ablation): Remove DepMinute. Hypothesis: it is redundant with monotonic CRSDepTime; gain importance on the best saved model showed zero use of DepMinute. Removing it should preserve AUC and make row-by-row preparation simpler/faster.

Experiment 10 result (26cba57): Eval AUC 0.6775, equal to the previous best; eval time fell from 35.2 to 32.4 s. Keep as a simpler, faster model.

## Synthesis after 10 experiments

The best is 0.6775 at 26cba57. Smaller ensembles generalized better across 2005-to-2006: 300, 100, 50, 25, then 10 rounds revealed a useful range around 25-50. Raising min_child_weight from 1 to 10 helped modestly, while depth 4 lost signal; depth 6 with larger minimum leaves is a better compromise. Departure hour helped, but minute-of-day was redundant with raw HHMM. A high-cardinality route feature hurt substantially and slowed row scoring. Next, focus on generalizable calendar/operational patterns and consider feature and model regularization without making routes more granular.

Research refresh: [airline disruption management research](https://www.sciencedirect.com/science/article/pii/S2666827021000517) uses periodic representations of time and calendar dates; [flight-delay prediction research](https://pmc.ncbi.nlm.nih.gov/articles/PMC12685205/) discusses day-of-year and departure-hour features; [XGBoost documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) describes leaf-growth and split controls. These sources motivate testing a smooth calendar coordinate next.

Experiment 11 (exploration): Add numeric day-of-year from Month and DayofMonth, using fixed non-leap month offsets. Hypothesis: a continuous calendar coordinate lets the limited 25-tree ensemble capture broader seasonal weather/travel trends more efficiently than separate categorical month and day splits. Both 2005 and 2006 are non-leap years.

Experiment 11 result (239f9ef): Eval AUC 0.6779, +0.0004. Keep. The feature appears in model splits; eval time increased to 36.6 s.

Experiment 12 (follow-up): Add sine and cosine of day-of-year using fixed 365-day lookup tables. Hypothesis: December and January are adjacent in the annual cycle, and periodic coordinates may capture smooth seasonal risk with fewer tree splits. Motivated by [airline disruption feature research](https://www.sciencedirect.com/science/article/pii/S2666827021000517), which uses periodic calendar transforms.

Experiment 12 result (687c4c8): Eval AUC 0.6782, +0.0003. Keep. Both sine and cosine were used in splits. Eval time increased to 41.2 s.

Experiment 13 (exploration): Use 50 trees with learning_rate 0.05 instead of 25 trees at 0.1. Hypothesis: about the same aggregate shrinkage delivered in smaller steps may fit stable patterns more smoothly without the overfitting seen at 300 trees and eta 0.1. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explicitly links lower eta with more boosting rounds.

Experiment 13 result (c6d32d6): Eval AUC 0.6794, +0.0012. Keep. Lower eta with proportional rounds is promising.

Experiment 14 (follow-up): Use 100 trees with learning_rate 0.025, preserving roughly the same aggregate step size. Hypothesis: another halving of each update may further stabilize fitted patterns under year shift.

Experiment 14 result (39b2cb3): Eval AUC 0.6796, +0.0002. Keep. Gain is small, suggesting diminishing returns.

Experiment 15 (follow-up): Use 200 trees at learning_rate 0.0125, again preserving the same aggregate step size. Hypothesis: the lower-rate trajectory may continue to smooth splits, but likely with still smaller gains. This is the last planned step-size refinement before switching axes.

Experiment 15 result (a5632a0): Eval AUC 0.6796, equal to the previous best, but training took 2.1 s instead of 1.5 s. Discard under the keep rule.

Experiment 16 (exploration): Set subsample to 0.8 at the kept 100-tree, eta 0.025 setting. Hypothesis: randomizing training rows per tree can suppress date-specific noise and improve out-of-year transfer. [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) recommends subsampling as an overfitting control.

Experiment 16 result (f5990d1): Eval AUC 0.6797, +0.0001. Keep. A small gain; whether sampling helps more remains uncertain.

Experiment 17 (follow-up): Lower subsample to 0.6. Hypothesis: stronger row randomization may further reduce 2005-specific noise, with still 120,000 rows available per tree.

Experiment 17 result (0e27020): Eval AUC 0.6793, -0.0004. Discard. Some subsampling helped, but 0.6 was too much.

Experiment 18 (exploration): Set reg_lambda to 10 instead of its default 1. Hypothesis: stronger L2 regularization on leaf values will temper large, potentially year-specific effects while retaining useful depth-6 interactions. [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) describes lambda as an L2 weight regularizer.

Experiment 18 result (576cc30): Eval AUC 0.6793, -0.0004. Discard.

Experiment 19 (exploration): Set max_cat_threshold=16 for native categorical partitions. Hypothesis: limiting the number of airport/carrier categories considered at a split may reduce unstable partitions caused by sparse 2005 examples, without removing the airport features. [XGBoost categorical parameter docs](https://xgboost.readthedocs.io/en/stable/parameter.html) describe this control as preventing overfitting.

Experiment 19 result (e565772): Eval AUC 0.6743, -0.0054. Discard. The narrow partition limit removes useful airport grouping capacity.

Experiment 20 (follow-up): Increase max_cat_threshold to 128 from the default (64 in this XGBoost version). Hypothesis: if 16 loses useful category groupings, allowing broader candidate partitions may help distinguish stable airport and carrier effects.

Experiment 20 result (a2789b9): Eval AUC 0.6793, -0.0004. Discard. The default categorical threshold performed best among 16/default/128.

## Synthesis after 20 experiments

Best Eval AUC is 0.6797 at f5990d1. Calendar features (day-of-year, annual sine/cosine) produced small repeatable gains. Using more boosting rounds with a proportionally lower learning rate produced the largest recent gain; 100 rounds at 0.025 was better than 25 at 0.1, while 200 at 0.0125 tied but trained more slowly. Row subsampling at 0.8 added a small gain, while 0.6, strong L2 regularization, and changing categorical partition limits hurt. Native category partitions at their defaults appear useful; a route-level category was too granular. Next I will try cheap row-level signals with plausible transfer across years, then revisit model structure if they stall.

Research refresh: [Stanford airline departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) used day-of-week, day-of-year, and holiday proximity; [XGBoost parameter guidance](https://xgboost.readthedocs.io/en/stable/parameter.html) outlines additional regularization and tree-growth choices. Weekend and holiday schedule signals are candidates derivable from inputs known before departure.

Experiment 21 (exploration): Add a weekend indicator from DayOfWeek. Hypothesis: the existing categorical weekday split may spend trees learning a simple weekday/weekend contrast, and an explicit binary feature can make it easier for a limited ensemble to share that contrast with time-of-day and airport effects. [Flight-delay feature study](https://www.mdpi.com/2079-9292/13/24/4910) includes a weekend feature.

Experiment 21 result (805a9b7): Eval AUC 0.6797, equal to best, but eval slowed to 43.7 s and code gained a feature. Discard under the keep rule.

Experiment 22 (exploration): Add cyclic distance in days to New Year's Day, July 4, Thanksgiving dates (Nov 23/24 across 2005/2006), and Christmas. Hypothesis: a shared proximity feature can express holiday travel disruption with fewer splits than memorizing each date in DayOfYear. [Stanford departure-delay study](https://cs229.stanford.edu/proj2008/Naul-AirlineDepartureDelayPrediction.pdf) includes holiday proximity among its predictive features.

Experiment 22 result (5db62db): Eval AUC 0.6801, +0.0004. Keep. The holiday feature added about 2.5 s to row evaluation.

Experiment 23 (follow-up): Add Memorial Day (May 29/30) and Labor Day (Sep 4/5) to the holiday calendar. Hypothesis: these long weekends change travel mix and airport operations, and a broader proximity signal may generalize across 2005 and 2006. Both years' observed dates are included because year is absent from model inputs.

Experiment 23 result (a001aae): Eval AUC 0.6795, -0.0006. Discard. A broad holiday-distance feature diluted the signal from the four major holiday periods.

Experiment 24 (exploration): Set histogram max_bin=64 instead of the default 256, holding the best features and other model settings fixed. Hypothesis: coarser scheduled-time and calendar thresholds reduce sensitivity to exact 2005 patterns while preserving the main daypart and seasonal trends. [XGBoost tree-method documentation](https://xgboost.readthedocs.io/en/release_3.2.0/treemethod.html) explains the binning tradeoff.

Experiment 24 result (cfebc01): Eval AUC 0.6804, +0.0003. Keep. Coarser numeric thresholds improved generalization modestly.

Experiment 25 (follow-up): Test max_bin=32. Hypothesis: further smoothing could help if 64 bins still fit narrow time windows, but it might erase useful schedule detail. This locates the coarse side of the histogram range.

Experiment 25 result (163d022): Eval AUC 0.6805, +0.0001. Keep. Improvement is very small, but coarsening has continued to help.

Experiment 26 (follow-up): Test max_bin=16. Hypothesis: if smoother numeric thresholds remain beneficial, another halving may improve transfer; this is likely near the point where too much timing detail is lost.

Experiment 26 result (7ddafb8): Eval AUC 0.6795, -0.0010. Discard. 32 bins is the best observed point; 16 erased useful numeric detail.

Experiment 27 (exploration): Set max_cat_to_onehot=8 so the seven-valued DayOfWeek uses one-hot splits while Month, DayofMonth, carriers, and airports still use partitions. Hypothesis: specific weekday effects may be more stable across years than learned weekday groups. [XGBoost categorical documentation](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html) explains this threshold and the two split strategies.

Experiment 27 result (fe037f8): Eval AUC 0.6780, -0.0025. Discard. Partitioned weekdays are better than one-hot in this model.

Research before ensemble change: [scikit-learn VotingClassifier documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.VotingClassifier.html) specifies that soft voting averages class probabilities, and [XGBoost's random forest documentation](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) discusses row sampling and boosting ensembles. Averaging separately seeded models is a plausible variance-reduction strategy with this temporal transfer.

Experiment 28 (exploration): Soft-vote three otherwise identical XGBoost models with random states 42, 43, and 44. Hypothesis: different row samples per tree will produce complementary ranking errors; averaging probabilities may generalize better to 2006. Training cost is expected to stay well below one minute.

Experiment 28 result (ede41b2): Eval AUC 0.6809, +0.0004. Keep. Training 3.0 s and evaluation 44.3 s, safely within limits.

Experiment 29 (follow-up): Add seeds 45 and 46 to make a five-model soft vote. Hypothesis: averaging more sampled fits may further reduce variance, though the effect likely diminishes.

Experiment 29 result (172a2b3): Eval AUC 0.6810, +0.0001. Keep. Training 4.4 s; marginal gain.

Experiment 30 (follow-up): Increase the soft vote to nine seeds (42-50). Hypothesis: if seed variation still contributes useful diversity, a larger ensemble may move AUC beyond 0.6810. This tests the diminishing-return point before changing model structure.

Experiment 30 result (65183de): Eval AUC 0.6810, equal to five seeds, with training rising from 4.4 to 7.1 s. Discard under the keep rule.

## Synthesis after 30 experiments

Best Eval AUC is 0.6810 at 172a2b3. The four major holiday periods added a little transferable signal; adding more holidays diluted it. Numeric histogram bins down to 32 helped, but 16 lost detail. Native partitioned weekdays beat one-hot weekday splits. Soft voting over different row-sampling seeds gave another gain, but nine seeds tied the five-seed model. Next, test sources of complementary model diversity rather than simply adding seeds, while preserving the 60-second training and 5-minute evaluation limits.

Research refresh: [XGBoost's boosted-random-forest guidance](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) combines row and feature sampling; [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) describes split-level column sampling and leaf-wise tree growth. Airline-delay research links airport conditions, time of day, season, and carrier, supporting interactions among those preflight fields.

Experiment 31 (exploration): Set colsample_bynode=0.8 for each of the five seed models. Hypothesis: random feature selection at each split will diversify the models beyond row sampling and may improve the soft vote on 2006 flights.

Experiment 31 result (8780dcc): Eval AUC 0.6812, +0.0002. Keep. Training and evaluation remain well within limits.

Experiment 32 (follow-up): Lower colsample_bynode to 0.6. Hypothesis: stronger split-level feature diversity may improve averaging, though it risks withholding the dominant scheduled-departure-time predictor too often.

Experiment 32 result (9bcf600): Eval AUC 0.6816, +0.0004. Keep. Ensembled feature diversity helps more than expected.

Experiment 33 (follow-up): Lower colsample_bynode to 0.4. Hypothesis: even stronger diversity could help the five-model vote, but may cross into underfitting because too few candidate features remain per split. This is the last planned split-sampling test.

Experiment 33 result (8368ac7): Eval AUC 0.6821, +0.0005. Keep. Improvement was large enough to justify one more lower value despite expecting 0.4 to be the last test.

Experiment 34 (follow-up): Try colsample_bynode=0.25, roughly three candidate features per split. Hypothesis: the ensemble may gain further diversity, but the dominant scheduled time and category features may be withheld too often.

Experiment 34 result (0a436f3): Eval AUC 0.6819, -0.0002. Discard. 0.4 is the best feature-sampling ratio tried.

Experiment 35 (exploration): Raise max_depth from 6 to 8 while keeping colsample_bynode=0.4 and the five-model vote. Hypothesis: feature sampling regularizes individual nodes enough that deeper interactions, such as airport-by-season-by-departure-time, may add transferable signal. [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html) link greater depth to more model complexity.

Experiment 35 result (05c8287): Eval AUC 0.6821, equal to best, but training rose to 6.3 s. Discard under the keep rule.

Experiment 36 (follow-up): Try max_depth=5 at the same ensemble settings. Hypothesis: with 100 rounds and feature sampling, depth 5 may capture sufficient interactions while reducing year-specific leaf combinations. This revisits depth under substantially different settings from the early 25-tree depth-4 test.

Experiment 36 result (2f2aa36): Eval AUC 0.6811, -0.0010. Discard. Depth 6 is best among 5, 6, and 8 for this ensemble.

Experiment 37 (exploration): Lower min_child_weight from 10 to 5 in all five models. Hypothesis: row and feature sampling plus averaging may already control variance enough to permit finer, useful airport and time interactions. The earlier single-model test only compared 1, 10, and 30 under different boosting settings.

Experiment 37 result (06c2f5a): Eval AUC 0.6817, -0.0004. Discard. The 10 setting remains better.

Experiment 38 (exploration): Add gamma=1 to require a minimum split improvement. Hypothesis: after feature sampling, some weak deep splits may still reflect 2005-specific noise; a gain threshold could suppress them without limiting all leaves equally. [XGBoost parameter documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) defines gamma as minimum loss reduction for a split.

Experiment 38 result (b5bb09b): Eval AUC 0.6818, -0.0003. Discard. Additional split-gain restriction did not help.

Plateau research: [XGBoost tree-growth documentation](https://xgboost.readthedocs.io/en/stable/parameter.html) offers loss-guided splitting with max_leaves; [flight-delay feature research](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches) emphasizes interactions among departure time, airport, season, and carrier. We cannot add operational or weather fields beyond the provided data, so I will first test whether a different tree-growth policy allocates the available splits more effectively.

Experiment 39 (exploration): Use grow_policy='lossguide' with max_leaves=32, retaining max_depth=6 and all other settings. Hypothesis: focusing splits on nodes with the largest loss reduction may model strong time and airport interactions while avoiding unhelpful depthwise splits.

Experiment 39 result (f71840e): Eval AUC 0.6816, -0.0005. Discard. Default depthwise growth remains better.

Experiment 40 (exploration): Increase n_estimators from 100 to 150 at the same learning_rate=0.025. Hypothesis: strong row/feature sampling and five-model averaging may allow a longer boosting trajectory than the earlier single-model optimum, capturing remaining signal without overfitting.

Experiment 40 result (b2f618a): Eval AUC 0.6831, +0.0010. Keep. Strong evidence the sampled ensemble was underfit at 100 rounds.

## Synthesis after 40 experiments

Best Eval AUC is 0.6831 at b2f618a. Split-level feature sampling improved AUC as its ratio fell from 1.0 to 0.4; 0.25 was too low. Depth 5, depth 8, lower min_child_weight, gamma=1, and loss-guided trees all failed to beat depth-6 default growth with child weight 10. Raising boosting rounds from 100 to 150 then produced the largest recent gain, likely because feature sampling reduced each tree's capacity. Next I will locate the new boosting optimum and consider a complementary model structure if time permits.

Research refresh: [XGBoost tuning guidance](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html) explicitly pairs more rounds with smaller learning rate and recommends row/column sampling to reduce overfitting. [XGBoost boosted-forest documentation](https://xgboost.readthedocs.io/en/stable/tutorials/rf.html) notes that row and feature sampling can support combined forest/boosting models.

Experiment 41 (follow-up): Increase each of the five models from 150 to 225 trees at the same learning rate. Hypothesis: the strong 100-to-150 gain indicates more rounds may still help under colsample_bynode=0.4, but an eventual overfit boundary is expected.

Experiment 41 result (3a28936): Eval AUC 0.6838, +0.0007. Keep. Training 7.8 s; ample time remains under the per-run limit.

Experiment 42 (follow-up): Increase to 350 rounds. Hypothesis: the continued gain indicates the sampled ensemble may still be underfit, but this jump should reveal whether out-of-year AUC has peaked.

Experiment 42 result (af6939d): Eval AUC 0.6838, equal to 225 rounds, but training rose to 11.2 s. Discard. Gains appear to saturate by 225 rounds.

Experiment 43 (follow-up): Test 275 rounds, between the best 225 and tied-but-slower 350. Hypothesis: a moderate additional boosting budget may add a small AUC gain before overfitting or saturation.

Experiment 43 result (8202360): Eval AUC 0.6839, +0.0001. Keep. Training 9.3 s, well within limit.

Experiment 44 (exploration): Raise colsample_bynode from 0.4 to 0.5 at 275 rounds. Hypothesis: longer boosting may use more candidate features per split without losing the ensemble's diversity, improving airport and time interactions.

Experiment 44 result (5487cd9): Eval AUC 0.6832, -0.0007. Discard. More candidate features per split hurt with the longer fit.

Experiment 45 (exploration): Raise row subsample from 0.8 to 0.9 while keeping five models, 275 rounds, and colsample_bynode=0.4. Hypothesis: slightly more training rows per tree may stabilize small airport groups while seed and feature sampling preserve diversity.

Experiment 45 result (b7a18e1): Eval AUC 0.6839, equal to best, with no speed improvement. Discard.

Experiment 46 (ablation): Remove Distance from the model features. Hypothesis: departure-delay risk is mainly driven by scheduled time, calendar, origin, and carrier; distance had low gain importance in earlier fitted models and may compete for split candidates when colsample_bynode=0.4. If AUC is equal and code is simpler/faster, keep.

Experiment 46 result (519f8f1): Eval AUC 0.6838, -0.0001. Discard under the strict keep rule; Distance adds a small amount of transferable signal.

## Final summary

Best Eval AUC: **0.6839** at commit **8202360**. The untouched baseline was 0.6743, a gain of 0.0096 AUC on the 2006 evaluation set. The final model is a soft vote of five XGBoost models with 275 rounds, learning rate 0.025, max depth 6, min child weight 10, 80% row sampling, 40% feature sampling per split, and 32 numeric histogram bins. It uses departure hour, day-of-year, annual sine/cosine, and distance to major holidays in addition to the original fields.

What worked: lighter boosting steps, moderate minimum leaf weight, calendar features, major-holiday proximity, coarser numeric bins, seed averaging, split-level feature sampling, and longer boosting once sampling regularized the trees. What did not: a high-cardinality route feature, too few or too many rounds, depth changes, very restrictive categorical partitions, one-hot weekdays, excessive split regularization, and removing Distance. A broader holiday calendar diluted the useful holiday signal. Future work could test more diverse model components in the soft vote or interactions derived from stable airport and schedule characteristics, while checking any gains on the human-only holdout after this run.
