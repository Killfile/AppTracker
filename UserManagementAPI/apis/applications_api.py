from flask import Blueprint, request, jsonify, g
from apptracker_database.database import SessionLocal
from ..app import jwt_required
from apptracker_database.application_dao import ApplicationDAO

applications_api = Blueprint('applications_api', __name__)

# --- Application CRUD ---
@applications_api.route('/api/applications', methods=['POST'])
@jwt_required
def create_application():
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        application_dao = ApplicationDAO(db)
        application = application_dao.create_application(
            title=data['title'],
            date_applied=data['date_applied'],
            company_id=data['company_id'],
            user_id=g.current_user.id
        )
        return jsonify({'id': application.id}), 201

@applications_api.route('/api/applications/<int:app_id>', methods=['GET'])
@jwt_required
def get_application(app_id):
    with SessionLocal() as db:
        application_dao = ApplicationDAO(db)
        app = application_dao.get_application(app_id)
        if not app:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'id': app.id, 'title': app.title, 'date_applied': str(app.date_applied), 'company_id': app.company_id, 'user_id': app.user_id})

@applications_api.route('/api/applications', methods=['GET'])
@jwt_required
def search_applications():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        application_dao = ApplicationDAO(db)
        apps = application_dao.search_applications_by_title(q)
        return jsonify([{'id': a.id, 'title': a.title, 'date_applied': str(a.date_applied), 'company_id': a.company_id, 'user_id': a.user_id} for a in apps])

@applications_api.route('/api/applications/<int:app_id>', methods=['PUT'])
@jwt_required
def update_application(app_id):
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    
    update_fields = {}
    if 'title' in data:
        update_fields['title'] = data['title']
    if 'date_applied' in data:
        update_fields['date_applied'] = data['date_applied']
    if 'company_id' in data:
        update_fields['company_id'] = data['company_id']
    
    with SessionLocal() as db:
        application_dao = ApplicationDAO(db)    
        updated_app = application_dao.update_application(app_id, **update_fields)
        if not updated_app:
            return jsonify({'error': 'Not found'}), 404

        return jsonify({'id': updated_app.id})

@applications_api.route('/api/applications/<int:app_id>', methods=['DELETE'])
@jwt_required
def delete_application(app_id):
    with SessionLocal() as db:
        application_dao = ApplicationDAO(db)
        app = application_dao.get_application(app_id)
        if not app:
            return jsonify({'error': 'Not found'}), 404
        application_dao.delete_application(app_id)
        return '', 204