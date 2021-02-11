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
from odoo.http import content_disposition, dispatch_rpc, request, \
                      serialize_exception as _serialize_exception
from odoo.addons.website.models import website




class salesdeliveryController(http.Controller):
	_cp_path = '/salesdelivery'
	
	@http.route('/salesdelivery', type='http', auth='none')
	def creditnote_email_action(self, model=False, delivery_id=False, res_id=False, action=False, reason=False, message=False, reply=False, **args):
		print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk salesdelivery"

		
		
		if res_id: res_id = int(res_id)
		if delivery_id: delivery_id = int(delivery_id)
		
		cr, uid, context, registry = request.cr, request.uid, request.context , request.registry

		logistic_trail_line_model = http.request.env[model]
		logistic_trail_line_obj2 = logistic_trail_line_model.sudo().search([('id','=',delivery_id)])

	
		###--- Commented for testing purpose ---###
		if model not in request.env or not res_id:
			print "gggggggggggggggggggggggggggggggggggggg" , model , res_id 
			return request.render("sales_meet.email_logistic_trail_line", {'invalid':True,'title':"Invalid Sales Order"})
		
		# request.env[model]
		credit_note_obj = False

		try:
			logistic_trail_line_model = http.request.env[model]
			logistic_trail_line_obj2 = logistic_trail_line_model.sudo().search([('id','=',delivery_id)])
		except:
			return request.render("sales_meet.email_logistic_trail_line", {'invalid':True,'title':"Invalid Sales Order"})
		
		values = {
			'salesdelivery': logistic_trail_line_obj2,
			'title': "",
		}
		
		if action == 'approve_delivery_sales_order':
			print "ooooooooooooooooooooooooooooooooooooooo approve_delivery_sales_order .00000000000000000o"
			if logistic_trail_line_obj2.state and logistic_trail_line_obj2.state  in ('draft','reverted'):
				return request.render("sales_meet.email_logistic_trail_line", {'invalid':True,'title':"Invalid action on Approved Delivered Material"})
				
			result = logistic_trail_line_obj2.sudo().approve_delivery_sales_order()
			values['approve_delivery_sales_order'] = True
			values['title'] = "Material Delivered !!!"

		return request.render("sales_meet.email_logistic_trail_line", values)
		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))