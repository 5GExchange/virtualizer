#    Filename: virtualizer_info.py		 Created: 2016-10-12  13:29:07
#    This file was automatically created by a pyang plugin (PNC) developed at Ericsson Hungary Ltd., 2015
#    Authors: Robert Szabo, Balazs Miriszlai, Akos Recse, Raphael Vicente Rosa
#    Credits: Robert Szabo, Raphael Vicente Rosa, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
            
#    Yang file info:
#    Namespace: urn:unify:virtualizer_info
#    Prefix: virtualizer_info
#    Organization: ETH
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
#    Description: Monitoring support for the virtualizer

__copyright__ = "Copyright 2015, Ericsson Hungary Ltd."
__license__ = "Apache License, Version 2.0"
__version__ = "2016-10-09"

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


from baseclasses import *


# YANG construct: grouping element
class GroupingElement(Yang):
    def __init__(self, tag, parent=None, target=None, data=None):
        super(GroupingElement, self).__init__(tag, parent)
        self._sorted_children = ["target", "data"]
        # yang construct: leaf
        self.target = Leafref("target", parent=self, value=target)
        """:type: Leafref"""
        # yang construct: leaf
        self.data = StringLeaf("data", parent=self, value=data)
        """:type: StringLeaf"""


# YANG construct: list log
class Element(ListedYang, GroupingElement):
    def __init__(self, tag="log", parent=None, target=None, data=None):
        ListedYang.__init__(self, "log", ["target"])
        GroupingElement.__init__(self, tag, parent, target, data)
        self._sorted_children = ["target", "data"]


# YANG construct: container info
class Info(Yang):
    def __init__(self, tag="info", parent=None, logs=None, tops=None):
        super(Info, self).__init__(tag, parent)
        self._sorted_children = ["logs", "tops"]
        # yang construct: container
        self.logs = None
        """:type: InfoLogs"""
        if logs is not None:
            self.logs = logs
        else:
            self.logs = InfoLogs(parent=self, tag="logs")
        # yang construct: container
        self.tops = None
        """:type: InfoTops"""
        if tops is not None:
            self.tops = tops
        else:
            self.tops = InfoTops(parent=self, tag="tops")


# YANG construct: container logs
class InfoLogs(Yang):
    def __init__(self, tag="logs", parent=None):
        super(InfoLogs, self).__init__(tag, parent)
        self._sorted_children = ["log"]
        # yang construct: list
        self.log = ListYang("log", parent=self, type=Element)
        """:type: ListYang(Element)"""

    def add(self, item):
        return self.log.add(item)

    def remove(self, item):
        return self.log.remove(item)

    def __getitem__(self, key):
        return self.log[key]

    def __iter__(self):
        return self.log.itervalues()


# YANG construct: container tops
class InfoTops(Yang):
    def __init__(self, tag="tops", parent=None):
        super(InfoTops, self).__init__(tag, parent)
        self._sorted_children = ["top"]
        # yang construct: list
        self.log = ListYang("top", parent=self, type=Element)
        """:type: ListYang(Element)"""

    def add(self, item):
        return self.log.add(item)

    def remove(self, item):
        return self.log.remove(item)

    def __getitem__(self, key):
        return self.log[key]

    def __iter__(self):
        return self.log.itervalues()

