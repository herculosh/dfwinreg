# -*- coding: utf-8 -*-
"""Fake Windows Registry objects implementation."""

import construct

from dfwinreg import dependencies
from dfwinreg import definitions
from dfwinreg import errors
from dfwinreg import interface


dependencies.CheckModuleVersion(u'construct')


class FakeWinRegistryKey(interface.WinRegistryKey):
  """Fake implementation of a Windows Registry key."""

  def __init__(
      self, name, key_path=u'', last_written_time=None, offset=0, subkeys=None,
      values=None):
    """Initializes a Windows Registry key object.

    Subkeys and values with duplicate names are silenty ignored.

    Args:
      name: the name of the Windows Registry key.
      key_path: optional Windows Registry key path.
      last_written_time: optional last written time (contains
                         a FILETIME timestamp).
      offset: optional offset of the key within the Windows Registry file.
      subkeys: optional list of subkeys (instances of FakeWinRegistryKey).
      values: optional list of values (instances of FakeWinRegistryValue).
    """
    super(FakeWinRegistryKey, self).__init__(key_path=key_path)
    self._last_written_time = last_written_time
    self._name = name
    self._offset = offset
    self._subkeys = {}
    self._values = {}

    if subkeys:
      for registry_key in subkeys:
        name = registry_key.name.upper()
        if name in self._subkeys:
          continue
        self._subkeys[name] = registry_key

        registry_key._key_path = self._JoinKeyPath([
            self._key_path, registry_key.name])

    if values:
      for registry_value in values:
        name = registry_value.name.upper()
        if name in self._values:
          continue
        self._values[name] = registry_value

  @property
  def last_written_time(self):
    """The last written time of the key (contains a FILETIME timestamp)."""
    return self._last_written_time

  @property
  def name(self):
    """The name of the key."""
    return self._name

  @property
  def number_of_subkeys(self):
    """The number of subkeys within the key."""
    return len(self._subkeys)

  @property
  def number_of_values(self):
    """The number of values within the key."""
    return len(self._values)

  @property
  def offset(self):
    """The offset of the key within the Windows Registry file."""
    return self._offset

  def AddSubkey(self, registry_key):
    """Adds a subkey.

    Args:
      registry_key: the Windows Registry subkey (instance of
                    FakeWinRegistryKey).

    Raises:
      KeyError: if the subkey already exists.
    """
    name = registry_key.name.upper()
    if name in self._subkeys:
      raise KeyError(
          u'Subkey: {0:s} already exists.'.format(registry_key.name))

    self._subkeys[name] = registry_key
    registry_key._key_path = self._JoinKeyPath([
        self._key_path, registry_key.name])

  def AddValue(self, registry_value):
    """Adds a value.

    Args:
      registry_value: the Windows Registry value (instance of
                      FakeWinRegistryValue).

    Raises:
      KeyError: if the value already exists.
    """
    name = registry_value.name.upper()
    if name in self._values:
      raise KeyError(
          u'Value: {0:s} already exists.'.format(registry_value.name))

    self._values[name] = registry_value

  def GetSubkeyByName(self, name):
    """Retrieves a subkey by name.

    Args:
      name: The name of the subkey.

    Returns:
      The Windows Registry subkey (instances of WinRegistryKey) or
      None if not found.
    """
    return self._subkeys.get(name.upper(), None)

  def GetSubkeys(self):
    """Retrieves all subkeys within the key.

    Yields:
      Windows Registry key objects (instances of WinRegistryKey) that represent
      the subkeys stored within the key.
    """
    for registry_key in iter(self._subkeys.values()):
      yield registry_key

  def GetValueByName(self, name):
    """Retrieves a value by name.

    Value names are not unique and pyregf provides first match for
    the value.

    Args:
      name: Name of the value or an empty string for the default value.

    Returns:
      A Windows Registry value object (instance of WinRegistryValue) if
      a corresponding value was found or None if not.
    """
    return self._values.get(name.upper(), None)

  def GetValues(self):
    """Retrieves all values within the key.

    Yields:
      Windows Registry value objects (instances of WinRegistryValue) that
      represent the values stored within the key.
    """
    for registry_value in iter(self._values.values()):
      yield registry_value


