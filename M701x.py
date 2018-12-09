#! /usr/bin/python
# -*- coding: utf-8 -*-
#
# (C) 2014 juewei@fabfolk.com, All rights reserved.
#
# Distribute under MIT License or ask.
#
# Authors: mose@fabfolk.com, juewei@fabfolk.com
# Modified: Wolfgang.Scherer@gmx.de

import re,sys,string,serial,time

try:
  from pyjsmo.compat import uc_type, ucs, nts
  from pyjsmo.compat import sformat, printf, printe, dbg_fwid
except ImportError:
  def _ucs(string, charset=None):                            # ||:fnc:||
    return unicode(string, charset or 'utf-8')
  try:
    _ucs("")
  except NameError:
    _ucs = lambda s, c=None: s.decode(c or 'utf-8')

  try:
    exec('uc_type = type(_ucs(b""))')
  except SyntaxError:
    uc_type = type(_ucs(""))

  def ucs(value, charset=None):                              # ||:fnc:||
    if not isinstance(value, uc_type):
      return _ucs(value, charset)
    return value

  def nts(string):
    # for python3, unicode strings have type str
    if isinstance(string, str):
        return string
    # for python2, encode unicode strings to utf-8 strings
    if isinstance(string, uc_type):
        return string.encode('utf-8')
    return string

  def sformat (fmtspec, *args, **kwargs):
    return fmtspec.format(*args, **kwargs)

  try:
    printf = eval("print") # python 3.0 case
  except SyntaxError:
    printf_dict = dict()
    exec("from __future__ import print_function\nprintf=print", printf_dict)
    printf = printf_dict["printf"] # 2.6 case
    del printf_dict

  printe = printf

  dbg_fwid = 25

if isinstance(ucs('0').encode('utf-8')[0], int):
  byte_ord = lambda _c: _c
else:
  byte_ord = ord

UDOLLAR = ucs('$')
USEMICOLON = ucs(';')

