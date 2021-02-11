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



class BankPaymentController(http.Controller):
	_cp_path = '/csv'

	@http.route('/csv/download/<int:rec_id>/', type='http', auth='none', website=True)
	def csvdownload(self, rec_id, **kw):
		print "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr"
		return http.request.env['sales_meet.bank_payment']._csv_download({'rec_id': rec_id})

class ExpenseController(http.Controller):
	_cp_path = '/expense'
	
	@http.route('/expense', type='http', auth='none')
	def expense_email_action(self, model=False, meeting_id=False, res_id=False, action=False, reason=False, message=False, reply=False, **args):
		
		if res_id: res_id = int(res_id)
		if meeting_id: meeting_id = int(meeting_id)
		
		cr, uid, context, registry = request.cr, request.uid, request.context , request.registry

		expens_meet = http.request.env[model]
		meeting_obj2 = expens_meet.sudo().search([('id','=',meeting_id)])

	
		###--- Commented for testing purpose ---###
		if model not in request.env or not res_id:
			return request.render("sales_meet.email_expense", {'invalid':True,'title':"Invalid meeting"})
		
		# request.env[model]
		meeting_obj = False

		# refuse_reason = http.request.env['hr.expense.refuse.wizard']
		# meeting_obj2 = refuse_reason.sudo().search([('active_ids','=',meeting_id)])

		try:
			# meeting_obj = request.registry[model].search(cr, res_id, meeting_id)
			expens_meet = http.request.env[model]
			meeting_obj2 = expens_meet.sudo().search([('id','=',meeting_id)])
		except:
			return request.render("sales_meet.email_expense", {'invalid':True,'title':"Invalid meeting"})
		
		values = {
			'meeting': meeting_obj2,
			'title': "",
		}

		# if meeting_obj2.state and meeting_obj2.state  not in ('submit','manager_approve'):
		# 	return request.render("sales_meet.email_expense", {'invalid':True,'title':"Invalid action on Closed Expense"})

		
		if action == 'approve_expense_sheets_manager':
			if meeting_obj2.state and meeting_obj2.state  not in ('submit'):
				return request.render("sales_meet.email_expense", {'invalid':True,'title':"Invalid action on Approved Expense"})
				
			result = meeting_obj2.sudo().approve_expense_sheets_manager()
			values['approve_expense_sheets_manager'] = True
			values['title'] = "Expense Approved"

				
		if action == 'refuse_expenses':
			if meeting_obj2.state and meeting_obj2.state  not in ('submit','manager_approve'):
				return request.render("sales_meet.email_expense", {'invalid':True,'title':"Invalid action on Closed Expense"})

			values['refuse_expenses'] = True
			if reason:
				print "ooooooooooooooooooooooooooooooooooooooo refuse_expenses .00000000000000000o"
				result = meeting_obj2.refuse_expenses(reason)
				# if result:
				values['reason'] = reason
				values['title'] = "Expense Rejected"
				# else:
				# 	values['invalid'] = True
				# 	values['title'] = "Invalid action on meeting"
			else:
				return request.render("sales_meet.email_expense", values)


		if action == 'info':
			values['info'] = True
			if message:
				result = meeting_obj.more_info_email(res_id, message)
				if result:
					values['message'] = True
					values['title'] = "More information requested"
				else:
					values['invalid'] = True
					values['title'] = "Invalid action on meeting"
			else:
				return request.render("sales_meet.email_expense", values)
			
		# if action == 'reply':
		# 	values['reply'] = True
		# 	if message:
		# 		result = meeting_obj.reply_email(res_id, reply)
		# 		if result:
		# 			values['message'] = True
		# 			values['title'] = "Replied to meeting"
		# 		else:
		# 			values['invalid'] = True
		# 			values['title'] = "Invalid action on meeting"
		# 	else:
		# 		return request.render("sales_meet.email_expense", values)
		# 
		
		return request.render("sales_meet.email_expense", values)
		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))
	
