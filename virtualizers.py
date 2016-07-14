#    Filename: virtualizers.py		 Created: 2016-07-08  18:58:21
#    This file was automatically created by a pyang plugin (PNC) developed at Ericsson Hungary Ltd., 2015
#    Authors: Robert Szabo, Balazs Miriszlai, Akos Recse, Raphael Vicente Rosa
#    Credits: Robert Szabo, Raphael Vicente Rosa, David Jocha, Janos Elek, Balazs Miriszlai, Akos Recse
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
            
#    Yang file info:
#    Namespace: urn:unify:virtualizers
#    Prefix: virtualizers
#    Organization: ETH
#    Contact: Robert Szabo <robert.szabo@ericsson.com>
#    Description: First release

__copyright__ = "Copyright 2015, Ericsson Hungary Ltd."
__license__ = "Apache License, Version 2.0"
__version__ = "2016-07-08"

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


# YANG construct: list virtualizer
class virtualizer(ListedYang):
    def __init__(self, tag="virtualizer", parent=None):
        ListedYang.__init__(self, "virtualizer", ["id"])
        self._sorted_children = ["id", "name", "nodes", "links", "metadata", "version"]
        v.GroupingVirtualizer.__init__(self, tag, parent)


# YANG construct: container virtualizers
class Virtualizers(Yang):
    """Container for a list of virtualizers"""
    def __init__(self, tag="virtualizers", parent=None):
        super(Virtualizers, self).__init__(tag, parent)
        self._sorted_children = ["virtualizer"]
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

