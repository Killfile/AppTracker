from flask import Blueprint, request, jsonify
from apptracker_database.database import SessionLocal
from ..app import jwt_required
from apptracker_database.company_dao import CompanyDAO

company_api = Blueprint('company_api', __name__)

# --- Company CRUD ---
@company_api.route('/api/companies', methods=['POST'])
@jwt_required
def create_company():
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        company_dao = CompanyDAO(db)
        existing_company = company_dao.get_company_by_name(data['name'])
        if existing_company:
            return jsonify({'error': 'Company already exists'}), 400
        
        company = company_dao.create_company(data['name'])
    return jsonify({'id': company.id, 'name': company.name}), 201

@company_api.route('/api/companies/<int:company_id>', methods=['GET'])
@jwt_required
def get_company(company_id):
    with SessionLocal() as db:
        company_dao = CompanyDAO(db)
        company = company_dao.get_company(company_id)
    if not company:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'id': company.id, 'name': company.name})

@company_api.route('/api/companies', methods=['GET'])
@jwt_required
def search_companies():
    q = request.args.get('q', '')
    with SessionLocal() as db:
        company_dao = CompanyDAO(db)
        companies = company_dao.search_companies_by_substring(q)
    return jsonify([{'id': c.id, 'name': c.name} for c in companies])

@company_api.route('/api/companies/<int:company_id>', methods=['PUT'])
@jwt_required
def update_company(company_id):
    data = request.json
    if data is None:
        return jsonify({'error': 'Invalid input; no json data found'}), 400
    with SessionLocal() as db:
        company_dao = CompanyDAO(db)
        company = company_dao.get_company(company_id)
        if not company:
            return jsonify({'error': 'Not found'}), 404
        updated_company = company_dao.update_company(company_id, data.get('name', company.name))
        return jsonify({'id': updated_company.id, 'name': updated_company.name})

@company_api.route('/api/companies/<int:company_id>', methods=['DELETE'])
@jwt_required
def delete_company(company_id):
    with SessionLocal() as db:
        company_dao = CompanyDAO(db)
        company = company_dao.get_company(company_id)
        if not company:
            return jsonify({'error': 'Not found'}), 404
        company_dao.delete_company(company_id)
        return '', 204






