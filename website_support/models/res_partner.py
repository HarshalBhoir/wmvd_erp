# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError

class ResPartnerTicket(models.Model):

    _inherit = "res.partner"
    
    support_ticket_ids = fields.One2many('website.support.ticket', 'partner_id', string='Tickets')
    support_ticket_count = fields.Integer(compute="_count_support_tickets", string="Ticket Count")
    new_support_ticket_count = fields.Integer(compute="_count_new_support_tickets", string="New Ticket Count")
    support_ticket_string = fields.Char(compute="_compute_support_ticket_string", string="Support Ticket String")
    stp_ids = fields.Many2many('res.partner', 'stp_res_partner_rel', 'stp_p1_id', 'stp_p2_id', string="Support Ticket Access Accounts",
                 help="Can view support tickets from other contacts")
    it_supplier = fields.Boolean(string="IT Vendor", store="True")
    partner_type =  fields.Many2one(comodel_name='partner.type', string='Vendor Type') 
    quality_factor = fields.Integer()
    competetive_factor = fields.Integer()
    time_factor = fields.Integer()
    service_factor = fields.Integer()
    total_eval =  fields.Integer('Total')

    attach_asset_count = fields.Integer(string="Number of Assets attached", compute='count_assets')


    @api.onchange('quality_factor','competetive_factor','time_factor','service_factor')
    def _onchange_vendor_eval(self):

        if  (self.quality_factor >4 or self.quality_factor <0) or (self.competetive_factor >4 or self.competetive_factor < 0) or \
             (self.time_factor >4 or self.time_factor <0) or (self.service_factor > 4 or self.service_factor <0) :
            raise Warning(_("Please enter rating within 0 - 4"))

        else:

            self.total_eval = (self.quality_factor if self.quality_factor else 0.0 ) + \
            (self.competetive_factor if self.competetive_factor else 0.0 ) + \
            (self.time_factor if self.time_factor else 0.0 ) + \
            (self.service_factor if self.service_factor else 0.0 )

    @api.multi
    def count_assets(self):
        for res in self:

            asset_ids = self.env['bt.asset'].search([("vendor_id","=",res.id)])
            if len(asset_ids):
                res.attach_asset_count = len(asset_ids) or 0



    @api.multi
    def get_attached_assets(self):
        asset_ids = self.env['bt.asset'].search([("vendor_id","=",self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('website_support.action_bt_asset')
        list_view_id = imd.xmlid_to_res_id('website_support.bt_asset_management_asset_tree')
        form_view_id = imd.xmlid_to_res_id('website_support.bt_asset_management_asset_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'],
                [False, 'graph'], [False, 'kanban'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(asset_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % asset_ids.ids
        elif len(asset_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = asset_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
    
    @api.one
    @api.depends('support_ticket_ids')
    def _count_support_tickets(self):
        """Sets the amount support tickets owned by this customer"""
        self.support_ticket_count = self.support_ticket_ids.search_count([('partner_id','=',self.id)])
        
    @api.one
    @api.depends('support_ticket_ids')
    def _count_new_support_tickets(self):
        """Sets the amount of new support tickets owned by this customer"""
        opened_state = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_open')
        self.new_support_ticket_count = self.support_ticket_ids.search_count([('partner_id','=',self.id), ('state','=',opened_state.id)])
        
    @api.one
    @api.depends('support_ticket_count', 'new_support_ticket_count')
    def _compute_support_ticket_string(self):
        self.support_ticket_string = str(self.support_ticket_count) + " (" + str(self.new_support_ticket_count) + ")"



class ResPartnerType(models.Model):

    _name = "partner.type"
    _description = "Partner Type"
    
    name = fields.Char(string="Vendor Type")
