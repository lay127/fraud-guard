"""Minimal HTTP load generator (standard library only).

Use it to put the inference service under load and watch the HPA scale out:
    python tools/loadgen.py --url http://localhost:8000/predict --duration 120
"""

import argparse
import json
import random
import statistics
import threading
import time
import urllib.request


def worker(url, deadline, unique, latencies, errors, lock):
    while time.monotonic() < deadline:
        text = f"sample {random.randrange(unique)}"
        body = json.dumps({"text": text}).encode()
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response.read()
            elapsed = time.perf_counter() - start
            with lock:
                latencies.append(elapsed)
        except OSError:  # URLError, timeouts and connection resets
            with lock:
                errors.append(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8000/predict")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--duration", type=float, default=30.0, help="seconds")
    parser.add_argument(
        "--unique",
        type=int,
        default=1000,
        help="distinct inputs; fewer inputs mean more cache hits",
    )
    args = parser.parse_args()

    latencies, errors, lock = [], [], threading.Lock()
    deadline = time.monotonic() + args.duration
    threads = [
        threading.Thread(
            target=worker,
            args=(args.url, deadline, args.unique, latencies, errors, lock),
        )
        for _ in range(args.concurrency)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    total = len(latencies) + len(errors)
    print(f"requests={total} errors={len(errors)} "
          f"throughput={len(latencies) / args.duration:.1f}/s")
    if len(latencies) >= 2:
        cuts = statistics.quantiles(latencies, n=100)
        print(f"p50={cuts[49] * 1000:.1f}ms p95={cuts[94] * 1000:.1f}ms "
              f"p99={cuts[98] * 1000:.1f}ms")


if __name__ == "__main__":
    main()