class STString(uc_type):                                   # ||:cls:||
  r"""Generalized SECUTEST string.

  **Parse DOS String**

  >>> dos_string = ucs('März').encode(STString.transfer_encoding)

  >>> ans = STString.parse_raw(dos_string)
  >>> ans == False
  False

  >>> printf(nts(ans))
  März

  >>> printf(nts(ans.uraw))
  März$e1

  >>> ans._dump()
  e1 None [März]

  **Parse Unicode String**

  >>> ans = STString.parse(ucs('März'))
  >>> ans == False
  False

  >>> printf(nts(ans))
  März

  >>> printf(nts(ans.uraw))
  März$e1

  >>> ans._dump()
  e1 None [März]

  **Parse Native String**

  >>> ans = STString.parse('März', 'utf-8')
  >>> ans == False
  False

  >>> printf(nts(ans))
  März

  >>> printf(nts(ans.uraw))
  März$e1

  >>> ans._dump()
  e1 None [März]

  **Invalid Checksum**

  >>> dos_string = ucs('März$E2').encode(STString.transfer_encoding)

  >>> ans = STString.parse_raw(dos_string)
  >>> ans == False
  True

  >>> printf(nts(ans))
  März

  >>> printf(nts(ans.uraw))
  März$e1

  >>> ans._dump()
  e1 e2 [März]

  **Multi String**

  >>> _id = 'IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52$30'
  >>> _mstr = ';'.join((_id, _id))

  >>> ans = STString.parse(_mstr)
  >>> ans == False
  False

  >>> printf(nts(ans))
  IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52;IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52

  >>> printf(nts(ans.uraw))
  IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52$30;IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52$30

  >>> ans._dump()
  30 30 [IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52]
  30 30 [IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52]

  >>> for _p, _cc, _cs in ans.parts:
  ...     printf(nts(_p))
  IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52
  IDN0=0;GMN;SECUTEST-PSI;M702F;AW;19. März 2014  10:15:52

  **Predefined Empty String with Checksum Error**

  >>> CHECKSUM_ERROR == False
  True

  >>> nts(CHECKSUM_ERROR)
  ''

  """

  transfer_encoding = 'cp437'
  raw = None
  uraw = None
  parts = []
  checksum_ok = False

  @staticmethod
  def _checksum(str, encoding=None):                         # |:mth:|
    """ calculates checksum of a request/answer """
    str = ucs(str, encoding).encode(STString.transfer_encoding)
    qsum_dec = ord('$')
    for i in str:
      d = byte_ord(i)
      qsum_dec += d
    return "%02x" % (qsum_dec & 0xff)

  @staticmethod
  def parse(str, encoding=None):                             # |:mth:|

    ustr = ucs(str, encoding or 'utf8')
    parts = []
    checksum_ok = True

    _rest = re.sub('[\r\n]+', '', ustr)
    while _rest:
      mo = re.search('[$]([0-9a-f][0-9a-f])(;)?(?i)', _rest)
      if not mo:
        _part = _rest
        _chksum = None
        _rest = None
      else:
        _part = _rest[:mo.start(0)]
        _chksum = mo.group(1).lower()
        _rest = _rest[mo.end(0):]
      _chkcalc = STString._checksum(_part)
      parts.append((_part, _chkcalc, _chksum))
      checksum_ok = checksum_ok and (_chksum is None or _chksum == _chkcalc)

    _dollar_parts = []
    _plain_parts = []
    for _p, _cc, _cs in parts:
      _dollar_parts.append(UDOLLAR.join((_p, _cc)))
      _plain_parts.append(_p)

    _dstr = USEMICOLON.join(_dollar_parts)
    _pstr = USEMICOLON.join(_plain_parts)

    sstr = STString(_pstr)
    sstr.parts = parts
    sstr.checksum_ok = checksum_ok
    sstr.raw = _dstr.encode(STString.transfer_encoding)
    sstr.uraw = _dstr
    return sstr

  @staticmethod
  def parse_raw(str):                                        # |:mth:|
    return STString.parse(str, STString.transfer_encoding)

  def _slice(self, _from, _to):                             # |:mth:|
    sstr = self.__class__(self[_from:_to])
    for _attr in ('raw', 'uraw', 'parts', 'checksum_ok'):
      setattr(sstr, _attr, getattr(self, _attr))
    return sstr

  def __eq__(self, other):                                   # |:mth:|
    r"""If comparing to boolean True/False, compare self.checksum_ok"""
    if other in (True, False):
      return self.checksum_ok == other
    return uc_type(self) == other

  def _dump(self):                                           # |:mth:|
    r""" """
    for _p in self.parts:
      printf(nts(sformat(ucs('{1} {2} [{0}]'), *_p)))

CHECKSUM_ERROR = STString.parse('$25')
B_CRNL = ucs('\r\n').encode(STString.transfer_encoding)
B_ACK = ucs('\x06').encode(STString.transfer_encoding)

