# -*- coding: utf-8 -*-
{
    "name": "Database auto-backup for Odoo.sh",
    "summary": "Automated backups for Odoo.sh",
    "description": """
        Allow automated backups from Odoo.sh to a remote (FTP) server
    """,
    "author": "Yenthe Van Ginneken",
    "website": "https://mainframemonkey.com",
    "category": "Administration",
    "version": "16.0.1.0.1",
    "installable": True,
    "license": "LGPL-3",

    # any module necessary for this one to work correctly
    "depends": [
        "auto_backup"
        ],

    # always loaded
    "data": [
        "views/odoosh_db_backup_view.xml",
    ],
}
