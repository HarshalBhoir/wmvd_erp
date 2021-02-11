#!/usr/bin/env bash

import json
from odoo import SUPERUSER_ID
# from odoo.addons.web import http
# from odoo.addons.web.http import request
from odoo.tools import html_escape as escape

import logging
import odoo
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
                      serialize_exception as _serialize_exception
from odoo.addons.website.models import website

class retailerworkingController(http.Controller):
	_cp_path = '/retailerworking'
	
	@http.route('/retailerworking', type='http', auth='none')
	def retailerworking_email_action(self, model=False, working_id=False, res_id=False, action=False, reason=False, message=False, reply=False, **args):
		print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk retailerworking"
		
		if res_id: res_id = int(res_id)
		if working_id: working_id = int(working_id)
		
		cr, uid, context, registry = request.cr, request.uid, request.context , request.registry

		retailer_working_model = http.request.env[model]
		retailer_working_obj2 = retailer_working_model.sudo().search([('id','=',working_id)])

	
		###--- Commented for testing purpose ---###
		if model not in request.env or not res_id:
			return request.render("sales_meet.email_retailerworking", {'invalid':True,'title':"Invalid Working"})
		
		# request.env[model]
		retailer_working_obj = False

		try:
			retailer_working_model = http.request.env[model]
			retailer_working_obj2 = retailer_working_model.sudo().search([('id','=',working_id)])
		except:
			return request.render("sales_meet.email_retailerworking", {'invalid':True,'title':"Invalid Working"})
		
		values = {
			'retailerworking': retailer_working_obj2,
			'title': "",
		}
		
		if action == 'approve_retailer_working':
			print "ooooooooooooooooooooooooooooooooooooooo approve_retailer_working .00000000000000000o"
			if retailer_working_obj2.state and retailer_working_obj2.state  in ('draft','approved','rejected'):
				return request.render("sales_meet.email_retailerworking", {'invalid':True,'title':"Invalid action on Approved Retailer Working"})
				
			result = retailer_working_obj2.sudo().approve_retailer_working()
			values['approve_retailer_working'] = True
			values['title'] = "Retailer Working Approved"

				
		if action == 'refuse_retailer_working':
			if retailer_working_obj2.state and retailer_working_obj2.state  in ('draft','approved','rejected'):
				return request.render("sales_meet.email_retailerworking", {'invalid':True,'title':"Invalid action on Closed Retailer Working"})

			values['refuse_retailer_working'] = True
			print "ooooooooooooooooooooooooooooooooooooooo refuse_retailer_working .00000000000000000o"
			result = retailer_working_obj2.refuse_retailer_working()
			values['refuse_retailer_working'] = True
			values['title'] = "Retailer Working Rejected"

			

		return request.render("sales_meet.email_retailerworking", values)
		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))