class M701x(object):
  """ Class for interfacing with Gossen Metrawatt devices over serial """

  # M701x has a rate limit of 1 call per second?!
  _pyjsmo_x_rate_limit = 1
  _pyjsmo_x_last_req = 0

  def __init__(self, serial_port):
    self.port = serial_port
    self.__serial = serial.Serial(
                    port=self.port,
                    baudrate=9600,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=3,
                    xonxoff=True
                  )

    # turn off local echo # ACK
    self.__serial.write(B_ACK)

    # r =  self.request('IDN!0')
    #

  def _read(self):
    r"""reads one line, removes CRLF and validates checksum.

    :returns: :class:`STString` instance, which compares boolean values to checksum status:
      ::

        if _answer == True:
          print('checksum OK')
    """
    return STString.parse_raw(self.__serial.readline())

  def _write(self, string, encoding=None):
    """ adds $-delimiter, checksum and line ending to str and sends it to the serial line """
    sstr = STString.parse(string, encoding)
    self.__serial.write(sstr.raw + B_CRNL)

  _checksum = staticmethod(STString._checksum)

  def _flush(self):
    """ discards all waiting answers in the buffer """
    self.__serial.flushInput()

  def request(self,command,retries=3):
    """ sends a command to device and parses reply """
    i = 0
    answer = CHECKSUM_ERROR
    while i < retries:
      _d = time.time() - self._pyjsmo_x_last_req
      if _d < self._pyjsmo_x_rate_limit:
        time.sleep(_d or self._pyjsmo_x_rate_limit)
      self._pyjsmo_x_last_req = time.time()

      self._flush()
      self._write(command)
      answer = self._read()
      # on checksum error retry
      # Answer .N<ADRESSE>=101 stands for checksum error
      if ((answer == False) or (answer[:2] == '.N' and answer[3:7] == '=101')):
        i+=1
        continue
      # on NACK return False and full answer
      elif (answer[:2] == '.N'):
        return False, answer._slice(2, None)
      # on ACK return True and address of device
      elif (answer[:2] == '.Y'):
        return True, answer._slice(2, None)
      # on 'string answer' or unhandled answer return None and full answer
      else:
        return None,answer
    # if not sucessful within retries return False
    else:
      return False,answer

  def sync_clock(self, idn=None):
    # needs more testing and ability to sync all devices (e.g. PSI + S2N)
    """ synchronizes device clock with PC """
    if idn is None:
      idn = ''
    return self.request('DAT'+idn+'!'+time.strftime("%d.%m.%y;%H:%M:%S"))

  def vrequest_(self, method, *args):
    _success, _answer = getattr(self, method)(*args)
    printe(sformat(
      "#    "":DBG:    {1:<{0}s}: ]{2!s:<14s}[ ]{3!s:<5s}[ ]{4!s}[", dbg_fwid,
      "req/succ/answer", sformat('{0}({1})', method, ', '.join(args)),
      _success, nts(_answer)))
    if len(_answer.parts) > 1:
      _answer._dump()
    return _success, _answer

  def vrequest(self, *args):
    return self.vrequest_('request', *args)

  def vsync_clock(self, *args):
    return self.vrequest_('sync_clock', *args)

if __name__ == "__main__":
  if len(sys.argv) < 2:
    import os
    for arg in ('/dev/ttyUSB0', '/dev/ttyS0'):
      if os.path.exists(arg):
        break
    print('port: ' + arg)
  else:
    arg = sys.argv[1]

  if arg == '--test':
    import doctest
    sys.exit(doctest.testmod()[0])

  m701 = M701x(arg)
  #m701._write("IDN?")
  #print m701._read()

  m701.vrequest('IDN!0')
  m701.vrequest('IDN?')
  m701.vrequest('BEEP!')

  m701.vrequest('XYZ?')

  m701.vrequest('DAT?')
  m701.vsync_clock()
  m701.vrequest('DAT?')
  #m701.vsync_clock('1')

  m701.vrequest('WER?')

  # str = "\x13DATIMx=20.09.14;18:33$18\r\n\x11"
  #         ^what             ^param        ^XOFF

# :ide: COMPILE: Run with /dev/ttyUSB0
# . (progn (save-buffer) (compile (concat "python ./" (file-name-nondirectory (buffer-file-name)) " /dev/ttyUSB0")))

# :ide: COMPILE: Run with python3 --test
# . (progn (save-buffer) (compile (concat "python3 ./" (file-name-nondirectory (buffer-file-name)) " --test")))

# :ide: COMPILE: Run with python3 w/o args
# . (progn (save-buffer) (compile (concat "python3 ./" (file-name-nondirectory (buffer-file-name)) " ")))

# :ide: COMPILE: Run with python2 --test
# . (progn (save-buffer) (compile (concat "python2 ./" (file-name-nondirectory (buffer-file-name)) " --test")))

# :ide: COMPILE: Run with python2 w/o args
# . (progn (save-buffer) (compile (concat "python2 ./" (file-name-nondirectory (buffer-file-name)) " ")))