class FakeWinRegistryValue(interface.WinRegistryValue):
  """Fake implementation of a Windows Registry value."""

  _INT32_BIG_ENDIAN = construct.SBInt32(u'value')
  _INT32_LITTLE_ENDIAN = construct.SLInt32(u'value')
  _INT64_LITTLE_ENDIAN = construct.SLInt64(u'value')

  def __init__(self, name, data=b'', data_type=definitions.REG_NONE, offset=0):
    """Initializes a Windows Registry value object.

    Args:
      name: the name of the Windows Registry value.
      data: optional binary string containing the value data.
      data_type: optional integer containing the value data type.
      offset: optional offset of the value within the Windows Registry file.
    """
    super(FakeWinRegistryValue, self).__init__()
    self._data = data
    self._data_type = data_type
    self._data_size = len(data)
    self._name = name
    self._offset = offset

  @property
  def data(self):
    """The value data as a byte string."""
    return self._data

  @property
  def data_type(self):
    """Numeric value that contains the data type."""
    return self._data_type

  @property
  def name(self):
    """The name of the value."""
    return self._name

  @property
  def offset(self):
    """The offset of the value within the Windows Registry file."""
    return self._offset

  def GetData(self):
    """Retrieves the data.

    Returns:
      The data as a Python type.

    Raises:
      WinRegistryValueError: if the value data cannot be read.
    """
    if not self._data:
      return

    if self._data_type in self._STRING_VALUE_TYPES:
      try:
        return self._data.decode(u'utf-16-le')

      except UnicodeError as exception:
        raise errors.WinRegistryValueError(
            u'Unable to read data from value: {0:s} with error: {1:s}'.format(
                self._name, exception))

    elif (self._data_type == definitions.REG_DWORD and
          self._data_size == 4):
      return self._INT32_LITTLE_ENDIAN.parse(self._data)

    elif (self._data_type == definitions.REG_DWORD_BIG_ENDIAN and
          self._data_size == 4):
      return self._INT32_BIG_ENDIAN.parse(self._data)

    elif (self._data_type == definitions.REG_QWORD and
          self._data_size == 8):
      return self._INT64_LITTLE_ENDIAN.parse(self._data)

    elif self._data_type == definitions.REG_MULTI_SZ:
      try:
        utf16_string = self._data.decode(u'utf-16-le')
        return filter(None, utf16_string.split(u'\x00'))

      except UnicodeError as exception:
        raise errors.WinRegistryValueError(
            u'Unable to read data from value: {0:s} with error: {1:s}'.format(
                self._name, exception))

    return self._data


class FakeWinRegistryFile(interface.WinRegistryFile):
  """Fake implementation of a Windows Registry file."""

  def __init__(self, ascii_codepage=u'cp1252', key_path_prefix=u''):
    """Initializes the Windows Registry file.

    Args:
      ascii_codepage: optional ASCII string codepage. The default is cp1252
                      (or windows-1252).
      key_path_prefix: optional Windows Registry key path prefix.
    """
    super(FakeWinRegistryFile, self).__init__(
        ascii_codepage=ascii_codepage, key_path_prefix=key_path_prefix)
    self._root_key = None

  def AddKeyByPath(self, key_path, registry_key):
    """Adds a Windows Registry for a specific key path.

    Args:
      key_path: the Windows Registry key path to add the key.
      registry_key: the Windows Registry key (instance of FakeWinRegistryKey).

    Returns:
      A boolean containing True if successful or False if not.
    """
    if not key_path.startswith(self._KEY_PATH_SEPARATOR):
      return False

    if not self._root_key:
      self._root_key = FakeWinRegistryKey(self._key_path_prefix)

    path_segments = self._SplitKeyPath(key_path)
    parent_key = self._root_key
    for path_segment in path_segments:
      subkey = FakeWinRegistryKey(path_segment)
      if not parent_key.AddSubkey(subkey):
        return False

    return parent_key.AddSubkey(registry_key)

  def Close(self):
    """Closes the Windows Registry file."""
    return

  def GetKeyByPath(self, key_path):
    """Retrieves the key for a specific path.

    Args:
      key_path: the Windows Registry key path.

    Returns:
      A Registry key (instance of WinRegistryKey) or None if not available.
    """
    key_path_upper = key_path.upper()
    if key_path_upper.startswith(self._key_path_prefix_upper):
      relative_key_path = key_path[self._key_path_prefix_length:]
    elif key_path.startswith(self._KEY_PATH_SEPARATOR):
      relative_key_path = key_path
      key_path = u''.join([self._key_path_prefix, key_path])
    else:
      return

    path_segments = self._SplitKeyPath(relative_key_path)
    registry_key = self._root_key
    for path_segment in path_segments:
      if not registry_key:
        return

      registry_key = registry_key.GetSubkeyByName(path_segment)

    return registry_key

  def GetRootKey(self):
    """Retrieves the root key.

    Returns:
      The Windows Registry root key (instance of WinRegistryKey) or
      None if not available.
    """
    return self._root_key

  def Open(self, unused_file_object):
    """Opens the Windows Registry file using a file-like object.

    Args:
      file_object: the file-like object.

    Returns:
      A boolean containing True if successful or False if not.
    """
    return True