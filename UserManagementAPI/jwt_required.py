import os
from flask import request, jsonify
import jwt
from .user import AppUser
from functools import wraps
from flask import g
from apptracker_database.user_dao import UserDAO
from apptracker_database.database import SessionLocal

JWT_SECRET = os.getenv('JWT_SECRET', 'dev_jwt_secret')
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 3600

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            with SessionLocal() as db:
                userDAO = UserDAO(db)
                user = userDAO.get_user_by_id(payload['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 401
            g.current_user = user
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token', 'details': str(e)}), 401
        return f(*args, **kwargs)
    return decorated