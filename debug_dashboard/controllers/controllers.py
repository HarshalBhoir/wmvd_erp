# -*- coding: utf-8 -*-
from odoo import http

# class DebugDashboard(http.Controller):
#     @http.route('/debug_dashboard/debug_dashboard/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/debug_dashboard/debug_dashboard/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('debug_dashboard.listing', {
#             'root': '/debug_dashboard/debug_dashboard',
#             'objects': http.request.env['debug_dashboard.debug_dashboard'].search([]),
#         })

#     @http.route('/debug_dashboard/debug_dashboard/objects/<model("debug_dashboard.debug_dashboard"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('debug_dashboard.object', {
#             'object': obj
#         })