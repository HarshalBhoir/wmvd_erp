# -*- coding: utf-8 -*-

{
    'name': 'Barcode / QR Code Mgmt',
    'version': '10.0.1.0.1',
    'sequence': 1,
    'summary': """Manages barcodes for marketing team""",
    'description': """This module is used to tracking the barcodes on Coupons.""",
    'category': "Generic Modules/Human Resources",
    'author': 'Harshal Bhoir (Walplast)',
    'website': 'https://harshalbhoir.github.io/',
    'company': 'Walplast',
    'depends': ['base','mail'],
    'data': [
        'security/barcode_security.xml',
        'security/ir.model.access.csv',
        'views/barcode_report_view.xml',
        'views/barcode_marketing_view.xml',
        'views/barcode_scan_view.xml',
        'views/barcode_reports.xml',
        'views/barcode_report_templates.xml',
        'static/src/xml/barcode_marketing_template.xml',
    ],
    'demo': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}


