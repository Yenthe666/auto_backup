## 1. Prerequisites
This module needs the Python library pysftp, otherwise it cannot be installed and used. Install pysftp through the command <code>sudo pip install pysftp</code>

## 2. Which version to choose?
Version 12.0 is the latest stable version for this module and is compatible with the latest Odoo version (Odoo 12).
The versions 8.0, 9.0, 10.0 and 11.0 of this module are tested and verified to work for their specific Odoo versions. The master version is the development version and will be for the next Odoo version.
The master version is still in testing and contains the newest features, which might still have problems/error.<br/>
<b>Tip:</b> At this point the master version is being rewritten to drop the pysftp library need, please don't use this version at this point.<br/>
If you need to connect to a remote FTP server on another port than port 22 you should download and install the 9.0, 10.0, 11.0, 12.0 or master version. Version 8 does not support another port than 22.

## 3. Guide / documentation
Need more help with this module or want a guide about how to set this up? <h4><a href="http://www.odoo.yenthevg.com/automated-backups-in-odoo/" target="_Blank">Follow my tutorial!</a></h4>

## 4. Important information
### 4.1 `limit_time_real` parameter
When you've configured your Odoo instance to run with workers you should change the default value of `limit_time_real` (as this defaults to 120). You can configure the value in `/etc/odoo/your_odoo.conf` to the appropriate number in case of a large database backup. This is required when `max_cron_threads` > 0 to avoid worker timeout during the backup.

### 4.2 `list_db` parameter
The backup module will only work when `list_db` is set to `True` (or is not configured). If `list_db` is set to `False` the Odoo instance will block looking for the databases and the module will fail. Make sure it is always on (or script a workaround).

## 5. Bugs or problems
Please post them here under 'Issues' and I will get back to you as soon as I can!
