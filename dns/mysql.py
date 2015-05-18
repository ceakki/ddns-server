__author__ = 'cristian'

import MySQLdb
import MySQLdb.cursors


class MySql:
    _host = ''
    _user = ''
    _password = ''
    _database = ''

    _con = None

    error = ''
    last_id = 0
    num_rows = 0

    def __init__(self, mysql_host, mysql_user, mysql_pass, mysql_db):
        self._host = mysql_host
        self._user = mysql_user
        self._password = mysql_pass
        self._database = mysql_db

    # mysql connection function
    def open(self):
        self.error = ''

        try:
            con = MySQLdb.connect(self._host, self._user, self._password, self._database,
                                  cursorclass=MySQLdb.cursors.DictCursor)
        except MySQLdb.Error, e:
            try:
                con = None
                self.error = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                con = None
                self.error = "MySQL Error: %s" % str(e)

        return con

    # mysql query function
    def query(self, query):
        self.error = ''
        self.last_id = 0
        self.num_rows = 0

        if self._con is None:
            con = self.open()

            if self.error:
                return False

            self._con = con

        if self._con.open is False:
            con = self.open()

            if self.error:
                return False

            self._con = con

        with self._con:
            try:
                curs = self._con.cursor()
                curs.execute(query)
                rows = curs.fetchall()

                if curs.lastrowid:
                    self.last_id = curs.lastrowid

                self.num_rows = curs.rowcount
            except MySQLdb.Error, e:
                try:
                    rows = False
                    self.error = "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
                except IndexError:
                    rows = False
                    self.error = "MySQL Error: %s" % str(e)

        return rows