from flask import Blueprint, request, jsonify
from apptracker_database.database import SessionLocal
from ..app import jwt_required
from apptracker_database.action_dao import ActionDAO

actions_api = Blueprint('actions_api', __name__)

# --- Action CRUD ---
@actions_api.route('/api/actions', methods=['POST'])
@jwt_required
def create_action():
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        action_dao = ActionDAO(db)
        action = action_dao.create_action(
            date_logged=data['date_logged'],
            type=data['type'],
            application_id=data['application_id'],
            message_id=data['message_id']
        )
        return jsonify({'id': action.id}), 201

@actions_api.route('/api/actions/<int:action_id>', methods=['GET'])
@jwt_required
def get_action(action_id):
    with SessionLocal() as db:
        action_dao = ActionDAO(db)
        action = action_dao.get_action(action_id)
    if not action:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': action.id,
        'date_logged': str(action.date_logged),
        'type': action.type.value,
        'application_id': action.application_id,
        'message_id': action.message_id
    })

@actions_api.route('/api/actions', methods=['GET'])
@jwt_required
def search_actions():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        action_dao = ActionDAO(db)
        actions = action_dao.search_actions_by_type(q)
    return jsonify([
        {
        'id': a.id,
        'date_logged': str(a.date_logged),
        'type': a.type.value,
        'application_id': a.application_id,
        'message_id': a.message_id
        } for a in actions
    ])

@actions_api.route('/api/actions/<int:action_id>', methods=['PUT'])
@jwt_required
def update_action(action_id):
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input'}), 400

    update_fields = {}
    for field in ['date_logged', 'type', 'application_id', 'message_id']:
        if field in data:
            update_fields[field] = data[field]

    with SessionLocal() as db:
        action_dao = ActionDAO(db)
        updated_action = action_dao.update_action(action_id, **update_fields)
    if not updated_action:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': updated_action.id})

@actions_api.route('/api/actions/<int:action_id>', methods=['DELETE'])
@jwt_required
def delete_action(action_id):
    with SessionLocal() as db:
        action_dao = ActionDAO(db)
        deleted = action_dao.delete_action(action_id)
    if not deleted:
        return jsonify({'error': 'Not found'}), 404
    return '', 204