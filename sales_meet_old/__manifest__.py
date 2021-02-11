# -*- coding: utf-8 -*-


{
    'name': 'Walplast CRM & Utilities',
    'category': 'CRM',
    'version': '1.0',
    'sequence': 1,
    'description': """
    Task on Lead, Add Task from lead, Task Lead, Create Project Task from Lead, 
    Add task from mail, Create task from mail.Task on lead, add task on lead, tasks on lead,
     lead tasks, automated task by lead, 
    Generate task from lead.
""",
    'author': 'Harshal Bhoir (Walplast)',
    'website': 'https://harshalbhoir.github.io/',
    'images': [],
    'depends': ['base', 'calendar', 'crm', 'sale', 'project','hr','purchase','hr_expense','website', 'mail','document',
                'hr_timesheet','hr_holidays','stock','sales_team','account','hr_payroll','hr_attendance','hr_recruitment'],
    
    'data': [ 
            'security/sales_meet_security.xml',
            'security/lettermgmnt_security.xml',
            'security/ir.model.access.csv',
            'static/src/xml/sales_meet_template.xml',
            'template/lead_assign_action_data.xml',
            'template/expense_template.xml',
            'template/booking_template.xml',
            'template/credit_note_template.xml',
            'template/sampling_template.xml',
            'template/delivery_mail_template.xml',
            'wizard/credit_note_line_import_view.xml',
            'views/expense_extension_view.xml',
            'views/grade_master_view.xml',
            'report/sale_register_report_view.xml',
            'report/meetings_details_report_view.xml',
            'report/sample_stock_details_report_view.xml',
            'report/lead_details_report_view.xml',
            'report/project_details_report_view.xml',
            'report/hr_expense_xls_view.xml',
            'report/employee_data_xls.xml',
            'report/invoice_delivery_report_view.xml',
            'report/exec_stock_details_report_view.xml',
            
            'views/sales_meet_view.xml',
            'views/partner_extension_view.xml',
            'views/account_extension_view.xml',
            'views/credit_note_view.xml',
            # 'views/db_connect_view.xml',
            'views/product_extension_view.xml',
            'views/user_extension_view.xml',
            'views/quotation_extension_view.xml',
            'views/expense_automation_view.xml',
            'views/hr_extension_view.xml',
            'views/ho_lead_view.xml',
            'views/org_master_view.xml',
            'views/crm_extension_view.xml',
            'views/hr_attendance_extension_view.xml',
            'report/exec_attendance_details_report_view.xml',

            'template/mail_action_data.xml',
            'views/posting_error_view.xml',
            'views/bank_payment_view.xml',
            'views/invoice_payment_view.xml',
            'views/bank_receipt_view.xml',
            'views/external_db_connect_view.xml',

            'wizard/mail_compose_message_view.xml',

            'data/website.menu.csv',
            'data/external.db.configuration.csv',
            'views/website_hrms_form_templates.xml',
            'views/logistic_trail_view.xml',
            'views/sample_extension_view.xml',
            # 'views/meetings_dashboard_views.xml',

            'data/scheduler_data.xml',
            'data/sequence_data.xml',

            "data/letter_sequence.xml",
            'views/fo_visit_master_view.xml',
            'report/report.xml',
            'report/fo_property_label.xml',
            'report/fo_visitor_label.xml',
            'report/visitors_report.xml',
            'views/letter_mgmt_master_view.xml',
            'views/ticket_booking_view.xml',
            'views/lettermgmt_menus.xml',
            'views/knowage_reports_menus.xml',
            'views/sales_meet_menus.xml',

             
    ],
    "qweb": [
        "template/remove_odoo.xml",
        "static/src/xml/meetings_dashboard.xml"
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

# https://stackoverflow.com/questions/39223570/how-to-set-a-field-editable-only-for-a-group-in-odoo9