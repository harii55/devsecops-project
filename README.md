# Library Book Tracker

**Name:** Hariny Patel
**ID:** 2024eb02494
**Course:** DevOps Final Capstone (Session 21)

Library Book Tracker is a small web app for a library. A librarian can add books, see which books are available, lend a book to a member and mark it as returned. I built the app first and then took it through the full DevOps flow: tests, Docker, a CI/CD pipeline with a security scan, AWS infrastructure with Terraform, Kubernetes with Helm and Argo CD, and monitoring with Prometheus and Grafana.

## 1. Architecture

```
Developer
   |  git push
   v
GitHub repository
   |
   v
GitHub Actions
   |-- test: pytest + frontend build
   |-- build-scan-push: Docker build -> Trivy scan -> push to GHCR (tag = commit SHA)
   `-- deploy: writes the new tag into helm/booktracker/values.yaml
                 |
                 v
              Argo CD (watches the repo) ---> syncs the Helm chart
                 |
                 v
AWS (made by Terraform): VPC + EKS cluster
   |
   |-- Traefik Ingress (AWS load balancer)
   |      |-- /      -> frontend Service -> React app on Nginx (2 pods)
   |      `-- /api   -> backend Service  -> FastAPI (2 to 5 pods, HPA)
   |                                          |
   |                                          v
   |                                     PostgreSQL (StatefulSet + EBS volume)
   |
   `-- Prometheus (scrapes /metrics) -> Grafana dashboard
```

## 2. Tech Stack

| Area | Tools |
|------|-------|
| Frontend | React 19, Vite, CSS, Nginx |
| Backend | Python 3.13, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 17 |
| Testing | Pytest with an in-memory SQLite test database |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions, GitHub Container Registry (GHCR) |
| Security | Trivy |
| Infrastructure | Terraform, AWS VPC, AWS EKS |
| Kubernetes | Helm, Traefik Ingress, HPA, Argo CD |
| Monitoring | Prometheus, Grafana (kube-prometheus-stack) |

## 3. Folder Structure

```
backend/        FastAPI app, Alembic migration, tests, Dockerfile
frontend/       React app, Nginx config, Dockerfile
docker-compose.yml
.github/workflows/ci-cd.yml
terraform/      VPC + EKS
k8s/            namespace, storage class, Argo CD application
helm/booktracker/   Helm chart for the whole app
monitoring/     values for Prometheus and Grafana
scripts/        load test for the HPA demo
demo/           presentation slides and video
```

## 4. The Application

### Backend API

| Method | Path | What it does |
|--------|------|--------------|
| GET | `/health` | Liveness check, returns `ok` if the app is running |
| GET | `/ready` | Readiness check, returns 503 if the database cannot be reached |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/books` | List books, optional filter `?status=available` or `?status=borrowed` |
| GET | `/api/books/{id}` | Get one book |
| POST | `/api/books` | Add a book (title, author, genre) |
| PUT | `/api/books/{id}` | Edit a book, borrow it or return it |
| DELETE | `/api/books/{id}` | Delete a book |
| GET | `/api/books/stats` | Count of total, available and borrowed books |

Swagger docs are at `http://localhost:8000/docs`.

Rules I added in the API:
- A book cannot be borrowed without a borrower name (400 error).
- When a book is returned, the borrower name is cleared.
- A missing book gives 404 and empty fields give 422.

### Database

The `books` table is created by the Alembic migration `backend/alembic/versions/0001_create_books.py`. The backend container runs `alembic upgrade head` before it starts, so the table is always there.

### Frontend

The React page shows three counters (total, available, borrowed), a form to add a book, filter buttons and a table with Borrow, Return and Delete buttons. It shows a loading message and an error box if the backend is down. On small screens the counters stack and the table scrolls sideways.

The browser only calls `/api/...`. Nginx (in Docker) or the Ingress (in Kubernetes) sends those calls to the backend, so the frontend never needs the backend address.

## 5. Run Locally

### With Docker Compose (one command)

```bash
docker compose up --build
```

- App: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics

Stop with `docker compose down`. Add `-v` to also delete the database volume.

### Without Docker

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://library:library@localhost:5432/library
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

## 6. Tests

```bash
cd backend
pytest -v
```

There are 11 tests in `backend/tests/test_api.py`. They cover health, readiness, adding a book, validation errors, getting a book, 404 for a missing book, borrow and return, borrowing without a name, filtering with stats, deleting and the metrics endpoint.

The tests never touch the real database. `tests/conftest.py` replaces the database with an in-memory SQLite database for each test, so every test starts empty.

## 7. Docker

- `backend/Dockerfile` starts from `python:3.13-slim`, installs the requirements, removes pip (it is only needed while building) and runs as user `10001`.
- `frontend/Dockerfile` is a multi-stage build. Stage 1 uses Node to run `npm run build`. Stage 2 copies only the built `dist/` folder into `nginx-unprivileged`, which runs as user `101`. Node and the source code are not in the final image.
- `docker-compose.yml` starts postgres, backend and frontend. The backend waits until the postgres health check passes.

## 8. CI/CD Pipeline

File: `.github/workflows/ci-cd.yml`. It runs on every push to `main` (and can be started by hand).

1. **test**: installs Python packages and runs `pytest -v`, then runs `npm ci` and `npm run build`. If any test fails, the pipeline stops here and no image is built.
2. **build-scan-push** (runs for backend and frontend in parallel): builds the image, scans it with Trivy and pushes it to GHCR only if the scan passes. The tag is the Git commit SHA, for example `ghcr.io/harii55/booktracker-backend:3f2c1ab...`, so every running image can be traced back to one commit.
3. **deploy**: writes the new SHA into `helm/booktracker/values.yaml` and commits it with `[skip ci]`. Argo CD sees the change and rolls out the new images. This is the GitOps flow: Git is the source of truth and the cluster follows it.

