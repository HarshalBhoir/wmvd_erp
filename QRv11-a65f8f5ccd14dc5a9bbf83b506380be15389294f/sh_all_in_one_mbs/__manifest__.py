# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name": "All in One Mobile Barcode Scanner",

    "author" : "Softhealer Technologies",
    
    "website": "https://www.softhealer.com",
    
    "support": "support@softhealer.com",
        
    "version": "11.0.1",
        
    "category": "",

   "summary": "invoice mobile barcode scanner, bom mobile barcode scanner app, stock adjustment barcode scan, sales mobile barcode scanner, product mobile barcode scanner, inventory mobile qrcode app, invoice mobile qrcode scanner, purchase barcode/qrcode module",
        
    "description": """
Do you want to scan Barcode/QRCode in your mobile/tablet? Do your time wasting in odoo operations by manual product selection ? So here is the solutions this modules useful do quick operations of odoo mobile/tablet Barcode/QRCode scanner. You no need to select product and do one by one. scan it and you done! So be very quick in all operations of odoo in mobile/tablet and cheers!

 All In One Mobile Barcode Scanner For Sales, Purchase, Stock Adjustment, Invoice, Inventory, BOM Odoo.
 Inventory Mobile Barcode Scanner Odoo, Invoice Mobile Barcode Scanner Module, BOM Mobile Barcode Scanner Odoo, Stock Adjustment Mobile Barcode Scanner Odoo, Purchase Mobile Barcode Scanner Odoo, Sales Mobile Barcode Scanner Odoo.
All In One Mobile Barcode Scanner App,Package All in one Mobile barcode scanner,  Operations Of Sales, Purchase In Barcode Module, Invoice In Barcode, Inventory In Barcode, Bom In Barcode, Scrap Using Barcode Odoo.

Add products by barcode    
Add products using barcode    

sales mobile barcode scanner
so barcode scanner
so mobile barcode scanner
sale mobile barcode scanner

po mobile barcode scanner
purchase order mobile barcode scanner
purchase order barcode scanner
po barcode scanner
    
inventory mobile barcode scanner    
stock mobile barcode scanner
inventory barcode scanner
stock barcode scanner

inventory adjustment mobile barcode scanner
stock adjustment mobile barcode scanner
inventory adjustment barcode scanner
stock adjustment barcode scanner

invoice barcode scanner
bill barcode scanner
credit note barcode scanner
debit note barcode scanner
invoice barcode mobile scanner
bill barcode mobile scanner
credit note barcode mobile scanner
debit note barcode mobile scanner

    """,
    
    "depends": [
        
            "mrp", 
            "stock", 
            "account", 
            "account_invoicing",
            "purchase", 
            "sale_management",
            "sh_product_qrcode_generator",
            #"web_notify",
                        
            ],
    
    "data": [
        
        "views/asset.xml",
        
        "sh_sale_barcode_mobile/views/res_config_settings_views.xml",
        "sh_sale_barcode_mobile/views/sale_view.xml",
            
        "sh_purchase_barcode_mobile/views/res_config_settings_views.xml",
        "sh_purchase_barcode_mobile/views/purchase_view.xml",            
                
        "sh_invoice_barcode_mobile/views/res_config_settings_views.xml",
        "sh_invoice_barcode_mobile/views/account_view.xml",
                     
        "sh_bom_barcode_mobile/views/res_config_settings_views.xml",
        "sh_bom_barcode_mobile/views/mrp_view.xml",
         
        "sh_inventory_adjustment_barcode_mobile/views/res_config_settings_views.xml",
        "sh_inventory_adjustment_barcode_mobile/views/stock_view.xml",
          
        "sh_inventory_barcode_mobile/views/res_config_settings_views.xml",
        "sh_inventory_barcode_mobile/views/stock_view.xml",
     
        "sh_product_barcode_mobile/security/product_bm_security.xml",     
        "sh_product_barcode_mobile/views/res_config_settings_views.xml",
        "sh_product_barcode_mobile/wizard/sh_product_barcode_mobile_wizard.xml", 
             

    ],
    "images": ["static/description/background.png", ],
    
    "installable": True,
    "application": True,
    "autoinstall": False,
    
    "price": 120,
    "currency": "EUR"        
}
