# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import Warning,UserError
import logging

from collections import OrderedDict


_logger = logging.getLogger(__name__)
class stock_move(models.Model):
    _inherit = "stock.move"
    
    
    sh_stock_move_barcode_mobile = fields.Char(string = "Mobile Barcode")
 

    def default_sh_stock_move_bm_is_cont_scan(self):
        if self.env.user and self.env.user.company_id:
            return self.env.user.company_id.sh_stock_bm_is_cont_scan
    

    
    sh_stock_move_bm_is_cont_scan = fields.Char(string='Continuously Scan?',default = default_sh_stock_move_bm_is_cont_scan, readonly=True)
        
 
     
    
    @api.onchange('sh_stock_move_barcode_mobile')
    def _onchange_sh_stock_move_barcode_mobile(self):
        
        if self.sh_stock_move_barcode_mobile in ['',"",False,None]:
            return
        
        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        
        if self.env.user.company_id.sudo().sh_stock_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"
         
        if self.env.user.company_id.sudo().sh_stock_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"    
                    
        
        if self.picking_id.state not in ['confirmed','assigned']:
            selections = self.picking_id.fields_get()['state']['selection']
            value = next((v[1] for v in selections if v[0] == self.picking_id.state), self.picking_id.state)
            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL + 'You can not scan item in %s state.')% (value)
 
                # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)                
                
            return
                   
        elif self.move_line_ids:
            for line in self.move_line_ids:
                if self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'barcode':
                    if self.product_id.barcode == self.sh_stock_move_barcode_mobile:
                        line.qty_done += 1
                        
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (self.product_id.name,line.qty_done)

                            # self.env.user.notify_info(message, title=_('Succeed'), sticky=False)   
                                                   
                        if self.quantity_done == self.product_uom_qty + 1:                      
#                             warning_mess = {
#                                     'title': _('Alert!'),
#                                     'message' : 'Becareful! Quantity exceed than initial demand!'
#                                 }
#                             return {'warning': warning_mess} 
                            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Becareful! Quantity exceed than initial demand!')
                               
                                # self.env.user.notify_warning(message, title=_('Alert!'), sticky=False)                                                     
                                                         
                        break
                    else:
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            
                            # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)                            
                            
                        return                              
                     
                elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'int_ref':
                    if self.product_id.default_code == self.sh_stock_move_barcode_mobile:
                        line.qty_done += 1
                        
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (self.product_id.name,line.qty_done)
                            # self.env.user.notify_info(message, title=_('Succeed'), sticky=False) 
                                                    
                        if self.quantity_done == self.product_uom_qty + 1:                      
#                             warning_mess = {
#                                     'title': _('Alert!'),
#                                     'message' : 'Becareful! Quantity exceed than initial demand!'
#                                 }
#                             return {'warning': warning_mess}    

                            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Becareful! Quantity exceed than initial demand!')
                                
                                # self.env.user.notify_warning(message, title=_('Alert!'), sticky=False)                                                                    
                        break
                    else:
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                           
                            # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)                            
                            
                        return                             
                    
                elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'sh_qr_code':
                    if self.product_id.sh_qr_code == self.sh_stock_move_barcode_mobile:
                        line.qty_done += 1
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (self.product_id.name,line.qty_done)
                            # self.env.user.notify_info(message, title=_('Succeed'), sticky=False) 
                                                    
                        if self.quantity_done == self.product_uom_qty + 1:                        
                            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Becareful! Quantity exceed than initial demand!')
                                
                                # self.env.user.notify_warning(message, title=_('Alert!'), sticky=False)                       
                                                      
                        break
                    else:
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            
                            # self.env.user.notify_warning(message, title=_('Alert!'), sticky=False)
                            
                        return       
                                                             
                     
                elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'all':
                    lot = 0
                    lote = self.env["stock.production.lot"].search([('name','=',self.sh_stock_move_barcode_mobile)])
                    if lote:
                        lot = lote.product_id.id     
                    if self.product_id.barcode == self.sh_stock_move_barcode_mobile or self.product_id.default_code == self.sh_stock_move_barcode_mobile or self.product_id.sh_qr_code == self.sh_stock_move_barcode_mobile or self.product_id.id == lot:
                        line.qty_done += 1
                        line.lot_id = lote.id
                        line.lot_name = lote.name

                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (self.product_id.name,line.qty_done)
                            # self.env.user.notify_info(message, title=_('Succeed'), sticky=False) 
                                                    
                        if self.quantity_done == self.product_uom_qty + 1:                    
