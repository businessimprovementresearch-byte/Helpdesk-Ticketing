"""
Script SEKALI JALAN buat dapetin GMAIL_REFRESH_TOKEN.
Jalanin di komputer kamu sendiri, bukan di server.
Butuh 'client_secret.json' (download dari Google Cloud Console) di folder yang sama.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
creds = flow.run_local_server(port=0)

print("\n=== SUKSES ===")
print("Copy 3 nilai ini ke environment variables di Render:\n")
print(f"GMAIL_CLIENT_ID={creds.client_id}")
print(f"GMAIL_CLIENT_SECRET={creds.client_secret}")
print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
print("\nGMAIL_SENDER_EMAIL = alamat Gmail yang tadi kamu pakai login")