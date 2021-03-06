# Copyright 2018 5G Exchange (5GEx) Project
# Copyright 2016-2017 Ericsson Hungary Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#    Yang baseclasses for the pyang plugin (PNC) developed at Ericsson Hungary Ltd.

__author__ = "5GEx Consortium, Robert Szabo, Balazs Miriszlai, Akos Recse, Raphael Vicente Rosa"
__copyright__ = "Copyright 2018 5G Exchange (5GEx) Project, Copyright 2016-2017 Ericsson Hungary Ltd."
__credits__ = "Robert Szabo, Raphael Vicente Rosa, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse"
__license__ = "Apache License, Version 2.0"
__version_text__ = "yang/baseclasses/v5bis"
__version__ = "2017-06-26"


from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET
import copy
from decimal import *
from collections import OrderedDict, Iterable
import StringIO
import os
import sys
import string
import logging
import json
import re

logger = logging.getLogger("baseclss")


__EDIT_OPERATION_TYPE_ENUMERATION__ = (  # see https://tools.ietf.org/html/rfc6241#section-7.2
    "merge",  # default operation
    "replace",
    "create",
    "delete",
    "remove"
)

DEFAULT = object()

__IGNORED_ATTRIBUTES__ =    ("_parent", "_tag", "_sorted_children", "_referred", "_key_attributes", "_sh")
__EQ_IGNORED_ATTRIBUTES__ = ("_parent", "_sorted_children", "_referred", "_key_attributes", "_floating")
__YANG_COPY_ATTRIBUTES__ =  ("_tag", "_sorted_children", "_operation", "_attributes", "_floating")

__REDUCE_ATTRIBUTES__ = ("")


class PathUtils:
    @staticmethod
    def path_to_list(path):
        _list = list()
        _remaining = path
        while '[' in _remaining:
            _begin, _remaining = _remaining.split('[', 1)
            _mid, _remaining = _remaining.split(']', 1)
            _p = _begin.split('/')
            if len(_list) > 0:
                _p.pop(0)
            _list.extend(_p)
            _list[-1] += '[' + _mid + ']'
            if _remaining is None:
                break
        if _remaining is not None:
            _p = _remaining.split('/')
            if len(_list) > 0:
                _p.pop(0)
            _list.extend(_p)
        return _list

    @staticmethod
    def add(_from, _to):
        if _to[0] == '/':  # absolute path
            return _to
        p1 = PathUtils.path_to_list(_from)
        p2 = PathUtils.path_to_list(_to)
        l = p2.pop(0)
        while l == "..":
            p1.pop()
            l = p2.pop(0)
        p1.append(l)
        p1 += p2
        return '/'.join(p1)

    @staticmethod
    def diff(_from, _to):
        if _to[0] != '/':  # relative path
            return _to
        p1 = PathUtils.path_to_list(_from)
        p2 = PathUtils.path_to_list(_to)
        l1 = p1.pop(0)
        l2 = p2.pop(0)
        try:
            while l1 == l2:
                l1 = p1.pop(0)
                l2 = p2.pop(0)
            p2.insert(0, l2)
            p2.insert(0, '..')  # the paths divereged but both exist to this level
        except:
            pass  # catch exection that one of the path did not exist at this level, it is not a problem
        while len(p1)>0:
            p2.insert(0, "..")
            p1.pop(0)
        return '/'.join(p2)

    @staticmethod
    def match_path_regexp(path, path_regexp):
        p = PathUtils.path_to_list(path)
        _filter = PathUtils.path_to_list(path_regexp)
        try:
            while re.match(_filter[0], p[0]) is not None:
                p.pop(0)
                _filter.pop(0)
        finally:
            if len(_filter)>0:
                return None


    @staticmethod
    def remove_id_from_path(path):
        '''
        Returns with a simple type path by removing ids from the given path.
        Example:
            /virtualizer/nodes/node[id=1]/ports/port[id=2] => /virtualizer/nodes/node/ports/port
        '''
        id_regex = re.compile('\[(.*?)\]')
        return re.sub(id_regex, '', path)


    @staticmethod
    def split_tag_and_key_values(tag_with_key_values):
        if (tag_with_key_values.find("[") > 0) and (tag_with_key_values.find("]") > 0):
            tag = tag_with_key_values[0: tag_with_key_values.find("[")]
            key_values = tag_with_key_values[tag_with_key_values.find("[") + 1: tag_with_key_values.rfind("]")]
            kv = key_values.split("=")
            return tag, kv
        return tag_with_key_values, None

    @staticmethod
    def split_path_segment_to_key_value_dict(path_segment):
        if (path_segment.find("[") > 0) and (path_segment.find("]") > 0):
            tag = path_segment[0: path_segment.find("[")]
            keystring = path_segment[path_segment.find("[") + 1: path_segment.rfind("]")]
            keys = dict(item.split("=") for item in keystring.split(","))
            return tag, keys
        return path_segment, None

    @staticmethod
    def merge_tag_and_keyst_to_path_segment(tag, keys):
        if keys is None:
            return tag
        return tag + '[' + ','.join(['%s=%s' % (key, value) for (key, value) in keys.items()]) + ']'

    @staticmethod
    def get_key_values_by_tag(path, tag):
        p = path.split("/")
        t = tag.split("/")
        for i in range(1, len(p)+1):
            _tag, _kv = PathUtils.split_tag_and_key_values(p[-i])
            if (_tag == t[-1]) and (_kv is not None):
                match = True
                for j in range(1, min(len(p)+1-i,len(t))):
                    __tag, __kv = PathUtils.split_tag_and_key_values(p[-i-j])
                    if __tag != t[-1-j]:
                        match = False
                        break
                if match:
                    return _kv[1]
        return None

    @staticmethod
    def has_tags(path, tags, at=None):
        """
        Check if path has tags (without key and values)
        :param path: string, path
        :param tags: pattern to check for
        :param at: int, position to check for (can be negative)
        :return: boolean, True if match; False otherwise
        """
        p = path.split("/")
        _path = ""
        for i in range(0, len(p)):
            l = p[i]
            if (l.find("[") > 0) and (l.find("]") > 0):
                attrib = l[0: l.find("[")]
                _path= _path + "/" + attrib
            else:
                _path= _path + l

        p = path.split('/')
        if at is not None:
            if len(p) > abs(at):
                return p[at] == path
            return False
        return path in p


class YangJson:
    @classmethod
    def elem_to_dict(cls, elem):
        d = OrderedDict()
        tag = elem.tag
        for subelement in elem:
            sub_tag = subelement.tag
            sub_value = cls.elem_to_dict(subelement)
            value = sub_value[sub_tag]

            if sub_tag in d.keys():
                if type(d[sub_tag]) is list:
                    d[sub_tag].append(value)
                else:
                    d[sub_tag] = [d[sub_tag], value]
            else:
                d[sub_tag] = value
        if d:
            if elem.text:
                d['text'] = elem.text
            if elem.attrib:
                d['attributes'] = elem.attrib
            if elem.tail:
                d['tail'] = elem.tail
        else:
            if elem.text:
                d = elem.text or None
        return {tag: d}

    @classmethod
    def dict_to_elem(cls, input_dict):
        dict_tag = input_dict.keys()[0]
        dict_value = input_dict[dict_tag]
        sub_nodes = []
        text = None
        tail = None
        attributes = None
        if type(dict_value) is dict:
            for key, value in dict_value.items():
                if key == 'text':
                    text = value
                elif key == 'tail':
                    tail = value
                elif key == 'attributes':
                    attributes = value
                elif type(value) is list:
                    list_sub_nodes = map(lambda sub_node: {key: sub_node}, value)
                    list_sub_nodes = map(cls.dict_to_elem, list_sub_nodes)
                    sub_nodes.extend(list_sub_nodes)
                else:
                    sub_node = cls.dict_to_elem({key: value})
                    sub_nodes.append(sub_node)
        else:
            text = dict_value
        node = ET.Element(dict_tag)
        node.text = text
        node.tail = tail
        for sub_node in sub_nodes:
            node.append(sub_node)
        if attributes:
            node.attrib = attributes
        return node

    @classmethod
    def from_json(cls, _json):
        _dict = json.loads(_json)
        _elem = cls.dict_to_elem(_dict)
        return _elem

    @classmethod
    def to_json(cls, _elem, ordered=True):
        _dict = cls.elem_to_dict(_elem)
        _json = json.dumps(_dict, indent=4, sort_keys=ordered)
        return _json

# Custom Exceptions
class YangCopyDifferentParent(Exception):
    pass

