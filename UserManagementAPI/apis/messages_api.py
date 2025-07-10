from flask import Blueprint, request, jsonify, g
from apptracker_database.database import SessionLocal
from ..app import jwt_required
from apptracker_database.message_dao import MessageDAO

messages_api = Blueprint('messages_api', __name__)

# --- Message CRUD ---
@messages_api.route('/api/messages/upsert', methods=['PUT'])
@jwt_required
def upsert_message():
    data = request.json
    if data is None or 'gmail_message_id' not in data:
        return jsonify({'error': 'Missing gmail_message_id or invalid input'}), 400

    gmail_message_id = data['gmail_message_id']
    with SessionLocal() as db:
        message_dao = MessageDAO(db)
        msg = message_dao.get_by_gmail_id(gmail_message_id)
        if msg:
            # Update existing message
            update_fields = {}
            for field in ['subject', 'date_received', 'message_body', 'company_id', 'email_address_id']:
                if field in data:
                    update_fields[field] = data[field]
            updated_msg = message_dao.update_message(msg.id, **update_fields)
            return jsonify({'id': updated_msg.id, 'action': 'updated'}), 200
        else:
            # Create new message
            new_msg = message_dao.create_message(
                subject=data.get('subject'),
                date_received=data.get('date_received'),
                message_body=data.get('message_body'),
                gmail_message_id=gmail_message_id,
                user_id=g.current_user.id,
                company_id=data.get('company_id'),
                email_address_id=data.get('email_address_id')
            )
            return jsonify({'id': new_msg.id, 'action': 'created'}), 201


@messages_api.route('/api/messages', methods=['POST'])
@jwt_required
def create_message():
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        message_dao = MessageDAO(db)
        msg = message_dao.create_message(
            subject=data['subject'],
            date_received=data['date_received'],
            message_body=data['message_body'],
            gmail_message_id=data.get('gmail_message_id'),
            user_id=g.current_user.id,
            company_id=data.get('company_id'),
            email_address_id=data['email_address_id']
        )
        return jsonify({'id': msg.id}), 201

def _get_message_by_gmail_id(gmail_id):
    with SessionLocal() as db:
        message_dao = MessageDAO(db)
        msg = message_dao.get_by_gmail_id(gmail_id)
    return msg

@messages_api.route('/api/messages/gmail/<string:gmail_id>', methods=['GET'])
@jwt_required
def get_message_by_gmail_id(gmail_id):
    msg = _get_message_by_gmail_id(gmail_id)
    if not msg:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': msg.id,
        'subject': msg.subject,
        'date_received': str(msg.date_received),
        'message_body': msg.message_body,
        'gmail_message_id': msg.gmail_message_id,
        'user_id': msg.user_id,
        'company_id': msg.company_id,
        'email_address_id': msg.email_address_id
    })

@messages_api.route('/api/messages/<int:msg_id>', methods=['GET'])
@jwt_required
def get_message(msg_id):
    with SessionLocal() as db:
        message_dao = MessageDAO(db)
        msg = message_dao.get_by_id(msg_id)
        if not msg:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({
            'id': msg.id,
            'subject': msg.subject,
            'date_received': str(msg.date_received),
            'message_body': msg.message_body,
            'gmail_message_id': msg.gmail_message_id,
            'user_id': msg.user_id,
            'company_id': msg.company_id,
            'email_address_id': msg.email_address_id
        })

@messages_api.route('/api/messages', methods=['GET'])
@jwt_required
def search_messages():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        message_dao = MessageDAO(db)
        msgs = message_dao.search_messages(q)
        return jsonify([
            {
                'id': m.id,
                'subject': m.subject,
                'date_received': str(m.date_received),
                'message_body': m.message_body,
                'gmail_message_id': m.gmail_message_id,
                'user_id': m.user_id,
                'company_id': m.company_id,
                'email_address_id': m.email_address_id
            }
            for m in msgs
        ])

@messages_api.route('/api/messages/<int:msg_id>', methods=['PUT'])
@jwt_required
def update_message(msg_id):
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    update_fields = {}
    for field in ['subject', 'date_received', 'message_body', 'gmail_message_id', 'company_id', 'email_address_id']:
        if field in data:
            update_fields[field] = data[field]
    with SessionLocal() as db:
        message_dao = MessageDAO(db)
        updated_msg = message_dao.update_message(msg_id, **update_fields)
        if not updated_msg:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'id': updated_msg.id})

@messages_api.route('/api/messages/<int:msg_id>', methods=['DELETE'])
@jwt_required
def delete_message(msg_id):
    with SessionLocal() as db:
        message_dao = MessageDAO(db)
        if not message_dao.delete_message(msg_id):
            return jsonify({'error': 'Not found'}), 404
        return '', 204