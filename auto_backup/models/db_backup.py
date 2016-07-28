# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import xmlrpclib
import socket
import os
import time
import datetime
import base64
import re
import logging

try:
    import pysftp
except ImportError:
    raise ImportError('This module needs pysftp to automaticly write backups to the FTP through SFTP. Please install pysftp on your system. (sudo pip install pysftp)')
from openerp import models, fields, api, tools, _

_logger = logging.getLogger(__name__)

def execute(connector, method, *args):
    res = False
    try:        
        res = getattr(connector,method)(*args)
    except socket.error,e:        
            raise e
    return res

addons_path = tools.config['addons_path'] + '/auto_backup/DBbackups'

class db_backup(models.Model):
    _name = 'db.backup'
    
    def get_db_list(self, host, port, context={}):
        uri = 'http://' + host + ':' + port
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
        db_list = execute(conn, 'list')
        return db_list

    def _get_db_name(self):
        dbName = self._cr.dbname
        return dbName
        
    # Columns for local server configuration
    host = fields.Char('Host', size=100, required=True, default='localhost')
    port = fields.Char('Port', size=10, required=True, default=8069)
    name = fields.Char('Database', size=100, required=True,help='Database you want to schedule backups for', default=_get_db_name)
    folder = fields.Char('Backup Directory', size=100, help='Absolute path for storing the backups', required='True', default='/odoo/backups')
    backup_type = fields.Selection([('zip', 'Zip'), ('dump', 'Dump')], 'Backup Type', required=True, default='zip')
    autoremove = fields.Boolean('Auto. Remove Backups', help='If you check this option you can choose to automaticly remove the backup after xx days')
    days_to_keep = fields.Integer('Remove after x days', help="Choose after how many days the backup should be deleted. For example:\nIf you fill in 5 the backups will be removed after 5 days.", required=True)
                   
    # Columns for external server (SFTP)
    sftp_write = fields.Boolean('Write to external server with sftp', help="If you check this option you can specify the details needed to write to a remote server with SFTP.")
    sftp_path = fields.Char('Path external server', help='The location to the folder where the dumps should be written to. For example /odoo/backups/.\nFiles will then be written to /odoo/backups/ on your remote server.')
    sftp_host = fields.Char('IP Address SFTP Server', help='The IP address from your remote server. For example 192.168.0.1')
    sftp_port = fields.Integer('SFTP Port', help='The port on the FTP server that accepts SSH/SFTP calls.', default=22)
    sftp_user = fields.Char('Username SFTP Server', help='The username where the SFTP connection should be made with. This is the user on the external server.')
    sftp_password = fields.Char('Password User SFTP Server', help='The password from the user where the SFTP connection should be made with. This is the password from the user on the external server.')
    days_to_keep_sftp = fields.Integer('Remove SFTP after x days', help='Choose after how many days the backup should be deleted from the FTP server. For example:\nIf you fill in 5 the backups will be removed after 5 days from the FTP server.', default=30)
    send_mail_sftp_fail = fields.Boolean('Auto. E-mail on backup fail', help='If you check this option you can choose to automaticly get e-mailed when the backup to the external server failed.')
    email_to_notify = fields.Char('E-mail to notify', help='Fill in the e-mail where you want to be notified that the backup failed on the FTP.')
    
    def _check_db_exist(self):
        for record in self.browse(self):
            db_list = self.get_db_list(self, record.host, record.port)
            if record.name in db_list:
                return True
        return False
    
    _constraints = [(_check_db_exist, _('Error ! No such database exists!'), [])]


    def test_sftp_connection(self, context=None):
        conf_ids= self.search(self._cr, self._uid, [])
        confs = self.browse(self._cr, self._uid, conf_ids)
        #Check if there is a success or fail and write messages 
        messageTitle = ""
        messageContent = ""
        for rec in confs:
            db_list = self.get_db_list(cr, uid, [], rec.host, rec.port)
            try:
                pathToWriteTo = rec.sftp_path
                ipHost = rec.sftpip
                portHost = rec.sftpport
                usernameLogin = rec.sftp_user
                passwordLogin = rec.sftp_password
                #Connect with external server over SFTP, so we know sure that everything works.
                srv = pysftp.Connection(host=ipHost, username=usernameLogin,
password=passwordLogin,port=portHost)
                srv.close()
                #We have a success.
                messageTitle = "Connection Test Succeeded!"
                messageContent = "Everything seems properly set up for FTP back-ups!"
            except Exception, e:
                messageTitle = "Connection Test Failed!"
                if len(rec.sftpip) < 8:
                    messageContent += "\nYour IP address seems to be too short.\n"
                messageContent += "Here is what we got instead:\n"
        if "Failed" in messageTitle:
            raise osv.except_osv(_(messageTitle), _(messageContent + "%s") % tools.ustr(e))
        else:
            raise osv.except_osv(_(messageTitle), _(messageContent))

    def schedule_backup(self, cr, user, context={}):
        conf_ids= self.search(cr, user, [])
        confs = self.browse(cr,user,conf_ids)
        for rec in confs:
            db_list = self.get_db_list(cr, user, [], rec.host, rec.port)
            if rec.name in db_list:
                try:
                    if not os.path.isdir(rec.folder):
                        os.makedirs(rec.folder)
                except:
                    raise
                #Create name for dumpfile.
                bkp_file='%s_%s.%s' % (time.strftime('%d_%m_%Y_%H_%M_%S'),rec.name, rec.backup_type)
                file_path = os.path.join(rec.folder,bkp_file)
                uri = 'http://' + rec.host + ':' + rec.port
                conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
                bkp=''
                try:
                    bkp = execute(conn, 'dump', tools.config['admin_passwd'], rec.name, rec.backup_type)
                except:
                    _logger.debug("Couldn't backup database %s. Bad database administrator password for server running at http://%s:%s" %(rec.name, rec.host, rec.port))
                    continue
                bkp = base64.decodestring(bkp)
                fp = open(file_path,'wb')
                fp.write(bkp)
                fp.close()
            else:
                _logger.debug("database %s doesn't exist on http://%s:%s" %(rec.name, rec.host, rec.port))

            # Check if user wants to write to SFTP or not.
            if rec.sftp_write is True:
                try:
                    # Store all values in variables
                    dir = rec.folder
                    pathToWriteTo = rec.sftp_path
                    ipHost = rec.sftpip
                    portHost = rec.sftpport
                    usernameLogin = rec.sftp_user
                    passwordLogin = rec.sftp_password
                    # Connect with external server over SFTP
                    srv = pysftp.Connection(host=ipHost, username=usernameLogin,
password=passwordLogin, port=portHost)
                    # set keepalive to prevent socket closed / connection dropped error
                    srv._transport.set_keepalive(30)
                    # Move to the correct directory on external server. If the user made a typo in his path with multiple slashes (/odoo//backups/) it will be fixed by this regex.
                    pathToWriteTo = re.sub('([/]{2,5})+','/',pathToWriteTo)
                    _logger.debug('sftp remote path: %s' % pathToWriteTo)
                    try:
                        srv.chdir(pathToWriteTo)
                    except IOError:
                        #Create directory and subdirs if they do not exist.
                        currentDir = ''
                        for dirElement in pathToWriteTo.split('/'):
                            currentDir += dirElement + '/'
                            try:
                                srv.chdir(currentDir)
                            except:
                                _logger.info('(Part of the) path didn\'t exist. Creating it now at ' + currentDir)
                                #Make directory and then navigate into it
                                srv.mkdir(currentDir, mode=777)
                                srv.chdir(currentDir)
                                pass
                    srv.chdir(pathToWriteTo)
                    # Loop over all files in the directory.
                    for f in os.listdir(dir):
                        fullpath = os.path.join(dir, f)
                        if os.path.isfile(fullpath):
                            if not srv.exists(f):
                                _logger.info('The file %s is not yet on the remote FTP Server ------ Copying file' % fullpath)
                                srv.put(fullpath)
                                _logger.info('Copying File % s------ success' % fullpath)
                            else:
                                _logger.debug('File %s already exists on the remote FTP Server ------ skipped' % fullpath)

                    # Navigate in to the correct folder.
                    srv.chdir(pathToWriteTo)

                    # Loop over all files in the directory from the back-ups.
                    # We will check the creation date of every back-up.
                    for file in srv.listdir(pathToWriteTo):
                        # Get the full path
                        fullpath = os.path.join(pathToWriteTo,file) 
                        # Get the timestamp from the file on the external server
                        timestamp = srv.stat(fullpath).st_atime
                        createtime = datetime.datetime.fromtimestamp(timestamp)
                        now = datetime.datetime.now()
                        delta = now - createtime
                        # If the file is older than the days_to_keep_sftp (the days to keep that the user filled in on the Odoo form it will be removed.
                        if delta.days >= rec.days_to_keep_sftp:
                            # Only delete files, no directories!
                            if srv.isfile(fullpath) and ".dump" in file:
                                _logger.info("Delete too old file from SFTP servers: " + file)
                                srv.unlink(file)
                    # Close the SFTP session.
                    srv.close()
                except Exception, e:
                    _logger.debug('Exception! We couldn\'t back up to the FTP server..')
                    #At this point the SFTP backup failed. We will now check if the user wants
                    #an e-mail notification about this.
                    if rec.send_mail_sftp_fail:
                        try:
                            ir_mail_server = self.pool.get('ir.mail_server') 
                            message = "Dear,\n\nThe backup for the server " + rec.host + " (IP: " + rec.sftpip + ") failed.Please check the following details:\n\nIP address SFTP server: " + rec.sftpip + "\nUsername: " + rec.sftp_user + "\nPassword: " + rec.sftp_password + "\n\nError details: " + tools.ustr(e) + "\n\nWith kind regards"
                            msg = ir_mail_server.build_email("auto_backup@" + rec.name + ".com", [rec.email_to_notify], "Backup from " + rec.host + "(" + rec.sftpip + ") failed", message) 
                            ir_mail_server.send_email(cr, user, msg)
                        except Exception:
                            pass

            """
            Remove all old files (on local server) in case this is configured..
            This is done after the SFTP writing to prevent unusual behaviour:
            If the user would set local back-ups to be kept 0 days and the SFTP
            to keep backups xx days there wouldn't be any new back-ups added to the
            SFTP.
            If we'd remove the dump files before they're writen to the SFTP there willbe nothing to write. Meaning that if an user doesn't want to keep back-ups locally and only wants them on the SFTP (NAS for example) there wouldn't be any writing to the remote server if this if statement was before the SFTP write method right above this comment.
            """
            if rec.autoremove is True:
                dir = rec.folder
                #Loop over all files in the directory.
                for f in os.listdir(dir):
                    fullpath = os.path.join(dir, f)
                    timestamp = os.stat(fullpath).st_ctime
                    createtime = datetime.datetime.fromtimestamp(timestamp)
                    now = datetime.datetime.now()
                    delta  = now - createtime
                    if delta.days >= rec.days_to_keep:
                        #Only delete files (which are .dump), no directories.
                        if os.path.isfile(fullpath) and ".dump" in f:
                            _logger.info("Delete local out-of-date file: " + fullpath)
                            os.remove(fullpath)

