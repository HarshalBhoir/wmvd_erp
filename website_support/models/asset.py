# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError
from email import _name
import string

import base64
import cStringIO

import qrcode

class BtAsset(models.Model):   
    _name = "bt.asset"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Asset"
    _rec_name = 'display_name'
    
    @api.multi
    def _get_default_location(self):
        obj = self.env['bt.asset.location'].search([('default','=',True)])
        if not obj:
            raise Warning(_("Please create asset location first"))
        loc = obj[0]
        return loc 

   
    name = fields.Many2one('hr.employee', string='User') #fields.Char(string='Name', required=True)
    asset_name = fields.Char(string='Asset Name')
    display_name = fields.Char(string="Name", compute="_name_get" , store=True)
    purchase_date = fields.Date(string='Purchase Date',track_visibility='always')
    purchase_value = fields.Float(string='Purchase Value', track_visibility='always')
    tax_value = fields.Float(string='Tax Value', track_visibility='always')
    total_value = fields.Float(string='Total Value', track_visibility='always')
    asset_code = fields.Char(string='Asset Code')
    is_created = fields.Boolean('Created', copy=False)
    current_loc_id = fields.Many2one('bt.asset.location', string="Current Location", default=_get_default_location)
    model_name = fields.Char(string='Model Name')
    serial_no = fields.Char(string='Serial No', track_visibility='always')
    manufacturer = fields.Char(string='Manufacturer')
    warranty_start = fields.Date(string='Warranty Start')
    warranty_end = fields.Date(string='Warranty End')
    category_id = fields.Many2one('bt.asset.category', string='Category Id')
    budget_id = fields.Many2one('bt.budget', string="Budget")
    budget_category_id = fields.Many2one('bt.budget.category', 'Budget Category')
    note = fields.Text(string='Internal Notes')
    state = fields.Selection([('draft', 'Draft'),
            ('active', 'Active'),
            ('scrapped', 'Scrapped')], string='State',track_visibility='onchange', default='draft', copy=False)
    image = fields.Binary("Image", attachment=True,
        help="This field holds the image used as image for the asset, limited to 1024x1024px.")
    image_medium = fields.Binary("Medium-sized image", attachment=True,
        help="Medium-sized image of the asset. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved, "\
             "only when the image exceeds one of those sizes. Use this field in form views or some kanban views.")
    image_small = fields.Binary("Small-sized image", attachment=True,
        help="Small-sized image of the asset. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    component_ids = fields.One2many('bt.asset.component','asset_id', string='Components')
    user_id = fields.Many2one('res.users', string='User')
    main_asset = fields.Boolean('Main Asset', copy=False)
    company_id = fields.Many2one('res.company', string="Company")
    department_id = fields.Many2one('hr.department', string="Department", domain="[('company_id','=',company_id)]")
    asset_type = fields.Selection(string='Asset Type',
        selection=[('employee', 'Employee'), ('other', 'Other')],
        default='employee')
    service_asset = fields.Boolean('Service Asset', copy=False)
    vendor_id = fields.Many2one('res.partner', string='Vendor')

    quality_factor = fields.Integer()
    competetive_factor = fields.Integer()
    time_factor = fields.Integer()
    service_factor = fields.Integer()
    total_eval =  fields.Integer('Total')

    asset_qr_code = fields.Char('QR Code')
    qr_code = fields.Binary('QR Code')
    qr_code_link = fields.Binary('Download Link')
    qr_code_name = fields.Char(default="qr_code.png")
    maintenance_ids = fields.One2many('bt.asset.maintenance.line','asset_id', string='Maintenance')
    allocations_count = fields.Integer(compute='_compute_allocations_count', string='Allocations')


    @api.multi
    def _compute_allocations_count(self):
        data = self.env['bt.asset.allocation'].search([('asset_id', '=', self.ids)]).ids
        self.allocations_count = len(data)

    @api.multi
    def get_attached_docs(self):
        allocation_ids = self.env['bt.asset.allocation'].search([("asset_id","=",self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('website_support.action_bt_asset_allocation')
        list_view_id = imd.xmlid_to_res_id('website_support.bt_asset_allocation_tree')
        form_view_id = imd.xmlid_to_res_id('website_support.bt_asset_allocation_form')
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
        if len(allocation_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % allocation_ids.ids
        elif len(allocation_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = allocation_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


    @api.multi
    def create_allocation(self):

        # employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)]).id
        self.ensure_one()
        
        ctx = self._context.copy()
        allocation_ids = self.env['bt.asset.allocation'].search([('asset_id', '=', self.id)])
        if allocation_ids:
            result = self.get_attached_docs()
        if not allocation_ids:
            ctx.update({
                'search_default_asset_id': self.id, # 
                'default_employee': self.name.id,
                'default_asset_id': self.id,
                'default_asset_id': self.id,
                
            })
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('website_support.action_bt_asset_allocation')
            form_view_id = imd.xmlid_to_res_id('website_support.bt_asset_allocation_form')
            
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'target': 'current',
                
                'context': ctx,
                'res_model': action.res_model,
            }
        return result


    @api.multi
    def generate_qr_code(self):
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=20, border=4)
        self.asset_qr_code = 'Name: ' + self.asset_name + ', Code: ' + self.asset_code + ((', Model: ' + self.model_name) if self.model_name else '')  + ((', Serial: '\
         + self.serial_no) if self.serial_no else '') + ', Dept: ' + self.department_id.name + \
        ((', Location: ' + self.current_loc_id.name) if self.current_loc_id else '')  + ', Company: ' + str(self.company_id.name) + ', Date: ' + str(self.purchase_date)
        if self.asset_qr_code:
            name = self.display_name + '_asset.png'
            qr.add_data(self.asset_qr_code)
            qr.make(fit=True)
            img = qr.make_image()
            buffer = cStringIO.StringIO()
            img.save(buffer, format="PNG")
            qrcode_img = base64.b64encode(buffer.getvalue())
            self.update({'qr_code': qrcode_img, 'qr_code_link': qrcode_img, 'qr_code_name': name})


    def _default_company_id(self):
        company = self.env['res.users'].sudo().search([('id', '=', self.env.uid)],limit=1).company_id.id
        return company


    @api.multi
    @api.depends('name','asset_name','model_name')
    def _name_get(self):
        for ai in self:
            if (ai.name or ai.asset_name)  and ai.model_name:
                name = '('+str(ai.model_name) + ') ' + (str(ai.name.name) if ai.name else str(ai.asset_name))
                ai.display_name = name
            elif not ai.model_name:
                ai.display_name = ai.asset_name


    @api.onchange('name')
    def _onchange_name(self):
        if self.name:
            try:
                self.asset_name = self.env['hr.employee'].sudo().search([('id', '=', self.name.id)],limit=1).name
                self.company_id = self.env['res.company'].sudo().search([('id', '=', self.name.company_id.id)],limit=1)
                self.department_id = self.env['hr.department'].sudo().search([('id', '=', self.name.department_id.id)],limit=1)

            except UserError:
                pass

    @api.onchange('purchase_value','tax_value')
    def _onchange_value(self):
        if self.purchase_value and not self.tax_value:
            self.total_value = self.purchase_value
        elif self.purchase_value and  self.tax_value:
            self.total_value = self.purchase_value + self.tax_value 


    @api.onchange('quality_factor','competetive_factor','time_factor','service_factor')
    def _onchange_vendor_eval(self):

        if  (self.quality_factor >4 or self.quality_factor <0) or (self.competetive_factor >4 or self.competetive_factor < 0) or \
             (self.time_factor >4 or self.time_factor <0) or (self.service_factor > 4 or self.service_factor <0) :
            raise Warning(_("Please enter rating within 0 - 4"))

        else:

            self.total_eval = (self.quality_factor if self.quality_factor else 0.0 ) + (self.competetive_factor if self.competetive_factor else 0.0 ) + \
            (self.time_factor if self.time_factor else 0.0 ) + (self.service_factor if self.service_factor else 0.0 )


    @api.model
    def create(self, vals):

        tools.image_resize_images(vals)
        vals.update({'is_created':True})
        new_id = super(BtAsset, self).create(vals)
        if new_id.asset_type=='other' and new_id.service_asset == True:
            new_id.state = 'active'

        # if new_id.company_id and new_id.name and new_id.category_id:
        #     new_id.asset_code = new_id.company_id.short_name + '-' + new_id.name.category_id + '-'+ new_id.category_id.categ_no+ str(new_id.department_id.next_support_ticket_number)

        #     new_id.message_post(body=_("Asset %s created with asset code %s")% (new_id.name.name,new_id.asset_code))

        #     #Add one to the next ticket number
        #     write_data = self.env['hr.department'].search([('id', '=', new_id.department_id.id)]).sudo().write({
        #                                                     'next_support_ticket_number': new_id.department_id.next_support_ticket_number+1,
        #                                                     })



        return new_id
    
    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        lot = super(BtAsset, self).write(vals)
        return lot
    
    @api.multi
    def action_move_vals(self):
        for asset in self:
            location_obj = self.env['bt.asset.location'].search([('default_scrap','=',True)])
            if not location_obj:
                raise Warning(_("Please set scrap location first"))
            move_vals = {
                'from_loc_id' : asset.current_loc_id.id,
                'asset_id' : asset.id,
                'to_loc_id' : location_obj.id
                }
            asset_move = self.env['bt.asset.move'].create(move_vals)
            asset_move.action_move()
            asset.current_loc_id = location_obj.id
            asset.state = 'scrapped'
            if asset.state == 'scrapped':
                asset.message_post(body=_("Scrapped"))
        return True

    @api.multi
    def add_inventory(self):
        self.state = 'active'
        # budget_id = self.env['bt.budget'].search([('department_id','=',self.department_id.id),('company_id','=',self.company_id.id),('state','=','approved')])
        # if budget_id:
        #     for budget in budget_id[0]:
        #         budget_line_id = self.env['bt.budget.line'].search([('budget_id','=',budget.id),('category_id','=',self.budget_category_id.id)])
        #         if budget_line_id:
        #             budget.amount_alloted += self.purchase_value
        #             self.state = 'active'
        #             for line in budget_line_id:
        #                 line.claimed += self.purchase_value
        # else:
        #     raise Warning(_(" Budget not found for below Department and Company")) 

                    

class BtAssetLocation(models.Model):   
    _name = "bt.asset.location"
    _description = "Asset Location" 
    
    name = fields.Char(string='Name', required=True)
    asset_ids = fields.One2many('bt.asset','current_loc_id', string='Assets')
    default = fields.Boolean('Default', copy=False)
    default_scrap = fields.Boolean('Scrap')
    short_name = fields.Char(string='Short')
    
    @api.model
    def create(self, vals):
        result = super(BtAssetLocation, self).create(vals)
        obj = self.env['bt.asset.location'].search([('default','=',True)])
        asset_obj = self.env['bt.asset.location'].search([('default_scrap','=',True)])
        if len(obj) > 1 or len(asset_obj) > 1:
            raise ValidationError(_("Default location have already set."))
        return result
    
    @api.multi
    def write(self, vals):
        res = super(BtAssetLocation, self).write(vals)
        obj = self.env['bt.asset.location'].search([('default','=',True)])
        asset_obj = self.env['bt.asset.location'].search([('default_scrap','=',True)])
        if len(obj) > 1 or len(asset_obj) > 1:
            raise ValidationError(_("Default location have already set."))
        return res

class BtAssetCategory(models.Model): 
    _name = "bt.asset.category"
    _description = "Asset Category"
    
    name = fields.Char(string='Name')  
    categ_no = fields.Char(string='Category No')



class BtAssetComponents(models.Model):   
    _name = "bt.asset.component"
    _description = "Asset Components"
    
  
    name = fields.Many2one('bt.component.item', 'Components')
    asset_code = fields.Char(string='Asset Code')
    model_name = fields.Char(string='Model Name')
    serial_no = fields.Char(string='Serial No', track_visibility='always')
    warranty_end = fields.Date(string='Warranty End')
    asset_id = fields.Many2one('bt.asset', 'Assets')
    state = fields.Selection([
            ('active', 'Active'),
            ('scrapped', 'Scrapped')], string='State',track_visibility='onchange', default='active', copy=False)
    extra_asset_id = fields.Many2one('bt.asset', 'Assets')



class BtComponentItem(models.Model):
    _name = "bt.component.item"
    _description = "Components Items" 

    name = fields.Char(string='Name')
    capacity = fields.Char(string='Capacity')

    
# vim:expandtab:smartindent:tabstop=2:softtabstop=2:shiftwidth=2: