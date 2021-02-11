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

logger = logging.getLogger(__name__)

class WebsiteRedirectKnowage(odoo.addons.web.controllers.main.Home):

	@http.route('/salesregister', type='http', auth="public", website=True)
	def salesregisterindex(self, s_action=None, db=None, **kw):
		logger.info("Redirected to salesregisterindex")
		company = request.env['res.company']._company_default_get('calendar.event')
		ad_client_id = company.ad_client_id

		knowage_url = 'http://35.200.135.16:8888/knowage/public/servlet/AdapterHTTP?ACTION_NAME=EXECUTE_DOCUMENT_ACTION&OBJECT_LABEL=SRR&TOOLBAR_VISIBLE=true&ORGANIZATION=DEFAULT_TENANT&NEW_SESSION=true&PARAMETERS=AD_Client_ID=%s' %(ad_client_id)

		if request.session.get('login') in [None,False]:
			return http.local_redirect(knowage_url, query=request.params, keep_hash=True)
		else:
			return http.local_redirect(knowage_url, query=request.params, keep_hash=True)


	@http.route('/soauditreport', type='http', auth="public", website=True)
	def soauditreportindex(self, s_action=None, db=None, **kw):
		logger.info("Redirected to soauditreportindex")
		company = request.env['res.company']._company_default_get('calendar.event')
		ad_client_id = company.ad_client_id

		knowage_url = 'http://35.200.135.16:8888/knowage/public/servlet/AdapterHTTP?ACTION_NAME=EXECUTE_DOCUMENT_ACTION&OBJECT_LABEL=SIAR&TOOLBAR_VISIBLE=true&ORGANIZATION=DEFAULT_TENANT&NEW_SESSION=true&PARAMETERS=AD_Client_ID=%s' %(ad_client_id)

		if request.session.get('login') in [None,False]:
			return http.local_redirect(knowage_url, query=request.params, keep_hash=True)
		else:
			return http.local_redirect(knowage_url, query=request.params, keep_hash=True)



	@http.route('/purchaseregister', type='http', auth="public", website=True)
	def purchaseregisterindex(self, s_action=None, db=None, **kw):
		logger.info("Redirected to Purchase Knowage")
		if request.session.get('login') in [None,False]:
			return http.local_redirect('http://103.16.141.159:9876/knowage/public/servlet/AdapterHTTP?ACTION_NAME=EXECUTE_DOCUMENT_ACTION&OBJECT_LABEL=SRR&TOOLBAR_VISIBLE=true&ORGANIZATION=DEFAULT_TENANT&NEW_SESSION=true', query=request.params, keep_hash=True)
		else:
			return http.local_redirect('http://103.16.141.159:9876/knowage/public/servlet/AdapterHTTP?ACTION_NAME=EXECUTE_DOCUMENT_ACTION&OBJECT_LABEL=SRR&TOOLBAR_VISIBLE=true&ORGANIZATION=DEFAULT_TENANT&NEW_SESSION=true', query=request.params, keep_hash=True)

website.index = WebsiteRedirectKnowage.salesregisterindex
website.index = WebsiteRedirectKnowage.soauditreportindex
website.index = WebsiteRedirectKnowage.purchaseregisterindex


