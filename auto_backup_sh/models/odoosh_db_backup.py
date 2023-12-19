
import os
import datetime
import time
import shutil
import json
import tempfile
import gzip
from odoo.exceptions import ValidationError

from odoo import models, fields, api, tools, _
import odoo

import logging
_logger = logging.getLogger(__name__)

try:
    import paramiko
except ImportError:
    raise ImportError(
        'This module needs paramiko to automatically write backups to the FTP through SFTP. '
        'Please install paramiko on your system. (sudo pip3 install paramiko)')


class DbBackup(models.Model):
    _inherit = 'db.backup'

    is_odoo_sh_instance = fields.Boolean(
        string="Is Odoo.sh instance?",
        default=True,
        help="Flag used to determine if the Odoo instance is on Odoo.sh or not.")

    @api.onchange('is_odoo_sh_instance')
    def _onchange_is_odoo_sh_instance(self):
        if self.is_odoo_sh_instance:
            self.update({
                'backup_type' :'zip',
                'sftp_write': True
            })
    
    @api.constrains('backup_type', 'is_odoo_sh_instance')
    def _constrains_is_odoo_sh_instance(self):
        if self.is_odoo_sh_instance and self.backup_type != 'zip':
            raise ValidationError(_('The "Backup Type" has to be set to "Zip" for Odoo.sh instances'))
        if self.is_odoo_sh_instance and not self.sftp_write:
            raise ValidationError(_('The option "Write to external server with sftp" must be activated as we can only backup to remote instances with Odoo.sh.'))

    def _take_dump(self, db_name, stream, model, backup_format='zip', odoo_sh=True):
        if odoo_sh:
            if backup_format == 'zip':
                with tempfile.TemporaryDirectory() as dump_dir:
                    filestore = os.path.join(os.getcwd(), 'backup.daily', f'{db_name}_daily', 'home', 'odoo', 'data', 'filestore', db_name)
                    # filestore = os.path.join(os.getcwd(), 'backup.daily', f'{db_name}_daily', db_name)
                    if os.path.exists(filestore):
                        shutil.copytree(filestore, os.path.join(dump_dir, 'filestore'))

                    with open(os.path.join(dump_dir, 'manifest.json'), 'w') as fh:
                        db = odoo.sql_db.db_connect(db_name)
                        with db.cursor() as cr:
                            json.dump(self._dump_db_manifest(cr), fh, indent=4)

                    dump_sql_path = os.path.join(os.getcwd(), 'backup.daily', f"{db_name}_daily.sql.gz")
                    with gzip.open(dump_sql_path, 'rb') as dump_sql_in, open(os.path.join(dump_dir, 'dump.sql'), 'wb') as dump_sql_out:
                        shutil.copyfileobj(dump_sql_in, dump_sql_out)

                    if stream:
                        odoo.tools.osutil.zip_dir(dump_dir, stream, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
                    else:
                        t=tempfile.TemporaryFile()
                        odoo.tools.osutil.zip_dir(dump_dir, t, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
                        t.seek(0)
                        return t
        else:
            return super()._take_dump(db_name, stream, model, backup_format)

    @api.model
    def schedule_backup(self):
        db_backup_obj = self.env['db.backup']
        odoo_sh_db_backups = db_backup_obj.search([('is_odoo_sh_instance','=', True)])
        for backup in odoo_sh_db_backups:
            backup_path_location = backup.folder
            ts = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            backup_file_name = "%s_%s.%s" % (backup.name, ts, backup.backup_type)
            file_path = os.path.join(backup_path_location, backup_file_name)

            try:
                fp = open(file_path, 'wb')
                self._take_dump(backup.name, fp, 'db.backup', backup.backup_type, odoo_sh=True)
                fp.close()
            except Exception as error:
                _logger.info("Something Went Wrong : %s", str(error))
                os.remove(file_path)
                continue
            
            # Check if user wants to write to SFTP or not.
            if backup.sftp_write:
                try:
                    # Store all values in variables
                    dir = backup.folder
                    path_to_write_to = backup.sftp_path
                    ip_host = backup.sftp_host
                    port_host = backup.sftp_port
                    username_login = backup.sftp_user
                    password_login = backup.sftp_password

                    try:
                        s = paramiko.SSHClient()
                        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        s.connect(ip_host, port_host, username_login, password_login, timeout=20)
                        sftp = s.open_sftp()
                    except Exception as error:
                        _logger.critical('Error connecting to remote server! Error: %s', str(error))

                    try:
                        sftp.chdir(path_to_write_to)
                    except IOError:
                        # Create directory and subdirs if they do not exist.
                        current_directory = ''
                        for dir_element in path_to_write_to.split('/'):
                            current_directory += dir_element + '/'
                            try:
                                sftp.chdir(current_directory)
                            except:
                                _logger.info('(Part of the) path didn\'t exist. Creating it now at %s', current_directory)
                                # Make directory and then navigate into it
                                sftp.mkdir(current_directory, 777)
                                sftp.chdir(current_directory)
                                pass
                    sftp.chdir(path_to_write_to)
                    # Loop over all files in the directory.
                    for f in os.listdir(dir):
                        if backup.name in f:
                            fullpath = os.path.join(dir, f)
                            if os.path.isfile(fullpath):
                                try:
                                    sftp.stat(os.path.join(path_to_write_to, f))
                                    _logger.debug('File %s already exists on the remote FTP Server ------ skipped', fullpath)
                                # This means the file does not exist (remote) yet!
                                except IOError:
                                    try:
                                        sftp.put(fullpath, os.path.join(path_to_write_to, f))
                                        _logger.info('Copying File % s------ success', fullpath)
                                    except Exception as err:
                                        _logger.critical('We couldn\'t write the file to the remote server. Error: %s', str(err))

                    # Navigate in to the correct folder.
                    sftp.chdir(path_to_write_to)

                    _logger.debug("Checking expired files")
                    # Loop over all files in the directory from the back-ups.
                    # We will check the creation date of every back-up.
                    
                    for file in sftp.listdir(path_to_write_to):
                        if backup.name in file:
                            # Get the full path
                            fullpath = os.path.join(path_to_write_to, file)
                            # Get the timestamp from the file on the external server
                            timestamp = sftp.stat(fullpath).st_mtime
                            createtime = datetime.datetime.fromtimestamp(timestamp)
                            now = datetime.datetime.now()
                            delta = now - createtime
                            # If the file is older than the days_to_keep_sftp (the days to keep that the user filled in
                            # on the Odoo form it will be removed.
                            if delta.days >= backup.days_to_keep_sftp:
                                # Only delete files, no directories!
                                if ".dump" in file or '.zip' in file:
                                    _logger.info("Delete too old file from SFTP servers: %s", file)
                                    sftp.unlink(file)
                    # Close the SFTP session.
                    sftp.close()
                    s.close()
                except Exception as e:
                    try:
                        sftp.close()
                        s.close()
                    except:
                        pass
                    _logger.error('Exception! We couldn\'t back up to the FTP server. Here is what we got back '
                                  'instead: %s', str(e))
                    # At this point the SFTP backup failed. We will now check if the user wants
                    # an e-mail notification about this.
                    if backup.send_mail_sftp_fail:
                        try:
                            ir_mail_server = self.env['ir.mail_server'].search([], order='sequence asc', limit=1)
                            message = "Dear,\n\nThe backup for the server " + backup.host + " (IP: " + backup.sftp_host + \
                                      ") failed. Please check the following details:\n\nIP address SFTP server: " + \
                                      backup.sftp_host + "\nUsername: " + backup.sftp_user + \
                                      "\n\nError details: " + tools.ustr(e) + \
                                      "\n\nWith kind regards"
                            catch_all_domain = self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
                            response_mail = "auto_backup@%s" % catch_all_domain if catch_all_domain else self.env.user.partner_id.email
                            msg = ir_mail_server.build_email(response_mail, [backup.email_to_notify],
                                                             "Backup from " + backup.host + "(" + backup.sftp_host +
                                                             ") failed",
                                                             message)
                            ir_mail_server.send_email(msg)
                        except Exception:
                            pass

        return super(DbBackup, db_backup_obj.search([('is_odoo_sh_instance','=', False)])).schedule_backup()
