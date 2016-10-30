#    Filename: virtualizers.py		 Created: 2016-10-30  21:16:23
#    This file was automatically created by a pyang plugin (PNC) developed at Ericsson Hungary Ltd., 2015
#    Authors: Robert Szabo, Balazs Miriszlai, Akos Recse, Raphael Vicente Rosa
#    Credits: Robert Szabo, Raphael Vicente Rosa, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
            
#    Yang file info:
#    Namespace: urn:unify:virtualizers
#    Prefix: virtualizers
#    Organization: ETH
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
#    Description: Bind list added

__copyright__ = "Copyright 2015, Ericsson Hungary Ltd."
__license__ = "Apache License, Version 2.0"
__version__ = "2016-10-30"

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
import virtualizer as v



# YANG construct: grouping bind
class GroupingBind(Yang):
    def __init__(self, tag, parent=None):
        super(GroupingBind, self).__init__(tag, parent)
        self._sorted_children = ["bind"]
        # yang construct: list
        self.bind = ListYang("bind", parent=self, type=BindBind)
        """:type: ListYang(BindBind)"""

    def add(self, item):
        return self.bind.add(item)

    def remove(self, item):
        return self.bind.remove(item)

    def __getitem__(self, key):
        return self.bind[key]

    def __iter__(self):
        return self.bind.itervalues()


# YANG construct: list bind
class BindBind(ListedYang):
    def __init__(self, tag="bind", parent=None, id=None, src=None, dst=None):
        ListedYang.__init__(self, "bind", ["id"])
        self._sorted_children = ["id", "src", "dst"]
        # yang construct: leaf
        self.id = StringLeaf("id", parent=self, value=id, mandatory=True)
        """:type: StringLeaf"""
        # yang construct: leaf
        self.src = Leafref("src", parent=self, value=src)
        """:type: Leafref"""
        # yang construct: leaf
        self.dst = Leafref("dst", parent=self, value=dst)
        """:type: Leafref"""


# YANG construct: list virtualizer
class virtualizer(ListedYang, v.Virtualizer):
    def __init__(self, tag="virtualizer", parent=None):
        ListedYang.__init__(self, "virtualizer", ["id"])
        self._sorted_children = ["id", "name", "nodes", "links", "metadata", "version"]
        v.GroupingVirtualizer.__init__(self, tag, parent)


# YANG construct: container virtualizers
class Virtualizers(GroupingBind):
    """Container for a list of virtualizers"""
    def __init__(self, tag="virtualizers", parent=None):
        GroupingBind.__init__(self, tag, parent)
        self._sorted_children = ["virtualizer", "bind"]
        # yang construct: list
        self.virtualizer = ListYang("virtualizer", parent=self, type=virtualizer)
        """:type: ListYang(V:virtualizer)"""

    def add(self, item):
        return self.virtualizer.add(item)

    def remove(self, item):
        return self.virtualizer.remove(item)

    def __getitem__(self, key):
        return self.virtualizer[key]

    def __iter__(self):
        return self.virtualizer.itervalues()

