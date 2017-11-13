<h3>Prerequisites</h3>
This module needs the Python library pysftp, otherwise it cannot be installed and used. Install pysftp through the command <code>sudo pip install pysftp</code>

<h3>Version 8.0 or 9.0 or master?</h3>
Version 8.0 is the stable version for this module and build for Odoo V8, 9.0 is made for Odoo V9.
The version 8.0 of this module is tested and verified, 9.0 is still in progress / test. The master version is the development version.
The master version is still in testing and contains the newest features, which might still have problems/error.
If you need to connect to a remote FTP server on another port than port 22 you should download and install the 9.0 or master version. Version 8 does not (yet) support another port than 22.

## Important information
### `limit_time_real` parameter
When you've configured your Odoo instance to run with workers you should change the default value of `limit_time_real` (as this defaults to 120). You can configure the value in `/etc/odoo/your_odoo.conf` to the appropriate number in case of a large database backup. This is required when `max_cron_threads` > 0 to avoid worker timeout during the backup.

### `list_db` parameter
The backup module will only work when `list_db` is set to `True` (or is not configured). If `list_db` is set to `False` the Odoo instance will block looking for the databases and the module will fail. Make sure it is always on (or script a workaround).

<h3>Guide / documentation</h3>
Need more help with this module or want a guide about how to set this up? <h4><a href="http://www.odoo.yenthevg.com/automated-backups-in-odoo/" target="_Blank">Follow my tutorial!</a></h4>

<h3>Errors / Suggestions</h3>
Please post them here under 'Issues' and I will get back to you as soon as I can!
