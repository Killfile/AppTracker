from flask import Blueprint, request, jsonify, g
from apptracker_database.models import Application, Action, Message, Company, EmailAddress
from apptracker_database.database import SessionLocal
from sqlalchemy.orm import joinedload
from sqlalchemy import func, or_
from .app import jwt_required

api = Blueprint('api', __name__)

# --- Company CRUD ---
@api.route('/api/companies', methods=['POST'])
@jwt_required
def create_company():
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        company = Company(name=data['name'])
        db.add(company)
        db.commit()
        return jsonify({'id': company.id, 'name': company.name}), 201

@api.route('/api/companies/<int:company_id>', methods=['GET'])
@jwt_required
def get_company(company_id):
    with SessionLocal() as db:
        company = db.query(Company).get(company_id)
        if not company:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'id': company.id, 'name': company.name})

@api.route('/api/companies', methods=['GET'])
@jwt_required
def search_companies():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        query = db.query(Company)
        if q:
            query = query.filter(Company.name.ilike(f'%{q}%'))
        companies = query.all()
        return jsonify([{'id': c.id, 'name': c.name} for c in companies])

@api.route('/api/companies/<int:company_id>', methods=['PUT'])
@jwt_required
def update_company(company_id):
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        company = db.query(Company).get(company_id)
        if not company:
            return jsonify({'error': 'Not found'}), 404
        company.name = data.get('name', company.name)
        db.commit()
        return jsonify({'id': company.id, 'name': company.name})

@api.route('/api/companies/<int:company_id>', methods=['DELETE'])
@jwt_required
def delete_company(company_id):
    with SessionLocal() as db:
        company = db.query(Company).get(company_id)
        if not company:
            return jsonify({'error': 'Not found'}), 404
        db.delete(company)
        db.commit()
        return '', 204

# --- Application CRUD ---
@api.route('/api/applications', methods=['POST'])
@jwt_required
def create_application():
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        app = Application(
            title=data['title'],
            date_applied=data['date_applied'],
            company_id=data['company_id'],
            user_id=g.current_user.id
        )
        db.add(app)
        db.commit()
        return jsonify({'id': app.id}), 201

@api.route('/api/applications/<int:app_id>', methods=['GET'])
@jwt_required
def get_application(app_id):
    with SessionLocal() as db:
        app = db.query(Application).get(app_id)
        if not app:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'id': app.id, 'title': app.title, 'date_applied': str(app.date_applied), 'company_id': app.company_id, 'user_id': app.user_id})

@api.route('/api/applications', methods=['GET'])
@jwt_required
def search_applications():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        query = db.query(Application)
        if q:
            query = query.filter(Application.title.ilike(f'%{q}%'))
        apps = query.all()
        return jsonify([{'id': a.id, 'title': a.title, 'date_applied': str(a.date_applied), 'company_id': a.company_id, 'user_id': a.user_id} for a in apps])

@api.route('/api/applications/<int:app_id>', methods=['PUT'])
@jwt_required
def update_application(app_id):
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        app = db.query(Application).get(app_id)
        if not app:
            return jsonify({'error': 'Not found'}), 404
        app.title = data.get('title', app.title)
        app.date_applied = data.get('date_applied', app.date_applied)
        app.company_id = data.get('company_id', app.company_id)
        db.commit()
        return jsonify({'id': app.id})

@api.route('/api/applications/<int:app_id>', methods=['DELETE'])
@jwt_required
def delete_application(app_id):
    with SessionLocal() as db:
        app = db.query(Application).get(app_id)
        if not app:
            return jsonify({'error': 'Not found'}), 404
        db.delete(app)
        db.commit()
        return '', 204

# --- Message CRUD ---
@api.route('/api/messages', methods=['POST'])
@jwt_required
def create_message():
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        msg = Message(
            subject=data['subject'],
            date_received=data['date_received'],
            message_body=data['message_body'],
            gmail_message_id=data.get('gmail_message_id'),
            user_id=g.current_user.id,
            company_id=data.get('company_id'),
            email_address_id=data['email_address_id']
        )
        db.add(msg)
        db.commit()
        return jsonify({'id': msg.id}), 201

@api.route('/api/messages/<int:msg_id>', methods=['GET'])
@jwt_required
def get_message(msg_id):
    with SessionLocal() as db:
        msg = db.query(Message).get(msg_id)
        if not msg:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'id': msg.id, 'subject': msg.subject, 'date_received': str(msg.date_received), 'message_body': msg.message_body, 'gmail_message_id': msg.gmail_message_id, 'user_id': msg.user_id, 'company_id': msg.company_id, 'email_address_id': msg.email_address_id})

@api.route('/api/messages', methods=['GET'])
@jwt_required
def search_messages():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        query = db.query(Message)
        if q:
            query = query.filter(or_(Message.subject.ilike(f'%{q}%'), Message.message_body.ilike(f'%{q}%')))
        msgs = query.all()
        return jsonify([{'id': m.id, 'subject': m.subject, 'date_received': str(m.date_received), 'message_body': m.message_body, 'gmail_message_id': m.gmail_message_id, 'user_id': m.user_id, 'company_id': m.company_id, 'email_address_id': m.email_address_id} for m in msgs])

