__author__ = 'ekosrec'

import virtualizer
import copy


def combine(self, source):
    old_self = copy.deepcopy(self)
    self.merge(source)
    for virt1_node in old_self.nodes.node:
        virt1_saps = {}
        for port in old_self.nodes[virt1_node].ports.port:
            if old_self.nodes[virt1_node].ports[port].port_type.get_as_text() == 'port-sap':
                virt1_saps[old_self.nodes[virt1_node].ports[port].sap.get_as_text()]=old_self.nodes[virt1_node].ports[port].id.get_as_text()

        for virt2_node in source.nodes.node:
            virt2_saps = {}

            for port in source.nodes[virt2_node].ports.port:
                if source.nodes[virt2_node].ports[port].port_type.get_as_text() == 'port-sap':
                    virt2_saps[source.nodes[virt2_node].ports[port].sap.get_as_text()]=source.nodes[virt2_node].ports[port].id.get_as_text()

            pairs = {virt1_saps[k]: virt2_saps[k] for k in virt1_saps.keys() if k in virt2_saps.keys()}

            for virt1_port in pairs.keys():
                self.nodes[virt1_node].ports[virt1_port].port_type='port-abstract'
                self.nodes[virt2_node].ports[pairs[virt1_port]].port_type='port-abstract'
                link = virtualizer.Link(id='automaicliadded_'+virt1_port+'_'+pairs[virt1_port],
                                        name='aa_link',
                                        resources=virtualizer.Link_resource(delay=0, bandwidth=0)
                                        )

                self.links.add(link)
                link.src = link.src.get_rel_path(self.nodes[virt1_node].ports[virt1_port])
                link.dst = link.dst.get_rel_path(self.nodes[virt2_node].ports[pairs[virt1_port]])

                # link = virtualizer.Link(id='automaicliadded_'+pairs[virt1_port]+'_'+virt1_port,
                #                         name='aa_link',
                #                         resources=virtualizer.Link_resource(delay=0, bandwidth=0)
                #                         )
                #
                #
                # self.links.add(link)
                # link.src = link.dst.get_rel_path(self.nodes[virt2_node].ports[pairs[virt1_port]])
                # link.dst = link.src.get_rel_path(self.nodes[virt1_node].ports[virt1_port])
