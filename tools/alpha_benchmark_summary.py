#!/usr/bin/env python3
"""Offline benchmark summary: no network, no database writes, no scans."""
import argparse
import json
import math
import statistics
from pathlib import Path


def summarize(values):
    if not values or any(not isinstance(x,(float,int)) or isinstance(x,bool) or not math.isfinite(x) or x<0 for x in values):
        raise ValueError("latencies_ms must contain finite nonnegative numbers")
    sample=sorted(float(x) for x in values)
    def percentile(q):
        pos=(len(sample)-1)*q
        lo=int(pos)
        hi=min(lo+1,len(sample)-1)
        return sample[lo]+(sample[hi]-sample[lo])*(pos-lo)
    return {"count":len(sample),"p50_ms":round(percentile(.5),3),
            "p95_ms":round(percentile(.95),3),"max_ms":round(max(sample),3),
            "mean_ms":round(statistics.mean(sample),3)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path,help="Private sanitized JSON containing latencies_ms list")
    args=parser.parse_args()
    data=json.loads(args.input.read_text(encoding="utf-8"))
    print(json.dumps(summarize(data["latencies_ms"]),sort_keys=True))



if __name__=="__main__":
    main()
