"""Print the schema and a few rows of an IndicContextEval parquet shard (no audio decoding).

    uv run python -I scripts/inspect_ice.py <shard.parquet>
"""

import sys

import pyarrow.parquet as pq

pf = pq.ParquetFile(sys.argv[1])
print("rows", pf.metadata.num_rows, "row groups", pf.metadata.num_row_groups)
cols = [c for c in pf.schema_arrow.names if c != "audio"]
tbl = pf.read_row_group(0, columns=cols).slice(0, 400).to_pylist()
print("audio field:", pf.schema_arrow.field("audio").type)
for k in ("speech_style", "code_mixing", "domain_name", "task_name"):
    vals = {}
    for r in tbl:
        vals[r[k]] = vals.get(r[k], 0) + 1
    print(k, dict(sorted(vals.items(), key=lambda kv: -kv[1])[:8]))
print("durations", round(min(r["duration"] for r in tbl), 1), round(sum(r["duration"] for r in tbl) / len(tbl), 1), round(max(r["duration"] for r in tbl), 1))
print("speakers in first 400 rows:", len({r["speaker_id"] for r in tbl}))
for r in tbl[:3]:
    print("\n---")
    for k in cols:
        v = str(r[k])
        print(f"{k}: {v[:700]}")
