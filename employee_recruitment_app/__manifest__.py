# -*- coding: utf-8 -*-

{
    "name" : "Employee Recruitment",
    "author": "Edge Technologies",
    "version" : "11.0.1.0",
    "live_test_url":'https://youtu.be/qyYQnlh1Kpo',
    "images":["static/description/main_screenshot.png"],
    'summary': 'Employee Recruitment is designed to recruit multiple applicant with experience or fresher.',
    "description": """ This app is designed to recruit multiple applicant by the HR according to the applicants. Helps to shortlist employees. """, 
    "depends" : ['base','hr_recruitment','stock'],
    "data": [
        'security/staff_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/applicant_inherit_views.xml',
        'views/staff_recruitment_views.xml',
    ],
    "auto_install": False,
    "installable": True,
    "price": 000,
    "currency": 'EUR',
    "category" : "Human Resource",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
