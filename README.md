## 1. Prerequisites
This module needs the Python library pysftp, otherwise it cannot be installed and used. Install pysftp through the command <code>sudo pip install pysftp</code>

## 2. Which version to choose?
Version 13.0 is the latest stable version for this module and is compatible with the latest Odoo version (Odoo 13).
The versions 8.0, 9.0, 10.0,11.0 and 12.0 of this module are tested and verified to work for their specific Odoo versions. The master version is the development version and will be for the next Odoo version.
The master version is still in testing and contains the newest features, which might still have problems/error.<br/>
<b>Tip:</b> At this point the master version is being rewritten to drop the pysftp library need, please don't use this version at this point.<br/>
If you need to connect to a remote FTP server on another port than port 22 you should download and install the 9.0, 10.0, 11.0, 12.0, 13.0 or master version. Version 8 does not support another port than 22.

## 3. Guide / documentation
Need more help with this module or want a guide about how to set this up? <h4><a href="http://www.odoo.yenthevg.com/automated-backups-in-odoo/" target="_Blank">Follow my tutorial!</a></h4>

## 4. Important information
### 4.1 `limit_time_real` parameter
When you've configured your Odoo instance to run with workers you should change the default value of `limit_time_real` (as this defaults to 120). You can configure the value in `/etc/odoo/your_odoo.conf` to the appropriate number in case of a large database backup. This is required when `max_cron_threads` > 0 to avoid worker timeout during the backup.

### 4.2 `list_db` parameter
The backup module only used to work when `list_db` was set to `True` (or was not configured). Since 28/02/2020 ( https://github.com/Yenthe666/auto_backup/commit/c7d0512a0d0b2d42662831008e7a9316b264f23e) you no longer have to have the database manager enabled and the module can also take backups without it being exposed. If you run the backup module before this commit and want to run it without the database manager being exposed you should update the backup module to the latest version first.
It is advised to disable the database manager for security purposes. See https://www.odoo.com/documentation/13.0/setup/deploy.html#database-manager-security for more information about this subject.

### 4.3 `--load` / `server_wide_modules` parameter
In V12 and V13 Odoo will need the values 'base' and 'web' set if you use the `--load` (or `server_wide_modules`) parameter. Without these values set you will get a 404 NOT FOUND from the backup module.
For more information see https://github.com/Yenthe666/auto_backup/issues/122

## 5. Bugs or problems
Please post them here under 'Issues' and I will get back to you as soon as I can!
