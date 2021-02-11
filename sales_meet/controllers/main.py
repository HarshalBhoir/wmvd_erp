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


#from odoo.addons.base_rest.controllers import main


#class SalesMeetPublicApiController(main.RestController):
#    _root_path = "/sales_meet_api/public/"
#    _collection_name = "sales.meet.public.services"
#    _default_auth = "public"


#class SalesMeetPrivateApiController(main.RestController):
#    _root_path = "/sales_meet_api/private/"
#    _collection_name = "sales.meet.private.services"
#    _default_auth = "user"



# class BankPaymentController(http.Controller):
# 	_cp_path = '/csv'

# 	@http.route('/csv/download/<int:rec_id>/', type='http', auth='none', website=True)
# 	def csvdownload(self, rec_id, **kw):
# 		print "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr"
# 		return http.request.env['sales_meet.bank_payment']._csv_download({'rec_id': rec_id})

