#
# Aqua-Giraffe
#
import json
from odoo import SUPERUSER_ID
# from odoo.addons.web import http
# from odoo.addons.web.http import request
from odoo.tools import html_escape as escape

import logging
import odoo
from odoo import http
from odoo.http import Response

from odoo.http import content_disposition, dispatch_rpc, request, \
                      serialize_exception as _serialize_exception
from odoo.addons.website.models import website

import os
# from flask import request, jsonify

import requests

import json
# import sqlalchemy
# import falcon
# from db.models import LeadDetails, Session
# from sqlalchemy.orm import load_only
# from app import app, mongo
# import logger

# class samplingController(http.Controller):
# 	_cp_path = '/sampling'
	
# 	@http.route('/sampling', type='http', auth='none')
# 	def sampling_email_action(self, model=False, sampling_id=False, res_id=False, action=False, reason=False, message=False, reply=False, **args):
# 		print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk sampling"
		
# 		if res_id: res_id = int(res_id)
# 		if sampling_id: sampling_id = int(sampling_id)
		
# 		cr, uid, context, registry = request.cr, request.uid, request.context , request.registry

# 		ticket_sampling_model = http.request.env[model]
# 		ticket_sampling_obj2 = ticket_sampling_model.sudo().search([('id','=',sampling_id)])

	
# 		###--- Commented for testing purpose ---###
# 		if model not in request.env or not res_id:
# 			print "111111111111111111111111111111111111111111111111"
# 			return request.render("sales_meet.email_sampling", {'invalid':True,'title':"Invalid Sampling"})
		
# 		# request.env[model]
# 		ticket_sampling_obj = False

# 		try:
# 			ticket_sampling_model = http.request.env[model]
# 			ticket_sampling_obj2 = ticket_sampling_model.sudo().search([('id','=',sampling_id)])
# 		except:
# 			return request.render("sales_meet.email_sampling", {'invalid':True,'title':"Invalid sampling"})
		
# 		values = {
# 			'sampling': ticket_sampling_obj2,
# 			'title': "",
# 		}
		
# 		if action == 'approve_ticket_sampling_manager':
# 			print "ooooooooooooooooooooooooooooooooooooooo approve_ticket_sampling_manager .00000000000000000o"
# 			if ticket_sampling_obj2.state and ticket_sampling_obj2.state  in ('draft','approved','posted','cancel'):
# 				return request.render("sales_meet.email_sampling", {'invalid':True,'title':"Invalid action on Approved sampling"})
				
# 			result = ticket_sampling_obj2.sudo().approve_ticket_sampling_manager()
# 			values['approve_ticket_sampling_manager'] = True
# 			values['title'] = "Sampling Approved"


# 		if action == 'refuse_ticket_sampling':
# 			if ticket_sampling_obj2.state and ticket_sampling_obj2.state  not in ('done','approved','refused','posted','cancel'):
# 				return request.render("sales_meet.email_sampling", {'invalid':True,'title':"Invalid action on Closed sampling"})

			
# 			result = ticket_sampling_obj2.refuse_ticket_sampling()
# 			values['refuse_ticket_sampling'] = True
# 			values['title'] = "Sampling Rejected"


# 		if action == 'info':
# 			values['info'] = True
# 			if message:
# 				result = ticket_sampling_obj.more_info_email(res_id, message)
# 				if result:
# 					values['message'] = True
# 					values['title'] = "More information requested"
# 				else:
# 					values['invalid'] = True
# 					values['title'] = "Invalid action on sampling"
# 			else:
# 				return request.render("sales_meet.email_sampling", values)
			

# 		return request.render("sales_meet.email_sampling", values)
# 		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))


class LeadApiController(http.Controller):
	_cp_path = '/lead_api/lead'

	# @app.route('/api/lead', methods=["GET","POST"])
	@http.route('/lead_api/lead', type='http', auth='none', methods=["GET","POST"])
	def lead_api(self, model=False, sampling_id=False, id=False, action=False, reason=False, message=False, reply=False, resp=False, **args):

		print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk"

		error = ''
		all_lead =[]

		# if res_id: res_id = int(res_id)
		# if credit_note_id: credit_note_id = int(credit_note_id)
		
		# cr, uid, context, registry = request.cr, request.uid, request.context , request.registry
		model = 'crm.lead'

		credit_note_model = http.request.env[model]
		credit_note_obj2 = credit_note_model.sudo().search([('user_id','=',1)])

		print "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv" , credit_note_obj2
		for record in credit_note_obj2:
			all_lead.append((record.id,record.name))



		# all_partner = []
		# session = Session()
		# column = ["id","name"]
		# if not id:

		# 	all_partner = session.query(LeadDetails).options(load_only(*column)).all()
		# 	all_customer = [cust.__dict__ for cust in all_partner]
		# 	for cust in all_customer:
		# 		cust.pop("_sa_instance_state", None)
		# else:
		# 	lead_id = int(id)
		# 	all_partner2 = session.query(LeadDetails).options(load_only(*column)).filter_by(id=lead_id)
		# 	all_customer = [cust.__dict__ for cust in all_partner2]
		# 	for cust in all_customer:
		# 		cust.pop("_sa_instance_state", None)

		# resp.status = falcon.HTTP_200
		print "ggggggggggggggggggggggggggggggggggggggggg" , all_lead
		content_type = 'application/json'
		body = json.dumps(all_lead)
		return body


		# return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))
	    # try:
		
	    #     if request.method == "POST":
			
	    #         attempted_username = request.form['username']
	    #         attempted_password = request.form['password']

	    #         #flash(attempted_username)
	    #         #flash(attempted_password)

	    #         if attempted_username == "admin" and attempted_password == "password":
	    #             return redirect(url_for('dashboard'))
					
	    #         else:
	    #             error = "Invalid credentials. Try Again."

	    #     return render_template("login.html", error = error)

	    # except Exception as e:
	    #     #flash(e)
	    #     return render_template("login.html", error = error)  
	