#!/bin/bash
#
# Drive one xgboost-autoresearch-minimal2 run with codex, end to end, in a new
# agents2 container, copy the results to OUT_DIR, then delete the container.
# Mechanical part of the /xgb-multi skill: every run gets the same messages
# under the same rules. Claude does the validity review and run.md afterwards.
#
# Usage: run_one.sh CONTAINER_NAME MODEL EFFORT OUT_DIR
#
# Exit codes:
#   0  run completed (clock stopped, results copied, container deleted)
#   1  run failed after the container was started (record as excluded);
#      whatever results exist were copied, container deleted if the copy worked
#   2  precondition failed (image/volume/container/login/effort level);
#      nothing usable was run - stop the whole group
#
# Writes OUT_DIR/driver.log (timestamped log of everything sent and seen) and
# OUT_DIR/driver-summary.json.

set -uo pipefail

C=$1 MODEL=$2 EFFORT=$3 OUT=$4
R=/home/ubuntu/xgboost-autoresearch-minimal2
HERE=$(cd "$(dirname "$0")" && pwd)
PROMPT="Hi have a look at program.md and let's kick off a new experiment! let's do the setup first."

MAX_GO=5            # "go" turns while the clock is not started
MAX_KEEP_GOING=20   # "keep going" turns while the clock has time left
MAX_FAILED_TURNS=3  # consecutive turns that end without turn.completed
FAILED_TURN_WAIT=300
WRAP_UP_S=900       # time the agent gets after TIME IS UP to run harness.py stop
POLL_S=60
MEM_LIMIT=24g       # container memory cap, no swap: the agent's runs can't starve the host

mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
LOG=$OUT/driver.log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG" >&2; }
dx() { docker exec -w $R $C bash -c "$1"; }
clock() { dx 'python3 harness.py status' 2>&1; }

STATUS=ok REASON="" SID="" NT=0 STOPPED_BY="" STARTED=0
MESSAGES=()
fail() { STATUS=failed; REASON=$*; log "FAILED: $*"; }

log "run $C: model=$MODEL effort=$EFFORT out=$OUT"

# ---------- preconditions (nothing started yet) ----------

docker image inspect agents2 > /dev/null 2>&1 || { log "PRECONDITION: image agents2 missing"; exit 2; }
docker volume inspect codex-auth > /dev/null 2>&1 || { log "PRECONDITION: volume codex-auth missing"; exit 2; }
if docker container inspect "$C" > /dev/null 2>&1; then log "PRECONDITION: container $C already exists"; exit 2; fi

docker run -dit --name "$C" --memory=$MEM_LIMIT --memory-swap=$MEM_LIMIT -v codex-auth:/home/ubuntu/.codex-auth agents2 > /dev/null \
  || { log "PRECONDITION: docker run failed"; exit 2; }
STARTED=1
log "container started"
MEM_MAX=$(docker exec $C cat /sys/fs/cgroup/memory.max 2> /dev/null)
log "memory limit: ${MEM_MAX:-unknown} bytes ($MEM_LIMIT requested, no swap)"

precondition_fail() {
  log "PRECONDITION: $*"
  docker stop "$C" > /dev/null && docker rm "$C" > /dev/null && log "container deleted"
  exit 2
}

# repo state as shipped: report anything unexpected, don't work around it
dx 'ls -la ~/.codex; git status --short --branch; git log --oneline | head -3; ls' >> "$LOG" 2>&1
dx 'test -f data/train.csv && test -f data/eval.csv && test -f data/holdout.csv' \
  || precondition_fail "data/train.csv, eval.csv or holdout.csv missing"
dx 'test ! -e timing && test ! -e artifacts && test ! -e results.tsv' \
  || log "NOTE: leftover timing/, artifacts/ or results.tsv in the repo"
dx 'test "$(ls ~/.codex)" = auth.json' || log "NOTE: ~/.codex holds more than auth.json"

log "setup check: python3 train.py"
dx 'python3 train.py' > "$OUT/setup-train.log" 2>&1
grep -q '^Eval AUC:' "$OUT/setup-train.log" || precondition_fail "setup train.py run failed (see setup-train.log)"
log "setup check: $(grep '^Eval AUC:' "$OUT/setup-train.log")"
dx 'rm -rf artifacts __pycache__'

dx 'codex login status' 2>&1 | tee -a "$LOG" | grep -q 'ChatGPT' || precondition_fail "codex login status is not a ChatGPT login"
CODEX_VERSION=$(dx 'codex --version' 2>&1)

