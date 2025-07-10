import datetime
from flask import Blueprint, request, jsonify, current_app
from flask import g
import os

# Shared Imports
from apptracker_shared.gmail.gmail_gateway import GmailGateway

# Local Imports
from ..jwt_required import jwt_required

gmail_api = Blueprint('gmail_api', __name__)

google_secrets = {
    'client_id': os.getenv('GOOGLE_CLIENT_ID'),
    'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'redirect_uris': ['http://localhost:5000/oauth2callback'],
}


def is_token_expired(expiry):
    return expiry and datetime.datetime.utcnow() >= expiry

@gmail_api.route('/messages', methods=['GET'])
@jwt_required
def gmail_messages():
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    access_token = user.google_access_token
    refresh_token = user.google_refresh_token
    expiry = user.token_expiry
    if not access_token:
        return jsonify({'error': 'No Google access token found. Please log out and log in again.'}), 401
    if is_token_expired(expiry):
        return jsonify({'error': 'Google access token expired. Please log out and log in again.'}), 401

    try:
        max_results = min(int(request.args.get('maxResults', 10)), 100)
    except ValueError:
        return jsonify({'error': 'Invalid maxResults parameter'}), 400

    page_token = request.args.get('pageToken')
    search_query = request.args.get('q')  # <-- passed in from frontend

    gateway = GmailGateway(access_token, refresh_token, user_id=user.google_id)

    try:
        result = gateway.list_messages(
            max_results=max_results,
            page_token=page_token,
            query=search_query
        )
        return jsonify(result.dict())
    except Exception as e:
        current_app.logger.exception("Failed to fetch Gmail messages")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500