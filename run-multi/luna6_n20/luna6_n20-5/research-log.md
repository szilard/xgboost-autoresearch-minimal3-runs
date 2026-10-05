# Research log

## Setup
- Run tag: `oct5` (2026-10-05)
- Branch created from the current `main` HEAD.
- Baseline run: pending user confirmation to start the experiment clock.

## Baseline — `b15ec66`
- Result: Eval AUC 0.6743 (`keep`).
- Configuration: starter `XGBClassifier`, 100 trees, depth 6, learning rate 0.1; raw scheduled departure time and distance plus categorical calendar, carrier, origin and destination.
- Clock started 2026-10-05; baseline completed in about 45 seconds including setup overhead.
- Next step: research XGBoost tuning and airline-delay feature construction before the first modified run.

## Experiment 1 proposal — exploration: scheduled-time features
- Hypothesis: `CRSDepTime` is stored as HHMM (e.g. 0959 then 1000), so numeric splits see uneven gaps and raw HHMM does not express the day’s periodic boundary. Add the scheduled hour as a 24-level category plus minute-of-day sine/cosine, retaining the raw field. These expose broad operational time blocks, precise within-day timing, and midnight wraparound.
- Evidence: scikit-learn's official cyclical feature example explains that sine/cosine encodings represent periodic values without a jump between the last and first values ([documentation](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)). A flight-delay feature-engineering case study includes scheduled departure hour/time blocks among its temporal features ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)). XGBoost's tuning notes emphasize balancing tree complexity and regularization and note that preprocessing can matter ([parameter tuning](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)); its categorical guide supports category-typed columns with `enable_categorical=True` ([categorical data](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html)).
- Data check on `train.csv`: scheduled times range from 0005 to 2359, with no nulls and no minute component outside 00–59.
- Decision: test only scheduled-time representation in this run; do not tune model hyperparameters at the same time. Keep only if Eval AUC exceeds the current kept result (0.6743), unless equal AUC comes with a simplification/faster code (not expected here).
- Outcome: Eval AUC 0.6745, `keep` at `fe953cd` (+0.0002 vs baseline; harness status `ok`, 40.1s total). The gain is small but clears the 4-decimal keep rule.

## Experiment 2 proposal — ablation: remove the cyclic pair
- Hypothesis: the new scheduled-hour category may explain the small gain by itself; removing `DepTimeSin`/`DepTimeCos` tests whether the cyclical pair adds value and may simplify the feature set at no AUC cost.
- Classification: ablation of the time-feature result at `fe953cd`.
- Outcome: Eval AUC 0.6747, `keep` at `359b335` (+0.0002 vs `fe953cd`, +0.0004 vs baseline; `ok`, 35.9s total). Removing the cyclic pair improved the score, so keep the coarser scheduled-hour category and omit sine/cosine.

## Experiment 3 proposal — ablation: remove raw HHMM
- Hypothesis: after adding a 24-level scheduled-hour category, raw HHMM may add little beyond within-hour noise or the uneven HHMM numeric scale. Remove only raw `CRSDepTime`, keeping distance, all original categories, and `DepHour`.
- Classification: ablation of the time-feature result at `359b335`; a tie would favor the simpler feature set.
- Outcome: Eval AUC 0.6741, `discard` at `8ef11e3` (-0.0006 vs `359b335`; `ok`, 34.6s total). The raw scheduled-time value still adds useful signal alongside hour; reverting this ablation.

