from google.cloud import firestore
from google.cloud import kms
import base64

PROJECT_ID = "akkie-dev"
KMS_LOCATION = "us-central1"
KMS_KEYRING = "example-agent-kr"
KMS_KEY = "example-agent-key"

def _kms_key_name(project_id: str = PROJECT_ID,
                  location: str = KMS_LOCATION,
                  key_ring: str = KMS_KEYRING,
                  key: str = KMS_KEY) -> str:
    return (
        f"projects/{project_id}/locations/{location}/keyRings/{key_ring}/cryptoKeys/{key}"
    )


def encrypt_token_with_kms(plain_text: str,
                           project_id: str = PROJECT_ID) -> str:
    """KMSで暗号化してbase64文字列を返す"""
    client = kms.KeyManagementServiceClient()
    name = _kms_key_name(project_id=project_id)
    resp = client.encrypt(request={
        "name": name,
        "plaintext": plain_text.encode("utf-8"),
    })
    # ciphertext は bytes
    return base64.b64encode(resp.ciphertext).decode("utf-8")


def decrypt_token_with_kms(cipher_b64: str,
                           project_id: str = PROJECT_ID) -> str:
    """KMSで復号してプレーンテキストを返す"""
    client = kms.KeyManagementServiceClient()
    name = _kms_key_name(project_id=project_id)
    ciphertext = base64.b64decode(cipher_b64)
    resp = client.decrypt(request={
        "name": name,
        "ciphertext": ciphertext,
    })
    return resp.plaintext.decode("utf-8")


def save_user_token(user_id: str, token: str, database: str, project_id: str = PROJECT_ID):
    # KMSで暗号化 + 保存（nonceは不要）
    cipher_b64 = encrypt_token_with_kms(token, project_id=project_id)

    db = firestore.Client(database=database, project=project_id)
    doc_ref = db.collection("auth_tokens").document(user_id)
    doc_ref.set({"cipher": cipher_b64})

    print(f"Saved encrypted token for {user_id}")

def load_user_token(user_id: str, database: str, project_id: str = PROJECT_ID):
    # 読み込み + KMSで復号

    db = firestore.Client(database=database, project=project_id)
    doc = db.collection("auth_tokens").document(user_id).get()

    if not doc.exists:
        print("Token not found")
        return None

    data = doc.to_dict()

    plain_token = decrypt_token_with_kms(data["cipher"], project_id=project_id)

    return plain_token


if __name__ == "__main__":
    USER_ID = "user_123"
    TOKEN = "xoxp-1234567890-your-slack-token"
    service_name = "example-agent"
    project_id="akkie-dev"

    save_user_token(USER_ID, TOKEN, database=service_name, project_id=project_id)

    loaded = load_user_token(USER_ID, database=service_name, project_id=project_id)
    print("Loaded token:", loaded)
