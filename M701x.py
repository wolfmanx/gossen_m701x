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
    # turn off local echo
    self.__serial.write('\x06') # ACK

    # r =  self.request('IDN!0')
    #

  def _read(self):
    """ reads one line, removes CRLF and validates checksum. Returns read line or False on checksum error """
    #return re.sub('[\r\n]+','',self.__serial.readline()) # uncomment for development and unprocessed return
    parts = string.split(re.sub('[\r\n]+','',self.__serial.readline()),'$')
    partcount = len(parts)
    i = 0
    returnstr = ''
    while i < partcount-1:
      checksum = parts[i+1][:2].lower() # the checksum is on the next parts first two chars as we split on $
      if (checksum == self._checksum(parts[i][3:])): # multi line case for lines with first three chars like 'XX;' checksum and a delimiter
        returnstr += parts[i][2:] # subtract checksum but leave delimiter
      elif (checksum == self._checksum(parts[i])): # first line case
        returnstr += parts[i]
      else:
        return False
      i+=1
    return returnstr

  def _write(self,str):
    """ adds $-delimiter, checksum and line ending to str and sends it to the serial line """
    self.__serial.write(str + '$' + self._checksum(str) + '\r\n')

  @staticmethod
  def _checksum(str):
    """ calculates checksum of a request/answer """
    qsum_dec = ord('$')
    for i in str:
      d = ord(i)
      qsum_dec += d
    return "%02x" % (qsum_dec & 0xff)

  def _flush(self):
    """ discards all waiting answers in the buffer """
    self.__serial.flushInput()

  def request(self,command,retries=3):
    """ sends a command to device and parses reply """
    i = 0
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
        return False,answer
      # on ACK return True and address of device
      elif (answer[:2] == '.Y'):
        return True,answer[2:3]
      # on 'string answer' or unhandled answer return None and full answer
      else:
        return None,answer
    # if not sucessful within retries return False
    else:
      return False,'CHKSUM_ERROR'

  def sync_clock(self, idn=None):
    # needs more testing and ability to sync all devices (e.g. PSI + S2N)
    """ synchronizes device clock with PC """
    if idn is None:
      idn = ''
    return self.request('DAT'+idn+'!'+time.strftime("%d.%m.%y;%H:%M:%S"))

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
    sys.exit(doctest.testmod())

  m701 = M701x(arg)
  #m701._write("IDN?")
  #print m701._read()

  print(m701.request('IDN!0'))
  print(m701.request('IDN?'))
  print(m701.request('BEEP!'))

  #print(m701.sync_clock())
  #print(m701.sync_clock('1'))

  #print(m701.request('WER?'))

  # str = "\x13DATIMx=20.09.14;18:33$18\r\n\x11"
  #         ^what             ^param        ^XOFF

# :ide: COMPILE: Run with /dev/ttyUSB0
# . (progn (save-buffer) (compile (concat "python ./" (file-name-nondirectory (buffer-file-name)) " /dev/ttyUSB0")))

# :ide: COMPILE: Run with python3 --test
# . (progn (save-buffer) (compile (concat "python3 ./" (file-name-nondirectory (buffer-file-name)) " --test")))

# :ide: COMPILE: Run with python2 --test
# . (progn (save-buffer) (compile (concat "python2 ./" (file-name-nondirectory (buffer-file-name)) " --test")))

# :ide: COMPILE: Run w/o args
# . (progn (save-buffer) (compile (concat "python ./" (file-name-nondirectory (buffer-file-name)) " ")))
