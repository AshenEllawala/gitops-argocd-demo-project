# 🚀 GitOps with ArgoCD on Azure Kubernetes Service (AKS)

![GitOps](https://img.shields.io/badge/GitOps-ArgoCD-orange?style=for-the-badge&logo=argo)
![Kubernetes](https://img.shields.io/badge/Kubernetes-AKS-blue?style=for-the-badge&logo=kubernetes)
![Azure](https://img.shields.io/badge/Cloud-Azure-0078D4?style=for-the-badge&logo=microsoftazure)
![Nginx](https://img.shields.io/badge/App-Nginx-009639?style=for-the-badge&logo=nginx)

## 📌 Project Overview

This project demonstrates a **production-style GitOps workflow** using **ArgoCD** on **Azure Kubernetes Service (AKS)**. Any change pushed to this Git repository is **automatically detected and deployed** to the Kubernetes cluster — no manual `kubectl apply` required.

> **Core Principle:** Git is the single source of truth. The cluster always reflects what's in the repository.

---

## 🏗️ Architecture

```
Developer pushes change to GitHub
            ↓
    ArgoCD detects new commit
            ↓
  ArgoCD compares Git state vs Cluster state
            ↓
    Cluster is OutOfSync → ArgoCD auto-applies
            ↓
  Live web app updates automatically ✅
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| **Azure AKS** | Managed Kubernetes cluster |
| **ArgoCD** | GitOps continuous delivery engine |
| **GitHub** | Source of truth for all manifests |
| **Nginx** | Web application container |
| **Kubernetes ConfigMap** | Stores HTML — changed to trigger GitOps demo |
| **Azure LoadBalancer** | Exposes app with public IP |

---

## 📁 Repository Structure

```
gitops-argocd-demo/
├── k8s/
│   ├── configmap.yaml      # HTML content served by nginx (edit this to trigger GitOps)
│   ├── deployment.yaml     # Nginx deployment with ConfigMap volume mount
│   └── service.yaml        # LoadBalancer service — exposes app publicly
├── argocd-app.yaml         # ArgoCD Application manifest
└── README.md
```

---

## ⚙️ How It Works

### 1. Kubernetes Manifests (`k8s/`)
- **`configmap.yaml`** — Contains the HTML page served by nginx. Editing this file and pushing to GitHub triggers the GitOps loop.
- **`deployment.yaml`** — Runs an nginx container and mounts the ConfigMap as the web root (`/usr/share/nginx/html`).
- **`service.yaml`** — Exposes the nginx pod via Azure LoadBalancer with a public IP.

### 2. ArgoCD Application (`argocd-app.yaml`)
- Tells ArgoCD to watch this repo at the `k8s/` path
- Auto-sync enabled — detects and applies changes automatically
- Self-heal enabled — reverts any manual cluster changes to match Git

---

## 🚀 Setup Guide

### Prerequisites
- Azure CLI installed and logged in
- `kubectl` installed
- A GitHub account

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

kubectl patch svc argocd-server -n argocd \
  -p '{"spec": {"type": "LoadBalancer"}}'
```

### Step 3 — Get ArgoCD Credentials
```bash
# Get external IP
kubectl get svc argocd-server -n argocd

# Get admin password
kubectl get secret argocd-initial-admin-secret \
  -n argocd \
  -o jsonpath="{.data.password}" | base64 -d
```

### Step 4 — Deploy ArgoCD Application
```bash
kubectl apply -f argocd-app.yaml
```

### Step 5 — Access the Web App
```bash
kubectl get svc nginx-service -n default
# Open browser → http://EXTERNAL-IP
```

---

## 🎯 Demonstrating the GitOps Loop

1. Open `k8s/configmap.yaml` in GitHub
2. Change `Version 1` → `Version 2` and `background-color: #3498db` → `background-color: #27ae60`
3. Commit the change
4. Watch ArgoCD UI — status goes `OutOfSync` → `Syncing` → `Synced`
5. Refresh the browser — page changes from **Blue** to **Green** automatically ✅

---

## 📸 Key Concepts Demonstrated

- ✅ **GitOps workflow** — Git as single source of truth
- ✅ **Declarative infrastructure** — all config in YAML manifests
- ✅ **Automated sync** — no manual deployments
- ✅ **Self-healing** — cluster reverts manual changes automatically
- ✅ **Kubernetes on Azure** — real cloud deployment
- ✅ **ConfigMap-driven config** — separation of app config from app code

---

## 🧹 Cleanup

```bash
az group delete --name gitops-rg --yes --no-wait
```

---

## 📚 What I Learned

- How to provision and manage AKS clusters via Azure CLI
- Installing and configuring ArgoCD on a live Kubernetes cluster
- Writing Kubernetes manifests (Deployment, Service, ConfigMap)
- Implementing a GitOps pipeline where Git drives cluster state
- Debugging ArgoCD sync issues and Kubernetes resource errors

---

## 🔗 References

- [ArgoCD Official Docs](https://argo-cd.readthedocs.io/)
- [Azure AKS Documentation](https://learn.microsoft.com/en-us/azure/aks/)
- [Kubernetes Official Docs](https://kubernetes.io/docs/)
