# -*- coding: utf-8 -*-
 
from odoo import models, api, _
from odoo.http import request
import calendar
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta , date
import time

class ResPartnerExtension(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def get_attached_docs(self):
        meeting_ids = self.env['calendar.event'].search(['|',("lead_id","=",self.id),("opportunity_id","=",self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('sales_meet.action_calendar_event_crm')
        list_view_id = imd.xmlid_to_res_id('sales_meet.view_calendar_event_tree_extension')
        form_view_id = imd.xmlid_to_res_id('sales_meet.view_calendar_event_form_extension')
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
        if len(meeting_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % meeting_ids.ids
        elif len(meeting_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = meeting_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


    @api.model
    def get_mdm_details(self):
        uid = request.session.uid
        cr = self.env.cr

        user_id = self.env['res.users'].sudo().search_read([('id', '=', uid)], limit=1)
              
        date_today = datetime.today()
        date_from = datetime.today().replace(day=1)
        date_to = datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1])

        customer_count = self.env['res.partner'].sudo().search_count([('active', '=', False),
                                                        ('state', 'in', ('draft','Submitted')),
                                                        ('customer','=',True)])

        approved_customer_count = self.env['res.partner'].sudo().search_count([('active', '=', False),
                                                        ('state', '=', 'Approved'),
                                                        ('customer','=',True)])

        created_customer_count = self.env['res.partner'].sudo().search_count([('active', '=', True),
                                                        ('state', 'in', ('created','updated')),
                                                        ('customer','=',True)])

        vendor_count = self.env['res.partner'].sudo().search_count([('active', '=', False),
                                                        ('state', 'in', ('draft','Submitted')),
                                                        ('supplier','=',True)])

        approved_vendor_count = self.env['res.partner'].sudo().search_count([('active', '=', False),
                                                        ('state', '=', 'Approved'),
                                                        ('supplier','=',True)])
        created_vendor_count = self.env['res.partner'].sudo().search_count([('active', '=', True),
                                                        ('state', 'in', ('created','updated')),
                                                        ('supplier','=',True)])


        product_count = self.env['product.product'].sudo().search_count([('active', '=', False)])

        if user_id:
            data = {
                'customer_count': customer_count,
                'vendor_count': vendor_count,
                'approved_customer_count': approved_customer_count,
                'approved_vendor_count': approved_vendor_count,
                'created_customer_count': created_customer_count,
                'created_vendor_count': created_vendor_count,
                'product_count': product_count,                
            }
            user_id[0].update(data)

        return user_id