## Experiment 4 proposal — exploration: ordered route category
- Hypothesis: an `Origin`-`Dest` category can expose route-specific effects and origin/destination interactions more directly than two separate airport features. Build the lookup from `train.csv` only, then map each row independently in `prepare`; unseen pairs become missing categories. This is a categorical interaction, not a group statistic.
- Evidence: a flight-delay study notes that origin-destination pairs can have considerable delay effects, while also cautioning that airport-link effects need enough data ([AIAA paper](https://junchen.sdsu.edu/proceedings/scitech_gnc19_Chen.pdf)). XGBoost supports native categorical partition splits, and `max_cat_threshold` is documented as a way to limit category candidates to help prevent overfitting ([categorical guide](https://xgboost.readthedocs.io/en/latest/tutorials/categorical.html), [Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)).
- Train-only diagnostic: 4,290 ordered routes among 200,000 rows; median route count 32 (90th percentile 105), so many route categories are sparse. Test the raw route category once, keeping other settings fixed; if it does not improve AUC, discard and pursue lower-cardinality ideas.
- Classification: exploration, a new origin-destination interaction direction.
- Outcome: Eval AUC 0.6660, `discard` at `c58a53c` (-0.0087 vs best `359b335`; `ok`, 49.3s total). The sparse, high-cardinality route category materially hurt out-of-year performance; evaluation also emitted repeated pandas warnings for routes absent from the train-fitted category list. Do not keep this feature.

## Experiment 5 proposal — follow-up: reduce tree depth
- Hypothesis: depth 6 may learn 2005-specific interactions that do not transfer to 2006. Lowering only `max_depth` to 4 adds regularization and may improve year-to-year generalization.
- Classification: follow-up to the current best `359b335` (scheduled-hour feature); model-capacity adjustment after sparse route categories failed to transfer.
- Evidence: XGBoost documents that increasing `max_depth` increases model complexity and overfitting risk ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)). Keep every feature unchanged to isolate depth.
- Outcome: Eval AUC 0.6789, `keep` at `f117ce7` (+0.0042 vs best `359b335`; `ok`, 35.4s total). Shallower trees improved out-of-year AUC substantially.

## Experiment 6 proposal — follow-up: raise `min_child_weight`
- Hypothesis: the depth-4 model transfers better, and requiring more Hessian mass per child may further suppress small, train-year-specific leaves. Change only `min_child_weight` from its default 1 to 5.
- Classification: follow-up to the depth-4 improvement at `f117ce7`.
- Evidence: XGBoost documents that larger `min_child_weight` prevents further splitting unless a child has enough summed Hessian, making the model more conservative ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Outcome: Eval AUC 0.6789, `discard` at `e1d8c8d` (equal to `f117ce7` at 4 decimals; `ok`, 35.5s total). This added setting neither improved the metric nor simplified/faster the model.

## Experiment 7 proposal — follow-up: row subsampling
- Hypothesis: the depth-4 model may benefit from fitting each tree on a random 80% of 2005 rows, reducing dependence on particular sampled flights and improving transfer to 2006. Change only `subsample` from 1.0 to 0.8; keep `random_state=42`.
- Classification: follow-up to the depth-4 improvement at `f117ce7`, testing row randomness separately from tree-depth regularization.
- Evidence: XGBoost's tuning notes describe `subsample` as a way to add randomness for robustness and say uniform sampling is typically set to at least 0.5 ([tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html), [parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Outcome: Eval AUC 0.6781, `discard` at `05bcaac` (-0.0008 vs `f117ce7`; `ok`, 35.5s total). Row subsampling did not help this split; revert it.

## Experiment 8 proposal — follow-up: smaller steps with more trees
- Hypothesis: the current 100 trees at learning rate 0.1 may stop before reaching a useful smoother fit. Try 200 trees at learning rate 0.05, changing these as a linked pair while holding depth 4 and all features fixed.
- Classification: follow-up to `f117ce7`; a learning-rate/round-count tradeoff, distinct from sampling-based regularization.
- Evidence: XGBoost's tuning notes say decreasing `eta` makes boosting more conservative and should be paired with a higher number of rounds ([tuning notes](https://xgboost.readthedocs.io/en/stable/tutorials/param_tuning.html)).
- Outcome: Eval AUC 0.6797, `keep` at `3bf7f9b` (+0.0008 vs `f117ce7`; `ok`, 36.2s total). The lower-step, longer fit improved AUC.

