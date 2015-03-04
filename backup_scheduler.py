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
import base64

from openerp.osv import fields,osv
from openerp import tools
from openerp import netsvc
from openerp import tools, _
#from tools.translate import _

#logger = netsvc.Logger()

def execute(connector, method, *args):
    res = False
    try:        
        res = getattr(connector,method)(*args)
    except socket.error,e:        
            raise e
    return res

addons_path = tools.config['addons_path'] + '/auto_backup/DBbackups'

class db_backup(osv.Model):
    _name = 'db.backup'
    
    def get_db_list(self, cr, user, ids, host='localhost', port='8069', context={}):
        uri = 'http://' + host + ':' + port
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
        db_list = execute(conn, 'list')
        return db_list

    def _get_db_name(self,cr,uid, vals,context=None):
        attach_pool = self.pool.get("ir.logging")
        dbName = cr.dbname
        return dbName
        
    _columns = {
                    'host' : fields.char('Host', size=100, required='True'),
                    'port' : fields.char('Port', size=10, required='True'),
                    'name' : fields.char('Database', size=100, required='True',help='Database you want to schedule backups for'),
                    'bkp_dir' : fields.char('Backup Directory', size=100, help='Absolute path for storing the backups', required='True')
                }

    _defaults = {
                    #'bkp_dir' : lambda *a : addons_path,
                    'bkp_dir' : '/odoo/backups',
                    'host' : lambda *a : 'localhost',
                    'port' : lambda *a : '8069',
                    'name': _get_db_name,
                 }
    
    def _check_db_exist(self, cr, user, ids):
        for rec in self.browse(cr,user,ids):
            db_list = self.get_db_list(cr, user, ids, rec.host, rec.port)
            if rec.name in db_list:
                return True
        return False
    
    _constraints = [
                    (_check_db_exist, _('Error ! No such database exists!'), [])
                    ]
    
    def schedule_backup(self, cr, user, context={}):
        conf_ids= self.search(cr, user, [])
        confs = self.browse(cr,user,conf_ids)
        for rec in confs:
            db_list = self.get_db_list(cr, user, [], rec.host, rec.port)
            if rec.name in db_list:
                try:
                    if not os.path.isdir(rec.bkp_dir):
                        os.makedirs(rec.bkp_dir)
                except:
                    raise
                bkp_file='%s_%s.dump' % (time.strftime('%d%m%Y_%H_%M_%S'),rec.name)
                file_path = os.path.join(rec.bkp_dir,bkp_file)
                fp = open(file_path,'wb')
                uri = 'http://' + rec.host + ':' + rec.port
                conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
                bkp=''
                try:
                    bkp = execute(conn, 'dump', tools.config['admin_passwd'], rec.name)
                except:
                    logger.notifyChannel('backup', netsvc.LOG_INFO, "Could'nt backup database %s. Bad database administrator password for server running at http://%s:%s" %(rec.name, rec.host, rec.port))
                    continue
                bkp = base64.decodestring(bkp)
                fp.write(bkp)
                fp.close()
            else:
                logger.notifyChannel('backup', netsvc.LOG_INFO, "database %s doesn't exist on http://%s:%s" %(rec.name, rec.host, rec.port))

db_backup()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
