# 🚀 GitOps with ArgoCD + GitHub Actions on Azure AKS

![GitOps](https://img.shields.io/badge/GitOps-ArgoCD-orange?style=for-the-badge&logo=argo)
![Kubernetes](https://img.shields.io/badge/Kubernetes-AKS-blue?style=for-the-badge&logo=kubernetes)
![Azure](https://img.shields.io/badge/Cloud-Azure-0078D4?style=for-the-badge&logo=microsoftazure)
![GitHub Actions](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions)
![Docker](https://img.shields.io/badge/Registry-Docker_Hub-2496ED?style=for-the-badge&logo=docker)
![Python](https://img.shields.io/badge/App-Flask-000000?style=for-the-badge&logo=flask)

---

## 📌 Project Overview

This project implements a **production-style CI/CD + GitOps pipeline** on Azure Kubernetes Service (AKS). Every code change pushed to GitHub automatically triggers a full pipeline — building a Docker image, updating Kubernetes manifests, and deploying to the cluster — all without any manual intervention.

> **Core Principle:** Git is the single source of truth. No manual `kubectl apply` — ever.

---

## 🏗️ Full Pipeline Architecture

```
Developer pushes code change
            ↓
  GitHub Actions triggers (CI)
            ↓
  Builds Docker image from Flask app
            ↓
  Pushes image to Docker Hub with build tag
            ↓
  Updates deployment.yaml with new image tag
            ↓
  Commits manifest change back to GitHub
            ↓
  GitHub Webhook notifies ArgoCD instantly
            ↓
  ArgoCD detects manifest change (CD)
            ↓
  ArgoCD deploys new version to AKS
            ↓
  Live web app updates automatically ✅
```

**Total time from push to live: ~2 minutes**

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| **Azure AKS** | Managed Kubernetes cluster (2 nodes) |
| **ArgoCD v3.3.7** | GitOps continuous delivery engine |
| **GitHub Actions** | CI pipeline — build, push, update manifests |
| **Docker Hub** | Container image registry |
| **Python Flask** | Web application (Gunicorn production server) |
| **GitHub Webhooks** | Instant ArgoCD notification on push |
| **Azure LoadBalancer** | Public IP exposure for ArgoCD UI |

---

## 📁 Repository Structure

```
gitops-argocd-demo-project/
├── app/
│   ├── app.py                    # Flask web application
│   ├── requirements.txt          # Python dependencies (Flask + Gunicorn)
│   ├── Dockerfile                # Multi-layer optimized Docker build
│   └── templates/
│       └── index.html            # Web UI showing version + build number
├── k8s/
│   ├── deployment.yaml           # K8s Deployment — auto-updated by CI
│   └── service.yaml              # LoadBalancer service
├── .github/
│   └── workflows/
│       └── ci-cd.yaml            # GitHub Actions pipeline
├── argocd-app.yaml               # ArgoCD Application manifest
├── TROUBLESHOOTING.md            # All errors faced + solutions
└── README.md
```

---

## ⚙️ How It Works

### CI Pipeline (GitHub Actions)
When code is pushed to `main`:
1. Checks out the repository
2. Logs into Docker Hub using GitHub Secrets
3. Builds Docker image from `app/` directory
4. Tags image with both `latest` and build number (e.g., `ashenellawala/gitops-demo-app:7`)
5. Pushes to Docker Hub
6. Updates `image:` tag in `k8s/deployment.yaml` using `sed`
7. Commits and pushes the manifest change back to the repo

### CD Pipeline (ArgoCD)
1. GitHub Webhook instantly notifies ArgoCD of the new commit
2. ArgoCD compares cluster state vs Git state
3. Detects `OutOfSync` — new image tag in deployment
4. Automatically applies updated manifest to AKS
5. Rolling update deploys new pods with new image
6. Old pods terminate after new pods are healthy

### Self-Healing
If anyone manually changes the cluster (e.g., scales replicas), ArgoCD detects the drift and automatically reverts to match Git state.

---

## 🚀 Setup Guide

### Prerequisites
- Azure CLI installed and logged in (`az login`)
- `kubectl` installed
- GitHub account with a repo
- Docker Hub account

### Step 1 — Create AKS Cluster
```bash
az group create --name gitops-rg --location eastus

az aks create \
  --resource-group gitops-rg \
  --name gitops-aks \
  --node-count 2 \
  --node-vm-size Standard_B2s \
  --generate-ssh-keys \
  --enable-managed-identity

az aks get-credentials --resource-group gitops-rg --name gitops-aks
kubectl get nodes
```

### Step 2 — Install ArgoCD
```bash
kubectl create namespace argocd

kubectl apply -n argocd -f \
  https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Expose ArgoCD UI publicly
kubectl patch svc argocd-server -n argocd \
  -p '{"spec": {"type": "LoadBalancer"}}'

# Get external IP (wait ~2 mins)
kubectl get svc argocd-server -n argocd

# Get admin password
kubectl get secret argocd-initial-admin-secret \
  -n argocd \
  -o jsonpath="{.data.password}" | base64 -d
```

### Step 3 — Add GitHub Secrets
Go to GitHub repo → Settings → Secrets and variables → Actions:

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

### Step 4 — Deploy ArgoCD Application
```bash
kubectl apply -f argocd-app.yaml
```

### Step 5 — Configure GitHub Webhook
Go to GitHub repo → Settings → Webhooks → Add webhook:

| Field | Value |
|-------|-------|
| Payload URL | `https://YOUR-ARGOCD-IP/api/webhook` |
| Content type | `application/json` |
| Secret | Leave empty |
| SSL verification | Disable |
| Events | Just push events |

### Step 6 — Access the Web App
```bash
kubectl get svc gitops-service -n default
# Open http://EXTERNAL-IP
```

> **Note:** If on Azure Student subscription (3 IP limit), use port-forward:
> ```bash
> kubectl port-forward svc/gitops-service -n default 8080:80
> # Open http://localhost:8080
> ```

---

## 🎯 Demonstrating the GitOps Loop

Make any change to `app/templates/index.html` and push:

```bash
git add .
git commit -m "feat: update UI for demo"
git push origin main
```

Watch the pipeline:
1. GitHub Actions tab → pipeline running
2. Docker Hub → new image tag appears
3. ArgoCD UI → status changes OutOfSync → Syncing → Synced
4. Browser → refresh and see the change live ✅

**Zero manual deployment commands required.**

---

## 🔐 Key Concepts Demonstrated

| Concept | Implementation |
|---------|---------------|
| GitOps | Git as single source of truth — ArgoCD enforces it |
| CI/CD Pipeline | GitHub Actions builds + ArgoCD deploys |
| Declarative Config | All state defined in YAML manifests |
| Auto-sync | ArgoCD syncs on every Git commit |
| Self-healing | Manual cluster changes auto-reverted |
| Webhook Integration | Instant sync — no polling delay |
| Image Versioning | Every build tagged with unique build number |
| Prune | Deleted manifests removed from cluster automatically |

---

## 🧹 Cleanup

```bash
az group delete --name gitops-rg --yes --no-wait
```

---

## 📚 What I Built & Learned

**Built:**
- Full CI/CD + GitOps pipeline from scratch on Azure
- Flask web app containerized with Docker and Gunicorn
- GitHub Actions workflow that builds, pushes, and auto-updates manifests
- ArgoCD configured with auto-sync, self-heal, and prune policies
- GitHub Webhook for instant ArgoCD notifications

**Learned:**
- GitOps principles and why Git is the source of truth
- Difference between CI (GitHub Actions) and CD (ArgoCD) responsibilities
- Kubernetes concepts: Deployments, Services, namespaces, env variables
- AKS provisioning and management via Azure CLI
- Debugging Kubernetes issues: CrashLoopBackOff, pending services, credential issues
- Webhook mechanics: HTTP signatures, SSL, event types
- Azure Student subscription limitations and workarounds

---

## 🐛 Troubleshooting

All errors encountered during this project with full root cause analysis and solutions are documented in [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

---

## 🔗 References

- [ArgoCD Official Docs](https://argo-cd.readthedocs.io/)
- [Azure AKS Documentation](https://learn.microsoft.com/en-us/azure/aks/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Hub](https://hub.docker.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
