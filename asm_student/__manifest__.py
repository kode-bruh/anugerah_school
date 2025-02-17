# -*- coding: utf-8 -*-
{
    'name': "Students Master Data",

    'summary': """
        Students, Classes and Miscellaneous Operations.""",

    'description': """
        What's included?
        - Student table
        - Classes table
        - Student's State table
    """,

    'author': "Kode-Bruh",
    'website': "www.kode-bruh.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        'security/security_group.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'default/default_records.xml',
        'wizard/move_class_wizard.xml',
        'wizard/change_class_student_wizard.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}