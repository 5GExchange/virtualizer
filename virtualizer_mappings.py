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

#    Filename: virtualizer_mappings.py		 Created: 2016-11-25  14:13:23
#    The original file was automatically created by a pyang plugin
#    (PNC) developed at Ericsson Hungary Ltd., 2015

#    Yang file info:
#    Namespace: urn:5gex:virtualizer_mappings
#    Prefix: virtualizer_mappings
#    Organization: 5GEx
#    Description: Mapping resolution service for the virtualizer

__author__ = "5GEx Consortium, Robert Szabo, Balazs Miriszlai, Akos Recse, Raphael Vicente Rosa"
__copyright__ = "Copyright 2018 5G Exchange (5GEx) Project, Copyright 2016-2017 Ericsson Hungary Ltd."
__credits__ = "Robert Szabo, Raphael Vicente Rosa, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse"
__license__ = "Apache License, Version 2.0"
__version__ = "2016-11-19"


from baseclasses import *


# YANG construct: grouping object
class GroupingObject(Yang):
    def __init__(self, tag, parent=None, object=None):
        super(GroupingObject, self).__init__(tag, parent)
        self._sorted_children = ["object"]
        # yang construct: leaf
        self.object = Leafref("object", parent=self, value=object)
        """:type: Leafref"""


# YANG construct: grouping mapping
class GroupingMapping(GroupingObject):
    def __init__(self, tag, parent=None, object=None, target=None):
        GroupingObject.__init__(self, tag, parent, object)
        self._sorted_children = ["object", "target"]
        # yang construct: container
        self.target = None
        """:type: MappingTarget"""
        if target is not None:
            self.target = target
        else:
            self.target = MappingTarget(parent=self, tag="target")


# YANG construct: list mapping
class Mapping(ListedYang, GroupingMapping):
    def __init__(self, tag="mapping", parent=None, object=None, target=None):
        ListedYang.__init__(self, "mapping", ["object"])
        GroupingMapping.__init__(self, tag, parent, object, target)
        self._sorted_children = ["object", "target"]


# YANG construct: container target
class MappingTarget(GroupingObject):
    def __init__(self, tag="target", parent=None, object=None, domain=None):
        GroupingObject.__init__(self, tag, parent, object)
        self._sorted_children = ["object", "domain"]
        # yang construct: leaf
        self.domain = StringLeaf("domain", parent=self, value=domain)
        """:type: StringLeaf"""


# YANG construct: container mappings
class Mappings(Yang):
    def __init__(self, tag="mappings", parent=None):
        super(Mappings, self).__init__(tag, parent)
        self._sorted_children = ["mapping"]
        # yang construct: list
        self.mapping = ListYang("mapping", parent=self, type=Mapping)
        """:type: ListYang(Mapping)"""

    def add(self, item):
        return self.mapping.add(item)

    def remove(self, item):
        return self.mapping.remove(item)

    def __getitem__(self, key):
        return self.mapping[key]

    def __iter__(self):
        return self.mapping.itervalues()

