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




class TicketBookingController(http.Controller):
	_cp_path = '/booking'
	
	@http.route('/booking', type='http', auth='none')
	def ticketbooking_email_action(self, model=False, booking_id=False, res_id=False, action=False, reason=False, message=False, reply=False, **args):
		print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk booking"
		
		if res_id: res_id = int(res_id)
		if booking_id: booking_id = int(booking_id)
		
		cr, uid, context, registry = request.cr, request.uid, request.context , request.registry

		ticket_booking_model = http.request.env[model]
		ticket_booking_obj2 = ticket_booking_model.sudo().search([('id','=',booking_id)])

	
		###--- Commented for testing purpose ---###
		if model not in request.env or not res_id:
			return request.render("sales_meet.email_ticketbooking", {'invalid':True,'title':"Invalid Booking"})
		
		# request.env[model]
		ticket_booking_obj = False

		try:
			ticket_booking_model = http.request.env[model]
			ticket_booking_obj2 = ticket_booking_model.sudo().search([('id','=',booking_id)])
		except:
			return request.render("sales_meet.email_ticketbooking", {'invalid':True,'title':"Invalid Booking"})
		
		values = {
			'ticketbooking': ticket_booking_obj2,
			'title': "",
		}
		
		if action == 'approve_ticket_booking_manager':
			print "ooooooooooooooooooooooooooooooooooooooo approve_ticket_booking_manager .00000000000000000o"
			if ticket_booking_obj2.state and ticket_booking_obj2.state  in ('draft','cancel','approved'):
				return request.render("sales_meet.email_ticketbooking", {'invalid':True,'title':"Invalid action on Approved Booking"})
				
			result = ticket_booking_obj2.sudo().approve_ticket_booking_manager()
			values['approve_ticket_booking_manager'] = True
			values['title'] = "Booking Approved"


		if action == 'refuse_ticket_booking':
			if ticket_booking_obj2.state and ticket_booking_obj2.state  not in ('created','cancel'):
				return request.render("sales_meet.email_ticketbooking", {'invalid':True,'title':"Invalid action on Closed Booking"})

			values['refuse_ticket_booking'] = True
			if reason:
				print "ooooooooooooooooooooooooooooooooooooooo refuse_expenses .00000000000000000o"
				result = ticket_booking_obj2.refuse_ticket_booking(reason)
				values['reason'] = reason
				values['title'] = "Booking Rejected"

			else:
				return request.render("sales_meet.email_ticketbooking", values)


		if action == 'info':
			values['info'] = True
			if message:
				result = ticket_booking_obj.more_info_email(res_id, message)
				if result:
					values['message'] = True
					values['title'] = "More information requested"
				else:
					values['invalid'] = True
					values['title'] = "Invalid action on Booking"
			else:
				return request.render("sales_meet.email_ticketbooking", values)
			

		return request.render("sales_meet.email_ticketbooking", values)
		return werkzeug.utils.redirect('/mail/view?%s' % url_encode({'model': model, 'res_id': res_id}))


