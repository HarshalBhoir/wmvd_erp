# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BtTransferLead(models.TransientModel):
    _name = 'bt.transfer.lead'
    _description = 'Transfer Lead'
    

    present_user_id = fields.Many2one('res.users', 'Old Salesperson')
    lead_details_ids = fields.One2many('bt.lead.details', 'transfer_lead_id')
    assign_user_id = fields.Many2one('res.users', 'New Salesperson')
     
     
    @api.onchange('present_user_id')
    @api.multi    
    def on_change_sale_person(self):
        
        if not self.present_user_id:
            return {}
        lead_ids = self.env['crm.lead'].search([('user_id', '=' , self.present_user_id.id)])
        if lead_ids:
            x = [{
                'lead_id': lead.id , 
                'user_id': lead.user_id.id, 
                'lead_name': lead.name
            } for lead in lead_ids]
            
            return {'value':{'lead_details_ids': x}}
        else:
            raise UserError(_('There is no lead  for   %s ') % (self.present_user_id.name))
                 
            
    @api.multi       
    def action_transfer_apply(self):
        if self.assign_user_id:
            for lead in self.lead_details_ids:
                lead.lead_id.with_context(mail_auto_subscribe_no_notify=True).sudo().write({'user_id': self.assign_user_id.id})
                
        else:
            for lead in self.lead_details_ids:
                if lead.assign_user_id :
                   lead.lead_id.with_context(mail_auto_subscribe_no_notify=True).sudo().write({'user_id': lead.assign_user_id.id})

        self.env['bt.lead.details'].search([]).unlink()

               
        
class BtLeadDetails(models.TransientModel):
    _name = 'bt.lead.details'
    _description = 'Lead Details'
    
    lead_id = fields.Many2one('crm.lead', 'Lead Id')
    user_id = fields.Many2one('res.users', 'Salesperson')
    transfer_lead_id = fields.Many2one('bt.transfer.lead', 'Lead Transfer', ondelete='cascade')
    assign_user_id = fields.Many2one('res.users', 'New Salesperson')
    lead_name = fields.Char('Lead')
    

