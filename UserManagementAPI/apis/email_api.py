from flask import Blueprint, request, jsonify
from apptracker_database.database import SessionLocal
from ..app import jwt_required
from apptracker_database.email_address_dao import EmailAddressDAO

email_api = Blueprint('email_api', __name__)

# --- EmailAddress CRUD ---
@email_api.route('/api/email_address', methods=['PUT'])
@jwt_required
def upsert_email_address():
    data = request.json or {}
    if data is None:
        return jsonify({'error': 'Invalid input'}), 400
    email_address = data.get('email', '').strip().lower()
    
    if not email_address:
        return jsonify({'error': 'email is required'}), 400

    return_address = _get_email_address_by_string_match(email_address)
    if not return_address:
        return_address = _create_email_address(email_address)

    return jsonify({'id': return_address.id, 'email': return_address.email})

def _create_email_address(email_address):
    with SessionLocal() as db:
        email_address_dao = EmailAddressDAO(db)
        print(f"Creating email address: {email_address} ", flush=True)
        created_email = email_address_dao.create_email_address(email=email_address)
    return created_email


@email_api.route('/api/email_addresses', methods=['POST'])
@jwt_required
def create_email_address():
    data = request.json or {}
    if data is None:
        return jsonify({'error': 'Invalid input'}), 400
    email_address = data.get('email', '').strip().lower()
    company_id = data.get('company_id')
    if not email_address or not company_id:
        return jsonify({'error': 'Email and company_id are required'}), 400

    created_email = _create_email_address(email_address)
    if not created_email:
        return jsonify({'error': 'Failed to create email address'}), 500
    return jsonify({'id': created_email.id, 'email': created_email.email, 'company_id': created_email.company_id}), 201

@email_api.route('/api/email_addresses/<int:email_id>', methods=['GET'])
@jwt_required
def get_email_address(email_id):
    with SessionLocal() as db:
        email_address_dao = EmailAddressDAO(db)
        email_address = email_address_dao.get_by_id(email_id)
    if not email_address:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': email_address.id, 'email': email_address.email, 'company_id': email_address.company_id})

def _get_email_address_by_string_match(email):
    with SessionLocal() as db:
        email_address_dao = EmailAddressDAO(db)
        return email_address_dao.get_by_email(email)

@email_api.route('/api/email_address', methods=['GET'])
@jwt_required
def get_email_address_by_address():
    q = request.args.get('q', '')
    email_address = _get_email_address_by_string_match(q)
    if not email_address:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': email_address.id, 'email': email_address.email})

@email_api.route('/api/email_addresses/<int:email_id>', methods=['PUT'])
@jwt_required
def update_email_address(email_id):
    data = request.json or {}
    with SessionLocal() as db:
        email_address_dao = EmailAddressDAO(db)
        update_fields = {}
        if 'email' in data:
            update_fields['email'] = data['email']
        if 'company_id' in data:
            update_fields['company_id'] = data['company_id']
        updated_email = email_address_dao.update(email_id, **update_fields)
        if not updated_email:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'id': updated_email.id, 'email': updated_email.email, 'company_id': updated_email.company_id})

@email_api.route('/api/email_addresses/<int:email_id>', methods=['DELETE'])
@jwt_required
def delete_email_address(email_id):
    with SessionLocal() as db:
        email_address_dao = EmailAddressDAO(db)
        deleted = email_address_dao.delete(email_id)
        if not deleted:
            return jsonify({'error': 'Not found'}), 404
        return '', 204
