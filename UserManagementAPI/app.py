from flask import Flask, redirect, url_for, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import urllib.parse
from authlib.integrations.flask_client import OAuth
from flask_migrate import Migrate, upgrade as flask_migrate_upgrade
from gmail_gateway import GmailGateway
from flask import g
from flask_cors import CORS
import os, json
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://appuser:appuserpassword@mysql:3306/apptracker')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
# login_manager.login_view = 'login'  # Remove or comment out this line to avoid mypy/pyright error

# Authlib OAuth setup
oauth = OAuth(app)
with open(os.path.join(os.path.dirname(__file__), 'google_oauth_secrets.json')) as f:
    google_secrets = json.load(f)['web']

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
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/gmail.readonly'},
)

CORS(app, supports_credentials=True)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    google_access_token = db.Column(db.Text, nullable=True)
    google_refresh_token = db.Column(db.Text, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, username, email, google_id, google_access_token=None, google_refresh_token=None, token_expiry=None):
        self.username = username
        self.email = email
        self.google_id = google_id
        self.google_access_token = google_access_token
        self.google_refresh_token = google_refresh_token
        self.token_expiry = token_expiry

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

JWT_SECRET = os.getenv('JWT_SECRET', 'dev_jwt_secret')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 3600

@app.route('/login')
def login():
    redirect_uri = url_for('authorized', _external=True)
    return google.authorize_redirect(redirect_uri)

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
    user = User.query.filter_by(email=email).first()
    # --- Persist Google tokens to DB ---
    access_token = token.get('access_token')
    refresh_token = token.get('refresh_token')
    expires_at = token.get('expires_at')
    expiry_dt = None
    if expires_at:
        expiry_dt = datetime.datetime.utcfromtimestamp(expires_at)
    if not user:
        user = User(
            username=name,
            email=email,
            google_id=google_id,
            google_access_token=access_token,
            google_refresh_token=refresh_token,
            token_expiry=expiry_dt
        )
        db.session.add(user)
    else:
        user.google_access_token = access_token
        if refresh_token:  # Only update if present (Google may not always send it)
            user.google_refresh_token = refresh_token
        user.token_expiry = expiry_dt
    db.session.commit()
    login_user(user)
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



def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user = User.query.get(payload['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 401
            g.current_user = user
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token', 'details': str(e)}), 401
        return f(*args, **kwargs)
    return decorated

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

@app.route('/api/gmail/messages', methods=['GET'])
@jwt_required
def gmail_messages():
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    # Use the Google access token from the database
    access_token = user.google_access_token
    expiry = user.token_expiry
    now = datetime.datetime.utcnow()
    if not access_token:
        return jsonify({'error': 'No Google access token found. Please log out and log in again.'}), 401
    if expiry and now >= expiry:
        return jsonify({'error': 'Google access token expired. Please log out and log in again.'}), 401
    gateway = GmailGateway(access_token, user_id=user.google_id)
    max_results = int(request.args.get('maxResults', 10))
    page_token = request.args.get('pageToken')
    try:
        result = gateway.list_messages(max_results=max_results, page_token=page_token)
        return jsonify(result.dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
