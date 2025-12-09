# This script is idempotent - it can be safely executed multiple times without changing the end result.
#
# ===== Config =====
PROJECT_ID="akkie-dev"
SERVICE_NAME="example-agent"
REGION="us-central1"
# ==================
CLOUDRUN_SA_EMAIL="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KMS_KEYRING="${SERVICE_NAME}-kr"
KMS_KEY="${SERVICE_NAME}-key"

set -x
# ==== Fail if gcloud command is not installed
if ! command -v gcloud &> /dev/null; then
    echo "gcloud command is not installed. Please install it first. ref:https://docs.cloud.google.com/sdk/docs/install"
    exit 1
fi
# ===== Cloud KMS setup (preferred over storing keys in Secret Manager) =====
# Create KeyRing if it doesn't exist
if ! gcloud kms keyrings describe ${KMS_KEYRING} --location=${REGION} --project=${PROJECT_ID} >/dev/null 2>&1; then
  gcloud kms keyrings create ${KMS_KEYRING} --location=${REGION} --project=${PROJECT_ID}
fi

# Create symmetric encryption key if it doesn't exist
if ! gcloud kms keys describe ${KMS_KEY} --keyring=${KMS_KEYRING} --location=${REGION} --project=${PROJECT_ID} >/dev/null 2>&1; then
  gcloud kms keys create ${KMS_KEY} \
    --keyring=${KMS_KEYRING} \
    --location=${REGION} \
    --purpose="encryption" \
    --project=${PROJECT_ID}
fi

# Grant Cloud Run service account encrypt/decrypt permissions on the key
gcloud kms keys add-iam-policy-binding ${KMS_KEY} \
  --keyring=${KMS_KEYRING} \
  --location=${REGION} \
  --member="serviceAccount:${CLOUDRUN_SA_EMAIL}" \
  --role="roles/cloudkms.cryptoKeyEncrypterDecrypter" \
  --project=${PROJECT_ID}

# Firestore read/write permission
gcloud projects add-iam-policy-binding ${PROJECT_ID} --member="serviceAccount:$CLOUDRUN_SA_EMAIL" --role="roles/datastore.user"

# Create Firestore
# databaseが存在しない場合のみ作成
if ! gcloud firestore databases describe --project=${PROJECT_ID} --database=${SERVICE_NAME} 2>/dev/null; then
  gcloud firestore databases create --project=${PROJECT_ID} --database="${SERVICE_NAME}" --location=${REGION} --type=firestore-native
fi
set +x