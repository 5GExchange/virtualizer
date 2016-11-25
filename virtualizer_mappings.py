#    Filename: virtualizer_mappings.py		 Created: 2016-11-19  17:06:59
#    This file was automatically created by a pyang plugin (PNC) developed at Ericsson Hungary Ltd., 2015
#    Authors: Robert Szabo, Balazs Miriszlai, Akos Recse, Raphael Vicente Rosa
#    Credits: Robert Szabo, Raphael Vicente Rosa, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
            
#    Yang file info:
#    Namespace: urn:5gex:virtualizer_mappings
#    Prefix: virtualizer_mappings
#    Organization: ETH
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
#    Description: Mapping resolution service for the virtualizer

__copyright__ = "Copyright 2015, Ericsson Hungary Ltd."
__license__ = "Apache License, Version 2.0"
__version__ = "2016-11-19"

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
import virtualizer_types as vt


# YANG construct: grouping mapping
class GroupingMapping(Yang):
    def __init__(self, tag, parent=None, target=None):
        super(GroupingMapping, self).__init__(tag, parent)
        self._sorted_children = ["object", "target"]
        vt.GroupingObject.__init__(self, tag, parent)
        # yang construct: container
        self.target = None
        """:type: MappingTarget"""
        if target is not None:
            self.target = target
        else:
            self.target = MappingTarget(parent=self, tag="target")


# YANG construct: list mapping
class Mapping(ListedYang, GroupingMapping):
    def __init__(self, tag="mapping", parent=None, target=None):
        ListedYang.__init__(self, "mapping", ["object"])
        GroupingMapping.__init__(self, tag, parent, target)
        self._sorted_children = ["object", "target"]


# YANG construct: container target
class MappingTarget(Yang):
    def __init__(self, tag="target", parent=None):
        super(MappingTarget, self).__init__(tag, parent)
        self._sorted_children = ["domain", "object"]
        vt.GroupingDestination.__init__(self, tag, parent)
        vt.GroupingObject.__init__(self, tag, parent)


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

