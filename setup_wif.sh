
GCP_PROJECT_ID="akkie-dev"
GITHUB_REPO="dakimura/cdci-example"
# PoolとProviderの名前は任意ですが、分かりやすく github-pool/github-provider とします
WIF_POOL_NAME="runway-github-pool"
WIF_PROVIDER_NAME="runway-github-provider"
SERVICE_ACCOUNT_NAME="runway-github-actions-sa"
ARTIFACT_REGISTRY_NAME="runway-docker-repo"
ARTIFACT_REGISTRY_LOCATION="asia-northeast1"
CLOUDRUN_SA_NAME="example-app"

# Create Artifact Registry
if [[ $(gcloud artifacts repositories list --project=${GCP_PROJECT_ID} --filter="name:${ARTIFACT_REGISTRY_NAME}") ]]; then
  echo "Artifact Registry already exists. skipping..."
else
  gcloud artifacts repositories create ${ARTIFACT_REGISTRY_NAME} \
      --repository-format=docker \
      --location=${ARTIFACT_REGISTRY_LOCATION} \
      --project=${GCP_PROJECT_ID}
fi

# Check if Workload Identity Pool exists
if [[ $(gcloud iam workload-identity-pools list --location=global --filter=name:${WIF_POOL_NAME} --format='value(name)') ]]; then
    echo "Workload Identity Pool ${WIF_POOL_NAME} already exists. skipping..."
else
    # Create Workload Identity Pool
    gcloud iam workload-identity-pools create "${WIF_POOL_NAME}" \
        --project="${GCP_PROJECT_ID}" \
        --location="global" \
        --display-name="GitHub Actions Pool for Runway" \
        --quiet
fi

# Identity Provider の作成
# create-oidc	OIDC（OpenID Connect）の認証方式を使う窓口を新規作成します。
# --workload-identity-pool どの「プール（枠組み）」の中にこの窓口を作るかを指定
# --attribute-mapping	「GitHubからの情報をGoogle Cloudの属性にどう変換するか」 を定義
# --issuer-uri: 誰が発行した証明書を信じるか
if [[ $(gcloud iam workload-identity-pools providers list --location="global" --workload-identity-pool=${WIF_POOL_NAME}) ]]; then
    echo "Workload Identity provider already exists. skipping..."
else
    gcloud iam workload-identity-pools providers create-oidc "${WIF_PROVIDER_NAME}" \
        --project="${GCP_PROJECT_ID}" \
        --location="global" \
        --workload-identity-pool="${WIF_POOL_NAME}" \
        --display-name="GH Actions Provider for Runway" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --attribute-condition="assertion.repository == '${GITHUB_REPO}'"
fi


# サービスアカウントの作成
if [[ $(gcloud iam service-accounts list --filter="email:${SERVICE_ACCOUNT_NAME}") ]]; then
  echo "Runway service account alraedy exists. skipping..."
else
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
      --project="${GCP_PROJECT_ID}" \
      --display-name="GitHub Actions Service Account for Runway"
fi

# サービスアカウントへの権限付与（Artifact Registry）
gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer" \
    --no-user-output-enabled

# GitHubリポジトリからの偽装（Impersonation）を許可
# Workload Identity Pool のIDを取得
WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe "${WIF_POOL_NAME}" --project="${GCP_PROJECT_ID}" --location="global" --format="value(name)")
echo "WORKLOAD_IDENTITY_POOL_ID=${WORKLOAD_IDENTITY_POOL_ID}"

# Workflow Identity Federationによる認証
gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --project="${GCP_PROJECT_ID}" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${GITHUB_REPO}" \
    --no-user-output-enabled

# Cloud Runをデプロイする権限を与えておく
gcloud projects add-iam-policy-binding "${GCP_PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.admin" \
    --no-user-output-enabled

# Cloud Runを実行するService Accountを作成
if [[ $(gcloud iam service-accounts --project=${GCP_PROJECT_ID} list --filter="email:${SERVICE_ACCOUNT_NAME}") ]];then
  echo "Runway Cloud Run App Execution Service Account already exists. skipping..."
else
  gcloud iam service-accounts create "${CLOUDRUN_SA_NAME}" \
      --project="${GCP_PROJECT_ID}" \
      --display-name="Runway Cloud Run App Execution SA"
fi

# WIFでgithub actionsが使うService Accountに、Cloud Runの実行Service Accountを使ってデプロイするなりすまし権限を付与
gcloud iam service-accounts add-iam-policy-binding "${CLOUDRUN_SA_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --no-user-output-enabled

# GitHub Actions で使うWIF Poolの確認
echo "Workload Identity Provider Name that will be used on Github Actions:"
gcloud iam workload-identity-pools providers describe "${WIF_PROVIDER_NAME}" \
    --project="${GCP_PROJECT_ID}" \
    --location="global" \
    --workload-identity-pool="${WIF_POOL_NAME}" \
    --format="value(name)"

