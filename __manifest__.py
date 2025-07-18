# -*- coding: utf-8 -*-
{
    'name': 'Inouk Attachments Storage (ir.attachments)',
    'summary': 'Simple GUI to manage attachments storage locations.\n    This addon is compatible with Odoo 13, 14, 15, 16\n    ',
    'version': '13.0.1',
    'category': 'Extra Tools',
    'license': 'LGPL-3',
    'author': 'Cyril MORISSE',
    'website': 'https://github.com/cmorisse',
    'contributors': [
        'Cyril MORISSE <cmorisse@boxes3.net>'
    ],
    'depends': ['base', 'inouk_message_queue'],
    'data': [
        'data/ir_config_parameter.xml',
        'views/ir_attachment_views.xml',
        'views/res_config_settings_views.xml'
    ],
    'application': False,
    'installable': True,
    'auto_install': False
}
