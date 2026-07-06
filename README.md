# ContainerBench

ContainerBench is an open-source container image benchmarking framework. It serves as both a reproducible academic research artifact for empirical container evaluation and a DevOps utility to automate container optimizations.

## Methodology

ContainerBench automatically builds, verifies, and analyzes container images across various optimization strategies. For each benchmark run, the framework captures:

1. **Build Performance**: Measures raw build time (`build_time_seconds`) using high-resolution performance counters.
2. **Storage Metrics**:
   - **Image Size** (`image_size_mb`): Extracted directly from `docker inspect` (converting bytes to Megabytes).
   - **Layer Count** (`layer_count`): Determined by counting filesystem layers in the image metadata.
3. **Runtime Metrics**:
   - **Startup Validation**: Maps exposed ports dynamically to avoid localhost conflicts, performs dynamic HTTP validation, and records the container initialization duration (`startup_time_seconds`).
4. **Security Vulnerabilities**: Integrates with Trivy to fetch CVE counts programmatically by severity class (Critical, High, Medium, Low, Unknown).
5. **System Context**: Dumps system environment details (OS version, CPU, RAM, Python version, Docker version) once per session to maintain reproducible research.

---

## Express Pilot Experiment Results

An automated pilot experiment was conducted on the **Express** workload, executing **5 repetitions** for each of the **6 optimization strategies** (total of 30 runs). The raw readings derived from [express-pilot.csv](file:///d:/Coding/containerbench/data/pilot/express-pilot.csv) yield the following aggregated statistics:

| Strategy | Mean Build Time (s) | Image Size (MB) | Layer Count | Mean Startup Time (s) | Security Scan | Overall Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **baseline** | 1.87s | 391.28 MB | 12 | 1.13s | SKIPPED | PASS |
| **alpine** | 1.60s | 56.60 MB | 8 | 1.14s | SKIPPED | PASS |
| **slim** | 1.52s | 78.03 MB | 9 | 1.11s | SKIPPED | PASS |
| **multistage** | 2.23s | 390.08 MB | 10 | 1.12s | SKIPPED | PASS |
| **alpine-multistage** | 1.93s | 55.39 MB | 6 | 1.12s | SKIPPED | PASS |
| **distroless** | 2.07s | 50.75 MB | 21 | 1.14s | SKIPPED | PASS |

---

## Key Findings and Conclusions

1. **Storage Optimization Winner**: **Distroless** produced the smallest overall image footprint (**50.75 MB**), closely followed by **alpine-multistage** (**55.39 MB**). This represents a **~87% size reduction** compared to the baseline image (391.28 MB).
2. **Layer Count Trade-off**: Although **distroless** achieved the smallest footprint, it introduced the highest layer complexity (**21 layers**). Conversely, **alpine-multistage** combined a highly optimized size (55.39 MB) with the minimal layer overhead (**6 layers**), making it the most balanced strategy for combined storage and deployment pipelines.
3. **Speed & Efficiency**: **slim** (Debian Slim) delivered the fastest build times (**1.52s average**) and the lowest startup latency (**1.11s average**), making it highly suitable for rapid development loops where intermediate cache invalidation is frequent.
4. **Resiliency**: The pilot experiment verified that dynamic host port publication (`-P`) and multi-stage HTTP validation prevent false negatives in container startup tracking.
