# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError

class StockInventory(models.Model):
    _inherit = "stock.inventory"
    
    def default_sh_inventory_adjt_bm_is_cont_scan(self):
        if self.env.user and self.env.user.company_id:
            return self.env.user.company_id.sh_inventory_adjt_bm_is_cont_scan
    
    sh_inventory_adjt_barcode_mobile = fields.Char(string = "Mobile Barcode")
    
    sh_inventory_adjt_bm_is_cont_scan = fields.Char(string='Continuously Scan?',default = default_sh_inventory_adjt_bm_is_cont_scan, readonly=True)
        
 
    
    @api.onchange('sh_inventory_adjt_barcode_mobile')
    def _onchange_sh_inventory_adjt_barcode_mobile(self):
        
        if self.sh_inventory_adjt_barcode_mobile in ['',"",False,None]:
            return
        
        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        if self.env.user.company_id.sudo().sh_inventory_adjt_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"
        
        if self.env.user.company_id.sudo().sh_inventory_adjt_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"
                    
            
        #step 1: state validation.
        if self and self.state != 'confirm':
            selections = self.fields_get()['state']['selection']
            value = next((v[1] for v in selections if v[0] == self.state), self.state)
            
            if self.env.user.company_id.sudo().sh_inventory_adjt_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL + 'You can not scan item in %s state.')% (value)
                self.env.user.notify_warning(message, title=_('Failed'), sticky=False)     
                
            return
        
        elif self:
            search_lines = False
            domain = []
            
            if self.env.user.company_id.sudo().sh_inventory_adjt_barcode_mobile_type == 'barcode':
                search_lines = self.line_ids.filtered(lambda l: l.product_id.barcode == self.sh_inventory_adjt_barcode_mobile)
                domain = [("barcode","=",self.sh_inventory_adjt_barcode_mobile)]
            
            elif self.env.user.company_id.sudo().sh_inventory_adjt_barcode_mobile_type == 'int_ref':
                search_lines = self.line_ids.filtered(lambda l: l.product_id.default_code == self.sh_inventory_adjt_barcode_mobile)
                domain = [("default_code","=",self.sh_inventory_adjt_barcode_mobile)]
            
            elif self.env.user.company_id.sudo().sh_inventory_adjt_barcode_mobile_type == 'sh_qr_code':
                search_lines = self.line_ids.filtered(lambda l: l.product_id.sh_qr_code == self.sh_inventory_adjt_barcode_mobile)
                domain = [("sh_qr_code","=",self.sh_inventory_adjt_barcode_mobile)]
                
            elif self.env.user.company_id.sudo().sh_inventory_adjt_barcode_mobile_type == 'all':
                lot = 0
                lote = self.env["stock.production.lot"].search([('name','=',self.sh_inventory_adjt_barcode_mobile)])
                if lote:
                    lot = lote.product_id.id     
                search_lines = self.line_ids.filtered(lambda l: l.product_id.barcode == self.sh_inventory_adjt_barcode_mobile 
                                                      or l.product_id.default_code == self.sh_inventory_adjt_barcode_mobile
                                                      or l.product_id.sh_qr_code == self.sh_inventory_adjt_barcode_mobile or l.product_id.id == lot)
                domain = ["|","|","|",
                    ("default_code","=",self.sh_inventory_adjt_barcode_mobile),
                    ("barcode","=",self.sh_inventory_adjt_barcode_mobile),
                    ("sh_qr_code","=",self.sh_inventory_adjt_barcode_mobile),
                    ("id","=",lot),                   
                ]
                
           
                
                              
            
            if search_lines:
                for line in search_lines:
                    line.product_qty += 1
                    
                    if self.env.user.company_id.sudo().sh_inventory_adjt_bm_is_notify_on_success:
                        message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (line.product_id.name,line.product_qty)                        
                        self.env.user.notify_info(message, title=_('Succeed'), sticky=False)   
                                                     
                    break
            else:
                search_product = self.env["product.product"].search(domain, limit = 1)
                if search_product:                    
                    inventory_line_val = {
                            'display_name': search_product.name,
                            'product_id': search_product.id,
                            'location_id':self.location_id.id,   
                            'product_qty': 1,
                            'inventory_id': self.id
                    }
                    if search_product.uom_id:
                        inventory_line_val.update({
                            'product_uom_id': search_product.uom_id.id,                            
                            })
                    self.env["stock.inventory.line"].new(inventory_line_val)     
                    
                    if self.env.user.company_id.sudo().sh_inventory_adjt_bm_is_notify_on_success:
                        message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (search_product.name,1)                       
                        self.env.user.notify_info(message, title=_('Succeed'), sticky=False)   
                                              
                else:
                    if self.env.user.company_id.sudo().sh_inventory_adjt_bm_is_notify_on_fail:    
                        message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')                  
                        self.env.user.notify_warning(message, title=_('Failed'), sticky=False)     
                    return
                    