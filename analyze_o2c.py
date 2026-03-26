import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from itertools import combinations

ROOT = Path("sap-order-to-cash-dataset") / "sap-o2c-data"
OUT = Path("analysis_output")
OUT.mkdir(exist_ok=True)

DATE_PATTERNS = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "date"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$"), "datetime"),
]


def infer_scalar_type(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int) and not isinstance(v, bool):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return "string"
        for pat, t in DATE_PATTERNS:
            if pat.match(s):
                return t
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def canonical_type(type_counter):
    non_null = {k: c for k, c in type_counter.items() if k != "null"}
    if not non_null:
        return "null"
    if len(non_null) == 1:
        return next(iter(non_null.keys()))
    keys = set(non_null.keys())
    if keys <= {"int", "float"}:
        return "float"
    if keys <= {"date", "datetime"}:
        return "datetime"
    if "string" in keys:
        return "string"
    return "mixed(" + ",".join(sorted(keys)) + ")"


def normalize_value(v):
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        return str(v)
    return None


def read_jsonl(file_path):
    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main():
    entity_files = defaultdict(list)
    for p in ROOT.rglob("*.jsonl"):
        entity_files[p.parent.name].append(p)

    entities = {}
    value_samples = defaultdict(lambda: defaultdict(set))

    for entity, files in sorted(entity_files.items()):
        row_count = 0
        fields = defaultdict(lambda: {
            "types": Counter(),
            "nulls": 0,
            "non_null": 0,
            "distinct": set(),
            "examples": [],
        })

        for fp in files:
            for row in read_jsonl(fp):
                if not isinstance(row, dict):
                    continue
                row_count += 1
                for k, v in row.items():
                    t = infer_scalar_type(v)
                    st = fields[k]
                    st["types"][t] += 1
                    if v is None:
                        st["nulls"] += 1
                    else:
                        st["non_null"] += 1
                        nv = normalize_value(v)
                        if nv is not None:
                            if len(st["distinct"]) < 300000:
                                st["distinct"].add(nv)
                            if len(value_samples[entity][k]) < 120000:
                                value_samples[entity][k].add(nv)
                    if len(st["examples"]) < 3 and v is not None:
                        st["examples"].append(v)

        field_info = {}
        for k, st in fields.items():
            field_info[k] = {
                "type": canonical_type(st["types"]),
                "null_ratio": (st["nulls"] / row_count) if row_count else 0.0,
                "non_null": st["non_null"],
                "distinct_count": len(st["distinct"]),
                "examples": st["examples"],
                "types_breakdown": dict(st["types"]),
            }

        # Primary key candidates
        pk_candidates = []
        for k, info in field_info.items():
            if info["non_null"] == row_count and info["distinct_count"] == row_count and row_count > 0:
                pk_candidates.append(k)

        # Composite key check among id-like fields when no strict single PK
        composite_candidates = []
        if not pk_candidates and row_count > 0:
            id_like = [
                k for k in field_info
                if any(tok in k.lower() for tok in ["id", "uuid", "number", "document", "item", "line", "order", "billing", "delivery", "entry"]) 
            ]
            id_like = sorted(set(id_like))[:12]
            if len(id_like) >= 2:
                # Approximate uniqueness by concatenating from sampled sets isn't safe; compute exact by second pass.
                for combo in combinations(id_like, 2):
                    seen = set()
                    unique = True
                    for fp in files:
                        for row in read_jsonl(fp):
                            if not isinstance(row, dict):
                                continue
                            vals = []
                            bad = False
                            for c in combo:
                                v = row.get(c)
                                if v is None:
                                    bad = True
                                    break
                                vals.append(str(v))
                            if bad:
                                unique = False
                                break
                            key = "|".join(vals)
                            if key in seen:
                                unique = False
                                break
                            seen.add(key)
                    if unique and len(seen) == row_count:
                        composite_candidates.append(list(combo))
                    if len(composite_candidates) >= 3:
                        break

        entities[entity] = {
            "entity": entity,
            "files": [str(f.as_posix()) for f in sorted(files)],
            "row_count": row_count,
            "fields": field_info,
            "pk_candidates": pk_candidates,
            "composite_pk_candidates": composite_candidates,
        }

    # Build primary key reference sets (best guess)
    pk_map = {}
    for e, meta in entities.items():
        pk = None
        if meta["pk_candidates"]:
            # Prefer id-like names
            id_like = [k for k in meta["pk_candidates"] if any(tok in k.lower() for tok in ["id", "uuid", "number", "document", "order", "delivery", "billing", "entry", "partner", "product", "plant", "location"])]
            pk = id_like[0] if id_like else meta["pk_candidates"][0]
        pk_map[e] = pk

    relationships = []
    for src, src_meta in entities.items():
        for f, finfo in src_meta["fields"].items():
            if finfo["non_null"] == 0:
                continue
            src_vals = value_samples[src].get(f, set())
            if not src_vals:
                continue
            for tgt, tgt_meta in entities.items():
                if src == tgt:
                    continue
                tgt_pk = pk_map.get(tgt)
                if not tgt_pk:
                    continue
                tgt_vals = value_samples[tgt].get(tgt_pk, set())
                if not tgt_vals:
                    continue
                inter = src_vals & tgt_vals
                if not inter:
                    continue
                ratio_src = len(inter) / max(1, len(src_vals))
                ratio_tgt = len(inter) / max(1, len(tgt_vals))
                name_hint = (
                    f.lower() == tgt_pk.lower()
                    or f.lower().endswith("_id")
                    or "id" in f.lower()
                    or any(tok in f.lower() and tok in tgt.lower() for tok in ["customer", "partner", "product", "order", "delivery", "billing", "plant", "location", "payment", "journal", "entry"])
                )
                if ratio_src >= 0.6 or (name_hint and ratio_src >= 0.2):
                    relationships.append({
                        "source_entity": src,
                        "source_field": f,
                        "target_entity": tgt,
                        "target_field": tgt_pk,
                        "overlap_values": len(inter),
                        "source_unique_values": len(src_vals),
                        "target_unique_values": len(tgt_vals),
                        "coverage_source": ratio_src,
                        "coverage_target": ratio_tgt,
                    })

    # Deduplicate by best coverage
    dedup = {}
    for r in relationships:
        key = (r["source_entity"], r["source_field"], r["target_entity"], r["target_field"])
        if key not in dedup or r["coverage_source"] > dedup[key]["coverage_source"]:
            dedup[key] = r
    relationships = sorted(dedup.values(), key=lambda x: (x["source_entity"], -x["coverage_source"]))

    # Cardinality estimation
    for r in relationships:
        src = r["source_entity"]
        sf = r["source_field"]
        src_meta = entities[src]
        distinct = src_meta["fields"][sf]["distinct_count"]
        rows = src_meta["row_count"]
        if distinct == rows:
            card = "1:1_or_N:1"
        else:
            card = "N:1"
        r["estimated_cardinality"] = card

    output = {
        "root": str(ROOT.as_posix()),
        "entities": entities,
        "primary_key_choice": pk_map,
        "relationships": relationships,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    out_json = OUT / "dataset_profile.json"
    out_json.write_text(json.dumps(output, indent=2), encoding="utf-8")

    # Also write quick summary TSV for easy terminal inspection
    lines = ["entity\trows\tpk_choice\tfield_count"]
    for e, m in sorted(entities.items()):
        lines.append(f"{e}\t{m['row_count']}\t{pk_map.get(e) or ''}\t{len(m['fields'])}")
    (OUT / "entity_counts.tsv").write_text("\n".join(lines), encoding="utf-8")

    rel_lines = ["source_entity\tsource_field\ttarget_entity\ttarget_field\tcoverage_source\toverlap\tcardinality"]
    for r in relationships:
        rel_lines.append(
            f"{r['source_entity']}\t{r['source_field']}\t{r['target_entity']}\t{r['target_field']}\t{r['coverage_source']:.3f}\t{r['overlap_values']}\t{r['estimated_cardinality']}"
        )
    (OUT / "relationships.tsv").write_text("\n".join(rel_lines), encoding="utf-8")

    print(f"Profile complete. Entities={len(entities)} Relationships={len(relationships)}")
    print(f"Wrote: {out_json.as_posix()}")


if __name__ == "__main__":
    main()