# the effort level must exist by that exact name for MODEL
LEVELS=$(dx "codex debug models 2>/dev/null | python3 -c '
import json, sys
d = json.load(sys.stdin)
for m in (d.get(\"models\", d) if isinstance(d, dict) else d):
    if m.get(\"slug\") == \"$MODEL\":
        print(\" \".join(x.get(\"effort\", \"\") if isinstance(x, dict) else x
                       for x in m.get(\"supported_reasoning_levels\", [])))
'")
[ -n "$LEVELS" ] || precondition_fail "model $MODEL not in codex's model catalog"
log "reasoning levels for $MODEL: $LEVELS"
[[ " $LEVELS " == *" $EFFORT "* ]] || precondition_fail "no effort level named '$EFFORT' for $MODEL (has: $LEVELS)"

# ---------- driving codex ----------

# turn MESSAGE: one codex turn; while it runs, poll the clock and stop codex
# if the agent hasn't stopped the clock WRAP_UP_S after TIME IS UP.
# Returns 0 if the turn completed, 1 otherwise.
turn() {
  NT=$((NT + 1))
  local n=$NT msg=$1 sub timeup_at="" pid rc
  MESSAGES+=("$msg")
  if [ -z "$SID" ]; then sub="exec"; else sub="exec resume $SID"; fi
  log "turn $n send: $msg"
  docker exec -w $R $C bash -c "mkdir -p ~/turns && codex $sub \
    --dangerously-bypass-approvals-and-sandbox --json \
    -m $MODEL -c model_reasoning_effort=\"$EFFORT\" \
    -o ~/turns/$n.txt \"\$1\" < /dev/null > ~/turns/$n.jsonl 2> ~/turns/$n.err" _ "$msg" &
  pid=$!
  while kill -0 $pid 2> /dev/null; do
    sleep $POLL_S
    local st; st=$(clock)
    if [[ "$st" == *"TIME IS UP"* ]]; then
      [ -n "$timeup_at" ] || { timeup_at=$(date +%s); log "clock: TIME IS UP, agent has $((WRAP_UP_S / 60)) min to stop"; }
      if [ $(( $(date +%s) - timeup_at )) -ge $WRAP_UP_S ]; then
        log "agent did not stop the clock within $((WRAP_UP_S / 60)) min: pkill codex, harness.py stop"
        docker exec $C pkill codex
        dx 'python3 harness.py stop' >> "$LOG" 2>&1
        STOPPED_BY=driver
      fi
    fi
  done
  wait $pid; rc=$?

  if [ -z "$SID" ]; then
    SID=$(dx 'head -1 ~/turns/1.jsonl' | python3 -c 'import json,sys; print(json.loads(sys.stdin.readline())["thread_id"])' 2> /dev/null)
    log "session id: ${SID:-<none>}"
  fi
  local nsess; nsess=$(dx 'find ~/.codex/sessions -type f 2>/dev/null | wc -l')
  [ "$nsess" = 1 ] || { fail "expected 1 codex session file, found $nsess"; return 1; }

  if dx "grep -q '\"type\":\"turn.completed\"' ~/turns/$n.jsonl"; then
    log "turn $n done (exit $rc): $(dx "tr '\n' ' ' < ~/turns/$n.txt" | cut -c1-400)"
    return 0
  fi
  log "turn $n did not complete (exit $rc): $(dx "tail -c 600 ~/turns/$n.err ~/turns/$n.jsonl" | tr '\n' ' ')"
  return 1
}

# all turn_context entries must carry MODEL, EFFORT, never, danger-full-access
check_turn_context() {
  dx "python3 - \"$MODEL\" \"$EFFORT\" <<'EOF'
import glob, json, sys
model, effort = sys.argv[1:3]
seen = set()
for f in glob.glob('/home/ubuntu/.codex/sessions/**/*.jsonl', recursive=True):
    for line in open(f):
        d = json.loads(line)
        if d.get('type') == 'turn_context':
            p = d['payload']
            seen.add((p.get('model'), p.get('effort'), p.get('approval_policy'),
                      (p.get('sandbox_policy') or {}).get('type')))
print(sorted(seen))
sys.exit(0 if seen == {(model, effort, 'never', 'danger-full-access')} else 1)
EOF"
}

drive() {
  local go=0 keep=0 failed=0 ok st
  turn "$PROMPT"; ok=$?
  [ "$STATUS" = ok ] || return
  if ! TC=$(check_turn_context); then fail "turn_context mismatch: $TC"; return; fi
  log "turn_context: $TC"
  while true; do
    st=$(clock)
    if [ $ok = 0 ]; then failed=0
    elif [[ "$st" != *"Clock stopped"* ]]; then
      failed=$((failed + 1))
      [ $failed -lt $MAX_FAILED_TURNS ] || { fail "$failed consecutive turns did not complete"; return; }
      log "waiting $FAILED_TURN_WAIT s before retrying"; sleep $FAILED_TURN_WAIT
      st=$(clock)
    fi
    log "clock: $(echo "$st" | tr '\n' ' ')"
    if [[ "$st" == *"Clock stopped"* ]]; then
      [ -n "$STOPPED_BY" ] || STOPPED_BY=agent
      return
    elif [[ "$st" == *"Clock not started"* ]]; then
      go=$((go + 1)); [ $go -le $MAX_GO ] || { fail "clock still not started after $MAX_GO x go"; return; }
      turn "go"; ok=$?
    elif [[ "$st" == *"TIME IS UP"* ]]; then
      # the agent's turn ended after the budget without stopping the clock
      log "turn ended after TIME IS UP without harness.py stop: stopping the clock"
      dx 'python3 harness.py stop' >> "$LOG" 2>&1
      STOPPED_BY=driver; return
    else
      keep=$((keep + 1)); [ $keep -le $MAX_KEEP_GOING ] || { fail "more than $MAX_KEEP_GOING x keep going"; return; }
      turn "keep going"; ok=$?
    fi
    [ "$STATUS" = ok ] || return
  done
}

drive

# whatever happened, make sure codex is gone and the clock is stopped
docker exec $C pkill codex 2> /dev/null && log "killed a leftover codex process"
if [[ "$(clock)" != *"Clock not started"* && "$(clock)" != *"Clock stopped"* ]]; then
  dx 'python3 harness.py stop' >> "$LOG" 2>&1; log "clock stopped by the driver after failure"
  STOPPED_BY=${STOPPED_BY:-driver}
fi
log "final clock: $(clock | tr '\n' ' ')"

# peak memory and processes killed at the cap over the whole run
MEM_PEAK=$(docker exec $C cat /sys/fs/cgroup/memory.peak 2> /dev/null)
OOM_KILLS=$(docker exec $C awk '$1 == "oom_kill" { print $2 }' /sys/fs/cgroup/memory.events 2> /dev/null)
log "memory: peak=${MEM_PEAK:-unknown} bytes, oom_kills=${OOM_KILLS:-unknown}"

# ---------- after the run ----------

if dx 'test -f timing/clock.json'; then
  dx 'python3 harness.py report > report.txt' && log "report: $(dx 'cat report.txt' | tr '\n' ' ')"
fi
if dx 'test -f results.tsv && [ $(wc -l < results.tsv) -gt 1 ]'; then
  log "run_groundtruth_all.sh"
  dx './run_groundtruth_all.sh > ~/groundtruth.log 2>&1' || log "run_groundtruth_all.sh failed (see groundtruth.log)"
  dx 'python3 plot_auc_history.py' >> "$LOG" 2>&1 || log "plot_auc_history.py failed"
else
  [ "$STATUS" = ok ] && fail "no experiments in results.tsv"
fi

# best kept commit: highest Eval AUC among keep rows (first one on ties)
BEST=$(dx "awk -F'\t' 'NR > 1 && \$3 == \"keep\" && (b == \"\" || \$2 > a) { a = \$2; b = \$1 } END { print b }' results.tsv 2>/dev/null")
FIRST=$(dx 'git rev-list --max-parents=0 HEAD')
BRANCH=$(dx 'git branch --show-current')
[ -n "$BRANCH" ] || log "NOTE: repo is on a detached HEAD at the end of the run"
UPSTREAM=$(dx "git log -1 --format=%s $FIRST")
log "branch=${BRANCH:-<detached>} first=$FIRST best=${BEST:-<none>} upstream: $UPSTREAM"

# leak check needs the container's holdout.csv and forbidden files, so it runs there
docker cp "$HERE/leak_check.py" $C:/tmp/leak_check.py > /dev/null
dx 'python3 /tmp/leak_check.py' > "$OUT/leak_check.txt" 2>&1 || log "leak_check.py failed (see leak_check.txt)"

# copy out
cp_out() { docker cp "$C:$1" "$2" > /dev/null 2>&1 || log "copy: $1 not found"; }
for f in results.tsv research-log.md groundtruth_all.tsv auc_history.png report.txt timing; do
  cp_out $R/$f "$OUT/"
done
cp_out /home/ubuntu/groundtruth.log "$OUT/"
# the final message and stderr of each turn; the event streams (turns/*.jsonl)
# duplicate the session log and are not kept
cp_out /home/ubuntu/turns "$OUT/" && rm -f "$OUT"/turns/*.jsonl
[ -n "$BEST" ] && dx "git show $BEST:train.py" > "$OUT/train.py"
[ -n "$BRANCH" ] && dx "git log --stat $BRANCH" > "$OUT/git-log.txt"
[ -n "$BEST" ] && dx "git diff --stat $FIRST $BEST" > "$OUT/diff-stat.txt"
SESSION=$(dx 'find ~/.codex/sessions -type f' | head -1)
[ -n "$SESSION" ] && cp_out "$SESSION" "$OUT/.codex-session-raw.jsonl"

# archive the session log slimmed and gzipped (encrypted reasoning dropped,
# account ids redacted, also in the other copied files); keep the raw copy
# only if that fails
if [ -s "$OUT/.codex-session-raw.jsonl" ]; then
  python3 "$HERE/slim_session.py" "$OUT/.codex-session-raw.jsonl" "$OUT/codex-session.jsonl.gz" \
    --also "$OUT" 2>&1 | while read -r l; do log "$l"; done
  if [ "${PIPESTATUS[0]}" = 0 ]; then
    rm "$OUT/.codex-session-raw.jsonl"
  else
    log "slim_session.py failed: keeping the raw session log as .codex-session-raw.jsonl"
    rm -f "$OUT/codex-session.jsonl.gz"
  fi
fi

# summary for Claude
EVAL=$(awk -F'\t' -v c="$BEST" '$1 "" == c { print $4 }' "$OUT/groundtruth_all.tsv" 2> /dev/null)
HOLD=$(awk -F'\t' -v c="$BEST" '$1 "" == c { print $5 }' "$OUT/groundtruth_all.tsv" 2> /dev/null)
NEXP=$(awk 'NR > 1' "$OUT/results.tsv" 2> /dev/null | wc -l)
printf '%s\n' "${MESSAGES[@]}" > "$OUT/.turns"
C=$C STATUS=$STATUS REASON=$REASON MODEL=$MODEL EFFORT=$EFFORT CODEX_VERSION=${CODEX_VERSION:-} \
TC=${TC:-} SID=$SID STOPPED_BY=$STOPPED_BY BRANCH=$BRANCH FIRST=$FIRST UPSTREAM=$UPSTREAM \
NEXP=$NEXP BEST=$BEST EVAL=$EVAL HOLD=$HOLD \
MEM_MAX=${MEM_MAX:-} MEM_PEAK=${MEM_PEAK:-} OOM_KILLS=${OOM_KILLS:-} python3 - "$OUT" <<'EOF'
import json, os, pathlib, sys
out = pathlib.Path(sys.argv[1])
e = os.environ
turns = (out / ".turns").read_text().splitlines()
(out / ".turns").unlink()
json.dump({
    "container": e["C"], "status": e["STATUS"], "reason": e["REASON"],
    "model": e["MODEL"], "effort": e["EFFORT"], "codex_version": e["CODEX_VERSION"],
    "turn_context": e["TC"], "session_id": e["SID"], "turns": turns,
    "clock_stopped_by": e["STOPPED_BY"], "branch": e["BRANCH"], "first_commit": e["FIRST"],
    "upstream": e["UPSTREAM"], "results_rows": int(e["NEXP"]),
    "best_commit": e["BEST"], "best_eval_auc": e["EVAL"], "best_holdout_auc": e["HOLD"],
    "memory_limit_bytes": e["MEM_MAX"], "memory_peak_bytes": e["MEM_PEAK"],
    "oom_kills": e["OOM_KILLS"],
}, open(out / "driver-summary.json", "w"), indent=2)
EOF
log "summary: $(tr -d '\n' < "$OUT/driver-summary.json")"

# delete the container only if the essentials made it out
if [ -s "$OUT/codex-session.jsonl.gz" ] && [ -s "$OUT/driver-summary.json" ] \
   && { [ "$STATUS" != ok ] || { [ -s "$OUT/results.tsv" ] && [ -s "$OUT/groundtruth_all.tsv" ]; }; }; then
  docker stop "$C" > /dev/null && docker rm "$C" > /dev/null && log "container deleted"
else
  log "NOT deleting container $C: essential files missing from $OUT"
  STATUS=failed
fi

[ "$STATUS" = ok ] && exit 0 || exit 1
