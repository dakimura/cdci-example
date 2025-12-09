import json
from typing import Optional, Dict

import requests
import streamlit as st
from google.cloud import secretmanager
from streamlit_oauth import OAuth2Component
import logging
import os

logger = logging.getLogger(__name__)

st.set_page_config(page_title="OAuth Token Helper", layout="centered")
st.title("🔍OAuth Token Helper")
st.write("This tool helps you get your OAuth tokens.")

service_name = "get-oauth-tokens"
gcp_account_number = 333548032969 # kouzoh-ai-tf-enablers-dev
region = "us-central1"
if os.getenv("K_SERVICE"):
    # On Cloud Run
    redirect_uri = f"https://{service_name}-{str(gcp_account_number)}.{region}.run.app"
else:
    # On localhost
    redirect_uri = "https://127.0.0.1:12345"

@st.cache_data
def get_slack_credentials() -> tuple[str, str]:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/kouzoh-ai-tf-enablers-dev/secrets/akkie-slack-client/versions/latest"
    response = client.access_secret_version(request={"name": name})
    d = json.loads(response.payload.data.decode("UTF-8"))
    return d["client_id"], d["client_secret"]


def setup_slack_oauth(client_id, client_secret):
    return OAuth2Component(
        client_id=client_id,
        client_secret=client_secret,
        authorize_endpoint="https://slack.com/oauth/v2/authorize",
        token_endpoint="https://slack.com/api/oauth.v2.access",
    )

@st.cache_data
def get_google_credentials() -> tuple[str, str]:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/kouzoh-ai-tf-enablers-dev/secrets/akkie-google-client/versions/latest"
    response = client.access_secret_version(request={"name": name})
    d = json.loads(response.payload.data.decode("UTF-8"))
    return d["web"]["client_id"], d["web"]["client_secret"]


def setup_google_oauth(client_id, client_secret):
    return OAuth2Component(
        client_id=client_id,
        client_secret=client_secret,
        authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
    )


slack_client_id, slack_client_secret = get_slack_credentials()
google_client_id, google_client_secret = get_google_credentials()

slack_oauth = setup_slack_oauth(slack_client_id, slack_client_secret)

google_oauth = setup_google_oauth(google_client_id, google_client_secret)

# 認証ボタン表示
slack_user_scope = st.text_input(label="Slack token's user_scope", value="search:read,channels:history,groups:history,im:history,users:read,users:read.email,channels:read,groups:read,mpim:read,im:read")
slack_token = slack_oauth.authorize_button("Get Slack user token", redirect_uri=redirect_uri, scope="",extras_params={"user_scope": slack_user_scope}) # @formatter:off
google_scope = st.text_input(label="Google token's scope", value="email https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/admin.directory.resource.calendar.readonly https://www.googleapis.com/auth/admin.directory.customer.readonly")
google_token = google_oauth.authorize_button("Get Google access token & refresh token",
                                             redirect_uri=redirect_uri,
                                             scope=google_scope,
                                             extras_params={
                                                 "access_type": "offline", # "offline" を指定すると refresh_token（長期利用トークン） が発行され、アプリはユーザー不在でもAPIを呼び出せます。
                                                 # "consent": 毎回同意画面を表示
                                                 # "select_account": Googleアカウント選択画面を表示
                                                 # "none": 既に認可済みなら画面を出さずに即リダイレクト
                                                 "prompt": "consent", #
                                             }) # @formatter:off

if slack_token:
    try:
        slack_access_token = slack_token["token"]["authed_user"]["access_token"]
        st.success(f"Slack user token: {slack_access_token}")
        st.write("API response")
        st.write(slack_token)
    except KeyError as e:
        st.warning(e)
        st.error("⚠ failed to get Slack User Token.")


def refresh_google_access_token(client_id:str, client_secret:str, refresh_token: str) -> Optional[Dict]:
    """Use refresh_token to obtain a new Google access token."""
    try:
        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        resp = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=10)
        if resp.status_code == 200:
            payload = resp.json()
            if "access_token" in payload:
                return payload["access_token"]
            else:
                logger.error(f"Google refresh response missing access_token: {payload}")
        else:
            logger.error(f"Google refresh failed: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.exception(f"Exception refreshing Google access token: {e}")
    return None

if google_token:
    try:
        google_access_token = google_token["token"]["access_token"]
        st.success(f"Google access token(will expire in an hour): {google_access_token}")
        google_refresh_token = google_token["token"]["refresh_token"]
        st.success(f"Google refresh token: {google_refresh_token}")
        google_access_token = refresh_google_access_token(client_id=google_client_id, client_secret=google_client_secret,
                                                          refresh_token=google_token["token"]["refresh_token"])
        st.write("API response")
        st.write(google_token)
        st.info("To refresh access token, you need client ID and secret. If you’d like to know the values, please contact @akkie. Of course, it’s recommended that you create your own client instead.")

    except KeyError as e:
        st.warning(e)
        st.error("⚠ failed to get Google User Token.")


# streamlit run --server.address=127.0.0.1 --server.port=3000 --server.headless=true streamlit_app.py