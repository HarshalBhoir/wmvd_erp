from odoo import http
from odoo.http import request
import json





class ResUsers(http.Controller):

    @http.route('/restfulapi/login', auth='none', type="http")
    def login(self, **kw):
        xmlrpclib = xmlrpc.client
        url, db, username, password = 'http://localhost:7900', http.request.env.cr.dbname, kw.get('username'), kw.get('password')
        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        try:
            uid = common.authenticate(db, username, password, {})
            return json.dumps({'user_id':uid})
        except:
            return json.dumps({'Error':'Invalid Request'})
     
    @http.route('/restfulapi/get-products', auth='none', type="http")
    def get_products(self, **kw):
        xmlrpclib = xmlrpc.client
        url, db, username, password = 'http://localhost:7900', http.request.env.cr.dbname, kw.get('username'), kw.get('password')
        models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(url))
        common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(url))
        try:
            uid = common.authenticate(db, username, password, {})
            res = models.execute_kw(db, uid, password, 'product.product', 'search_read', [], {})
            return json.dumps({'products':res})
        except:
            return json.dumps({'Error':'Invalid Request'})


    @http.route('/api/get_new_users', csrf=False, type='http', methods=["GET"], token=None, auth='user')
    def get_new_users(self, **args):
        request.env.cr.execute(""" SELECT * FROM res_users where active= True  """)
        data = []
        q_result = request.env.cr.dictfetchall()
        for line in q_result:

            id_user = line.get('id')
            active = line.get('active')
            company_id = line.get('company_id')
            partner_id = line.get('partner_id')

            data.append({
                    "id_user":id_user,
                    "active":active,
                    "company_id":company_id,
                    "partner_id":partner_id
                })
        return json.dumps(data)


    @http.route('/get_users', type='json', auth='user')
    def get_users(self):
        print("Yes here entered")
        users_rec = request.env['res.users'].search([('active','=',True)])
        users = []
        for rec in users_rec:
            vals = {
                'id': rec.id,
                'login': rec.login,
                # 'partner_id': rec.partner_id,
            }
            users.append(vals)
        print("users List--->", users)
        data = {'status': 200, 'response': users, 'message': 'Done All users Returned'}
        return data




    # @http.route('/create/webpatient', type="http", auth="public", website=True)
    # def create_webpatient(self, **kw):
    #     print("Data Received.....", kw)
    #     request.env['hospital.patient'].sudo().create(kw)
    #     # doctor_val = {
    #     #     'name': kw.get('patient_name')
    #     # }
    #     # request.env['hospital.doctor'].sudo().create(doctor_val)
    #     return request.render("om_hospital.patient_thanks", {})







    # @http.route('/patient_webform', website=True, auth='user')
    # def patient_webform(self):
    #     return request.render("om_hospital.patient_webform", {})
    #
    # # Check and insert values from the form on the model <model>
    # @http.route(['/create_web_patient'], type='http', auth="public", website=True)
    # def patient_contact_create(self, **kwargs):
    #     print("ccccccccccccc")
    #     request.env['hospital.patient'].sudo().create(kwargs)
    #     return request.render("om_hospital.patient_thanks", {})



    # # Sample Controller Created
    # @http.route('/hospital/patient/', website=True, auth='user')
    # def hospital_patient(self, **kw):
    #     # return "Thanks for watching"
    #     patients = request.env['hospital.patient'].sudo().search([])
    #     return request.render("om_hospital.patients_page", {
    #         'patients': patients
    #     })

    # # Sample Controller Created
    # @http.route('/update_patient', type='json', auth='user')
    # def update_patient(self, **rec):
    #     if request.jsonrequest:
    #         if rec['id']:
    #             print("rec...", rec)
    #             patient = request.env['hospital.patient'].sudo().search([('id', '=', rec['id'])])
    #             if patient:
    #                 patient.sudo().write(rec)
    #             args = {'success': True, 'message': 'Patient Updated'}
    #     return args

    # @http.route('/create_patient', type='json', auth='user')
    # def create_patient(self, **rec):
    #     if request.jsonrequest:
    #         print("rec", rec)
    #         if rec['name']:
    #             vals = {
    #                 'patient_name': rec['name'],
    #                 'email_id': rec['email_id']
    #             }
    #             new_patient = request.env['hospital.patient'].sudo().create(vals)
    #             print("New Patient Is", new_patient)
    #             args = {'success': True, 'message': 'Success', 'id': new_patient.id}
    #     return args




    # @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    # def web_auth_reset_password(self, *args, **kw):
    #     return super(AuthSignupHomeInherit, self).web_auth_reset_password(*args, **kw)