## 9. Security Scan (Trivy)

Trivy scans both images for known vulnerabilities (CVEs) in the OS packages and in the Python and npm libraries. The pipeline uses `--exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed`, so the build fails if there is any HIGH or CRITICAL issue that already has a fix.

What I found while building this: the plain `python:3.13-slim` image failed the scan with four HIGH issues. One of them was CVE-2026-97687 in `urllib3 2.7.0`, which is a copy of urllib3 bundled inside pip. My app does not use pip at runtime, so I uninstall pip after installing the requirements and the issue is gone. The nginx image had a HIGH issue in `curl` (CVE-2026-92392) that was fixed in a newer Alpine package, so the Dockerfile runs `apk upgrade`. After these two changes both images scan clean.

A clean scan does not mean the app is fully secure. It only means no known HIGH or CRITICAL CVE with a fix was found in the image at that time.

## 10. Terraform (AWS)

Folder: `terraform/`. It uses the official `terraform-aws-modules` for VPC and EKS.

- VPC `10.0.0.0/16` in `us-east-1` with 2 public subnets and 2 private subnets in two zones, plus one NAT gateway.
- EKS cluster `booktracker-eks` with one managed node group (3 x `t3.medium`).
- EKS add-ons: VPC CNI, CoreDNS, kube-proxy, Pod Identity agent, EBS CSI driver (for the database volume) and metrics-server (for the HPA).
- The EBS CSI driver gets its own IAM role through EKS Pod Identity. My first try gave the policy to the node role, but the driver pods could not reach the node metadata, so the driver kept crashing. Pod Identity fixed it, and only the driver gets EBS permissions instead of every pod on the node.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
aws eks update-kubeconfig --region us-east-1 --name booktracker-eks
```

Every AWS resource gets the tag `Project=booktracker`, so it is easy to see what this project created. No AWS keys are stored in this repo. Terraform uses the AWS CLI login on my machine. `terraform.tfvars` and the state files are in `.gitignore`.

## 11. Kubernetes and Helm

The Helm chart is in `helm/booktracker/`:

| Template | What it creates |
|----------|-----------------|
| `backend.yaml` | Backend Deployment (waits for postgres, readiness `/ready`, liveness `/health`) and ClusterIP Service |
| `frontend.yaml` | Frontend Deployment with 2 replicas and ClusterIP Service |
| `postgres.yaml` | Secret, StatefulSet with a 1 GiB EBS volume and Service |
| `ingress.yaml` | `/api` goes to the backend and `/` goes to the frontend |
| `hpa.yaml` | Scales the backend from 2 to 5 pods at 70% CPU |
| `servicemonitor.yaml` | Tells Prometheus to scrape the backend `/metrics` |

Deploy steps (in this order):

```bash
kubectl apply -f k8s/namespace.yaml -f k8s/storageclass.yaml

helm repo add traefik https://traefik.github.io/charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install traefik traefik/traefik -n traefik --create-namespace
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f monitoring/prometheus-values.yaml

helm upgrade --install booktracker helm/booktracker -n booktracker

kubectl get pods -n booktracker
kubectl get svc -n booktracker
kubectl get ingress -n booktracker
helm list -n booktracker
```

Open the address shown by `kubectl get ingress -n booktracker` in the browser.

Monitoring is installed before the app because the chart has a ServiceMonitor, which only exists after kube-prometheus-stack is installed.

### Argo CD (GitOps)

```bash
kubectl create namespace argocd
kubectl apply -n argocd --server-side -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl apply -f k8s/argocd-app.yaml
kubectl port-forward -n argocd svc/argocd-server 8080:443
kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

Open https://localhost:8080 and log in as `admin`. The Argo CD app has the same name as the Helm release, so it takes over the resources Helm created, and from then on every pipeline run is deployed by Argo CD.

### Autoscaling

```bash
sh scripts/load-test.sh
kubectl get hpa -n booktracker --watch
```

The load test runs a small pod that keeps calling the API. When the backend CPU goes over 70%, the HPA adds pods.

## 12. Observability

- The backend exposes `/metrics` using `prometheus-fastapi-instrumentator` (request counts, latency, status codes).
- `monitoring/prometheus-values.yaml` sets up kube-prometheus-stack so Prometheus picks up every ServiceMonitor, and it loads a Grafana dashboard called **Library Book Tracker - Backend** with requests per second, 95th percentile latency, error responses and number of backend pods.

```bash
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
kubectl get secret -n monitoring monitoring-grafana -o jsonpath='{.data.admin-password}' | base64 -d
```

- Prometheus targets: http://localhost:9090/targets (the backend shows as UP)
- Grafana: http://localhost:3001 (user `admin`)

## 13. Clean Up (avoid AWS charges)

```bash
helm uninstall booktracker -n booktracker
kubectl delete pvc --all -n booktracker
helm uninstall traefik -n traefik
cd terraform && terraform destroy
```

The Traefik load balancer and the database EBS volume are created by Kubernetes, not by Terraform, so I delete them first. Otherwise `terraform destroy` gets stuck on the VPC.

## 14. Known Issues and Limitations

- PostgreSQL runs inside the cluster with one replica. For a real production app I would use Amazon RDS with backups.
- The database password is a simple demo value in `values.yaml`. In production it should come from AWS Secrets Manager or a sealed secret.
- The app uses plain HTTP through the load balancer address. A real setup would add a domain name and an HTTPS certificate.
- There is no login, so anyone who can open the page can change the books.
- Two backend pods could run the Alembic migration at the same moment on a brand new database. One of them may restart once, then it works.
