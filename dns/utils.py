__author__ = 'cristian'


def inttoasc(number):
    try:
        hs = hex(number)[2:]
    except:
        pass

    if hs[-1:].upper() == 'L':
        hs = hs[:-1]

    result = ''
    while len(hs) > 2:
        result = chr(int(hs[-2:], 16)) + result
        hs = hs[:-2]

    result = chr(int(hs, 16)) + result

    return result


def pds(s, l):
    # pad string with chr(0)'s so that
    # return string length is l
    x = l - len(s)
    return x * chr(0) + s


def pack_domain(name):
    if name == "":
        return chr(0)
    if len(name) > 255:
        return chr(0)

    parts = name.split(".")
    ret = ""
    for p in parts:
        ret += chr(len(p)) + p

    ret += chr(0)

    return ret


def pack_text(text):
    if text == "":
        return chr(0)
    if len(text) > 255:
        return chr(0)

    return chr(len(text)) + text


def pack_ipv4(ip):
    return str.join('', map(lambda x: chr(int(x)), ip.split('.')))
