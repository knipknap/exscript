# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
Utilities for serializing/deserializing XML.
"""
from lxml import etree
import Exscript

def get_list_from_etree(node):
    """
    Given a <list> node, this function looks for child elements
    and returns a list of strings::

        <list name="mylist">
          <list-item>foo</list-item>
          <list-item>bar</list-item>
        </list>

    @type  node: lxml.etree.ElementNode
    @param node: A node containing list-item elements.
    @rtype:  list(str)
    @return: A list of strings.
    """
    items = node.iterfind('list-item')
    if items is None:
        return []
    return [i.text.strip() for i in items if i.text is not None]

def add_list_to_etree(root, tag, thelist, name = None):
    """
    Given a list, this function creates the syntax shown in
    get_list_from_etree() and adds it to the given node.
    Returns the new list element.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new element is added.
    @type  tag: str
    @param tag: The tag name of the new node.
    @type  thelist: list(str)
    @param thelist: A list of strings.
    @type  name: str
    @param name: The name attribute of the new node.
    @rtype:  lxml.etree.ElementNode
    @return: The new node.
    """
    if name:
        list_elem = etree.SubElement(root, tag, name = name)
    else:
        list_elem = etree.SubElement(root, tag)
    for value in thelist:
        item = etree.SubElement(list_elem, 'list-item')
        item.text = value
    return list_elem

def get_dict_from_etree(node):
    """
    Given a parent node, this function looks for child elements
    and returns a dictionary of arguments::

        <argument-list name="myargs">
          <variable name="myvar">myvalue</variable>
          <list name="mylist">
            <list-item>foo</list-item>
            <list-item>bar</list-item>
          </list>
        </argument-list>

    @type  node: lxml.etree.ElementNode
    @param node: A node containing variable elements.
    @rtype:  dict
    @return: A map of variables.
    """
    if node is None:
        return {}
    args = {}
    for child in node:
        name = child.get('name').strip()
        if child.tag == 'variable':
            args[name] = child.text.strip()
        elif child.tag == 'list':
            args[name] = get_list_from_etree(child)
        else:
            raise Exception('Invalid XML tag: %s' % element.tag)
    return args

def add_dict_to_etree(root, tag, thedict, name = None):
    """
    Given a dictionary, this function creates the syntax shown in
    get_dict_from_etree() and adds it to the given node.
    Returns the new dictionary element.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new element is added.
    @type  tag: str
    @param tag: The tag name of the new node.
    @type  thedict: dict(str|list)
    @param thedict: A dictionary containing strings or lists.
    @type  name: str
    @param name: The name attribute of the new node.
    @rtype:  lxml.etree.ElementNode
    @return: The new node.
    """
    if name:
        arg_elem = etree.SubElement(root, tag, name = name)
    else:
        arg_elem = etree.SubElement(root, tag)
    for name, value in thedict.iteritems():
        if isinstance(value, list):
            add_list_to_etree(arg_elem, 'list', value, name = name)
        elif isinstance(value, str):
            variable = etree.SubElement(arg_elem, 'variable', name = name)
            variable.text = value
        else:
            raise Exception('unknown variable type')
    return arg_elem

def get_host_from_etree(node):
    """
    Given a <host> node, this function returns a Exscript.Host instance.
    The following XML syntax is expected, whereby the <argument-list>
    element is optional::

        <host name="otherhost" address="10.0.0.2">
          <argument-list>
            <list name="mylist">
              <list-item>foo</list-item>
              <list-item>bar</list-item>
            </list>
          </argument-list>
        </host>
    
    The arguments are parsed using get_dict_from_etree() and attached
    to the host using Exscript.Host.set_all().

    @type  node: lxml.etree.ElementNode
    @param node: A <host> element.
    @rtype:  Exscript.Host
    @return: The resulting host.
    """
    name     = node.get('name', '').strip()
    address  = node.get('address', name).strip()
    arg_elem = node.find('argument-list')
    args     = get_dict_from_etree(arg_elem)
    host     = Exscript.Host(address)
    if not address:
        raise TypeError('host element without name or address')
    if name:
        host.set_name(name)
    host.set_all(args)
    return host

def add_host_to_etree(root, tag, host):
    """
    Given a dictionary, this function creates the syntax shown in
    get_host_from_etree() and adds it to the given node.
    Returns the new host element.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new element is added.
    @type  tag: str
    @param tag: The tag name of the new node.
    @type  host: Exscript.Host
    @param host: A dictionary containing strings or lists.
    @rtype:  lxml.etree.ElementNode
    @return: The new node.
    """
    elem = etree.SubElement(root,
                            tag,
                            address = host.get_address(),
                            name    = host.get_name())
    if host.get_all():
        add_dict_to_etree(elem, 'argument-list', host.get_all())
    return elem

def get_hosts_from_etree(node):
    """
    Given an lxml.etree node, this function looks for <host> tags and
    returns a list of Exscript.Host instances. The following XML syntax
    is expected, whereby the <argument-list> element is optional::

        <root>
           <host name="localhost" address="10.0.0.1"/>
           <host name="otherhost" address="10.0.0.2">
             <argument-list>
               <list name="mylist">
                 <list-item>foo</list-item>
                 <list-item>bar</list-item>
               </list>
             </argument-list>
           </host>
        </root>
    
    The arguments are parsed using get_arguments_from_etree() and attached
    to the host using Exscript.Host.set().

    @type  node: lxml.etree.ElementNode
    @param node: A node containing <host> elements.
    @rtype:  list(Exscript.Host)
    @return: A list of hosts.
    """
    hosts = []
    for host_elem in node.iterfind('host'):
        host = get_host_from_etree(host_elem)
        hosts.append(host)
    return hosts

def add_hosts_to_etree(root, hosts):
    """
    Given a list of hosts, this function creates the syntax shown in
    get_hosts_from_etree() and adds it to the given node.

    @type  root: lxml.etree.ElementNode
    @param root: The node under which the new elements are added.
    @type  hosts: list(Exscript.Host)
    @param hosts: A list of hosts.
    """
    for host in hosts:
        add_host_to_etree(root, 'host', host)