## Experiment 9 proposal — follow-up: constrain categorical split search
- Hypothesis: the destination/origin features have many airport categories, and rare airport identities may fit noise. Limit the number of categories considered per partition split to 32, keeping the depth-4, 200-tree fit and features unchanged.
- Classification: follow-up to the current best `3bf7f9b`; categorical-specific regularization, motivated by route-category overfit and the XGBoost categorical docs.
- Evidence: XGBoost describes `max_cat_threshold` as limiting categories considered for each partition split to help prevent overfitting ([parameter reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Outcome: Eval AUC 0.6797, `discard` at `840aec5` (tied with `3bf7f9b` at 4 decimals; `ok`, 35.9s total). The small runtime difference (36.2s to 35.9s) is too small to credit confidently as a code/model speedup, so the added parameter does not meet the tie rule.

## Experiment 10 proposal — exploration: cyclic month features
- Hypothesis: month is currently nominal, so December and January are not explicitly adjacent. Add month-of-year sine/cosine values with period 12 while retaining the original category, to expose smooth seasonal structure and the year boundary.
- Classification: exploration of calendar seasonality, distinct from scheduled clock-time features.
- Evidence: scikit-learn's time-feature guide uses period-12 sine/cosine encoding for month and explains that the pair avoids a discontinuity at the periodic boundary ([cyclical feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)); the flight feature study includes month as a seasonal temporal feature ([UC Berkeley project](https://www.ischool.berkeley.edu/projects/2025/air-travel-delay-prediction-feature-engineering-and-ml-approaches)).
- First attempt crashed at `91cd246`: `Month` is loaded as text, so `df["Month"] - 1` raised `TypeError`. This is a simple type-conversion bug; log the crash and rerun the same hypothesis after casting the row's month to integer in `prepare`.
- Second attempt crashed at `8ca8510`: month labels are strings such as `c-11`, so `astype(int)` cannot parse them. Train-only inspection confirmed all 12 values follow `c-<month>`; fix by parsing the suffix and rerun.
- Outcome: Eval AUC 0.6797, `discard` at `ddb2b9d` (tied with `3bf7f9b`; `ok`, 40.6s total). After fixing month parsing, cyclic month features did not improve AUC and increased evaluation time.

## Synthesis after 10 experiments
- Best result remains `3bf7f9b`, Eval AUC 0.6797: retain raw `CRSDepTime`, add categorical scheduled hour, use depth 4 and 200 trees at learning rate 0.05.
- The hour category gave a small gain; the cyclic time pair could be removed for a further small gain, while dropping raw HHMM lost signal. Month sine/cosine tied and slowed evaluation.
- Lower tree depth produced the largest improvement (+0.0042). A smaller learning rate with twice as many rounds added another +0.0008. Increasing `min_child_weight`, row subsampling, and categorical thresholding did not improve the score. The high-cardinality ordered route category generalized poorly (-0.0087).
- Current theory: broad schedule-time structure and a less complex tree ensemble transfer better across the 2005-to-2006 split than sparse route memorization. Next, research airport-by-time interactions and other stable, row-local interactions before testing them.

## Experiment 11 proposal — exploration: carrier-by-hour interaction
- Hypothesis: carrier-specific delay risk may change across the day, so a `UniqueCarrier` × scheduled-hour category could capture airline scheduling/operations patterns that separate carrier and hour features miss. This cross has much lower cardinality than full routes.
- Classification: exploration of a lower-cardinality row-local interaction, distinct from the failed origin-destination cross.
- Evidence: a recent analysis of 21.7M U.S. DOT flights reports that evening on-time declines vary substantially by carrier ([FlyerIntel analysis](https://flyerintel.com/research/airline-reliability-by-hour/)); a Transportation Research Board study finds delay impact varies by time of day ([TRB record](https://trid.trb.org/View/777637)). XGBoost describes tree paths as feature interactions and notes they can capture spurious relations, motivating a domain-based cross with controlled cardinality ([interaction constraints tutorial](https://xgboost.readthedocs.io/en/release_2.0.0/tutorials/feature_interaction_constraint.html)).
- Train-only diagnostic: 20 carriers form 401 observed carrier-hour categories among 200,000 rows (median 360 rows/category; 25th percentile 99). Fit category levels on `train`, calculate each row's pair in `prepare`, and let unseen pairs become missing.
- Outcome: Eval AUC 0.6792, `discard` at `cda7ceb` (-0.0005 vs `3bf7f9b`; `ok`, 43.2s total). The carrier-hour cross did not transfer and added about 7 seconds of evaluation time. Keep separate carrier and hour features.

## Experiment 12 proposal — follow-up: coarsen carrier-time interaction
- Hypothesis: the exact carrier-hour cross in `cda7ceb` was too granular. Replace that idea with a carrier × busy-window category, using 18:00–02:00 versus other hours. This should retain airline-specific late-day differences with far more rows per category.
- Classification: follow-up to the failed exact carrier-hour cross, changing only the interaction granularity and feature.
- Evidence: a recent DOT-based analysis reports carrier-dependent evening performance drops ([FlyerIntel](https://flyerintel.com/research/airline-reliability-by-hour/)); a flight-delay study represents busy time as 18:00–02:00 versus other hours ([IET study](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)).
- Train-only diagnostic: this window yields 40 carrier-period categories with 127–22,879 rows each (median 3,243), compared with 401 exact carrier-hour categories (median 360). Fit the 40 levels on `train`; unknown pairs map to missing.
- Outcome: Eval AUC 0.6795, `discard` at `e8d1fb6` (-0.0002 vs `3bf7f9b`; `ok`, 43.6s total). The coarser carrier-busy cross still failed to improve and added about 7 seconds to row-wise evaluation.

## Experiment 13 proposal — follow-up: depth 3
- Hypothesis: depth 4 was a large gain over depth 6, so one more level of regularization may further improve transfer from 2005 to 2006. Change only `max_depth` from 4 to 3, retaining 200 trees at 0.05 and all features.
- Classification: follow-up to the strongest parameter result (`f117ce7`/`3bf7f9b`).
- Evidence: XGBoost's parameter guide notes that larger `max_depth` makes trees more complex and more likely to overfit ([reference](https://xgboost.readthedocs.io/en/stable/parameter.html)).
- Outcome: Eval AUC 0.6794, `discard` at `718a665` (-0.0003 vs `3bf7f9b`; `ok`, 35.8s total). Depth 3 did not beat depth 4.

## Experiment 14 proposal — follow-up: depth 5
- Hypothesis: depth 3 was slightly worse than depth 4; depth 5 tests the other side of this local capacity search. The stronger 0.05 learning rate and 200 rounds may allow one extra level to capture useful interactions without returning to the earlier depth-6 fit.
- Classification: targeted follow-up around the current depth-4 best; only `max_depth` changes.
- Outcome: Eval AUC 0.6778, `discard` at `9f723ca` (-0.0019 vs `3bf7f9b`; `ok`, 36.7s total). The depth-3/4/5 local sweep favors depth 4.
- Plateau pause: experiments 11–13 were consecutive discards with absolute movement below 0.001. Research is required before the next experiment.

## Experiment 15 proposal — exploration: cross-fitted smoothed route target rate
- Hypothesis: raw native `Origin`–`Dest` categories overfit and lost 0.0087 AUC, but routes may still carry signal if represented by a strongly smoothed historical delay rate. Add one numeric route-rate feature, shrinking each route toward the balanced training prior (0.5) with smoothing strength 50.
- Leakage control: fit all route statistics on `train.csv` only. Assign each training row to one of five deterministic folds using a hash of its known-at-prediction feature row (target excluded); encode each training signature from the other four folds so its own fold labels cannot influence it. In `prepare`, look up the OOF value for signatures present in train and the full train-fitted smoothed route rate for unseen signatures. This is row-local and never reads the row's target for encoding.
- Classification: exploration of a different encoding strategy for the failed high-cardinality route feature.
- Evidence: scikit-learn documents target encoding as a category target mean shrunk toward the global mean, with larger smoothing placing more weight on that prior ([TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). Its cross-fitting guide encodes each training fold using the other folds specifically to prevent target leakage and overfitting ([internal cross fitting](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)).
- Outcome: Eval AUC 0.6796, `discard` at `beae9c5` (-0.0001 vs `3bf7f9b`; `ok`, 49.2s total). Cross-fitting prevented in-sample route leakage, but the smoothed route rate did not beat the best model and increased evaluation time by about 12 seconds; the artifact also grew to 5.0 MB.

## Experiment 16 proposal — follow-up: reduce route-rate smoothing
- Hypothesis: the alpha-50 cross-fitted route rate nearly tied the best score (0.6796 vs 0.6797). Try smoothing strength 20 so observed route rates carry more weight; keep the same five-fold OOF construction and all other features/settings fixed.
- Classification: follow-up to `beae9c5`; one target-encoding regularization change.
- Evidence: scikit-learn's TargetEncoder docs state that a larger `smooth` value places more weight on the global target mean, while a smaller value relies more on category-conditioned means ([TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)).
- Outcome: Eval AUC 0.6789, `discard` at `08b4942` (-0.0008 vs `3bf7f9b`; `ok`, 48.8s total). Lower smoothing increased route noise; remove the route target-rate path.

## Experiment 17 proposal — exploration: cross-fitted carrier and airport rates
- Hypothesis: route rates were too sparse, but individual carrier, origin, and destination rates have much more support. Add their smoothed historical delay rates as three numeric features alongside the original categories; these may give the model a stable ordering of carrier/airport risk.
- Leakage control: use the same five deterministic folds based on the full known-at-prediction feature row, excluding each row's fold when fitting its carrier/origin/destination rate. For any row, `prepare` hashes that row and uses the matching fold-specific train lookup. Shrink means toward the balanced training prior (0.5) with smoothing strength 100. No row target is used by the encoding.
- Classification: exploration of target encoding for lower-cardinality source features, distinct from route-rate encoding.
- Evidence: official scikit-learn docs describe target encoding as a category mean shrunk toward the global mean and use fold cross-fitting to prevent target leakage ([TargetEncoder](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html), [cross-fitting guide](https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html)). Flight-delay research identifies airline and airport effects as relevant predictors ([TRB flight-delay study](https://trid.trb.org/View/777637), [airport spatial-temporal study](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)); applying numeric target rates to these existing fields is an inference to test here.
- Outcome: Eval AUC 0.6799, `keep` at `11f9f8f` (+0.0002 vs `3bf7f9b`; `ok`, 49.3s total). Cross-fitted, strongly smoothed carrier/origin/destination rates improved AUC, with a small evaluation-time cost.

## Experiment 18 proposal — ablation: destination rate
- Hypothesis: destination delay tendency may be less direct for predicting whether a flight departs late than carrier and origin tendency. Remove only `DestTargetRate`; retain the destination category and the other two cross-fitted rates.
- Classification: ablation of the promising target-rate result at `11f9f8f`.
- Rationale: distinguish useful departure-side signal from a potentially noisy arrival-side proxy; this is a problem-specific inference, not a claim that destination effects never matter.
- Outcome: Eval AUC 0.6799, `keep` at `6dd6c96` (equal to `11f9f8f` at 4 decimals; `ok`, 47.9s total). Removing `DestTargetRate` simplified the feature set, reduced artifact size from 1.5 MB to 1.4 MB, and preserved AUC.

## Experiment 19 proposal — ablation: carrier rate
- Hypothesis: the carrier category already represents airline identity, so its numeric target rate may be redundant once the origin rate is present. Remove only `CarrierTargetRate`; preserve the original carrier category and origin rate.
- Classification: ablation of the kept simplified target-rate model at `6dd6c96`.
- Outcome: Eval AUC 0.6803, `keep` at `8bfaefd` (+0.0004 vs `6dd6c96`; `ok`, 47.2s total). Removing the carrier target rate improved AUC; keep only the origin rate.

## Experiment 20 proposal — ablation: origin rate
- Hypothesis: the origin target rate may be the useful signal among the target encodings. Remove only `OriginTargetRate` to quantify its contribution against the 0.6803 best at `8bfaefd`.
- Classification: ablation of the promising origin-rate feature; a tie would favor the simpler model.
- Outcome: Eval AUC 0.6797, `discard` at `9c73270` (-0.0006 vs `8bfaefd`; `ok`, 35.8s total). The origin rate contributes to the best score; dropping all rate features returned to the no-rate model's score.

## Research synthesis after experiment 20
- Across experiments 11–20, the strongest stable direction was cross-fitted airport/carrier target rates. Native route categories and route rates did not help; among the carrier/origin/destination rates, ablations retained only the origin rate, with AUC 0.6803. Removing the origin rate fell to 0.6797.
- The best model remains `8bfaefd`: depth 4, 200 trees at learning rate 0.05, scheduled departure hour, raw scheduled time, and the cross-fitted origin delay rate. The gain from the origin rate is modest (+0.0006 over its ablation), so its smoothing deserves a direct follow-up.
- Scikit-learn documents target encoding as a category mean shrunk toward the global mean and says higher smoothing gives the prior more weight; this supports a controlled smoothing sweep while retaining the same leakage-safe folds ([TargetEncoder smoothing](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)). Airport-level effects have also appeared in flight-delay studies, though their findings do not establish this encoding's value here ([airport spatial-temporal delay study](https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/itr2.12071)).

## Experiment 21 proposal — follow-up: origin-rate smoothing 50
- Hypothesis: with the other target rates ablated, lowering origin-rate smoothing from 100 to 50 may let well-supported airports contribute more of their measured delay tendency and improve on 0.6803.
- Keep the five-fold cross-fitting, prior, feature set, and model settings fixed; change only the smoothing strength.
- Classification: one-parameter follow-up on the retained origin rate. The documentation supports the direction of the regularization change; the AUC outcome remains empirical.
- Outcome: Eval AUC 0.6795, `discard` at `2190c6d` (-0.0008 vs `8bfaefd`; `ok`, 46.5s total). Smoothing 50 let noisy airport estimates through; retain the alpha-100 origin rate.

## Experiment 22 proposal — follow-up: origin-rate smoothing 200
- Hypothesis: stronger shrinkage may damp noisy estimates for less frequent airports; test smoothing 200 against the alpha-100 best after alpha 50 underperformed.
- Keep all other features, folds, prior, and model settings fixed. This brackets the best known smoothing setting with a higher regularization point.
- Classification: one-parameter smoothing follow-up, motivated by target-encoding regularization guidance ([TargetEncoder smoothing](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)).
- Outcome: Eval AUC 0.6797, `discard` at `9ee21dd` (-0.0006 vs `8bfaefd`; `ok`, 46.9s total). Stronger smoothing moved back toward the no-rate result and did not improve the alpha-100 setting.

## Final synthesis — October 5 experiment
- Best kept commit: `8bfaefd`, Eval AUC 0.6803. Keep depth 4, 200 trees at learning rate 0.05, raw scheduled departure time plus `DepHour`, and the five-fold cross-fitted origin delay rate smoothed at 100.
- The origin-rate ablation scored 0.6797. Smoothing 50 scored 0.6795; smoothing 200 scored 0.6797. These comparisons support retaining the rate at alpha 100. Route features/rates did not beat the incumbent, and carrier/destination rate ablations left origin as the only useful target rate.
- This is the best observed configuration on the permitted eval set during this hour; the small AUC differences may be within evaluation variability. No holdout was used.
