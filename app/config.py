import os
from dotenv import load_dotenv
from google.oauth2 import service_account

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# GCP credentials – either individual env vars (Vercel) or a JSON key file (local)
GCP_CLIENT_EMAIL = os.getenv("GCP_CLIENT_EMAIL")
GCP_PRIVATE_KEY = os.getenv("GCP_PRIVATE_KEY")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")


def get_google_credentials(scopes: list[str]) -> service_account.Credentials:
    """Build Google service-account credentials.

    Prefers individual env vars (GCP_CLIENT_EMAIL, GCP_PRIVATE_KEY,
    GCP_PROJECT_ID) which work on Vercel.  Falls back to a local JSON
    key file for development.
    """
    if GCP_CLIENT_EMAIL and GCP_PRIVATE_KEY and GCP_PROJECT_ID:
        # Normalise the private key: strip wrapping quotes, convert literal
        # "\n" sequences to real newlines, and trim whitespace.
        pk = GCP_PRIVATE_KEY.strip()
        if pk.startswith('"') and pk.endswith('"'):
            pk = pk[1:-1]
        pk = pk.replace("\\n", "\n")
        info = {
            "type": "service_account",
            "project_id": GCP_PROJECT_ID,
            "client_email": GCP_CLIENT_EMAIL,
            "private_key": pk,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)

    return service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes
    )
