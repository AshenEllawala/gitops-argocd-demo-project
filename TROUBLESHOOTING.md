# 🔧 Troubleshooting Documentation
## GitOps with ArgoCD + GitHub Actions on Azure AKS

**Author:** Ashen Ellawala
**Project:** gitops-argocd-demo-project
**Date:** April 2026

---

## Table of Contents
1. [ArgoCD Repository Authentication Error](#1-argocd-repository-authentication-error)
2. [GitHub Actions Not Triggering](#2-github-actions-not-triggering)
3. [kubectl get nodes — No Resources Found](#3-kubectl-get-nodes--no-resources-found)
4. [AKS Infrastructure Resource Group Missing](#4-aks-infrastructure-resource-group-missing)
5. [Service EXTERNAL-IP Stuck on Pending](#5-service-external-ip-stuck-on-pending)
6. [Public IP Count Limit Reached](#6-public-ip-count-limit-reached)
7. [BUILD_NUMBER Not Updating on Web Page](#7-build-number-not-updating-on-web-page)
8. [GitHub Webhook — HTTP 307 Redirect](#8-github-webhook--http-307-redirect)
9. [GitHub Webhook — HTTP 400 Bad Request](#9-github-webhook--http-400-bad-request)
10. [ArgoCD Not Auto-Syncing](#10-argocd-not-auto-syncing)

---

## 1. ArgoCD Repository Authentication Error

### Error Message
```
Failed to load target state: failed to generate manifest for source 1 of 1:
rpc error: code = Unknown desc = failed to list refs:
authentication required: Repository not found.
```

### Phase
Phase 4 — Connect Git Repo to ArgoCD

### Root Cause
ArgoCD could not access the GitHub repository. Either the repository was **private** or the `repoURL` in `argocd-app.yaml` had a typo.

### How to Diagnose
```bash
kubectl describe application nginx-gitops-app -n argocd
# Look for "Message" field under Status → Conditions
```

### Solution
**Option A — Make repo public:**
1. Go to GitHub repo → Settings
2. Scroll to Danger Zone → Change visibility → Make Public

**Option B — Fix repo URL:**
Check `argocd-app.yaml` for typos in `repoURL` field.

**Then force ArgoCD to retry:**
```bash
kubectl patch application nginx-gitops-app \
  -n argocd \
  --type merge \
  -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}'
```

### Lesson Learned
Always verify your GitHub repo is public when using ArgoCD without credentials configured. Check the exact repo URL for typos.

---

## 2. GitHub Actions Not Triggering

### Symptom
Pipeline does not run after pushing changes to GitHub. No workflow runs appear in the Actions tab.

### Phase
Phase B — GitHub Actions Setup

### Root Cause
The workflow had a `paths` filter that only triggered on changes inside `app/**`. Changes made to other folders (like `k8s/`, `.github/`, `README.md`) did not match the filter.

```yaml
# Old trigger — only fires when app/ changes
on:
  push:
    branches:
      - main
    paths:
      - 'app/**'   ← Too restrictive
```

### Solution
Remove the path filter or expand it:

```yaml
# Option A — trigger on any push to main
on:
  push:
    branches:
      - main

# Option B — trigger on app or k8s changes
on:
  push:
    branches:
      - main
    paths:
      - 'app/**'
      - 'k8s/**'
```

### Lesson Learned
Path filters are powerful but can silently block triggers. For learning projects, use Option A. For production, use Option B to avoid unnecessary rebuilds.

---

## 3. kubectl get nodes — No Resources Found

### Error Message
```
No resources found
```

### Phase
Phase 2 — AKS Cluster Setup

### Root Cause
Two possible causes were identified:
- **Cause A:** kubectl was pointing to a stale/old cluster context with outdated credentials
- **Cause B:** The AKS cluster's infrastructure resource group was missing (see Issue 4)

### How to Diagnose
```bash
# Check which cluster kubectl is pointing to
kubectl config current-context

# Check if cluster exists on Azure
az aks list --output table

# Check node pool status
az aks nodepool list \
  --resource-group gitops-rg \
  --cluster-name gitops-aks \
  --output table
```

### Solution
Re-pull credentials with overwrite flag:
```bash
az aks get-credentials \
  --resource-group gitops-rg \
  --name gitops-aks \
  --overwrite-existing

kubectl get nodes
```

### Common Mistake
Typo in cluster name — `gitops-ak` instead of `gitops-aks`. Azure returns `ResourceNotFound` for typos.

### Lesson Learned
Always use `--overwrite-existing` when re-pulling credentials. Double-check spelling of resource names — Azure is case and character sensitive.

---

## 4. AKS Infrastructure Resource Group Missing

### Error Message (Azure Portal)
```
The infrastructure resource group 'MC_gitops-rg_gitops-aks_eastasia'
could not be found.
```

### Phase
Phase 2 — AKS Cluster Setup

### Root Cause
When AKS creates a cluster it creates TWO resource groups:
- `gitops-rg` — the main resource group you create
- `MC_gitops-rg_gitops-aks_[region]` — auto-created by Azure, holds actual VMs and load balancers

The infrastructure resource group (`MC_`) was deleted or never created properly, leaving the cluster config intact but with no actual nodes.

### How to Diagnose
```bash
az aks show \
  --resource-group gitops-rg \
  --name gitops-aks \
  --query "agentPoolProfiles[].{Name:name,Count:count,State:provisioningState}" \
  --output table
```

Check Azure Portal — look for the red error banner on the AKS overview page.

### Solution
The cluster cannot be repaired. Delete and recreate:

```bash
# Delete broken cluster
az aks delete \
  --resource-group gitops-rg \
  --name gitops-aks \
  --yes

# Recreate fresh cluster
az aks create \
  --resource-group gitops-rg \
  --name gitops-aks \
  --node-count 2 \
  --node-vm-size Standard_B2s \
  --generate-ssh-keys \
  --enable-managed-identity \
  --location eastus

# Reconnect kubectl
az aks get-credentials \
  --resource-group gitops-rg \
  --name gitops-aks
```

### Lesson Learned
Never manually delete the `MC_` resource group. AKS manages it automatically. If it goes missing, the only fix is full cluster recreation.

---

## 5. Service EXTERNAL-IP Stuck on Pending

### Symptom
```
NAME             TYPE           CLUSTER-IP    EXTERNAL-IP   PORT(S)
gitops-service   LoadBalancer   10.0.11.108   <pending>     80:32381/TCP
```

### Phase
Phase 4 — Application Deployment

### Root Cause
Multiple causes identified:
- Stale kubectl credentials (cluster was recreated but credentials not refreshed)
- Azure subscription IP limit reached (see Issue 6)
- Azure LoadBalancer provisioning delay

### How to Diagnose
```bash
# Check events on the service
kubectl describe svc gitops-service -n default
# Look for events at the bottom

# Check IP quota
az network public-ip list --output table
```

### Solution
**If credentials stale:** Re-pull credentials (see Issue 3)

**If IP limit reached:** Use port-forward instead:
```bash
kubectl port-forward svc/gitops-service -n default 8080:80
# Access at http://localhost:8080
```

**If just slow:** Wait 3-5 minutes and watch:
```bash
kubectl get svc gitops-service -n default --watch
```

---

## 6. Public IP Count Limit Reached

### Error Message
```
Cannot create more than 3 public IP addresses for this subscription in this region.
PublicIPCountLimitReached
```

### Phase
Phase 4 — Exposing the Application

### Root Cause
Azure Student subscription has a limit of **3 public IP addresses per region**. Multiple clusters and LoadBalancer services were consuming all available IPs.

### How to Diagnose
```bash
az network public-ip list \
  --output table \
  --query "[].{Name:name,IP:ipAddress,ResourceGroup:resourceGroup}"
```

### Solution
**Option A — Free up IPs by deleting unused clusters:**
```bash
# Delete old observability cluster if not needed
az aks delete \
  --resource-group observability-rg \
  --name observability-aks \
  --yes
```

**Option B — Use port-forward (no public IP needed):**
```bash
# For app
kubectl port-forward svc/gitops-service -n default 8080:80

# For ArgoCD
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Lesson Learned
Azure Student subscription has strict resource limits. Always clean up unused clusters and services to free IP quota. Port-forwarding is a valid alternative for learning projects.

---

## 7. BUILD_NUMBER Not Updating on Web Page

### Symptom
Web page always shows the same build number regardless of how many times the pipeline runs.

### Phase
Phase B — GitHub Actions + Flask App

### Root Cause
Two bugs found simultaneously:

**Bug 1 — Typo in environment variable name:**
```yaml
# Wrong
- name: APP_VRERSION   ← extra R
  value: "1.0.0"

# Correct
- name: APP_VERSION
  value: "1.0.0"
```

**Bug 2 — Spacing mismatch in sed command:**
The GitHub Actions `sed` command searched for `"1"  # BUILD` (two spaces) but `deployment.yaml` had `"1" # BUILD` (one space). The pattern never matched so the value was never updated.

```yaml
# Wrong (one space)
value: "1" # BUILD

# Correct (two spaces — must match sed pattern exactly)
value: "1"  # BUILD
```

### Solution
Fix both lines in `k8s/deployment.yaml`:
```yaml
env:
- name: APP_VERSION        # Fix typo
  value: "1.0.0"
- name: BUILD_NUMBER
  value: "1"  # BUILD      # Fix spacing (two spaces before #)
```

### Lesson Learned
`sed` pattern matching is exact — spacing matters. Always verify your sed patterns match the exact format in your files. Test sed commands locally before putting them in CI/CD pipelines.

---

## 8. GitHub Webhook — HTTP 307 Redirect

### Error
```
Response 307
Request URL: http://172.210.88.64/api/webhook
```

### Phase
Webhook Setup

### Root Cause
ArgoCD automatically redirects all HTTP requests to HTTPS. The webhook was configured with `http://` instead of `https://`.

### Solution
Update webhook Payload URL from:
```
http://172.210.88.64/api/webhook
```
to:
```
https://172.210.88.64/api/webhook
```

Also disable SSL verification in GitHub webhook settings since ArgoCD uses a self-signed certificate.

### Lesson Learned
ArgoCD enforces HTTPS by default. Always use `https://` in webhook URLs. Disable SSL verification for self-signed certificates in learning environments.

---

## 9. GitHub Webhook — HTTP 400 Bad Request

### Error
```
Response 400
"msg":"Webhook processing failed: missing X-Hub-Signature-256 Header"
```

### Phase
Webhook Setup

### Root Cause
ArgoCD had an old webhook secret stored internally from a previous configuration. When GitHub sent requests without a signature (after secret was cleared from GitHub side), ArgoCD rejected them because it was still expecting a signed request.

Additionally, redelivering old ping events resent the original signatures — creating a mismatch.

### How to Diagnose
```bash
kubectl logs deployment/argocd-server \
  -n argocd --tail=50 | grep -i webhook
```

### Solution

**Step 1 — Clear secret from ArgoCD:**
```bash
kubectl patch secret argocd-secret \
  -n argocd \
  --type json \
  -p='[{"op": "remove", "path": "/data/webhook.github.secret"}]'
```

**Step 2 — Restart ArgoCD server:**
```bash
kubectl rollout restart deployment/argocd-server -n argocd
kubectl rollout status deployment/argocd-server -n argocd
```

**Step 3 — Delete old webhook on GitHub and create fresh one** (without secret field)

**Step 4 — Test with real push** (not ping redelivery — redelivery resends old signatures)

### Important Note
ArgoCD returns `400` for GitHub `ping` events by design — it only processes `push` events. A `400` on ping does not mean the webhook is broken. Test with a real git push to confirm.

### Lesson Learned
When troubleshooting webhooks, always test with a real push event — not a ping redelivery. Old ping redeliveries carry original signatures that may no longer be valid.

---

## 10. ArgoCD Not Auto-Syncing

### Symptom
ArgoCD only syncs when the Refresh button is clicked manually. Changes pushed to GitHub are not automatically deployed even after waiting several minutes.

### Phase
Phase 5 — Testing GitOps Loop

### Root Cause
Two separate issues:

**Issue A — Webhook not configured:** Without webhook, ArgoCD polls GitHub every 3 minutes. If you check immediately after pushing, sync hasn't happened yet.

**Issue B — Old webhook secret in ArgoCD:** Even after clearing secret on GitHub side, ArgoCD kept rejecting webhook calls because it still had the secret stored internally. This prevented webhook notifications from reaching ArgoCD.

### How to Diagnose
```bash
# Check sync policy is configured
kubectl get application nginx-gitops-app \
  -n argocd -o yaml | grep -A5 syncPolicy

# Check ArgoCD server logs for webhook errors
kubectl logs deployment/argocd-server \
  -n argocd --tail=50 | grep webhook
```

### Solution
Fix webhook configuration (see Issue 9) and ensure `argocd-app.yaml` has auto-sync enabled:

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  syncOptions:
  - CreateNamespace=true
```

### Lesson Learned
Auto-sync via polling (3 min interval) is normal ArgoCD behavior. Webhooks reduce this to near-instant sync. Both are valid — webhooks are preferred for production environments.

---

## Summary Table

| # | Problem | Root Cause | Fix |
|---|---------|-----------|-----|
| 1 | ArgoCD auth error | Private repo / wrong URL | Make repo public |
| 2 | Actions not triggering | Path filter too restrictive | Remove/expand path filter |
| 3 | No nodes found | Stale kubectl credentials | Re-pull credentials |
| 4 | MC_ resource group missing | Cluster corrupted | Delete and recreate cluster |
| 5 | EXTERNAL-IP pending | IP limit / stale credentials | Port-forward or free IPs |
| 6 | IP limit reached | Student subscription quota | Delete unused resources |
| 7 | Build number not updating | Typo + spacing mismatch in sed | Fix env var name and spacing |
| 8 | Webhook 307 redirect | Using http instead of https | Change to https:// |
| 9 | Webhook 400 bad request | Old secret in ArgoCD | Clear ArgoCD secret, restart |
| 10 | ArgoCD not auto-syncing | Webhook blocked by secret mismatch | Fix webhook + verify syncPolicy |