#                             warning_mess = {
#                                     'title': _('Alert!'),
#                                     'message' : 'Becareful! Quantity exceed than initial demand!'
#                                 }
#                             return {'warning': warning_mess}   
                            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Becareful! Quantity exceed than initial demand!')
                                # self.env.user.notify_warning(message, title=_('Alert!'), sticky=False)     
                                                               
                        break
                    else:
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            # self.env.user.notify_warning(message, title=_('Alert!'), sticky=False)
                            
                        return                                
                 
        else:
            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL + 'Pls add all product items in line than rescan.')
                # self.env.user.notify_warning(message, title=_('Alert!'), sticky=False)
                
            return   
         
         
    
    
            
class stock_picking(models.Model):
    _inherit = "stock.picking"


    def default_sh_stock_bm_is_cont_scan(self):
        if self.env.user and self.env.user.company_id:
            return self.env.user.company_id.sh_stock_bm_is_cont_scan
    
    sh_stock_barcode_mobile = fields.Char(string = "Mobile Barcode")
    
    sh_stock_bm_is_cont_scan = fields.Char(string='Continuously Scan?',default = default_sh_stock_bm_is_cont_scan, readonly=True)
        
     
    
    @api.onchange('sh_stock_barcode_mobile')
    def _onchange_sh_stock_barcode_mobile(self):
        
        
        if self.sh_stock_barcode_mobile in ['',"",False,None]:
            return
        
        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        
        if self.env.user.company_id.sudo().sh_stock_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"
         
        if self.env.user.company_id.sudo().sh_stock_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"               
        
        if self and self.state not in ['assigned','draft','confirmed']:
            selections = self.fields_get()['state']['selection']
            value = next((v[1] for v in selections if v[0] == self.state), self.state)
            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL + 'You can not scan item in %s state.')% (value)
                                
                # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)           
            
            return              
            
        
        elif self:
            search_mls = False
            domain = []
            
            if self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'barcode':
                search_mls = self.move_lines.filtered(lambda ml: ml.product_id.barcode == self.sh_stock_barcode_mobile)
                domain = [("barcode","=",self.sh_stock_barcode_mobile)]
            
            elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'int_ref':
                search_mls = self.move_lines.filtered(lambda ml: ml.product_id.default_code == self.sh_stock_barcode_mobile)
                domain = [("default_code","=",self.sh_stock_barcode_mobile)]                
                
            elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'sh_qr_code':
                search_mls = self.move_lines.filtered(lambda ml: ml.product_id.sh_qr_code == self.sh_stock_barcode_mobile)
                domain = [("sh_qr_code","=",self.sh_stock_barcode_mobile)]   
                                
            elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'all':
                lot = 0
                lote = self.env["stock.production.lot"].search([('name','=',self.sh_stock_barcode_mobile)])
                if lote:
                    lot = lote.product_id.id     
                if not self.picking_type_id.show_operations:
                    search_mls = self.move_lines.filtered(lambda ml: ml.product_id.barcode == self.sh_stock_barcode_mobile 
                                                                         or ml.product_id.default_code == self.sh_stock_barcode_mobile
                                                                         or ml.product_id.sh_qr_code == self.sh_stock_barcode_mobile
                                                                         or ml.product_id.id == lot)
                else:
                    search_mls = self.move_line_ids.filtered(lambda ml: ml.product_id.barcode == self.sh_stock_barcode_mobile 
                                                                         or ml.product_id.default_code == self.sh_stock_barcode_mobile
                                                                         or ml.product_id.sh_qr_code == self.sh_stock_barcode_mobile
                                                                         or ml.product_id.id == lot)
                domain = ["|","|","|",
                    ("default_code","=",self.sh_stock_barcode_mobile),
                    ("barcode","=",self.sh_stock_barcode_mobile),
                    ("sh_qr_code","=",self.sh_stock_barcode_mobile),
                    ("id","=",lot),                   
                ]  
                                                
            if search_mls and not self.picking_type_id.show_operations:
                for move_line in search_mls:
                    _logger.debug('\n\n\n\n\nencontro move')
                    # if move_line.show_details_visible:
                    #     if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                    #         message = _(CODE_SOUND_FAIL + 'You can not scan product item for lot/serial directly here, Pls click detail button (at end each line) and than rescan your product item.')
                            
                    #         # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)                              
                            
                    #     return
                            
                            
                                      
                    if self.state == 'draft':
                        move_line.product_uom_qty += 1
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (move_line.product_id.name,move_line.product_uom_qty)
                            _logger.debug('\n\n\n\n\nentro a aumento cantidad')
                            _logger.debug(move_line.product_uom_qty)
                            # self.env.user.notify_info(message, title=_('Succeed'), sticky=False)                                                       
                                                    
                        
                    else:
                        move_line.quantity_done = move_line.quantity_done + 1
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (move_line.product_id.name,move_line.quantity_done)
                            _logger.debug('entro a aumento quantity_done')
                            # self.env.user.notify_info(message, title=_('Succeed'), sticky=False)    
                            
                                                                    
                        if move_line.quantity_done == move_line.product_uom_qty + 1:                    
                            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Becareful! Quantity exceed than initial demand!')
                                # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)
                    
                    break
                                    
            elif self.state == 'draft':
                _logger.debug('\n\n\n\n\nentro a borrador crear  producto')
                if self.env.user.company_id.sudo().sh_stock_bm_is_add_product:
                    if not self.picking_type_id:
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(CODE_SOUND_FAIL + 'You must first select a Operation Type.')
                            # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)
                            
                        return                   
                        
                    search_product = self.env["product.product"].search(domain, limit = 1)
                    if search_product:                                         
                         
                        order_line_val = {
                           "name": search_product.name,
                           "product_id": search_product.id,
                           "product_uom_qty": 1,
                           "price_unit": search_product.lst_price,
                           "lot_id": lote.id,
                           "lot_name": lote.name,
                           "qty_done" : 1,
                           "location_id" : self.location_id.id,
                           "location_dest_id": self.location_dest_id.id,
                           'date_expected' : str(fields.date.today())
                        }      
                        order_line_val2 = {
                           "name": search_product.name,
                           "product_id": search_product.id,
                           "price_unit": search_product.lst_price,
                           "lot_id": lote.id,
                           "lot_name": lote.name,
                           "qty_done" : 1,
                           "location_id" : self.location_id.id,
                           "location_dest_id": self.location_dest_id.id,
                           'date_expected' : str(fields.date.today())
                        }   
                        if not self.picking_type_id.show_operations:
                            if search_product.uom_id:
                                order_line_val.update({
                                    "product_uom": search_product.uom_id.id,                            
                                })    
                            old_lines = self.move_lines
                            new_order_line = self.move_lines.create(order_line_val)
                            self.move_lines = old_lines + new_order_line
                            new_order_line.onchange_product_id()                              
                        else:
                            if search_product.uom_id:
                                order_line_val2.update({
                                    "product_uom_id": search_product.uom_id.id,                            
                                })    
                            old_lines = self.move_line_ids
                            new_order_line = self.move_line_ids.create(order_line_val2)
                            self.move_line_ids = old_lines + new_order_line
                            new_order_line.onchange_product_id() 
                            # if search_product.uom_id:
                            #     order_line_val2.update({
                            #         "product_uom": search_product.uom_id.id,                            
                            #     })    
                            # old_lines2 = self.move_lines
                            # new_order_line2 = self.move_lines.create(order_line_val2)
                            # self.move_lines = old_lines2 + new_order_line2
                            # new_order_line2.onchange_product_id()          

                        
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (new_order_line.product_id.name,new_order_line.product_uom_qty)
                            
                            # self.env.user.notify_info(message, title=_('Succeed'), sticky=False)                               
                                                                         
                                            
                    else: 
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)
                            
                        return                                          
                                           
                else:
                    if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                        message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                        # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)
                        
                    return    
            else:
                _logger.debug('\n\n\n\n\nScanned Internal Reference/Barcode not exist in any product')
                if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                    message = _(CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                    
                    # self.env.user.notify_warning(message, title=_('Failed'), sticky=False)
                    
                return             
        