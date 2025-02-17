# -*- coding: utf-8 -*-
{
    'name': "Student Payment",

    'summary': """
        Monthly Fee & One Time Payment""",

    'description': """
    """,

    'author': "Kode-Bruh",
    'website': "www.kode-bruh.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'asm_student', 'asm_accounting', 'mail'],

    # always loaded
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/inherit.xml',
        'views/res_config.xml',
        'cron/cron.xml',
        'report/invoice_report.xml',
        'report/invoice_list_report.xml',
        'report/student_contract.xml',
        'report/financial_report.xml',
        'data/as_selection.xml',
        'wizard/create_invoice_wizard.xml',
        'wizard/edit_invoice_wizard.xml',
        'wizard/move_payment_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}