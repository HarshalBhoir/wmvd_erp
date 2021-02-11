#
# Aqua-Giraffe
#
import json
from odoo import SUPERUSER_ID
from odoo.addons.web import http
from odoo.addons.web.http import request
from odoo.tools import html_escape as escape


class TicketController(http.Controller):
	_cp_path = '/ticket'
	
	@http.route('/ticket/approve', type='http', auth='user')
	def mail_action_follow(self, model='it.ticket', res_id=False):
		if model not in request.env:
			return self._redirect_to_messaging()
		Model = request.env[model]
		try:
			Model.browse(res_id).message_subscribe_users()
		except:
			return self._redirect_to_messaging()
		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))
	
	
	# @http.route('/property_image/<string:ref_no>', type='http', auth="public")
	# def get_property_details(self, ref_no='', *arg, **post):
	# 	if not ref_no:
	# 		return True
	# 	cr, uid, context = request.cr, request.uid, request.context
	# 	prop_obj = False
	# 	prop_id = request.registry['real.estate.property'].search(cr, SUPERUSER_ID, [('code','=',ref_no)])
	# 	if prop_id:
	# 		prop_obj = request.registry['real.estate.property'].browse(cr, SUPERUSER_ID, prop_id)
	# 		
	# 		values = {
	# 			'p': prop_obj,
	# 			# 'partner_data': json.dumps(partner_data)
	# 		}
	# 		return request.render("real_estate.portal_property", values)
	# 	else:
	# 		return request.render("real_estate.portal_property", {})