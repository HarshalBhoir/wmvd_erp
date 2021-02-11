# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import api, exceptions, models, fields, _


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """ search full name and barcode """
        if args is None:
            args = []
            
        search_by_barcode = self.env['ir.config_parameter'].sudo().get_param('stock.module_search_by_barcode')
        if search_by_barcode:
            recs = self.search(['|', ('barcode', '=', name), ('complete_name', operator, name)] + args, limit=limit)
        else:
            recs = self.search(['|', ('barcode', operator, name), ('complete_name', operator, name)] + args, limit=limit)
        return recs.name_get()

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_search_by_barcode = fields.Boolean("Search faster with barcodes")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            module_search_by_barcode=self.env['ir.config_parameter'].sudo().get_param('stock.module_search_by_barcode')
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('stock.module_search_by_barcode', self.module_search_by_barcode)