class Yang(object):
    """
    Class defining the root attributes and methods for all Virtualizer classes
    """

    def __init__(self, tag, parent=None):
        self._parent = parent
        self._tag = tag
        self._operation = None
        self._referred = []  # to hold leafref references for backward search
        self._sorted_children = []  # to hold children Yang list
        self._attributes = ['_operation']
        # self._leaf_attributes = list()
        self._floating = False  # get_path() will not return initial '/', i.e., only relative path is returned

    def format(self, **kwargs):
        for c in self._sorted_children:
            if self.__dict__[c] is not None:
                self.__dict__[c].format(**kwargs)

    # def __setattr__(self, key, value):
    #     """
    #     Calls set_value() for Leaf types so that they behave like string, int etc...
    #     :param key: string, attribute name
    #     :param value: value of arbitrary type
    #     :return: -
    #     """
    #     if (value is not None) and (key in self.__dict__) and issubclass(type(self.__dict__[key]),
    #                                                                      Leaf) and not issubclass(type(value), Yang):
    #         self.__dict__[key].set_value(value)
    #     else:
    #         self.__dict__[key] = value

    def match_tags(self, tags):
        if tags is None:
            return True
        if type(tags) in [] in (list, tuple):
            return self._tag in tags
        return self._tag == tags

    def path_filter(self, path_filter, reference=None):
        def check_attrib(base, offset, attrib_path, value):
            try:
                a = base.walk_path(offset)
                a = a.walk_path(attrib_path)
                if value is not None:
                    return a.get_value() == value
                return True
            except:
                return False

        if path_filter is None:
            return True  # empty filter matches everything
        path = self.get_path()
        m = re.match(path_filter['path'], path)
        if m is not None:
            a_path = path_filter.get('attrib', None)
            if a_path is not None:
                if check_attrib(self, m.group(0), a_path, path_filter.get('value', None)):
                    return True
                if reference is not None:
                    return check_attrib(reference, m.group(0), a_path, path_filter.get('value', None))
                return False
            return True
        else:
            return False


    def get_next(self, children=None, operation=None, tags=None, _called_from_parent_=False, reference= None, path_filter=None):
        """
        Returns the next Yang element followed by the one called for. It can be used for in-depth traversar of the yang tree.
        :param children: Yang (for up level call to hand over the callee children)
        :return: Yang
        """

        i = 0
        if operation is None:
            operation = (None,) + __EDIT_OPERATION_TYPE_ENUMERATION__
        if len(self._sorted_children) > 0:
            if children is None:
                while i < len(self._sorted_children):
                    if (self.__dict__[self._sorted_children[i]] is not None) and \
                            (self.__dict__[self._sorted_children[i]].is_initialized()):
                        if self.__dict__[self._sorted_children[i]].has_operation(operation) and self.__dict__[self._sorted_children[i]].match_tags(tags) and self.__dict__[self._sorted_children[i]].path_filter(path_filter, reference=reference):
                            return self.__dict__[self._sorted_children[i]]
                        else:
                            res = self.__dict__[self._sorted_children[i]].get_next(operation=operation, tags=tags, _called_from_parent_=True, reference=reference, path_filter=path_filter)
                            if res is not None:
                                return res
                    i += 1
            else:
                while i < len(self._sorted_children):
                    i += 1
                    if self.__dict__[self._sorted_children[i - 1]] == children:
                        break
                while i < len(self._sorted_children):
                    if (self.__dict__[self._sorted_children[i]] is not None) and \
                            (self.__dict__[self._sorted_children[i]].is_initialized()):
                        if self.__dict__[self._sorted_children[i]].has_operation(operation) and self.__dict__[self._sorted_children[i]].match_tags(tags) and self.__dict__[self._sorted_children[i]].path_filter(path_filter, reference=reference):
                            return self.__dict__[self._sorted_children[i]]
                        else:
                            res = self.__dict__[self._sorted_children[i]].get_next(operation=operation, tags=tags, _called_from_parent_=True, reference=reference, path_filter=path_filter)
                            if res is not None:
                                return res
                    i += 1
        # go to parent
        if (self._parent is not None) and (not _called_from_parent_):
            return self._parent.get_next(self, operation=operation, tags=tags, reference=reference, path_filter=path_filter)
        return None

    def get_attr(self, attrib, v=None, default=DEFAULT):
        if hasattr(self, attrib):
            return self.__dict__[attrib]
        if (v is not None) and isinstance(v, Yang):
            _v = v.walk_path(self.get_path())
            if hasattr(_v, attrib):
                return _v.__dict__[attrib]
        if default is not DEFAULT:
            # default return is given
            return default
        raise ValueError("Attrib={attrib} cannot be found in self={self} and other={v}".format(
                self=self.get_as_text(), v=v.get_as_text()))

    def has_attr_with_value(self, attrib, value, ignore_case=True):
        if hasattr(self, attrib):
            if ignore_case and (self.__dict_[attrib].get_as_text().lower() == value.lower()):
                return True
            return self.__dict_[attrib].get_as_text() == value
        return False

    def has_attrs_with_regex(self, av_list):
        try:
            if len(av_list) == 0:  # for list entries
                return self
            if len(av_list) == 1 and type(av_list[0]) in (list, tuple):
                return self.has_attrs_with_regex(av_list[0])
            if type(av_list) is tuple:
                av_list = list(av_list)
            if type(av_list[0]) is list:
                l = av_list.pop(0)
                attr = l[0]
            elif type(av_list[0]) is tuple:
                l = av_list.pop(0)
                if self.has_attrs_with_regex(l):
                    return self.has_attrs_with_regex(av_list)
            elif (len(av_list) == 2) and (isinstance(av_list[1], basestring)): # attrib and value check
                l = list(av_list)
                av_list = ()
                attr = l[0]
            else:
                l = av_list.pop(0)
                attr = l
            _return = True
            if hasattr(self, attr):
                if self.__dict__[attr].is_initialized():
                    if type(l) in (list, tuple):
                        if type(l[1]) in (list, tuple):
                            _return = self.__dict__[attr].has_attrs_with_regex(l[1])  # recursive structure call
                            if _return and len(av_list) > 0:
                                return _return and self.has_attrs_with_regex(av_list)
                            else:
                                return _return
                        else:
                            if re.match(l[1], self.__dict__[attr].get_as_text()) is not None:
                                if len(av_list) > 0:
                                    return self.has_attrs_with_regex(av_list)
                                else:
                                    return True
                    else:
                        if (type(av_list) in (list, tuple)) and (len(av_list)>0):
                            return self.__dict__[attr].has_attrs_with_regex(av_list)
                        else:
                            return True
            return False
        except:
            return False

    def has_attrs_with_values(self, av_list, ignore_case=True):
        try:
            if len(av_list) == 0:  # for list entries
                return self
            if len(av_list) == 1 and type(av_list[0]) in (list, tuple):
                return self.has_attrs_with_values(av_list[0], ignore_case)
            if type(av_list) is tuple:
                av_list = list(av_list)
            if type(av_list[0]) is list:
                l = av_list.pop(0)
                attr = l[0]
            elif type(av_list[0]) is tuple:
                l = av_list.pop(0)
                if self.has_attrs_with_values(l, ignore_case):
                    return self.has_attrs_with_values(av_list, ignore_case)
            elif (len(av_list) == 2) and (isinstance(av_list[1], basestring)): # attrib and value check
                l = list(av_list)
                av_list = ()
                attr = l[0]
            else:
                l = av_list.pop(0)
                attr = l
            _return = True
            if hasattr(self, attr):
                if self.__dict__[attr].is_initialized():
                    if type(l) in (list, tuple):
                        if type(l[1]) in (list, tuple):
                            _return = self.__dict__[attr].has_attrs_with_values(l[1], ignore_case)  # recursive structure call
                            if _return and len(av_list) > 0:
                                return _return and self.has_attrs_with_values(av_list, ignore_case)
                            else:
                                return _return
                        else:
                            if ignore_case and (self.__dict__[attr].get_as_text().lower() == l[1].lower()):
                                if len(av_list) > 0:
                                    return self.has_attrs_with_values(av_list, ignore_case)
                                else:
                                    return _return
                            if self.__dict__[attr].get_as_text() == l[1]:
                                if len(av_list) > 0:
                                    return self.has_attrs_with_values(av_list, ignore_case)
                                else:
                                    return True
                    else:
                        if (type(av_list) in (list, tuple)) and (len(av_list)>0):
                            return self.__dict__[attr].has_attrs_with_values(av_list, ignore_case)
                        else:
                            return True
            return False
        except:
            return False

    def get_parent(self, level=1, tag=None):
        """
        Returns the parent in the class subtree.
        :param level: number of recursive parent calls or number of tag match to iterate
        :param tag: look for specific tag; if level is also used then levelth match of the tag
        :return: Yang
        """
        if tag is not None:
            if self._tag == tag:
                return self._parent.get_parent(level=level-1, tag=tag) if level > 1 else self  # return self if no more level but matcing tag; otherwise continue
            return self._parent.get_parent(level=level, tag=tag)
        if level > 1:
            return self._parent.get_parent(level=level-1) if self._parent is not None else None
        return self._parent

    def set_parent(self, parent):
        """
        Set the parent to point to the next node up in the Yang class instance tree
        :param parent: Yang
        :return: -
        """
        self._parent = parent

    def get_tag(self):
        """
        Returns the YANG tag for the class.
        :return: string
        """
        return self._tag

    def set_tag(self, tag):
        """
        Set the YANG tag for the class
        :param tag: string
        :return: -
        """
        self._tag = tag

    def et(self):
        return self._et(None, False, True)

    def json(self, ordered=True):
        velem = self._et(None, False, ordered=True)
        vjson = YangJson.to_json(velem, ordered=True)
        return vjson

    def xml(self, ordered=True):
        """
        Dump the class subtree as XML string
        :param ordered: boolean -- defines alaphabetic ordering (True) or the one that was read
        :return: string
        """
        root = self._et(None, False, ordered)
        xmlstr = ET.tostring(root, encoding="utf8", method="xml")
        dom = parseString(xmlstr)
        return dom.toprettyxml()

    def get_as_text(self, ordered=True):
        """
        Dump the class subtree as TEXT string
        :return: string
        """
        root = self._et(None, False, ordered)
        return ET.tostring(root, encoding="utf8", method="html")

    def html(self, ordered=True, header="", tailer=""):
        """
        Dump the class subtree as HTML pretty formatted string
        :return: string
        """

        def indent(elem, level=0):
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for elem in elem:
                    indent(elem, level + 1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i

        root = self._et(None, False, ordered)
        indent(root)

        output = StringIO.StringIO()
        if not isinstance(root, ET.ElementTree):
            root = ET.ElementTree(root)

        root.write(output)
        if output.buflist[-1] == '\n':
            output.buflist.pop()
        html = header + output.getvalue() + tailer
        output.close()
        return html

    def write_to_file(self, outfilename, format="html", ordered=True):
        """
        Writes Yang tree to a file; path is created on demand
        :param outfilename: string
        :param format: string ("html", "xml", "text"), default is "html"
        :return: -
        """
        if not os.path.exists(os.path.dirname(outfilename)):
            os.makedirs(os.path.dirname(outfilename))
        text = self.html(ordered=ordered)
        if format == "text":
            text = self.get_as_text(ordered=ordered)
        elif format == "xml":
            text = self.xml(ordered=ordered)
        with open(outfilename, 'w') as outfile:
            outfile.writelines(text)

    def update_parent(self):
        for k, v in self.__dict__.items():
            if k not in __IGNORED_ATTRIBUTES__:
                if isinstance(v, Yang):
                    v.set_parent(self)
                    v.update_parent()

    def reduce(self, reference, ignores=None):
        """
        Delete instances which equivalently exist in the reference tree.
        The call is recursive, a node is removed if and only if all of its children are removed.
        :param reference: Yang
        :param ignores: tuple of attribute names not to use during the compare operation
        :return: True if object to be removed otherwise False
        """
        _reduce = True
        _ignores = list(__IGNORED_ATTRIBUTES__)
        if ignores is not None:
            if type(ignores) is tuple:
                _ignores.extend(ignores)
            else:
                _ignores.append(ignores)
        for k in self._sorted_children:
            if k not in _ignores:
                v = getattr(self, k)
                vv = getattr(reference, k)
                if self.has_operation(('delete', 'remove')):
                    if v is not None:
                        v.clear_data()
                elif type(v) == type(vv):
                    if v.reduce(vv):
                        v.clear_data()
                    else:
                        _reduce = False
                else:
                    _reduce = False
        if self.has_operation(reference.get_operation()):
            self.set_operation(None, recursive=None, force=True)
        else:
            _reduce = False
        # _reduce &= self.has_operation(reference.get_operation())
        return _reduce

    def _diff(self, source, ignores=None):
        """
        Delete instances which equivalently exist in the reference tree.
        The call is recursive, a node is removed if and only if all of its children are removed.
        :param reference: Yang
        :param ignores: tuple of attribute names not to use during the compare operation
        :return: True if object to be removed otherwise False
        """
        _ignores = list(__IGNORED_ATTRIBUTES__)
        if ignores is not None:
            if type(ignores) is tuple:
                _ignores.extend(ignores)
            else:
                _ignores.append(ignores)
        for k, v in self.__dict__.items():
            if type(self._parent) is ListYang:  # todo: move this outside
                if k == self.keys():
                    _ignores.append(k)
            if k not in _ignores:
                if isinstance(v, Yang):
                    if k in source.__dict__.keys():
                        if type(v) == type(source.__dict__[k]):
                            v._diff(source.__dict__[k])
                            if v.is_initialized() is False:
                                v.delete()
                    else:
                        v.set_operation("create", recursive=False, force=False)
        for k, v in source.__dict__.items():
            if k not in _ignores:
                if isinstance(v, Yang):
                    if k not in self.__dict__.keys():
                        self.__dict__[k] = v.empty_copy()
                        self.__dict__[k].set_operation("delete", recursive=False, force=True)


    def clear_subtree(self, ignores=None):
        """
        Removes children recursively
        :param ignores: list of attributes to be ignored (e.g., keys)
        :return:
        """

        _ignores = list(__IGNORED_ATTRIBUTES__)
        if ignores is not None:
            if type(ignores) is tuple:
                _ignores.extend(ignores)
            else:
                _ignores.append(ignores)
        for k, v in self.__dict__.items():
            if type(self._parent) is ListYang:
                if k == self.keys():
                    _ignores.append(k)
            if k not in _ignores:
                if isinstance(v, Yang):
                    v.delete()

    def get_path(self, path_cache=None, drop=0):
        """
        Returns the complete path (since the root) of the instance of Yang
        :param: -
        :return: string
        """
        if drop > 0:
            if self._parent is None:
                raise ValueError("get_path cannot drop {drop} tails at {path}".format(drop=drop, path=self.get_path(path_cache=path_cache)))
            return self._parent.get_path(path_cache=path_cache, drop=drop-1)

        try:
            return path_cache[self]  # if object is already in the cache
        except:
            pass
        if self._parent is not None:
            p = self._parent.get_path(path_cache=path_cache) + "/" + self.get_tag()
        elif not self._floating:
            p = "/" + self.get_tag()
        else:
            p = self.get_tag()
        if (path_cache is not None) and (not self._floating):
            path_cache[self] = p
        return p

    def has_path(self, path, at=None):
        """
        Check if path is in the object's path
        :param path: string, pattern to check for
        :param at: int, position to check for (can be negative)
        :return: boolean, True if match; False otherwise
        """
        p = PathUtils.path_to_list(self.get_path())
        if at is not None:
            if len(p) > abs(at):
                return p[at] == path
            return False
        return path in p

    def create_from_path(self, path):
        """
        Create yang tree from path
        :param path: string, path to create
        :return: Yang, Yang object at the source instance's / path's path
        """
        if path == "" or len(path) == 0:
            return self
        if type(path) in (list, tuple):
            p = path
        else:
            p = PathUtils.path_to_list(path)
        if len(p) < 1:
            return self
        if p[0] == "":  # absolute path
            if self.get_parent() is not None:
                return self.get_parent().create_from_path(p)
            p.pop(0)
            return self.create_from_path(p)
        l = p.pop(0)
        if l == "..":
            return self.get_parent().create_from_path(p)
        elif l == self._tag:
            return self.create_from_path(p)
        elif (l.find("[") > 0) and (l.find("]") > 0):
            attrib = l[0: l.find("[")]
            keystring = l[l.find("[") + 1: l.rfind("]")]
            keys = dict(item.split("=") for item in keystring.split(","))
            if self._tag == attrib:  # listed yang, with match
                if self.match_keys(**keys):
                    return self.create_from_path(p)
                else:
                    raise ValueError("Error: cannot create path at this entry, check configurations!!!\n{}\nfor path: {}".format(self, path))
            try:
                return self.__dict__[attrib][keys].create_from_path(p)
            except:
                # key does not exist
                _yang = self.__dict__[attrib]._type(**keys)
                self.__dict__[attrib].add(_yang)
                return self.__dict__[attrib][keys].create_from_path(p)
        else:
            try:
                return self.__dict__[l].create_from_path(p)
            except:
                logger.exception("Fixme: how to create class object")
                raise ValueError("Fixme: how to create class object")

        raise ValueError("create_from_path: no conditions matched ")

    def create_path(self, source, path=None, target_copy_type=None):
        """
        Create yang tree from source for non-existing objects along the path
        :param source: Yang, used to initialize the yang tree as needed
        :param path: string, path to create; if None then source's path is used
        :return: Yang, Yang object at the source instance's / path's path
        """
        try:
            if path is None:
                path = source.get_path()
            if type(path) in (list, tuple):
                p = path
            else:
                p = PathUtils.path_to_list(path)
            if len(p) < 1:
                return self
            _copy_type = "empty"
            if len(p) == 1:
                _copy_type = target_copy_type
            l = p.pop(0)
            if l == "":  # absolute path
                if self.get_parent() is not None:
                    return self.get_parent().create_path(source, path=path, target_copy_type=target_copy_type)
                elif self.get_tag() == PathUtils.split_tag_and_key_values(p[0])[0]:
                    p.pop(0)
                    return self.create_path(source, path=p, target_copy_type=target_copy_type)
                _p = PathUtils.path_to_list(self.get_path())
                # if p[0] == _p[1]:
                p.pop(0)
                return self.create_path(source, path=p, target_copy_type=target_copy_type)

                # raise ValueError("Root tag not found in walk_path()")
            if l == "..":
                return self.get_parent().create_path(source, path=p, target_copy_type=target_copy_type)
            elif (l.find("[") > 0) and (l.find("]") > 0):
                attrib = l[0: l.find("[")]
                keystring = l[l.find("[") + 1: l.rfind("]")]
                key = list()
                keyvalues = keystring.split(",")
                for kv in keyvalues:
                    v = kv.split("=")
                    key.append(v[1])
                if len(key) == 1:
                    key = key[0]

                if not (key in self.__dict__[attrib].keys()):
                    _yang = source.walk_path(self.get_path()).__dict__[attrib][key]
                    self.__dict__[attrib].add(_yang.copy(_copy_type))
                return getattr(self, attrib)[key].create_path(source, path=p, target_copy_type=target_copy_type)
            else:
                if (not (l in self.__dict__.keys())) or (getattr(self, l) is None):
                    _yang = getattr(source.walk_path(self.get_path()), l)
                    self.__dict__[l] = _yang.copy(_copy_type)
                    self.__dict__[l].set_parent(self)
                return getattr(self, l).create_path(source, path=p, target_copy_type=target_copy_type)
            raise ValueError("Root tag not found in walk_path()")
        except Exception as e:
            try:
                logger.error("CreatePath: attrib={} path={} at\n{}".format(l, '/'.join(p),self))
            except:
                pass
            finally:
                raise e


    def walk_path(self, path, reference=None):
        """
        Follows the specified path to return the instance the path points to (handles relative and absolute paths)
        :param path: string
        :return: attribute instance of Yang
        """
        if type(path) is Leafref:
            return self.walk_path(path.data)
        if type(path) in (list, tuple):
            p = path
        else:
            p = PathUtils.path_to_list(path)
        if len(p) < 1:
            return self
        l = p.pop(0)
        if l == "":  # absolute path
            if self.get_parent() is not None:
                return self.get_parent().walk_path(path, reference)
            if len(p) == 0:
                return self
            if self.get_tag() == PathUtils.split_tag_and_key_values(p[0])[0]:
                p.pop(0)
                return self.walk_path(p, reference)
            _p = PathUtils.path_to_list(self.get_path())
            if p[0] == _p[1]:
                p.pop(0)
                return self.walk_path(p, reference)
            # entry not in the current tree, let's try the reference tree
            if reference is not None:
                try:
                    yng = reference.walk_path(self.get_path(), reference=None)
                    return yng.walk_path(p, reference=None)
                except:
                    # path does not exist in the reference tree raise exception
                    raise ValueError("in walk_path(): Root tag not found neither in the current nor in the reference tree")
            # raise ValueError("Root tag not found in walk_path()")
        if l == "..":
            return self.get_parent().walk_path(p, reference)
        else:
            if (l.find("[") > 0) and (l.find("]") > 0):
                attrib = l[0: l.find("[")]
                keystring = l[l.find("[") + 1: l.rfind("]")]
                key = list()
                keyvalues = keystring.split(",")
                for kv in keyvalues:
                    v = kv.split("=")
                    key.append(v[1])
                if len(key) == 1:
                    if key[0] in self.__dict__[attrib].keys():
                        return getattr(self, attrib)[key[0]].walk_path(p, reference)
                    elif reference is not None:
                        yng = reference.walk_path(self.get_path(), reference=None)
                        p.insert(0, l)
                        return yng.walk_path(p, reference=None)
                elif key in self.__dict__[attrib].keys():
                   return getattr(self, attrib)[key].walk_path(p, reference)
            else:
                if (l in self.__dict__.keys()) and (getattr(self, l) is not None):
                    return getattr(self, l).walk_path(p, reference)
                elif reference is not None:
                    path = self.get_path()
                    yng = reference.walk_path(path, reference=None)
                    p.insert(0, l)
                    return yng.walk_path(p, reference=None)
        raise ValueError("Path does not exist from {f} to {t}; yang tree={y}".format(f=self.get_path(), t=l+"/"+"/".join(p), y=self.html()))

    def get_rel_path(self, target):
        """
        Returns the relative path from self to the target
        :param target: instance of Yang
        :return: string
        """
        src = self.get_path()
        dst = target.get_path()
        s = PathUtils.path_to_list(src)
        d = PathUtils.path_to_list(dst)
        if s[0] != d[0]:
            return dst
        i = 1
        ret = list()
        while s[i] == d[i]:
            i += 1
        for j in range(i, len(s)):
            ret.insert(0, "..")
        for j in range(i, len(d)):
            ret.append(d[j])
        return '/'.join(ret)

    @classmethod
    def parse(cls, parent=None, root=None):
        """
        Class method to create virtualizer from XML string
        :param parent: Yang
        :param root: ElementTree
        :return: class instance of Yang
        """
        temp = cls(root.tag, parent=parent)
        temp._parse(parent, root)
        return temp

    @classmethod
    def parse_from_file(cls, filename):
        try:
            tree = ET.parse(filename)
            return cls.parse(root=tree.getroot())
        except ET.ParseError as e:
            raise Exception('XML file ParseError: %s' % e.message)

    @classmethod
    def parse_from_text(cls, text):
        try:
            if text == "":
                raise ValueError("Empty file")
            tree = ET.ElementTree(ET.fromstring(text))
            return cls.parse(root=tree.getroot())
        except ET.ParseError as e:
            logger.exception("parse error: " + text)
            raise e
        except ValueError as e:
            logger.warning("parse_from_file EMPTY input")
            raise e

    @classmethod
    def parse_from_json(cls, virt_json):
        try:
            elem = YangJson.from_json(virt_json)
            return cls.parse(root=elem)
        except ET.ParseError as e:
            raise Exception('XML Text ParseError: %s' % e.message)

    def _et_attribs(self):
        attribs = {}
        for a in self._attributes:
            if self.__dict__[a] is not None:
                attribs[a.translate(None, '_')] = str(self.__dict__[a])
        return attribs

    def _et(self, node, inherited=False, ordered=True):
        """
        Inserts children and current nodes recursively as subelements of current ElementTree or create a new tree if it is not initialized;
        param node: reference to the node element
        return: Element of ElementTree
        """
        _prohibited = ["_tag", "_sorted_children", "_key_attributes", "_referred"]
        # attribs = {}
        # for a in self._attributes:
        #     if self.__dict__[a] is not None:
        #         attribs[a.translate(None, '_')] = str(self.__dict__[a])
        #
        if self.is_initialized():
            if node is not None:
                node = ET.SubElement(node, self.get_tag(), attrib=self._et_attribs())
            else:
                node = ET.Element(self.get_tag(), attrib=self._et_attribs())
            if len(self._sorted_children) > 0:
                for c in self._sorted_children:
                    if self.__dict__[c] is not None:
                        self.__dict__[c]._et(node, inherited, ordered)
        else:
            if node is None:
                node = ET.Element(self.get_tag(), attrib=self._et_attribs())

        return node

    def setHighlightSyntax(self, enabled):
        """ Sets whether syntax highlighting should be enabled for string
        output.
        :param enabled: True for enabling syntax highlighting, False for
        disabling """
        class DefaultSyntaxHighlight:
            Tag = "\033[1;32m"
            Attr = "\033[36m"
            Operation = "\033[1;31m"
            Reset = "\033[0m"
        class DisabledSyntaxHighlight:
            Tag = ""
            Attr = ""
            Operation = ""
            Reset = ""
        if enabled and sys.stdout.isatty():
            self._sh = DefaultSyntaxHighlight()
        else:
            self._sh = DisabledSyntaxHighlight()

    def _tree_to_string(self, el, s="", ident=0):
        if el is None: return ""
        if not hasattr(self, '_sh'):
            self.setHighlightSyntax(True)

        attrs = []
        subtrees = []
        for subel in el:
            if not list(subel):
                optag = subel.tag
                if subel.get("operation"):
                    optag = subel.get("operation").upper() + ":" + optag
                attrs.append(self._sh.Attr + optag + self._sh.Reset + "=" + \
                    "'" + str(subel.text) + "'")
            else:
                subtrees.append(subel)

        optag = self._sh.Tag + el.tag + self._sh.Reset
        if el.get("operation"):
            optag = self._sh.Operation + el.get("operation").upper() + ":" + \
                self._sh.Reset + optag
        s += ident*'    ' + optag
        s += " " + " ".join(attrs)

        for subtree in subtrees:
            s += "\n"
            s = self._tree_to_string(subtree, s, ident+1)

        return s

    def __str__(self):
        """
        Dump the class subtree as readable string.
        :return: string
        """
        root = self._et(None, False, True)
        return self._tree_to_string(root)

    def has_operation(self, operation):
        """
        Return True if instance's operation value is in the list of operation values
        :param operation: string or tuple of strings
        :return: boolean
        """
        if isinstance(operation, (tuple, list, set)):
            for op in operation:
                if (op is not None) and (op not in __EDIT_OPERATION_TYPE_ENUMERATION__):
                    raise ValueError("has_operation(): Illegal operation value={op} out of {operation}".format(op=op,
                                                                                                               operation=operation))
            return self._operation in operation
        if (operation is not None) and (operation not in __EDIT_OPERATION_TYPE_ENUMERATION__):
            raise ValueError("has_operation(): Illegal operation value={operation}".format(operation=operation))
        return self._operation == operation

    # def contains_operation(self, operation="delete"):  # FIXME: rename has_operation()
    #     """
    #     Verifies if the instance contains operation set for any of its attributes
    #     :param operation: string
    #     :return: boolean
    #     """
    #     if self.get_operation() == operation:
    #         return True
    #     for k, v in self.__dict__.items():
    #         if isinstance(v, Yang) and k is not "_parent":
    #             if v.contains_operation(operation):
    #                 return True
    #     return False

    def get_operation(self):
        """
        Returns the _operation attribute
        :param: -
        :return: string
        """
        return self._operation

    def set_operation(self, operation, recursive=True, force=True, execute=False):
        """
        Defines operation for instance
        :param operation: string
        :param recursive: boolean, default is True; determines if children operations are also set or not
        :param force: boolean, determines if overwrite of attribute is enforced (True) or not
        :param execute: boolean, determines if delete operations must be carried out (True) or just marked (False)
        :return: -
        """
        if issubclass(type(operation), Yang):
            operation = operation._operation

        if operation not in ((None,) + __EDIT_OPERATION_TYPE_ENUMERATION__):
            raise ValueError("Illegal operation value: operation={operation} at {yang}".format(operation=operation,
                                                                                               yang=self.get_as_text()))
        if force or (self._operation is None):
            self._operation = operation
            if operation is "delete" and execute:
                self.clear_subtree()
        if recursive:
            for k, v in self.__dict__.items():
                if isinstance(v, Yang) and k is not "_parent":
                    v.set_operation(operation, recursive=recursive, force=force, execute=execute)

    def replace_operation(self, fromop, toop, recursive=True):
        """
        Replaces operation for instance
        :param fromop: string
        :param toop: string
        :param recursive: boolean, default is True; determines if children operations are also set or not
        :return: -
        """
        if fromop not in ( __EDIT_OPERATION_TYPE_ENUMERATION__):
            raise ValueError("Illegal operation value: operation={operation} at {yang}".format(operation=fromop,
                                                                                               yang=self.get_as_text()))
        if toop not in ( __EDIT_OPERATION_TYPE_ENUMERATION__):
            raise ValueError("Illegal operation value: operation={operation} at {yang}".format(operation=toop,
                                                                                               yang=self.get_as_text()))
        if self._operation == fromop:
            self.set_operation(toop, recursive=False, force=True)
        if recursive:
            for k, v in self.__dict__.items():
                if isinstance(v, Yang) and k is not "_parent":
                    v.replace_operation(fromop, toop, recursive=recursive)

    def clear_data(self):
        _ignore = ['_parent', 'tag']
        for k, v in self.__dict__.items():
            if k not in _ignore:
                if isinstance(v, Yang):
                    v.clear_data()

    def is_initialized(self):
        """
        Check if any of the attributes of instance are initialized, returns True if yes
        :param: -
        :return: boolean
        """
        for k, v in self.__dict__.items():
            if isinstance(v, Yang) and (k is not "_parent"):
                if v.is_initialized():
                    return True
        return False

    def __eq__(self, other):
        """
        Check if all the attributes and class attributes are the same in instance and other, returns True if yes
        :param other: instance of Yang
        :return: boolean
        """
        if other is None:
            return False
        if self is other:
            # logger.warning("__eq__ for the same objects self={self}; other={other}".format(self=self.get_as_text(), other=other.get_as_text()))
            return True
        eq = True
        # Check attributes
        self_atribs = self.__dict__
        other_atribs = other.__dict__
        eq = eq and (self_atribs.keys().sort() == other_atribs.keys().sort())
        if eq:
            for k in self_atribs.keys():
                if k not in __EQ_IGNORED_ATTRIBUTES__:
                    for k_ in other_atribs.keys():
                        if k == k_:
                            eq = eq and (self_atribs[k] == other_atribs[k_])
                            if not eq: return False
        # Check class attributes
        self_class_atribs = self.__class__.__dict__
        other_class_atribs = other.__class__.__dict__
        eq = eq and (self_class_atribs.keys().sort() == other_class_atribs.keys().sort())
        if eq:
            for k in self_class_atribs.keys():
                for k_ in other_class_atribs.keys():
                    if k == k_ and not callable(self_class_atribs[k]):
                        eq = eq and (self_class_atribs[k] == other_class_atribs[k_])
                        if not eq: return False
        return eq

    def translate_and_merge(self, translator, destination, path_caches=None, execute=False):

        # prepare caches if needed
        if path_caches is None:
            path_caches = dict()
            path_caches['dst'] = dict()
            path_caches['src'] = dict()

        return self.__translate_and_merge__(translator, destination, path_caches=path_caches, execute=execute)


    def translate(self, translator, destination, path_caches=None):
        """
        Common recursive functionaltify for merge() and patch() methods with TRANSLATION. Execute defines if operation is copied or executed.
        :param destination: instance of Yang
        :param execute: True - operation is executed; False - operation is copied
        :return: yang: destination object
        """
        # prepare caches if needed
        if path_caches is None:
            path_caches = dict()
            path_caches['dst'] = dict()
            path_caches['src'] = dict()

        dst_path = translator.get_target_path(self.get_path(path_caches['src']))
        tmp = destination.empty_copy()
        dst = tmp.create_from_path(dst_path)

        dst.set_operation(self.get_operation(), recursive=False)  # copy operation over

        for k in self._sorted_children:
            if hasattr(self, '_key_attributes') and (k in self._key_attributes):
                pass
            else:
                if dst.__dict__[k] is None:
                    dst.create_from_path(k)
                self.__dict__[k].__translate_and_merge__(translator, dst.__dict__[k], path_caches=path_caches)
        return dst

    def __translate_and_merge__(self, translator, destination, path_caches=None, execute=False):
        """
        Common recursive functionaltify for merge() and patch() methods with TRANSLATION. Execute defines if operation is copied or executed.
        :param destination: instance of Yang
        :param execute: True - operation is executed; False - operation is copied
        :return: yang: destination object
        """

        _delete = self.has_operation(('delete', 'remove'))
        dst_path = translator.get_target_path(self.get_path(path_caches['src']))
        dst = destination.create_from_path(dst_path)
        if execute and _delete:
            if isinstance(dst, Leaf):
                dst.clear_data()
            else:
                dst.delete()
            return dst

        if not self.is_initialized():
            return dst

        for k in self._sorted_children:
            if _delete:
                if dst.__dict__[k] is not None:
                    dst.__dict__[k].delete()
            elif self.__dict__[k] is not None:
                if dst.__dict__[k] is None:
                    dst.create_from_path(k)
                self.__dict__[k].__translate_and_merge__(translator, dst.__dict__[k], path_caches=path_caches, execute=execute)

        if execute:
            dst.set_operation(None, recursive=False)
        else:
            dst.set_operation(self)
        return dst

    def __merge__(self, source, execute=False):
        """
        Common recursive function for merge() and patch() methods. Execute defines if operation is copied or executed.
        :param source: instance of Yang
        :param execute: True - operation is executed; False - operation is copied
        :return: -
        """

        if execute and source.has_operation(('delete', 'remove')):
            if isinstance(source, Leaf):
                self.clear_data()
            else:
                self.delete()
            return

        if not source.is_initialized():
            return

        for k, v in source.__dict__.items():
            if k is not "_parent":
                if k not in self.__dict__.keys():
                    if not (execute and source.has_operation(('delete', 'remove'))):
                        if isinstance(v, Yang):
                            self.__dict__[k] = v.full_copy()
                            self.__dict__[k].set_parent(self)
                        else:
                            self.__dict__[k] = copy.deepcopy(v)
                else:
                    if isinstance(v, Yang):
                        if isinstance(self.__dict__[k], Yang):
                            self.__dict__[k].__merge__(v, execute)
                        else:
                            self.__dict__[k] = v.full_copy()
                            self.__dict__[k].set_parent(self)
                    else:
                        if (v != self.__dict__[k]) and (v is not None):
                            self.__dict__[k] = copy.deepcopy(v)

    def merge(self, source):
        """
        Merge source into the instance recursively; source remains unchanged.
        :param source: instance of Yang
        :return: -
        """
        dst = self.create_path(source)
        dst.__merge__(source, False)

    def patch(self, source):
        """
        Method to process diff changeset, i.e., merge AND execute operations in the diff. For example, operation = delete removes the yang object.        :param diff: Yang
        :return: -
        """
        dst = self.create_path(source, target_copy_type="empty")
        dst.__merge__(source, execute=True)
        dst.set_operation(None, recursive=True, force=True, execute=True)

    def copy(self, copy_type=None):
        """
        Wrapper method for copying yang subtree
        :param copy_type: full|yang|empty, default is full
        :return: yang object
        """
        if (copy_type is None) or (copy_type == "full"):
            return self.full_copy()
        elif copy_type == 'yang':
            return self.yang_copy()
        else:
            return self.empty_copy()

    def empty_copy(self):
        """
        Create a new Yang instance of the same type, only the tag and key values are set (see ListedYang overrides)
        :param: -
        :return: instance copy (of Yang)
        """
        result = self.__class__(self._tag)
        result._referred = []
        return result


    def full_copy(self, memo=None):
        """
        Performs deepcopy of instance of Yang
        :param: -
        :return: instance copy (of Yang)
        """
        if memo is None:
            memo = {}
        if self._parent is not None:
            memo[id(self._parent)] = None
        result = copy.deepcopy(self, memo)
        result._parent = None
        return result

    def full_copy_subtree(self):
        """
        Performs deepcopy of instance of Yang
        :param: -
        :return: instance copy (of Yang)
        """
        # let's save the parent
        return self.full_copy()
        # _parent = self._parent
        # self._parent = None  # to avoid upstream copying
        # _subtree = copy.deepcopy(self)
        # self._parent = _parent
        # return _subtree

    def yang_copy(self, parent=None):
        cls = self.__class__
        result = cls.__new__(cls)
        result._referred = []
        result._parent = parent
        for k in self._sorted_children:
            if self.__dict__[k] is not None:
                setattr(result, k, self.__dict__[k].yang_copy(result))
            else:
                setattr(result, k, self.__dict__[k])
        for k in __YANG_COPY_ATTRIBUTES__:
            setattr(result, k, copy.deepcopy(self.__dict__[k]))
        return result

    def __deepcopy__(self, memo, ignore_list = []):
        # if id(self) in memo.keys():
        #     return memo[id(self)]  # object seen
        # ignore_list.append("_parent")
        try:
            cls = self.__class__
            result = cls.__new__(cls)
            memo[id(self)] = result
            if self._parent is not None:
                if id(self._parent) not in memo.keys():
                    logger.error("Parent Error Stack: " + self.get_path())
                    raise YangCopyDifferentParent("At {path} parent is outside of the yang tree; object:\n{self}\nparent:{parent}".format(
                        path=self.get_path(), self=str(self), parent=str(self._parent)))
            for k, v in self.__dict__.items():
                if k not in ignore_list:
                    setattr(result, k, copy.deepcopy(v, memo))
            return result
        except YangCopyDifferentParent as e:
            logger.error("Parent Error Stack: " + self.get_path())
            raise e

    def delete(self):  # FIXME: if referred by a LeafRef?
        """
        Remove element when ListYang and set to None when Leaf
        :param: -
        :return: -
        """
        if self.get_parent() is not None:
            if isinstance(self, ListedYang):
                try:
                    # try to unregister object
                    self._parent.remove(self)
                except:
                    pass
            else:
                self.get_parent().__dict__[
                    self.get_tag()] = None  # FIXME: tag is not necessarily Python naming conform!

    def set_referred(self, leaf_ref):
        """
        Append in referred names of leafs referred (children of) by instance of Yang
        :param leaf_ref: LeafRef
        :return: -
        """
        if not hasattr(self, '_referred'):
            self._referred = []
        if leaf_ref not in self._referred:
            self._referred.append(leaf_ref)

    def unset_referred(self, leaf_ref):
        """
        Append in referred names of leafs referred (children of) by instance of Yang
        :param leaf_ref: LeafRef
        :return: -
        """
        if not hasattr(self, '_referred'):
            self._referred = []
        if leaf_ref in self._referred:
            self._referred.remove(leaf_ref)

    def bind(self, relative=True, reference=None):
        """
        Binds all elements of self attributes
        :param relative: Boolean
        :param reference: Yang tree, to copy missing referals if needed
        :return: -
        """
        if len(self._sorted_children) > 0:
            for c in self._sorted_children:
                if self.__dict__[c] is not None:
                    self.__dict__[c].bind(relative=relative, reference=reference)
        return

    def _convert_leafrefs_to(self, relative=False, recursive=True):
        """
        Convert Leafref to relative/absolute paths
        :param relative: True or False
        :param recursive: True - for all the sub-tree; False - local object only
        :return: -
        """
        if (len(self._sorted_children) > 0) and (recursive):
            for c in self._sorted_children:
                if self.__dict__[c] is not None:
                    self.__dict__[c]._convert_leafrefs_to(relative=relative, recursive=recursive)
        return

    def convert_leafrefs_to_absolute_path(self, recursive=True):
        return self._convert_leafrefs_to(relative=False, recursive=recursive)

    def convert_leafrefs_to_relative_path(self, recursive=True):
        return self._convert_leafrefs_to(relative=True, recursive=recursive)

    def _parse(self, parent, root):
        """
        Abstract method to create classes from XML string
        :param parent: Yang
        :param root: ElementTree
        :return: -
        """
        for key in self._sorted_children:
            item = self.__dict__[key]
            if isinstance(item, Leaf):
                item.parse(root)
            elif isinstance(item, ListYang):
                object_ = root.find(key)
                itemClass = item.get_type()
                while object_ is not None:
                    itemparsed = itemClass.parse(self, object_)
                    if "operation" in object_.attrib.keys():
                        itemparsed.set_operation(object_.attrib["operation"], recursive=False, force=True)
                    self.__dict__[key].add(itemparsed)
                    root.remove(object_)
                    object_ = root.find(key)
            elif isinstance(item, Yang):
                object_ = root.find(key)
                if object_ is not None:
                    item._parse(self, object_)
                    if "operation" in object_.attrib.keys():
                        self.set_operation(object_.attrib["operation"], recursive=False, force=True)
                    root.remove(object_)


    def diff(self, target):
        diff = target.yang_copy()
        diff._diff(self)
        return diff

    def diff_failsafe(self, target):
        base_xml = self.xml()
        base = self.parse_from_text(base_xml)
        candidate_xml = target.xml()
        candidate = self.parse_from_text(candidate_xml)
        diff = base.diff(candidate)
        return diff


class Leaf(Yang):
    """
    Class defining Leaf basis with attributes and methods
    """

    def __init__(self, tag, parent=None):
        super(Leaf, self).__init__(tag, parent)
        self.data = None
        """:type: ???"""
        self.mandatory = False
        """:type: boolean"""
        self.units = ""
        """:type: string"""
        self._leaf_attributes = ['data', 'mandatory', 'units', '_leaf_attributes']

    def yang_copy(self, parent=None):
        result = super(Leaf, self).yang_copy(parent)
        for k in self._leaf_attributes:
            setattr(result, k, copy.deepcopy(self.__dict__[k]))
        return result


    def __setattr__(self, key, value):
        """
        Calls set_value() for Leaf types so that they behave like string, int etc...
        :param key: string, attribute name
        :param value: value of arbitrary type
        :return: -
        """
        if (value is not None) and (key in self.__dict__) and issubclass(type(self.__dict__[key]),
                                                                             Leaf) and not issubclass(type(value), Yang):
            self.__dict__[key].set_value(value)
        else:
            self.__dict__[key] = value



    def __translate_and_merge__(self, translator, destination, path_caches=None, execute=False):
        """
        Common recursive functionaltify for merge() and patch() methods with TRANSLATION. Execute defines if operation is copied or executed.
        :param source: instance of Yang
        :param execute: True - operation is executed; False - operation is copied
        :return: -
        """

        if type(self) != type(destination):
            dst_path = translator.get_target_path(self.get_path(path_caches['src']))
            destination = destination.create_from_path(dst_path)

        if execute and self.has_operation(('delete', 'remove')):
            destination.clear_data()
        else:
            destination.set_value(self.get_value())
            if execute:
                destination.set_operation(None, recursive=False)
            else:
                destination.set_operation(self)


    def get_value(self):
        """
        Abstract method to get data value
        """
        return self.data

    def get_as_text(self):
        """
        Returns data value as text
        :param: -
        :return: string
        """
        return str(self.data)

    def set_value(self, value):
        """
        Abstract method to set data value
        """
        pass

    def get_units(self):
        """
        Return self.units
        :return: string
        """
        return self.units

    def set_units(self, units):
        """
        Set self.units
        :param units:
        :return: -
        """
        self.units = units

    def get_mandatory(self):
        """
        Return self.mandatory
        :return: string
        """
        return self.mandatory

    def set_mandatory(self, mandatory):
        """
        Set self.mandatory
        :param mandatory:
        :return: -
        """
        self.mandatory = mandatory

    def is_mandatory(self):
        """
        Returns True if mandatory field; otherwise returns false
        :return: boolean
        """
        return self.mandatory

    def is_initialized(self):
        """
        Overides Yang method to check if data contains value
        :param: -
        :return: boolean
        """
        if self.data is not None:
            return True
        return False

    def _et(self, node, inherited=False, ordered=True):
        """
        Overides Yang method return parent with subelement as leaf tag and data as text if it is initialized
        :param parent: ElementTree
        :return: Element of ElementTree
        """
        if self.is_initialized():
            if node is None:
                if type(self.data) is ET.Element:
                    return self.data
                else:
                    node = ET.Element(self.get_tag(), attrib=self._et_attribs())
                    node.text = self.get_as_text() + self.get_units()
            else:
                if type(self.data) is ET.Element:
                    node.append(self.data)
                else:
                    e_data = ET.SubElement(node, self.get_tag(), attrib=self._et_attribs())
                    e_data.text = self.get_as_text() + self.get_units()
        return node

    def clear_data(self):
        """
        Erases data defining it as None
        :param: -
        :return: -
        """
        self.data = None

    def delete(self):
        """
        Erases data defining it as None
        :param: -
        :return: -
        """
        self.data = None

    def reduce(self, reference):
        """
        Overrides Yang.reduce(): Delete instances which equivalently exist in the reference tree otherwise updates
        operation attribute.
        The call is recursive, a node is removed if and only if all of its children are removed.
        :param reference: instance of Yang
        :return: boolean
        """

        if self.data is None:
            return True
        if self.has_operation(("delete", "remove")):
            self.data = None
            return not self.has_operation(reference.get_operation())
        if isinstance(self.data, ET.Element):
            if ET.tostring(self.data) != ET.tostring(reference.data):
                if not self.has_operation(("delete", "remove")):
                    self.set_operation("replace", recursive=False, force=True)
                return False
            elif not self.has_operation([reference.get_operation(), "merge"]):
                return False
        else:
            if self.data != reference.data:
                if not self.has_operation(("delete", "remove")):
                    self.set_operation("replace", recursive=False, force=True)
                return False
            elif not self.has_operation([reference.get_operation(), "merge"]):
                return False
        return True


    def _diff(self, source):
        """
        Overrides Yang._diff(): ...
        The call is recursive, a node is removed if and only if all of its children are removed.
        :param reference: instance of Yang
        :return: boolean
        """

        if (self.data is None) and (source.data is not None):
            self.data = copy.deepcopy(source.data)
            self.set_operation("delete", recursive=False, force=True)
        elif (self.data is not None) and (source.data is None):
            self.set_operation("create", recursive=False, force=True)
        elif isinstance(self.data, ET.Element) or isinstance(source.data, ET.Element):
            try:
                if ET.tostring(self.data) == ET.tostring(source.data):
                    self.clear_data()
            except:
                self.set_operation("replace", recursive=False, force=True)
        elif self.get_as_text() != source.get_as_text():
            self.set_operation("replace", recursive=False, force=True)
        else:
            self.clear_data()

    def __eq__(self, other):
        """
        Check if other leaf has the same attributes and values, returns True if yes
        :param other: instance
        :return: boolean
        """
        eq = True
        for k, v in self.__dict__.items():
            if k not in __EQ_IGNORED_ATTRIBUTES__:
                eq = eq and (hasattr(other, k)) and (v == other.__dict__[k])
                if not eq:
                    return eq
        return eq

    def __ne__(self, other):
        return not self.__eq__(other)


class StringLeaf(Leaf):
    """
    Class defining Leaf with string extensions
    """

    def __init__(self, tag, parent=None, value=None, units="",
                 mandatory=False):  # FIXME: why having units for StringLeaf?
        super(StringLeaf, self).__init__(tag, parent=parent)
        self.set_value(value)
        """:type: string"""
        self.set_units(units)
        """:type: string"""
        self.set_mandatory(mandatory)  # FIXME: Mandatory should be handled in the Leaf class!
        """:type: boolean"""
        # self._leaf_attributes.extend(['units'])

    def parse(self, root):
        """
        Abstract method to create instance class StringLeaf from XML string
        :param root: ElementTree
        :return: -
        """
        e_data = root.find(self.get_tag())
        if e_data is not None:
            if len(e_data._children) > 0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data
            else:
                self.set_value(e_data.text)
            if "operation" in e_data.attrib.keys():
                self.set_operation(e_data.attrib["operation"], recursive=False, force=True)
            root.remove(e_data)

    def format(self, **kwargs):
        if self.data is not None:
            try:
                self.data = self.data.format(**kwargs)
            except:
                try:
                    _s = self.get_as_text()
                    _f = _s.find('{')
                    _l = _s.rfind('}')
                    if _l > _f:
                        _ss = _s[_f+1:_l]
                        _ss = _ss.format(**kwargs)
                        self.data = _s[0:_f+1] + _ss + _s[_l:len(_s)]
                except:
                    logger.warning("Cannot format string: {data}".format(data=self.data))

    def get_as_text(self, default=None):
        """
        Returns data value as text
        :param: -
        :return: string
        """
        if self.data is None and default is not None:
            return default
        if type(self.data) == ET:
            return ET.tostring(self.data, encoding="us-ascii", method="text")
        return super(StringLeaf, self).get_as_text()

    def set_value(self, value):
        """
        Sets data value
        :param value: string
        :return: -
        """
        if value is not None:
            if isinstance(value, (ET.ElementTree, ET.Element)):
                self.data = value
            else:
                self.data = str(value)
        else:
            self.data = value

    def __eq__(self, other):
        """
        Check if other leaf has the same attributes and values, returns True if yes
        :param other: instance
        :return: boolean
        """
        if type(other) is str:
            return self.data == other
        return super(StringLeaf, self).__eq__(other)

    def __ne__(self, other):
        """
        Check if other leaf has the same attributes and values, returns True if yes
        :param other: instance
        :return: boolean
        """
        if type(other) is str:
            return self.data != other
        return super(StringLeaf, self).__ne__(other)


class IntLeaf(Leaf):
    """
    Class defining Leaf with integer extensions (e.g., range)
    """

    def __init__(self, tag, parent=None, value=None, int_range=[], units="", mandatory=False):
        super(IntLeaf, self).__init__(tag, parent=parent)
        self.int_range = int_range
        self.data = None
        """:type: int"""
        if value is not None:
            self.set_value(value)
        self.set_units(units)
        """:type: string"""
        self.set_mandatory(mandatory)
        """:type: boolean"""

    def parse(self, root):
        """
        Creates instance IntLeaf setting its value from XML string
        :param root: ElementTree
        :return: -
        """

        def check_int(s):
            if s[0] in ('-', '+'):
                return s[1:].isdigit()
            return s.isdigit()

        e_data = root.find(self.get_tag())
        if e_data is not None:
            if len(e_data._children) > 0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data  # ?? don't know if need to replace as others
            else:
                if self.units != "":
                    for c in range(0, len(e_data.text)):
                        v = len(e_data.text) - c
                        st = e_data.text[:v]
                        if check_int(st):
                            self.set_value(st)
                            self.set_units(e_data.text[v:len(e_data.text)])
                            break
                else:
                    self.set_value(e_data.text)
            root.remove(e_data)
            self.initialized = True

    def get_value(self):
        """
        Returns data value
        :param: -
        :return: int
        """
        return self.data

    def set_value(self, value):
        """
        Sets data value as int
        :param value: int
        :return: -
        """
        if value is None:
            self.data = value
            return
        if type(value) is not int:
            try:
                value = int(value)
            except TypeError:
                logger.error("Cannot cast to integer!")
        if self.check_range(value):
            self.data = value
        else:
            logger.error ("Out of range!")

    def check_range(self, value):
        """
        Check if value is inside range limits
        :param value: int
        :return: boolean
        """
        for i in self.int_range:
            if type(i) is tuple:
                if value in range(i[0], i[1]):
                    return True
            else:
                if value == i:
                    return True
        return False



class Decimal64Leaf(Leaf):
    """
    Class defining Leaf with decimal extensions (e.g., dec_range)
    """

    def __init__(self, tag, parent=None, value=None, dec_range=[], fraction_digits=1, units="", mandatory=False):
        super(Decimal64Leaf, self).__init__(tag, parent=parent)
        self.dec_range = dec_range
        self.fraction_digits = fraction_digits
        self.data = None
        """:type: Decimal"""
        if value is not None:
            self.set_value(value)
        self.set_units(units)
        """:type: string"""
        self.set_mandatory(mandatory)
        """:type: boolean"""

    def parse(self, root):
        """
        Abstract method to instance class Decimal64Leaf from XML string
        :param root: ElementTree
        :return: -
        """
        e_data = root.find(self.get_tag())
        if e_data is not None:
            if len(e_data._children) > 0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data  # ?? don't know if need to replace as others
            else:
                self.set_value(e_data.text)
            root.remove(e_data)
            self.initialized = True

    def set_value(self, value):
        """
        Sets data value as decimal
        :param value: decimal
        :return: -
        """
        if type(value) is not Decimal:
            try:
                value = Decimal(value)
            except TypeError:
                logger.error("Cannot cast to Decimal!")
        if self.check_range(value):
            self.data = value
        else:
            logger.error("Out of range!")

    def check_range(self, value):
        """
        Check if value is inside range limits
        :param value: decimal
        :return: boolean
        """
        for i in self.dec_range:
            if type(i) is tuple:
                if value in range(i[0], i[1]):
                    return True
            else:
                if value == i:
                    return True
        return False


class BooleanLeaf(Leaf):
    """
    Class defining Leaf with boolean extensions (e.g., True or False)
    """

    def __init__(self, tag, parent=None, value=None, units="", mandatory=False):
        super(BooleanLeaf, self).__init__(tag, parent=parent)
        self.data = None
        """:type: boolean"""
        if value is not None:
            self.set_value(value)
        self.set_units(units)
        """:type: string"""
        self.set_mandatory(mandatory)
        """:type: boolean"""

    def parse(self, root):
        """
        Abstract method to create instance class BooleanLeaf from XML string
        :param root: ElementTree
        :return: -
        """
        e_data = root.find(self.get_tag())
        if e_data is not None:
            if len(e_data._children) > 0:
                for i in e_data.iter():
                    i.tail = None
                e_data.text = None
                self.data = e_data  # ?? don't know if need to replace as others
            else:
                self.set_value(e_data.text)
            root.remove(e_data)
            self.initialized = True

    def get_as_text(self):
        """
        Returns data value as text
        :param: -
        :return: string
        """
        return str(self.data).lower()

    def set_value(self, value):
        """
        Sets data value as decimal
        :param value: int
        :return: -
        """
        if value == "true":
            self.data = True
        elif value == "false":
            self.data = False
        else:
            raise TypeError("Not a boolean!")


class Leafref(StringLeaf):
    """
    Class defining Leaf extensions for stringleaf when its data references other instances
    """

    def __init__(self, tag, parent=None, value=None, units="", mandatory=False):
        self.target = None  # must be before the super call as set_value() is overidden
        """:type: Yang"""
        # super call calls set_value()
        super(Leafref, self).__init__(tag, parent=parent, value=value, mandatory=mandatory)
        # commented to avoid copying
        # self._leaf_attributes.append('target')

    def yang_copy(self, parent=None):
        result = super(Leafref, self).yang_copy(parent)
        result.target = None
        return result

    def __deepcopy__(self, memo):
        result = super(Leafref, self).__deepcopy__(memo, ignore_list=['target'])
        result.target = None
        return result

    def __translate_and_merge__(self, translator, destination, path_caches=None, execute=False):
        """
        Common recursive functionaltify for merge() and patch() methods with TRANSLATION. Execute defines if operation is copied or executed.
        :param destination: instance of Yang
        :param execute: True - operation is executed; False - operation is copied
        :return: -
        """
        # let's call ancestor's copy function first
        super(Leafref, self).__translate_and_merge__(translator, destination, path_caches=path_caches, execute=execute)
        translator.translate_leafref(destination)

    def set_value(self, value):
        """
        Sets data value as either a path or a Yang object
        :param value: path string or Yang object
        :return: -
        """
        if value is None:
            self.unbind()
            self.data = None
            self.target = None
            return
        if type(value) is str:
            value = value.translate(None, string.whitespace)  # removing whitespaces or newlines from path
            if self.data != value:
                self.unbind()
                self.target = None
                self.data = value
                # self.bind() # cannot call bind due to text parsing (destination may not be parsed yet)
        elif issubclass(type(value), Yang):
            if self.target != value:
                self.unbind()
                self.data = None
                self.target = value
                self.target.set_referred(self)
                # self.bind()
        else:
            raise ValueError("Leafref value is of unknown type.")

    def is_initialized(self):
        """
        Overides Leaf method to check if data contains data and target is set
        :param: -
        :return: boolean
        """
        if (self.data is not None) or (self.target is not None):
            return True
        else:
            return False

    def get_as_text(self):
        """
        If data return its value as text, otherwise get relative path to target
        :param: -
        :return: string
        """
        if self.data is not None:
            return self.data
        if self.target is not None:
            return self.target.get_path()
        else:
            raise ReferenceError("Leafref get_as_text() is called but neither data nor target exists.")

    def get_target(self, reference=None):
        """
        Returns get path to target if data is initialized
        :param: -
        :return: string
        """
        if self.target is None:
            return self.walk_path(self.data, reference=reference)
        return self.target

    def _convert_leafrefs_to(self, relative=False, recursive=True):
        """
        Convert Leafref to relative/absolute paths
        :param relative: True or False
        :param recursive: True - for all the sub-tree; False - local object only
        :return: -
        """
        if (self.target is None) and (self.data is None):  # operation delete
            return
        if relative:
            if self.target is not None:
                self.data = PathUtils.diff(self.get_path(), self.target.get_path())
            else:
                self.data = PathUtils.diff(self.get_path(), self.data)
        else:
            if self.target is not None:
                self.data = self.target.get_path()
                return
            self.data = PathUtils.add(self.get_path(), self.data)
        return


    def get_absolute_path_to_target(self, strip=0):
        """
        Returns the absolute path of the target
        :param: -
        :return: string
        """
        def _walk(path, steps):
            if len(steps) > 0:
                n = steps.pop(0)
                if n == "..":
                    path.pop(-1)
                    return _walk(path, steps)
                else:
                    path.append(n)
                    return _walk(path, steps)
            else:
                return path

        if self.target is not None:
            self.target.get_path()
        if self.data is not None:
            if self.data[0] == "/":  # absolute path
                return self.data
            path = PathUtils.path_to_list(self.get_path())
            steps = PathUtils.path_to_list(self.data)
            _path = _walk(path, steps)
            while strip > 0:
                _path.pop(-1)
                strip-=1
            return "/".join(_path)

    def get_target_from(self, src):
        path = self.get_absolute_path_to_target()
        t = None
        if type(src) is tuple:
            for s in src:
                try:
                    return s.walk_path(path)
                except: # object not found
                    pass
            text = ""
            for s in src:
                text += s.html() + "\n========================================"
            raise ValueError("{target} from {obj} is not available in \n{virt}".format(target=self.data,obj=self.get_path(),virt=text))
        else:
            try:
                return src.walk_path(path)
            except: # object not found
                pass
            raise ValueError("{target} from {obj} is not available in \n{virt}".format(target=self.data,obj=self.get_path(),virt=src.html()))

    def bind(self, relative=True, reference=None):
        """
        Binds the target and add the referee to the referende list in the target. The path is updated to relative or absolut based on the parameter
        :param relative: Boolean - Create relative paths if True; absolute path is False
        :param reference: Yang tree to copy missing objects from
        :return: -
        """
        if self.target is not None:
            if relative:
                self.data = self.get_rel_path(self.target)
            else:
                self.data = self.target.get_path()
        elif self.data is not None:
            if self._parent is not None:
                try:
                    if not '://' in self.data:
                        self.target = self.walk_path(self.data)
                except (ValueError):
                    if reference is not None:
                        self.create_path(source=reference, path=self.data, target_copy_type="yang")
                        self.target = self.walk_path(self.data)
                    else:
                        raise
                if self.target is not None:
                    self.target.set_referred(self)
                if not '://' in self.data:
                    if ((self.data[0] == "/") and (relative is True)) or ((self.data[0] != "/") and (relative is False)):
                        self.bind(relative=relative)

    def unbind(self):
        if self.target is not None:
            self.target.unset_referred(self)
            self.target = None

    def clear_data(self):
        """
        Erases data defining it as None
        :param: -
        :return: -
        """
        self.data = None
        self.target = None

    def _diff(self, source):
        """
        :param source: Yang
        :return: -
        """

        # self_path = ""
        # if self.target is not None:
        #     path_self = self.target.get_path()
        # elif self.data[0] == '/':
        #     path_self = self.data
        # elif self

        if (self.data is not None) and (source.data is not None):
            if self.data == source.data:
                self.clear_data()
            else:
                self.set_operation("replace", recursive=False, force=True)
        elif (self.data is None) and (source.data is not None):
            self.data = source.data
            self.set_operation("delete", recursive=False, force=True)
        elif (self.data is not None) and (source.data is None):
            self.set_operation("create", recursive=False, force=True)

    def __eq__(self, other):
        """
        Check if other leaf has the same attributes and values, returns True if yes
        :param other: instance
        :return: boolean
        """
        eq = True
        for k, v in self.__dict__.items():
            if k not in (__EQ_IGNORED_ATTRIBUTES__ + ("target",)):
                eq = eq and (hasattr(other, k)) and (v == other.__dict__[k])
        return eq


class ListedYang(Yang):
    """
    Class defined for Virtualizer classes inherit when modeled as list
    """

    def __init__(self, tag, keys, parent=None):
        super(ListedYang, self).__init__(tag, parent)
        self._key_attributes = keys

    def yang_copy(self, parent=None):
        cls = self.__class__
        result = cls.__new__(cls)
        result._parent = parent
        for k in self._sorted_children:
            if self.__dict__[k] is not None:
                setattr(result, k, self.__dict__[k].yang_copy(result))
            else:
                setattr(result, k, self.__dict__[k])
        for k in __YANG_COPY_ATTRIBUTES__:
            setattr(result, k, copy.deepcopy(self.__dict__[k]))
        result._key_attributes = copy.deepcopy(self._key_attributes)
        return result

    def __translate_and_merge__(self, translator, destination, path_caches=None, execute=False):
        """
        Common recursive functionaltify for merge() and patch() methods with TRANSLATION. Execute defines if operation is copied or executed.
        :param destination: instance of Yang
        :param execute: True - operation is executed; False - operation is copied
        :return: -
        """

        _delete = self.has_operation(('delete', 'remove'))
        dst_path = translator.get_target_path(self.get_path(path_caches['src']))
        dst = destination.create_from_path(dst_path)
        if execute and _delete:
            if isinstance(dst, Leaf):
                dst.clear_data()
            else:
                dst.delete()
            return

        if not self.is_initialized():
            return dst

        for k in self._sorted_children:
            if k not in dst._key_attributes:
                if _delete:
                    if dst.__dict__[k] is not None:
                        dst.__dict__[k].delete()
                elif self.__dict__[k] is not None:
                    if dst.__dict__[k] is None:
                        dst.create_from_path(k)
                    self.__dict__[k].__translate_and_merge__(translator, dst.__dict__[k], path_caches=path_caches, execute=execute)

        if execute:
            dst.set_operation(None, recursive=False)
        else:
            dst.set_operation(self, recursive=False)

        return dst

    def is_initialized(self, ignore_key=False):
        """
        Check if any of the attributes of instance are initialized, returns True if yes
        :param: -
        :return: boolean
        """
        if self._operation is not None:
            return True
        ignores = list()
        if ignore_key:
            ignores = self._key_attributes
        for c in self._sorted_children:
            try:

                if (self.__dict__[c] is not None) and (c not in ignores) and self.__dict__[c].is_initialized():
                    return True
            except:  # children was null?
                pass
        # for k, v in self.__dict__.items():
        #     if isinstance(v, Yang) and (k is not "_parent") and (k not in self._key_attributes):
        #         if v.is_initialized():
        #             return True
        return False

    def get_parent(self, level=1, tag=None):
        """
        Returns the parent in the class subtree. See parent class for parameters
        :return: Yang
        """
        if tag is not None:
            return super(ListedYang, self).get_parent(level=level, tag=tag)
        return super(ListedYang, self).get_parent(level=level+1, tag=tag)

    def keys(self):
        """
        Abstract method to get identifiers of class that inherit ListedYang
        """
        if len(self._key_attributes) > 1:
            keys = []
            for k in self._key_attributes:
                keys.append(self.__dict__[k].get_value())
            return tuple(keys)
        return self.__dict__[self._key_attributes[0]].get_value()

    def match_keys(self, **kwargs):
        """
        Check if item has the key
        :param kwargs:
        :return:
        """
        res = True
        for k in self._key_attributes:
            if k in kwargs.keys():
                res = res and (self.__dict__[k] == kwargs[k])
            else:
                return False
        return res

    def get_key_tags(self):
        """
        Abstract method to get tags of class that inherit ListedYang
        """
        if len(self._key_attributes) > 1:
            tags = []
            for k in self._key_attributes:
                tags.append(self.__dict__[k].get_tag())
            return tuple(tags)
        return self.__dict__[self._key_attributes[0]].get_tag()

    def get_path(self, path_cache=None, drop=0):
        """
        Returns path of ListedYang based on tags and values of its components
        :param: path_cache: dictionary of yang object paths
        :return: string
        """
        if drop > 0:
            if self._parent is None:
                raise ValueError("get_path cannot drop {drop} tails at {path}".format(drop=drop, path=self.get_path(path_cache=path_cache)))
            return self._parent.get_path(path_cache=path_cache, drop=drop-1)
        try:
            return path_cache[self]  # if object is already in the cache
        except:
            pass

        key_values = self.keys()
        if key_values is None:
            raise KeyError("List entry without key value: " + self.get_as_text())
        key_tags = self.get_key_tags()
        if type(key_tags) is tuple:
            s = ', '.join('%s=%s' % t for t in zip(key_tags, key_values))
        else:
            s = key_tags + "=" + key_values

        if self._parent is not None:
            try:
                p = path_cache[self._parent] + "/" + self.get_tag() + "[" + s + "]"
            except:
                p = self._parent.get_path(path_cache=path_cache) + "/" + self.get_tag() + "[" + s + "]"
        else:
            p = "/" + self.get_tag() + "[" + s + "]"
        if path_cache is not None:
            path_cache[self] = p
        return p

    def empty_copy(self):
        """
        Performs copy of instance defining its components with deep copy
        :param: -
        :return: instance
        """
        inst = self.__class__()
        for key in self._key_attributes:
            setattr(inst, key, getattr(self, key).full_copy())
        return inst

    def reduce(self, reference):
        """
        Delete instances which equivalently exist in the reference tree otherwise updates operation attribute
        The call is recursive, a node is removed if and only if all of its children are removed.
        :param reference: Yang
        :return:
        """
        keys = self.get_key_tags()
        return super(ListedYang, self).reduce(reference, keys)


    def _diff(self, source):
        """
        Delete instances which equivalently exist in the reference tree otherwise updates operation attribute
        The call is recursive, a node is removed if and only if all of its children are removed.
        :param reference: Yang
        :return:
        """
        keys = self.get_key_tags()
        return super(ListedYang, self)._diff(source, keys)

    def clear_subtree(self, ignores=None):
        keys = self.get_key_tags()
        return super(ListedYang, self).clear_subtree(keys)


class LeafListYang(Yang):
    """
    Implementation of LeafList
    """
    def __init__(self, tag, parent=None, type=None):
        super(ListYang, self).__init__(tag, parent)
        self._data = OrderedDict()
        self._type = type

    pass

    def get_next(self, children=None, operation=None, tags=None, _called_from_parent_=False, reference=None, path_filter=None):
        """
        Overrides Yang method. Returns the next Yang element followed by the one called for. It can be used for in-depth traversar of the yang tree.
        :param children: Yang (for up level call to hand over the callee children)
        :return: Yang
        """
        if operation is None:
            operation = (None,) + __EDIT_OPERATION_TYPE_ENUMERATION__
        if children is None:
            # return first key
            for key in self._data:
                if self._data[key].has_operation(operation) and self._data[key].match_tags(tags) and self._data[key].path_filter(path_filter, reference=reference):
                    return self._data[key]
        else:
            # pretty tricky internal dic access, see http://stackoverflow.com/questions/12328184/how-to-get-the-next-item-in-an-ordereddict
            next = self._data._OrderedDict__map[children.keys()][1]
            while not (next is self._data._OrderedDict__root):
                if self._data[next[2]].has_operation(operation) and self._data[next[2]].match_tags(tags) and self._data[next[2]].path_filter(path_filter, reference=reference):
                    return self._data[next[2]]

        # go to parent
        if (self._parent is not None) and (not _called_from_parent_):
            return self._parent.get_next(self, operation=operation, tags=tags, reference=reference, path_filter=path_filter)
        return None

    def add(self, item):
        """
        add single or a list of items
        :param item: a single ListedYang or a list of ListedYang derivates
        :return: item
        """
        if type(item) in (list, tuple):
            for i in item:
                if isinstance(i, ListedYang):
                    self.add(i)
                else:
                    raise TypeError("Item must be ListedYang or a list of ListedYang!")
        elif isinstance(item, ListedYang):
            item.set_parent(self)
            self[item.get_as_text()] = item
        else:
            raise TypeError("Item must be ListedYang or a list of ListedYang!")
        return item

    def remove(self, item):
        '''
        remove a single element from the list based on a key or a ListedYang
        :param item: key (single or composit) or a ListedYang
        :return: item
        '''
        if isinstance(item, ListedYang):
            item = item.get_as_text()
        return self._data.pop(item)

    def _et(self, node, inherited=False, ordered=True):
        """
        Overides Yang method to each ListYang component be defined as SubElement of ElementTree
        :param node: ElementTree
        :return: ElementTree
        """
        if node is None:
            node = ET.Element(self.get_tag())

        if ordered:
            ordered_keys = sorted(self.keys())
            for k in ordered_keys:
                self._data[k]._et(node, ordered)
        else:
            for v in self.values():
                v._et(node, ordered)
        return node

class ListYang(Yang):  # FIXME: to inherit from OrderedDict()
    """
    Class to express list as dictionary
    """

    def __init__(self, tag, parent=None, type=None):
        super(ListYang, self).__init__(tag, parent)
        self._data = OrderedDict()
        self._type = type

    def yang_copy(self, parent=None):
        cls = self.__class__
        result = cls(self._tag, parent=parent, type=self._type)
        for k, v in self._data.items():
            result._data[k] = v.yang_copy(result)
        for k in __YANG_COPY_ATTRIBUTES__:
            setattr(result, k, copy.deepcopy(self.__dict__[k]))
        return result

    def format(self, **kwargs):
        for v in self._data.itervalues():
            v.format(**kwargs)

    def __translate_and_merge__(self, translator, destination, path_caches=None, execute=False):
        """
        Common recursive functionaltify for merge() and patch() methods with TRANSLATION. Execute defines if operation is copied or executed.
        :param destination: instance of Yang
        :param execute: True - operation is executed; False - operation is copied
        :return: -
        """

        for k, v in self._data.items():
            v.__translate_and_merge__(translator, destination, path_caches=path_caches, execute=execute)


    def get_next(self, children=None, operation=None, tags=None, _called_from_parent_=False, reference=None, path_filter=None):
        """
        Overrides Yang method. Returns the next Yang element followed by the one called for. It can be used for in-depth traversar of the yang tree.
        :param children: Yang (for up level call to hand over the callee children)
        :return: Yang
        """
        if operation is None:
            operation = (None,) + __EDIT_OPERATION_TYPE_ENUMERATION__
        if children is None:
            # return first key
            for key in self._data:
                if self._data[key].has_operation(operation) and self._data[key].match_tags(tags) and self._data[key].path_filter(path_filter, reference=reference):
                    return self._data[key]
                else:
                    res = self._data[key].get_next(operation=operation, tags=tags, _called_from_parent_=True, reference=reference, path_filter=path_filter)
                    if res is not None:
                        return res
        else:
            # pretty tricky internal dic access, see http://stackoverflow.com/questions/12328184/how-to-get-the-next-item-in-an-ordereddict
            next = self._data._OrderedDict__map[children.keys()][1]
            while not (next is self._data._OrderedDict__root):
                if self._data[next[2]].has_operation(operation) and self._data[next[2]].match_tags(tags) and self._data[next[2]].path_filter(path_filter, reference=reference):
                    return self._data[next[2]]
                else:
                    res = self._data[next[2]].get_next(operation=operation, tags=tags, _called_from_parent_=True, reference=reference, path_filter=path_filter)
                    if res is not None:
                        return res
                    children = self._data[next[2]]
                    next = self._data._OrderedDict__map[children.keys()][1]

        # go to parent
        if (self._parent is not None) and (not _called_from_parent_):
            return self._parent.get_next(self, operation=operation, tags=tags, reference=reference, path_filter=path_filter)
        return None

    def get_type(self):
        """
        Returns class which references elements of _data OrderedDict
        :param: -
        :return: Yang subclass
        """
        return self._type

    def set_type(self, type):
        """
        Sets class which references elements of _data OrderedDict
        :param: Yang subclass
        :return: -
        """
        self._type = type

    def keys(self):
        """
        Returns indices of ListYang dictionary
        :param: -
        :return: list
        """
        return self._data.keys()

    def values(self):
        """
        Returns values of ListYang dictionary
        :param: -
        :return: list
        """
        return self._data.values()

    def iterkeys(self):
        """
        Returns iterator of keys of ListYang dictionary
        :param: -
        :return: iterator
        """
        return self._data.iterkeys()

    def itervalues(self):
        """
        Returns iterator of values of ListYang dictionary
        :param: -
        :return: list
        """
        return self._data.itervalues()

    def items(self):
        """
        Returns items of ListYang dictionary
        :param: -
        :return: list
        """
        return self._data.items()

    def iteritems(self):
        """
        Returns iterator of items of ListYang dictionary
        :param: -
        :return: list
        """
        return self._data.iteritems()

    def has_key(self, key):  # PEP8 wants it with 'in' instead of 'has_key()'
        """
        Returns if key is in ListYang dictionary
        :param key: string
        :return: boolean
        """
        return key in self._data.keys()

    def has_value(self, value):
        """
        Returns if value is in ListYang dictionary values
        :param value: string or instance
        :return: boolean
        """
        return value in self._data.values()

    def length(self):
        """
        Returns length of ListYang dictionary
        :param: -
        :return: int
        """
        return len(self._data)

    def is_initialized(self):
        """
        Returns if ListYang dictionary contains elements
        :param: -
        :return: boolean
        """
        if len(self._data) > 0:
            return True
        return False

    def add(self, item):
        """
        add single or a list of items
        :param item: a single ListedYang or a list of ListedYang derivates
        :return: item
        """
        if type(item) is list or type(item) is tuple:
            for i in item:
                if isinstance(i, ListedYang):
                    self.add(i)
                else:
                    raise TypeError("Item must be ListedYang or a list of ListedYang!")
        elif isinstance(item, ListedYang):
            item.set_parent(self)
            self[item.keys()] = item
        else:
            raise TypeError("Item must be ListedYang or a list of ListedYang!")
        return item

    def remove(self, item):
        '''
        remove a single element from the list based on a key or a ListedYang
        :param item: key (single or composit) or a ListedYang
        :return: item
        '''
        if isinstance(item, ListedYang):
            item = item.keys()
        return self._data.pop(item)

    def get_path(self, path_cache=None, drop=0):
        """
        Overides Yang method
        :param: -
        :return: upstream path
        """
        if drop > 0:
            if self._parent is None:
                raise ValueError("get_path cannot drop {drop} tails at {path}".format(drop=drop, path=self.get_path(path_cache=path_cache)))
            return self._parent.get_path(path_cache=path_cache, drop=drop-1)

        if self._parent is not None:
            p = self._parent.get_path(path_cache=path_cache)
        else:
            # if no parent, let's assume root
            p = "/"
        if path_cache is not None:
            path_cache[self] = p
        return p


    def _et(self, node, inherited=False, ordered=True):
        """
        Overides Yang method to each ListYang component be defined as SubElement of ElementTree
        :param node: ElementTree
        :return: ElementTree
        """
        if node is None:
            node = ET.Element(self.get_tag())

        if ordered:
            ordered_keys = sorted(self.keys())
            for k in ordered_keys:
                self._data[k]._et(node, ordered)
        else:
            for v in self.values():
                v._et(node, ordered)
        return node
        # for v in self.values():
        #     v._et(node)
        # return node

    def __iter__(self):  # ???
        """
        Returns iterator of ListYang dict
        :param: -
        :return: iterator
        """
        return self._data.__iter__()

    def next(self):
        """
        Go to next element of ListYang dictionary
        :param: -
        :return: -
        """
        self._data.next()

    def __getitem__(self, key):
        """
        Returns ListYang value if key in dictionary
        :param key: string
        :return: instance
        """
        if type(key) is list:
            key = tuple(key)
        if type(key) is dict:
            key = key.values()
            if len(key) == 1:
                key = key[0]
            else:
                key = tuple(key)
        if key in self._data.keys():
            return self._data[key]
        else:
            raise KeyError("key does not exist: {key} at: {item}".format(key=str(key), item=str(self)))

    def __setitem__(self, key, value):
        """
        Fill ListYang dict with key associated to value
        :param key: string
        :param value: string or instance
        :return: -
        """
        self._data[key] = value
        value.set_parent(self)

    def __delitem__(self, key):
        """
        Delete key from dictionary
        :param key: string
        :return: -
        """
        del self._data[key]

    def clear_data(self):
        """
        Clear ListYang dict
        :param: -
        :return: -
        """
        self._data = OrderedDict()

    def reduce(self, reference):
        """
        Check if all keys of reference are going to be reduced and erase their values if yes
        :param reference: ListYang
        :return: boolean
        """
        _reduce = True
        for key in self.keys():
            if key in reference.keys():
                if self[key].reduce(reference[key]):
                    del self[key]
                else:
                    # self[key].set_operation("replace", recursive=False, force=False)
                    _reduce = False
            else:
                self[key].set_operation(None, recursive=True, force=True)
                self[key].set_operation("create", recursive=False, force=True)
                _reduce = False
        return _reduce

    def _diff(self, source):
        """
        Check if all keys of reference are going to be reduced and erase their values if yes
        :param reference: ListYang
        :return: boolean
        """
        _done = []
        for key in self.keys():
            _done.append(key)
            if key in source.keys():
                self[key]._diff(source[key])
                if self[key].is_initialized(ignore_key=True) is False:
                    self[key].delete()
            else:
                self[key].set_operation("create", recursive=False, force=False)
        for key in source.keys():
            if key not in _done:
                item = source[key].empty_copy()
                item.set_operation("delete", recursive=False, force=True)
                self.add(item)

    def __merge__(self, source, execute=False):
        for item in source.keys():
            if item not in self.keys():
                if not (execute and source.has_operation(('delete', 'remove'))):
                    self.add(source[item].full_copy())
            else:
                if isinstance(self[item], Yang) and type(self[item]) == type(source[item]):
                    # self[item].set_operation(target[item].get_operation())
                    self[item].__merge__(source[item], execute)

    def __eq__(self, other):
        """
        Check if dict of other ListYang is equal
        :param other: ListYang
        :return: boolean
        """
        if not issubclass(type(other), ListYang):
            return False
        if self._data == other._data:
            return True
        return False

    def contains_operation(self, operation):
        """
        Check if any of items have operation set
        :param operation: string
        :return: boolean
        """
        for key in self._data.keys():
            if self._data[key].contains_operation(operation):
                return True
        return False

    def set_operation(self, operation, recursive=True, force=True, execute=False):
        """
        Set operation for all items in ListYang dict`
        :param operation: string
        :param recursive: boolean, default is True; determines if children operations are also set or not
        :param force: boolean, determines if overwrite of attribute is enforced (True) or not
        :param execute: boolean, determines if delete operations must be carried out (True) or just marked (False)
        :return: -
        """
        # super(ListYang, self).set_operation(operation, recursive=recursive, force=force)
        for key in self._data.keys():
            if execute and self._data[key].has_operation(('delete', 'remove')):
                del self._data[key]
            else:
                self._data[key].set_operation(operation, recursive=recursive, force=force, execute=execute)

    def replace_operation(self, fromop, toop, recursive=True):
        """
        Replace operation for all items in ListYang dict`
        :param fromop: string
        :param toop: string
        :param recursive: boolean, default is True; determines if children operations are also set or not
        :return: -
        """
        # super(ListYang, self).set_operation(operation, recursive=recursive, force=force)
        for key in self._data.keys():
            self._data[key].replace_operation(fromop, toop, recursive=recursive)

    def bind(self, relative=False, reference=None):
        for v in self.values():
            v.bind(relative=relative, reference=reference)

    def _convert_leafrefs_to(self, relative=False, recursive=True):
        """
        Convert Leafref to relative/absolute paths
        :param relative: True or False
        :param recursive: True - for all the sub-tree; False - local object only
        :return: -
        """
        for v in self.values():
            v._convert_leafrefs_to(relative=relative, recursive=recursive)

    def has_attrs_with_regex(self, av_list):
        def search_keys(pattern):
            result = []
            for key in self._data.keys():
                if re.match(pattern, key):
                    result.append(key)
            return result
        try:
            if len(av_list) == 1 and type(av_list[0]) in (list, tuple):
                return self.has_attrs_with_regex(av_list[0])
            if type(av_list) is tuple:
                av_list = list(av_list)
            if type(av_list[0]) is list:
                l = av_list.pop(0)
                attr = l[0]
            elif type(av_list[0]) is tuple:
                l = av_list.pop(0)
                if self.has_attrs_with_regex(l):
                    return self.has_attrs_with_regex(av_list)
            elif (len(av_list) == 2) and (isinstance(av_list[1], basestring)): # attrib and value check
                l = list(av_list)
                av_list = ()
                attr = l[0]
            else:
                l = av_list.pop(0)
                attr = l
            if self.has_key(attr):
                return self[attr].has_attrs_with_regex(av_list)
            return False
        except:
            return False


    def has_attrs_with_values(self, av_list, ignore_case=True):
        try:
            if len(av_list) == 1 and type(av_list[0]) in (list, tuple):
                return self.has_attrs_with_values(av_list[0], ignore_case)
            if type(av_list) is tuple:
                av_list = list(av_list)
            if type(av_list[0]) is list:
                l = av_list.pop(0)
                attr = l[0]
            elif type(av_list[0]) is tuple:
                l = av_list.pop(0)
                if self.has_attrs_with_values(l, ignore_case):
                    return self.has_attrs_with_values(av_list, ignore_case)
            elif (len(av_list) == 2) and (isinstance(av_list[1], basestring)): # attrib and value check
                l = list(av_list)
                av_list = ()
                attr = l[0]
            else:
                l = av_list.pop(0)
                attr = l
            _return = True
            if self.has_key(attr):
                return self[attr].has_attrs_with_values(av_list, ignore_case)
            return False
        except:
            return False


class FilterYang(Yang):
    def __init__(self, filter):
        # super(FilterYang, self).__init__()
        self.target = None
        self.result = None
        self.filter_xml = filter

    def run(self, yang):
        if self.filter_xml is not None:
            for child in self.filter_xml:
                self.result = self.walk_yang(child, yang, self.result)
        else:
            self.result = yang
        return self.result

    def walk_yang(self, filter, target, result):
        if target._tag == filter.tag:  # probably double check
            if isinstance(target, Iterable):

                if len(filter) > 0:
                    result = target.empty_copy()
                    for target_child in target:
                        for filter_child in filter:
                            result.add(self.walk_yang(filter_child,
                                                      target_child,
                                                      None))
                else:
                    for target_child in target:
                        result.add(target_child)
                return result
            else:
                if len(filter) > 0:
                    result = target.empty_copy()
                    for filter_child in filter:  # probably double check
                        if filter_child.tag in target.__dict__:
                            result.__dict__[filter_child.tag] = self.walk_yang(filter_child,
                                                                               target.__dict__[filter_child.tag],
                                                                               result.__dict__[filter_child.tag])
                    return result
                else:
                    return target.full_copy()

    def __str__(self):
        return ET.tostring(self.filter_xml)

    def xml(self):  # FIXME have to remove!
        return self.filter_xml

    def set_filter(self, filter):
        self.filter_xml = filter

    def get_filter(self):
        return self.filter_xml
