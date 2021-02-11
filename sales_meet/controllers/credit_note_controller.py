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

class creditnoteController(http.Controller):
	_cp_path = '/creditnote'
	
	@http.route('/creditnote', type='http', auth='none')
	def creditnote_email_action(self, model=False, credit_note_id=False, res_id=False, action=False, reason=False, message=False, reply=False, **args):
		print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk creditnote"
		
		if res_id: res_id = int(res_id)
		if credit_note_id: credit_note_id = int(credit_note_id)
		
		cr, uid, context, registry = request.cr, request.uid, request.context , request.registry

		credit_note_model = http.request.env[model]
		credit_note_obj2 = credit_note_model.sudo().search([('id','=',credit_note_id)])

	
		###--- Commented for testing purpose ---###
		if model not in request.env or not res_id:
			return request.render("sales_meet.email_creditnote", {'invalid':True,'title':"Invalid Credit Note"})
		
		# request.env[model]
		credit_note_obj = False

		try:
			credit_note_model = http.request.env[model]
			credit_note_obj2 = credit_note_model.sudo().search([('id','=',credit_note_id)])
		except:
			return request.render("sales_meet.email_creditnote", {'invalid':True,'title':"Invalid Credit Note"})
		
		values = {
			'creditnote': credit_note_obj2,
			'title': "",
		}
		
		if action == 'approve_credit_note_manager':
			print "ooooooooooooooooooooooooooooooooooooooo approve_credit_note_manager .00000000000000000o"
			if credit_note_obj2.state and credit_note_obj2.state  in ('draft','cancel','approved','posted'):
				return request.render("sales_meet.email_creditnote", {'invalid':True,'title':"Invalid action on Approved Credit Note"})
				
			result = credit_note_obj2.sudo().approve_credit_note_manager()
			values['approve_credit_note_manager'] = True
			values['title'] = "Credit Note Approved"

				
		if action == 'refuse_credit_note':
			if credit_note_obj2.state and credit_note_obj2.state  in ('draft','cancel','approved','posted'):
				return request.render("sales_meet.email_creditnote", {'invalid':True,'title':"Invalid action on Closed Credit Note"})

			values['refuse_credit_note'] = True
			print "ooooooooooooooooooooooooooooooooooooooo refuse_credit_note .00000000000000000o"
			result = credit_note_obj2.refuse_credit_note()
			values['refuse_credit_note'] = True
			values['title'] = "Credit Note Rejected"


		if action == 'info':
			values['info'] = True
			if message:
				result = credit_note_obj.more_info_email(res_id, message)
				if result:
					values['message'] = True
					values['title'] = "More information requested"
				else:
					values['invalid'] = True
					values['title'] = "Invalid action on CN"
			else:
				return request.render("sales_meet.email_creditnote", values)
			

		return request.render("sales_meet.email_creditnote", values)
		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))


