# -*- coding: utf-8 -*-
{
    'name': "Accounting Master Data",

    'summary': """
        Credit & Debit Operations, Accounting Book.""",

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
    'depends': ['base', 'asm_student'],

    # always loaded
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/ir_action.xml',
        'views/views.xml',
        'views/inherit.xml',
        'views/res_config.xml',
        'report/transaction_report.xml',
        'wizard/change_journal_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}