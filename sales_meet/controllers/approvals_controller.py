
import json
from odoo import SUPERUSER_ID
from odoo.tools import html_escape as escape

import logging
import odoo
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
                      serialize_exception as _serialize_exception
from odoo.addons.website.models import website


class ApprovalsController(http.Controller):
	_cp_path = '/approvals'
	
	@http.route('/approvals', type='http', auth='none')
	def approvals_email_action(self, model=False, approval_id=False, res_id=False, 
		user_id=False, action=False, remarks=False, message=False, reply=False, **args):
		
		if res_id: res_id = int(res_id)
		if approval_id: approval_id = int(approval_id)
		if user_id: user_id = int(user_id)
		
		cr, uid, context, registry = request.cr, request.uid, request.context , request.registry

		approval_request = http.request.env[model]
		approval_request2 = approval_request.sudo().search([('id','=',approval_id)])

	
		###--- Commented for testing purpose ---###
		if model not in request.env or not res_id:
			return request.render("sales_meet.email_approval_request", {'invalid':True,'title':"Invalid Approval Request"})
		
		approval_request_obj = False

		try:
			approval_request = http.request.env[model]
			approval_request2 = approval_request.sudo().search([('id','=',approval_id)])
		except:
			return request.render("sales_meet.email_approval_request", {'invalid':True,'title':"Invalid Approval Request"})
		
		values = {
			'approval_request': approval_request2,
			'title': "",
		}
		
		if action == 'approve_approval_request':
			if approval_request2.state and approval_request2.state  not in ('update','update2','submitted_to_manager'):
				return request.render("sales_meet.email_approval_request", {'invalid':True,'title':"Invalid action on Closed Request"})
				
			values['approve_approval_request'] = True
			values['approver_id'] = user_id

			if remarks:
				result = approval_request2.sudo().approve_approval_request(remarks , user_id)
				values['remarks'] = remarks
				values['title'] = "Request Approved"
				print "ooooooooooooooooooooooooooooooooooooooo request Aproved .00000000000000000o" , result , values
			else:
				return request.render("sales_meet.email_approval_request", values)

				
		if action == 'refuse_approval_request':
			if approval_request2.state and approval_request2.state  not in ('update','update2','submitted_to_manager','approved'): 
				return request.render("sales_meet.email_approval_request", {'invalid':True,'title':"Invalid action on Closed Request"})

			values['refuse_approval_request'] = True
			if remarks:
				print "ooooooooooooooooooooooooooooooooooooooo refuse_approval_request .00000000000000000o"
				result = approval_request2.refuse_approval_request(remarks, user_id)
				values['remarks'] = remarks
				values['title'] = "Request Rejected"
				print "ooooooooooooooooooooooooooooooooooooooo refuse_approval_request .00000000000000000o"
			else:
				return request.render("sales_meet.email_approval_request", values)


		if action == 'info':
			values['info'] = True
			if message:
				result = approval_request_obj.more_info_email(res_id, message)
				if result:
					values['message'] = True
					values['title'] = "More information requested"
				else:
					values['invalid'] = True
					values['title'] = "Invalid action on approval_request"
			else:
				return request.render("sales_meet.email_approval_request", values)
			
		
		return request.render("sales_meet.email_approval_request", values)
		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))