@api.route('/api/messages/<int:msg_id>', methods=['PUT'])
@jwt_required
def update_message(msg_id):
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        msg = db.query(Message).get(msg_id)
        if not msg:
            return jsonify({'error': 'Not found'}), 404
        msg.subject = data.get('subject', msg.subject)
        msg.date_received = data.get('date_received', msg.date_received)
        msg.message_body = data.get('message_body', msg.message_body)
        msg.gmail_message_id = data.get('gmail_message_id', msg.gmail_message_id)
        msg.company_id = data.get('company_id', msg.company_id)
        msg.email_address_id = data.get('email_address_id', msg.email_address_id)
        db.commit()
        return jsonify({'id': msg.id})

@api.route('/api/messages/<int:msg_id>', methods=['DELETE'])
@jwt_required
def delete_message(msg_id):
    with SessionLocal() as db:
        msg = db.query(Message).get(msg_id)
        if not msg:
            return jsonify({'error': 'Not found'}), 404
        db.delete(msg)
        db.commit()
        return '', 204

# --- Action CRUD ---
@api.route('/api/actions', methods=['POST'])
@jwt_required
def create_action():
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        action = Action(
            date_logged=data['date_logged'],
            type=data['type'],
            application_id=data['application_id'],
            message_id=data['message_id']
        )
        db.add(action)
        db.commit()
        return jsonify({'id': action.id}), 201

@api.route('/api/actions/<int:action_id>', methods=['GET'])
@jwt_required
def get_action(action_id):
    with SessionLocal() as db:
        action = db.query(Action).get(action_id)
        if not action:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'id': action.id, 'date_logged': str(action.date_logged), 'type': action.type.value, 'application_id': action.application_id, 'message_id': action.message_id})

@api.route('/api/actions', methods=['GET'])
@jwt_required
def search_actions():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        query = db.query(Action)
        if q:
            query = query.filter(Action.type.ilike(f'%{q}%'))
        actions = query.all()
        return jsonify([{'id': a.id, 'date_logged': str(a.date_logged), 'type': a.type.value, 'application_id': a.application_id, 'message_id': a.message_id} for a in actions])

@api.route('/api/actions/<int:action_id>', methods=['PUT'])
@jwt_required
def update_action(action_id):
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input'}), 400
    
    with SessionLocal() as db:
        action = db.query(Action).get(action_id)
        if not action:
            return jsonify({'error': 'Not found'}), 404
        action.date_logged = data.get('date_logged', action.date_logged)
        action.type = data.get('type', action.type)
        action.application_id = data.get('application_id', action.application_id)
        action.message_id = data.get('message_id', action.message_id)
        db.commit()
        return jsonify({'id': action.id})

@api.route('/api/actions/<int:action_id>', methods=['DELETE'])
@jwt_required
def delete_action(action_id):
    with SessionLocal() as db:
        action = db.query(Action).get(action_id)
        if not action:
            return jsonify({'error': 'Not found'}), 404
        db.delete(action)
        db.commit()
        return '', 204

# --- EmailAddress CRUD ---
@api.route('/api/email_addresses', methods=['POST'])
@jwt_required
def create_email_address():
    data = request.json or {}
    if data is None:
        return jsonify({'error': 'Invalid input'}), 400
    email_address = data.get('email', '').strip().lower()
    company_id = data.get('company_id')
    if not email_address or not company_id:
        return jsonify({'error': 'Email and company_id are required'}), 400
    
    
    with SessionLocal() as db:
        email_address = EmailAddress(
            email=email_address,
            company_id=company_id
        )
        db.add(email_address)
        db.commit()
        return jsonify({'id': email_address.id, 'email': email_address.email, 'company_id': email_address.company_id}), 201

@api.route('/api/email_addresses/<int:email_id>', methods=['GET'])
@jwt_required
def get_email_address(email_id):
    with SessionLocal() as db:
        email_address = db.query(EmailAddress).get(email_id)
        if not email_address:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({'id': email_address.id, 'email': email_address.email, 'company_id': email_address.company_id})

@api.route('/api/email_addresses', methods=['GET'])
@jwt_required
def search_email_addresses():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        query = db.query(EmailAddress)
        if q:
            query = query.filter(EmailAddress.email == func.lower(q))
        email_addresses = query.all()
        return jsonify([
            {'id': e.id, 'email': e.email, 'company_id': e.company_id} for e in email_addresses
        ])

@api.route('/api/email_addresses/<int:email_id>', methods=['PUT'])
@jwt_required
def update_email_address(email_id):
    data = request.json or {}
    with SessionLocal() as db:
        email_address = db.query(EmailAddress).get(email_id)
        if not email_address:
            return jsonify({'error': 'Not found'}), 404
        email_address.email = data.get('email', email_address.email)
        email_address.company_id = data.get('company_id', email_address.company_id)
        db.commit()
        return jsonify({'id': email_address.id, 'email': email_address.email, 'company_id': email_address.company_id})

@api.route('/api/email_addresses/<int:email_id>', methods=['DELETE'])
@jwt_required
def delete_email_address(email_id):
    with SessionLocal() as db:
        email_address = db.query(EmailAddress).get(email_id)
        if not email_address:
            return jsonify({'error': 'Not found'}), 404
        db.delete(email_address)
        db.commit()
        return '', 204
