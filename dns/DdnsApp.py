import socket
import threading
import time
import sqlite3
import sys
from dns.DnsQuery import DNSQuery
from dns.config import mysql_host, mysql_user, mysql_pass, mysql_db
from dns.mysql import MySql

__author__ = 'cristian'


def answer_handler(udps, addr, data):
    p = DNSQuery(data)
    udps.sendto(p.answer(p.domain, p.DnsType), addr)


def sync_db():
    conn = sqlite3.connect('file:memdb1?mode=memory&cache=shared')

    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS domains;")
    c.execute("DROP TABLE IF EXISTS zones;")
    c.execute("DROP TABLE IF EXISTS records;")

    # Create table
    c.execute('''CREATE TABLE domains
               (id integer PRIMARY KEY, user_id integer, domain text, ip text, username text, password text)''')

    c.execute('''CREATE TABLE zones
               (id integer PRIMARY KEY, user_id integer, zone text, name_server text, email text, serial_number integer, refresh integer, retry integer, expiry integer, minimum integer)''')


    c.execute('''CREATE TABLE records
               (id integer PRIMARY KEY, zone_id integer, name text, type text, value text, priority integer, ttl integer)''')

    db = MySql(mysql_host, mysql_user, mysql_pass, mysql_db)

    # Insert a row of data
    data = db.query("SELECT * FROM `domains`;")
    if data:
        c.executemany("INSERT INTO domains VALUES(?, ?, ?, ?, ?, ?);", data)
        c.execute("CREATE INDEX domains_user_id ON domains (user_id);")

    data = db.query("SELECT * FROM `zones`;")
    if data:
        c.executemany("INSERT INTO zones VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", data)
        c.execute("CREATE INDEX zones_user_id ON zones (user_id);")

    data = db.query("SELECT * FROM `records`;")
    if data:
        c.executemany("INSERT INTO records VALUES(?, ?, ?, ?, ?, ?, ?);", data)
        c.execute("CREATE INDEX records_zone_id ON records (zone_id);")

    # Save (commit) the changes
    conn.commit()

    conn.close()


def sync_db_thread():
    # TO DO: SHUTDOWN CHECK

    sync_db()

    time.sleep(60)


class DdnsApp():
    def __init__(self):
        pass

    @staticmethod
    def run():

        sync_db()

        udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udps.bind(('', 53))
        except:
            print "Could not open socket"
            sys.exit(1)

        t = threading.Thread(target=sync_db_thread)
        t.start()

        while True:
            data, addr = udps.recvfrom(1024)
            tt = threading.Thread(target=answer_handler, args=(udps, addr, data,))
            tt.start()
