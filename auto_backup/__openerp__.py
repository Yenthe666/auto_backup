# -*- encoding: utf-8 -*-
{
    'name' : 'Database Auto-Backup',
    'version' : '10.0',
    'author' : 'VanRoey.be - Yenthe Van Ginneken',
    'website' : 'http://www.vanroey.be/applications/bedrijfsbeheer/odoo',
    'category' : 'Generic Modules',
    'summary': 'Backups',
    'description': """The Database Auto-Backup module enables the user to make configurations for the automatic backup of the database. Backups can be taken on the local system or on a remote server, through SFTP.
You only have to specify the hostname, port, backup location and databasename (all will be pre-filled by default with correct data.
If you want to write to an external server with SFTP you will need to provide the IP, username and password for the remote backups.
The base of this module is taken from Odoo SA V6.1 (https://www.odoo.com/apps/modules/6.0/auto_backup/) and then upgraded and heavily expanded.
This module is made and provided by VanRoey.be.

Automatic backup for all such configured databases can then be scheduled as follows:  
                      
1) Go to Settings / Technical / Automation / Scheduled actions.
2) Search the action 'Backup scheduler'.
3) Set it active and choose how often you wish to take backups.
4) If you want to write backups to a remote location you should fill in the SFTP details.
""",
    'depends' : ['base'],
    'data': [
      'views/bkp_conf_view.xml',
      'data/backup_data.xml',
    ],
    'auto_install': False,
    'installable': True
}
