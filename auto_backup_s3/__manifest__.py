# -*- coding: utf-8 -*-
{
    'name': "Database auto-backup s3",
    'summary': 'Automated backups s3',
    'description': """
    """,
    'author': "Heliconia Solutions Pvt. Ltd.",
    'website': "https://www.heliconia.io/",
    'category': 'Administration',
    "version": "18.0.1.0.0",
    'installable': True,
    'license': 'LGPL-3',
    'module_type': 'official',
    'depends': ['base', 'auto_backup'],
    'data': [
        'views/backup_view.xml',
    ],
}
