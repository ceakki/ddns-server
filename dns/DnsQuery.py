import sqlite3
from dns.config import root_servers
from dns.utils import pds, inttoasc, pack_ipv4, pack_domain, pack_text

__author__ = 'cristian'

qtype = {"SOA": 6, "A": 1, "MX": 0x0F, "CNAME": 5, "NS": 2, "TXT": 0x10}


class DNSQuery:
    def __init__(self, data):
        self.data = data
        self.domain = ""
        self.DnsType = ""
        self.root_servers_index = 0

        HDNS = data[-4:-2].encode("hex")
        if HDNS == "0001":
            self.DnsType = "A"

        elif HDNS == "000f":
            self.DnsType = "MX"

        elif HDNS == "0002":
            self.DnsType = "NS"

        elif HDNS == "0010":
            self.DnsType = "TXT"

        elif HDNS == "000c":
            self.DnsType = "PTR"

        else:
            self.DnsType = "Unknown"

        type = (ord(data[2]) >> 3) & 15   # Opcode bits
        if type == 0:                     # Standard query
            ini = 12
            lon = ord(data[ini])
            while lon != 0:
                self.domain += data[ini+1:ini+lon+1] + '.'
                ini += lon+1
                lon = ord(data[ini])

    def packet_header(self, ac = 1, nsc = 0, error = 0):
        packet = ""

        packet += self.data[:2]
        packet += chr(0x81) + chr(0x80 + error)

        packet += self.data[4:6] + pds(inttoasc(ac), 2) + pds(inttoasc(nsc), 2) + "\x00\x00"
        packet += self.data[12:]

        return packet

    def prepare_message(self, result, type):
        msg = ""
        if type == "A":
            msg += pack_ipv4(result[0])
        elif type == "NS":
            msg += pack_domain(result[0])

        elif type == "MX":
            msg += pds(inttoasc(result[1]), 2)
            msg += pack_domain(result[0])
        elif type == "CNAME":
            msg = pack_domain(result[0])
        elif type == "TXT":
            msg += pack_text(result[0])
        elif type == "SOA":
            msg  = pack_domain(result[0])
            msg += pack_domain(result[1])
            msg += pds(inttoasc(result[2]), 4)
            msg += pds(inttoasc(result[3]), 4)
            msg += pds(inttoasc(result[4]), 4)
            msg += pds(inttoasc(result[5]), 4)
            msg += pds(inttoasc(result[6]), 4)

        return msg

    def soa_message(self):
        msg = pack_domain("a.root-servers.net")
        msg += pack_domain("nstld.verisign-grs.com")
        msg += pds(inttoasc(12192086), 4) # serial
        msg += pds(inttoasc(900), 4)      # refresh
        msg += pds(inttoasc(900), 4)      # retry
        msg += pds(inttoasc(604800), 4)   # expire
        msg += pds(inttoasc(86400), 4)    # minimum

        return msg

    def answer_unknow(self):
        result = root_servers[self.root_servers_index]
        self.root_servers_index += 1
        if self.root_servers_index > len(root_servers) - 1:
            self.root_servers_index = 0

        # msg = chr(0xC0) + chr(0x0C)
        msg = chr(0x00)
        msg += pds(inttoasc(qtype["NS"]), 2)  # QTYPE
        msg += pds(inttoasc(1), 2)            # QCLASS
        msg += pds(inttoasc(result[2]), 4)    # TTL

        msg2 = self.prepare_message(result, "NS")
        msg += pds(inttoasc(len(msg2)), 2)
        msg += msg2

        packet = self.packet_header(0, 1, 0) + msg

        return packet

    def answer(self, domain, type):
        domain = domain[:-1]

        conn = sqlite3.connect('file:memdb1?mode=memory&cache=shared')
        c = conn.cursor()

        zone = ""

        searched = (domain, )
        c.execute('SELECT zone FROM zones WHERE ? LIKE ("%" || zone);', searched)
        result = c.fetchone()
        if result:
            zone = result[0]

        if zone == "":
            conn.close()
            return self.answer_unknow()

        packet = ""
        if type == "PTR":
            packet = self.not_implemented()
        else:
            if type == "AAAA" or type == "A":
                searched = (domain, )
                c.execute('SELECT ip FROM domains WHERE domain = ?', searched)
                result = c.fetchone()

                if not result:
                    record_name = domain.replace(zone, "")
                    if record_name == "":
                        record_name = "@"
                    else:
                        record_name = record_name[:-1]

                    searched = (zone, record_name, type, )
                    c.execute('SELECT value, priority, ttl FROM records AS r'
                              ' INNER JOIN zones AS z ON r.zone_id = z.id AND z.zone = ?'
                              ' WHERE r.name = ? AND r.type = ?', searched)
                    result = c.fetchone()

                else:
                    result = list(result)
                    result.append(0)
                    result.append(300)


            else:
                if type == "SOA":
                    searched = (zone, )
                    c.execute('SELECT name_server, email, serial_number, refresh, retry, expiry, minimum'
                              ' FROM zones WHERE zone = ?', searched)
                    result = c.fetchone()

                else:
                    record_name = domain.replace(zone, "")
                    if record_name == "":
                        record_name = "@"
                    else:
                        record_name = record_name[:-1]

                    searched = (zone, record_name, type, )
                    c.execute('SELECT value, priority, ttl FROM records AS r'
                              ' INNER JOIN zones AS z ON r.zone_id = z.id AND z.zone = ? '
                              'WHERE r.name = ? AND r.type = ?', searched)
                    result = c.fetchone()

        if result:
            result = list(result)
            if type == "SOA":
                result[0] = result[0].encode('ascii', 'ignore')
                result[1] = result[1].encode('ascii', 'ignore')

            else:
                result[0] = result[0].encode('ascii', 'ignore')

            # send response
            msg = chr(0xC0) + chr(0x0C)
            msg += pds(inttoasc(qtype[type]), 2)  # QTYPE
            msg += pds(inttoasc(1), 2)            # QCLASS
            msg += pds(inttoasc(result[2]), 4)    # TTL

            msg2 = self.prepare_message(result, type)
            msg += pds(inttoasc(len(msg2)), 2)
            msg += msg2

            packet = self.packet_header(1, 0, 0) + msg

        else:


            searched = (zone, type, )
            c.execute('SELECT value, priority, ttl FROM records AS r '
                      'INNER JOIN zones AS z ON r.zone_id = z.id AND z.zone = ? '
                      'WHERE r.name = "*" AND r.type = ?', searched)
            result = c.fetchone()

            if result:

                result = list(result)
                if type == "SOA":
                    result[0] = result[0].encode('ascii', 'ignore')
                    result[1] = result[1].encode('ascii', 'ignore')

                else:
                    result[0] = result[0].encode('ascii', 'ignore')

                # send response
                msg = chr(0xC0) + chr(0x0C)
                msg += pds(inttoasc(qtype[type]), 2)  # QTYPE
                msg += pds(inttoasc(1), 2)            # QCLASS
                msg += pds(inttoasc(result[2]), 4)    # TTL

                msg2 = self.prepare_message(result, type)
                msg += pds(inttoasc(len(msg2)), 2)
                msg += msg2

                packet = self.packet_header(1, 0, 0) + msg

            else:

                packet = self.answer_unknow()


        conn.close()

        return packet

    def empty(self):
        packet = ""
        if self.domain:
            packet += self.data[:2]                                          # Message ID
            packet += "\x81\x00"                                             # QR	OPCODE	AA	TC	RD	RA	res1	res2	res3	RCODE
            packet += self.data[4:6] + "\x00\x00" + '\x00\x00\x00\x00'       # Questions, Answers Counts, NS Counts, Additional Resource Counts
            packet += self.data[12:]                                         # Original Domain Name Question
        return packet

    def not_implemented(self):
        packet = ""
        if self.domain:
            packet += self.data[:2]                                          # Message ID
            packet += "\x81\x04"                                             # QR	OPCODE	AA	TC	RD	RA	res1	res2	res3	RCODE

            # Error Message no 4 = Not Implemented
            packet += self.data[4:6] + "\x00\x00" + '\x00\x00\x00\x00'       # Questions, Answers Counts, NS Counts, Additional Resource Counts
            packet += self.data[12:]                                         # Original Domain Name Question
        return packet