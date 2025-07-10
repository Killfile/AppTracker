from flask import Flask, redirect, url_for, session, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import urllib.parse
from authlib.integrations.flask_client import OAuth
from flask_migrate import Migrate, upgrade as flask_migrate_upgrade
from flask import g
from flask_cors import CORS
import os, json
import jwt
import datetime

# Shared Imports
from apptracker_database.database import SessionLocal
from apptracker_database.migrations_runner import run_migrations
from apptracker_shared.gmail.gmail_gateway import GmailGateway
from apptracker_database.user_dao import UserDAO
from apptracker_database.models import User

# Local Imports
from .jwt_required import JWT_ALGORITHM, JWT_EXP_DELTA_SECONDS, JWT_SECRET, jwt_required
from .user import AppUser
from .apis.company_api import company_api
from .apis.actions_api import actions_api
from .apis.applications_api import applications_api
from .apis.email_api import email_api
from .apis.messages_api import messages_api
from .email_browser.gmail_api import gmail_api




app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://appuser:appuserpassword@mysql:3306/apptracker')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.register_blueprint(company_api)
app.register_blueprint(actions_api)
app.register_blueprint(applications_api)
app.register_blueprint(email_api)
app.register_blueprint(messages_api)
app.register_blueprint(gmail_api, url_prefix='/gmail')

google_secrets = {
    'client_id': os.getenv('GOOGLE_CLIENT_ID'),
    'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'redirect_uris': ['http://localhost:5000/oauth2callback'],
}

with app.app_context():
    run_migrations()

login_manager = LoginManager(app)
# login_manager.login_view = 'login'  # Remove or comment out this line to avoid mypy/pyright error

# Authlib OAuth setup
oauth = OAuth(app)
with open(os.path.join(os.path.dirname(__file__), 'google_oauth_secrets.json')) as f:
    google_secrets = json.load(f)['web']

scopes = [
    'openid',
    'email',
    'profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    "https://www.googleapis.com/auth/gmail.labels"
]

google = oauth.register(
    name='google',
    client_id=google_secrets['client_id'],
    client_secret=google_secrets['client_secret'],
    access_token_url=google_secrets['token_uri'],
    access_token_params=None,
    authorize_url=google_secrets['auth_uri'],
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://www.googleapis.com/oauth2/v1/userinfo',
    server_metadata_url= 'https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': ' '.join(scopes)},
)

CORS(app, supports_credentials=True)



@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))

@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri, access_type='offline', prompt='consent') # Offline and Consent request the refresh token

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/signup')
def signup():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/oauth2callback')
def authorized():
    print("Authorization callback received", flush=True)
    try:
        token = google.authorize_access_token()
        print(f"Token received: {token}", flush=True)
    except Exception as e:
        print(f"Error during authorization: {e}", flush=True)
        return jsonify({'error': 'Authorization failed'}), 500
    
    resp = google.get('userinfo')
    info = resp.json()
    email = info.get('email')
    name = info.get('name', email)
    google_id = info.get('id')

    # --- Persist Google tokens to DB ---
    access_token = token.get('access_token')
    refresh_token = token.get('refresh_token')
    expires_at = token.get('expires_at')
    expiry_dt = None

    if expires_at:
        expiry_dt = datetime.datetime.utcfromtimestamp(expires_at)

    with SessionLocal() as db:
        user = db.query(User).filter_by(email=email).first()
        # If user doesn't exist, create a new one
        if not user:
            user = User(
                username=name,
                email=email,
                google_id=google_id,
                google_access_token=access_token,
                google_refresh_token=refresh_token,
                token_expiry=expiry_dt
            )
            db.add(user)
        else:
            user.google_access_token = access_token
            if refresh_token:  # Only update if present (Google may not always send it)
                user.google_refresh_token = refresh_token
            user.token_expiry = expiry_dt
        db.commit()

        # Possibly not necessary
        login_user(AppUser(user))

    # Store access token in session for Gmail API use
    session['google_token'] = token

    # Issue JWT for the client
    payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    jwt_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Instead of redirect, return JWT to frontend (for SPA)
    user_info = urllib.parse.quote(json.dumps({
    'id': user.id,
    'username': user.username,
    'email': user.email
    }))
    
    # Redirect to frontend with JWT and user info in query params
    return redirect(f'http://localhost:3000/?jwt={jwt_token}&user={user_info}')


@app.route('/users', methods=['GET'])
@jwt_required
def get_users():
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify({'users': [{'id': user.id, 'username': user.username, 'email': user.email}]})

@app.route('/landing')
@login_required
def landing():
    return f"Welcome, {current_user.username}! This is the landing page."

# --- Auto-apply migrations on startup ---
def run_migrations():
    try:
        flask_migrate_upgrade()
        print("Database migrations applied successfully.", flush=True)
    except Exception as e:
        print(f"Error applying migrations: {e}", flush=True)


if __name__ == '__main__':
    run_migrations()
    app.run(host='0.0.0.0', port=5000, debug=True)
