# -*- coding: utf-8 -*-

from openerp import models, fields, api


class Vehicle(models.Model):
    _name = 'tt.vehicle'

    name = fields.Char(string="Name")
    longitude = fields.Char(string="Longitude", required="True", default="51.6643335")
    latitude = fields.Char(string="Latitude", required="True", default="19.2976092")
    matriculate = fields.Char(string="Matricule", default="58924/A/48")
    # location = fields.Char(string="Coordonnées géographiques", compute="tt_return_location")

    @api.multi
    def tt_locate_vehicle(self):
        return{
                "type": "ir.actions.act_url",
                "url": "http://localhost:63342/odoo/geolocation/google_map.html?longitude=" + self.longitude + "&latitude=" + self.latitude + "&key=AIzaSyBWGBUR56Byqip7RUel5-EeWzFQygna2Hg",
                "target": "new",
        }