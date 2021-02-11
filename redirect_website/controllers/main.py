# -*- coding: utf-8 -*-
import logging
import odoo
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
                      serialize_exception as _serialize_exception
from odoo.addons.website.models import website

logger = logging.getLogger(__name__)

class WebsiteRedirect(odoo.addons.web.controllers.main.Home):

	@http.route('/', type='http', auth="public", website=True)
	def index(self, s_action=None, db=None, **kw):
		logger.info("Redirected to Portal")
		if request.session.get('login') in [None,False]:
			return http.local_redirect('/web', query=request.params, keep_hash=True)
		else:
			return http.local_redirect('/web', query=request.params, keep_hash=True)




	@http.route('/*', type='http', auth="public", website=True)
	def index2(self, s_action=None, db=None, **kw):
		logger.info("Redirected to Portal")
		if request.session.get('login') in [None,False]:
			return http.local_redirect('/web', query=request.params, keep_hash=True)
		else:
			return http.local_redirect('/web', query=request.params, keep_hash=True)

website.index = WebsiteRedirect.index
website.index = WebsiteRedirect.index2