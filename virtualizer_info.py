#    Filename: virtualizer_info.py		 Created: 2017-02-04  17:25:55
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


# YANG construct: grouping object
class GroupingObject(Yang):
    def __init__(self, tag, parent=None, object=None):
        super(GroupingObject, self).__init__(tag, parent)
        self._sorted_children = ["object"]
        # yang construct: leaf
        self.object = Leafref("object", parent=self, value=object)
        """:type: Leafref"""


# YANG construct: grouping infoelement
class GroupingInfoelement(GroupingObject):
    def __init__(self, tag, parent=None, object=None, data=None):
        GroupingObject.__init__(self, tag, parent, object)
        self._sorted_children = ["object", "data"]
        # yang construct: leaf
        self.data = StringLeaf("data", parent=self, value=data)
        """:type: StringLeaf"""


# YANG construct: grouping connection
class GroupingConnection(GroupingObject):
    def __init__(self, tag, parent=None, object=None):
        GroupingObject.__init__(self, tag, parent, object)
        self._sorted_children = ["object", "objects"]
        # yang construct: list
        self.objects = ListYang("objects", parent=self, type=Object)
        """:type: ListYang(Object)"""

    def add(self, item):
        return self.objects.add(item)

    def remove(self, item):
        return self.objects.remove(item)

    def __getitem__(self, key):
        return self.objects[key]

    def __iter__(self):
        return self.objects.itervalues()


# YANG construct: list objects
class Object(ListedYang, GroupingObject):
    def __init__(self, tag="objects", parent=None, object=None):
        ListedYang.__init__(self, tag, ["object"])
        GroupingObject.__init__(self, tag, parent, object)
        self._sorted_children = ["object"]


# YANG construct: list log
class Infoelement(ListedYang, GroupingInfoelement):
    def __init__(self, tag="log", parent=None, object=None, data=None):
        ListedYang.__init__(self, tag, ["object"])
        GroupingInfoelement.__init__(self, tag, parent, object, data)
        self._sorted_children = ["object", "data"]


# YANG construct: list connection
class Connection(ListedYang, GroupingConnection):
    def __init__(self, tag="connection", parent=None, object=None):
        ListedYang.__init__(self, tag, ["object"])
        GroupingConnection.__init__(self, tag, parent, object)
        self._sorted_children = ["object", "objects"]


# YANG construct: container info
class Info(Yang):
    def __init__(self, tag="info", parent=None, logs=None, tops=None, connections=None):
        super(Info, self).__init__(tag, parent)
        self._sorted_children = ["logs", "tops", "connections"]
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
        # yang construct: container
        self.connections = None
        """:type: InfoConnections"""
        if connections is not None:
            self.connections = connections
        else:
            self.connections = InfoConnections(parent=self, tag="connections")


# YANG construct: container logs
class InfoLogs(Yang):
    def __init__(self, tag="logs", parent=None):
        super(InfoLogs, self).__init__(tag, parent)
        self._sorted_children = ["log"]
        # yang construct: list
        self.log = ListYang("log", parent=self, type=Infoelement)
        """:type: ListYang(Infoelement)"""

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
        self.top = ListYang("top", parent=self, type=Infoelement)
        """:type: ListYang(Infoelement)"""

    def add(self, item):
        return self.top.add(item)

    def remove(self, item):
        return self.top.remove(item)

    def __getitem__(self, key):
        return self.top[key]

    def __iter__(self):
        return self.top.itervalues()


# YANG construct: container connections
class InfoConnections(Yang):
    def __init__(self, tag="connections", parent=None):
        super(InfoConnections, self).__init__(tag, parent)
        self._sorted_children = ["connection"]
        # yang construct: list
        self.connection = ListYang("connection", parent=self, type=Connection)
        """:type: ListYang(Connection)"""

    def add(self, item):
        return self.connection.add(item)

    def remove(self, item):
        return self.connection.remove(item)

    def __getitem__(self, key):
        return self.connection[key]

    def __iter__(self):
        return self.connection.itervalues()

