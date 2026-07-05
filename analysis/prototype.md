
# Express Prototype Benchmark

## Environment

Machine: Lenovo LOQ Essentials
CPU: Intel Core i5-12450HX
GPU: NVIDIA RTX 3050 6GB
RAM: 16 GB
OS: Windows 11 (for now)

---

## Baseline Docker Image

Base Image:
node:22

Build Command:

docker build -f ../dockerfiles/Dockerfile -t containerbench/express:baseline .

Image Size:
411MB

Build Time:
9.0073978 seconds

Status:
✅ Successful

Endpoints Tested:

GET /
✅ Working

GET /health
✅ Working

GET /users
✅ Working

Notes

- Successfully built the baseline Docker image.
- Application runs correctly inside Docker.
- This serves as the baseline for future optimization strategies.