# Slim a codex session log for archiving with the run's results:
# - drop the encrypted reasoning (`encrypted_content`: readable only by OpenAI,
#   ~15% of the log) - the reasoning summaries, if any, stay
# - redact the ChatGPT account ids (creator_user_id / creator_account_id of
#   session_meta) everywhere in the log, and in the text files of --also DIR
# - write it gzipped; everything else (commands, outputs, messages,
#   turn_context, token counts) is kept as is
#
# Usage: python3 slim_session.py SESSION.jsonl OUT.jsonl.gz [--also DIR]
#
# Used by run_one.sh of /xgb-multi. Also works on an
# already redacted log (e.g. to convert an archived codex-session.jsonl).
import gzip
import json
import sys
from pathlib import Path

args = sys.argv[1:]
also = None
if "--also" in args:
    i = args.index("--also")
    also = Path(args[i + 1])
    del args[i:i + 2]
src, dst = Path(args[0]), Path(args[1])


def drop_encrypted(x):
    if isinstance(x, dict):
        return {k: drop_encrypted(v) for k, v in x.items() if k != "encrypted_content"}
    if isinstance(x, list):
        return [drop_encrypted(v) for v in x]
    return x


lines = src.read_text().splitlines()
ids = set()
for line in lines:
    d = json.loads(line)
    if d.get("type") == "session_meta":
        for k in ("creator_user_id", "creator_account_id"):
            v = d["payload"].get(k)
            if v and v != "REDACTED":
                ids.add(v)

out = []
for line in lines:
    line = json.dumps(drop_encrypted(json.loads(line)), ensure_ascii=False)
    for i in ids:
        line = line.replace(i, "REDACTED")
    out.append(line)
data = ("\n".join(out) + "\n").encode()
assert not any(i.encode() in data for i in ids)
# mtime=0: the same log always gives the same bytes
dst.write_bytes(gzip.compress(data, mtime=0))

# check it reads back
n = sum(1 for _ in gzip.open(dst, "rt"))
assert n == len(lines), (n, len(lines))
print(f"{src.name}: {src.stat().st_size / 1e6:.1f} MB -> {dst.name}: {dst.stat().st_size / 1e6:.2f} MB "
      f"({len(lines)} lines, {len(ids)} account id(s) redacted)")

if also:
    for f in sorted(also.rglob("*")):
        if f.is_file() and f != dst and f.suffix in (".jsonl", ".txt", ".err", ".log", ".md", ".tsv", ".json"):
            t = f.read_text(errors="surrogateescape")
            n = sum(t.count(i) for i in ids)
            if n:
                for i in ids:
                    t = t.replace(i, "REDACTED")
                f.write_text(t, errors="surrogateescape")
                print(f"redacted {n} account id(s) in {f.relative_to(also)}")
