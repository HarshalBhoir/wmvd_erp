# -*- coding: utf-8 -*-

import odoo
from odoo import http, SUPERUSER_ID
from odoo.http import content_disposition, dispatch_rpc, request, \
                      serialize_exception as _serialize_exception

class ApprovalsController(http.Controller):
	_cp_path = '/meeting'
	
	@http.route('/meeting', type='http', auth='none')
	def approvals_email_action(self, model=False, meeting_id=False, res_id=False, 
		user_id=False, action=False, remarks=False, message=False, reply=False, **args):
		
		if res_id: res_id = int(res_id)
		if meeting_id: approval_id = int(meeting_id)
		
		cr, uid, context, registry = request.cr, request.uid, request.context , request.registry
		approval_request_obj = False

		try:
			approval_request = http.request.env[model]
			approval_request2 = approval_request.sudo().search([('id','=',meeting_id)])
		except:
			return request.render("sales_meet.email_meeting_approval_request",
			 {'invalid':True,'title':"Invalid Meeting Approval Request"})
		
		values = {
			'approval_request': approval_request2,
			'title': "",
		}

		if action == 'approve_meeting':
			if approval_request2.state and approval_request2.state  not in ('done','refused'):
				return request.render("sales_meet.email_meeting_approval_request", 
					{'invalid':True,'title':"Invalid action on Approved Request"})
			
			values['approve_data'] = True
			values['title'] = "Request Approved"
			result = approval_request2.sudo().approve_data()
			print "----------------------- approve_meeting_request .-----------------"
							
		if action == 'refuse_meeting':
			if approval_request2.state and approval_request2.state  not in ('done','approved'):
				return request.render("sales_meet.email_meeting_approval_request", 
					{'invalid':True,'title':"Invalid action on Refused Request"})

			values['refuse_data'] = True
			result = approval_request2.sudo().refuse_data()
			values['title'] = "Request Rejected"
			print "----------------------- refuse_approval_request .-----------------"
		
		return request.render("sales_meet.email_meeting_approval_request", values)
		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))