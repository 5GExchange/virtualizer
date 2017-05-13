__author__ = 'ekosrec'

import virtualizer
import copy

def combine(self, source):
    old_self = copy.deepcopy(self)
    self.merge(source)

    virt1_saps = {}
    for infra1 in old_self.nodes.node:
        for port in old_self.nodes[infra1].ports.port:
            if old_self.nodes[infra1].ports[port].port_type.get_as_text() == 'port-sap':
                if old_self.nodes[infra1].ports[port].sap.is_initialized():
                    if old_self.nodes[infra1].ports[port].sap_data.role.is_initialized():
                        sap_type = old_self.nodes[infra1].ports[port].sap_data.role.get_as_text()
                        virt1_saps[old_self.nodes[infra1].ports[port].sap.get_as_text()]=(infra1, port, sap_type)
                    else:
                        virt1_saps[old_self.nodes[infra1].ports[port].sap.get_as_text()]=(infra1, port)

    virt2_saps = {}
    for infra2 in source.nodes.node:
        for port in source.nodes[infra2].ports.port:
            if source.nodes[infra2].ports[port].port_type.get_as_text() == 'port-sap':
                if source.nodes[infra2].ports[port].sap.is_initialized():
                    if source.nodes[infra2].ports[port].sap_data.role.is_initialized():
                        sap_type = source.nodes[infra2].ports[port].sap_data.role.get_as_text()
                        virt2_saps[source.nodes[infra2].ports[port].sap.get_as_text()] = (infra2, port, sap_type)
                    else:
                        virt2_saps[source.nodes[infra2].ports[port].sap.get_as_text()] = (infra2, port)


    pairs = {virt1_saps[k]: virt2_saps[k] for k in virt1_saps.keys() if k in virt2_saps.keys()}

    for key in pairs.keys():
        infra1 = key[0]
        port1 = key[1]
        infra2 = pairs[key][0]
        port2 = pairs[key][1]

        # Only connect if one is not defined or if roles are different
        if len(key) < 3 or len(pairs[key]) < 3 or (key[2] != pairs[key][2]):
            self.nodes[infra1].ports[port1].port_type='port-abstract'
            self.nodes[infra2].ports[port2].port_type='port-abstract'

            id_int = 0
            id_fw = 'automaticallyadded_'+infra1+'-'+port1+'_'+infra2+'-'+port2
            id_bw = 'automaticallyadded_'+infra2+'-'+port2+'_'+infra1+'-'+port1

            while id_fw in self.links.link or id_bw in self.links.link:
                id_fw = 'automaticallyadded_'+infra1+'-'+port1+'_'+infra2+'-'+port2+'_'+str(id_int)
                id_bw = 'automaticallyadded_'+infra2+'-'+port2+'_'+infra1+'-'+port1+'_'+str(id_int)
                id_int += 1


            link_fw = virtualizer.Link(id=id_fw,
                                       name='aa_link',
                                       resources=virtualizer.Link_resource(delay=0, bandwidth=0)
            )
            self.links.add(link_fw)
            link_fw.src = link_fw.src.get_rel_path(self.nodes[infra1].ports[port1])
            link_fw.dst = link_fw.dst.get_rel_path(self.nodes[infra2].ports[port2])


            link_bw = virtualizer.Link(id=id_bw,
                                       name='aa_link',
                                       resources=virtualizer.Link_resource(delay=0, bandwidth=0)
            )
            self.links.add(link_bw)
            link_bw.src = link_bw.src.get_rel_path(self.nodes[infra2].ports[port2])
            link_bw.dst = link_bw.dst.get_rel_path(self.nodes[infra1].ports[port1])
        else:
            print(key, pairs[key])
