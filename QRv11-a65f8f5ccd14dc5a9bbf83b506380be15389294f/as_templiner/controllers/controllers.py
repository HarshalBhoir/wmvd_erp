# -*- coding: utf-8 -*-
from odoo import http

# class AsTemplateModule(http.Controller):
#     @http.route('/as_template_module/as_template_module/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/as_template_module/as_template_module/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('as_template_module.listing', {
#             'root': '/as_template_module/as_template_module',
#             'objects': http.request.env['as_template_module.as_template_module'].search([]),
#         })

#     @http.route('/as_template_module/as_template_module/objects/<model("as_template_module.as_template_module"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('as_template_module.object', {
#             'object': obj
#         })