from odoo import models, fields, api
import webbrowser

class LeadLocation(models.Model):
    _inherit = 'crm.lead'
    longit = fields.Float(string='Longitude', digits=(8,10))
    latit = fields.Float(string='Latitude',digits=(8,10))

    @api.multi
    def gotomap(self):
        url = ("http://maps.google.com/maps?q={},{}".format(self.longit,self.latit))
        webbrowser.open_new(url)
        return True