# -*- coding: utf-8 -*-
{
    'name': "Ahorasoft Templiner Project",
    'category': 'Templiner',
    'version': '1.0.2',
    'author': "Ahorasoft",
    'website': 'http://www.ahorasoft.com',
    "support": "soporte@ahorasoft.com",
    'summary': """
        Ahorasoft Templiner Project""",
    'description': """
        Ahorasoft Templiner Project
    """,
    "images": [],
    "depends": [
        "base","stock","product","report_xlsx","mrp","quality_mrp"
    ],
    'data': [
        # 'security/ir.model.access.csv',#########
        'views/as_mrp_serie.xml',
        'wizard/mrp_product_produce.xml',
        'views/as_report_format.xml',
        'views/as_product_template.xml',
        'views/as_sequence.xml',
        'views/as_mrp_production_work.xml',
        'report/as_report_serie_qr.xml',
      
    ],
    'qweb': [
    ],
    # 'demo': [
    #     'demo/demo.xml',
    # ],
    'installable': True,
    'auto_install': False,
    
}