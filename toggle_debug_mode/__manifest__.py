# -*- coding: utf-8 -*-
# © 2017 Jérome Guerriat
# © 2017 Niboo SPRL (<https://www.niboo.be/>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    'name': 'Toggle Developer Mode',
    'summary': 'Allow to easily switch to developer mode from any page',
    'version': '10.0.1.0.0',
    'author': 'Niboo',
    'description': '''
This module allow the technical group to quickly switch to developer mode
    ''',
    'license': 'AGPL-3',
    'website': 'https://www.niboo.be/',
    'images': [
    ],
    'depends': [
        'web'
    ],
    'data': [
        'views/assets_backend.xml',
    ],
    'qweb': [
        'static/src/xml/templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}
