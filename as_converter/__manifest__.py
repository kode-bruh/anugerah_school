# -*- coding: utf-8 -*-
{
    'name': "Payment Converter & Importer",

    'summary': """
        Convert and Import Payments
        """,

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
    'depends': ['base', 'asm_student_payment', 'asm_accounting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
}